"""
Behavior Tree Nodes — 标准节点库
==================================
实现完整的 BT 节点类型：
  组合节点: Sequence, Selector, Parallel
  修饰节点: Inverter, Repeater, Timeout, Cooldown
  叶子节点: Condition, Action

所有节点返回 NodeStatus: SUCCESS / FAILURE / RUNNING
"""

from __future__ import annotations
import time
from enum import Enum
from typing import Callable, List, Optional, Any


class NodeStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


# ======================================================================
# 基类
# ======================================================================

class BTNode:
    """行为树节点基类。"""

    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__
        self._status: NodeStatus = NodeStatus.FAILURE

    def tick(self, blackboard: "Blackboard") -> NodeStatus:
        """执行节点逻辑，返回状态。子类必须实现。"""
        raise NotImplementedError

    def reset(self):
        """重置节点状态（用于重新开始树的执行）。"""
        self._status = NodeStatus.FAILURE

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.name}')"


# ======================================================================
# 组合节点 — Composite Nodes
# ======================================================================

class Sequence(BTNode):
    """
    顺序节点（AND逻辑）：
    依次执行子节点，任一子节点 FAILURE 则返回 FAILURE，
    全部 SUCCESS 则返回 SUCCESS，任一 RUNNING 则返回 RUNNING。
    """

    def __init__(self, children: List[BTNode], name: str = "Sequence"):
        super().__init__(name)
        self.children = children
        self._current_index = 0

    def tick(self, blackboard) -> NodeStatus:
        while self._current_index < len(self.children):
            child = self.children[self._current_index]
            status = child.tick(blackboard)
            if status == NodeStatus.FAILURE:
                self._current_index = 0
                return NodeStatus.FAILURE
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            # SUCCESS: 继续下一个
            self._current_index += 1

        self._current_index = 0
        return NodeStatus.SUCCESS

    def reset(self):
        super().reset()
        self._current_index = 0
        for c in self.children:
            c.reset()


class Selector(BTNode):
    """
    选择节点（OR逻辑）：
    依次执行子节点，任一 SUCCESS 则返回 SUCCESS，
    全部 FAILURE 则返回 FAILURE，任一 RUNNING 则返回 RUNNING。
    """

    def __init__(self, children: List[BTNode], name: str = "Selector"):
        super().__init__(name)
        self.children = children
        self._current_index = 0

    def tick(self, blackboard) -> NodeStatus:
        while self._current_index < len(self.children):
            child = self.children[self._current_index]
            status = child.tick(blackboard)
            if status == NodeStatus.SUCCESS:
                self._current_index = 0
                return NodeStatus.SUCCESS
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            # FAILURE: 尝试下一个
            self._current_index += 1

        self._current_index = 0
        return NodeStatus.FAILURE

    def reset(self):
        super().reset()
        self._current_index = 0
        for c in self.children:
            c.reset()


class Parallel(BTNode):
    """
    并行节点：同时 tick 所有子节点。
    success_threshold: 需要至少多少个子节点 SUCCESS 才算成功（默认全部）。
    """

    def __init__(
        self,
        children: List[BTNode],
        success_threshold: Optional[int] = None,
        name: str = "Parallel",
    ):
        super().__init__(name)
        self.children = children
        self.success_threshold = success_threshold or len(children)

    def tick(self, blackboard) -> NodeStatus:
        success_count = 0
        failure_count = 0

        for child in self.children:
            status = child.tick(blackboard)
            if status == NodeStatus.SUCCESS:
                success_count += 1
            elif status == NodeStatus.FAILURE:
                failure_count += 1

        if success_count >= self.success_threshold:
            return NodeStatus.SUCCESS
        if failure_count > len(self.children) - self.success_threshold:
            return NodeStatus.FAILURE
        return NodeStatus.RUNNING


# ======================================================================
# 修饰节点 — Decorator Nodes
# ======================================================================

