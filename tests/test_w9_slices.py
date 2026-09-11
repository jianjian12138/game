"""tests/test_w9_slices.py — W9 八垂直切片端到端验证（真实生成 + 诚实防粉饰）。

防伪核心（与 W5/W6/W7/W8 一致，红线 13.2）：
  - 切片原型由 slice_prototyper 确定性生成（不依赖 LLM/网络/浏览器），且真正注入运行时契约；
    验证「生成成功」≠「通过」——必须通过 W8 PlaytestEngine 在真实浏览器跑通才算 PASS。
  - 无真实浏览器驱动时，每片 status=NEEDS_RUNTIME_TOOL，绝不把「HTML 存在」粉饰成通过。
  - 默认单测不依赖真实浏览器：用 monkeypatch 强制「无驱动」稳定验证诚实门禁，
    并验证规格目录真实锚定本仓库 part_*（数清楚再声称）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from core.runtime_adapter import RuntimeStatus
from pipeline import playtest_engine as pe
from pipeline.browser_runtime_adapter import BrowserRuntimeAdapter
from pipeline.vertical_slices import VERTICAL_SLICES, get_slice, all_slice_ids

ROOT = Path(__file__).resolve().parent.parent

# 真实零件映射：每个切片锚定的 part_* 必须能在 ford_t_game_parts_hub.py 找到
PARTS_HUB = ROOT / "core" / "ford_t_game_parts_hub.py"


def _force_no_driver():
    BrowserRuntimeAdapter._load_driver = staticmethod(
        lambda: (None, "forced no-driver in test"))


class TestSliceSpecsRealInventory(unittest.TestCase):
    """规格必须真实锚定本仓库零件（Count before claiming）。"""

    def test_eight_slices_defined(self):
        self.assertEqual(len(VERTICAL_SLICES), 8)

    def test_all_slice_ids_unique(self):
        self.assertEqual(len(set(all_slice_ids())), 8)

    def test_parts_exist_in_hub(self):
        self.assertTrue(PARTS_HUB.exists(), "ford_t_game_parts_hub.py 必须存在")
        hub = PARTS_HUB.read_text(encoding="utf-8")
        for s in VERTICAL_SLICES:
            for pid in s.parts:
                self.assertIn(
                    f'"{pid}"', hub,
                    f"切片 {s.id} 锚定的零件 {pid} 未在 ford_t_game_parts_hub.py 找到")


class TestSlicePrototyperDeterministic(unittest.TestCase):
    """原型生成确定性 + 契约真实注入（不依赖浏览器）。"""

    def test_generate_html_has_contract_and_canvas(self):
        from pipeline.slice_prototyper import generate_slice_html
        html = generate_slice_html(VERTICAL_SLICES[0])
        self.assertIn("game-agent-runtime-contract:v1", html)
        self.assertIn('<canvas id="game"', html)
        self.assertIn("window.GameApp", html)

    def test_generate_is_deterministic(self):
        from pipeline.slice_prototyper import generate_slice_html
        a = generate_slice_html(VERTICAL_SLICES[1])
        b = generate_slice_html(VERTICAL_SLICES[1])
        self.assertEqual(a, b)

    def test_genre_branches_distinct_html(self):
        from pipeline.slice_prototyper import generate_slice_html
        a = generate_slice_html(VERTICAL_SLICES[0])
        b = generate_slice_html(VERTICAL_SLICES[2])
        self.assertNotEqual(a, b)


class TestSliceFailClosed(unittest.TestCase):
    """核心防伪：无驱动时，每片诚实返回 NEEDS_RUNTIME_TOOL，绝不 PASS。"""

    def setUp(self):
        self._orig = BrowserRuntimeAdapter._load_driver
        _force_no_driver()

    def tearDown(self):
        BrowserRuntimeAdapter._load_driver = self._orig

    def test_single_slice_no_driver_is_needs_runtime_tool(self):
        from pipeline.vertical_slice_validator import validate_slice
        r = validate_slice(VERTICAL_SLICES[0], episodes=1, play_seconds=1.0, seed=1)
        self.assertEqual(r.status, RuntimeStatus.NEEDS_RUNTIME_TOOL)
        self.assertEqual(r.needs_runtime_tool, "browser_runtime")
        # 即便无驱动，HTML 与 W7 音频资产仍真实生成（诚实：产物存在，只是试玩未跑）
        self.assertTrue(r.assets.get("html"))

    def test_all_slices_no_driver_honest_report(self):
        from pipeline.vertical_slice_validator import validate_all
        # 写入独立临时报告，避免覆盖权威聚合报告 vertical_slices_report.json
        tmp = str(ROOT / "output" / "slices" / "report.nodriver.json")
        report = validate_all(episodes=1, play_seconds=1.0, seed=1, attach_audio=False,
                              report_path=tmp)
        self.assertEqual(report["total"], 8)
        for s in report["slices"]:
            self.assertEqual(s["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)
        self.assertEqual(report["failed"], 0)


class TestVerticalSlicesCLI(unittest.TestCase):
    """CLI 入口结构行为（不依赖真实浏览器）。"""

    def _run_cli(self, *cli_args):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "game_agent", "vertical-slices", *cli_args],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180, env=env)

    def test_cli_unknown_slice_exit2(self):
        proc = self._run_cli("--slice", "does_not_exist")
        self.assertEqual(proc.returncode, 2)

    def test_cli_no_audio_flag_accepted(self):
        # 验证参数被接受、命令进入执行并产生报告；退出码依赖环境是否装了真实浏览器
        # （有驱动→PASS=0；无驱动→NEEDS_RUNTIME_TOOL=4），两种都属诚实出口
        proc = self._run_cli("--no-audio", "--slice", all_slice_ids()[0])
        self.assertIn("VSLICES", proc.stdout)
        self.assertIn(proc.returncode, (0, 4))


@unittest.skipUnless(os.environ.get("W9_REAL_BROWSER") == "1",
                     "需要真实浏览器（W9_REAL_BROWSER=1）")
class TestW9RealSlices(unittest.TestCase):
    """真实浏览器端到端：生成→接W7音频→W8试玩→诚实 verdict + 证据。"""

    def test_all_eight_slices_pass_with_evidence(self):
        from pipeline.vertical_slice_validator import validate_all
        report = validate_all(episodes=2, play_seconds=3.0, seed=42, attach_audio=True)
        self.assertEqual(report["total"], 8)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["needs_runtime_tool"], 0)
        for s in report["slices"]:
            self.assertEqual(s["status"], RuntimeStatus.PASS)
            self.assertGreaterEqual(s["episodes_reached_playing"], 1)
            # 防伪核心（13.2）：每片都必须真采样到渲染像素 + 输入响应，不能只数帧数
            self.assertGreaterEqual(s["pixel_rendered_count"], 1,
                                    f"切片 {s['slice_id']} 必须采样到非空白像素")
            self.assertGreaterEqual(s["input_reflected_count"], 1,
                                    f"切片 {s['slice_id']} 驱动输入后画面必须确有变化")
            self.assertGreater(s["total_frames"], 0)
            self.assertEqual(s["page_error_count"], 0)
            self.assertTrue(s["evidence_path"])
            epath = Path(s["evidence_path"])
            self.assertTrue(epath.exists(), f"证据缺失: {s['slice_id']}")
            data = json.loads(epath.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], RuntimeStatus.PASS)
            # 诚实：每片都真实暴露 endMatch/restartMatch，故 game_over/restart 如实为 True
            self.assertTrue(s["game_over_supported"])
            self.assertTrue(s["restart_supported"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
