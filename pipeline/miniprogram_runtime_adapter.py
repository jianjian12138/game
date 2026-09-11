#!/usr/bin/env python3
"""pipeline/miniprogram_runtime_adapter.py: 微信小游戏 / 小程序 真实运行时适配器

诚实边界（红线 13.2 / Tier 2）：
    微信小游戏的真实运行验证需要「微信开发者工具 CLI」或「真机 + miniprogram-ci」。
    本机（Windows）未安装上述工具时，所有运行期场景一律返回 NEEDS_RUNTIME_TOOL；
    「游戏代码存在 / 静态结构合法」只说明工程被生成过，绝不能等同于「游戏真的在微信运行时里跑起来了」。

判定方式（工具就绪后才会执行，当前本机不具备）：
    用微信开发者工具 CLI 以 --auto 无头打开工程，或 miniprogram-ci preview/upload，
    从运行日志 / 真机回传采集：画面帧计数、状态迁移、触摸输入反射。
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent

from core.runtime_adapter import RuntimeAdapter, RuntimeStatus
from core.host_contract import MiniProgramContract

GAME_JSON = "game.json"
PROJECT_CONFIG = "project.config.json"
DEFAULT_SCENARIOS = ["boot", "core_loop", "touch_input"]

# 微信开发者工具 CLI 常见位置（Windows / macOS）；命中其一视为工具就绪
_COMMON_DEVTOOLS = [
    os.environ.get("WECHAT_DEVTOOLS_PATH", ""),
    r"C:\Program Files (x86)\Tencent\微信web开发者工具\cli.bat",
    r"C:\Program Files\Tencent\微信web开发者工具\cli.bat",
    "/Applications/wechatwebdevtools.app/Contents/MacOS/cli",
    os.path.expandvars(r"%LOCALAPPDATA%\微信web开发者工具\cli.bat"),
]


class MiniProgramRuntimeAdapter(RuntimeAdapter):
    name = "miniprogram_runtime_adapter"
    version = "1.0.0"

    def __init__(self, devtools_cli: Optional[str] = None, timeout_s: int = 120):
        self.devtools_cli = devtools_cli
        self.timeout_s = timeout_s
        self.contract = MiniProgramContract()

    # ---------------------------------------------------------------- 公开接口

    def preflight(self, target: str = "wechat", environment: str = "sandbox") -> Dict[str, Any]:
        cli = self._resolve_cli()
        if not cli:
            return {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "target": target,
                "can_launch": False,
                "devtools_cli": "",
                "reason": "未检测到微信开发者工具 CLI（cli）或 miniprogram-ci；无法做真实验证",
                "hint": "安装微信开发者工具并在 WECHAT_DEVTOOLS_PATH 指定 cli 路径，或 npm i -g miniprogram-ci",
            }
        return {
            "status": RuntimeStatus.PASS,
            "target": target,
            "can_launch": True,
            "devtools_cli": cli,
            "reason": None,
        }

    def launch(self, artifact_path: Path, environment: str = "sandbox") -> Dict[str, Any]:
        path = Path(artifact_path)
        project_dir = self._resolve_project_dir(path)
        cli = self._resolve_cli()
        session: Dict[str, Any] = {
            "session_id": f"wx_{abs(hash(str(project_dir or path))) % 10**10}",
            "target": "wechat",
            "project_dir": str(project_dir) if project_dir else None,
            "devtools_cli": cli,
            "scenarios": {},
            "observations": {},
            "metrics": {"collected": False},
            "errors": [],
        }
        if project_dir is None:
            session["status"] = RuntimeStatus.BLOCKED_BY_STATIC
            session["errors"].append({"code": "WECHAT_PROJECT_MISSING",
                                       "message": f"未找到含 {GAME_JSON} 的微信小游戏工程: {path}"})
        elif not cli:
            session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
            session["errors"].append({"code": "WECHAT_RUNTIME_MISSING", "message": "未检测到微信开发者工具 CLI"})
        else:
            session["status"] = RuntimeStatus.PASS
        return session

    def run_scenarios(self, session: Dict[str, Any], scenarios: Optional[List[str]] = None) -> Dict[str, Any]:
        target_scenarios = list(scenarios or DEFAULT_SCENARIOS)
        session["scenarios"] = session.get("scenarios") or {}

        if session.get("status") == RuntimeStatus.BLOCKED_BY_STATIC:
            reason = "工程缺少 game.json，静态校验未通过"
        elif not session.get("devtools_cli"):
            reason = "未检测到微信开发者工具 CLI / miniprogram-ci"
        else:
            reason = None

        # 诚实降级：缺真实验证工具时，绝不编造 PASS。
        if reason:
            for sc in target_scenarios:
                session["scenarios"][sc] = {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL, "reason": reason}
            session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
            return {"status": session["status"], "scenarios": session["scenarios"], "observations": session["observations"]}

        # 工具就绪时的真实路径（本机不执行，仅描述契约消费方式）：
        #   用 devtools_cli 无头打开工程 -> 采集运行日志 -> MiniProgramContract.parse_evidence 归一化。
        # 该分支需要真实微信运行时，故用 NEEDS_RUNTIME_TOOL 占位，待工具就绪后填充。
        for sc in target_scenarios:
            session["scenarios"][sc] = {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "reason": "微信运行时真验证需开发者工具CLI/真机，本机未启用（NEEDS_RUNTIME_TOOL 占位，非伪 PASS）",
            }
        session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
        return {"status": session["status"], "scenarios": session["scenarios"], "observations": session["observations"]}

    def collect_evidence(self, session: Dict[str, Any]) -> Dict[str, Any]:
        metrics = session.get("metrics") or {"collected": False}
        return {
            "status": session.get("status", RuntimeStatus.NEEDS_RUNTIME_TOOL),
            "scenarios": session.get("scenarios", {}),
            "metrics": metrics,
            "runtime_facts": {
                "adapter": self.name,
                "adapter_version": self.version,
                "target": "wechat",
                "project_dir": session.get("project_dir"),
                "devtools_cli": session.get("devtools_cli"),
                "observations": session.get("observations", {}),
            },
            "errors": session.get("errors", []),
        }

    def close(self, session: Dict[str, Any]) -> Dict[str, Any]:
        session["alive"] = False
        return {"closed": True, "session_id": session.get("session_id")}

    # ---------------------------------------------------------------- 静态结构自检（非运行期证据，仅文档）
    # 这些方法只做工程结构核对，返回的不是 RuntimeStatus.PASS，调用方不得据此宣称已验证。

    @staticmethod
    def validate_project_structure(project_dir: Path) -> Dict[str, Any]:
        """静态核对微信小游戏工程结构（game.json / project.config.json / wx API 使用）。

        重要：这只是「工程能被打包」的自检，不是「游戏真的跑起来」的证明。
        返回中不含 RuntimeStatus.PASS；运行期 PASS 只能由 run_scenarios 在真机/CLI 下给出。
        """
        project_dir = Path(project_dir)
        findings: List[Dict[str, Any]] = []
        game_json = project_dir / GAME_JSON
        findings.append({"rule": "game.json 存在", "ok": game_json.is_file()})
        if game_json.is_file():
            try:
                cfg = json.loads(game_json.read_text(encoding="utf-8"))
                findings.append({"rule": "game.json 可解析", "ok": True, "deviceOrientation": cfg.get("deviceOrientation")})
            except ValueError:
                findings.append({"rule": "game.json 可解析", "ok": False})
        findings.append({"rule": "project.config.json 存在", "ok": (project_dir / PROJECT_CONFIG).is_file()})

        js_files = list(project_dir.rglob("*.js"))
        wx_usage: Dict[str, bool] = {}
        if js_files:
            blob = "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in js_files)
            wx_usage = MiniProgramContract.scan_wx_usage(blob)
        findings.append({"rule": "使用了微信运行时 API (wx.*)", "ok": any(wx_usage.values()), "detail": wx_usage})
        # 该检查通过只代表「结构合法可打包」，不进入运行时裁决
        return {"static_valid": all(f["ok"] for f in findings), "findings": findings}

    # ---------------------------------------------------------------- 内部实现

    def _resolve_cli(self) -> Optional[str]:
        # None = 自动探测；空字符串 = 调用方明确要求禁用（便于离线诚实测试）。
        if self.devtools_cli is not None:
            return self.devtools_cli or None
        for p in _COMMON_DEVTOOLS:
            if p and shutil.which(p):
                return p
            if p and Path(p).exists():
                return p
        # miniprogram-ci（npm 全局脚本）
        ci = shutil.which("miniprogram-ci") or shutil.which("miniprogram-ci.cmd")
        if ci:
            return ci
        return None

    @staticmethod
    def _resolve_project_dir(path: Path) -> Optional[Path]:
        candidates = [path]
        if path.is_file():
            candidates = [path.parent, path]
        else:
            candidates = [path, path / "wechat"]
        for candidate in candidates:
            if candidate.is_dir() and (candidate / GAME_JSON).is_file():
                return candidate
        return None


__all__ = ["MiniProgramRuntimeAdapter", "GAME_JSON"]