class Inverter(BTNode):
    """反转子节点的 SUCCESS/FAILURE，RUNNING 透传。"""

    def __init__(self, child: BTNode, name: str = "Inverter"):
        super().__init__(name)
        self.child = child

    def tick(self, blackboard) -> NodeStatus:
        status = self.child.tick(blackboard)
        if status == NodeStatus.SUCCESS:
            return NodeStatus.FAILURE
        if status == NodeStatus.FAILURE:
            return NodeStatus.SUCCESS
        return NodeStatus.RUNNING


class Repeater(BTNode):
    """重复执行子节点。times=-1 表示无限重复。"""

    def __init__(self, child: BTNode, times: int = -1, name: str = "Repeater"):
        super().__init__(name)
        self.child = child
        self.times = times
        self._count = 0

    def tick(self, blackboard) -> NodeStatus:
        if self.times != -1 and self._count >= self.times:
            self._count = 0
            return NodeStatus.SUCCESS

        status = self.child.tick(blackboard)
        if status != NodeStatus.RUNNING:
            self._count += 1
            self.child.reset()
            if self.times != -1 and self._count >= self.times:
                self._count = 0
                return NodeStatus.SUCCESS
            return NodeStatus.RUNNING

        return NodeStatus.RUNNING

    def reset(self):
        super().reset()
        self._count = 0
        self.child.reset()


class Timeout(BTNode):
    """超时修饰：子节点在 time_limit 秒内未完成则强制返回 FAILURE。"""

    def __init__(self, child: BTNode, time_limit: float, name: str = "Timeout"):
        super().__init__(name)
        self.child = child
        self.time_limit = time_limit
        self._start_time: Optional[float] = None

    def tick(self, blackboard) -> NodeStatus:
        now = time.monotonic()
        if self._start_time is None:
            self._start_time = now

        if now - self._start_time > self.time_limit:
            self._start_time = None
            self.child.reset()
            return NodeStatus.FAILURE

        status = self.child.tick(blackboard)
        if status != NodeStatus.RUNNING:
            self._start_time = None
        return status

    def reset(self):
        super().reset()
        self._start_time = None
        self.child.reset()


class Cooldown(BTNode):
    """冷却修饰：子节点 SUCCESS 后进入冷却期，冷却中直接返回 FAILURE。"""

    def __init__(self, child: BTNode, cooldown: float, name: str = "Cooldown"):
        super().__init__(name)
        self.child = child
        self.cooldown = cooldown
        self._last_success: float = 0.0

    def tick(self, blackboard) -> NodeStatus:
        now = time.monotonic()
        if now - self._last_success < self.cooldown:
            return NodeStatus.FAILURE  # 冷却中

        status = self.child.tick(blackboard)
        if status == NodeStatus.SUCCESS:
            self._last_success = now
        return status

    def reset(self):
        super().reset()
        self._last_success = 0.0
        self.child.reset()


# ======================================================================
# 叶子节点 — Leaf Nodes
# ======================================================================

class Condition(BTNode):
    """
    条件节点：执行 predicate(blackboard) → bool，
    True → SUCCESS，False → FAILURE。
    """

    def __init__(self, predicate: Callable, name: str = "Condition"):
        super().__init__(name)
        self.predicate = predicate

    def tick(self, blackboard) -> NodeStatus:
        try:
            result = self.predicate(blackboard)
            return NodeStatus.SUCCESS if result else NodeStatus.FAILURE
        except Exception as e:
            print(f"[BT] Condition '{self.name}' 异常: {e}")
            return NodeStatus.FAILURE


class Action(BTNode):
    """
    动作节点：执行 action(blackboard) → NodeStatus。
    action 可返回 NodeStatus 枚举或 bool（True=SUCCESS，False=FAILURE）。
    """

    def __init__(self, action: Callable, name: str = "Action"):
        super().__init__(name)
        self.action = action

    def tick(self, blackboard) -> NodeStatus:
        try:
            result = self.action(blackboard)
            if isinstance(result, NodeStatus):
                return result
            return NodeStatus.SUCCESS if result else NodeStatus.FAILURE
        except Exception as e:
            print(f"[BT] Action '{self.name}' 异常: {e}")
            return NodeStatus.FAILURE
