"""
Universal AI-Native Frame-Stepping Controller (Article 43 - VibeGame Architecture)
Triad Attributes:
1. GUI-Independent: Game state expressed as type-checked JSON/dataclass schemas, pre-validating assets & references.
2. Runtime-Accessible: Exposes frame-stepping APIs (pause, step, inject_action, query_state) to transform real-time asynchronous systems into deterministic synchronous inspection flows.
3. Source-Available: Fully whitebox inspection and reproducible state assertions.
"""

import copy
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable, Tuple


@dataclass
class SceneNode:
    node_id: str
    node_type: str  # "player", "enemy", "boss", "projectile", "terrain", "hud"
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    hp: float = 100.0
    max_hp: float = 100.0
    posture: float = 0.0       # Sekiro posture bar (0~100)
    max_posture: float = 100.0
    state: str = "IDLE"        # "IDLE", "ATTACKING", "DEFENDING", "PARRYING", "STUNNED"
    parry_window_frames: int = 0
    hitbox_size: Tuple[float, float] = (32.0, 32.0)
    asset_ref: str = "sprites/default.png"
    tags: List[str] = field(default_factory=list)


@dataclass
class SceneSnapshot:
    tick: int
    time_sec: float
    nodes: Dict[str, SceneNode] = field(default_factory=dict)
    global_events: List[str] = field(default_factory=list)


