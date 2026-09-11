#!/usr/bin/env python3
"""pipeline/desktop_shell_adapter.py: PC 桌面 web-shell（Electron / Tauri）适配器

诚实边界（红线 13.2 / Tier 1，但带诚实标注）：
    桌面 web-shell 只是把已验证的 Web 构建封进桌面壳，再用 steam/itch 分发。
    我们**绝不**把它粉饰成「原生游戏引擎」：分发清单里标 web_in_desktop=true，
    且桌面壳本身的「真实运行验证」需要 Electron/Tauri 构建链（node/npm 或 cargo）。

判定方式：
    - package_desktop_shell() 生成壳工程文件（main.js/package.json 等）——这是真实文件产物，可 PASS。
    - DesktopShellAdapter.run_scenarios() 若要证明「游戏真的在桌面壳里跑起来」，
      必须启动 Electron/Tauri 渲染 index.html；缺框架 -> NEEDS_RUNTIME_TOOL（不伪 PASS）。
"""
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent

from core.runtime_adapter import RuntimeAdapter, RuntimeStatus

DEFAULT_SCENARIOS = ["boot", "core_loop"]

_ELECTRON_MAIN_JS = """'use strict';
// 桌面 web-shell 主进程：把已验证的 Web 构建封进 BrowserWindow。
// 注意：这是 web-in-desktop，不是原生游戏引擎重写。
const {{ app, BrowserWindow }} = require('electron');
const path = require('path');

function createWindow() {{
  const win = new BrowserWindow({{
    width: 1280, height: 720,
    webPreferences: {{ contextIsolation: true, nodeIntegration: false }}
  }});
  win.loadFile(path.join(__dirname, 'index.html'));
}}

app.whenReady().then(() => {{
  createWindow();
  app.on('activate', () => {{ if (BrowserWindow.getAllWindows().length === 0) createWindow(); }});
}});
app.on('window-all-closed', () => {{ if (process.platform !== 'darwin') app.quit(); }});
"""

_TAURI_MAIN_RS = """// 桌面 web-shell（Tauri）主入口：加载同目录 index.html。
// 注意：这是 web-in-desktop，不是原生游戏引擎重写。
use tauri::{{Builder, Manager}};

fn main() {{
    Builder::default()
        .run(tauri::generate_context!())
        .expect("桌面壳启动失败");
}}
"""

_TAURI_CONF_JSON = """{{
  "build": {{
    "beforeDevCommand": "",
    "beforeBuildCommand": "",
    "devPath": "../index.html",
    "distDir": "../"
  }},
  "package": {{
    "productName": "{title}",
    "version": "1.0.0"
  }},
  "tauri": {{
    "windows": [
      {{ "title": "{title}", "width": 1280, "height": 720, "resizable": true }}
    ],
    "bundle": {{ "active": true, "identifier": "com.gameagent.{slug}", "targets": "all" }}
  }}
}}
"""


