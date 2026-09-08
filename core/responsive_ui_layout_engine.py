"""
Universal Responsive Game UI/UX Layout Engine (Article 47 - Game-Responsive-UI-UX Skill)
Solves:
1. 9-Anchor layout coordinate calculation across any aspect ratio (PC 16:9, Mobile 19.5:9, iPad 4:3)
2. Safe Area Insets (Mobile notch/pill top padding and home gesture bottom bar)
3. Virtual Reference Resolution scaling (Match Width / Match Height)
4. Screen Stack Navigation Router (Push, Pop, Replace)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


class AnchorPoint(str, Enum):
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    MIDDLE_LEFT = "middle_left"
    CENTER = "center"
    MIDDLE_RIGHT = "middle_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    STRETCH = "stretch"


@dataclass
class SafeAreaInsets:
    top: float = 0.0      # e.g. 44px on iPhone notch
    bottom: float = 0.0   # e.g. 34px on iPhone home bar
    left: float = 0.0
    right: float = 0.0


@dataclass
class ScreenMetrics:
    width: float = 1920.0
    height: float = 1080.0
    safe_area: SafeAreaInsets = field(default_factory=SafeAreaInsets)
    ref_width: float = 1920.0
    ref_height: float = 1080.0


@dataclass
class UIWidget:
    widget_id: str
    anchor: AnchorPoint
    offset_x: float = 0.0
    offset_y: float = 0.0
    width: float = 100.0
    height: float = 40.0
    respect_safe_area: bool = True


@dataclass
class LayoutRect:
    x: float
    y: float
    width: float
    height: float


class ResponsiveLayoutSolver:
    """
    Computes absolute pixel layout rectangles for 9-anchor UI elements
    with safe area insets and reference scaling.
    """

    @staticmethod
    def solve(widget: UIWidget, screen: ScreenMetrics) -> LayoutRect:
        # 1. Effective bounds considering safe area
        if widget.respect_safe_area:
            eff_x = screen.safe_area.left
            eff_y = screen.safe_area.top
            eff_w = screen.width - screen.safe_area.left - screen.safe_area.right
            eff_h = screen.height - screen.safe_area.top - screen.safe_area.bottom
        else:
            eff_x = 0.0
            eff_y = 0.0
            eff_w = screen.width
            eff_h = screen.height

        w = widget.width
        h = widget.height

        # 2. Anchor position mapping
        if widget.anchor == AnchorPoint.TOP_LEFT:
            x = eff_x + widget.offset_x
            y = eff_y + widget.offset_y
        elif widget.anchor == AnchorPoint.TOP_CENTER:
            x = eff_x + (eff_w - w) / 2.0 + widget.offset_x
            y = eff_y + widget.offset_y
        elif widget.anchor == AnchorPoint.TOP_RIGHT:
            x = eff_x + eff_w - w - widget.offset_x
            y = eff_y + widget.offset_y
        elif widget.anchor == AnchorPoint.MIDDLE_LEFT:
            x = eff_x + widget.offset_x
            y = eff_y + (eff_h - h) / 2.0 + widget.offset_y
        elif widget.anchor == AnchorPoint.CENTER:
            x = eff_x + (eff_w - w) / 2.0 + widget.offset_x
            y = eff_y + (eff_h - h) / 2.0 + widget.offset_y
        elif widget.anchor == AnchorPoint.MIDDLE_RIGHT:
            x = eff_x + eff_w - w - widget.offset_x
            y = eff_y + (eff_h - h) / 2.0 + widget.offset_y
        elif widget.anchor == AnchorPoint.BOTTOM_LEFT:
            x = eff_x + widget.offset_x
            y = eff_y + eff_h - h - widget.offset_y
        elif widget.anchor == AnchorPoint.BOTTOM_CENTER:
            x = eff_x + (eff_w - w) / 2.0 + widget.offset_x
            y = eff_y + eff_h - h - widget.offset_y
        elif widget.anchor == AnchorPoint.BOTTOM_RIGHT:
            x = eff_x + eff_w - w - widget.offset_x
            y = eff_y + eff_h - h - widget.offset_y
        elif widget.anchor == AnchorPoint.STRETCH:
            x = eff_x
            y = eff_y
            w = eff_w
            h = eff_h
        else:
            x = eff_x + widget.offset_x
            y = eff_y + widget.offset_y

        return LayoutRect(round(x, 1), round(y, 1), round(w, 1), round(h, 1))


class ScreenStackManager:
    """
    Manages LIFO screen stack navigation router (e.g. MainMenu -> Gameplay -> PauseMenu -> Inventory).
    """

    def __init__(self, initial_screen: str = "MAIN_MENU"):
        self.stack: List[str] = [initial_screen]

    def push(self, screen_id: str):
        self.stack.append(screen_id)

    def pop(self) -> Optional[str]:
        if len(self.stack) > 1:
            return self.stack.pop()
        return None  # Cannot pop root screen

    def replace(self, screen_id: str):
        if self.stack:
            self.stack.pop()
        self.stack.append(screen_id)

    def active_screen(self) -> str:
        return self.stack[-1] if self.stack else "NONE"

    def stack_depth(self) -> int:
        return len(self.stack)
