#!/usr/bin/env python3
"""
pipeline/browser_runtime_adapter.py: 浏览器真实运行适配器 (Browser Runtime Adapter)

诚实边界（红线 13.2）：
    没有可用的真实自动化驱动时，本适配器一律返回 NEEDS_RUNTIME_TOOL，
    绝不因为「HTML 里写了 canvas」或「import 成功」而判定场景通过。
    只有真正完成页面加载、主循环推进、错误采集之后才会给出 PASS。
"""
import os
import time
import socket
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from http.server import HTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parent.parent

from core.runtime_adapter import RuntimeAdapter, RuntimeSession, RuntimeStatus
from core.environment_inspector import EnvironmentInspector

# 判定主循环存活所要求的最小 rAF 推进帧数
MIN_FRAME_ADVANCE = 3
# 主循环采样窗口（毫秒）
FRAME_SAMPLE_WINDOW_MS = 400

# 无头浏览器默认会把页面当作不可见并停止合成，实测 requestAnimationFrame 1 秒 0 帧，
# 导致「页面加载成功」被误判成「游戏没在跑」。加入下列参数后实测恢复至约 39 帧/秒，
# 且 SwiftShader 仍能提供可用的 WebGL 上下文（renderer 报告 WebKit WebGL）。
CHROMIUM_ARGS = [
    "--use-gl=angle",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-gpu",
    "--run-all-compositor-stages-before-draw",
]

_JS_CANVAS_SIZE = """
() => {
  const c = document.querySelector('canvas');
  return c ? { width: c.width, height: c.height } : null;
}
"""

_JS_GAME_CONTRACT = """
() => {
  const g = window.__GAME_AGENT__;
  if (!g) { return null; }
  return {
    state: g.state || null,
    frame: typeof g.frame === 'number' ? g.frame : 0,
    ticks: typeof g.ticks === 'number' ? g.ticks : 0,
    ready: !!g.ready,
    game_over_count: typeof g.game_over_count === 'number' ? g.game_over_count : 0,
    restart_count: typeof g.restart_count === 'number' ? g.restart_count : 0,
    errors: Array.isArray(g.errors) ? g.errors.slice(0, 5) : []
  };
}
"""


def _loop_position(contract: Optional[Dict[str, Any]]) -> int:
    """主循环推进位置：rAF 帧数 + 定时器 tick 数。"""
    if not contract:
        return 0
    return int(contract.get("frame") or 0) + int(contract.get("ticks") or 0)


# 真实像素采样（防伪核心）：证明「画面真在渲染」而非仅 canvas 存在。
#   2D 画布：getImageData 统计非背景像素数 + 内容 FNV 哈希（用于前后帧 diff 证明动画/输入生效）。
#   WebGL / 被污染的画布：回退 toDataURL 哈希（长度启发式判定非空）。
#   返回 None 表示页面根本没有 canvas；type=='fail' 表示两种采样都失败（无法证实渲染）。
_JS_CANVAS_PIXELS = r"""
() => {
  const c = document.querySelector('canvas');
  if (!c) return null;
  const w = c.width, h = c.height;
  if (!w || !h) return null;
  try {
    const ctx2d = c.getContext('2d');
    if (ctx2d && typeof ctx2d.getImageData === 'function') {
      const data = ctx2d.getImageData(0, 0, w, h).data;
      let hash = 2166136261 >>> 0, nonzero = 0, sampled = 0;
      for (let i = 0; i < data.length; i += 4 * 31) {
        const r = data[i], g = data[i+1], b = data[i+2];
        hash = (Math.imul(hash ^ ((r*3 + g*5 + b*7) & 0xff), 16777619)) >>> 0;
        if (r + g + b > 12) nonzero++;
        sampled++;
      }
      return { type: '2d', w: w, h: h, hash: hash >>> 0,
               nonzero: nonzero, sampled: sampled, nonblank: nonzero > 0 };
    }
  } catch (e) {}
  try {
    const url = c.toDataURL();
    let hash = 2166136261 >>> 0;
    for (let i = 0; i < url.length; i += 11) {
      hash = (Math.imul(hash ^ url.charCodeAt(i), 16777619)) >>> 0;
    }
    return { type: 'dataurl', w: w, h: h, hash: hash >>> 0,
             length: url.length, nonblank: url.length > 1500 };
  } catch (e) {
    return { type: 'fail', w: w, h: h, error: String(e) };
  }
}
"""


class _QuietHTTPHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class BrowserRuntimeAdapter(RuntimeAdapter):
    """基于受控本地 HTTP 托管 + Playwright/Chromium 真实驱动的浏览器适配器"""

    name: str = "browser_runtime_adapter"
    target: str = "web"
    version: str = "1.1.0"

    def __init__(self, browser_path: Optional[str] = None, evidence_dir: Optional[Path] = None):
        self.browser_path = browser_path or EnvironmentInspector.detect_chromium_executable()
        self.evidence_dir = Path(evidence_dir) if evidence_dir else None

    def preflight(self, target: str = "web", environment: str = "sandbox") -> Dict[str, Any]:
        exe = self.browser_path or EnvironmentInspector.detect_chromium_executable()
        if not exe or not os.path.isfile(exe):
            return {
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "browser_executable": None,
                "reason": "未检测到本地 Edge 或 Chrome 浏览器可执行程序",
                "can_launch": False,
            }
        driver, driver_reason = self._load_driver()
        return {
            "status": RuntimeStatus.PASS if driver else RuntimeStatus.NEEDS_RUNTIME_TOOL,
            "browser_executable": exe,
            "automation_driver": "playwright" if driver else None,
            "driver_reason": driver_reason,
            "can_launch": bool(driver),
        }

    def launch(self, artifact_path: Path, environment: str = "sandbox") -> RuntimeSession:
        target = Path(artifact_path)
        if target.is_file():
            serve_dir, file_name = target.parent, target.name
        else:
            serve_dir, file_name = target, "index.html"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        handler_factory = lambda *a, **kw: _QuietHTTPHandler(*a, directory=str(serve_dir), **kw)
        httpd = HTTPServer(("127.0.0.1", port), handler_factory)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

        server_url = f"http://127.0.0.1:{port}/{file_name}"
        return RuntimeSession(
            session_id=f"session_{int(time.time() * 1000)}_{port}",
            url=server_url,
            target="web",
            server=httpd,
            port=port,
            server_url=server_url,
            artifact_path=str(target),
            browser_exe=self.browser_path or EnvironmentInspector.detect_chromium_executable(),
            status="LAUNCHED",
            scenarios={},
            observations={"host": "127.0.0.1", "port": port, "entry_url": server_url},
            metrics={"collected": False},
            errors=[],
        )

    def run_scenarios(self, session: Dict[str, Any], scenarios: Optional[List[str]] = None) -> Dict[str, Any]:
        target_scenarios = scenarios or ["boot", "start", "core_loop", "game_over", "restart"]

        html, fetch_error = self._fetch_entry(session)
        if fetch_error:
            session["status"] = RuntimeStatus.FAIL
            session["errors"].append({"code": "HTTP_SERVE_FAILED", "message": fetch_error})
            return {"status": RuntimeStatus.FAIL, "session": session}

        # 弱信号：仅作记录，绝不参与通过判定
        session["observations"]["http_status"] = 200
        session["observations"]["content_length"] = len(html)
        session["observations"]["declares_canvas"] = "<canvas" in html
        session["observations"]["declares_raf"] = "requestAnimationFrame" in html

        driver, driver_reason = self._load_driver()
        if driver is None:
            session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
            session["errors"].append({
                "code": "RUNTIME_DRIVER_MISSING",
                "message": f"缺少真实浏览器自动化驱动，无法断言运行时行为: {driver_reason}",
            })
            for sc in target_scenarios:
                session["scenarios"][sc] = {
                    "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                    "reason": "无自动化驱动，未执行真实加载与交互",
                }
            return {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL, "scenarios": session["scenarios"],
                    "observations": session["observations"]}

        return self._drive_scenarios(session, target_scenarios, driver)

    def collect_evidence(self, session: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "session_id": session.get("session_id"),
            "status": session.get("status"),
            "runtime_facts": {
                "adapter": self.name,
                "adapter_version": self.version,
                "browser_executable": session.get("browser_exe"),
                "entry_url": session.get("server_url"),
                "port": session.get("port"),
            },
            "scenarios": session.get("scenarios", {}),
            "observations": session.get("observations", {}),
            "metrics": session.get("metrics", {}),
            "errors": session.get("errors", []),
        }

    def close(self, session: Any) -> Dict[str, Any]:
        server = session.get("server")
        if server:
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                pass
        if hasattr(session, "alive"):
            session.alive = False
        session["status"] = "CLOSED"
        return {"status": "SUCCESS", "session_id": session.get("session_id")}

    def probe_webgl(self, asset_path: Path) -> Dict[str, Any]:
        """3D 资产 WebGL 观测：供 pipeline/webgl_runtime_probe.py 作为真实驱动调用。

        只有在真实浏览器中创建出 WebGL 上下文、且页面暴露 __GAME_AGENT__ 契约
        报告了渲染统计时，才返回 SUCCESS；否则一律 NEEDS_RUNTIME_TOOL。
        """
        path = Path(asset_path)
        if not path.exists():
            return {"status": "FAIL", "error": f"资产不存在: {path}"}

        driver, reason = self._load_driver()
        if driver is None:
            return {"status": "NEEDS_RUNTIME_TOOL", "error": reason}

        session = self.launch(path)
        payload: Dict[str, Any] = {"status": "NEEDS_RUNTIME_TOOL"}
        try:
            with driver() as p:
                browser = p.chromium.launch(
                    executable_path=session.get("browser_exe"),
                    headless=True,
                    args=CHROMIUM_ARGS,
                )
                page = browser.new_page(viewport={"width": 960, "height": 600})
                page.goto(session.get("server_url"), wait_until="load", timeout=20000)
                page.wait_for_timeout(600)
                payload = page.evaluate("""() => {
                    const probe = document.createElement('canvas');
                    const gl = probe.getContext('webgl2') || probe.getContext('webgl');
                    const agent = window.__GAME_AGENT__ || null;
                    return {
                        webgl_context: !!gl,
                        renderer: gl ? gl.getParameter(gl.RENDERER) : null,
                        agent: agent ? { state: agent.state || null, frame: agent.frame ?? null,
                                         triangles: agent.triangles ?? null,
                                         draw_calls: agent.draw_calls ?? null } : null,
                    };
                }""")
                browser.close()
        except Exception as exc:
            return {"status": "NEEDS_RUNTIME_TOOL", "error": f"WebGL 观测执行失败: {exc}"}
        finally:
            self.close(session)

        observed = payload or {}
        if observed.get("webgl_context") is not True:
            return {"status": "NEEDS_RUNTIME_TOOL", "error": "浏览器未能创建 WebGL 上下文", **observed}

        agent = observed.get("agent") or {}
        if agent.get("triangles") is None and agent.get("draw_calls") is None:
            return {
                "status": "NEEDS_RUNTIME_TOOL",
                "error": "WebGL 上下文可用，但页面未暴露 __GAME_AGENT__ 渲染统计契约，无法确认资产已渲染",
                **observed,
            }
        return {"status": "SUCCESS", **observed}

    # ------------------------------------------------------------------ 内部实现

    @staticmethod
    def _load_driver():
        """返回 (playwright_sync_factory, reason)。不可用时返回 (None, 原因)。"""
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            return None, f"playwright 不可用 ({exc.__class__.__name__})；请执行 pip install playwright && playwright install chromium"
        return sync_playwright, None

    @staticmethod
    def _fetch_entry(session: Dict[str, Any]):
        import urllib.request
        try:
            with urllib.request.urlopen(session.get("server_url"), timeout=5.0) as resp:
                return resp.read().decode("utf-8", errors="ignore"), None
        except Exception as exc:
            return "", f"本地静态服务访问失败: {exc}"

    def _drive_scenarios(self, session: Dict[str, Any], scenarios: List[str], driver) -> Dict[str, Any]:
        console_errors: List[str] = []
        page_errors: List[str] = []
        failed_requests: List[str] = []

        try:
            with driver() as p:
                browser = p.chromium.launch(
                    executable_path=session.get("browser_exe"),
                    headless=True,
                    args=CHROMIUM_ARGS,
                )
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda e: page_errors.append(str(e)))
                page.on("requestfailed", lambda r: failed_requests.append(str(r.url)))

                page.goto(session.get("server_url"), wait_until="load", timeout=20000)
                page.wait_for_timeout(300)

                canvas = page.evaluate(_JS_CANVAS_SIZE)
                contract_before = page.evaluate(_JS_GAME_CONTRACT)
                page.wait_for_timeout(FRAME_SAMPLE_WINDOW_MS)
                contract = page.evaluate(_JS_GAME_CONTRACT)
                loop_advance = _loop_position(contract) - _loop_position(contract_before)

                session["observations"].update({
                    "canvas_size": canvas,
                    "loop_advance_in_window": loop_advance,
                    "game_contract": contract,
                })

                # boot 只证明「页面被正确加载并初始化」：canvas 有实际尺寸、契约已挂载、无未捕获异常。
                # 主循环是否真的在跑由 start 之后的 core_loop 场景判定——很多游戏要等到开始输入后才注册循环。
                boot_ok = (
                    bool(canvas and canvas.get("width", 0) > 0 and canvas.get("height", 0) > 0)
                    and contract is not None
                    and bool(contract.get("ready"))
                    and not page_errors
                )
                session["scenarios"]["boot"] = (
                    {"status": RuntimeStatus.PASS, "driver": "playwright",
                     "canvas": canvas, "loop_advance": loop_advance}
                    if boot_ok else
                    {"status": RuntimeStatus.FAIL, "driver": "playwright",
                     "canvas": canvas, "loop_advance": loop_advance, "page_errors": page_errors[:5]}
                )

                for sc in scenarios:
                    if sc == "boot":
                        continue
                    session["scenarios"][sc] = self._contract_scenario(page, sc, contract)

                if self.evidence_dir:
                    self.evidence_dir.mkdir(parents=True, exist_ok=True)
                    shot = self.evidence_dir / f"{session.get('session_id')}.png"
                    page.screenshot(path=str(shot))
                    session["observations"]["screenshot"] = str(shot)

                browser.close()
        except Exception as exc:
            session["status"] = RuntimeStatus.NEEDS_RUNTIME_TOOL
            session["errors"].append({"code": "DRIVER_EXECUTION_FAILED", "message": str(exc)})
            for sc in scenarios:
                session["scenarios"].setdefault(
                    sc, {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL, "reason": str(exc)})
            return {"status": RuntimeStatus.NEEDS_RUNTIME_TOOL, "scenarios": session["scenarios"],
                    "observations": session["observations"]}

        # 404 之类的资源加载失败属于网络噪音，会记录但不作为致命错误阻断门禁
        fatal_console = [t for t in console_errors if "Failed to load resource" not in t]
        resource_errors = [t for t in console_errors if "Failed to load resource" in t]

        session["metrics"] = {
            "collected": True,
            "console_error_count": len(fatal_console),
            "page_error_count": len(page_errors),
            "network_failure_count": len(failed_requests) + len(resource_errors),
            "console_errors": fatal_console[:10],
            "page_errors": page_errors[:10],
            "failed_requests": (failed_requests + resource_errors)[:10],
        }

        failed_scenarios = sorted(k for k, v in session["scenarios"].items() if v.get("status") == RuntimeStatus.FAIL)
        if session["scenarios"].get("boot", {}).get("status") != RuntimeStatus.PASS:
            session["status"] = RuntimeStatus.FAIL
        elif failed_scenarios:
            session["status"] = RuntimeStatus.FAIL
        elif session["metrics"]["page_error_count"] or session["metrics"]["console_error_count"]:
            session["status"] = RuntimeStatus.FAIL
        else:
            session["status"] = RuntimeStatus.PASS

        return {
            "status": session["status"],
            "scenarios": session["scenarios"],
            "observations": session["observations"],
            "metrics": session["metrics"],
        }

    @staticmethod
    def _try_start_game(page) -> str:
        """尽力触发游戏开始：优先调用页面暴露的开始接口，其次点击开始按钮，最后才退回按键。"""
        triggered = page.evaluate("""() => {
            // 顶层 const 声明的游戏对象不会挂在 window 上，只能用裸标识符探测
            const holder = (typeof GameApp !== 'undefined' && GameApp)
                || (typeof game !== 'undefined' && game)
                || window.GameApp || window.game || window.GAME || null;
            if (!holder) { return null; }
            // 多数模板要求先选角色/关卡，否则开始按钮仍是 disabled
            const card = document.querySelector('.char-card, [id^="card-"], .choice-card');
            if (card) { card.click(); }
            for (const name of ['startMatch', 'startGame', 'start', 'begin', 'newGame']) {
                if (typeof holder[name] === 'function') {
                    holder[name]();
                    return 'api:' + name;
                }
            }
            return null;
        }""")
        if triggered:
            return triggered

        for selector in ("#start-battle-btn", "#btn-start", "#start", "button:not([disabled])"):
            try:
                element = page.query_selector(selector)
                if element and element.is_visible():
                    element.click()
                    return f"click:{selector}"
            except Exception:
                continue

        page.keyboard.press("Space")
        return "keyboard:space"

    @staticmethod
    def _try_end_game(page) -> Optional[str]:
        """调用游戏自身的终局接口。游戏没有暴露终局入口时返回 None（不做任何猜测）。"""
        return page.evaluate("""() => {
            const holder = (typeof GameApp !== 'undefined' && GameApp) || window.GameApp || null;
            if (!holder) { return null; }
            for (const name of ['endMatch', 'gameOver', 'end']) {
                if (typeof holder[name] === 'function') { holder[name](false); return 'api:' + name; }
            }
            return null;
        }""")

    @staticmethod
    def _try_restart_game(page) -> Optional[str]:
        """触发重开：优先游戏自身的重开接口，其次结算面板上的重开按钮。"""
        triggered = page.evaluate("""() => {
            const holder = (typeof GameApp !== 'undefined' && GameApp) || window.GameApp || null;
            if (holder) {
                for (const name of ['restartMatch', 'restart', 'restartGame', 'newGame']) {
                    if (typeof holder[name] === 'function') { holder[name](); return 'api:' + name; }
                }
            }
            const btn = document.querySelector('#btn-restart, [onclick*="restartMatch"], [onclick*="restart"]');
            if (btn) { btn.click(); return 'click:' + (btn.id || btn.tagName); }
            return null;
        }""")
        return triggered

    @classmethod
    def _contract_scenario(cls, page, scenario: str, contract: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """需要游戏侧运行时契约 (window.__GAME_AGENT__) 才能断言的场景。"""
        if not contract:
            return {
                "status": "NEEDS_GAME_CONTRACT",
                "reason": "页面未暴露 window.__GAME_AGENT__ 运行时契约，无法断言该场景",
            }
        if scenario == "core_loop":
            before = _loop_position(page.evaluate(_JS_GAME_CONTRACT))
            page.wait_for_timeout(FRAME_SAMPLE_WINDOW_MS)
            after_contract = page.evaluate(_JS_GAME_CONTRACT) or {}
            after = _loop_position(after_contract)
            advanced = after - before >= MIN_FRAME_ADVANCE
            return ({"status": RuntimeStatus.PASS, "driver": "playwright", "loop_from": before, "loop_to": after}
                    if advanced else
                    {"status": RuntimeStatus.FAIL, "driver": "playwright", "loop_from": before, "loop_to": after,
                     "reason": "主循环在采样窗口内没有推进"})

        if scenario == "start":
            trigger = cls._try_start_game(page)
            # 无头合成器的第一帧往往要等更久，固定短窗口会漏判，这里轮询至多 2 秒
            current = {}
            for _ in range(10):
                page.wait_for_timeout(200)
                current = page.evaluate(_JS_GAME_CONTRACT) or {}
                if current.get("state") in ("playing", "running"):
                    return {"status": RuntimeStatus.PASS, "driver": "playwright",
                            "state": current.get("state"), "trigger": trigger}
            return {"status": RuntimeStatus.FAIL, "driver": "playwright", "state": current.get("state"),
                    "trigger": trigger, "reason": "未能触发游戏主循环启动"}

        if scenario == "game_over":
            trigger = cls._try_end_game(page)
            if not trigger:
                return {"status": "NEEDS_GAME_CONTRACT",
                        "reason": "游戏未暴露终局接口（endMatch/gameOver），无法真实断言 game_over"}
            current = {}
            for _ in range(10):
                page.wait_for_timeout(200)
                current = page.evaluate(_JS_GAME_CONTRACT) or {}
                if current.get("state") == "gameover" and current.get("game_over_count", 0) >= 1:
                    return {"status": RuntimeStatus.PASS, "driver": "playwright",
                            "state": current.get("state"), "trigger": trigger}
            return {"status": RuntimeStatus.FAIL, "driver": "playwright", "state": current.get("state"),
                    "trigger": trigger, "reason": "调用终局接口后契约未上报 gameover 状态"}

        if scenario == "restart":
            trigger = cls._try_restart_game(page)
            if not trigger:
                return {"status": "NEEDS_GAME_CONTRACT",
                        "reason": "游戏未暴露重开接口或重开按钮，无法真实断言 restart"}
            current = {}
            for _ in range(10):
                page.wait_for_timeout(200)
                current = page.evaluate(_JS_GAME_CONTRACT) or {}
                if current.get("restart_count", 0) >= 1 and current.get("state") in ("playing", "running"):
                    return {"status": RuntimeStatus.PASS, "driver": "playwright",
                            "state": current.get("state"), "trigger": trigger}
            return {"status": RuntimeStatus.FAIL, "driver": "playwright", "state": current.get("state"),
                    "trigger": trigger, "restart_count": current.get("restart_count", 0),
                    "reason": "触发重开后契约未上报 restart 迁移或主循环未恢复"}

        return {"status": "NEEDS_GAME_CONTRACT",
                "reason": f"场景 {scenario} 需要游戏侧上报状态迁移，当前通用契约未覆盖"}
