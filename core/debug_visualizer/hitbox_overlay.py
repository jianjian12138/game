"""
Hitbox Overlay Debug Visualizer
Visualizes 3-layer hitboxes (HITBOX, HURTBOX, PUSHBOX) in ASCII grid and collision report.
"""

from typing import List, Dict, Any, Tuple


class HitboxOverlay:
    """Renders ASCII bounding boxes and overlap markers for combat debugging."""

    def __init__(self, width: int = 30, height: int = 15, scale: float = 1.0):
        self.width = width
        self.height = height
        self.scale = scale

    def render_boxes(self, boxes: List[Dict[str, Any]]) -> str:
        """
        boxes: [{ "type": "HITBOX"|"HURTBOX"|"PUSHBOX", "x": float, "y": float, "w": float, "h": float }]
        Markers:
          HITBOX:  'H' (Red in terminal, 'H' in ascii)
          HURTBOX: 'U' (Green in terminal, 'U' in ascii)
          PUSHBOX: 'P' (Yellow in terminal, 'P' in ascii)
          OVERLAP: 'X'
        """
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]

        type_chars = {"HITBOX": "H", "HURTBOX": "U", "PUSHBOX": "P"}

        for b in boxes:
            btype = b.get("type", "HURTBOX")
            char = type_chars.get(btype, "?")
            x1 = int(b.get("x", 0) * self.scale)
            y1 = int(b.get("y", 0) * self.scale)
            w = int(b.get("w", 2) * self.scale)
            h = int(b.get("h", 2) * self.scale)

            for r in range(y1, min(self.height, y1 + h)):
                for c in range(x1, min(self.width, x1 + w)):
                    if 0 <= r < self.height and 0 <= c < self.width:
                        cur = grid[r][c]
                        if cur != " " and cur != char:
                            grid[r][c] = "X"  # Overlap
                        else:
                            grid[r][c] = char

        lines = ["+" + "-" * self.width + "+"]
        for row in grid:
            lines.append("|" + "".join(row) + "|")
        lines.append("+" + "-" * self.width + "+")
        lines.append("Legend: [H] Hitbox  [U] Hurtbox  [P] Pushbox  [X] Overlap Collision")
        return "\n".join(lines)
