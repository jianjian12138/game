"""
Save Templates — 世界状态模板
==============================
适用于：经营模拟、开放世界RPG 等拥有大地图状态的游戏。
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class WorldStateTemplate:
    """
    世界状态模板：整个游戏世界的持久化状态。

    设计原则：
        - 尽量使用可 JSON 序列化的基本类型
        - 实体（NPC/建筑/物品）用 ID 引用，不内嵌完整对象
        - 大型集合（地图格子）使用稀疏存储（只存非默认值）
    """

    # 游戏时间
    world_time: float = 0.0         # 游戏内时间（天/小时）
    day_count: int = 1
    season: str = "spring"          # spring/summer/autumn/winter

    # 玩家基础信息
    player_position: dict = field(default_factory=lambda: {"x": 0, "y": 0, "map": "town"})
    player_stats: dict = field(default_factory=dict)

    # 资源
    resources: dict = field(default_factory=dict)       # {"gold": 100, "wood": 50, ...}

    # 建筑（稀疏存储）
    # 格式: {"grid_x_y": {"type": "farm", "level": 2, "built_day": 3}}
    buildings: dict = field(default_factory=dict)

    # NPC 状态（只存与默认值不同的字段）
    npc_states: dict = field(default_factory=dict)      # {npc_id: {overrides}}

    # 任务进度
    quest_states: dict = field(default_factory=dict)    # {quest_id: "active"/"done"/"failed"}
    quest_variables: dict = field(default_factory=dict) # 任务内变量

    # 解锁区域
    explored_maps: list = field(default_factory=list)   # 已探索地图列表
    unlocked_areas: list = field(default_factory=list)

    # 事件历史（影响世界的决策记录）
    event_history: list = field(default_factory=list)   # [{"id": "event_1", "day": 5}]

    # 扩展字段（游戏专属数据）
    custom: dict = field(default_factory=dict)

    def add_resource(self, resource: str, amount: float):
        self.resources[resource] = self.resources.get(resource, 0) + amount

    def spend_resource(self, resource: str, amount: float) -> bool:
        current = self.resources.get(resource, 0)
        if current < amount:
            return False
        self.resources[resource] = current - amount
        return True

    def place_building(self, gx: int, gy: int, building_type: str, **attrs):
        key = f"{gx}_{gy}"
        self.buildings[key] = {"type": building_type, "built_day": self.day_count, **attrs}

    def advance_day(self):
        self.day_count += 1
        self.world_time += 1.0
        seasons = ["spring", "summer", "autumn", "winter"]
        season_idx = (self.day_count // 30) % 4
        self.season = seasons[season_idx]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorldStateTemplate":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
