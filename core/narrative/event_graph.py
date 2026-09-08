"""
Event Graph — 叙事事件依赖图
==============================
管理叙事事件的前置条件、触发和结果。
事件只有在所有前置条件满足时才能触发。

YAML 格式::

    events:
      find_key:
        name: 找到钥匙
        requires: []
        triggers: [unlock_door_hint]
        effect:
          - type: set_flag
            flag: has_key
            value: true
          - type: play_vfx
            asset: vfx_pickup

      unlock_door_hint:
        name: 门上出现光芒提示
        requires: [find_key]
        triggers: []
        effect:
          - type: activate_zone
            zone_id: door_zone

      open_door:
        name: 打开门
        requires: [find_key]
        condition: player_at_door
        triggers: [chapter2_start]
        effect:
          - type: play_animation
            target: door
            anim: door_open
          - type: unlock_area
            area: chapter2
"""

from __future__ import annotations
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class EventStatus(Enum):
    PENDING    = "pending"     # 等待触发
    TRIGGERED  = "triggered"   # 已触发
    COMPLETED  = "completed"   # 效果已执行
    LOCKED     = "locked"      # 前置条件未满足


@dataclass
class EventNode:
    """叙事事件节点。"""
    event_id: str
    name: str
    requires: list[str] = field(default_factory=list)   # 前置事件 ID 列表
    triggers: list[str] = field(default_factory=list)   # 触发的下游事件
    effects: list[dict] = field(default_factory=list)   # 效果列表
    condition: Optional[str] = None                     # 额外条件表达式
    status: EventStatus = EventStatus.PENDING
    trigger_count: int = 0


class EventGraph:
    """
    叙事事件依赖图：维护事件状态，驱动叙事流程。

    用法::
        graph = EventGraph.from_yaml("story/chapter1.yaml")

        # 触发事件
        effects = graph.trigger("find_key", context=game_context)

        # 检查状态
        if graph.is_completed("find_key"):
            show_door_hint()

        # 获取可触发的事件
        available = graph.available_events()
    """

    def __init__(self, events: dict[str, EventNode]):
        self._events = events

    # ------------------------------------------------------------------
    # 工厂方法
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str) -> "EventGraph":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "EventGraph":
        events = {}
        for eid, edef in data.get("events", {}).items():
            events[eid] = EventNode(
                event_id=eid,
                name=edef.get("name", eid),
                requires=edef.get("requires", []),
                triggers=edef.get("triggers", []),
                effects=edef.get("effect", []),
                condition=edef.get("condition"),
            )
        return cls(events)

    # ------------------------------------------------------------------
    # 核心 API
    # ------------------------------------------------------------------

    def trigger(self, event_id: str, context: dict = None) -> list[dict]:
        """
        触发事件，返回效果列表。

        前置条件不满足时返回空列表并打印警告。
        """
        context = context or {}
        node = self._events.get(event_id)
        if node is None:
            print(f"[EventGraph] 未知事件: {event_id}")
            return []

        if not self.can_trigger(event_id, context):
            print(f"[EventGraph] 前置条件未满足: {event_id}")
            return []

        node.status = EventStatus.TRIGGERED
        node.trigger_count += 1

        # 自动触发下游事件
        all_effects = list(node.effects)
        for downstream_id in node.triggers:
            downstream_effects = self.trigger(downstream_id, context)
            all_effects.extend(downstream_effects)

        node.status = EventStatus.COMPLETED
        print(f"[EventGraph] 事件触发: {node.name} ({event_id})")
        return all_effects

    def can_trigger(self, event_id: str, context: dict = None) -> bool:
        """检查事件是否可以触发（前置条件全部完成）。"""
        node = self._events.get(event_id)
        if node is None:
            return False
        for req_id in node.requires:
            if not self.is_completed(req_id):
                return False
        return True

    def is_completed(self, event_id: str) -> bool:
        node = self._events.get(event_id)
        return node is not None and node.status == EventStatus.COMPLETED

    def is_triggered(self, event_id: str) -> bool:
        node = self._events.get(event_id)
        return node is not None and node.status in (
            EventStatus.TRIGGERED, EventStatus.COMPLETED)

    def available_events(self) -> list[str]:
        """返回当前可触发（前置条件满足且未完成）的事件 ID 列表。"""
        return [
            eid for eid, node in self._events.items()
            if node.status == EventStatus.PENDING and self.can_trigger(eid)
        ]

    def get_flags(self) -> dict[str, bool]:
        """返回所有已完成事件的旗标字典（用于存档）。"""
        return {eid: node.status == EventStatus.COMPLETED
                for eid, node in self._events.items()}

    def restore_flags(self, flags: dict[str, bool]):
        """从存档恢复事件状态。"""
        for eid, completed in flags.items():
            if eid in self._events and completed:
                self._events[eid].status = EventStatus.COMPLETED
