"""
Behavior Tree Framework — 行为树框架
======================================
标准化的行为树实现，支持 Sequence / Selector / Parallel / Decorator / Leaf 节点。
提供 YAML 构建器、黑板共享状态和终端调试器。

用法::
    from core.behavior_tree import BTBuilder, Blackboard

    bb = Blackboard({"hp": 80, "target": player})
    tree = BTBuilder.from_yaml("presets/bt_boss_phases.yaml")
    status = tree.tick(bb)          # NodeStatus.SUCCESS / FAILURE / RUNNING
"""

from .bt_nodes import (
    NodeStatus,
    BTNode,
    Sequence,
    Selector,
    Parallel,
    Inverter,
    Repeater,
    Timeout,
    Cooldown,
    Condition,
    Action,
)
from .bt_blackboard import Blackboard
from .bt_builder import BTBuilder
from .bt_debugger import BTDebugger

__all__ = [
    "NodeStatus",
    "BTNode",
    "Sequence",
    "Selector",
    "Parallel",
    "Inverter",
    "Repeater",
    "Timeout",
    "Cooldown",
    "Condition",
    "Action",
    "Blackboard",
    "BTBuilder",
    "BTDebugger",
]
