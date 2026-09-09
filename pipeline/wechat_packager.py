"""
Antigravity WeChat Mini-Game Packager & Runtime Adapter Generator
=================================================================
Automates bundling standalone HTML5 canvas/web games into compliant WeChat Mini-Game
distribution packages (dist/wechat/) with:
  1. game.json configuration (orientation, network timeout, subpackages).
  2. project.config.json for WeChat DevTools.
  3. weapp-adapter.js (Canvas, DOM, Audio, Storage, and Touch->Mouse event shims).
  4. game.js bootstrap script.
  5. 4MB initial package threshold verification and asset distribution.
"""

import os
import sys
import json
import shutil
import re
from pathlib import Path
from typing import Dict, Any, Optional

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

WECHAT_ADAPTER_JS = """/**
 * Antigravity WeChat Mini-Game Universal Adapter (weapp-adapter.js)
 * Bridges DOM / Canvas / Audio / Touch events to WeChat wx API.
 */
(function() {
  if (typeof wx === 'undefined') return;

  const systemInfo = wx.getSystemInfoSync();
  const screenWidth = systemInfo.windowWidth;
  const screenHeight = systemInfo.windowHeight;
  const pixelRatio = systemInfo.pixelRatio || 1;

  // 1. Canvas initialization
  const mainCanvas = wx.createCanvas();
  mainCanvas.width = screenWidth * pixelRatio;
  mainCanvas.height = screenHeight * pixelRatio;
  mainCanvas.style = {
    width: screenWidth + 'px',
    height: screenHeight + 'px'
  };

  // 2. Global DOM shims
  const dummyElement = {
    addEventListener: function() {},
    removeEventListener: function() {},
    style: {},
    appendChild: function() {},
    removeChild: function() {}
  };

  const listeners = {};

  const documentShim = {
    createElement: function(tag) {
      if (tag === 'canvas') return wx.createCanvas();
      if (tag === 'audio') return wx.createInnerAudioContext ? wx.createInnerAudioContext() : dummyElement;
      return Object.assign({}, dummyElement);
    },
    getElementById: function(id) {
      return mainCanvas;
    },
    getElementsByTagName: function() { return [mainCanvas]; },
    body: dummyElement,
    documentElement: dummyElement,
    addEventListener: function(event, fn) {
      listeners[event] = listeners[event] || [];
      listeners[event].push(fn);
    },
    removeEventListener: function(event, fn) {
      if (!listeners[event]) return;
      listeners[event] = listeners[event].filter(cb => cb !== fn);
    }
  };

  const windowShim = {
    innerWidth: screenWidth,
    innerHeight: screenHeight,
    devicePixelRatio: pixelRatio,
    document: documentShim,
    canvas: mainCanvas,
    addEventListener: documentShim.addEventListener,
    removeEventListener: documentShim.removeEventListener,
    requestAnimationFrame: function(fn) {
      return (typeof requestAnimationFrame !== 'undefined') ? requestAnimationFrame(fn) : setTimeout(fn, 16);
    },
    cancelAnimationFrame: function(id) {
      return (typeof cancelAnimationFrame !== 'undefined') ? cancelAnimationFrame(id) : clearTimeout(id);
    },
    localStorage: {
      getItem: function(k) { try { return wx.getStorageSync(k); } catch(e) { return null; } },
      setItem: function(k, v) { try { wx.setStorageSync(k, v); } catch(e) {} },
      removeItem: function(k) { try { wx.removeStorageSync(k); } catch(e) {} },
      clear: function() { try { wx.clearStorageSync(); } catch(e) {} }
    },
    AudioContext: typeof AudioContext !== 'undefined' ? AudioContext : function() {
      return {
        createGain: function() { return { gain: { value: 1 }, connect: function() {} }; },
        createOscillator: function() { return { frequency: { value: 440 }, connect: function() {}, start: function() {}, stop: function() {} }; },
        destination: {},
        currentTime: 0
      };
    }
  };

  // Expose to global namespace
  if (typeof GameGlobal !== 'undefined') {
    GameGlobal.window = windowShim;
    GameGlobal.document = documentShim;
    GameGlobal.canvas = mainCanvas;
    GameGlobal.DOMParser = function() {};
  }

  // 3. Touch to Mouse Event Bridge
  function dispatchEvent(type, touch) {
    const rect = { left: 0, top: 0, width: screenWidth, height: screenHeight };
    const evt = {
      type: type,
      clientX: touch.clientX,
      clientY: touch.clientY,
      pageX: touch.pageX || touch.clientX,
      pageY: touch.pageY || touch.clientY,
      target: mainCanvas,
      preventDefault: function() {},
      stopPropagation: function() {}
    };
    if (mainCanvas.dispatchEvent) {
      mainCanvas.dispatchEvent(evt);
    }
    const cbs = listeners[type] || [];
    for (let i = 0; i < cbs.length; i++) {
      try { cbs[i](evt); } catch(e) { console.error(e); }
    }
  }

  wx.onTouchStart(function(e) {
    if (e.touches && e.touches.length > 0) {
      dispatchEvent('mousedown', e.touches[0]);
      dispatchEvent('touchstart', e.touches[0]);
    }
  });

  wx.onTouchMove(function(e) {
    if (e.touches && e.touches.length > 0) {
      dispatchEvent('mousemove', e.touches[0]);
      dispatchEvent('touchmove', e.touches[0]);
    }
  });

  wx.onTouchEnd(function(e) {
    if (e.changedTouches && e.changedTouches.length > 0) {
      dispatchEvent('mouseup', e.changedTouches[0]);
      dispatchEvent('click', e.changedTouches[0]);
      dispatchEvent('touchend', e.changedTouches[0]);
    }
  });

  console.log('[WeChat Adapter] Initialized: ' + screenWidth + 'x' + screenHeight + ' @' + pixelRatio + 'x');
})();
"""


