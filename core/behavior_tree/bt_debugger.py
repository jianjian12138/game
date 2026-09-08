"""
BT Debugger — 行为树运行时状态可视化
=======================================
在终端以树形结构打印当前节点执行状态，方便开发调试。
"""

from __future__ import annotations
from .bt_nodes import BTNode, NodeStatus


_STATUS_ICONS = {
    NodeStatus.SUCCESS: "✅",
    NodeStatus.FAILURE: "❌",
    NodeStatus.RUNNING: "🔄",
}

_STATUS_COLORS = {
    NodeStatus.SUCCESS: "\033[92m",   # 绿
    NodeStatus.FAILURE: "\033[91m",   # 红
    NodeStatus.RUNNING: "\033[93m",   # 黄
}
_RESET = "\033[0m"


class BTDebugger:
    """
    行为树调试器：包裹根节点，每次 tick 后打印状态树。

    用法::
        tree = BTBuilder.from_yaml("presets/bt_boss.yaml", registry)
        debugger = BTDebugger(tree, print_every=1)
        status = debugger.tick(bb)
    """

    def __init__(self, root: BTNode, print_every: int = 1, use_color: bool = True):
        """
        Args:
            root:         根行为树节点
            print_every:  每 N 次 tick 打印一次（避免刷屏）
            use_color:    是否使用 ANSI 颜色
        """
        self.root = root
        self.print_every = print_every
        self.use_color = use_color
        self._tick_count = 0
        self._last_statuses: dict[int, NodeStatus] = {}

    def tick(self, blackboard) -> NodeStatus:
        """执行树并可选打印状态。"""
        # 包装节点以捕获状态
        status_map: dict[int, NodeStatus] = {}
        self._tick_with_trace(self.root, blackboard, status_map)
        self._last_statuses = status_map
        self._tick_count += 1

        if self._tick_count % self.print_every == 0:
            self.print_tree()

        return status_map.get(id(self.root), NodeStatus.FAILURE)

    def _tick_with_trace(self, node: BTNode, bb, status_map: dict) -> NodeStatus:
        """递归 tick 并记录每个节点状态。"""
        # 对复合节点先递归子节点
        children = getattr(node, "children", None)
        child = getattr(node, "child", None)

        if children:
            for c in children:
                self._tick_with_trace(c, bb, status_map)

        if child:
            self._tick_with_trace(child, bb, status_map)

        status = node.tick(bb)
        status_map[id(node)] = status
        return status

    def print_tree(self):
        """打印树状结构到终端。"""
        print(f"\n{'─'*50}")
        print(f"[BT Debugger] Tick #{self._tick_count}")
        print('─'*50)
        self._print_node(self.root, depth=0)
        print('─'*50)

    def _print_node(self, node: BTNode, depth: int):
        status = self._last_statuses.get(id(node), NodeStatus.FAILURE)
        icon = _STATUS_ICONS[status]
        indent = "  " * depth + ("└─ " if depth > 0 else "")

        if self.use_color:
            color = _STATUS_COLORS[status]
            line = f"{indent}{color}{icon} {node.name}{_RESET}"
        else:
            line = f"{indent}{icon} {node.name}"

        print(line)

        # 递归子节点
        for child in getattr(node, "children", []):
            self._print_node(child, depth + 1)
        if hasattr(node, "child") and node.child:
            self._print_node(node.child, depth + 1)