class FrameSteppingController:
    """
    Universal Frame-Stepping Controller for AI-Native Game Engine Inspection.
    Enables agents to step simulation forward by exact frame increments,
    inject discrete semantic actions, and assert ground-truth state transitions.
    """

    def __init__(self, target_fps: int = 60):
        self.target_fps = target_fps
        self.dt = 1.0 / target_fps
        self.current_tick = 0
        self.time_sec = 0.0
        self.is_paused = False
        self.nodes: Dict[str, SceneNode] = {}
        self.history: List[SceneSnapshot] = []
        self.max_history: int = 600  # 10 seconds of 60 FPS rewind buffer
        self.action_queue: Dict[int, List[Dict[str, Any]]] = {}
        self.registered_assets: set = {"sprites/default.png", "sprites/hero.png", "sprites/boss.png", "sprites/fx_parry.png"}
        self.cumulative_events: List[str] = []

    def validate_scene_schema(self, scene_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        GUI-Independent Static Schema Validation.
        Detects missing assets, invalid node configurations, and unlinked references BEFORE runtime.
        """
        errors = []
        if "nodes" not in scene_config:
            errors.append("Missing required field 'nodes'")
            return False, errors

        for node_data in scene_config.get("nodes", []):
            node_id = node_data.get("node_id")
            if not node_id:
                errors.append("SceneNode missing 'node_id'")
                continue
            asset_ref = node_data.get("asset_ref", "")
            if asset_ref and asset_ref not in self.registered_assets:
                errors.append(f"Node '{node_id}' references missing asset '{asset_ref}'")
            if "node_type" not in node_data:
                errors.append(f"Node '{node_id}' missing 'node_type'")

        return len(errors) == 0, errors

    def load_scene(self, scene_config: Dict[str, Any]) -> bool:
        valid, errors = self.validate_scene_schema(scene_config)
        if not valid:
            raise ValueError(f"Scene schema validation failed: {errors}")

        self.nodes.clear()
        self.current_tick = 0
        self.time_sec = 0.0
        for nd in scene_config.get("nodes", []):
            node = SceneNode(
                node_id=nd["node_id"],
                node_type=nd["node_type"],
                x=nd.get("x", 0.0),
                y=nd.get("y", 0.0),
                vx=nd.get("vx", 0.0),
                vy=nd.get("vy", 0.0),
                hp=nd.get("hp", 100.0),
                max_hp=nd.get("max_hp", 100.0),
                posture=nd.get("posture", 0.0),
                max_posture=nd.get("max_posture", 100.0),
                state=nd.get("state", "IDLE"),
                hitbox_size=tuple(nd.get("hitbox_size", (32.0, 32.0))),
                asset_ref=nd.get("asset_ref", "sprites/default.png"),
                tags=nd.get("tags", [])
            )
            self.nodes[node.node_id] = node

        self._record_snapshot()
        return True

    def inject_action(self, at_tick: int, entity_id: str, action: str, params: Optional[Dict[str, Any]] = None):
        """
        Injects a semantic action at a specific tick for reproducible AI testbot replay.
        """
        if at_tick not in self.action_queue:
            self.action_queue[at_tick] = []
        self.action_queue[at_tick].append({
            "entity_id": entity_id,
            "action": action,
            "params": params or {}
        })

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def step(self, frames: int = 1) -> SceneSnapshot:
        """
        Advances the world by exact integer frame counts.
        Deterministic, whitebox, perfectly synchronized.
        """
        for _ in range(frames):
            self._step_single_frame()
        return self.get_current_snapshot()

    def _step_single_frame(self):
        self.current_tick += 1
        self.time_sec += self.dt
        events = []

        # 1. Process Injected Semantic Actions
        if self.current_tick in self.action_queue:
            for act in self.action_queue[self.current_tick]:
                eid = act["entity_id"]
                action = act["action"]
                params = act["params"]
                if eid in self.nodes:
                    self._apply_action(self.nodes[eid], action, params, events)

        # 2. Physics & State Machine Updates
        for node in self.nodes.values():
            # Update parry window timer
            if node.parry_window_frames > 0:
                node.parry_window_frames -= 1
                if node.parry_window_frames == 0 and node.state == "PARRYING":
                    node.state = "DEFENDING"

            # Apply velocity
            node.x += node.vx * self.dt
            node.y += node.vy * self.dt

        # 3. Combat Collision & Posture Arbitration (e.g. Sekiro Boss Combat)
        self._arbitrate_combat(events)

        if events:
            self.cumulative_events.extend(events)

        # Record History Snapshot with cumulative events
        self._record_snapshot(list(self.cumulative_events))

    def _apply_action(self, node: SceneNode, action: str, params: Dict[str, Any], events: List[str]):
        if action == "PARRY":
            # 6-frame active parry window
            node.state = "PARRYING"
            node.parry_window_frames = 6
            events.append(f"{node.node_id}_PARRY_START")
        elif action == "ATTACK":
            node.state = "ATTACKING"
            events.append(f"{node.node_id}_ATTACK")
        elif action == "MOVE":
            node.vx = params.get("vx", 0.0)
            node.vy = params.get("vy", 0.0)
        elif action == "STOP":
            node.vx = 0.0
            node.vy = 0.0

    def _arbitrate_combat(self, events: List[str]):
        player = self.nodes.get("player")
        boss = self.nodes.get("boss")
        if not player or not boss:
            return

        # Check proximity for attack contact
        dist = abs(player.x - boss.x)
        if dist < 48.0:
            # If Boss attacks Player
            if boss.state == "ATTACKING":
                if player.state == "PARRYING":
                    # Perfect Deflect! Boss takes heavy posture damage, player takes zero damage!
                    boss.posture += 25.0
                    events.append("PERFECT_DEFLECT_SPARK")
                    if boss.posture >= boss.max_posture:
                        boss.state = "STUNNED"
                        events.append("BOSS_POSTURE_BROKEN_EXECUTABLE")
                elif player.state == "DEFENDING":
                    # Regular Block: Player takes posture damage, no HP loss
                    player.posture += 15.0
                    events.append("BLOCK_GUARD")
                else:
                    # Direct Hit: Player loses HP
                    player.hp -= 20.0
                    events.append("PLAYER_HIT")
                boss.state = "IDLE"  # Reset attack after strike

    def _record_snapshot(self, events: Optional[List[str]] = None):
        snapshot = SceneSnapshot(
            tick=self.current_tick,
            time_sec=self.time_sec,
            nodes={nid: copy.deepcopy(n) for nid, n in self.nodes.items()},
            global_events=list(events or [])
        )
        self.history.append(snapshot)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_current_snapshot(self) -> SceneSnapshot:
        return self.history[-1] if self.history else SceneSnapshot(0, 0.0, {})

    def rewind(self, ticks: int) -> bool:
        """Rewinds the simulation backwards by exact ticks."""
        target_tick = max(0, self.current_tick - ticks)
        for snap in reversed(self.history):
            if snap.tick <= target_tick:
                self.current_tick = snap.tick
                self.time_sec = snap.time_sec
                self.nodes = {nid: copy.deepcopy(n) for nid, n in snap.nodes.items()}
                self.cumulative_events = list(snap.global_events)
                self.history = [s for s in self.history if s.tick <= snap.tick]
                return True
        return False
