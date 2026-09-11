#!/usr/bin/env python3
"""
godot_exporter.py: Godot 4 工业级跨端游戏工程导出调度器 (Godot 4 Project Exporter)

两个职责：
1. export_godot_project —— 调度 GodotFullEngine 装配核心，产出 Godot 4 工程源码
   （CharacterBody3D、胶囊体、SpringArm 相机、move_and_slide 物理与封闭刚性空气墙）。
2. export_windows —— 把已有 Godot 工程导出为独立可分发桌面包（.exe + .pck）。
   诚实边界（红线 13.2）：缺导出模板时如实返回 NEEDS_RUNTIME_TOOL，绝不伪称可出包。

本机现状（2026-09-11）：Godot 4.7.2 编辑器已装于 D:\\Godot\\，但**未安装导出模板**，
且运行环境无外网下载 tpz。因此本地独立 .exe 出包如实标记为 NEEDS_RUNTIME_TOOL；
运行时验证（boot/core_loop）走 GodotRuntimeAdapter，不在此模块。
"""
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from core.runtime_adapter import RuntimeStatus
from core.environment_inspector import EnvironmentInspector
from pipeline.godot_full_engine import GodotFullEngine

EXPORT_TIMEOUT_S = 300
# Godot 在模板缺失时报出的中英文关键串
_TEMPLATE_MISS_MARKERS = ("未找到导出模板", "export template", "Cannot export project", "export_templates")
_DEFAULT_PRESET = "Windows Desktop"


class GodotExporter:
    def __init__(self, godot_executable: Optional[str] = None, timeout_s: int = EXPORT_TIMEOUT_S):
        self.godot_executable = godot_executable
        self.timeout_s = timeout_s

    @staticmethod
    def export_godot_project(title: str, genre: str, output_dir: Path) -> Path:
        godot_dir = output_dir / "godot_project"
        # 调用全套工业工程装配中枢
        GodotFullEngine.assemble_full_godot_project(title=title, genre=genre, target_dir=godot_dir)
        
        # 联动 Asset3DBridge: 导出与注入原生 glTF 3D 资产
        try:
            from pipeline.asset_3d_bridge import Asset3DBridge
            models_dir = godot_dir / "assets" / "models"
            models_dir.mkdir(parents=True, exist_ok=True)
            Asset3DBridge.build_procedural_asset("turret", output_dir=models_dir)
            Asset3DBridge.build_procedural_asset("mech", output_dir=models_dir)
        except Exception as e:
            print(f"[GodotExporter] 3D 资产注入提示: {e}")

        return godot_dir

    # ---------------------------------------------------------------- 独立桌面包导出（诚实边界）

    def export_windows(
        self,
        project_dir: Path,
        preset_name: str = _DEFAULT_PRESET,
        export_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """把 Godot 工程导出为 Windows 独立包。返回含 status 的证据字典。

        诚实规则：
            - 项目缺 project.godot → BLOCKED_BY_STATIC
            - 未检测到 Godot 可执行文件 → NEEDS_RUNTIME_TOOL
            - 导出模板缺失（真实 --export-release 报错） → NEEDS_RUNTIME_TOOL（附模板目录与下载提示）
            - 仅当 returncode==0 且产物文件确实存在 → PASS（列出 .exe/.pck）
        """
        project_dir = Path(project_dir)
        if not (project_dir / "project.godot").is_file():
            return {
                "status": RuntimeStatus.BLOCKED_BY_STATIC,
                "reason": f"项目缺少 project.godot: {project_dir}",
            }

        exe = self._resolve_executable()
        if not exe:
            return {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "reason": "未检测到 Godot 可执行文件，无法导出独立包",
                "hint": "放置 tools/godot/godot.exe 或加入 PATH，或在 D:\\Godot\\ 安装编辑器",
            }

        version = self._godot_version(exe)
        if export_path is None:
            export_path = project_dir / "dist" / f"{project_dir.name}.exe"
        export_path = Path(export_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [exe, "--headless", "--path", str(project_dir), "--export-release", preset_name, str(export_path)]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_s)
        except subprocess.TimeoutExpired:
            return {
                "status": RuntimeStatus.TIMEOUT,
                "reason": f"导出超过 {self.timeout_s}s",
                "command": cmd,
            }

        stderr = completed.stderr or ""
        if any(marker in stderr for marker in _TEMPLATE_MISS_MARKERS):
            template_dir = self._expected_template_dir(version)
            return {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "reason": "Godot 导出模板缺失，无法产出独立 .exe",
                "expected_template_dir": str(template_dir),
                "hint": (
                    "从 https://godotengine.org/download 下载 "
                    "Godot_v4.7.2-stable_export_templates.tpz 并解压到该目录后重试"
                ),
                "command": cmd,
                "stderr_tail": stderr[-1500:],
            }

        if completed.returncode != 0 or not export_path.exists():
            return {
                "status": RuntimeStatus.FAIL,
                "reason": "导出命令返回非零或产物缺失",
                "returncode": completed.returncode,
                "command": cmd,
                "stderr_tail": stderr[-1500:],
                "stdout_tail": (completed.stdout or "")[-1500:],
            }

        artifacts = [str(export_path)]
        pck = export_path.with_suffix(".pck")
        if pck.exists():
            artifacts.append(str(pck))
        return {
            "status": RuntimeStatus.PASS,
            "export_path": str(export_path),
            "artifacts": artifacts,
            "godot_version": version,
            "command": cmd,
        }

    # ---------------------------------------------------------------- 内部实现

    def _resolve_executable(self) -> Optional[str]:
        # None = 自动探测；空字符串 = 调用方明确要求禁用引擎（便于离线诚实测试）。
        if self.godot_executable is not None:
            return self.godot_executable or None
        manifest = EnvironmentInspector.get_toolchain_manifest()
        return manifest.get("tools", {}).get("godot", {}).get("executable") or None

    @staticmethod
    def _godot_version(exe: str) -> str:
        try:
            res = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
            return (res.stdout or "").strip().splitlines()[0] if res.stdout else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    @staticmethod
    def _expected_template_dir(version: str) -> Path:
        # version 形如 "4.7.2.stable.official.ed1daf0bf" → 目录取前 3 段 "4.7.2.stable"
        short = ".".join(version.split(".")[:3]) if version else ""
        exe = EnvironmentInspector.get_toolchain_manifest().get("tools", {}).get("godot", {}).get("executable")
        base = Path(exe).resolve().parent if exe else Path(__file__).resolve().parent.parent
        return base / "export_templates" / short
