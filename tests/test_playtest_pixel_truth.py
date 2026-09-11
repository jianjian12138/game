#!/usr/bin/env python3
"""test_playtest_pixel_truth.py — 试玩引擎防伪回归（真实像素 + 真实输入响应）。

验证 13.2 红线的具体落地：帧数在涨 ≠ 画面在动。
  - 真实游戏：canvas 采样到非空白像素 + 驱动输入前后像素哈希确有变化 → PASS。
  - 空转壳子（canvas 存在、rAF 自增、state 被契约自动置 playing，但从不绘制、忽略输入）→ FAIL。
无真实浏览器自动化驱动时整组 skip（不污染无头 CI）。
"""
from __future__ import annotations

import textwrap
import tempfile
from pathlib import Path

from core.runtime_adapter import RuntimeStatus

try:
    from pipeline.browser_runtime_adapter import BrowserRuntimeAdapter
    _HAS_DRIVER = BrowserRuntimeAdapter().preflight().get("can_launch")
except Exception:
    _HAS_DRIVER = False

from pipeline.playtest_engine import PlaytestEngine

ROOT = Path(__file__).resolve().parent.parent
REAL_PKG = ROOT / "output" / "autonomous" / "run_00059cbea77652219563" / "package" / "index.html"

# 空转壳子：canvas 存在 + rAF 空转（契约自动置 playing），但从不绘制、忽略键盘。
_EMPTY_FAKE = textwrap.dedent("""
<!DOCTYPE html><html lang="zh"><head>
<script>
(function () {
  if (window.__GAME_AGENT__) { return; }
  var A = { ready:false, state:'boot', frame:0, ticks:0, errors:[], triangles:null, draw_calls:null, game_over_count:0, restart_count:0 };
  window.__GAME_AGENT__ = A;
  function markRunning(){ if (A.state==='boot'||A.state==='menu'){ A.state='playing'; } }
  A.markGameOver=function(){ A.state='gameover'; A.game_over_count+=1; };
  A.markRestart=function(){ A.restart_count+=1; A.state='boot'; A.frame=0; A.ticks=0; };
  var raf = window.requestAnimationFrame ? window.requestAnimationFrame.bind(window) : null;
  if (raf){ window.requestAnimationFrame=function(cb){ return raf(function(t){ A.frame+=1; markRunning(); return cb(t); }); }; }
  window.addEventListener('error', function(e){ A.errors.push(String((e&&e.message)||e)); });
  window.addEventListener('load', function(){ A.ready=true; });
})();
</script><meta charset="utf-8"></head>
<body><canvas id="game" width="960" height="540"></canvas>
<script>"use strict"; function loop(){ requestAnimationFrame(loop); } requestAnimationFrame(loop);</script>
</body></html>
""")


def _write_tmp(html: str) -> Path:
    # 写到系统 temp（delete=False）：playtest 引擎按路径静态托管即可；
    # 不主动 unlink，避免触发环境 safe-delete 批量删除护栏。
    tf = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     prefix="playtest_fake_")
    tf.write(html)
    tf.close()
    return Path(tf.name)


class TestPlaytestPixelTruth:
    def test_real_package_passes_with_pixel_and_input_truth(self):
        if not _HAS_DRIVER:
            import pytest
            pytest.skip("无真实浏览器自动化驱动，跳过真实试玩")
        if not REAL_PKG.exists():
            import pytest
            pytest.skip("真实出货包缺失，跳过")
        r = PlaytestEngine(seed=42, evidence_dir="output/playtest").run(
            str(REAL_PKG), episodes=2, play_seconds=3.0, seed=42)
        assert r.status == RuntimeStatus.PASS, r.error
        assert r.episodes_reached_playing >= 1
        # 防伪核心：不是「帧数在涨」就 PASS，必须真采样到渲染像素 + 输入响应
        assert r.pixel_rendered_count >= 1, "真实游戏必须采样到非空白像素"
        assert r.input_reflected_count >= 1, "真实游戏驱动输入后画面必须确有变化"
        # 抽样检查逐轮证据字段
        for ep in r.episodes:
            assert ep["pixel_rendered"] is True
            assert ep["pixel_nonzero"] > 0
            assert ep["input_reflected"] is True
            assert ep["pixel_before_hash"] != ep["pixel_after_hash"]

    def test_empty_fake_canvas_fails_pixel_truth(self):
        if not _HAS_DRIVER:
            import pytest
            pytest.skip("无真实浏览器自动化驱动，跳过真实试玩")
        fake = _write_tmp(_EMPTY_FAKE)
        r = PlaytestEngine(seed=7, evidence_dir="output/playtest").run(
            str(fake), episodes=2, play_seconds=2.0, seed=7)
        # 关键：空转壳子即使 state=playing、frame 在涨，也不得 PASS
        assert r.status == RuntimeStatus.FAIL
        assert r.pixel_rendered_count == 0, "空转壳子不应采样到非空白像素"
        assert "画面" in (r.error or ""), f"失败原因应点名画面未渲染: {r.error}"
        # 临时文件写在系统 temp，不主动删除（避免触发 safe-delete 护栏）；由 OS 临时清理

    def test_js_canvas_pixels_helper_contract(self):
        # 单元级：辅助函数能被导入且为字符串
        from pipeline.browser_runtime_adapter import _JS_CANVAS_PIXELS
        assert isinstance(_JS_CANVAS_PIXELS, str)
        assert "getImageData" in _JS_CANVAS_PIXELS
        assert "toDataURL" in _JS_CANVAS_PIXELS
