"""
Hitbox Manager — 三层判定箱管理
==================================
格斗游戏判定箱三层系统：
  攻击判定（Hurtbox）: 己方可被击中的区域（绿色）
  受身判定（Hitbox）:  己方攻击可命中对方的区域（红色）
  推挤判定（Pushbox）: 防止角色重叠的物理碰撞区域（蓝色）

命名约定（业界标准）：
  Hitbox  = 攻击方的命中区域（红）
  Hurtbox = 被攻击方的受伤区域（绿）
  注意：部分文档用法相反，这里用业界主流定义。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class HitboxType(Enum):
    HITBOX  = "hitbox"    # 攻击区域（红色）
    HURTBOX = "hurtbox"   # 受伤区域（绿色）
    PUSHBOX = "pushbox"   # 推挤区域（蓝色）


@dataclass
class Hitbox:
    """单个判定箱（AABB矩形）。"""
    htype: HitboxType
    x: float        # 相对角色中心的 X 偏移
    y: float        # 相对角色中心的 Y 偏移
    w: float        # 宽度
    h: float        # 高度
    active: bool = True     # 是否激活

    @property
    def left(self):   return self.x - self.w / 2
    @property
    def right(self):  return self.x + self.w / 2
    @property
    def top(self):    return self.y + self.h / 2
    @property
    def bottom(self): return self.y - self.h / 2

    def overlaps(self, other: "Hitbox") -> bool:
        """AABB 重叠检测。"""
        return (self.left < other.right and self.right > other.left and
                self.bottom < other.top and self.top > other.bottom)

    def translated(self, cx: float, cy: float) -> "Hitbox":
        """返回以角色世界坐标为中心的绝对坐标判定箱。"""
        return Hitbox(
            htype=self.htype,
            x=cx + self.x,
            y=cy + self.y,
            w=self.w,
            h=self.h,
            active=self.active,
        )


class HitboxManager:
    """
    管理两个角色之间的判定箱碰撞检测。

    用法::
        hm = HitboxManager()

        # 注册角色判定箱（一般从帧数据中读取）
        hm.register("p1", hitboxes=[
            Hitbox(HitboxType.HITBOX,  0.5, 0.3, 0.8, 0.4),
            Hitbox(HitboxType.HURTBOX, 0.0, 0.5, 0.6, 1.2),
            Hitbox(HitboxType.PUSHBOX, 0.0, 0.0, 0.5, 1.0),
        ])

        # 每帧检测
        hits = hm.check_hits("p1", p1_pos, "p2", p2_pos)
        for hit in hits:
            apply_damage(hit)
    """

    def __init__(self):
        self._character_boxes: dict[str, list[Hitbox]] = {}

    def register(self, char_id: str, hitboxes: list[Hitbox]):
        """注册角色的当前帧判定箱组。"""
        self._character_boxes[char_id] = hitboxes

    def clear(self, char_id: str):
        """清除角色的判定箱（招式结束时调用）。"""
        self._character_boxes.pop(char_id, None)

    def check_hits(
        self,
        attacker_id: str, attacker_pos: tuple[float, float],
        defender_id: str, defender_pos: tuple[float, float],
    ) -> list[dict]:
        """
        检查 attacker 的攻击判定与 defender 的受伤判定是否重叠。

        Returns:
            命中事件列表 [{"attacker": ..., "defender": ..., "hitbox": ...}]
        """
        atk_boxes = self._character_boxes.get(attacker_id, [])
        def_boxes = self._character_boxes.get(defender_id, [])

        events = []
        ax, ay = attacker_pos
        dx, dy = defender_pos

        for a_box in atk_boxes:
            if not a_box.active or a_box.htype != HitboxType.HITBOX:
                continue
            abs_a = a_box.translated(ax, ay)

            for d_box in def_boxes:
                if not d_box.active or d_box.htype != HitboxType.HURTBOX:
                    continue
                abs_d = d_box.translated(dx, dy)

                if abs_a.overlaps(abs_d):
                    events.append({
                        "attacker": attacker_id,
                        "defender": defender_id,
                        "hitbox": abs_a,
                        "hurtbox": abs_d,
                    })

        return events

    def check_pushbox_overlap(
        self,
        char_a_id: str, pos_a: tuple[float, float],
        char_b_id: str, pos_b: tuple[float, float],
    ) -> Optional[float]:
        """
        检查推挤判定是否重叠，返回需要推开的 X 距离（正=A向右推，负=A向左推）。
        """
        a_boxes = self._character_boxes.get(char_a_id, [])
        b_boxes = self._character_boxes.get(char_b_id, [])

        for ab in a_boxes:
            if ab.htype != HitboxType.PUSHBOX:
                continue
            for bb in b_boxes:
                if bb.htype != HitboxType.PUSHBOX:
                    continue
                abs_a = ab.translated(*pos_a)
                abs_b = bb.translated(*pos_b)
                if abs_a.overlaps(abs_b):
                    overlap = min(abs_a.right, abs_b.right) - max(abs_a.left, abs_b.left)
                    direction = 1 if pos_a[0] < pos_b[0] else -1
                    return -direction * overlap / 2
        return None

    def boxes_for(self, char_id: str, htype: HitboxType) -> list[Hitbox]:
        return [b for b in self._character_boxes.get(char_id, [])
                if b.htype == htype]
