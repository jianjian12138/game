"""
Trigger Zone — 空间触发器
===========================
定义游戏世界中的空间区域，当玩家进入/离开时触发事件。
支持圆形、矩形、自定义多边形三种形状。
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class ZoneShape(Enum):
    CIRCLE  = "circle"
    RECT    = "rect"
    POLYGON = "polygon"


@dataclass
class TriggerZone:
    """
    空间触发区域。

    用法::
        # 圆形区域
        zone = TriggerZone.circle(cx=100, cy=200, radius=50,
                                   event_id="enter_dungeon")

        # 矩形区域
        zone = TriggerZone.rect(left=0, top=0, right=200, bottom=100,
                                 event_id="safe_area")

        # 每帧检测
        if zone.check(player.x, player.y):
            # 首次进入触发
            if zone.just_entered:
                event_graph.trigger(zone.event_id)
    """

    event_id: str
    shape: ZoneShape
    # 圆形参数
    cx: float = 0.0
    cy: float = 0.0
    radius: float = 0.0
    # 矩形参数
    left: float = 0.0
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    # 多边形参数（顶点列表）
    vertices: list = field(default_factory=list)

    # 触发控制
    one_shot: bool = True       # 是否只触发一次
    triggered: bool = False     # 是否已触发
    active: bool = True         # 是否激活

    # 运行时状态
    _was_inside: bool = field(default=False, repr=False)
    just_entered: bool = field(default=False, repr=False)
    just_exited: bool = field(default=False, repr=False)

    # 回调（可选）
    on_enter: Optional[Callable] = field(default=None, repr=False)
    on_exit: Optional[Callable] = field(default=None, repr=False)

    # ------------------------------------------------------------------
    # 工厂方法
    # ------------------------------------------------------------------

    @classmethod
    def circle(cls, cx: float, cy: float, radius: float,
               event_id: str = "", **kwargs) -> "TriggerZone":
        return cls(event_id=event_id, shape=ZoneShape.CIRCLE,
                   cx=cx, cy=cy, radius=radius, **kwargs)

    @classmethod
    def rect(cls, left: float, top: float, right: float, bottom: float,
             event_id: str = "", **kwargs) -> "TriggerZone":
        return cls(event_id=event_id, shape=ZoneShape.RECT,
                   left=left, top=top, right=right, bottom=bottom, **kwargs)

    @classmethod
    def polygon(cls, vertices: list[tuple[float, float]],
                event_id: str = "", **kwargs) -> "TriggerZone":
        return cls(event_id=event_id, shape=ZoneShape.POLYGON,
                   vertices=list(vertices), **kwargs)

    # ------------------------------------------------------------------
    # 检测 API
    # ------------------------------------------------------------------

    def check(self, x: float, y: float) -> bool:
        """
        检查点 (x, y) 是否在区域内，并更新 just_entered/just_exited 状态。
        每帧调用一次。

        Returns:
            当前帧是否在区域内
        """
        if not self.active:
            return False
        if self.one_shot and self.triggered:
            return False

        inside = self._contains(x, y)

        self.just_entered = inside and not self._was_inside
        self.just_exited  = not inside and self._was_inside

        if self.just_entered:
            if self.one_shot:
                self.triggered = True
            if self.on_enter:
                self.on_enter(self)

        if self.just_exited and self.on_exit:
            self.on_exit(self)

        self._was_inside = inside
        return inside

    def reset(self):
        """重置触发状态（关卡重置时调用）。"""
        self.triggered = False
        self._was_inside = False
        self.just_entered = False
        self.just_exited = False

    # ------------------------------------------------------------------
    # 形状判断
    # ------------------------------------------------------------------

    def _contains(self, x: float, y: float) -> bool:
        if self.shape == ZoneShape.CIRCLE:
            return (x - self.cx) ** 2 + (y - self.cy) ** 2 <= self.radius ** 2
        if self.shape == ZoneShape.RECT:
            return self.left <= x <= self.right and self.top <= y <= self.bottom
        if self.shape == ZoneShape.POLYGON:
            return self._point_in_polygon(x, y)
        return False

    def _point_in_polygon(self, x: float, y: float) -> bool:
        """射线法判断点是否在多边形内。"""
        inside = False
        verts = self.vertices
        n = len(verts)
        j = n - 1
        for i in range(n):
            xi, yi = verts[i]
            xj, yj = verts[j]
            if ((yi > y) != (yj > y) and
                    x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside
