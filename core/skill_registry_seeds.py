"""core/skill_registry_seeds.py: W3a 默认种子（A 类首批 12 项）。

诚实标注：本文件是 W3a 阶段落地的"首批 A 类真实注册"，不声称已覆盖完整 40 项 A 类目标。
完整目标留 W3b——先把已确认能调用的 12 个做对，且每个都通过 entry 实测通过。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from core.skill_registry import skill_registry, SkillClass, SkillStatus


# (skill_id, entry_callable, version, resource_limits, evidence_requirements)
SEEDS: List[Tuple[str, Callable[..., Any], str, Dict[str, Any], List[str]]] = [
    (
        "data_oriented_typedarray_ecs",
        __import__("pipeline.data_oriented_ecs", fromlist=["DataOrientedECS"]).DataOrientedECS,
        "1.0.0",
        {"timeout_seconds": 60, "max_memory_mb": 512},
        ["input_hash", "output_hash", "soa_memory_footprint"],
    ),
    (
        "tech_tree_dag_economic_balance",
        __import__("pipeline.tech_tree_dag_engine", fromlist=["TechTreeDAGEngine"]).TechTreeDAGEngine,
        "1.0.0",
        {"timeout_seconds": 30, "max_memory_mb": 256},
        ["input_hash", "dag_cycle_check", "economic_balance_score"],
    ),
    (
        "autotile_47_bitmask_compilation",
        __import__("pipeline.autotile_bitmask_engine", fromlist=["AutotileBitmaskEngine"]).AutotileBitmaskEngine,
        "1.0.0",
        {"timeout_seconds": 30, "max_memory_mb": 256},
        ["input_hash", "bitmask_compile_log", "tile_count"],
    ),
    (
        "flow_field_swarm_navigation",
        __import__("pipeline.flow_field_pathfinding", fromlist=["FlowFieldGrid"]).FlowFieldGrid,
        "1.0.0",
        {"timeout_seconds": 60, "max_memory_mb": 512},
        ["input_hash", "field_density", "path_completeness"],
    ),
    (
        "ast_symbol_dependency_graph",
        __import__("pipeline.ast_symbol_graph", fromlist=["SymbolNode"]).SymbolNode,
        "1.0.0",
        {"timeout_seconds": 30, "max_memory_mb": 256},
        ["input_hash", "graph_node_count", "edge_count"],
    ),
    (
        "adversarial_red_team_inquisition",
        __import__("pipeline.adversarial_red_team", fromlist=["RedTeamInquisitor"]).RedTeamInquisitor,
        "1.0.0",
        {"timeout_seconds": 120, "max_memory_mb": 512},
        ["input_hash", "veto_reasons", "pass_rate"],
    ),
    (
        "headless_toolchain_orchestration",
        __import__("pipeline.headless_toolchain_orchestrator", fromlist=["ToolchainInspector"]).ToolchainInspector,
        "1.0.0",
        {"timeout_seconds": 60, "max_memory_mb": 256},
        ["input_hash", "toolchain_inventory", "fallback_chain"],
    ),
    (
        "lockstep_multiplayer_netcode",
        __import__("pipeline.multiplayer_netcode_engine", fromlist=["PlayerSession"]).PlayerSession,
        "1.0.0",
        {"timeout_seconds": 30, "max_memory_mb": 128},
        ["input_hash", "session_id", "lockstep_tick"],
    ),
    (
        "procedural_scene_scripting",
        __import__("pipeline.procedural_scene_compiler", fromlist=["ProceduralSceneCompiler"]).ProceduralSceneCompiler,
        "1.0.0",
        {"timeout_seconds": 120, "max_memory_mb": 512},
        ["input_hash", "scene_asset_hashes"],
    ),
    (
        "vertical_slice_milestoning",
        __import__("pipeline.vertical_slice_assembler", fromlist=["VerticalSliceAssembler"]).VerticalSliceAssembler,
        "1.0.0",
        {"timeout_seconds": 180, "max_memory_mb": 1024},
        ["input_hash", "slice_artifact_hashes", "tier_progression"],
    ),
    (
        "idea_coroner_autopsy",
        __import__("pipeline.idea_coroner_engine", fromlist=["MicroCoreLoop"]).MicroCoreLoop,
        "1.0.0",
        {"timeout_seconds": 30, "max_memory_mb": 128},
        ["input_hash", "loop_completeness", "verdict"],
    ),
    (
        "skeletal_skinning_animation",
        __import__("pipeline.skeletal_animation_engine", fromlist=["JointNode"]).JointNode,
        "1.0.0",
        {"timeout_seconds": 60, "max_memory_mb": 256},
        ["input_hash", "joint_count", "hierarchy_depth"],
    ),
    # ── W3b 第二批 13 项：8 个来自 DISCOVERED（语义核对后采纳），
    #    5 个来自内容级搜索（语义直接对应，非大文件杂命中）。
    #    未采纳的错配：arpeggio_generator→LOD / object_pool_manager→audio_pool
    #    / pbr_five_channel_baking→validator / save_state_serializer→inspector
    #    / webgl_shader_pipeline→runtime_probe —— 语义不符，不注册。
    (
        "adaptive_multitrack_audio",
        __import__("pipeline.adaptive_audio_system", fromlist=["AudioLayer"]).AudioLayer,
        "1.0.0",
        {"timeout_seconds": 60, "max_memory_mb": 256},
        ["input_hash", "layer_count", "mix_result"],
    ),
    (
        "bullet_hell_pattern_gen",
        __import__("core.bullet_system.bullet_pattern_runtime", fromlist=["BulletPatternRuntime"]).BulletPatternRuntime,
        "1.0.0",
        {"timeout_seconds": 60, "max_memory_mb": 256},
        ["input_hash", "pattern_id", "bullet_count"],
    ),
    (
        "fog_of_war_alpha_mask",
        __import__("core.lighting.fog_of_war", fromlist=["FogOfWar"]).FogOfWar,
        "1.0.0",
        {"timeout_seconds": 30, "max_memory_mb": 128},
        ["input_hash", "grid_size", "visible_tiles"],
    ),
    (
        "multi_tier_lod_generator",
        __import__("pipeline.asset_streaming.lod_generator", fromlist=["LODLevel"]).LODLevel,
        "1.0.0",
        {"timeout_seconds": 30, "max_memory_mb": 128},
        ["input_hash", "lod_tiers", "distance_thresholds"],
    ),
    (
        "save_load_integrity_test",
        __import__("core.save_system.save_integrity", fromlist=["SaveIntegrity"]).SaveIntegrity,
        "1.0.0",
        {"timeout_seconds": 60, "max_memory_mb": 256},
        ["input_hash", "integrity_check_passed", "mismatch_report"],
    ),
    (
        "scene_graph_transform_hierarchy",
        __import__("pipeline.engine_scene_graph", fromlist=["Transform2D"]).Transform2D,
        "1.0.0",
        {"timeout_seconds": 30, "max_memory_mb": 128},
        ["input_hash", "node_count", "dirty_flag_propagation"],
    ),
    (
        "visual_frame_diff_auditor",
        __import__("pipeline.visual_diff_engine", fromlist=["VisualDiffEngine"]).VisualDiffEngine,
        "1.0.0",
        {"timeout_seconds": 120, "max_memory_mb": 512},
        ["input_hash", "diff_pixel_ratio", "frame_hashes"],
    ),
    (
        "vlm_aesthetic_ux_critique",
        __import__("pipeline.vlm_aesthetic_evaluator", fromlist=["VLMAestheticCritic"]).VLMAestheticCritic,
        "1.0.0",
        {"timeout_seconds": 120, "max_memory_mb": 512},
        ["input_hash", "aesthetic_score", "critique_text"],
    ),
    (
        "deterministic_path_solving",
        __import__("pipeline.deterministic_solvers", fromlist=["PathConnectivitySolver"]).PathConnectivitySolver,
        "1.0.0",
        {"timeout_seconds": 60, "max_memory_mb": 256},
        ["input_hash", "path_found", "solver_steps"],
    ),
    (
        "event_driven_msg_bus",
        __import__("core.runtime_system_bus", fromlist=["RuntimeSystemBus"]).RuntimeSystemBus,
        "1.0.0",
        {"timeout_seconds": 30, "max_memory_mb": 128},
        ["input_hash", "subscriber_count", "event_log"],
    ),
    (
        "evidence_pack_targeted_healing",
        __import__("pipeline.evidence_healer", fromlist=["EvidenceHealer"]).EvidenceHealer,
        "1.0.0",
        {"timeout_seconds": 120, "max_memory_mb": 512},
        ["input_hash", "healed_evidence_ids", "residual_errors"],
    ),
    (
        "combat_damage_formula",
        __import__("core.combat_numerical_engine", fromlist=["CombatNumericalEngine"]).CombatNumericalEngine,
        "1.0.0",
        {"timeout_seconds": 30, "max_memory_mb": 128},
        ["input_hash", "damage_curve", "balance_report"],
    ),
    (
        "discrete_tick_physics_freeze",
        __import__("core.frame_stepping_controller", fromlist=["FrameSteppingController"]).FrameSteppingController,
        "1.0.0",
        {"timeout_seconds": 60, "max_memory_mb": 256},
        ["input_hash", "tick_rate", "determinism_check"],
    ),
]


def apply_default_seeds(verbose: bool = False) -> Dict[str, Any]:
    """把 SEEDS 里的 12 项注册为 capability。

    不会重复注册；只对 DISCOVERED 状态的技能有效。
    返回 {registered, failed, failed_ids}——**真实数字**，不美化。
    """
    if not skill_registry._skills:
        skill_registry.ingest_from_registry()
        skill_registry.discover_a_class()
    registered = 0
    failed: List[str] = []
    for sid, entry, version, limits, evidence in SEEDS:
        sk = skill_registry._skills.get(sid)
        if sk is None:
            failed.append(f"{sid}: unknown skill_id (not in GAME_SKILLS)")
            continue
        # 内容级搜索找到的实现：文件名与 skill_id 不匹配，discover 扫不到，
        # 这里按人工核对结果手工置为 DISCOVERED（不算自动发现，notes 里留痕）。
        if sk.status == SkillStatus.PENDING:
            sk.candidate_module = entry.__module__
            sk.candidate_score = 0.0
            sk.cls = SkillClass.A
            sk.status = SkillStatus.DISCOVERED
            sk.notes.append(f"manual mapping via content-level search: {entry.__module__}")
        try:
            skill_registry.register_as_capability(
                skill_id=sid, entry=entry, version=version,
                resource_limits=limits, evidence_requirements=evidence,
            )
            registered += 1
            if verbose:
                print(f"  [seed-ok ] {sid:42s} -> {entry.__module__}.{entry.__name__}")
        except Exception as exc:
            failed.append(f"{sid}: {type(exc).__name__}: {exc}")
            if verbose:
                print(f"  [seed-fail] {sid:42s} {exc}")
    return {"registered": registered, "failed": len(failed), "failed_ids": failed}
