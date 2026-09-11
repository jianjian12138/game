#!/usr/bin/env python3
"""pipeline/textured_3d_asset.py — W6 贴图 3D 资产构建器（次时代 PBR 美术团队落地）。

职责（与升级计划第十一章、M4 一致）：
  1. 用带**正确 UV** 的程序化几何（box/cylinder 逐面 UV，杜绝退化 (0,0)），
     让贴图可真实映射，而非只挂因子。
  2. AI albedo：复用 W5 ImageGenAdapter 真出图（ComfyUI/云端），真实才标
     is_ai_generated=True 并把模型/seed/端点写入 provenance。
  3. 程序化 4 通道 PBR 贴图：normal / metallicRoughness / ao / emissive，
     由 next_gen_3d_pipeline.PBRTextureBaker 纯 Python 烘焙（真实 PNG）。
  4. 把五通道贴图以相对 uri 引用挂进 glTF 2.0（images/textures/materials），
     与 .gltf 同目录落 5 张真实 PNG + provenance.json。
  5. 可选 M4 真机导入：verify_godot=True 时调用 GodotImporter 在真 Godot 4.7.2
     导入，返回 M4 真机证据；Godot 缺失则诚实报 needs_runtime_tool="godot_engine"。

防伪底线（13.2）：
  - AI 后端不可用 -> albedo 走程序化兜底，is_procedural_placeholder=True，
    needs_runtime_tool="aigc_backend"，绝不把程序化 PNG 粉饰成 AI 美术。
  - 五通道贴图均为真实生成的 PNG 字节，可独立校验（解码/哈希/尺寸）。
  - 不依赖 requests/PIL/numpy：解码用 base64，图像用 png_io / PBRTextureBaker 自带。
"""
from __future__ import annotations

import base64
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.asset_3d_bridge import Mesh3D, PBRMaterial, GLTF2Serializer
from pipeline.next_gen_3d_pipeline import PBRTextureBaker
from pipeline.image_gen_adapter import ImageGenAdapter
from pipeline.godot_importer import GodotImporter


def _decode_data_uri(uri: str) -> bytes:
    """PBRTextureBaker 返回 data:image/png;base64,...，解码为 PNG 字节。"""
    _, _, data = uri.partition(",")
    return base64.b64decode(data)


# 五通道贴图键（与 GLTF2Serializer.export_textured_gltf_json 约定一致）
PROC_CHANNELS = ("normal", "metallicRoughness", "ao", "emissive")
# 贴图键 -> PBRTextureBaker 烘焙方法名
_BAKE_METHOD = {
    "normal": "bake_normal",
    "metallicRoughness": "bake_metallic_roughness",
    "ao": "bake_ao",
    "emissive": "bake_emissive",
}


@dataclass
class TexturedAssetRecord:
    status: str = "success"
    asset_name: str = ""
    asset_type: str = "turret"
    gltf_path: str = ""
    texture_paths: Dict[str, str] = field(default_factory=dict)
    provenance_path: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    # albedo 诚实标记
    is_ai_albedo: bool = False
    is_procedural_albedo: bool = False
    albedo_backend: str = ""
    albedo_provenance: Dict[str, Any] = field(default_factory=dict)
    albedo_needs_runtime_tool: Optional[str] = None
    # 几何
    vertex_count: int = 0
    triangle_count: int = 0
    seed: int = 0
    resolution: int = 0
    # M4 真机
    m4_achieved: Optional[bool] = None
    godot: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: str = ""
    needs_runtime_tool: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "asset_name": self.asset_name,
            "asset_type": self.asset_type,
            "gltf_path": self.gltf_path,
            "texture_paths": self.texture_paths,
            "provenance_path": self.provenance_path,
            "is_ai_albedo": self.is_ai_albedo,
            "is_procedural_albedo": self.is_procedural_albedo,
            "albedo_backend": self.albedo_backend,
            "albedo_needs_runtime_tool": self.albedo_needs_runtime_tool,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "seed": self.seed,
            "resolution": self.resolution,
            "m4_achieved": self.m4_achieved,
            "godot": self.godot,
            "warnings": self.warnings,
            "error": self.error,
            "needs_runtime_tool": self.needs_runtime_tool,
        }


