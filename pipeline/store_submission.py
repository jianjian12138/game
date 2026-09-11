#!/usr/bin/env python3
"""pipeline/store_submission.py: 第三方渠道上架包与提交前门禁

与分发中枢（commercial_distribution_hub）的分工：
  分发中枢 = 把游戏打成各渠道包；
  本模块    = 补齐「商店上架」必须的东西，并在提交前真实拦截：
              - 商店元数据（标题/简介/关键词/分级/隐私政策）
              - 素材清单（图标、截图、宣传图）且必须真实存在、尺寸达标
              - 合规清单（防沉迷、隐私、分级问卷、SDK 声明、包体阈值）
              - 提交动作：缺凭据报 NEEDS_SANDBOX_CREDENTIALS，
                         缺官方上传器报 NEEDS_RUNTIME_TOOL，
                         绝不把「包打好了」说成「已上架」。
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pipeline.delivery_hygiene import redact, redact_values

NEEDS_SANDBOX_CREDENTIALS = "NEEDS_SANDBOX_CREDENTIALS"
NEEDS_RUNTIME_TOOL = "NEEDS_RUNTIME_TOOL"
BLOCKED = "BLOCKED"
READY = "READY"
SUBMITTED = "SUBMITTED"

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


def _image_size(path: Path) -> Optional[Tuple[int, int]]:
    """从文件头解析 PNG/JPEG 尺寸，避免引入图像库依赖；无法解析返回 None。"""
    try:
        head = path.read_bytes()[: 64 * 1024]
    except OSError:
        return None
    if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 24:
        width, height = struct.unpack(">II", head[16:24])
        return int(width), int(height)
    if head[:2] == b"\xff\xd8":
        offset = 2
        while offset < len(head) - 9:
            if head[offset] != 0xFF:
                offset += 1
                continue
            marker = head[offset + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height, width = struct.unpack(">HH", head[offset + 5 : offset + 9])
                return int(width), int(height)
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                offset += 2
                continue
            segment = struct.unpack(">H", head[offset + 2 : offset + 4])[0]
            offset += 2 + segment
    return None


STORE_SPECS: Dict[str, Dict[str, Any]] = {
    "wechat": {
        "label": "微信小游戏",
        "package_subdir": "wechat",
        "credential_env": ("WECHAT_APPID", "WECHAT_CI_KEY_PATH"),
        "uploader": "miniprogram-ci",
        # miniprogram-ci upload 缺少任一参数都会在服务端被拒，故前置校验
        "upload_args": lambda bundle, meta: [
            "upload", "--project-path", str(bundle), "--appid", os.environ["WECHAT_APPID"],
            "--private-key-path", os.environ["WECHAT_CI_KEY_PATH"],
            "--version", str(meta.get("version", "1.0.0")),
            "--desc", str(meta.get("short_desc", ""))[:200],
        ],
        "required_metadata": ["title", "short_desc", "long_desc", "keywords", "category",
                              "age_rating", "privacy_policy_url", "publisher", "version"],
        "required_assets": [
            {"key": "icon", "filename": "icon.png", "width": 256, "height": 256},
            {"key": "screenshot_1", "filename": "screenshot_1.png", "width": 1280, "height": 720},
            {"key": "screenshot_2", "filename": "screenshot_2.png", "width": 1280, "height": 720},
        ],
        "max_package_mb": 4.0,
    },
    "steam": {
        "label": "Steam",
        "package_subdir": "steam",
        "credential_env": ("STEAM_USER", "STEAM_APP_ID"),
        "uploader": "steamcmd",
        "upload_args": lambda bundle, meta: [
            "+login", os.environ["STEAM_USER"],
            "+run_app_build", str(Path(bundle) / "app_build.vdf"), "+quit",
        ],
        "required_metadata": ["title", "short_desc", "long_desc", "keywords", "category",
                              "age_rating", "privacy_policy_url", "publisher", "version",
                              "supported_languages", "price_tier"],
        "required_assets": [
            {"key": "library_capsule", "filename": "library_capsule.png", "width": 600, "height": 900},
            {"key": "header", "filename": "header.png", "width": 460, "height": 215},
            {"key": "screenshot_1", "filename": "screenshot_1.png", "width": 1280, "height": 720},
        ],
        "max_package_mb": None,
    },
    "itch": {
        "label": "itch.io",
        "package_subdir": "itch",
        "credential_env": ("ITCH_BUTLER_TARGET",),
        "uploader": "butler",
        "upload_args": lambda bundle, meta: [
            "push", str(bundle), f"{os.environ['ITCH_BUTLER_TARGET']}:{meta.get('channel_name', 'web')}",
            "--userversion", str(meta.get("version", "1.0.0")),
        ],
        "required_metadata": ["title", "short_desc", "long_desc", "keywords", "category",
                              "age_rating", "privacy_policy_url", "version"],
        "required_assets": [
            {"key": "cover", "filename": "cover.png", "width": 315, "height": 250},
            {"key": "screenshot_1", "filename": "screenshot_1.png", "width": 1280, "height": 720},
        ],
        "max_package_mb": None,
    },
    "pwa": {
        "label": "Web PWA / 应用商店 PWA 目录",
        "package_subdir": "pwa",
        "credential_env": ("PWA_DEPLOY_BASE_URL",),
        "uploader": None,  # 无官方 CLI 上传适配器，如实报 NEEDS_RUNTIME_TOOL
        "upload_args": None,
        "required_metadata": ["title", "short_desc", "long_desc", "keywords", "category",
                              "age_rating", "privacy_policy_url", "version", "start_url"],
        "required_assets": [
            {"key": "icon_192", "filename": "icon_192.png", "width": 192, "height": 192},
            {"key": "icon_512", "filename": "icon_512.png", "width": 512, "height": 512},
            {"key": "screenshot_1", "filename": "screenshot_1.png", "width": 1280, "height": 720},
        ],
        "max_package_mb": None,
    },
    "appstore": {
        "label": "Apple App Store (iOS)",
        "package_subdir": "appstore",
        "credential_env": ("APPLE_ID", "APPLE_APP_SPECIFIC_PASSWORD", "APPLE_TEAM_ID"),
        # 上传器在 Windows 本机不存在 -> submit 会如实返回 NEEDS_RUNTIME_TOOL；
        # 且 iOS 原生构建本身需 macOS（见 pipeline.ios_packaging），本机物理不可达。
        "uploader": "xcrun",
        "upload_args": lambda bundle, meta: [
            "xcrun", "altool", "--upload-app", "-f", str(bundle),
            "-t", "ios", "-u", os.environ["APPLE_ID"],
            "-p", os.environ["APPLE_APP_SPECIFIC_PASSWORD"],
            "--team-id", os.environ["APPLE_TEAM_ID"],
        ],
        "required_metadata": ["title", "short_desc", "long_desc", "keywords", "category",
                              "age_rating", "privacy_policy_url", "publisher", "version",
                              "supported_languages", "bundle_id"],
        "required_assets": [
            {"key": "icon_1024", "filename": "icon_1024.png", "width": 1024, "height": 1024},
            {"key": "screenshot_1", "filename": "screenshot_1.png", "width": 1280, "height": 720},
            {"key": "screenshot_2", "filename": "screenshot_2.png", "width": 1280, "height": 720},
        ],
        "max_package_mb": None,
        "host_reachability": "NEEDS_MACOS_BUILDER",  # 诚实标注：iOS 本机不可达
    },
    "googleplay": {
        "label": "Google Play (Android)",
        "package_subdir": "googleplay",
        "credential_env": ("PLAY_CONSOLE_SERVICE_ACCOUNT_JSON",),
        # 上传器在 Windows 本机不存在 -> submit 如实返回 NEEDS_RUNTIME_TOOL；
        # 且 Android 原生构建需 ANDROID_SDK_ROOT（见 pipeline.android_runtime_adapter）。
        "uploader": "gplay",
        "upload_args": lambda bundle, meta: [
            "gplay", "upload", str(bundle / "app.aab"),
            "--credentials", os.environ["PLAY_CONSOLE_SERVICE_ACCOUNT_JSON"],
            "--track", "internal", "--version", str(meta.get("version", "1.0.0")),
        ],
        "required_metadata": ["title", "short_desc", "long_desc", "keywords", "category",
                              "age_rating", "privacy_policy_url", "publisher", "version",
                              "supported_languages", "package_name"],
        "required_assets": [
            {"key": "feature_graphic", "filename": "feature_graphic.png", "width": 1024, "height": 500},
            {"key": "icon_512", "filename": "icon_512.png", "width": 512, "height": 512},
            {"key": "screenshot_1", "filename": "screenshot_1.png", "width": 1280, "height": 720},
        ],
        "max_package_mb": None,
        "host_reachability": "NEEDS_SDK",  # 诚实标注：Android 原生构建需 SDK
    },
}

__all__ = ["StoreSubmission", "STORE_SPECS", "NEEDS_SANDBOX_CREDENTIALS", "NEEDS_RUNTIME_TOOL"]


class StoreSubmission:
    """渠道上架包构建 + 提交前真实门禁。"""

    def __init__(self, dist_root: Path, submission_root: Optional[Path] = None):
        self.dist_root = Path(dist_root)
        self.submission_root = Path(submission_root or self.dist_root.parent / "submission")

    # ---------- 合规/就绪检查 ----------

    def check_readiness(self, channel: str, metadata: Dict[str, Any],
                        assets_dir: Optional[Path] = None) -> Dict[str, Any]:
        spec = STORE_SPECS.get(channel)
        if spec is None:
            return {"status": BLOCKED, "channel": channel,
                    "errors": [f"未知渠道: {channel}，可选: {', '.join(STORE_SPECS)}"], "findings": []}

        findings: List[Dict[str, str]] = []

        def add(rule: str, ok: bool, detail: str) -> None:
            findings.append({"rule": rule, "status": PASS if ok else FAIL, "detail": detail})

        for field in spec["required_metadata"]:
            value = str(metadata.get(field, "")).strip()
            add(f"元数据字段 {field}", bool(value),
                f"已填写: {value[:60]}" if value else "缺少必填商店元数据字段")

        privacy = str(metadata.get("privacy_policy_url", "")).strip()
        add("隐私政策链接", privacy.startswith("https://"),
            privacy if privacy.startswith("https://") else "隐私政策必须是 https 链接（商店审核硬性要求）")

        add("年龄分级问卷", str(metadata.get("age_rating", "")).strip() != "",
            f"已选择分级: {metadata.get('age_rating')}" if metadata.get("age_rating") else "未填写年龄分级（IARC/版号问卷）")

        sdk = metadata.get("third_party_sdks") or []
        add("第三方 SDK 声明", isinstance(sdk, list),
            f"已声明 {len(sdk)} 个 SDK: {', '.join(map(str, sdk)) or '无（纯自研无三方 SDK）'}"
            if isinstance(sdk, list) else "third_party_sdks 必须是列表，用于声明支付/广告/统计 SDK")

        package_dir = self.dist_root / spec["package_subdir"]
        add("渠道包已构建", package_dir.is_dir(),
            str(package_dir) if package_dir.is_dir() else f"未找到渠道包目录: {package_dir}")

        if package_dir.is_dir():
            size_mb = self._dir_size_mb(package_dir)
            limit = spec.get("max_package_mb")
            if limit is None:
                add("包体阈值", True, f"该渠道无硬性首包阈值，实测 {size_mb:.2f}MB")
            else:
                add(f"首包体积 ≤ {limit}MB", size_mb <= limit,
                    f"实测 {size_mb:.2f}MB / 上限 {limit}MB")

        asset_root = Path(assets_dir) if assets_dir else self.dist_root.parent / "store_assets"
        for asset in spec["required_assets"]:
            self._check_asset(asset_root, asset, add)

        missing = [f for f in findings if f["status"] == FAIL]
        return {
            "status": READY if not missing else BLOCKED,
            "channel": channel,
            "label": spec["label"],
            "total": len(findings),
            "passed": len(findings) - len(missing),
            "errors": [f"{f['rule']}: {f['detail']}" for f in missing],
            "findings": findings,
        }

    @staticmethod
    def _check_asset(asset_root: Path, asset: Dict[str, Any], add) -> None:
        path = asset_root / asset["filename"]
        if not path.is_file():
            add(f"素材 {asset['key']}", False, f"缺少素材文件: {path}")
            return
        size = _image_size(path)
        if size is None:
            add(f"素材 {asset['key']}", False, f"无法解析图片尺寸（需 PNG/JPEG）: {path}")
            return
        width, height = size
        ok = width >= asset["width"] and height >= asset["height"]
        add(f"素材 {asset['key']}", ok,
            f"{path.name} 实测 {width}x{height}，要求 ≥{asset['width']}x{asset['height']}"
            if ok else f"{path.name} 实测 {width}x{height}，低于要求 {asset['width']}x{asset['height']}")

    @staticmethod
    def _dir_size_mb(path: Path) -> float:
        total = sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())
        return total / (1024 * 1024)

    # ---------- 上架包构建 ----------

    def build_bundle(self, channel: str, metadata: Dict[str, Any],
                     assets_dir: Optional[Path] = None) -> Dict[str, Any]:
        readiness = self.check_readiness(channel, metadata, assets_dir)
        bundle = self.submission_root / channel
        if bundle.exists():
            shutil.rmtree(bundle)
        bundle.mkdir(parents=True, exist_ok=True)

        spec = STORE_SPECS[channel]
        package_dir = self.dist_root / spec["package_subdir"]
        if package_dir.is_dir():
            shutil.copytree(package_dir, bundle / "package", dirs_exist_ok=True)

        asset_root = Path(assets_dir) if assets_dir else self.dist_root.parent / "store_assets"
        assets_bundle = bundle / "assets"
        assets_bundle.mkdir(exist_ok=True)
        copied = []
        for asset in spec["required_assets"]:
            src = asset_root / asset["filename"]
            if src.is_file():
                shutil.copy2(src, assets_bundle / asset["filename"])
                copied.append(asset["filename"])

        # 落盘前统一脱敏：元数据字段由人工填写，存在把密钥误填进来的可能；
        # 报告会随上架包一起分发，因此绝不把原始值写进磁盘。
        safe = lambda text: redact(text)
        (bundle / "store_metadata.json").write_text(
            safe(json.dumps({"channel": channel, "label": spec["label"], **metadata},
                            ensure_ascii=False, indent=2)), encoding="utf-8")
        report = dict(readiness, bundle_path=str(bundle), copied_assets=copied)
        (bundle / "readiness_report.json").write_text(
            safe(json.dumps(report, ensure_ascii=False, indent=2)), encoding="utf-8")

        return report

    # ---------- 提交（真实执行，缺什么报什么） ----------

    def submit(self, channel: str, metadata: Dict[str, Any], dry_run: bool = True,
               assets_dir: Optional[Path] = None) -> Dict[str, Any]:
        report = self.build_bundle(channel, metadata, assets_dir)
        if report["status"] != READY:
            return {"status": BLOCKED, "channel": channel, "reason": "readiness_failed",
                    "errors": report["errors"], "bundle_path": report["bundle_path"]}

        spec = STORE_SPECS[channel]
        missing_credentials = [k for k in spec["credential_env"] if not (os.environ.get(k) or "").strip()]
        if missing_credentials:
            return {"status": NEEDS_SANDBOX_CREDENTIALS, "channel": channel,
                    "errors": [f"缺少渠道凭据环境变量: {', '.join(missing_credentials)}"],
                    "bundle_path": report["bundle_path"],
                    "note": "上架包已就绪，但未配置渠道凭据，因此没有提交；不会把打包成功当作已上架"}

        uploader = spec["uploader"]
        if not uploader:
            return {"status": NEEDS_RUNTIME_TOOL, "channel": channel,
                    "errors": [f"{spec['label']} 无官方 CLI 上传适配器，需人工在商店后台提交"],
                    "bundle_path": report["bundle_path"]}

        executable = shutil.which(uploader)
        if executable is None:
            return {"status": NEEDS_RUNTIME_TOOL, "channel": channel,
                    "errors": [f"未找到官方上传器可执行文件: {uploader}"],
                    "bundle_path": report["bundle_path"]}

        command = [executable] + list(spec["upload_args"](report["bundle_path"], metadata))

        # 命令里带有真实凭据（appid / 密钥路径 / 登录名），上传器输出也可能回显 token。
        # 这些都会进返回结构、进 CLI 打印、进落盘报告，因此统一打码后再外传。
        secret_values = [(os.environ.get(k) or "") for k in spec["credential_env"]]

        def _safe(text: str) -> str:
            return redact_values(redact(text), secret_values)

        safe_command = [_safe(arg) for arg in command]

        if dry_run:
            return {"status": READY, "channel": channel, "command": safe_command,
                    "bundle_path": report["bundle_path"],
                    "note": "dry-run：命令已组装但未执行（凭据已打码）"}

        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        return {
            "status": SUBMITTED if completed.returncode == 0 else FAIL,
            "channel": channel,
            "command": safe_command,
            "bundle_path": report["bundle_path"],
            "returncode": completed.returncode,
            "stdout_tail": _safe((completed.stdout or "")[-2000:]),
            "stderr_tail": _safe((completed.stderr or "")[-2000:]),
        }
