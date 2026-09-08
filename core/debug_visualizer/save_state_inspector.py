"""
Save State Inspector & Diff Viewer
Inspects save slot metadata, payload keys, integrity hashes, and diff patches.
"""

from typing import Dict, Any, Optional
from core.save_system.save_diff_engine import SaveDiffEngine


class SaveStateInspector:
    """Visualizes save payloads and compares incremental state changes."""

    @staticmethod
    def inspect_slot(save_data: Dict[str, Any]) -> str:
        lines = []
        meta = save_data.get("_meta", {})
        data = save_data.get("data", {})

        lines.append("=== SAVE STATE INSPECTION ===")
        lines.append(f"Format Version: {meta.get('version', 'N/A')}")
        lines.append(f"Slot Index:     {meta.get('slot_index', 'N/A')}")
        lines.append(f"Timestamp:      {meta.get('timestamp', 'N/A')}")
        lines.append(f"Checksum:       {meta.get('checksum', 'N/A')[:16]}...")
        lines.append("Payload Keys & Sample Values:")
        for k, v in data.items():
            val_str = str(v)
            if len(val_str) > 40:
                val_str = val_str[:37] + "..."
            lines.append(f"  - {k} ({type(v).__name__}): {val_str}")
        return "\n".join(lines)

    @staticmethod
    def compare_states(old_state: Dict[str, Any], new_state: Dict[str, Any]) -> str:
        diff = SaveDiffEngine.diff(old_state, new_state)
        lines = ["=== SAVE DIFF PATCH ==="]
        if not diff:
            lines.append("No changes detected (identical states).")
        else:
            for k, v in diff.items():
                lines.append(f"  [MODIFIED] {k}: {old_state.get(k)} -> {v}")
        return "\n".join(lines)
