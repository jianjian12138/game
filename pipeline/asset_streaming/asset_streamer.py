"""
Priority-Queue Asset Streamer
Streams game assets based on camera proximity, frustum relevance, and bandwidth budget.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import heapq


@dataclass
class StreamedAsset:
    asset_id: str
    size_bytes: int
    world_pos: Tuple[float, float, float]
    state: str = "UNLOADED"  # "UNLOADED", "LOADED"
    priority: float = 0.0


class AssetStreamer:
    """Manages dynamic loading and eviction of spatial assets based on camera position."""

    def __init__(self, load_radius: float = 60.0, unload_radius: float = 80.0):
        self.load_radius = load_radius
        self.unload_radius = unload_radius
        self.catalog: Dict[str, StreamedAsset] = {}

    def register_asset(self, asset: StreamedAsset):
        self.catalog[asset.asset_id] = asset

    def update_streaming(self, camera_pos: Tuple[float, float, float], max_loads_per_frame: int = 3) -> Dict[str, List[str]]:
        loaded = []
        evicted = []

        load_candidates = []

        for a in self.catalog.values():
            dx = a.world_pos[0] - camera_pos[0]
            dy = a.world_pos[1] - camera_pos[1]
            dz = a.world_pos[2] - camera_pos[2]
            dist = (dx*dx + dy*dy + dz*dz) ** 0.5

            if a.state == "LOADED" and dist > self.unload_radius:
                a.state = "UNLOADED"
                evicted.append(a.asset_id)
            elif a.state == "UNLOADED" and dist <= self.load_radius:
                # Priority: closer distance = higher priority (lower distance value for min-heap)
                heapq.heappush(load_candidates, (dist, a))

        # Load top N candidates
        for _ in range(min(max_loads_per_frame, len(load_candidates))):
            dist, asset = heapq.heappop(load_candidates)
            asset.state = "LOADED"
            loaded.append(asset.asset_id)

        return {"loaded": loaded, "evicted": evicted}
