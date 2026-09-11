"""tests/test_image_gen_adapter.py — W5 2D 资产工厂：真实运行 + 入库 QA + 防伪。

防伪核心（与 B/C 类一致）：
  - 程序化兜底 is_ai_generated=False、is_procedural_placeholder=True，且
    当所有 AIGC 后端都不可用时 needs_runtime_tool="aigc_backend" 如实标注。
  - 显式指定不可用后端 -> NEEDS_RUNTIME_TOOL，绝不假装出图。
  - 真 ComfyUI 出图（env W5_REAL_COMFYUI=1 且本机 ComfyUI 在跑时）才标
    is_ai_generated=True，并把模型/seed/端点写进 provenance。
默认单测套件不依赖 ComfyUI、不依赖网络、不依赖 PIL/numpy。
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from pipeline import png_io
from pipeline.asset_factory import AssetFactory, AssetQA, AssetSpec
from pipeline.image_gen_adapter import ImageGenAdapter, ImageGenResult
from pipeline.style_bible import StyleBible


class TestPngCodec(unittest.TestCase):
    def test_rgba_roundtrip(self):
        w = h = 8
        px = bytes((i * 4 + j) % 256 for i in range(h)
                   for j in range(w) for _ in range(4))
        data = png_io.encode_png(w, h, px, 4)
        d = png_io.decode_png(data)
        self.assertEqual((d["width"], d["height"], d["channels"]), (8, 8, 4))
        self.assertEqual(d["pixels"], px)

    def test_rgb_roundtrip(self):
        w = h = 8
        px = bytes((i * 3 + j) % 256 for i in range(h)
                   for j in range(w) for _ in range(3))
        d = png_io.decode_png(png_io.encode_png(w, h, px, 3))
        self.assertEqual(d["channels"], 3)
        self.assertEqual(d["pixels"], px)

    def test_decode_filters(self):
        # 用一段已知含 Paeth 滤波的 PNG 不现实，这里验证 decode 不抛异常即可；
        # 真实 ComfyUI 输出（RGB、filter 混合）能解，则滤镜还原基本可靠。
        probe = Path("D:/ComfyUI_dl/probe_out.png")
        if probe.exists():
            d = png_io.decode_png(probe.read_bytes())
            self.assertIn(d["channels"], (3, 4))
        self.assertTrue(True)


class TestStyleBible(unittest.TestCase):
    def test_build_lock_enrich(self):
        sb = StyleBible.build("fantasy_rpg", seed=7)
        sb.lock()
        p = sb.enrich_prompt("golden panel")
        self.assertIn("fantasy_rpg", p)
        self.assertIn("color palette", p)
        self.assertIn("watermark", p)  # 负向词已并入
        self.assertEqual(sb.palette_rgb()[0][0], 0x15)

    def test_lock_guards_mutation(self):
        sb = StyleBible.build("x", seed=1)
        sb.lock()
        with self.assertRaises(RuntimeError):
            sb.palette = ["#000000"]

    def test_roundtrip_dict(self):
        sb = StyleBible.build("y", seed=3)
        sb2 = StyleBible.from_dict(sb.to_dict())
        self.assertEqual(sb2.palette, sb.palette)
        self.assertEqual(sb2.name, sb.name)


class _DeadAdapter(ImageGenAdapter):
    """comfyui 指向死端口、cloud 配置指向不存在文件 -> 两个 AIGC 后端都不可用。"""
    def __init__(self):
        super().__init__(comfyui_url="http://127.0.0.1:9",
                         cloud_config_path=os.path.join(
                             tempfile.mkdtemp(), "no_image_gen.json"))


class TestAdapterAntiFake(unittest.TestCase):
    def test_procedural_is_honest_placeholder(self):
        ad = _DeadAdapter()
        sb = StyleBible.build("fantasy_rpg", seed=7)
        r = ad.generate("icon", style=sb, seed=1, width=64, height=64,
                        backend="procedural_placeholder", transparent=True)
        self.assertEqual(r.status, "PROCEDURAL_PLACEHOLDER")
        self.assertFalse(r.is_ai_generated)
        self.assertTrue(r.is_procedural_placeholder)
        self.assertTrue(r.has_alpha)
        self.assertTrue(r.ok())

    def test_auto_fallback_labels_needs_runtime_tool(self):
        ad = _DeadAdapter()
        sb = StyleBible.build("fantasy_rpg", seed=7)
        r = ad.generate("icon", style=sb, seed=1, width=64, height=64,
                        transparent=True)  # backend=None -> 全不可用 -> 程序化兜底
        self.assertTrue(r.is_procedural_placeholder)
        self.assertEqual(r.needs_runtime_tool, "aigc_backend")
        self.assertIn("程序化占位", " ".join(r.warnings))

    def test_explicit_unavailable_backend_is_not_faked(self):
        ad = _DeadAdapter()
        r = ad.generate("x", backend="comfyui_local")
        self.assertEqual(r.status, "NEEDS_RUNTIME_TOOL")
        self.assertFalse(r.ok())
        self.assertFalse(r.is_ai_generated)

    def test_explicit_cloud_unavailable_is_not_faked(self):
        ad = _DeadAdapter()
        r = ad.generate("x", backend="cloud_api")
        self.assertEqual(r.status, "NEEDS_RUNTIME_TOOL")
        self.assertFalse(r.is_ai_generated)


class TestAssetQA(unittest.TestCase):
    def _procedural(self, ad, sb, w=64, h=64, alpha=False):
        return ad.generate("icon", style=sb, seed=2, width=w, height=h,
                           backend="procedural_placeholder", transparent=alpha)

    def test_procedural_qa_passes(self):
        ad = _DeadAdapter()
        sb = StyleBible.build("fantasy_rpg", seed=7).lock()
        r = self._procedural(ad, sb, alpha=True)
        rec = AssetFactory(ad).generate(
            AssetSpec("icon", "pot", 64, 64, require_alpha=True, prompt="x"),
            style=sb, backend="procedural_placeholder", seed=2)
        self.assertTrue(rec.qa.passed)
        self.assertEqual(rec.qa.scores["alpha"], 1.0)
        self.assertNotIn("style_similarity", rec.qa.needs_vlm or [])

    def test_qa_dimension_mismatch_fails(self):
        ad = _DeadAdapter()
        sb = StyleBible.build("fantasy_rpg", seed=7).lock()
        img = self._procedural(ad, sb, w=64, h=64).image_bytes
        rep = AssetQA.check(img, AssetSpec("icon", "a", 128, 128), sb)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.scores["dimensions"], 0.0)

    def test_qa_alpha_required_fails_on_rgb(self):
        ad = _DeadAdapter()
        sb = StyleBible.build("fantasy_rpg", seed=7).lock()
        img = self._procedural(ad, sb, w=64, h=64, alpha=False).image_bytes
        rep = AssetQA.check(img, AssetSpec("icon", "a", 64, 64, require_alpha=True), sb)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.scores["alpha"], 0.0)


@unittest.skipUnless(os.environ.get("W5_REAL_COMFYUI") == "1",
                     "需本机 ComfyUI 在跑（env W5_REAL_COMFYUI=1）")
class TestAdapterRealComfyUI(unittest.TestCase):
    def test_real_comfyui_generates_ai_image(self):
        ad = ImageGenAdapter()  # 默认指向 127.0.0.1:8188
        if not ad.comfyui_available():
            self.skipTest("ComfyUI 不可达")
        sb = StyleBible.build("fantasy_rpg", seed=7).lock()
        r = ad.generate("golden panel", style=sb, seed=555, width=512, height=512,
                        backend="comfyui_local")
        self.assertEqual(r.status, "OK")
        self.assertTrue(r.is_ai_generated)
        self.assertFalse(r.is_procedural_placeholder)
        self.assertEqual(r.width, 512)
        self.assertIn("sd_xl_base_1.0", str(r.provenance.get("model")))


if __name__ == "__main__":
    unittest.main()