class DesktopShellAdapter(RuntimeAdapter):
    name = "desktop_shell_adapter"
    version = "1.0.0"

    def __init__(self, framework: str = "electron", timeout_s: int = 120):
        if framework not in ("electron", "tauri"):
            raise ValueError(f"不支持的桌面壳框架: {framework}（可选 electron / tauri）")
        self.framework = framework
        self.timeout_s = timeout_s

    # ---------------------------------------------------------------- 入口：生成壳工程（真实文件产物）

    def package_desktop_shell(
        self,
        html_file: Path,
        output_dir: Path,
        title: str = "GameAgent Desktop Shell",
        slug: str = "game-agent-shell",
    ) -> Dict[str, Any]:
        """把 Web 构建封进桌面壳工程并落盘。

        诚实口径：生成壳工程文件是真实可交付产物（PASS），但「构建出可运行 .exe/.app」
        依赖 Electron/Tauri 构建链，由 run_scenarios/preflight 如实门禁。
        """
        html_file = Path(html_file)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(html_file, out / "index.html")
        files = ["index.html"]

        if self.framework == "electron":
            (out / "package.json").write_text(json.dumps({
                "name": slug,
                "version": "1.0.0",
                "main": "main.js",
                "scripts": {"start": "electron .", "build": "electron-builder"},
            }, indent=2, ensure_ascii=False), encoding="utf-8")
            (out / "main.js").write_text(_ELECTRON_MAIN_JS, encoding="utf-8")
            files += ["package.json", "main.js"]
        else:  # tauri
            src_tauri = out / "src-tauri"
            src_tauri.mkdir(parents=True, exist_ok=True)
            (src_tauri / "tauri.conf.json").write_text(
                _TAURI_CONF_JSON.format(title=title, slug=slug), encoding="utf-8")
            (src_tauri / "main.rs").write_text(_TAURI_MAIN_RS, encoding="utf-8")
            files += ["src-tauri/tauri.conf.json", "src-tauri/main.rs"]

        return {
            "status": RuntimeStatus.PASS,
            "framework": self.framework,
            "web_in_desktop": True,
            "output_dir": str(out),
            "files": files,
            "note": "壳工程已生成；构建可运行桌面包需对应框架构建链（见 preflight）",
        }

    # ---------------------------------------------------------------- 运行时适配器接口

    def preflight(self, target: str = "desktop_shell", environment: str = "sandbox") -> Dict[str, Any]:
        exe = self._resolve_builder()
        if not exe:
            return {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "target": target,
                "can_launch": False,
                "framework": self.framework,
                "reason": f"未检测到 {self.framework} 构建链，无法把壳工程构建为可运行桌面包",
                "hint": "electron 需 node/npm + electron；tauri 需 cargo + tauri-cli",
            }
        return {
            "status": RuntimeStatus.PASS,
            "target": target,
            "can_launch": True,
            "framework": self.framework,
            "builder": exe,
            "reason": None,
        }

    def launch(self, artifact_path: Path, environment: str = "sandbox") -> Dict[str, Any]:
        path = Path(artifact_path)
        # 壳工程必须含 index.html（来自 package_desktop_shell）
        if not (path / "index.html").is_file():
            return {
                "status": RuntimeStatus.BLOCKED_BY_STATIC,
                "target": "desktop_shell",
                "project_dir": str(path),
                "scenarios": {},
                "observations": {},
                "metrics": {"collected": False},
                "errors": [{"code": "SHELL_PROJECT_MISSING", "message": f"壳工程缺少 index.html: {path}"}],
            }
        exe = self._resolve_builder()
        if not exe:
            return {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "target": "desktop_shell",
                "project_dir": str(path),
                "builder": None,
                "scenarios": {},
                "observations": {},
                "metrics": {"collected": False},
                "errors": [{"code": "SHELL_BUILDER_MISSING", "message": f"未检测到 {self.framework} 构建链"}],
            }
        return {
            "status": RuntimeStatus.PASS,
            "target": "desktop_shell",
            "project_dir": str(path),
            "builder": exe,
            "scenarios": {},
            "observations": {},
            "metrics": {"collected": False},
            "errors": [],
        }

    def run_scenarios(self, session: Dict[str, Any], scenarios: Optional[List[str]] = None) -> Dict[str, Any]:
        target_scenarios = list(scenarios or DEFAULT_SCENARIOS)
        session["scenarios"] = session.get("scenarios") or {}
        if session.get("status") == RuntimeStatus.BLOCKED_BY_STATIC:
            reason = "壳工程缺少 index.html，静态校验未通过"
        elif not session.get("builder"):
            reason = f"未检测到 {self.framework} 构建链"
        else:
            reason = None

        # 诚实降级：缺框架 -> 无法证明「游戏真的在桌面壳里跑起来」-> NEEDS_RUNTIME_TOOL。
        if reason:
            for sc in target_scenarios:
                session["scenarios"][sc] = {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL, "reason": reason}
            session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
            return {"status": session["status"], "scenarios": session["scenarios"], "observations": session["observations"]}

        # 框架就绪时的真实路径（本机不执行）：启动 Electron/Tauri 渲染 index.html，
        # 复用 BrowserContract 采集帧/状态/输入。此处用 NEEDS_RUNTIME_TOOL 占位。
        for sc in target_scenarios:
            session["scenarios"][sc] = {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "reason": "桌面壳真验证需框架构建链启动渲染进程，本机未启用（NEEDS_RUNTIME_TOOL 占位，非伪 PASS）",
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
                "target": "desktop_shell",
                "framework": self.framework,
                "project_dir": session.get("project_dir"),
                "builder": session.get("builder"),
            },
            "errors": session.get("errors", []),
            "web_in_desktop": True,
        }

    def close(self, session: Dict[str, Any]) -> Dict[str, Any]:
        session["alive"] = False
        return {"closed": True, "session_id": session.get("session_id")}

    # ---------------------------------------------------------------- 内部实现

    def _resolve_builder(self) -> Optional[str]:
        # 仅当框架二进制真实存在才算「可构建」：npx/cargo 存在不代表 electron/tauri 已装，
        # 故要求 electron / electron-builder / tauri 之一，避免把「有 node」误判为「能出桌面包」。
        if self.framework == "electron":
            return shutil.which("electron") or shutil.which("electron-builder")
        # tauri
        return shutil.which("tauri")


__all__ = ["DesktopShellAdapter"]
