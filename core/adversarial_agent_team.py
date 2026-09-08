"""
Universal 8-Agent Adversarial Team (AAT) Framework (Article 43 - VibeGame)
Roles:
1. Orchestrator (Global workflow & phase orchestration)
2. Designer (GDD ground truth: mechanics, numbers, state trees)
3. Artist (Visual concept, palette, style anchoring)
4. Architect (Technical PRD, schemas, module interfaces)
5. Programmer (Code implementation & integration)
6. Auditor (Static schema verification & cross-file reference linting)
7. Player (Frame-stepping runtime testbot, visual & feel feedback)
8. Reviewer (Adversarial 3D Gate: Functionality, Visuals, Playability)
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from core.frame_stepping_controller import FrameSteppingController, SceneNode


@dataclass
class ReviewResult:
    passed: bool
    overall_score: float
    functionality_score: float
    visual_score: float
    playability_score: float
    feedback_notes: List[str] = field(default_factory=list)
    repair_tickets: List[str] = field(default_factory=list)


class AdversarialAgentTeam:
    """
    Orchestrates the 8-Agent team through 3 phases:
    1. Intention Alignment (Designer GDD + Artist Ground Truth)
    2. Parallel Development (Architect -> Programmer -> Auditor -> Player)
    3. Adversarial Correction (Reviewer 3D Gate & Feedback Loop)
    """

    def __init__(self):
        self.worktree_branches: Dict[str, Dict[str, Any]] = {}
        self.gdd_ground_truth: Dict[str, Any] = {}
        self.visual_ground_truth: Dict[str, Any] = {}
        self.iteration_count = 0

    # Phase 1: Intention Alignment
    def align_intention(self, raw_prompt: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Designer & Artist align to create GDD and Visual Ground Truth.
        """
        # Designer expands prompt into formal GDD
        gdd = {
            "title": "Sekiro Boss Fight" if "boss" in raw_prompt.lower() else "Action Arena",
            "mechanics": ["Parry", "PostureSystem", "ExecuteOnBreak", "ScreenShake"],
            "parry_window_frames": 6,
            "boss_max_posture": 100.0,
            "deflect_posture_damage": 25.0,
            "target_fps": 60,
        }
        # Artist defines visual ground truth
        visuals = {
            "theme": "dark_fantasy_souls",
            "primary_color": "#e0a96d",
            "spark_color": "#ffe600",
            "hazard_color": "#ff0055",
            "required_assets": ["sprites/hero.png", "sprites/boss.png", "sprites/fx_parry.png"]
        }

        self.gdd_ground_truth = gdd
        self.visual_ground_truth = visuals
        return gdd, visuals

    # Phase 2: Parallel Development Pipeline
    def execute_development_pipeline(self, branch_name: str, scene_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes Architect -> Programmer -> Auditor -> Player in isolated worktree.
        """
        # 1. Architect defines schema & PRD
        prd = {
            "branch": branch_name,
            "scene_nodes": scene_nodes,
            "schema_version": "2.0.0"
        }

        # 2. Auditor checks static consistency
        auditor_errors = []
        for node in scene_nodes:
            asset = node.get("asset_ref", "")
            if asset not in self.visual_ground_truth.get("required_assets", []):
                auditor_errors.append(f"Auditor: Unanchored asset '{asset}' in node {node.get('node_id')}")

        # 3. Player runs deterministic simulation test via FrameSteppingController
        controller = FrameSteppingController()
        scene_config = {"nodes": scene_nodes}
        try:
            controller.load_scene(scene_config)
            # Inject: Boss attacks at tick 10, Player parries at tick 9
            controller.inject_action(at_tick=9, entity_id="player", action="PARRY")
            controller.inject_action(at_tick=10, entity_id="boss", action="ATTACK")
            controller.step(frames=20)
            player_snap = controller.get_current_snapshot()
            player_feedback = {
                "final_tick": player_snap.tick,
                "events_observed": player_snap.global_events,
                "simulation_stable": True
            }
        except Exception as e:
            player_feedback = {
                "simulation_stable": False,
                "error": str(e)
            }

        worktree_result = {
            "prd": prd,
            "auditor_clean": len(auditor_errors) == 0,
            "auditor_errors": auditor_errors,
            "player_feedback": player_feedback
        }
        self.worktree_branches[branch_name] = worktree_result
        return worktree_result

    # Phase 3: Adversarial Correction & Reviewer 3D Gate
    def adversarial_review(self, branch_name: str) -> ReviewResult:
        """
        Independent Reviewer evaluates on 3 Orthogonal Dimensions:
        1. Functionality (Logic strictly adheres to GDD without crash)
        2. Visual Quality (Assets anchor to visual ground truth, contrast)
        3. Playability (Parry window, feedback events, combat response)
        """
        self.iteration_count += 1
        worktree = self.worktree_branches.get(branch_name, {})
        auditor_clean = worktree.get("auditor_clean", False)
        player_feedback = worktree.get("player_feedback", {})

        # 1. Functionality Score
        func_score = 1.0 if (auditor_clean and player_feedback.get("simulation_stable", False)) else 0.4

        # 2. Visual Quality Score
        if not auditor_clean:
            vis_score = 0.60  # Deduct for asset mismatches
        else:
            vis_score = 0.95

        # 3. Playability Score (Check if deflect spark event was observed)
        events = player_feedback.get("events_observed", [])
        if "PERFECT_DEFLECT_SPARK" in events:
            play_score = 0.96
        elif "PLAYER_HIT" in events:
            play_score = 0.70  # Failed to parry, feedback poor
        else:
            play_score = 0.50

        overall = (func_score * 0.40) + (vis_score * 0.30) + (play_score * 0.30)
        passed = (overall >= 0.85) and (func_score >= 0.85) and (vis_score >= 0.80) and (play_score >= 0.80)

        notes = []
        tickets = []
        if not passed:
            if func_score < 0.85:
                notes.append("Functionality failed: simulation error or schema mismatch")
                tickets.append("TICKET_FIX_SCHEMA_INVARIANTS")
            if vis_score < 0.80:
                notes.append(f"Visual quality rejected: missing assets {worktree.get('auditor_errors')}")
                tickets.append("TICKET_REPLACE_UNANCHORED_ASSETS")
            if play_score < 0.80:
                notes.append("Playability rejected: parry timing window misaligned")
                tickets.append("TICKET_EXPAND_PARRY_WINDOW")
        else:
            notes.append("All 3 dimensions verified by Adversarial Reviewer!")

        return ReviewResult(
            passed=passed,
            overall_score=round(overall, 3),
            functionality_score=round(func_score, 3),
            visual_score=round(vis_score, 3),
            playability_score=round(play_score, 3),
            feedback_notes=notes,
            repair_tickets=tickets
        )
