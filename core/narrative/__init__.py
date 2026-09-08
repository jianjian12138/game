"""
Narrative System — 空间叙事触发器系统
======================================
基于空间区域和事件依赖图驱动的叙事系统。

用法::
    from core.narrative import TriggerZone, EventGraph, DialogueEngine

    graph = EventGraph.from_yaml("story/chapter1.yaml")
    zone  = TriggerZone.circle(cx=10, cy=20, radius=3.0,
                                event_id="enter_library")
    dlg   = DialogueEngine(graph)

    # 每帧检测
    triggered = zone.check(player_x, player_y)
    if triggered:
        dlg.trigger(zone.event_id, context)
"""

from .trigger_zone import TriggerZone, ZoneShape
from .event_graph import EventGraph, EventNode, EventStatus
from .dialogue_engine import DialogueEngine, DialogueLine
from .story_state import StoryState
from ..narrative_pedagogy_engine import (
    SLOMetricEvaluator,
    ThreeRoleNarrativePipeline,
    LegacyNarrativeHealer
)

__all__ = [
    "TriggerZone", "ZoneShape",
    "EventGraph", "EventNode", "EventStatus",
    "DialogueEngine", "DialogueLine",
    "StoryState",
    "SLOMetricEvaluator",
    "ThreeRoleNarrativePipeline",
    "LegacyNarrativeHealer",
]
