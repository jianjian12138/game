"""M3 第一批 3D 资产真实输出门禁测试。"""

import base64
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestGLTFM3(unittest.TestCase):
    def test_asset3d_bridge_output_passes_gltf_pbr_and_lod(self):
        from pipeline.asset_3d_bridge import Asset3DBridge
        from pipeline.gltf_validator import validate_gltf
        from pipeline.lod_budget_policy import validate_lod_budget
        from pipeline.pbr_validator import validate_pbr

        with tempfile.TemporaryDirectory(prefix="m3_asset_") as temp_dir:
            result = Asset3DBridge.build_procedural_asset("turret", output_dir=Path(temp_dir))
            asset_path = Path(result["gltf_path"])
            self.assertTrue(asset_path.is_file())
            self.assertEqual(validate_gltf(asset_path)["status"], "SUCCESS")
            self.assertEqual(validate_pbr(asset_path)["status"], "SUCCESS")
            lod = validate_lod_budget(asset_path, profile="gameplay")
            self.assertEqual(lod["status"], "SUCCESS")
            self.assertEqual(lod["base_triangles"], result["triangles_count"])
            self.assertTrue(asset_path.is_relative_to(Path(temp_dir)))

    def test_skeletal_engine_output_passes_skin_and_animation_gates(self):
        from pipeline.gltf_validator import validate_gltf
        from pipeline.pbr_validator import validate_pbr
        from pipeline.skeletal_animation_engine import SkeletalAnimationEngine
        from pipeline.skeleton_validator import validate_skeleton

        with tempfile.TemporaryDirectory(prefix="m3_rig_") as temp_dir:
            asset_path = Path(temp_dir) / "HeroRigged.gltf"
            result = SkeletalAnimationEngine.build_rigged_humanoid(str(asset_path))
            self.assertEqual(result["status"], "SUCCESS")
            self.assertEqual(validate_gltf(asset_path)["status"], "SUCCESS")
            self.assertEqual(validate_pbr(asset_path)["status"], "SUCCESS")
            skeleton = validate_skeleton(asset_path)
            self.assertEqual(skeleton["status"], "SUCCESS", skeleton)
            self.assertTrue(skeleton["checks"]["skins"])
            self.assertTrue(skeleton["checks"]["weights"])
            self.assertTrue(skeleton["checks"]["animations"])
            self.assertGreaterEqual(result["joint_count"], 15)
            self.assertEqual(set(result["animations"]), {"Idle", "Walk", "Attack"})

    def test_gltf_validator_rejects_bad_index(self):
        from pipeline.gltf_validator import validate_gltf

        raw = struct.pack("<9f3H", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0, 1, 3)
        document = {
            "asset": {"version": "2.0"},
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
            "accessors": [
                {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
                {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"},
            ],
            "bufferViews": [
                {"buffer": 0, "byteLength": 36, "target": 34962},
                {"buffer": 0, "byteOffset": 36, "byteLength": 6, "target": 34963},
            ],
            "buffers": [{"byteLength": len(raw), "uri": "data:application/octet-stream;base64," + base64.b64encode(raw).decode("ascii")}],
        }
        report = validate_gltf(document)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(item["code"] in {"INDEX_OUT_OF_RANGE", "INDICES_DATA"} for item in report["errors"]))

    def test_runtime_smoke_never_fakes_browser_success(self):
        from pipeline.asset_3d_bridge import Asset3DBridge
        from pipeline.runtime_asset_smoke import run_runtime_asset_smoke

        with tempfile.TemporaryDirectory(prefix="m3_runtime_") as temp_dir:
            result = Asset3DBridge.build_procedural_asset("crate", output_dir=Path(temp_dir))
            report = run_runtime_asset_smoke(result["gltf_path"], runtime_command=[sys.executable, "-c", "import sys; sys.exit(0)"])
            self.assertEqual(report["status"], "NEEDS_RUNTIME_TOOL")
            self.assertFalse(report["valid"])
            self.assertEqual(report["runtime"]["status"], "NEEDS_RUNTIME_TOOL")

    def test_runtime_probe_can_prove_success_explicitly(self):
        from pipeline.asset_3d_bridge import Asset3DBridge
        from pipeline.runtime_asset_smoke import run_runtime_asset_smoke

        with tempfile.TemporaryDirectory(prefix="m3_probe_") as temp_dir:
            result = Asset3DBridge.build_procedural_asset("mech", output_dir=Path(temp_dir))
            report = run_runtime_asset_smoke(
                result["gltf_path"],
                runtime_probe=lambda path: {"status": "SUCCESS", "loaded": path.is_file(), "rendered": True},
            )
            self.assertEqual(report["status"], "SUCCESS")
            self.assertTrue(report["valid"])


if __name__ == "__main__":
    unittest.main()
