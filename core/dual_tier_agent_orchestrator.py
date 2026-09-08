"""
Dual-Tier Agent Orchestrator (Brain-Cerebellum Dual-System Architecture)
Based on Article 40 (Tencent Games WeTest Gamescom Dev Standard):
- MasterAgent: Coordinates mission state, manages memory, switches control.
- Brain (System 2): High-level cognitive reasoning, topological map navigation, subgoal decomposition.
- Cerebellum (System 1): High-frequency, low-latency reactive control, streams continuous Action Chunks.
"""

from typing import Dict, Any, List, Optional, Tuple
import math

class SubGoal:
    def __init__(self, goal_id: str, goal_type: str, target_location: Tuple[float, float], priority: int):
        self.goal_id = goal_id
        self.goal_type = goal_type # "NAVIGATE", "COMBAT_ENGAGE", "INTERACT", "FLEE"
        self.target_location = target_location
        self.priority = priority
        self.completed = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "goal_type": self.goal_type,
            "target_location": self.target_location,
            "priority": self.priority,
            "completed": self.completed,
        }

class ActionChunk:
    def __init__(self, actions: List[Dict[str, Any]]):
        self.actions = actions # Sequence of discrete micro-actions (e.g. 16 frames of move_x, move_y, buttons)
        self.current_index = 0

    def next_action(self) -> Optional[Dict[str, Any]]:
        if self.current_index < len(self.actions):
            act = self.actions[self.current_index]
            self.current_index += 1
            return act
        return None

    def is_exhausted(self) -> bool:
        return self.current_index >= len(self.actions)

class System2Brain:
    """Brain: System 2 deliberate cognitive planner (Topological Navigation & Intent)."""
    def __init__(self):
        self.topological_nodes: Dict[str, Tuple[float, float]] = {}
        self.plan_queue: List[SubGoal] = []

    def register_landmark(self, name: str, x: float, y: float):
        self.topological_nodes[name] = (x, y)

    def plan_mission(self, mission_target: str) -> List[SubGoal]:
        self.plan_queue.clear()
        if mission_target in self.topological_nodes:
            target_pos = self.topological_nodes[mission_target]
            # Decompose into waypoint and final engagement
            mid_x = target_pos[0] * 0.5
            mid_y = target_pos[1] * 0.5
            self.plan_queue.append(SubGoal("sub_nav_mid", "NAVIGATE", (mid_x, mid_y), 1))
            self.plan_queue.append(SubGoal("sub_engage", "COMBAT_ENGAGE", target_pos, 2))
        return list(self.plan_queue)

    def get_current_subgoal(self) -> Optional[SubGoal]:
        for g in self.plan_queue:
            if not g.completed:
                return g
        return None

class System1Cerebellum:
    """Cerebellum: System 1 reactive low-latency executor (Generates Action Chunks)."""
    def __init__(self, chunk_size: int = 16):
        self.chunk_size = chunk_size
        self.active_chunk: Optional[ActionChunk] = None

    def generate_action_chunk(self, current_pos: Tuple[float, float], subgoal: SubGoal, threat_nearby: bool) -> ActionChunk:
        """Generates a smooth sequence of micro-actions toward subgoal target."""
        tx, ty = subgoal.target_location
        dx = tx - current_pos[0]
        dy = ty - current_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)
        norm_x = (dx / dist) if dist > 0.001 else 0.0
        norm_y = (dy / dist) if dist > 0.001 else 0.0

        actions = []
        for step in range(self.chunk_size):
            action = {
                "step": step,
                "axis_x": round(norm_x, 3),
                "axis_y": round(norm_y, 3),
                "btn_attack": threat_nearby and (step % 4 == 0),
                "btn_dodge": threat_nearby and (step == 0),
            }
            actions.append(action)

        self.active_chunk = ActionChunk(actions)
        return self.active_chunk

class DualTierAgentOrchestrator:
    def __init__(self):
        self.brain = System2Brain()
        self.cerebellum = System1Cerebellum()
        self.current_position: Tuple[float, float] = (0.0, 0.0)

    def execute_step(self, player_pos: Tuple[float, float], threat_nearby: bool) -> Dict[str, Any]:
        """
        Executes one frame:
        - If Cerebellum has an active chunk, stream next action.
        - If chunk exhausted or goal reached, query Brain for next SubGoal and generate new chunk.
        """
        self.current_position = player_pos
        current_subgoal = self.brain.get_current_subgoal()

        if current_subgoal is None:
            return {"status": "MISSION_COMPLETE", "action": None}

        # Check if current subgoal reached (distance < 5.0)
        gx, gy = current_subgoal.target_location
        dist_to_goal = math.sqrt((gx - player_pos[0])**2 + (gy - player_pos[1])**2)
        if dist_to_goal < 5.0:
            current_subgoal.completed = True
            current_subgoal = self.brain.get_current_subgoal()
            if current_subgoal is None:
                return {"status": "MISSION_COMPLETE", "action": None}
            self.cerebellum.active_chunk = None # Invalidate chunk to regenerate for new subgoal

        # Check if Cerebellum needs new Action Chunk
        if self.cerebellum.active_chunk is None or self.cerebellum.active_chunk.is_exhausted():
            self.cerebellum.generate_action_chunk(player_pos, current_subgoal, threat_nearby)

        next_action = self.cerebellum.active_chunk.next_action()
        return {
            "status": "EXECUTING",
            "active_subgoal": current_subgoal.to_dict(),
            "action": next_action
        }
