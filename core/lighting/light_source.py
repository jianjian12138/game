"""
Light Source Representation and Attenuation
Supports Point lights, Cone/Spot lights, and Ambient lighting with distance and angular falloff.
"""

import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any


class LightType(str, Enum):
    POINT = "POINT"
    CONE = "CONE"
    AMBIENT = "AMBIENT"


@dataclass
class LightSource:
    light_id: str
    light_type: LightType
    x: float = 0.0
    y: float = 0.0
    radius: float = 100.0
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    direction: float = 0.0      # Radians, for CONE lights
    cone_angle: float = math.pi / 3.0  # Total cone spread angle in radians

    def get_intensity_at(self, target_x: float, target_y: float) -> float:
        """Calculates normalized light intensity [0.0 .. 1.0] at a given world point."""
        if self.light_type == LightType.AMBIENT:
            return self.intensity

        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)

        if dist > self.radius or self.radius <= 0:
            return 0.0

        # Distance falloff (smooth hermite / quadratic)
        norm_dist = dist / self.radius
        dist_factor = (1.0 - norm_dist) ** 2

        if self.light_type == LightType.POINT:
            return self.intensity * dist_factor

        elif self.light_type == LightType.CONE:
            # Check angle delta
            pt_angle = math.atan2(dy, dx)
            diff = (pt_angle - self.direction + math.pi) % (2.0 * math.pi) - math.pi
            half_cone = self.cone_angle * 0.5
            if abs(diff) > half_cone:
                return 0.0
            # Angular falloff toward edges of cone
            ang_factor = math.cos((abs(diff) / half_cone) * (math.pi * 0.5))
            return self.intensity * dist_factor * ang_factor

        return 0.0
