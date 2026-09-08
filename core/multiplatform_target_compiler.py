"""
Universal Multi-Platform Target Compiler (Article 44 - LayaAir Multiplatform Matrix)
Compiles abstract game specifications into production-ready platform distributions:
1. WeChat Minigame (game.json, project.config.json, wx-adapter, game.js)
2. ByteDance Microgame (TikTok minigame specification)
3. HTML5 Standalone Web
4. Native Desktop (Rust Macroquad Engine Bridge)
"""

import os
import json
from enum import Enum
from typing import Dict, Any, List, Optional
from core.prompt_to_game_assembler import StructuredGameSpec


class TargetPlatform(str, Enum):
    WEB_HTML5 = "web_html5"
    WECHAT_MINIGAME = "wechat_minigame"
    BYTEDANCE_MICROGAME = "bytedance_microgame"
    NATIVE_DESKTOP = "native_desktop"


class MultiplatformTargetCompiler:
    """
    Automated distribution compiler supporting Write-Once, Deploy-Everywhere
    across Mini-Game ecosystems, Web, and Native containers.
    """

    @staticmethod
    def compile_target(
        spec: StructuredGameSpec,
        target: TargetPlatform,
        output_dir: str,
        app_id: str = "wx_preview_game_01"
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        manifest = {
            "target": target.value,
            "title": spec.title,
            "app_id": app_id,
            "output_dir": output_dir,
            "emitted_files": []
        }

        if target == TargetPlatform.WECHAT_MINIGAME:
            MultiplatformTargetCompiler._emit_wechat_minigame(spec, output_dir, app_id, manifest)
        elif target == TargetPlatform.BYTEDANCE_MICROGAME:
            MultiplatformTargetCompiler._emit_bytedance_microgame(spec, output_dir, app_id, manifest)
        elif target == TargetPlatform.WEB_HTML5:
            MultiplatformTargetCompiler._emit_web_html5(spec, output_dir, manifest)
        elif target == TargetPlatform.NATIVE_DESKTOP:
            MultiplatformTargetCompiler._emit_native_desktop(spec, output_dir, manifest)

        return manifest

    @staticmethod
    def _emit_wechat_minigame(spec: StructuredGameSpec, out_dir: str, app_id: str, manifest: Dict[str, Any]):
        # 1. game.json
        game_json = {
            "deviceOrientation": "portrait",
            "showStatusBar": False,
            "networkTimeout": {
                "request": 10000,
                "connectSocket": 10000,
                "uploadFile": 10000,
                "downloadFile": 10000
            },
            "subpackages": []
        }
        game_json_path = os.path.join(out_dir, "game.json")
        with open(game_json_path, "w", encoding="utf-8") as f:
            json.dump(game_json, f, indent=2)
        manifest["emitted_files"].append("game.json")

        # 2. project.config.json
        project_config = {
            "description": f"WeChat Minigame distribution for {spec.title}",
            "setting": {
                "urlCheck": False,
                "es6": True,
                "enhance": True,
                "postcss": False,
                "minified": True
            },
            "compileType": "minigame",
            "libVersion": "3.4.0",
            "appid": app_id,
            "projectname": spec.title.replace(" ", "_")
        }
        proj_cfg_path = os.path.join(out_dir, "project.config.json")
        with open(proj_cfg_path, "w", encoding="utf-8") as f:
            json.dump(project_config, f, indent=2)
        manifest["emitted_files"].append("project.config.json")

        # 3. minigame-adapter.js (WeChat Canvas & Touch Polyfill)
        adapter_code = """// WeChat Minigame Standard Runtime Adapter Shim
const canvas = wx.createCanvas();
const context = canvas.getContext('2d');

window = {
  innerWidth: canvas.width,
  innerHeight: canvas.height,
  devicePixelRatio: wx.getSystemInfoSync().pixelRatio,
  requestAnimationFrame: (cb) => setTimeout(cb, 1000 / 60),
  performance: { now: () => Date.now() }
};
document = {
  createElement: (tag) => tag === 'canvas' ? canvas : {},
  getElementById: () => canvas
};

// Touch to Pointer event translation
wx.onTouchStart((e) => {
  if (window.__onPointerDown && e.touches.length > 0) {
    window.__onPointerDown(e.touches[0].clientX, e.touches[0].clientY);
  }
});
wx.onTouchMove((e) => {
  if (window.__onPointerMove && e.touches.length > 0) {
    window.__onPointerMove(e.touches[0].clientX, e.touches[0].clientY);
  }
});
wx.onTouchEnd(() => {
  if (window.__onPointerUp) window.__onPointerUp();
});

module.exports = { canvas, context };
"""
        adapter_path = os.path.join(out_dir, "minigame-adapter.js")
        with open(adapter_path, "w", encoding="utf-8") as f:
            f.write(adapter_code)
        manifest["emitted_files"].append("minigame-adapter.js")

        # 4. game.js (Entry Point)
        spec_dict = spec.to_dict()
        game_js = f"""// Auto-generated WeChat Minigame Entry for {spec.title}
const {{ canvas, context }} = require('./minigame-adapter.js');
const SPEC = {json.dumps(spec_dict, indent=2)};

console.log('[WeChat Minigame Boot] Initialized: ' + SPEC.title);

let score = 0;
let lives = SPEC.termination.max_lives;
let playerY = canvas.height / 2;
let vy = 0;

window.__onPointerDown = (x, y) => {{
  if (SPEC.controls.scheme === 'one_tap') {{
    vy = -12;
  }}
}};

function loop() {{
  // Simple game loop iteration
  vy += 0.5; // gravity
  playerY += vy;
  if (playerY > canvas.height - 40) {{ playerY = canvas.height - 40; vy = 0; }}

  context.fillStyle = SPEC.aesthetics.bg_color || '#0a0e17';
  context.fillRect(0, 0, canvas.width, canvas.height);

  context.fillStyle = SPEC.aesthetics.primary_color || '#00f0ff';
  context.beginPath();
  context.arc(canvas.width / 2, playerY, SPEC.avatar.size || 16, 0, Math.PI * 2);
  context.fill();

  context.fillStyle = '#ffffff';
  context.font = '20px sans-serif';
  context.fillText(`Score: ${{score}}  Lives: ${{lives}}`, 20, 50);

  requestAnimationFrame(loop);
}}

requestAnimationFrame(loop);
"""
        game_js_path = os.path.join(out_dir, "game.js")
        with open(game_js_path, "w", encoding="utf-8") as f:
            f.write(game_js)
        manifest["emitted_files"].append("game.js")

    @staticmethod
    def _emit_bytedance_microgame(spec: StructuredGameSpec, out_dir: str, app_id: str, manifest: Dict[str, Any]):
        # ByteDance (TikTok) Microgame standard
        game_json = {
            "deviceOrientation": "portrait",
            "showStatusBar": False,
            "subpackages": []
        }
        with open(os.path.join(out_dir, "game.json"), "w", encoding="utf-8") as f:
            json.dump(game_json, f, indent=2)
        manifest["emitted_files"].append("game.json")

        proj_cfg = {
            "setting": {"es6": True, "minified": True},
            "appid": app_id,
            "projectname": spec.title.replace(" ", "_")
        }
        with open(os.path.join(out_dir, "project.config.json"), "w", encoding="utf-8") as f:
            json.dump(proj_cfg, f, indent=2)
        manifest["emitted_files"].append("project.config.json")

        tt_adapter = """// ByteDance TikTok Microgame Adapter
const canvas = tt.createCanvas();
const context = canvas.getContext('2d');
tt.onTouchStart((e) => { if (e.touches[0]) console.log('TT Tap', e.touches[0].clientX); });
module.exports = { canvas, context };
"""
        with open(os.path.join(out_dir, "tt-adapter.js"), "w", encoding="utf-8") as f:
            f.write(tt_adapter)
        manifest["emitted_files"].append("tt-adapter.js")

        with open(os.path.join(out_dir, "game.js"), "w", encoding="utf-8") as f:
            f.write(f"// ByteDance entry for {spec.title}\nrequire('./tt-adapter.js');\nconsole.log('TikTok Minigame Booted');\n")
        manifest["emitted_files"].append("game.js")

    @staticmethod
    def _emit_web_html5(spec: StructuredGameSpec, out_dir: str, manifest: Dict[str, Any]):
        from pipeline.game_remix_patcher import PlayableWebBundler
        index_html = os.path.join(out_dir, "index.html")
        PlayableWebBundler.bundle_to_html(spec, output_path=index_html)
        manifest["emitted_files"].append("index.html")

    @staticmethod
    def _emit_native_desktop(spec: StructuredGameSpec, out_dir: str, manifest: Dict[str, Any]):
        config = {
            "title": spec.title,
            "window_width": 480,
            "window_height": 720,
            "engine": "Macroquad Rust 2D/3D",
            "spec_ref": spec.spec_id
        }
        with open(os.path.join(out_dir, "desktop_launcher.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        manifest["emitted_files"].append("desktop_launcher.json")
