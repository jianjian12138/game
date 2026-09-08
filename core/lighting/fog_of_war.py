"""
Fog of War Grid System
Tracks 3-tier visibility (UNEXPLORED, EXPLORED, VISIBLE) for exploration & horror games.
"""

from enum import IntEnum
from typing import List, Tuple, Set


class FogTileState(IntEnum):
    UNEXPLORED = 0  # Pitch black / undiscovered
    EXPLORED = 1    # Discovered terrain, currently in fog
    VISIBLE = 2     # Direct line of sight / actively lit


class FogOfWar:
    """Manages 2D grid visibility states and player vision sweeps."""

    def __init__(self, width: int = 32, height: int = 32):
        self.width = width
        self.height = height
        self.grid: List[List[FogTileState]] = [
            [FogTileState.UNEXPLORED for _ in range(width)] for _ in range(height)
        ]

    def update_vision(self, center_x: int, center_y: int, radius: int):
        # 1. Downgrade previously VISIBLE tiles to EXPLORED
        for r in range(self.height):
            for c in range(self.width):
                if self.grid[r][c] == FogTileState.VISIBLE:
                    self.grid[r][c] = FogTileState.EXPLORED

        # 2. Mark tiles within vision radius as VISIBLE
        r2 = radius * radius
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if dr * dr + dc * dc <= r2:
                    tr = center_y + dr
                    tc = center_x + dc
                    if 0 <= tr < self.height and 0 <= tc < self.width:
                        self.grid[tr][tc] = FogTileState.VISIBLE

    def get_state(self, x: int, y: int) -> FogTileState:
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.grid[y][x]
        return FogTileState.UNEXPLORED

    def count_explored(self) -> Tuple[int, int]:
        total = self.width * self.height
        explored = sum(
            1 for r in range(self.height) for c in range(self.width)
            if self.grid[r][c] in [FogTileState.EXPLORED, FogTileState.VISIBLE]
        )
        return explored, total
