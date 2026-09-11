"""游戏运行时观测契约（单一真理源）。

生成的游戏页面必须暴露 window.__GAME_AGENT__，运行时适配器才能断言
「游戏真的在跑」，而不是靠 HTML 里有没有 canvas 字样去猜。

契约字段：
    ready      页面 load 完成
    state      boot -> playing -> gameover（由真实用户输入与游戏侧上报驱动）
    frame      主循环帧计数（包装 requestAnimationFrame 得到，非估算）
    errors     页面未捕获错误与 Promise 拒绝
    triangles / draw_calls   3D 渲染统计（仅 3D 展台由渲染器上报）
    game_over_count / restart_count   游戏侧显式上报的终局与重开次数
"""
from __future__ import annotations

import re
from typing import Any, Dict

CONTRACT_NAME = "__GAME_AGENT__"
# 幂等判定必须用独立标记：页面自身代码里出现 __GAME_AGENT__ 字样（比如上报渲染统计）
# 并不代表契约已注入，用契约名做判断会把这类页面全部跳过。
CONTRACT_MARKER = "/* game-agent-runtime-contract:v1 */"

_SNIPPET = """<script>
/* game-agent-runtime-contract:v1 */
(function () {
  if (window.__GAME_AGENT__) { return; }
  var A = { ready: false, state: 'boot', frame: 0, ticks: 0, errors: [], triangles: null, draw_calls: null,
            game_over_count: 0, restart_count: 0 };
  window.__GAME_AGENT__ = A;

  // state 必须由「主循环真的启动」来驱动，绝不能因为检测到一次按键就宣称游戏已开始
  function markRunning() { if (A.state === 'boot' || A.state === 'menu') { A.state = 'playing'; } }

  // 终局与重开必须由游戏侧显式上报：适配器无法靠通用输入可靠触发死亡，
  // 也不能靠「页面上有 Game Over 字样」去猜——那是伪证。
  A.markGameOver = function () { A.state = 'gameover'; A.game_over_count += 1; };
  A.markRestart = function () { A.restart_count += 1; A.state = 'boot'; A.frame = 0; A.ticks = 0; };

  var raf = window.requestAnimationFrame ? window.requestAnimationFrame.bind(window) : null;
  if (raf) {
    window.requestAnimationFrame = function (cb) {
      return raf(function (t) { A.frame += 1; markRunning(); return cb(t); });
    };
  }

  // 相当多模板用 setInterval 驱动固定步长主循环，只统计 rAF 会把它们误判成没在跑
  var si = window.setInterval ? window.setInterval.bind(window) : null;
  if (si) {
    window.setInterval = function (fn, ms, a, b, c) {
      return si(function () { A.ticks += 1; markRunning(); return fn.apply(this, arguments); }, ms, a, b, c);
    };
  }

  window.addEventListener('error', function (e) { A.errors.push(String((e && e.message) || e)); });
  window.addEventListener('unhandledrejection', function (e) { A.errors.push('unhandledrejection'); });

  window.addEventListener('load', function () { A.ready = true; });
  if (document.readyState === 'complete') { A.ready = true; }
})();
</script>
"""


def inject_runtime_contract(html: str) -> str:
    """把运行时契约注入到页面；已注入过则原样返回。

    必须注入到 <head> 最前面：契约靠包装 requestAnimationFrame / setInterval 来观察主循环，
    若在游戏脚本之后才注入，包装就永远拦截不到已经注册好的循环。
    """
    if not html or CONTRACT_MARKER in html:
        return html
    match = re.search(r"<head[^>]*>", html, flags=re.IGNORECASE)
    if match:
        pos = match.end()
        return html[:pos] + "\n" + _SNIPPET + html[pos:]
    lowered = html.lower()
    idx = lowered.rfind("</body>")
    if idx == -1:
        return html + "\n" + _SNIPPET
    return html[:idx] + _SNIPPET + html[idx:]


def empty_contract() -> Dict[str, Any]:
    """契约的初始形态，供文档与测试对照。"""
    return {
        "ready": False,
        "state": "boot",
        "frame": 0,
        "ticks": 0,
        "errors": [],
        "triangles": None,
        "draw_calls": None,
        "game_over_count": 0,
        "restart_count": 0,
    }


__all__ = ["CONTRACT_NAME", "CONTRACT_MARKER", "inject_runtime_contract", "empty_contract"]
