"""tests/test_w6_3d_assets.py — W6 贴图 3D 资产 + M4 真机导入（诚实防粉饰）。

防伪核心（与 B/C 类、W5 一致）：
  - 五通道贴图均为真实生成的 PNG 字节，可独立解码/哈希/校验。
  - albedo 走 AI（真出图才标 is_ai_generated）或程序化兜底（明确标
    is_procedural_placeholder 且 needs_runtime_tool="aigc_backend"），
    绝不把程序化 PNG 粉饰成 AI 美术。
  - glTF 以相对 uri 真实引用贴图，glTF/PBR 结构校验必须真通过。
  - M4 真机导入由 GodotImporter 在真 Godot 4.7.2 中执行，仅当日志出现
    [DONE] import 且无 ERROR: 才判定成功；Godot 缺失则诚实报 needs_runtime_tool。
  - 默认单测不依赖 Godot、不依赖 ComfyUI、不依赖网络、不依赖 PIL/numpy。
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from pipeline.asset_3d_bridge import Mesh3D, Asset3DBridge
from pipeline.textured_3d_asset import TexturedAssetBuilder
from pipeline import png_io
from pipeline.gltf_validator import validate_gltf
from pipeline.pbr_validator import validate_pbr


class TestUVGeometry(unittest.TestCase):
    """UV 必须非退化且在 [0,1]，否则贴图无法映射（W6 真实缺口之一）。"""

    def test_textured_uvs_are_non_degenerate_and_in_range(self):
        mesh = TexturedAssetBuilder.build_textured_defense_turret()
        self.assertGreater(len(mesh.uvs) // 2, 0)
        uvs = [(mesh.uvs[i], mesh.uvs[i + 1]) for i in range(0, len(mesh.uvs), 2)]
        # 不能全部是 (0,0) 退化
        self.assertTrue(any((u != 0.0 or v != 0.0) for u, v in uvs))
        # 必须落在 [0,1]
        for u, v in uvs:
            self.assertTrue(0.0 <= u <= 1.0 and 0.0 <= v <= 1.0, (u, v))
        # UV 顶点数必须等于几何顶点数
        self.assertEqual(len(uvs), len(mesh.positions) // 3)

    def test_legacy_add_box_uv_unchanged_degenerate_by_design(self):
        """确认 M3 旧 add_box 仍保持退化 UV（向后兼容，不意外改动）。"""
        m = Mesh3D(name="legacy")
        m.add_box(0, 0, 0, 1, 1, 1)
        self.assertEqual(
            {(m.uvs[i], m.uvs[i + 1]) for i in range(0, len(m.uvs), 2)},
            {(0.0, 0.0)},
        )


class TestTexturedGltfEmbedding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_build_writes_five_pngs_and_references_them(self):
        rec = TexturedAssetBuilder.build(
            "turret", output_dir=self.tmp,
            backend="procedural_placeholder", verify_godot=False)
        self.assertEqual(rec.status, "success")
        for ch in ("albedo", "normal", "metallicRoughness", "ao", "emissive"):
            self.assertIn(ch, rec.texture_paths)
            self.assertTrue(Path(rec.texture_paths[ch]).exists(), f"{ch} 文件缺失")
        gltf = json.loads(Path(rec.gltf_path).read_text(encoding="utf-8"))
        imgs = {im["name"]: im["uri"] for im in gltf.get("images", [])}
        for ch in ("albedo", "normal", "metallicRoughness", "ao", "emissive"):
            self.assertIn(ch, imgs, f"images 缺少 {ch}")
            self.assertTrue(Path(self.tmp, imgs[ch]).exists(),
                            f"{ch} uri 指向的文件不存在: {imgs[ch]}")
        # 材质真实引用五通道贴图
        mat = gltf["materials"][0]
        self.assertIn("baseColorTexture", mat["pbrMetallicRoughness"])
        self.assertIn("metallicRoughnessTexture", mat["pbrMetallicRoughness"])
        self.assertIn("normalTexture", mat)
        self.assertIn("occlusionTexture", mat)
        self.assertIn("emissiveTexture", mat)

    def test_gltf_and_pbr_validators_pass(self):
        rec = TexturedAssetBuilder.build(
            "turret", output_dir=self.tmp, backend="procedural_placeholder")
        rep = validate_gltf(rec.gltf_path)
        self.assertTrue(rep["valid"], rep["errors"])
        pbr = validate_pbr(rec.gltf_path)
        self.assertTrue(pbr["valid"], pbr.get("errors"))

    def test_procedural_albedo_is_honest(self):
        rec = TexturedAssetBuilder.build(
            "turret", output_dir=self.tmp, backend="procedural_placeholder")
        self.assertTrue(rec.is_procedural_albedo)
        self.assertFalse(rec.is_ai_albedo)
        # 程序化兜底且本机无 AIGC 后端时，必须诚实标注
        adapter_has_backend = bool(rec.albedo_needs_runtime_tool is None)
        if not adapter_has_backend:
            self.assertEqual(rec.albedo_needs_runtime_tool, "aigc_backend")
        # albedo 是真实有效 PNG（RGB）
        d = png_io.decode_png(Path(rec.texture_paths["albedo"]).read_bytes())
        self.assertEqual(d["channels"], 3)
        self.assertEqual(d["width"], rec.resolution)

    def test_godot_import_not_triggered_by_default(self):
        rec = TexturedAssetBuilder.build(
            "turret", output_dir=self.tmp,
            backend="procedural_placeholder", verify_godot=False)
        self.assertIsNone(rec.m4_achieved)
        self.assertEqual(rec.godot, {})

    def test_all_four_asset_types_build(self):
        for at in ("turret", "mech", "crate", "crystal"):
            rec = TexturedAssetBuilder.build(
                at, output_dir=self.tmp, backend="procedural_placeholder")
            self.assertEqual(rec.status, "success", at)
            self.assertTrue(Path(rec.gltf_path).exists(), at)


class TestM3BackwardCompat(unittest.TestCase):
    def test_build_procedural_asset_still_works(self):
        res = Asset3DBridge.build_procedural_asset(
            "turret", output_dir=Path(tempfile.mkdtemp()))
        self.assertEqual(res["status"], "success")
        self.assertTrue(Path(res["gltf_path"]).exists())
        self.assertTrue(Path(res["obj_path"]).exists())


@unittest.skipUnless(os.environ.get("W6_REAL_GODOT") == "1",
                     "需本机 Godot 4.7.2（env W6_REAL_GODOT=1）")
class TestGodotRealImport(unittest.TestCase):
    """M4 真机证据：在真 Godot 4.7.2 中导入贴图 glTF。"""

    def test_m4_godot_import_succeeds(self):
        rec = TexturedAssetBuilder.build(
            "turret", output_dir=tempfile.mkdtemp(),
            backend="procedural_placeholder", verify_godot=True)
        self.assertIsNotNone(rec.m4_achieved)
        self.assertTrue(rec.m4_achieved, rec.godot.get("error"))
        self.assertGreater(len(rec.godot.get("imported_files", [])), 0)


@unittest.skipUnless(os.environ.get("W6_REAL_COMFYUI") == "1",
                     "需本机 ComfyUI 在跑（env W6_REAL_COMFYUI=1）")
class TestAIAlbedoRealComfyUI(unittest.TestCase):
    """W6 AI albedo 真实出图路径（仅本机 ComfyUI 在跑时执行）。"""

    def test_ai_albedo_generated(self):
        rec = TexturedAssetBuilder.build(
            "turret", output_dir=tempfile.mkdtemp(),
            verify_godot=False, resolution=512)
        self.assertTrue(rec.is_ai_albedo, rec.to_dict())
        self.assertIn("sd_xl_base_1.0", str(rec.albedo_provenance.get("model")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
