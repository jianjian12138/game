"""
Client Lag Compensation & Interpolation Buffer
Provides smooth entity interpolation and server-side hit rewind validation.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple


@dataclass
class InterpolationSnapshot:
    timestamp: float
    positions: Dict[str, Tuple[float, float]]  # ent_id -> (x, y)


class LagCompensator:
    """Buffers entity positions over time and rewinds for fair hit-registration."""

    def __init__(self, buffer_duration_sec: float = 1.0, interp_delay_sec: float = 0.05):
        self.buffer: List[InterpolationSnapshot] = []
        self.buffer_duration_sec = buffer_duration_sec
        self.interp_delay_sec = interp_delay_sec

    def push_snapshot(self, timestamp: float, positions: Dict[str, Tuple[float, float]]):
        self.buffer.append(InterpolationSnapshot(timestamp, dict(positions)))
        # Prune old snapshots
        cutoff = timestamp - self.buffer_duration_sec
        self.buffer = [s for s in self.buffer if s.timestamp >= cutoff]

    def sample_interpolated_position(self, ent_id: str, render_time: float) -> Optional[Tuple[float, float]]:
        """Interpolates entity position between surrounding buffer frames."""
        target_time = render_time - self.interp_delay_sec
        if len(self.buffer) < 2:
            if self.buffer and ent_id in self.buffer[-1].positions:
                return self.buffer[-1].positions[ent_id]
            return None

        # Find two frames surrounding target_time
        before = None
        after = None
        for s in self.buffer:
            if s.timestamp <= target_time:
                before = s
            elif s.timestamp > target_time:
                after = s
                break

        if before and after and ent_id in before.positions and ent_id in after.positions:
            t1, p1 = before.timestamp, before.positions[ent_id]
            t2, p2 = after.timestamp, after.positions[ent_id]
            if t2 > t1:
                factor = (target_time - t1) / (t2 - t1)
                factor = max(0.0, min(1.0, factor))
                ix = p1[0] + (p2[0] - p1[0]) * factor
                iy = p1[1] + (p2[1] - p1[1]) * factor
                return round(ix, 2), round(iy, 2)

        if before and ent_id in before.positions:
            return before.positions[ent_id]
        if after and ent_id in after.positions:
            return after.positions[ent_id]
        return None

    def rewind_to_timestamp(self, timestamp: float) -> Dict[str, Tuple[float, float]]:
        """Returns entity positions at exact historical timestamp (lag compensation for hit-reg)."""
        positions: Dict[str, Tuple[float, float]] = {}
        all_ids = set()
        for s in self.buffer:
            all_ids.update(s.positions.keys())

        for eid in all_ids:
            pos = self.sample_interpolated_position(eid, timestamp + self.interp_delay_sec)
            if pos:
                positions[eid] = pos
        return positions
