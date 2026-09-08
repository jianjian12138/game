#!/usr/bin/env python3
"""
godot_exporter.py: Godot 4 工业级跨端游戏工程导出调度器 (Godot 4 Project Exporter)
调度 GodotFullEngine 装配核心，输出具备 CharacterBody3D、胶囊体、SpringArm相机、
move_and_slide 物理与封闭刚性空气墙的商业级 Godot 4 独立工程。
"""
from pathlib import Path
from pipeline.godot_full_engine import GodotFullEngine

class GodotExporter:
    @staticmethod
    def export_godot_project(title: str, genre: str, output_dir: Path) -> Path:
        godot_dir = output_dir / "godot_project"
        # 调用全套工业工程装配中枢
        GodotFullEngine.assemble_full_godot_project(title=title, genre=genre, target_dir=godot_dir)
        
        # 联动 Asset3DBridge: 导出与注入原生 glTF 3D 资产
        try:
            from pipeline.asset_3d_bridge import Asset3DBridge
            models_dir = godot_dir / "assets" / "models"
            models_dir.mkdir(parents=True, exist_ok=True)
            Asset3DBridge.build_procedural_asset("turret", output_dir=models_dir)
            Asset3DBridge.build_procedural_asset("mech", output_dir=models_dir)
        except Exception as e:
            print(f"[GodotExporter] 3D 资产注入提示: {e}")

        return godot_dir
