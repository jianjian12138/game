#!/usr/bin/env python3
"""visual_diff_engine P0 修复回归测试（评审 R1/R3/R5/R10）。

覆盖：
- 真像素直方图（替代压缩字节代理，R1）
- 损坏/非法 PNG 诚实返回不崩溃（R10）
- 无基准 → DEGRADED 诚实门禁（R5，不再谎报 PASS）
- seed → diff 闭环默认比对 target 基准帧（R3）
- 无生图后端 → NEEDS_RUNTIME_TOOL 诚实降级
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import png_io
from pipeline.visual_diff_engine import (
    VisualDiffEngine, compute_rgb_histogram, read_png_dimensions,
)


class VisualDiffEngineP0Test(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vde_p0_"))
        px_dark = bytes((10, 10, 10, 255) * (16 * 16))
        px_bright = bytes((240, 240, 240, 255) * (16 * 16))
        self.dark = self.tmp / "dark.png"
        self.bright = self.tmp / "bright.png"
        self.dark.write_bytes(png_io.encode_png(16, 16, px_dark, 4))
        self.bright.write_bytes(png_io.encode_png(16, 16, px_bright, 4))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_pixel_histogram_distinguishes_dark_bright(self):
        sd = compute_rgb_histogram(self.dark)
        sb = compute_rgb_histogram(self.bright)
        self.assertEqual(sd["status"], "SUCCESS")
        self.assertEqual(sb["status"], "SUCCESS")
        self.assertGreater(sd["dark_ratio"], 0.9)
        self.assertLess(sb["dark_ratio"], 0.1)
        self.assertEqual(read_png_dimensions(self.dark), (16, 16))

    def test_corrupt_png_returns_error_not_crash(self):
        bad = self.tmp / "bad.png"
        bad.write_bytes(b"not a png at all")
        res = compute_rgb_histogram(bad)
        self.assertIn(res["status"], ("DECODE_ERROR", "FILE_NOT_FOUND"))

    def test_audit_without_golden_is_degraded(self):
        eng = VisualDiffEngine(self.tmp)
        res = eng.audit_capture_vs_ground_truth(self.dark)
        self.assertEqual(res["status"], "DEGRADED")

    def test_seed_then_diff_closes_loop(self):
        eng = VisualDiffEngine(self.tmp)
        eng.seed_golden_frame(self.dark, name="target")
        self.assertEqual(eng.audit_capture_vs_ground_truth(self.dark)["status"], "PASS")
        self.assertEqual(eng.audit_capture_vs_ground_truth(self.bright)["status"], "WARN")

    def test_generate_without_backend_is_honest(self):
        eng = VisualDiffEngine(self.tmp)
        g = eng.generate_target_image("a cozy cafe game", name="target")
        self.assertEqual(g["status"], "NEEDS_RUNTIME_TOOL")


if __name__ == "__main__":
    unittest.main()
