# =================================================================
# 🧭 Game-Agent: 生产目录与前置路由中枢 (setting_overview.py)
# 对标《GameFactory-3A: setting_overview.md 路由入口》
# 拒绝无约束盲写代码，必须在 Stage 0 锁定引擎、网格、轴心与性能预算
# =================================================================

import json
from pathlib import Path
from typing import Dict, Any

from core.registry import get_team

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


class EngineFingerprintDetector:
    """
    两阶段项目指纹智能探测与任务路由决策器 (基于 awesome-gamedev-agent-skills Master Router 哲学)
    - 阶段一 (Exclusive Engine): 独占式扫描最高置信度特征文件，确定唯一游戏引擎
    - 阶段二 (Additive Disciplines & Genres): 根据上下文与任务关键词，链式叠加专业领域专家与技能组合
    """

    @staticmethod
    def detect_engine(project_dir: Path) -> Dict[str, Any]:
        """扫描项目目录文件特征，返回独占引擎判定"""
        p = Path(project_dir)
        if not p.exists() or not p.is_dir():
            return {
                "engine_id": "antigravity_web",
                "engine_name": "Antigravity WebGL/Canvas (Zero-Deps)",
                "confidence": 0.5,
                "evidence": "Target path is not directory, fallback to native web runtime",
                "recommended_agents": ["lead_architect", "gameplay_programmer", "graphics_shader_specialist"]
            }

        # 1. Godot 判定 (最高优先级: project.godot)
        if (p / "project.godot").exists():
            godot_content = (p / "project.godot").read_text(encoding="utf-8", errors="ignore")
            ver = "4.7" if "config_version=5" in godot_content else "4.3"
            return {
                "engine_id": "godot",
                "engine_name": f"Godot {ver} (GDScript / C#)",
                "confidence": 1.0,
                "evidence": "Detected project.godot configuration file",
                "recommended_agents": ["platform_porting_engineer", "autotile_bitmask_master", "skeletal_anim_director"],
                "recommended_skills": ["autotile_47_bitmask_compilation", "skeletal_skinning_animation", "procedural_scene_scripting"]
            }

        # 2. Unreal Engine 判定 (*.uproject)
        uproject_files = list(p.glob("*.uproject"))
        if uproject_files:
            return {
                "engine_id": "unreal",
                "engine_name": "Unreal Engine 5 (C++ / Blueprints / Nanite / Lumen)",
                "confidence": 1.0,
                "evidence": f"Detected Unreal project descriptor: {uproject_files[0].name}",
                "recommended_agents": ["cpp_engine_architect", "pbr_material_pipeline_engineer", "lod_streaming_architect"],
                "recommended_skills": ["tangent_normal_brdf_shader", "multi_tier_lod_generator", "pbr_five_channel_baking"]
            }

        # 3. Unity 判定 (Assets/ + ProjectSettings/ProjectVersion.txt)
        if (p / "Assets").exists() and (p / "ProjectSettings" / "ProjectVersion.txt").exists():
            return {
                "engine_id": "unity",
                "engine_name": "Unity Engine (C# / ScriptableObjects / URP / HDRP)",
                "confidence": 1.0,
                "evidence": "Detected Unity Assets/ and ProjectSettings/ProjectVersion.txt",
                "recommended_agents": ["lead_architect", "performance_optimizer", "physics_engineer"],
                "recommended_skills": ["object_pool_manager", "quadtree_collision", "lerp_smoothing_math"]
            }

        # 4. Rust Game Engine (Cargo.toml 含 bevy 或 macroquad)
        cargo_toml = p / "Cargo.toml"
        if cargo_toml.exists():
            txt = cargo_toml.read_text(encoding="utf-8", errors="ignore").lower()
            if "bevy" in txt or "macroquad" in txt:
                framework = "Bevy ECS" if "bevy" in txt else "Macroquad Native"
                return {
                    "engine_id": "rust_native",
                    "engine_name": f"Rust Engine ({framework})",
                    "confidence": 0.95,
                    "evidence": f"Detected Cargo.toml with {framework} dependency",
                    "recommended_agents": ["zero_gc_ecs_director", "ground_truth_reverser", "netcode_synchronizer"],
                    "recommended_skills": ["data_oriented_typedarray_ecs", "discrete_tick_physics_freeze", "lockstep_multiplayer_netcode"]
                }

        # 5. Web Engine (package.json 含 three / phaser / pixi.js)
        pkg_json = p / "package.json"
        if pkg_json.exists():
            txt = pkg_json.read_text(encoding="utf-8", errors="ignore").lower()
            for kw, name in [("three", "Three.js 3D WebGL"), ("phaser", "Phaser 2D"), ("pixi.js", "PixiJS 2D")]:
                if kw in txt:
                    return {
                        "engine_id": "web_engine",
                        "engine_name": name,
                        "confidence": 0.95,
                        "evidence": f"Detected package.json with {kw} dependency",
                        "recommended_agents": ["graphics_shader_specialist", "audio_programmer", "next_gen_sculpting_director"],
                        "recommended_skills": ["webgl_shader_pipeline", "webaudio_retro_synth", "pbr_five_channel_baking"]
                    }

        # 6. Pygame (*.py 含 import pygame 或 requirements.txt 含 pygame)
        req_txt = p / "requirements.txt"
        if req_txt.exists() and "pygame" in req_txt.read_text(encoding="utf-8", errors="ignore").lower():
            return {
                "engine_id": "pygame",
                "engine_name": "Pygame (Python 2D)",
                "confidence": 0.9,
                "evidence": "Detected pygame dependency in requirements.txt",
                "recommended_agents": ["gameplay_programmer", "physics_engineer", "sfx_designer"],
                "recommended_skills": ["aabb_collision_detection", "lerp_smoothing_math"]
            }

        # 默认通用回退
        return {
            "engine_id": "antigravity_web",
            "engine_name": "Universal High-Perf Canvas2D / WebGL 3D (Self-Contained)",
            "confidence": 0.8,
            "evidence": "Standard directory without third-party engine locks, using native zero-CORS runtime",
            "recommended_agents": ["lead_architect", "gameplay_programmer", "combat_balancer", "v8_performance_systems_engineer"],
            "recommended_skills": ["v8_hidden_class_zero_gc_tuning", "floating_combat_text", "screen_shake_effect"]
        }

    @classmethod
    def route_task(cls, project_dir: Path, user_prompt: str = "") -> Dict[str, Any]:
        """执行独占引擎嗅探与叠加领域专家装配"""
        engine_res = cls.detect_engine(project_dir)
        prompt_lower = user_prompt.lower()

        # 叠加学科领域 (Disciplines)
        additive_disciplines = []
        if any(k in prompt_lower for k in ("pbr", "3d", "次时代", "材质", "贴图", "lod")):
            next_gen_team = get_team("next_gen_3d_art_team")
            additive_disciplines.append({
                "discipline": "Next-Gen 3D Art & Asset Engineering",
                "team_id": next_gen_team["id"],
                "team_name": next_gen_team["name"],
                "lead_agent": next_gen_team["lead_agent"],
                "agents": next_gen_team["members"],
                "skills": sorted({skill for capability in next_gen_team["capabilities"] for skill in capability["skills"]}),
                "executors": sorted({executor for capability in next_gen_team["capabilities"] for executor in capability["executors"]}),
                "artifacts": sorted({artifact for capability in next_gen_team["capabilities"] for artifact in capability["artifacts"]}),
                "required_gates": next_gen_team["required_gates"],
                "maturity": next_gen_team["maturity"],
            })
        if any(k in prompt_lower for k in ("打击感", "手感", "顿帧", "震屏", "shake", "juice")):
            additive_disciplines.append({
                "discipline": "Combat Juice & Game Feel",
                "agents": ["gameplay_programmer", "physics_engineer"],
                "skills": ["screen_shake_effect", "floating_combat_text", "damage_flash_white"]
            })
        if any(k in prompt_lower for k in ("寻路", "ai", "向量场", "蜂群", "行为树")):
            additive_disciplines.append({
                "discipline": "Swarm AI & Navigation",
                "agents": ["ai_behavior_engineer", "flow_field_swarm_specialist"],
                "skills": ["a_star_pathfinding", "behavior_tree_evaluator", "flow_field_swarm_navigation"]
            })
        if any(k in prompt_lower for k in ("平衡", "抽卡", "数值", "掉落", "经济")):
            additive_disciplines.append({
                "discipline": "Economy & Mathematical Balance",
                "agents": ["combat_balancer", "executive_producer"],
                "skills": ["difficulty_kill_ratio_eval", "telemetry_funnel_analytics"]
            })

        return {
            "engine": engine_res,
            "additive_disciplines": additive_disciplines,
            "composite_agent_team": list(set(engine_res["recommended_agents"] + [a for d in additive_disciplines for a in d["agents"]])),
            "composite_skill_stack": list(set(engine_res.get("recommended_skills", []) + [s for d in additive_disciplines for s in d["skills"]]))
        }

