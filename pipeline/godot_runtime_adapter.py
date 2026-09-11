#!/usr/bin/env python3
"""pipeline/godot_runtime_adapter.py: Godot 4.x 真实运行时适配器

诚实边界（红线 13.2）：
    未检测到 Godot 可执行文件（tools/godot/godot.exe 或 PATH 中的 godot）时，
    所有场景一律返回 NEEDS_RUNTIME_TOOL；「project.godot 文件存在」只说明项目被生成过，
    绝不能等同于「游戏真的跑起来了」。

判定方式：
    以 --headless 启动项目，注入一个 extends SceneTree 的探针脚本，
    让引擎真实推进主循环若干帧后打印 GAME_AGENT_CONTRACT 行，再据此断言 boot/core_loop。
"""
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent

from core.runtime_adapter import RuntimeAdapter, RuntimeStatus
from core.environment_inspector import EnvironmentInspector
from core.host_contract import GodotContract

GODOT_PROJECT_FILE = "project.godot"
PROBE_FILENAME = "game_agent_runtime_probe.gd"
CONTRACT_PREFIX = "GAME_AGENT_CONTRACT"
# 探针推进的帧数：足以证明主循环在跑，又不至于让无头运行拖太久
PROBE_FRAMES = 120
# 认定主循环存活所要求的最小帧数
MIN_FRAMES = 30
DEFAULT_SCENARIOS = ["boot", "core_loop"]
DEFAULT_TIMEOUT_S = 60

# 探针脚本统一由 GodotContract 生成（单一真理源，避免与 host_contract 两份漂移）
PROBE_SCRIPT = GodotContract.godot_probe_script(PROBE_FRAMES)

# Godot 把这些输出到 stderr，出现即视为运行期错误
_ERROR_MARKERS = ("SCRIPT ERROR", "Parse Error", "ERROR:", "Cannot open file", "modules/gdscript")


