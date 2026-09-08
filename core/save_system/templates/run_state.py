"""
Save Templates — 单局状态模板
==============================
适用于：Roguelike 当局进度，可在局内任意存档续玩。
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict


@dataclass
class RunStateTemplate:
    """
    单局状态模板：Roguelike 一局的完整运行时状态。

    注意：此模板仅用于局内存档（Suspend Save），
    局结束后应清除此存档并更新 MetaProgressTemplate。
    """

    # 种子（用于重现随机结果）
    seed: int = 0
    run_id: str = ""                # 唯一局 ID

    # 局内进度
    floor: int = 1                  # 当前层
    room_index: int = 0             # 当前层的第几个房间
    rooms_cleared: int = 0

    # 角色状态
    character_id: str = "default"
    hp: int = 100
    max_hp: int = 100
    gold: int = 0
    energy: int = 3                 # 每回合行动点

    # 物品/遗物
    inventory: list = field(default_factory=list)    # [{id, count, ...}]
    relics: list = field(default_factory=list)       # [relic_id, ...]
    status_effects: list = field(default_factory=list)  # [{id, stacks, duration}]

    # 卡组（如果有卡牌系统）
    deck: list = field(default_factory=list)         # [card_id, ...]
    hand: list = field(default_factory=list)
    discard_pile: list = field(default_factory=list)
    exhaust_pile: list = field(default_factory=list)

    # 当前房间状态（战斗/商店/事件）
    room_type: str = "battle"       # battle/shop/event/rest/boss
    room_state: dict = field(default_factory=dict)  # 房间专属数据

    # 统计
    kills: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0
    gold_earned: int = 0
    playtime_seconds: float = 0.0

    # 随机状态（用于种子重现）
    random_state: list = field(default_factory=list)  # Python random.getstate() 结果

    def is_alive(self) -> bool:
        return self.hp > 0

    def heal(self, amount: int):
        self.hp = min(self.hp + amount, self.max_hp)

    def take_damage(self, amount: int):
        self.hp = max(0, self.hp - amount)
        self.damage_taken += amount

    def add_gold(self, amount: int):
        self.gold += amount
        self.gold_earned += amount

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RunStateTemplate":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
