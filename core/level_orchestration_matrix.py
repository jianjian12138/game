"""
Level Orchestration Matrix (Article 38: Space, Content & Pacing)
Implements:
1. Nintendo 3-Scale Planner (CEDEC 2017: Distance, Density, Time-Scale)
2. Metroidvania / Dungeon Lock-and-Key Topology Validator
3. Tension & Release Pacing Engine (Dark Souls Bonfire / Rest Point Pacing)
"""

from typing import Dict, Any, List, Set, Tuple, Optional
import math

class POIItem:
    def __init__(self, poi_id: str, poi_type: str, x: float, y: float, estimated_duration_sec: float):
        self.poi_id = poi_id
        self.poi_type = poi_type # "SHRINE", "COMBAT_CAMP", "TREASURE", "BONFIRE", "LANDMARK"
        self.x = x
        self.y = y
        self.estimated_duration_sec = estimated_duration_sec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "poi_id": self.poi_id,
            "poi_type": self.poi_type,
            "x": self.x,
            "y": self.y,
            "estimated_duration_sec": self.estimated_duration_sec,
        }

class NintendoThreeScaleReport:
    def __init__(
        self,
        world_size: Tuple[float, float],
        total_pois: int,
        avg_poi_travel_time_sec: float,
        avg_micro_loop_duration_sec: float,
        density_compliance: bool,
        time_scale_compliance: bool,
        diagnostics: List[str]
    ):
        self.world_size = world_size
        self.total_pois = total_pois
        self.avg_poi_travel_time_sec = round(avg_poi_travel_time_sec, 1)
        self.avg_micro_loop_duration_sec = round(avg_micro_loop_duration_sec, 1)
        self.density_compliance = density_compliance
        self.time_scale_compliance = time_scale_compliance
        self.diagnostics = diagnostics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "world_size": self.world_size,
            "total_pois": self.total_pois,
            "avg_poi_travel_time_sec": self.avg_poi_travel_time_sec,
            "avg_micro_loop_duration_sec": self.avg_micro_loop_duration_sec,
            "density_compliance": self.density_compliance,
            "time_scale_compliance": self.time_scale_compliance,
            "diagnostics": self.diagnostics,
        }

class LevelOrchestrationMatrix:
    def __init__(self, player_move_speed: float = 5.0):
        self.player_move_speed = player_move_speed # units per second

    # -------------------------------------------------------------
    # 1. 任天堂三大尺度法则 (Distance, Density, Time-Scale)
    # -------------------------------------------------------------
    def audit_nintendo_three_scales(
        self,
        world_width: float,
        world_height: float,
        pois: List[POIItem],
        target_travel_time_sec: float = 60.0, # Player should encounter a new POI every 60s
        min_micro_loop_sec: float = 120.0,   # 2 minutes minimum loop
        max_micro_loop_sec: float = 300.0    # 5 minutes maximum loop
    ) -> NintendoThreeScaleReport:
        diagnostics = []
        if not pois:
            return NintendoThreeScaleReport(
                world_size=(world_width, world_height),
                total_pois=0,
                avg_poi_travel_time_sec=9999.0,
                avg_micro_loop_duration_sec=0.0,
                density_compliance=False,
                time_scale_compliance=False,
                diagnostics=["CRITICAL: Map has zero Points of Interest (POIs). Entire world is hollow."]
            )

        # 1. Density: Average nearest-neighbor travel time between POIs
        nearest_distances = []
        for i, p1 in enumerate(pois):
            min_dist = float("inf")
            for j, p2 in enumerate(pois):
                if i != j:
                    dist = math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
                    if dist < min_dist:
                        min_dist = dist
            if min_dist != float("inf"):
                nearest_distances.append(min_dist)

        avg_dist = sum(nearest_distances) / len(nearest_distances) if nearest_distances else 0.0
        avg_travel_time = avg_dist / self.player_move_speed

        density_compliance = (avg_travel_time <= target_travel_time_sec * 1.5)
        if not density_compliance:
            diagnostics.append(f"DENSITY WARNING: Avg travel time between POIs is {avg_travel_time:.1f}s (Target: <={target_travel_time_sec * 1.5:.1f}s). World feels too empty (Kingdom of Tears Depths effect).")

        # 2. Time-Scale (尺感): Average duration of micro-loops (shrine, combat camp)
        durations = [p.estimated_duration_sec for p in pois if p.poi_type in ["SHRINE", "COMBAT_CAMP", "TREASURE"]]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        time_scale_compliance = (min_micro_loop_sec <= avg_duration <= max_micro_loop_sec)
        if avg_duration < min_micro_loop_sec:
            diagnostics.append(f"TIME-SCALE WARNING: Micro-loops too shallow ({avg_duration:.1f}s < {min_micro_loop_sec}s). Player lacks sense of accomplishment.")
        elif avg_duration > max_micro_loop_sec:
            diagnostics.append(f"TIME-SCALE WARNING: Micro-loops too dragging ({avg_duration:.1f}s > {max_micro_loop_sec}s). Fatigue risk.")

        return NintendoThreeScaleReport(
            world_size=(world_width, world_height),
            total_pois=len(pois),
            avg_poi_travel_time_sec=avg_travel_time,
            avg_micro_loop_duration_sec=avg_duration,
            density_compliance=density_compliance,
            time_scale_compliance=time_scale_compliance,
            diagnostics=diagnostics
        )

    # -------------------------------------------------------------
    # 2. 空间锁与钥匙拓扑检查器 (Lock-and-Key Topology Validator)
    # -------------------------------------------------------------
    def validate_lock_and_key_dag(
        self,
        rooms: List[str],
        start_room: str,
        goal_room: str,
        connections: List[Tuple[str, str, Optional[str]]], # (from_room, to_room, required_key_id)
        key_locations: Dict[str, str]                       # key_id -> room_where_key_is_found
    ) -> Dict[str, Any]:
        """
        Validates Metroidvania / Zelda Dungeon Lock-Key graph.
        Ensures goal is reachable and all required keys can be obtained before their respective locks.
        """
        acquired_keys: Set[str] = set()
        visited_rooms: Set[str] = {start_room}
        
        changed = True
        step_log = []

        while changed:
            changed = False
            
            # 1. Collect keys from newly visited rooms
            for key_id, key_room in key_locations.items():
                if key_room in visited_rooms and key_id not in acquired_keys:
                    acquired_keys.add(key_id)
                    step_log.append(f"Acquired key '{key_id}' in room '{key_room}'")
                    changed = True

            # 2. Traverse reachable edges
            for u, v, req_key in connections:
                if u in visited_rooms and v not in visited_rooms:
                    if req_key is None or req_key in acquired_keys:
                        visited_rooms.add(v)
                        step_log.append(f"Unlocked/Traversed {u} -> {v}" + (f" using '{req_key}'" if req_key else ""))
                        changed = True

        goal_reachable = goal_room in visited_rooms
        unreachable_rooms = [r for r in rooms if r not in visited_rooms]
        unobtained_keys = [k for k in key_locations if k not in acquired_keys]

        return {
            "valid": goal_reachable and len(unreachable_rooms) == 0,
            "goal_reachable": goal_reachable,
            "unreachable_rooms": unreachable_rooms,
            "unobtained_keys": unobtained_keys,
            "step_log": step_log
        }