class TexturedAssetBuilder:
    """工业级贴图 3D 资产构建中枢。"""

    # 资产类型 -> 几何构建函数
    ASSET_BUILDERS = {}

    # ── 几何构建（带正确 UV） ───────────────────────────────────────────────
    @staticmethod
    def build_textured_defense_turret() -> Mesh3D:
        mesh = Mesh3D(name="DefenseTurret_PBR", material=PBRMaterial(
            name="Military_Steel_PBR",
            base_color=(1.0, 1.0, 1.0, 1.0),
            metallic=1.0, roughness=1.0, emissive=(1.0, 1.0, 1.0),
        ))
        mesh.add_box_uv(0, 0.2, 0, 2.0, 0.4, 2.0)              # 八角基座
        mesh.add_cylinder_uv(0, 0.6, 0, 0.75, 0.4, 16)          # 旋转平台
        mesh.add_box_uv(0, 1.1, 0, 1.1, 0.7, 1.3)              # 装甲主体
        mesh.add_cylinder_uv(-0.3, 1.1, 1.2, 0.12, 1.6, 12)     # 左炮管
        mesh.add_cylinder_uv(0.3, 1.1, 1.2, 0.12, 1.6, 12)      # 右炮管
        mesh.add_cylinder_uv(-0.3, 1.1, 1.95, 0.18, 0.15, 12)   # 左制退环
        mesh.add_cylinder_uv(0.3, 1.1, 1.95, 0.18, 0.15, 12)    # 右制退环
        mesh.add_box_uv(0, 1.6, -0.3, 0.4, 0.3, 0.4)           # 雷达座
        return mesh

    @staticmethod
    def build_textured_mech_warrior() -> Mesh3D:
        mesh = Mesh3D(name="MechWarrior_PBR", material=PBRMaterial(
            name="Titanium_Armor_PBR",
            base_color=(1.0, 1.0, 1.0, 1.0),
            metallic=1.0, roughness=1.0, emissive=(1.0, 1.0, 1.0),
        ))
        mesh.add_box_uv(0, 1.8, 0, 1.2, 1.0, 0.8)
        mesh.add_box_uv(0, 2.45, 0.1, 0.5, 0.35, 0.5)
        mesh.add_box_uv(-0.85, 2.0, -0.2, 0.45, 0.8, 0.6)
        mesh.add_box_uv(0.85, 2.0, -0.2, 0.45, 0.8, 0.6)
        mesh.add_box_uv(0, 1.15, 0, 0.8, 0.3, 0.6)
        for side in (-0.45, 0.45):
            mesh.add_box_uv(side, 0.65, 0, 0.35, 0.7, 0.4)
            mesh.add_box_uv(side, 0.1, 0.1, 0.45, 0.2, 0.7)
        return mesh

    @staticmethod
    def build_textured_sci_fi_crate() -> Mesh3D:
        mesh = Mesh3D(name="SciFiCrate_PBR", material=PBRMaterial(
            name="Nanocarbon_Crate_PBR",
            base_color=(1.0, 1.0, 1.0, 1.0),
            metallic=1.0, roughness=1.0, emissive=(1.0, 1.0, 1.0),
        ))
        mesh.add_box_uv(0, 0.5, 0, 1.0, 1.0, 1.0)
        for x in (-0.45, 0.45):
            for y in (0.1, 0.9):
                for z in (-0.45, 0.45):
                    mesh.add_box_uv(x, y, z, 0.2, 0.2, 0.2)
        mesh.add_box_uv(0, 0.5, 0.52, 0.4, 0.15, 0.05)
        return mesh

    @staticmethod
    def build_textured_crystal_spire() -> Mesh3D:
        mesh = Mesh3D(name="CrystalSpire_PBR", material=PBRMaterial(
            name="Aether_Crystal_PBR",
            base_color=(1.0, 1.0, 1.0, 1.0),
            metallic=1.0, roughness=1.0, emissive=(1.0, 1.0, 1.0),
        ))
        mesh.add_box_uv(0, 1.5, 0, 0.6, 2.0, 0.6)
        mesh.add_box_uv(0, 1.5, 0, 0.4, 2.4, 0.4)
        mesh.add_cylinder_uv(0, 0.1, 0, 1.2, 0.2, 8)
        return mesh

    ASSET_BUILDERS = {
        "turret": build_textured_defense_turret,
        "defense": build_textured_defense_turret,
        "cannon": build_textured_defense_turret,
        "mech": build_textured_mech_warrior,
        "robot": build_textured_mech_warrior,
        "crate": build_textured_sci_fi_crate,
        "chest": build_textured_sci_fi_crate,
        "crystal": build_textured_crystal_spire,
        "spire": build_textured_crystal_spire,
    }

    # ── 主入口 ──────────────────────────────────────────────────────────────
    @classmethod
    def build(cls, asset_type: str = "turret",
              output_dir: Optional[str] = None,
              backend: Optional[str] = None,
              style: Any = None, seed: Optional[int] = None,
              verify_godot: bool = False,
              resolution: int = 256) -> TexturedAssetRecord:
        """构建一项带 PBR 贴图的 3D 资产，落盘并返回诚实结构化记录。"""
        out_root = Path(output_dir) if output_dir \
            else (ROOT / "output" / "assets" / "3d_textured")
        out_root.mkdir(parents=True, exist_ok=True)

        rec = TexturedAssetRecord(asset_type=asset_type, resolution=resolution)
        seed = int(seed) if seed is not None else 123456789
        rec.seed = seed

        builder_fn = cls.ASSET_BUILDERS.get(asset_type.lower(),
                                            cls.build_textured_defense_turret)
        mesh = builder_fn()
        rec.asset_name = mesh.name

        # 1) 程序化 4 通道 PBR 贴图（真实 PNG）
        texture_uris: Dict[str, str] = {}
        for ch in PROC_CHANNELS:
            uri = getattr(PBRTextureBaker, _BAKE_METHOD[ch])(resolution, resolution)
            png = _decode_data_uri(uri)
            fname = f"{mesh.name}_{ch}.png"
            (out_root / fname).write_bytes(png)
            texture_uris[ch] = fname
            rec.texture_paths[ch] = str(out_root / fname)

        # 2) albedo：AI（真实才标）/ 程序化兜底（诚实）
        adapter = ImageGenAdapter()
        prompt = ("seamless sci-fi military steel armor panel, PBR albedo texture, "
                  "tileable, matte painted metal, no text, no logo, no watermark")
        neg = ", ".join(style.negative_prompts) if style else \
            "blurry, lowres, deformed, text, watermark, signature"
        alb_backend = None if backend in (None, "auto") else backend
        res = adapter.generate(prompt=prompt, style=style, seed=seed,
                               width=resolution, height=resolution,
                               backend=alb_backend, negative_prompt=neg,
                               transparent=False)
        if res.ok() and res.is_ai_generated:
            albedo_png = res.image_bytes
            rec.is_ai_albedo = True
            rec.albedo_backend = res.backend
            rec.albedo_provenance = res.provenance
        elif res.ok() and res.is_procedural_placeholder:
            albedo_png = res.image_bytes
            rec.is_procedural_albedo = True
            rec.albedo_backend = "procedural_placeholder"
            rec.albedo_provenance = res.provenance
            if res.needs_runtime_tool:
                rec.albedo_needs_runtime_tool = res.needs_runtime_tool
            rec.warnings.extend(res.warnings)
        else:
            # 真出错（程序化兜底总能出图，理论上不会到这）：诚实暴露
            rec.status = "error"
            rec.error = res.error or "albedo 生成失败"
            rec.needs_runtime_tool = res.needs_runtime_tool
            rec.provenance = {"error": rec.error,
                              "albedo_needs_runtime_tool": rec.needs_runtime_tool}
            return rec

        fname = f"{mesh.name}_albedo.png"
        (out_root / fname).write_bytes(albedo_png)
        texture_uris["albedo"] = fname
        rec.texture_paths["albedo"] = str(out_root / fname)

        # 3) 贴图 glTF 2.0
        gltf = GLTF2Serializer.export_textured_gltf_json(mesh, texture_uris)
        gltf_path = out_root / f"{mesh.name}.gltf"
        gltf_path.write_text(gltf, encoding="utf-8")
        rec.gltf_path = str(gltf_path)
        rec.vertex_count = len(mesh.positions) // 3
        rec.triangle_count = len(mesh.indices) // 3

        # 4) provenance
        prov = {
            "asset_name": mesh.name,
            "asset_type": asset_type,
            "generator": "GameAgent TexturedAssetBuilder v6.1",
            "resolution": resolution,
            "seed": seed,
            "uv_correct": True,
            "textures": {k: Path(v).name for k, v in rec.texture_paths.items()},
            "albedo": {
                "is_ai_generated": rec.is_ai_albedo,
                "is_procedural_placeholder": rec.is_procedural_albedo,
                "backend": rec.albedo_backend,
                "needs_runtime_tool": rec.albedo_needs_runtime_tool,
                "provenance": rec.albedo_provenance,
            },
            "procedural_channels": list(PROC_CHANNELS),
            "warnings": rec.warnings,
        }
        rec.provenance = prov
        prov_path = out_root / f"{mesh.name}.provenance.json"
        prov_path.write_text(json.dumps(prov, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        rec.provenance_path = str(prov_path)

        # 5) M4 真机导入（可选）
        if verify_godot:
            gir = GodotImporter.verify(str(out_root))
            rec.godot = gir.to_dict()
            rec.m4_achieved = gir.success
            if not gir.success and gir.needs_runtime_tool:
                rec.needs_runtime_tool = gir.needs_runtime_tool
        return rec


if __name__ == "__main__":
    r = TexturedAssetBuilder.build("turret", verify_godot=False)
    print(f"[W6] 贴图资产构建: {r.asset_name} ｜ 顶点 {r.vertex_count} ｜ 面 {r.triangle_count}")
    print(f"  AI albedo   : {r.is_ai_albedo} ｜ 程序化 albedo: {r.is_procedural_albedo}")
    print(f"  glTF        : {r.gltf_path}")
    print(f"  贴图        : {list(r.texture_paths.keys())}")
