"""
2D Shadow Caster and Ray Occlusion
Tests line-of-sight and shadow casting against 2D obstacle segments.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class LineSegment:
    x1: float
    y1: float
    x2: float
    y2: float


class ShadowCaster:
    """Computes geometric ray-segment intersections for 2D dynamic shadows."""

    def __init__(self, obstacles: Optional[List[LineSegment]] = None):
        self.obstacles: List[LineSegment] = obstacles or []

    def add_obstacle(self, segment: LineSegment):
        self.obstacles.append(segment)

    @staticmethod
    def _intersect(p1: Tuple[float, float], p2: Tuple[float, float],
                   q1: Tuple[float, float], q2: Tuple[float, float]) -> bool:
        """Determines if segment p1-p2 intersects segment q1-q2."""
        def ccw(a, b, c):
            return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

        return (ccw(p1, q1, q2) != ccw(p2, q1, q2)) and (ccw(p1, p2, q1) != ccw(p1, p2, q2))

    def is_occluded(self, light_pos: Tuple[float, float], target_pos: Tuple[float, float]) -> bool:
        """Returns True if any obstacle blocks the direct line from light to target."""
        for seg in self.obstacles:
            if self._intersect(light_pos, target_pos, (seg.x1, seg.y1), (seg.x2, seg.y2)):
                return True
        return False
