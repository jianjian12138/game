"""
BT Builder — YAML → 行为树实例构建器
========================================
从 YAML 文件或字典构建完整的行为树。

YAML 格式::

    name: boss_ai
    root:
      type: Selector
      name: Boss主决策
      children:
        - type: Sequence
          name: 第三阶段（血量<30%）
          children:
            - type: Condition
              key: hp_below
              threshold: 30
            - type: Action
              name: 激活狂暴
              action: activate_berserk
            - type: Action
              name: 全屏弹幕
              action: fullscreen_barrage

        - type: Sequence
          name: 第二阶段（血量<60%）
          children:
            - type: Condition
              key: hp_below
              threshold: 60
            - type: Selector
              children:
                - type: Cooldown
                  cooldown: 5.0
                  child:
                    type: Action
                    action: charge_attack
                - type: Action
                  action: spiral_bullet

        - type: Action
          name: 默认攻击
          action: basic_attack
"""

import core.yaml_compat as yaml
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence

from .bt_nodes import (
    NodeStatus, BTNode, Sequence, Selector, Parallel,
    Inverter, Repeater, Timeout, Cooldown, Condition, Action,
)
from .bt_blackboard import Blackboard


class BTBuilder:
    """
    将 YAML 配置构建为 BTNode 树。
    使用 ActionRegistry 将动作名称映射到 Python 函数。
    """

    def __init__(self, action_registry: Optional[Dict[str, Callable]] = None):
        """
        Args:
            action_registry: {"action_name": callable(blackboard) → NodeStatus}
        """
        self.registry = action_registry or {}

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str, action_registry: dict = None) -> BTNode:
        """从 YAML 文件加载并构建行为树。"""
        builder = cls(action_registry or {})
        p = Path(path)
        config = yaml.safe_load(p.read_text(encoding="utf-8"))
        return builder.build(config)

    @classmethod
    def from_dict(cls, config: dict, action_registry: dict = None) -> BTNode:
        """从字典构建行为树。"""
        builder = cls(action_registry or {})
        return builder.build(config)

    def build(self, config: dict) -> BTNode:
        """构建完整树，返回根节点。"""
        root_def = config.get("root", config)  # 支持直接传入节点定义
        return self._build_node(root_def)

    def register_action(self, name: str, fn: Callable):
        """注册动作函数。"""
        self.registry[name] = fn

    # ------------------------------------------------------------------
    # 内部构建方法
    # ------------------------------------------------------------------

    def _build_node(self, node_def: dict) -> BTNode:
        ntype = node_def.get("type", "Action")
        name = node_def.get("name", ntype)

        builders = {
            "Sequence":  self._build_sequence,
            "Selector":  self._build_selector,
            "Parallel":  self._build_parallel,
            "Inverter":  self._build_inverter,
            "Repeater":  self._build_repeater,
            "Timeout":   self._build_timeout,
            "Cooldown":  self._build_cooldown,
            "Condition": self._build_condition,
            "Action":    self._build_action,
        }

        builder_fn = builders.get(ntype)
        if builder_fn is None:
            raise ValueError(f"未知的节点类型: '{ntype}'")
        return builder_fn(node_def, name)

    def _build_children(self, node_def: dict) -> list:
        return [self._build_node(c) for c in node_def.get("children", [])]

    def _build_sequence(self, d, name) -> Sequence:
        return Sequence(self._build_children(d), name=name)

    def _build_selector(self, d, name) -> Selector:
        return Selector(self._build_children(d), name=name)

    def _build_parallel(self, d, name) -> Parallel:
        threshold = d.get("success_threshold", None)
        return Parallel(self._build_children(d), success_threshold=threshold, name=name)

    def _build_inverter(self, d, name) -> Inverter:
        child = self._build_node(d["child"])
        return Inverter(child, name=name)

    def _build_repeater(self, d, name) -> Repeater:
        child = self._build_node(d["child"])
        return Repeater(child, times=d.get("times", -1), name=name)

    def _build_timeout(self, d, name) -> Timeout:
        child = self._build_node(d["child"])
        return Timeout(child, time_limit=d.get("time_limit", 5.0), name=name)

    def _build_cooldown(self, d, name) -> Cooldown:
        child = self._build_node(d["child"])
        return Cooldown(child, cooldown=d.get("cooldown", 3.0), name=name)

    def _build_condition(self, d, name) -> Condition:
        """从黑板键+阈值构建条件，或使用 lambda 表达式。"""
        key = d.get("key")
        threshold = d.get("threshold")
        op = d.get("op", "below")    # below / above / equal / has

        def predicate(bb: Blackboard) -> bool:
            val = bb.get(key)
            if val is None:
                return False
            if op == "below":
                return val < threshold
            if op == "above":
                return val > threshold
            if op == "equal":
                return val == threshold
            if op == "has":
                return bool(val)
            return False

        return Condition(predicate, name=name)

    def _build_action(self, d, name) -> Action:
        action_name = d.get("action", name)
        fn = self.registry.get(action_name)
        if fn is None:
            # 占位动作：打印日志，返回 SUCCESS
            def placeholder(bb, _n=action_name):
                print(f"[BT] 执行动作（未注册）: {_n}")
                return NodeStatus.SUCCESS
            fn = placeholder
        return Action(fn, name=name)
