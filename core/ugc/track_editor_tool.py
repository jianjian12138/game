"""
UGC Racing Track Editor Tool
Interactive track spline waypoints, width adjustment, and loop closure arbitration.
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple


@dataclass
class TrackWaypoint:
    index: int
    x: float
    y: float
    width: float = 15.0
    is_checkpoint: bool = False


class TrackEditorTool:
    """Provides tools for players to design, inspect, and export custom racing circuits."""

    def __init__(self):
        self.waypoints: List[TrackWaypoint] = []

    def add_waypoint(self, x: float, y: float, width: float = 15.0, is_checkpoint: bool = False) -> TrackWaypoint:
        idx = len(self.waypoints)
        wp = TrackWaypoint(index=idx, x=x, y=y, width=width, is_checkpoint=is_checkpoint)
        self.waypoints.append(wp)
        return wp

    def remove_waypoint(self, index: int) -> bool:
        if 0 <= index < len(self.waypoints):
            self.waypoints.pop(index)
            # Re-index
            for i, p in enumerate(self.waypoints):
                p.index = i
            return True
        return False

    def get_track_length(self, is_closed_loop: bool = True) -> float:
        if len(self.waypoints) < 2:
            return 0.0
        length = 0.0
        n = len(self.waypoints)
        limit = n if is_closed_loop else (n - 1)
        for i in range(limit):
            p1 = self.waypoints[i]
            p2 = self.waypoints[(i + 1) % n]
            length += math.hypot(p2.x - p1.x, p2.y - p1.y)
        return round(length, 2)

    def validate_track(self) -> Dict[str, Any]:
        """Validates track continuity and minimum waypoint requirements."""
        errors = []
        if len(self.waypoints) < 3:
            errors.append("TOO_FEW_WAYPOINTS_NEED_AT_LEAST_3")
        length = self.get_track_length()
        if length < 50.0:
            errors.append("TRACK_TOO_SHORT")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "waypoints_count": len(self.waypoints),
            "track_length": length
        }

    def serialize(self) -> Dict[str, Any]:
        return {
            "track_length": self.get_track_length(),
            "waypoints": [
                {"idx": w.index, "x": w.x, "y": w.y, "width": w.width, "is_checkpoint": w.is_checkpoint}
                for w in self.waypoints
            ]
        }
