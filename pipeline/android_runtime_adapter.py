#!/usr/bin/env python3
"""pipeline/android_runtime_adapter.py: Android 原生运行时适配器（Godot 导出 APK/AAB）

诚实边界（红线 13.2 / Tier 2）：
    Android 原生构建与真机验证需要 ANDROID_SDK_ROOT + adb + debug keystore +
    Godot 导出模板。本机（Windows）未安装 Android SDK/adb，所有运行期与打包场景
    一律返回 NEEDS_SDK；「project.godot 存在」或「导出预设写了 Android」只说明工程被生成过，
    绝不能等同于「游戏真的在 Android 上跑起来了」。

判定方式（工具就绪后才会执行，当前本机不具备）：
    用 adb 连接真机/模拟器 -> 安装并启动 APK -> logcat 采集 GAME_AGENT_FRAME/STATE/INPUT
    -> NativeContract.parse_evidence 归一化。本机不执行，仅描述契约消费方式。
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent

from core.runtime_adapter import RuntimeAdapter, RuntimeStatus
from core.environment_inspector import EnvironmentInspector
from core.host_contract import NativeContract

GODOT_PROJECT_FILE = "project.godot"
EXPORT_PRESETS = "export_presets.cfg"
ANDROID_PRESET_NAME = "Android"
DEFAULT_SCENARIOS = ["boot", "core_loop", "touch_input"]

# Android 导出模板还必须存在（与 Windows 出包同样的模板缺口）
_TEMPLATE_MISS_MARKERS = ("未找到导出模板", "export template", "Cannot export project", "export_templates")


class AndroidRuntimeAdapter(RuntimeAdapter):
    name = "android_runtime_adapter"
    version = "1.0.0"

    def __init__(
        self,
        godot_executable: Optional[str] = None,
        sdk_root: Optional[str] = None,
        adb: Optional[str] = None,
        keystore: Optional[str] = None,
        timeout_s: int = 300,
    ):
        self.godot_executable = godot_executable
        self.sdk_root = sdk_root
        self.adb = adb
        self.keystore = keystore
        self.timeout_s = timeout_s
        self.contract = NativeContract()

    # ---------------------------------------------------------------- 公开接口

    def preflight(self, target: str = "android", environment: str = "sandbox") -> Dict[str, Any]:
        sdk = self._resolve_sdk()
        adb = self._resolve_adb()
        keystore = self._resolve_keystore()
        missing = []
        if not sdk:
            missing.append("ANDROID_SDK_ROOT")
        if not adb:
            missing.append("adb")
        if not keystore:
            missing.append("debug keystore")
        if missing:
            return {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "target": target,
                "can_launch": False,
                "reason": f"缺少 Android 构建/验证工具链: {', '.join(missing)}",
                "hint": "安装 Android SDK Command-line Tools + 平台/构建工具，配置 ANDROID_SDK_ROOT，生成 debug keystore",
            }
        return {
            "status": RuntimeStatus.PASS,
            "target": target,
            "can_launch": True,
            "android_sdk_root": sdk,
            "adb": adb,
            "reason": None,
        }

    def launch(self, artifact_path: Path, environment: str = "sandbox") -> Dict[str, Any]:
        path = Path(artifact_path)
        project_dir = self._resolve_project_dir(path)
        sdk = self._resolve_sdk()
        adb = self._resolve_adb()
        keystore = self._resolve_keystore()
        session: Dict[str, Any] = {
            "session_id": f"android_{abs(hash(str(project_dir or path))) % 10**10}",
            "target": "android",
            "project_dir": str(project_dir) if project_dir else None,
            "android_sdk_root": sdk,
            "adb": adb,
            "scenarios": {},
            "observations": {},
            "metrics": {"collected": False},
            "errors": [],
        }
        if project_dir is None:
            session["status"] = RuntimeStatus.BLOCKED_BY_STATIC
            session["errors"].append({"code": "ANDROID_PROJECT_MISSING",
                                       "message": f"未找到含 {GODOT_PROJECT_FILE} 的 Android 工程: {path}"})
        elif not (sdk and adb and keystore):
            session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
            session["errors"].append({"code": "ANDROID_SDK_MISSING", "message": "缺少 ANDROID_SDK_ROOT / adb / keystore"})
        else:
            session["status"] = RuntimeStatus.PASS
        return session

    def run_scenarios(self, session: Dict[str, Any], scenarios: Optional[List[str]] = None) -> Dict[str, Any]:
        target_scenarios = list(scenarios or DEFAULT_SCENARIOS)
        session["scenarios"] = session.get("scenarios") or {}
        if session.get("status") == RuntimeStatus.BLOCKED_BY_STATIC:
            reason = "工程缺少 project.godot，静态校验未通过"
        elif not (session.get("android_sdk_root") and session.get("adb")):
            reason = "缺少 Android SDK / adb，无法真机验证"
        else:
            reason = None

        # 诚实降级：缺 SDK/adb -> 无法证明「游戏真的在 Android 上跑起来」-> NEEDS_RUNTIME_TOOL。
        if reason:
            for sc in target_scenarios:
                session["scenarios"][sc] = {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL, "reason": reason}
            session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
            return {"status": session["status"], "scenarios": session["scenarios"], "observations": session["observations"]}

        for sc in target_scenarios:
            session["scenarios"][sc] = {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "reason": "Android 真验证需 SDK + adb + 真机/模拟器，本机未启用（NEEDS_RUNTIME_TOOL 占位，非伪 PASS）",
            }
        session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
        return {"status": session["status"], "scenarios": session["scenarios"], "observations": session["observations"]}

    def collect_evidence(self, session: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": session.get("status", RuntimeStatus.NEEDS_RUNTIME_TOOL),
            "scenarios": session.get("scenarios", {}),
            "metrics": session.get("metrics") or {"collected": False},
            "runtime_facts": {
                "adapter": self.name,
                "adapter_version": self.version,
                "target": "android",
                "project_dir": session.get("project_dir"),
                "android_sdk_root": session.get("android_sdk_root"),
                "adb": session.get("adb"),
            },
            "errors": session.get("errors", []),
        }

    def close(self, session: Dict[str, Any]) -> Dict[str, Any]:
        session["alive"] = False
        return {"closed": True, "session_id": session.get("session_id")}

    # ---------------------------------------------------------------- Android 导出封装（诚实边界）

    def export_android(
        self,
        project_dir: Path,
        export_path: Optional[Path] = None,
        preset_name: str = ANDROID_PRESET_NAME,
    ) -> Dict[str, Any]:
        """把 Godot 工程导出为 Android 包（APK/AAB）。

        诚实规则：
            - 项目缺 project.godot -> BLOCKED_BY_STATIC
            - 未检测到 Godot -> NEEDS_RUNTIME_TOOL
            - 未检测到 Android SDK/adb/keystore -> NEEDS_SDK（包装成 NEEDS_RUNTIME_TOOL 语义）
            - 导出模板缺失（真实 --export-release 报错） -> NEEDS_RUNTIME_TOOL（附模板目录）
            - 仅当 returncode==0 且产物存在 -> PASS（列出 apk/aab）
        """
        project_dir = Path(project_dir)
        if not (project_dir / GODOT_PROJECT_FILE).is_file():
            return {"status": RuntimeStatus.BLOCKED_BY_STATIC,
                    "reason": f"项目缺少 project.godot: {project_dir}"}

        exe = self._resolve_executable()
        if not exe:
            return {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                    "reason": "未检测到 Godot 可执行文件，无法导出 Android 包"}

        sdk = self._resolve_sdk()
        adb = self._resolve_adb()
        keystore = self._resolve_keystore()
        if not (sdk and adb and keystore):
            return {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                    "reason": "缺少 Android 构建链 (ANDROID_SDK_ROOT / adb / keystore)，无法导出 Android 包",
                    "hint": "安装 Android SDK Command-line Tools，配置 ANDROID_SDK_ROOT，生成 debug.keystore"}

        if export_path is None:
            export_path = project_dir / "dist" / f"{project_dir.name}.apk"
        export_path = Path(export_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [exe, "--headless", "--path", str(project_dir), "--export-release", preset_name, str(export_path)]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_s)
        except subprocess.TimeoutExpired:
            return {"status": RuntimeStatus.TIMEOUT, "reason": f"导出超过 {self.timeout_s}s", "command": cmd}

        stderr = completed.stderr or ""
        if any(marker in stderr for marker in _TEMPLATE_MISS_MARKERS):
            version = self._godot_version(exe)
            return {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "reason": "Godot 导出模板缺失，无法产出 Android 包",
                "command": cmd,
                "stderr_tail": stderr[-1500:],
            }
        if completed.returncode != 0 or not export_path.exists():
            return {"status": RuntimeStatus.FAIL, "reason": "导出命令返回非零或产物缺失",
                    "returncode": completed.returncode, "command": cmd,
                    "stderr_tail": stderr[-1500:], "stdout_tail": (completed.stdout or "")[-1500:]}

        return {
            "status": RuntimeStatus.PASS,
            "export_path": str(export_path),
            "artifacts": [str(export_path)],
            "godot_version": version if (version := self._godot_version(exe)) else None,
            "command": cmd,
        }

    # ---------------------------------------------------------------- 内部实现

    def _resolve_executable(self) -> Optional[str]:
        if self.godot_executable is not None:
            return self.godot_executable or None
        manifest = EnvironmentInspector.get_toolchain_manifest()
        return manifest.get("tools", {}).get("godot", {}).get("executable") or None

    def _resolve_sdk(self) -> Optional[str]:
        if self.sdk_root is not None:
            return self.sdk_root or None
        env = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
        if env and Path(env).is_dir():
            return env
        return None

    def _resolve_adb(self) -> Optional[str]:
        if self.adb is not None:
            return self.adb or None
        found = shutil.which("adb")
        if found:
            return found
        sdk = self._resolve_sdk()
        if sdk:
            cand = Path(sdk) / "platform-tools" / "adb"
            cand_win = Path(sdk) / "platform-tools" / "adb.exe"
            for c in (cand, cand_win):
                if c.exists():
                    return str(c)
        return None

    def _resolve_keystore(self) -> Optional[str]:
        if self.keystore is not None:
            return self.keystore or None
        # 常见 debug keystore 位置
        env = os.environ.get("ANDROID_DEBUG_KEYSTORE")
        if env and Path(env).is_file():
            return env
        home = Path.home()
        for cand in (home / ".android" / "debug.keystore", Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "debug.keystore"):
            if cand.is_file():
                return str(cand)
        return None

    @staticmethod
    def _resolve_project_dir(path: Path) -> Optional[Path]:
        candidates = [path]
        if path.is_file():
            candidates = [path.parent, path]
        else:
            candidates = [path, path / "godot_project"]
        for candidate in candidates:
            if candidate.is_dir() and (candidate / GODOT_PROJECT_FILE).is_file():
                return candidate
        return None

    @staticmethod
    def _godot_version(exe: str) -> str:
        try:
            res = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
            return (res.stdout or "").strip().splitlines()[0] if res.stdout else ""
        except (OSError, subprocess.SubprocessError):
            return ""


__all__ = ["AndroidRuntimeAdapter", "ANDROID_PRESET_NAME"]
