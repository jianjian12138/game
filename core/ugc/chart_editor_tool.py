"""
UGC Rhythm Game Chart Editor Tool
Beat quantization, multi-lane note creation, mirror transformation, and chart export.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass
class ChartNote:
    note_id: str
    lane: int
    time_ms: float
    note_type: str = "TAP"
    duration_ms: float = 0.0


class ChartEditorTool:
    """Provides UGC authoring features for rhythm game charts."""

    def __init__(self, bpm: float = 120.0, lane_count: int = 4):
        self.bpm = bpm
        self.lane_count = lane_count
        self.notes: Dict[str, ChartNote] = {}
        self._seq = 0

    def add_note(self, lane: int, time_ms: float, note_type: str = "TAP", duration_ms: float = 0.0) -> ChartNote:
        self._seq += 1
        nid = f"note_{self._seq}"
        n = ChartNote(note_id=nid, lane=max(0, min(self.lane_count - 1, lane)),
                      time_ms=time_ms, note_type=note_type, duration_ms=duration_ms)
        self.notes[nid] = n
        return n

    def remove_note(self, note_id: str) -> bool:
        if note_id in self.notes:
            del self.notes[note_id]
            return True
        return False

    def quantize(self, division: int = 4):
        """Snaps all notes to nearest fractional beat interval."""
        beat_ms = 60000.0 / self.bpm
        step_ms = beat_ms / (division / 4.0)
        for n in self.notes.values():
            snapped = round(n.time_ms / step_ms) * step_ms
            n.time_ms = round(snapped, 1)

    def mirror_lanes(self):
        """Horizontally flips note lanes across center axis."""
        for n in self.notes.values():
            n.lane = (self.lane_count - 1) - n.lane

    def serialize(self) -> Dict[str, Any]:
        sorted_notes = sorted(self.notes.values(), key=lambda n: n.time_ms)
        return {
            "bpm": self.bpm,
            "lane_count": self.lane_count,
            "notes_count": len(sorted_notes),
            "notes": [
                {"id": n.note_id, "lane": n.lane, "time_ms": n.time_ms, "type": n.note_type, "duration_ms": n.duration_ms}
                for n in sorted_notes
            ]
        }
