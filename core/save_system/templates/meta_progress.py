"""
Save Templates — Meta进度模板
==============================
适用于：Roguelike、Metroidvania 等有永久解锁系统的游戏。
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class MetaProgressTemplate:
    """
    Meta进度模板：跨局持久的解锁和成就数据。

    使用场景：
        - Roguelike 的永久解锁（角色/遗物/关卡）
        - 成就系统
        - 全局统计（总游玩时长/总局数/最高分）
    """

    # 解锁内容
    unlocked_characters: list = field(default_factory=list)
    unlocked_relics: list = field(default_factory=list)
    unlocked_levels: list = field(default_factory=list)
    unlocked_endings: list = field(default_factory=list)

    # 货币/资源（Meta层）
    meta_currency: int = 0          # 跨局货币（魂/月魄等）
    spent_meta_currency: int = 0

    # 成就
    achievements: dict = field(default_factory=dict)  # {id: timestamp}

    # 全局统计
    total_runs: int = 0
    total_wins: int = 0
    total_deaths: int = 0
    total_playtime_seconds: float = 0.0
    best_score: int = 0
    best_run_time_seconds: float = 0.0

    # 新手引导
    tutorials_completed: list = field(default_factory=list)

    def unlock(self, category: str, item_id: str) -> bool:
        """解锁一个内容项，返回是否为新解锁。"""
        attr = f"unlocked_{category}"
        collection = getattr(self, attr, None)
        if collection is None:
            return False
        if item_id not in collection:
            collection.append(item_id)
            return True
        return False

    def is_unlocked(self, category: str, item_id: str) -> bool:
        attr = f"unlocked_{category}"
        return item_id in getattr(self, attr, [])

    def record_run_end(self, won: bool, score: int, playtime: float):
        """记录一局结束。"""
        self.total_runs += 1
        self.total_playtime_seconds += playtime
        if won:
            self.total_wins += 1
        else:
            self.total_deaths += 1
        if score > self.best_score:
            self.best_score = score

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MetaProgressTemplate":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
