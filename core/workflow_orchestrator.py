"""Small, deterministic workflow planner for the versioned delivery path."""
from __future__ import annotations

from typing import Any, Dict, List

from core.capability_registry import CapabilityRegistry, capability_registry
from core.contracts import GameIntent, GameSpec, WorkflowNode, WorkflowPlan


class WorkflowOrchestrator:
    def __init__(self, registry: CapabilityRegistry | None = None):
        self.registry = registry or capability_registry

    def normalize_spec(self, intent: GameIntent) -> GameSpec:
        is_3d = any(token in f"{intent.title} {intent.genre} {intent.custom_rules}".lower() for token in ("3d", "3a", "pbr", "lod", "次时代", "材质", "骨骼", "机甲"))
        acceptance = ["boot_to_play", "move_and_attack", "level_up", "death_and_restart"]
        assets = {}
        if is_3d:
            acceptance.extend(["asset_load", "pbr_material_visible", "skeleton_animation_play", "lod_switch"])
            assets = {
                "formats": ["gltf"],
                "pbr_channels": ["baseColor", "normal", "metallicRoughness", "ao", "emissive"],
                "skin_required": True,
                "animations": ["Idle", "Walk", "Attack"],
                "lod_levels": ["LOD0", "LOD1", "LOD2"],
            }
        return GameSpec(
            intent_ref=intent.intent_id,
            run_id=intent.run_id,
            title=intent.title,
            genre=intent.genre,
            target_platforms=intent.target_platforms,
            core_loop=["start", "play", "progress", "resolve"],
            acceptance_scenarios=acceptance,
            non_functional={"target_fps": 60, "console_error_max": 0},
            asset_requirements=assets,
            out_of_scope=intent.out_of_scope,
        )

    def build_plan(self, intent: GameIntent, spec: GameSpec) -> WorkflowPlan:
        nodes = [
            WorkflowNode("normalize", "intent.normalize", "1.0.0", [intent.intent_id], [spec.spec_id]),
            WorkflowNode("build", "build.game", "1.0.0", [spec.spec_id], ["build_artifact"], ["normalize"], "G3"),
            WorkflowNode("runtime", "test.runtime", "1.0.0", ["build_artifact"], ["evidence_pack"], ["build"], "G4"),
            WorkflowNode("gate", "gate.release", "1.0.0", ["evidence_pack"], ["gate_decisions"], ["runtime"], "G5"),
        ]
        is_3d = bool(spec.asset_requirements)
        if is_3d:
            nodes.insert(2, WorkflowNode("asset_validation", "team.next_gen_3d_art", "1.0.0", [spec.spec_id], ["asset_manifest"], ["normalize"], "G2"))
            nodes[3].depends_on = ["build", "asset_validation"]
        return WorkflowPlan(intent.run_id, intent.intent_id, spec.spec_id, intent.profile, nodes)
