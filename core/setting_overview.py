# =================================================================
# 🧭 Game-Agent: 生产目录与前置路由中枢 (setting_overview.py)
# 对标《GameFactory-3A: setting_overview.md 路由入口》
# 拒绝无约束盲写代码，必须在 Stage 0 锁定引擎、网格、轴心与性能预算
# =================================================================

import json
from pathlib import Path
from typing import Dict, Any

class SettingOverviewRouter:
    """
    项目级路由与前置约束中心 (Setting Overview Router)
    为 Agent 在动手写代码前提供严格的规范与上下文边界
    """

    PRESETS = {
        "rust_macroquad_2d": {
            "engine": "Rust + Macroquad",
            "target_platform": "Windows Native x64",
            "viewport_resolution": (1024, 720),
            "target_fps": 60,
            "grid_cell_px": 48.0,
            "sprite_pivot_mode": "Center-Centered (轴心严格居中)",
            "coordinate_system": "World-to-Screen Anchored Zoom",
            "color_depth": "RGBA8888",
            "ui_framework": "AABB Box Scene2D + TrueType Vector Fonts",
            "audio_backend": "Macroquad Audio Native (OGG/WAV)",
            "memory_budget_mb": 256,
            "render_layers": [
                "Layer 0: Floor & Ores",
                "Layer 1: Buildings & Infrastructure",
                "Layer 2: Units & Mechs",
                "Layer 3: Juice & Combat Effects (Lasers, Sparks, Shake)",
                "Layer 4: Hologram Ghost Placement Preview",
                "Layer 5: UI & Modals"
            ]
        },
        "godot_4_2d_3d": {
            "engine": "Godot 4.3 Engine",
            "target_platform": "PC Desktop",
            "viewport_resolution": (1280, 720),
            "target_fps": 60,
            "grid_cell_px": 32.0,
            "sprite_pivot_mode": "Bottom-Centered / Center-Centered",
            "coordinate_system": "Godot CanvasLayer & Camera2D",
            "memory_budget_mb": 512
        }
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_file = project_root / "knowledge" / "setting_overview.md"
        self.docs_file.parent.mkdir(parents=True, exist_ok=True)

    def route_and_lock(self, preset_name: str = "rust_macroquad_2d") -> Dict[str, Any]:
        """锁定项目级生产路由规范并生成 setting_overview.md"""
        preset = self.PRESETS.get(preset_name, self.PRESETS["rust_macroquad_2d"])
        
        md_lines = [
            f"# 🧭 项目级生产目录与路由大典 (setting_overview.md)",
            f"> **遵循 GameFactory-3A 工业规范：动手编码前必须先锁定所有规范边界**\n",
            "---\n",
            "## ⚙️ 当前项目全局锁定参数 (Locked Context)\n",
            f"- **目标引擎**: `{preset['engine']}`",
            f"- **目标平台**: `{preset['target_platform']}`",
            f"- **视口分辨率**: `{preset['viewport_resolution'][0]} x {preset['viewport_resolution'][1]}`",
            f"- **目标帧率**: `{preset['target_fps']} FPS (垂直同步/零掉帧)`",
            f"- **网格基准尺寸**: `{preset['grid_cell_px']} px`",
            f"- **Sprite 贴图轴心规范**: `{preset['sprite_pivot_mode']}`",
            f"- **摄像机坐标系**: `{preset['coordinate_system']}`",
            f"- **内存预算上限**: `{preset['memory_budget_mb']} MB`\n",
            "## 🎨 严格分层渲染管线约束 (Render Layer Contracts)\n"
        ]

        if "render_layers" in preset:
            for l in preset["render_layers"]:
                md_lines.append(f"  - **{l}**")

        self.docs_file.write_text("\n".join(md_lines), encoding="utf-8")
        return preset

if __name__ == "__main__":
    router = SettingOverviewRouter((Path(__file__).resolve().parent))
    res = router.route_and_lock("rust_macroquad_2d")
    print(f"=== SettingOverviewRouter: 路由规则已成功锁定并生成 setting_overview.md ===")
    print(f"  [LOCKED ENGINE] {res['engine']}")
    print(f"  [GRID UNIT] {res['grid_cell_px']} px")
