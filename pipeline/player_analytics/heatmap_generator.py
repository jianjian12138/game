"""
Player 2D Position & Death Heatmap Generator
Binned spatial frequency analysis for level design balance and death clusters.
"""

from typing import Dict, List, Any, Tuple, Optional
from .event_tracker import TrackedEvent


class HeatmapGenerator:
    """Generates 2D grid frequency heatmaps from spatial event telemetry."""

    def __init__(self, grid_w: int = 16, grid_h: int = 16, world_w: float = 100.0, world_h: float = 100.0):
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.world_w = world_w
        self.world_h = world_h
        self.density: List[List[int]] = [[0 for _ in range(grid_w)] for _ in range(grid_h)]
        self.total_points = 0

    def add_point(self, x: float, y: float, weight: int = 1):
        col = int((x / max(1.0, self.world_w)) * self.grid_w)
        row = int((y / max(1.0, self.world_h)) * self.grid_h)
        col = max(0, min(self.grid_w - 1, col))
        row = max(0, min(self.grid_h - 1, row))
        self.density[row][col] += weight
        self.total_points += weight

    def ingest_events(self, events: List[TrackedEvent], x_key: str = "x", y_key: str = "y", filter_event: Optional[str] = None):
        for e in events:
            if filter_event is None or e.event_name == filter_event:
                if x_key in e.properties and y_key in e.properties:
                    self.add_point(float(e.properties[x_key]), float(e.properties[y_key]))

    def get_max_cell(self) -> Tuple[int, int, int]:
        max_val = -1
        max_coord = (0, 0)
        for r in range(self.grid_h):
            for c in range(self.grid_w):
                if self.density[r][c] > max_val:
                    max_val = self.density[r][c]
                    max_coord = (c, r)
        return max_coord[0], max_coord[1], max_val

    def get_normalized_grid(self) -> List[List[float]]:
        _, _, max_val = self.get_max_cell()
        if max_val <= 0:
            return [[0.0 for _ in range(self.grid_w)] for _ in range(self.grid_h)]
        return [[round(self.density[r][c] / max_val, 3) for c in range(self.grid_w)] for r in range(self.grid_h)]

    def render_ascii(self) -> str:
        """Renders ASCII visualization using density intensity characters."""
        chars = [" ", ".", ":", "-", "=", "+", "*", "#", "%", "@"]
        norm = self.get_normalized_grid()
        lines = []
        for r in range(self.grid_h):
            row_str = "".join(chars[int(norm[r][c] * (len(chars) - 1))] for c in range(self.grid_w))
            lines.append(row_str)
        return "\n".join(lines)
