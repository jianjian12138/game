"""
Story State — 叙事状态持久化
==============================
将叙事进度（事件旗标、对话历史、任务状态）持久化到存档系统。
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class StoryState:
    """
    叙事状态快照，可序列化到存档系统。

    用法::
        state = StoryState()
        state.set_flag("find_key", True)
        state.set_quest("main_quest", "active")

        # 存档
        from core.save_system import SaveSerializer
        world_save["story"] = state.to_dict()

        # 恢复
        state = StoryState.from_dict(world_save["story"])
        graph.restore_flags(state.event_flags)
    """

    # 事件旗标 {event_id: completed}
    event_flags: dict = field(default_factory=dict)

    # 任务状态 {quest_id: "active"/"done"/"failed"}
    quest_states: dict = field(default_factory=dict)

    # 任务内变量 {quest_id: {var: value}}
    quest_variables: dict = field(default_factory=dict)

    # 对话历史（用于显示"已读"标记）
    dialogue_history: list = field(default_factory=list)

    # NPC好感度 {npc_id: int}
    npc_affinity: dict = field(default_factory=dict)

    # 全局故事变量
    story_variables: dict = field(default_factory=dict)

    # 解锁的场景/区域
    unlocked_areas: list = field(default_factory=list)

    # ------------------------------------------------------------------
    # 旗标操作
    # ------------------------------------------------------------------

    def set_flag(self, event_id: str, value: bool = True):
        self.event_flags[event_id] = value

    def get_flag(self, event_id: str) -> bool:
        return self.event_flags.get(event_id, False)

    # ------------------------------------------------------------------
    # 任务操作
    # ------------------------------------------------------------------

    def set_quest(self, quest_id: str, status: str):
        """status: 'active' / 'done' / 'failed'"""
        self.quest_states[quest_id] = status

    def get_quest(self, quest_id: str) -> Optional[str]:
        return self.quest_states.get(quest_id)

    def is_quest_active(self, quest_id: str) -> bool:
        return self.quest_states.get(quest_id) == "active"

    def is_quest_done(self, quest_id: str) -> bool:
        return self.quest_states.get(quest_id) == "done"

    def set_quest_var(self, quest_id: str, var: str, value):
        self.quest_variables.setdefault(quest_id, {})[var] = value

    def get_quest_var(self, quest_id: str, var: str, default=None):
        return self.quest_variables.get(quest_id, {}).get(var, default)

    # ------------------------------------------------------------------
    # NPC好感度
    # ------------------------------------------------------------------

    def change_affinity(self, npc_id: str, delta: int):
        self.npc_affinity[npc_id] = self.npc_affinity.get(npc_id, 0) + delta

    def get_affinity(self, npc_id: str) -> int:
        return self.npc_affinity.get(npc_id, 0)

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "StoryState":
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})