class GodotRuntimeAdapter(RuntimeAdapter):
    name = "godot_runtime_adapter"
    version = "1.0.0"

    def __init__(self, godot_executable: Optional[str] = None, timeout_s: int = DEFAULT_TIMEOUT_S):
        self.godot_executable = godot_executable
        self.timeout_s = timeout_s

    # ---------------------------------------------------------------- 公开接口

    def preflight(self, target: str = "godot", environment: str = "sandbox") -> Dict[str, Any]:
        exe = self._resolve_executable()
        if not exe:
            return {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "target": target,
                "can_launch": False,
                "godot_executable": "",
                "reason": "未检测到 Godot 4.x 可执行文件；请放置 tools/godot/godot.exe 或加入 PATH",
            }
        version = ""
        try:
            res = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
            version = (res.stdout or "").strip().splitlines()[0] if res.stdout else ""
        except (OSError, subprocess.SubprocessError):
            pass
        return {
            "status": RuntimeStatus.PASS,
            "target": target,
            "can_launch": True,
            "godot_executable": exe,
            "godot_version": version,
            "reason": None,
        }

    def launch(self, artifact_path: Path, environment: str = "sandbox") -> Dict[str, Any]:
        path = Path(artifact_path)
        project_dir = self._resolve_project_dir(path)
        exe = self._resolve_executable()
        session: Dict[str, Any] = {
            "session_id": f"godot_{abs(hash(str(project_dir or path))) % 10**10}",
            "target": "godot",
            "project_dir": str(project_dir) if project_dir else None,
            "godot_exe": exe,
            "scenarios": {},
            "observations": {},
            "metrics": {"collected": False},
            "errors": [],
        }
        if project_dir is None:
            session["status"] = RuntimeStatus.BLOCKED_BY_STATIC
            session["errors"].append({"code": "GODOT_PROJECT_MISSING", "message": f"未找到 {GODOT_PROJECT_FILE}: {path}"})
        elif not exe:
            session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
            session["errors"].append({"code": "GODOT_RUNTIME_MISSING", "message": "未检测到 Godot 可执行文件"})
        else:
            session["status"] = RuntimeStatus.PASS
        return session

    def run_scenarios(self, session: Dict[str, Any], scenarios: Optional[List[str]] = None) -> Dict[str, Any]:
        target_scenarios = list(scenarios or DEFAULT_SCENARIOS)
        session["scenarios"] = session.get("scenarios") or {}

        if session.get("status") == RuntimeStatus.BLOCKED_BY_STATIC:
            reason = "项目缺少 project.godot，静态校验未通过"
        elif not session.get("godot_exe"):
            reason = "未检测到 Godot 运行时"
        else:
            reason = None

        if reason:
            for sc in target_scenarios:
                session["scenarios"][sc] = {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL, "reason": reason}
            session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
            return {"status": session["status"], "scenarios": session["scenarios"], "observations": session["observations"]}

        project_dir = Path(session["project_dir"])
        probe_path = project_dir / PROBE_FILENAME
        cmd = [session["godot_exe"], "--headless", "--path", str(project_dir), "--script", f"res://{PROBE_FILENAME}"]
        try:
            probe_path.write_text(PROBE_SCRIPT, encoding="utf-8")
            session["probe_path"] = str(probe_path)
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_s)
        except subprocess.TimeoutExpired:
            session["status"] = RuntimeStatus.TIMEOUT
            session["errors"].append({"code": "GODOT_TIMEOUT", "message": f"无头运行超过 {self.timeout_s}s"})
            for sc in target_scenarios:
                session["scenarios"][sc] = {"status": RuntimeStatus.TIMEOUT, "reason": "无头运行超时"}
            return {"status": session["status"], "scenarios": session["scenarios"], "observations": session["observations"]}
        except (OSError, ValueError) as exc:
            session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
            session["errors"].append({"code": "GODOT_LAUNCH_FAILED", "message": str(exc)})
            for sc in target_scenarios:
                session["scenarios"][sc] = {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL, "reason": str(exc)}
            return {"status": session["status"], "scenarios": session["scenarios"], "observations": session["observations"]}

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        errors = [line.strip() for line in stderr.splitlines() if any(m in line for m in _ERROR_MARKERS)]
        # 证据解析统一走 GodotContract（host_contract 单一真理源）
        evidence = GodotContract().parse_evidence(stdout)

        session["observations"].update({
            "exit_code": completed.returncode,
            "stdout_tail": stdout[-2000:],
            "stderr_tail": stderr[-2000:],
            "contract": evidence,
            "command": cmd,
        })
        session["metrics"] = {
            "collected": True,
            "godot_error_count": len(errors),
            "godot_errors": errors[:10],
            "frames": evidence.get("frames") if evidence.get("available") else None,
        }

        boot_ok = completed.returncode == 0 and not any(
            m in stderr for m in ("Parse Error", "Cannot open file")
        )
        loop_ok = bool(evidence.get("available")) and int(evidence.get("frames", 0)) >= MIN_FRAMES

        for sc in target_scenarios:
            if sc == "boot":
                session["scenarios"][sc] = (
                    {"status": RuntimeStatus.PASS, "driver": "godot_headless", "exit_code": completed.returncode}
                    if boot_ok else
                    {"status": RuntimeStatus.FAIL, "driver": "godot_headless", "exit_code": completed.returncode,
                     "errors": errors[:5]}
                )
            elif sc == "core_loop":
                session["scenarios"][sc] = (
                    {"status": RuntimeStatus.PASS, "driver": "godot_headless", "frames": evidence.get("frames")}
                    if loop_ok else
                    {"status": RuntimeStatus.FAIL, "driver": "godot_headless", "frames": None,
                     "reason": "探针未上报主循环帧数或帧数不足"}
                )
            else:
                session["scenarios"][sc] = {
                    "status": "NEEDS_GAME_CONTRACT",
                    "reason": f"Godot 适配器暂不支持场景 {sc}；需项目侧实现对应状态上报",
                }

        failed = [k for k, v in session["scenarios"].items() if v.get("status") == RuntimeStatus.FAIL]
        if failed or errors:
            session["status"] = RuntimeStatus.FAIL
        else:
            session["status"] = RuntimeStatus.PASS
        return {"status": session["status"], "scenarios": session["scenarios"],
                "observations": session["observations"], "metrics": session["metrics"]}

    def collect_evidence(self, session: Dict[str, Any]) -> Dict[str, Any]:
        metrics = session.get("metrics") or {"collected": False}
        return {
            "status": session.get("status", RuntimeStatus.NEEDS_RUNTIME_TOOL),
            "scenarios": session.get("scenarios", {}),
            "metrics": metrics,
            "runtime_facts": {
                "adapter": self.name,
                "adapter_version": self.version,
                "target": "godot",
                "project_dir": session.get("project_dir"),
                "godot_exe": session.get("godot_exe"),
                "observations": session.get("observations", {}),
            },
            "errors": session.get("errors", []),
        }

    def close(self, session: Dict[str, Any]) -> Dict[str, Any]:
        probe = session.get("probe_path")
        if probe and Path(probe).exists():
            try:
                Path(probe).unlink()
            except OSError:
                pass
        session["alive"] = False
        return {"closed": True, "session_id": session.get("session_id")}

    # ---------------------------------------------------------------- 内部实现

    def _resolve_executable(self) -> Optional[str]:
        # None = 自动探测；空字符串 = 调用方明确要求禁用引擎。
        # 这一区分保证离线 honesty 测试和真实本机探测互不串台。
        if self.godot_executable is not None:
            return self.godot_executable or None
        manifest = EnvironmentInspector.get_toolchain_manifest()
        return manifest.get("tools", {}).get("godot", {}).get("executable") or None

    @staticmethod
    def _resolve_project_dir(path: Path) -> Optional[Path]:
        """接受 Godot 项目目录、run 目录或任意项目内路径，返回含 project.godot 的目录。"""
        candidates = [path]
        if path.is_file():
            candidates = [path.parent, path.parent / "godot_project", path]
        else:
            candidates = [path, path / "godot_project"]
        for candidate in candidates:
            if candidate.is_dir() and (candidate / GODOT_PROJECT_FILE).is_file():
                return candidate
        return None


__all__ = ["GodotRuntimeAdapter", "CONTRACT_PREFIX", "PROBE_FRAMES"]
