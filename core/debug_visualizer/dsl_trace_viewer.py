"""
DSL Execution Trace Viewer
Step-by-step logging and formatted table output for DSL effect evaluation.
"""

from typing import List, Dict, Any


class DSLTraceViewer:
    """Renders DSL runtime execution events in clean tabular format."""

    @staticmethod
    def render_trace(events: List[Dict[str, Any]]) -> str:
        if not events:
            return "No DSL execution events recorded."

        lines = ["=== DSL RUNTIME EXECUTION TRACE ==="]
        lines.append("| Step | Event Type | Target | Parameters / Effect |")
        lines.append("|:---|:---|:---|:---|")
        for i, ev in enumerate(events):
            etype = ev.get("type", "UNKNOWN")
            tgt = ev.get("target", "ALL")
            details = {k: v for k, v in ev.items() if k not in ["type", "target"]}
            lines.append(f"| {i + 1} | {etype} | {tgt} | {details} |")
        return "\n".join(lines)
