"""
2D Texture Atlas Bin Packer
Packs sprite rectangles into power-of-two texture atlases to reduce WebGL DrawCalls.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


@dataclass
class PackedRect:
    texture_id: str
    x: int
    y: int
    width: int
    height: int
    u0: float = 0.0
    v0: float = 0.0
    u1: float = 0.0
    v1: float = 0.0


class TextureAtlasPacker:
    """Shelf-based 2D bin packer for sprite sheets and texture atlases."""

    def __init__(self, atlas_width: int = 1024, atlas_height: int = 1024, padding: int = 2):
        self.atlas_w = atlas_width
        self.atlas_h = atlas_height
        self.padding = padding

    def pack(self, items: List[Tuple[str, int, int]]) -> Tuple[List[PackedRect], float]:
        """
        items: List of (id, width, height)
        Returns: (packed_rects, atlas_occupancy_ratio)
        """
        # Sort by height descending (best shelf packing heuristic)
        sorted_items = sorted(items, key=lambda x: x[2], reverse=True)

        packed: List[PackedRect] = []
        cur_x = self.padding
        cur_y = self.padding
        shelf_height = 0
        total_item_area = 0

        for tid, w, h in sorted_items:
            pw = w + self.padding * 2
            ph = h + self.padding * 2

            if cur_x + pw > self.atlas_w:
                # Next shelf
                cur_x = self.padding
                cur_y += shelf_height + self.padding
                shelf_height = 0

            if cur_y + ph > self.atlas_h:
                # Atlas full, cannot fit further
                break

            rect = PackedRect(
                texture_id=tid,
                x=cur_x,
                y=cur_y,
                width=w,
                height=h,
                u0=round(cur_x / self.atlas_w, 4),
                v0=round(cur_y / self.atlas_h, 4),
                u1=round((cur_x + w) / self.atlas_w, 4),
                v1=round((cur_y + h) / self.atlas_h, 4),
            )
            packed.append(rect)
            cur_x += pw
            shelf_height = max(shelf_height, ph)
            total_item_area += (w * h)

        occupancy = total_item_area / float(self.atlas_w * self.atlas_h)
        return packed, round(occupancy, 4)
