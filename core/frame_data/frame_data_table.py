"""
Frame Data Table — 招式帧数据表
================================
每个招式由三段组成：
  启动帧（Startup）: 动作开始到判定箱出现
  活跃帧（Active）:  判定箱存在，可造成命中
  硬直帧（Recovery）:判定箱消失到角色可再次行动

YAML 格式::

    character: ryu
    moves:
      light_punch:
        startup: 4
        active: 2
        recovery: 8
        damage: 30
        stun: 12
        cancel_into: [special, super]
        on_hit: +2            # 有利帧（正=攻击方有利）
        on_block: -2          # 格挡后帧差（负=攻击方不利）
        hitbox:
          x: 0.5
          y: 0.2
          w: 0.8
          h: 0.4

      hadouken:
        startup: 13
        active: 9
        recovery: 22
        damage: 70
        stun: 18
        cancel_into: [super]
        on_hit: -1
        on_block: -6
        type: projectile
        hitbox: {x: 1.0, y: 0.3, w: 0.5, h: 0.5}
"""

from __future__ import annotations
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class MovePhase(Enum):
    STARTUP  = "startup"
    ACTIVE   = "active"
    RECOVERY = "recovery"
    IDLE     = "idle"


@dataclass
class MoveData:
    """单个招式的完整帧数据。"""
    name: str
    startup: int        # 启动帧数
    active: int         # 活跃帧数
    recovery: int       # 硬直帧数
    damage: int = 0
    stun: int = 0
    on_hit: int = 0     # 命中帧差（正=攻击方有利）
    on_block: int = 0   # 格挡帧差
    cancel_into: list = field(default_factory=list)  # 可取消到的招式类别
    move_type: str = "normal"   # normal / special / super / projectile
    hitbox: dict = field(default_factory=dict)

    @property
    def total_frames(self) -> int:
        return self.startup + self.active + self.recovery

    def phase_at(self, frame: int) -> MovePhase:
        """给定执行帧数，返回当前所处阶段。"""
        if frame < self.startup:
            return MovePhase.STARTUP
        if frame < self.startup + self.active:
            return MovePhase.ACTIVE
        if frame < self.total_frames:
            return MovePhase.RECOVERY
        return MovePhase.IDLE

    def is_active(self, frame: int) -> bool:
        return self.phase_at(frame) == MovePhase.ACTIVE


class FrameDataTable:
    """
    角色招式帧数据表。

    用法::
        table = FrameDataTable.from_yaml("data/ryu_frames.yaml")
        move  = table.get("light_punch")
        phase = move.phase_at(current_frame)
    """

    def __init__(self, character: str, moves: dict[str, MoveData]):
        self.character = character
        self._moves = moves

    # ------------------------------------------------------------------
    # 工厂方法
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str) -> "FrameDataTable":
        """从 YAML 文件加载帧数据表。"""
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "FrameDataTable":
        character = data.get("character", "unknown")
        moves = {}
        for move_name, move_def in data.get("moves", {}).items():
            moves[move_name] = MoveData(
                name=move_name,
                startup=move_def.get("startup", 1),
                active=move_def.get("active", 1),
                recovery=move_def.get("recovery", 1),
                damage=move_def.get("damage", 0),
                stun=move_def.get("stun", 0),
                on_hit=move_def.get("on_hit", 0),
                on_block=move_def.get("on_block", 0),
                cancel_into=move_def.get("cancel_into", []),
                move_type=move_def.get("type", "normal"),
                hitbox=move_def.get("hitbox", {}),
            )
        return cls(character, moves)

    # ------------------------------------------------------------------
    # 查询 API
    # ------------------------------------------------------------------

    def get(self, move_name: str) -> Optional[MoveData]:
        return self._moves.get(move_name)

    def all_moves(self) -> list[str]:
        return list(self._moves.keys())

    def fastest_move(self) -> Optional[MoveData]:
        """返回启动帧最少的招式。"""
        if not self._moves:
            return None
        return min(self._moves.values(), key=lambda m: m.startup)

    def moves_by_type(self, move_type: str) -> list[MoveData]:
        return [m for m in self._moves.values() if m.move_type == move_type]

    def frame_advantage_ranking(self) -> list[tuple[str, int]]:
        """按命中帧差降序排列所有招式。"""
        ranked = [(name, m.on_hit) for name, m in self._moves.items()]
        return sorted(ranked, key=lambda x: x[1], reverse=True)

    def print_summary(self):
        """打印帧数据摘要（格斗游戏开发常用）。"""
        print(f"\n[FrameData] {self.character} 招式表")
        print(f"{'招式':<20} {'启动':>4} {'活跃':>4} {'硬直':>4} {'总计':>4} {'伤害':>5} {'命中帧差':>6}")
        print("-" * 55)
        for name, m in self._moves.items():
            print(f"{name:<20} {m.startup:>4} {m.active:>4} {m.recovery:>4} "
                  f"{m.total_frames:>4} {m.damage:>5} {m.on_hit:>+6}")
