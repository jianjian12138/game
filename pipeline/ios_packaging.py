#!/usr/bin/env python3
"""pipeline/ios_packaging.py: iOS 原生打包（Tier 3，本机物理不可达）

诚实边界（红线 13.2 / Tier 3）：
    iOS 原生构建必须 macOS + Xcode；本机是 Windows，**物理不可达**。
    因此 ios_export() 永远返回 NEEDS_MACOS_BUILDER，绝不伪造 PASS。
    本模块只提供 macOS 构建机 / CI 应执行的步骤清单（诚实标注 unverified），
    以及 Godot 导出 iOS 工程的命令模板，供换机后真验证使用。

判定方式（换 macOS 构建机后才会执行，此处不执行）：
    godot --headless --export-release "iOS" <xcode_project> ->
    xcodebuild -archive / -exportArchive -> 真机 log 采集 NativeContract 证据。
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent

from core.runtime_adapter import RuntimeStatus
from core.environment_inspector import EnvironmentInspector

IOS_PRESET_NAME = "iOS"


def ios_export(project_dir: Path, export_path: Optional[Path] = None) -> Dict[str, Any]:
    """iOS 原生导出入口。本机（Windows）物理不可达，如实返回 NEEDS_MACOS_BUILDER。

    绝不启动任何子进程假装能出包；仅做静态可达性判断 + 给出换机步骤。
    """
    project_dir = Path(project_dir)
    if not (project_dir / "project.godot").is_file():
        return {"status": RuntimeStatus.BLOCKED_BY_STATIC,
                "reason": f"项目缺少 project.godot: {project_dir}"}

    # 本机若为 Windows / 非 macOS，直接判不可达；绝不伪造。
    import sys
    if sys.platform != "darwin":
        return {
            "status": "NEEDS_MACOS_BUILDER",
            "reason": "iOS 原生构建需 macOS + Xcode；当前宿主为 "
                      f"{sys.platform}，物理不可达，不标已验证",
            "hint": "在 macOS 构建机或 GitHub Actions macOS runner 上执行 macos_ci_steps() 给出的步骤",
            "unverified": True,
        }
    # 以下分支仅在 macOS 上可达（本机不会走到这里），保留作为换机后的真实路径。
    exe = _resolve_godot()
    if not exe:
        return {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "reason": "macOS 上未检测到 Godot 可执行文件"}
    if export_path is None:
        export_path = project_dir / "dist" / f"{project_dir.name}.xcode"
    cmd = [exe, "--headless", "--path", str(project_dir), "--export-release", IOS_PRESET_NAME, str(export_path)]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return {"status": RuntimeStatus.TIMEOUT, "reason": "iOS 导出超时", "command": cmd}
    if completed.returncode != 0 or not Path(export_path).exists():
        return {"status": RuntimeStatus.FAIL, "reason": "iOS 导出失败", "command": cmd,
                "stderr_tail": (completed.stderr or "")[-1500:]}
    return {"status": RuntimeStatus.PASS, "export_path": str(export_path), "command": cmd}


def macos_ci_steps(project_dir: str = "output/godot_demo", scheme: str = "GameAgent") -> Dict[str, Any]:
    """返回 macOS 构建机 / GitHub Actions 应执行的 iOS 真验证步骤（诚实 unverified）。

    注意：这些步骤当前**未在本机执行**，只是给换机后的操作员/CI 使用的清单，
    标注 unverified=true，不表示已通过验证。
    """
    return {
        "unverified": True,
        "host_required": "macos-latest (Xcode 15+)",
        "runtime_status_on_this_host": "NEEDS_MACOS_BUILDER",
        "steps": [
            {"name": "检出代码", "run": "actions/checkout@v4"},
            {"name": "安装 Godot", "run": "下载 Godot 4.7.2 macOS 版并加入 PATH（或用预装缓存）"},
            {"name": "导出 Xcode 工程", "run":
                f'godot --headless --path {project_dir} --export-release "iOS" export/ios_xcode'},
            {"name": "archive", "run":
                f'xcodebuild -scheme {scheme} -archivePath build/{scheme}.xcarchive archive'},
            {"name": "导出 IPA", "run":
                f'xcodebuild -exportArchive -archivePath build/{scheme}.xcarchive '
                f'-exportPath build/ipa -exportOptionsPlist ExportOptions.plist'},
            {"name": "真机采集运行证据", "run":
                "idevicesyslog | grep GAME_AGENT_ 或在设备上运行并回传 NativeContract 证据"},
            {"name": "断言门禁", "run":
                "frames>=30 且 errors==0 才允许标 PLATFORM_VERIFIED；否则回退 NEEDS_RUNTIME_TOOL"},
        ],
    }


def _resolve_godot() -> Optional[str]:
    manifest = EnvironmentInspector.get_toolchain_manifest()
    return manifest.get("tools", {}).get("godot", {}).get("executable") or None


__all__ = ["ios_export", "macos_ci_steps", "IOS_PRESET_NAME"]
