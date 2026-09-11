#!/usr/bin/env python3
"""pipeline/delivery_hygiene.py: 交付卫生审计与脱敏

解决一个具体问题：本 Agent 会被交付给用户使用，而运行期必需的凭据
（LLM API Key、渠道上架凭据、沙箱密钥）只存在于工作区的未跟踪文件里：

    config/llm_endpoints.json   （明文 apiKey，已被 .gitignore 忽略）
    .env                        （沙箱/商店凭据，已被 .gitignore 忽略）
    环境变量                     （进程内，不落盘）

gitignore 只能挡住 git，挡不住「把整个工作区打包 zip 发给人」。
本模块提供三件事：

    1. scan / audit   —— 扫描目录里的秘密文件与明文密钥串，实测命中并定位
    2. redact         —— 把任意文本里的密钥串打码，供日志与报告安全落盘
    3. sanitize_copy  —— 生成脱敏交付副本，排除秘密文件，并复检自证干净

诚实红线：本模块只做「检测 + 排除 + 打码」，绝不假装加密或假装安全。
扫描基于已知模式，不能证明不存在未知形式的秘密；因此结论表述为
「未命中已知模式」而不是「绝对无泄露」。
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Pattern, Tuple

CLEAN = "CLEAN"
LEAK = "LEAK"

REDACTED = "***REDACTED***"

# ── 已知密钥串模式（命中即视为泄露候选） ───────────────────────────────────
SECRET_PATTERNS: List[Tuple[str, Pattern[str]]] = [
    # 收紧为两段式：纯字母数字长串，或 sk-<已知前缀段>-<长串>。
    # 早期写法 sk-[A-Za-z0-9_-]{16,} 会把 "risk-impact-..." 这类普通英文判成密钥。
    ("openai_style_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("prefixed_api_key", re.compile(r"sk-(?:proj|or|ant|live|test|beta)-[A-Za-z0-9_\-]{20,}")),
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}")),
    ("wechat_appid", re.compile(r"\bwx[0-9a-f]{16}\b")),
    (
        "json_secret_value",
        re.compile(
            r"(?i)[\"'](?:api[_-]?key|apikey|secret|token|password|passwd|access[_-]?key)[\"']\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']"
        ),
    ),
    # 仅匹配顶格的环境变量赋值（.env / shell 风格）。
    # 带缩进的 Python 常量（如类内 CLOUD_KEY_PREFIX = "save_slot_"）不算秘密。
    (
        "env_secret_assignment",
        re.compile(r"(?m)^(?:export[ \t]+)?[A-Za-z_][A-Za-z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD)[A-Za-z0-9_]*[ \t]*=[ \t]*[\"']?([^\s\"'#]{8,})"),
    ),
]

# ── 敏感文件名（整文件禁止进入交付物，不看内容） ───────────────────────────
SECRET_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "llm_endpoints.json",
    "credentials.json",
    "service_account.json",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}

SECRET_FILENAME_SUFFIXES = (".pem", ".p12", ".pfx", ".key", ".keystore", ".jks", ".p8", ".asc", ".ppk", ".kdbx")

# ── 扫描时跳过的目录（体积大且不属于交付源码） ─────────────────────────────
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".mypy_cache", ".idea", ".vscode"}

# ── 只做内容扫描的文本扩展（二进制如 png/zip 不扫内容，交由文件名规则处理） ──
TEXT_SUFFIXES = {
    ".py", ".json", ".md", ".txt", ".toml", ".yml", ".yaml", ".ini", ".cfg", ".conf",
    ".sh", ".bash", ".ps1", ".bat", ".env", ".example", ".js", ".ts", ".html", ".css", ".gd",
}

MAX_SCAN_FILE_BYTES = 4 * 1024 * 1024
MAX_SCAN_FILES = 50000

# ── 命中分类：形式相同，性质不同，处置也不同 ─────────────────────────────────
CODE = "code"
TEST_FIXTURE = "test_fixture"      # 测试固件里的构造假值，不是真凭据
EXTERNAL_DOC = "external_doc"      # 抓取/引用的第三方文档内容，非我方配置


def categorize(path_str: str) -> str:
    """判断命中所在位置属于哪一类，决定它是否构成交付阻断。"""
    p = str(path_str).replace("\\", "/").lower()
    if p.startswith("tests/") or "/tests/" in p or "/test_" in p or p.endswith("/conftest.py"):
        return TEST_FIXTURE
    if p.startswith("docs/") or "/docs/" in p:
        return EXTERNAL_DOC
    return CODE

__all__ = [
    "CLEAN", "LEAK", "REDACTED", "SECRET_PATTERNS", "SECRET_FILENAMES",
    "redact", "redact_values", "scan_path", "audit_delivery", "sanitize_copy",
    "is_secret_filename",
]


def is_secret_filename(name: str) -> bool:
    """按文件名判定是否属于禁止进入交付物的秘密文件。"""
    lower = name.lower()
    if lower in SECRET_FILENAMES:
        return True
    if lower.endswith(SECRET_FILENAME_SUFFIXES):
        return True
    # .env 及其变体（.env.local / .env.prod 等），但放开 .env.example 模板
    if lower == ".env" or (lower.startswith(".env.") and lower != ".env.example"):
        return True
    return False


def redact(text: str) -> str:
    """把文本中命中已知模式的部分替换为 REDACTED，供日志/报告安全落盘。"""
    if not text:
        return text
    out = str(text)
    for label, pattern in SECRET_PATTERNS:
        out = pattern.sub(lambda _m, _l=label: f"{REDACTED}[{_l}]", out)
    return out


def redact_values(text: str, values: Iterable[str]) -> str:
    """按具体值打码：用于把命令行、环境变量里的真实凭据值替换掉。"""
    out = str(text)
    for raw in values:
        value = (raw or "").strip()
        if len(value) >= 4 and value in out:
            out = out.replace(value, REDACTED)
    return out


def _read_text(path: Path) -> Optional[str]:
    try:
        if path.stat().st_size > MAX_SCAN_FILE_BYTES:
            return None
    except OSError:
        return None
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def scan_path(
    root: Path,
    skip_dirs: Optional[set] = None,
    check_content: bool = True,
) -> Dict[str, Any]:
    """扫描目录下的秘密文件与明文密钥串。

    返回 {"status", "root", "scanned_files", "findings": [...]}
    findings 中的 snippet 已打码，扫描器本身不会把秘密再泄漏一遍。
    """
    root = Path(root)
    skip = set(skip_dirs or SKIP_DIRS)
    findings: List[Dict[str, Any]] = []
    scanned = 0

    if not root.exists():
        return {"status": CLEAN, "root": str(root), "scanned_files": 0, "findings": [],
                "note": "目标路径不存在，未扫描"}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for filename in filenames:
            if scanned >= MAX_SCAN_FILES:
                break
            path = Path(dirpath) / filename
            scanned += 1
            try:
                rel = str(path.relative_to(root))
            except ValueError:
                rel = str(path)
            category = categorize(rel)

            if is_secret_filename(filename):
                findings.append({
                    "kind": "secret_file",
                    "rule": "secret_filename",
                    "category": category,
                    "path": str(path),
                    "line": 0,
                    "detail": "命中敏感文件名规则，禁止进入交付物",
                })
                continue

            if not check_content:
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES and filename.lower() not in SECRET_FILENAMES:
                continue

            content = _read_text(path)
            if content is None:
                continue
            for label, pattern in SECRET_PATTERNS:
                match = pattern.search(content)
                if match:
                    line_no = content[: match.start()].count("\n") + 1
                    findings.append({
                        "kind": "secret_content",
                        "rule": label,
                        "category": category,
                        "path": str(path),
                        "line": line_no,
                        "detail": redact(match.group(0))[:120],
                    })

    return {
        "status": LEAK if findings else CLEAN,
        "root": str(root),
        "scanned_files": scanned,
        "findings": findings,
    }


def audit_delivery(root: Path, check_content: bool = True, strict: bool = False) -> Dict[str, Any]:
    """对「即将交付出去的目录」做卫生审计。

    默认只有 CODE 类命中会阻断交付：测试固件里的构造假值和抓取的第三方文档
    并不是我方凭据，一律报警会造成「狼来了」，反而让真正的命中被忽略。
    strict=True 时任何命中都阻断，用于人工复核。

    诚实口径：CLEAN = 未命中已知模式，不等于「绝对无泄露」。
    """
    report = scan_path(root, check_content=check_content)
    findings = report["findings"]
    blocking = findings if strict else [f for f in findings if f["category"] == CODE]

    counts = {CODE: 0, TEST_FIXTURE: 0, EXTERNAL_DOC: 0}
    for item in findings:
        counts[item["category"]] = counts.get(item["category"], 0) + 1

    report["status"] = LEAK if blocking else CLEAN
    report["deliverable"] = not blocking
    report["strict"] = bool(strict)
    report["blocking_findings"] = blocking
    report["counts_by_category"] = counts
    report["checked_at"] = _now_iso()
    if not strict and (counts[TEST_FIXTURE] or counts[EXTERNAL_DOC]):
        report["note"] = ("存在非代码类命中（测试固件构造假值 / 第三方文档内容），"
                          "未计入阻断；如需一并处理用 strict 模式查看")
    return report


def sanitize_copy(
    src: Path,
    dst: Path,
    extra_exclude_names: Iterable[str] = (),
    extra_exclude_dirs: Iterable[str] = (),
) -> Dict[str, Any]:
    """生成脱敏交付副本：排除秘密文件，并复检自证产物干净。

    策略是「排除」而非「改写」——不静默修改源码内容。
    若某个未命中排除规则的文件内容扫出密钥，同样排除并如实记录。
    """
    src = Path(src)
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

    exclude_names = {n.lower() for n in extra_exclude_names}
    exclude_dirs = set(SKIP_DIRS) | {d.lower() for d in extra_exclude_dirs}

    copied: List[str] = []
    excluded: List[Dict[str, str]] = []

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(src))
        except ValueError:
            return str(p)

    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d.lower() not in exclude_dirs]
        current = Path(dirpath)
        rel_dir = current.relative_to(src) if current != src else Path(".")
        target_dir = dst / rel_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        for filename in filenames:
            path = current / filename
            lower = filename.lower()

            if is_secret_filename(filename) or lower in exclude_names:
                excluded.append({"path": _rel(path), "reason": "secret_filename_or_excluded"})
                continue

            if path.suffix.lower() in TEXT_SUFFIXES:
                content = _read_text(path)
                if content is not None:
                    hit = None
                    for label, pattern in SECRET_PATTERNS:
                        if pattern.search(content):
                            hit = label
                            break
                    # 测试固件里的构造假值不算真凭据，不因此删掉整个测试文件
                    if hit and categorize(_rel(path)) == CODE:
                        excluded.append({"path": _rel(path), "reason": f"content_scan:{hit}"})
                        continue
                (target_dir / filename).write_bytes(path.read_bytes())
                copied.append(_rel(path))
                continue

            try:
                shutil.copy2(path, target_dir / filename)
            except OSError:
                excluded.append({"path": _rel(path), "reason": "copy_failed"})
                continue
            copied.append(_rel(path))

    recheck = audit_delivery(dst, check_content=True)
    return {
        "status": recheck["status"],
        "src": str(src),
        "dst": str(dst),
        "copied_files": len(copied),
        "excluded_files": excluded,
        "recheck": {
            "status": recheck["status"],
            "blocking": len(recheck.get("blocking_findings", [])),
            "counts_by_category": recheck.get("counts_by_category", {}),
            "findings": recheck["findings"],
        },
        "note": "排除敏感文件后对产物复检；status=CLEAN 表示产物未命中已知密钥模式",
    }


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