class WeChatPackager:
    """Packages HTML5 canvas templates into WeChat Mini-Game projects."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace = workspace_root or WORKSPACE_ROOT
        self.max_main_package_bytes = 4 * 1024 * 1024  # 4.0 MB limit

    def extract_game_script_from_html(self, html_path: Path) -> str:
        """Extracts inline <script> tags from HTML file to create game.js."""
        content = html_path.read_text(encoding="utf-8")
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", content, flags=re.DOTALL | re.IGNORECASE)
        if not scripts:
            return "// No inline script found in template.\n"
        return "\n\n// --- Extracted from HTML template ---\n".join(scripts)

    def bundle(
        self,
        source_html: Path,
        output_dir: Path,
        app_id: str = "touristappid",
        project_name: str = "antigravity-game",
        orientation: str = "landscape"
    ) -> Dict[str, Any]:
        """Bundles the game into target directory."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write weapp-adapter.js
        adapter_path = output_dir / "weapp-adapter.js"
        adapter_path.write_text(WECHAT_ADAPTER_JS, encoding="utf-8")

        # 2. Extract script and create game.js
        extracted_js = self.extract_game_script_from_html(source_html)
        game_js_content = (
            "require('./weapp-adapter.js');\n\n"
            "// --- Game Global Init ---\n"
            + extracted_js
        )
        game_js_path = output_dir / "game.js"
        game_js_path.write_text(game_js_content, encoding="utf-8")

        # 3. Generate game.json
        game_json = {
            "deviceOrientation": orientation,
            "showStatusBar": False,
            "networkTimeout": {
                "request": 10000,
                "connectSocket": 10000,
                "uploadFile": 10000,
                "downloadFile": 10000
            },
            "subpackages": []
        }
        game_json_path = output_dir / "game.json"
        game_json_path.write_text(json.dumps(game_json, indent=2, ensure_ascii=False), encoding="utf-8")

        # 4. Generate project.config.json
        project_config = {
            "miniprogramRoot": "./",
            "projectname": project_name,
            "description": "Antigravity Ford-T AI-Native Game Platform WeChat Build",
            "appid": app_id,
            "setting": {
                "urlCheck": True,
                "es6": True,
                "enhance": True,
                "postcss": False,
                "preloadBackgroundData": False,
                "minified": True
            },
            "compileType": "game"
        }
        proj_config_path = output_dir / "project.config.json"
        proj_config_path.write_text(json.dumps(project_config, indent=2, ensure_ascii=False), encoding="utf-8")

        # 5. Measure output size
        total_size = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file())
        size_mb = round(total_size / (1024 * 1024), 3)
        compliant = total_size <= self.max_main_package_bytes

        return {
            "output_dir": str(output_dir),
            "total_bytes": total_size,
            "size_mb": size_mb,
            "max_mb": 4.0,
            "compliant": compliant,
            "files_generated": [
                str(adapter_path.name),
                str(game_js_path.name),
                str(game_json_path.name),
                str(proj_config_path.name)
            ]
        }


def run_standalone():
    packager = WeChatPackager()
    template_path = WORKSPACE_ROOT / "templates" / "survivor_danmaku" / "index.html"
    out_dir = WORKSPACE_ROOT / "dist" / "wechat"
    res = packager.bundle(template_path, out_dir, project_name="survivor-danmaku-wx", orientation="portrait")
    print(f"WeChat Bundle Completed -> {res['output_dir']}")
    print(f"Size: {res['size_mb']}MB / {res['max_mb']}MB | Compliant: {res['compliant']}")
    print(f"Files: {', '.join(res['files_generated'])}")


if __name__ == "__main__":
    run_standalone()
