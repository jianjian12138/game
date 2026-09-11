#!/usr/bin/env python3
"""
core/environment_inspector.py: 宿主机工具链环境自检与体检清册 (Toolchain & Environment Inspector)
自动探测宿主机 Python、Git、Edge(Chromium)、Chrome、Node、Godot 等核心工具路径与版本，
提供符合规范的 ToolchainManifest，对缺失工具提供 Fail-Closed 诊断指导。
纯 Python 3.9+ 标准库实现，零外部依赖。
"""
import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

ROOT = Path(__file__).resolve().parent.parent

class EnvironmentInspector:
    """工具链环境自检器与版本清册管理器"""

    COMMON_EDGE_PATHS = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
    ]

    COMMON_CHROME_PATHS = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]

    @classmethod
    def detect_chromium_executable(cls) -> Optional[str]:
        """优先搜索本地系统 PATH 及标准安装目录下的 Chromium 内核浏览器 (Edge / Chrome)"""
        # 1. 检查环境变量指定
        custom = os.environ.get("CHROMIUM_PATH", "").strip()
        if custom and os.path.isfile(custom):
            return custom

        # 2. 检查系统 PATH
        for name in ("chrome", "chrome.exe", "msedge", "msedge.exe", "chromium", "chromium.exe"):
            found = shutil.which(name)
            if found:
                return found

        # 3. 检查 Windows 常见安装路径
        for p in cls.COMMON_EDGE_PATHS:
            if os.path.isfile(p):
                return p
        for p in cls.COMMON_CHROME_PATHS:
            if os.path.isfile(p):
                return p

        return None

    @classmethod
    def get_toolchain_manifest(cls) -> Dict[str, Any]:
        """构建完整的工具链版本清册 (ToolchainManifest)"""
        tools = {}

        # 1. Python
        tools["python"] = {
            "name": "Python",
            "required": True,
            "installed": True,
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "executable": sys.executable,
            "role": "核心调度中枢、门禁裁决与契约引擎"
        }

        # 2. Git
        git_path = shutil.which("git")
        git_ver = ""
        if git_path:
            try:
                res = subprocess.run([git_path, "--version"], capture_output=True, text=True, timeout=3)
                git_ver = res.stdout.strip()
            except Exception:
                git_ver = "Unknown"
        tools["git"] = {
            "name": "Git",
            "required": True,
            "installed": bool(git_path),
            "version": git_ver,
            "executable": git_path or "",
            "role": "源码与审计版本追踪"
        }

        # 3. Chromium 内核浏览器 (Edge / Chrome)
        chrom_exe = cls.detect_chromium_executable()
        tools["chromium"] = {
            "name": "Chromium Browser Engine (Edge/Chrome)",
            "required": True,
            "installed": bool(chrom_exe),
            "version": "Chromium-based" if chrom_exe else "",
            "executable": chrom_exe or "",
            "role": "首条主线 (Web 2D/3D) 真实运行、渲染探测与页面事件采集"
        }

        # 4. Node.js & npm (可选前端重型工具)
        node_path = shutil.which("node")
        tools["node"] = {
            "name": "Node.js",
            "required": False,
            "installed": bool(node_path),
            "version": "Available" if node_path else "",
            "executable": node_path or "",
            "role": "可选外部 npm 打包链 (当前主线由 Python 原生编译替代)"
        }

        # 5. Godot 4.x (第二目标引擎)
        # 优先尊重显式 GODOT_PATH；其次查 PATH、项目 tools/godot，最后查
        # Windows 常见的绿色单文件安装位置。这样 Doctor 与 GodotRuntimeAdapter
        # 对“已安装但未入 PATH”的本机环境保持同一事实口径。
        godot_path = os.environ.get("GODOT_PATH", "").strip()
        if godot_path and not os.path.isfile(godot_path):
            godot_path = ""
        godot_path = godot_path or shutil.which("godot") or shutil.which("godot.exe")
        if not godot_path:
            local_candidates = [
                ROOT / "tools" / "godot" / "godot.exe",
                Path(r"D:\Godot\Godot_v4.7.2-stable_win64.exe"),
                Path(r"D:\Godot\Godot_v4.7.2-stable_win64_console.exe"),
            ]
            for local_godot in local_candidates:
                if local_godot.exists():
                    godot_path = str(local_godot)
                    break
        tools["godot"] = {
            "name": "Godot 4.x Engine",
            "required": False,
            "installed": bool(godot_path),
            "version": "4.7.2" if godot_path and "Godot_v4.7.2" in godot_path else ("4.x" if godot_path else ""),
            "executable": godot_path or "",
            "role": "第二目标：Godot 跨端导出与桌面运行"
        }

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "os": sys.platform,
            "tools": tools,
            "web_mainline_ready": bool(tools["python"]["installed"] and tools["chromium"]["installed"])
        }

    @classmethod
    def preflight_check(cls, target: str = "web") -> Dict[str, Any]:
        """运行前环境自检门禁，返回状态与诊断建议"""
        manifest = cls.get_toolchain_manifest()
        issues = []

        if not manifest["tools"]["python"]["installed"]:
            issues.append({"tool": "python", "level": "BLOCKING", "msg": "Python 运行时缺失"})

        if target == "web":
            if not manifest["tools"]["chromium"]["installed"]:
                issues.append({
                    "tool": "chromium",
                    "level": "BLOCKING",
                    "msg": "未检测到 Chromium 内核浏览器 (Edge/Chrome)。静态构建可用，但无法执行真实运行时冒烟验证。",
                    "solution": "请安装 Microsoft Edge 或 Google Chrome，或通过环境变量 CHROMIUM_PATH 指定可执行文件路径。"
                })
        elif target == "godot":
            if not manifest["tools"]["godot"]["installed"]:
                issues.append({
                    "tool": "godot",
                    "level": "BLOCKING",
                    "msg": "未检测到 Godot 4.x 命令行环境。",
                    "solution": "请下载官方 Godot 4.3+ 绿色单文件，置于 tools/godot/ 或加入系统 PATH。"
                })

        return {
            "target": target,
            "passed": len(issues) == 0,
            "issues": issues,
            "manifest": manifest
        }
