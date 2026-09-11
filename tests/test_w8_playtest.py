"""tests/test_w8_playtest.py — W8 自动试玩闭环（真实驱动 + 诚实防粉饰）。

防伪核心（与 W5/W6/W7 一致，红线 13.2）：
  - 没有任何真实浏览器自动化驱动时，引擎一律 NEEDS_RUNTIME_TOOL，绝不把
    「HTML 有 canvas / 文件存在」粉饰为通过。这是本测试文件首要断言。
  - 即使目标是一个完美的、含运行时契约的真实游戏，只要没有驱动，verdict 也绝不 PASS。
  - 真实浏览器闭环（boot→start→驱动输入→采样帧→尝试 game_over/restart 闭合）只在
    环境变量 W8_REAL_BROWSER=1 时运行（需本机已装 Playwright + 浏览器），避免默认 CI 依赖 GUI。
  - 默认单测不依赖网络、不依赖 GUI、不依赖真实浏览器；用 monkeypatch 强制「无驱动」来稳定验证诚实门禁。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.runtime_adapter import RuntimeStatus
from pipeline import playtest_engine as pe
from pipeline.browser_runtime_adapter import BrowserRuntimeAdapter

ROOT = Path(__file__).resolve().parent.parent
GAME_TARGET = ROOT / "output" / "runs" / "run_b6c2573f8c56c02f8a45" / "index.html"


def _force_no_driver():
    """强制「无真实浏览器驱动」以稳定验证诚实门禁（不真正启动浏览器）。"""
    BrowserRuntimeAdapter._load_driver = staticmethod(
        lambda: (None, "forced no-driver in test"))


class TestPlaytestFailClosed(unittest.TestCase):
    """核心防伪：没有真实驱动时，任何目标都绝不 PASS。"""

    def setUp(self):
        self._orig = BrowserRuntimeAdapter._load_driver
        _force_no_driver()

    def tearDown(self):
        BrowserRuntimeAdapter._load_driver = self._orig

    def test_no_driver_returns_needs_runtime_tool(self):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write("<html><body>static page, no canvas</body></html>")
            tpath = f.name
        try:
            res = pe.PlaytestEngine(seed=1).run(
                tpath, episodes=1, play_seconds=1.0, seed=1)
            self.assertEqual(res.status, RuntimeStatus.NEEDS_RUNTIME_TOOL)
            self.assertEqual(res.needs_runtime_tool, "browser_runtime")
            self.assertTrue(res.error)
        finally:
            os.unlink(tpath)

    def test_missing_target_reports_error_not_pass(self):
        res = pe.PlaytestEngine(seed=1).run(
            str(ROOT / "output" / "does_not_exist_xyz.html"),
            episodes=1, play_seconds=1.0, seed=1)
        self.assertEqual(res.status, RuntimeStatus.FAIL)
        self.assertIn("试玩目标不存在", res.error)

    def test_never_passes_without_driver_even_for_real_game(self):
        # 最关键断言：即便目标是一个含运行时契约的真实游戏，无驱动也绝不 PASS
        if not GAME_TARGET.exists():
            self.skipTest("真实游戏目标不存在")
        res = pe.PlaytestEngine(seed=1).run(
            str(GAME_TARGET), episodes=1, play_seconds=1.0, seed=1)
        self.assertNotEqual(res.status, RuntimeStatus.PASS)
        self.assertEqual(res.needs_runtime_tool, "browser_runtime")


class TestPlaytestResultShape(unittest.TestCase):
    """数据契约完整性：verdict / EvidencePack 字段齐全。"""

    def test_result_to_dict_keys(self):
        r = pe.PlaytestResult(status=RuntimeStatus.FAIL, target="x",
                              target_hash="sha256:none")
        d = r.to_dict()
        for k in ("status", "target", "target_hash", "episodes_planned",
                  "episodes_run", "episodes_reached_playing",
                  "full_loops_completed", "game_over_supported",
                  "restart_supported", "total_frames", "console_error_count",
                  "page_error_count", "network_failure_count",
                  "needs_runtime_tool", "episodes", "console_errors",
                  "failed_requests", "evidence_path", "error"):
            self.assertIn(k, d)

    def test_episode_to_dict_keys(self):
        ep = pe.EpisodeRecord(episode=0)
        ed = ep.to_dict()
        for k in ("episode", "boot_status", "canvas", "start_triggered",
                  "reached_playing", "frames_before", "frames_after",
                  "frames_advanced", "inputs_sent", "end_triggered",
                  "game_over_reached", "restart_triggered", "restart_reached",
                  "page_errors"):
            self.assertIn(k, ed)


class TestPlaytestCLI(unittest.TestCase):
    """CLI 入口结构行为（不依赖真实浏览器）。"""

    def _run_cli(self, *cli_args):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "game_agent", "playtest", *cli_args],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120, env=env)

    def test_cli_missing_target_exit2(self):
        proc = self._run_cli()
        self.assertEqual(proc.returncode, 2)

    def test_cli_remote_url_exit3(self):
        proc = self._run_cli("--target", "https://example.com/game.html")
        self.assertEqual(proc.returncode, 3)

    @unittest.skipUnless(os.environ.get("W8_REAL_BROWSER") == "1",
                         "需要真实浏览器（W8_REAL_BROWSER=1）")
    def test_cli_real_target_pass(self):
        if not GAME_TARGET.exists():
            self.skipTest("真实游戏目标不存在")
        proc = self._run_cli("--target", str(GAME_TARGET), "--episodes", "2",
                             "--ticks", "20", "--seed", "42")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("[VERDICT] PASS", proc.stdout)


@unittest.skipUnless(os.environ.get("W8_REAL_BROWSER") == "1",
                     "需要真实浏览器（W8_REAL_BROWSER=1）")
class TestW8RealPlaytest(unittest.TestCase):
    """真实浏览器闭环：boot→start→驱动→采样→尝试 game_over/restart 闭合 + 证据落盘。"""

    def test_real_engine_pass_with_evidence(self):
        if not GAME_TARGET.exists():
            self.skipTest("真实游戏目标不存在")
        res = pe.PlaytestEngine(seed=42).run(
            str(GAME_TARGET), episodes=2, play_seconds=3.0, seed=42)
        self.assertEqual(res.status, RuntimeStatus.PASS)
        self.assertGreaterEqual(res.episodes_reached_playing, 1)
        # 防伪核心（13.2）：不能只数帧数就 PASS，必须真采样到渲染像素 + 输入响应
        self.assertGreaterEqual(res.pixel_rendered_count, 1,
                                "真实游戏必须采样到非空白像素（帧数涨≠画面在动）")
        self.assertGreaterEqual(res.input_reflected_count, 1,
                                "真实游戏驱动输入后画面必须确有变化（输入真生效）")
        self.assertGreater(res.total_frames, 0)
        self.assertEqual(res.page_error_count, 0)
        self.assertTrue(res.evidence_path)
        epath = Path(res.evidence_path)
        self.assertTrue(epath.exists())
        data = json.loads(epath.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], RuntimeStatus.PASS)
        self.assertEqual(data["target_hash"], res.target_hash)
        # 诚实：未暴露 restartMatch 接口的游戏，restart 如实为 False，不伪造闭环
        self.assertFalse(res.restart_supported)


if __name__ == "__main__":
    unittest.main(verbosity=2)
