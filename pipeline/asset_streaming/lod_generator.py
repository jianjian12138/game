"""
Discrete Level of Detail (LOD) Generator & Distance Selector
Calculates triangle decimation ratios and assigns distance-based LOD tiers.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass
class LODLevel:
    level_index: int       # 0 = highest, 1 = medium, 2 = low
    max_distance: float    # switch to next level beyond this distance
    decimation_ratio: float  # 1.0 = 100%, 0.5 = 50% polygons
    triangle_count: int


class LODGenerator:
    """Configures and selects appropriate detail levels based on camera distance."""

    def __init__(self, lod_thresholds: Optional[List[float]] = None):
        # Default thresholds: LOD0 < 20m, LOD1 < 50m, LOD2 >= 50m
        self.thresholds = lod_thresholds or [20.0, 50.0]
        self.decimations = [1.0, 0.5, 0.2]

    def generate_lods(self, base_triangles: int) -> List[LODLevel]:
        lods = []
        for idx, ratio in enumerate(self.decimations):
            max_dist = self.thresholds[idx] if idx < len(self.thresholds) else float("inf")
            tris = max(12, int(round(base_triangles * ratio)))
            lods.append(LODLevel(level_index=idx, max_distance=max_dist, decimation_ratio=ratio, triangle_count=tris))
        return lods

    def select_lod(self, distance: float, lods: List[LODLevel]) -> LODLevel:
        for lod in lods:
            if distance <= lod.max_distance:
                return lod
        return lods[-1]
