"""
Behavior Tree State Monitor
Traverses and formats running Behavior Tree node states with status tags and execution counts.
"""

from typing import Dict, Any, Optional
from core.behavior_tree.bt_nodes import BTNode, NodeStatus


class BTStateMonitor:
    """Renders hierarchical tree representation with live execution status."""

    STATUS_TAGS = {
        NodeStatus.SUCCESS: "[SUCCESS]",
        NodeStatus.FAILURE: "[FAILURE]",
        NodeStatus.RUNNING: "[RUNNING]",
    }

    @classmethod
    def render_tree(cls, root: BTNode, indent: int = 0) -> str:
        lines = []
        cur_status = getattr(root, "status", getattr(root, "_status", None))
        status_tag = cls.STATUS_TAGS.get(cur_status, "[ IDLE  ]")
        prefix = "  " * indent + "|-- " if indent > 0 else ""
        lines.append(f"{prefix}{status_tag} {root.__class__.__name__} ('{root.name}')")

        if hasattr(root, "children"):
            for child in root.children:
                lines.append(cls.render_tree(child, indent + 1))
        elif hasattr(root, "child") and root.child:
            lines.append(cls.render_tree(root.child, indent + 1))

        return "\n".join(lines)
