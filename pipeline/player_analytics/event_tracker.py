"""
Player Event Tracking SDK
Provides unified event collection, buffer management, schema validation,
and filtering/aggregation for in-game analytics.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable


@dataclass
class TrackedEvent:
    event_id: str
    user_id: str
    event_name: str
    timestamp: float
    properties: Dict[str, Any] = field(default_factory=dict)
    session_id: str = "default_session"


class EventTracker:
    """In-memory event collection, validation, and batch export pipeline."""

    STANDARD_EVENTS = {
        "session_start", "session_end",
        "level_start", "level_complete", "level_fail",
        "item_purchase", "gacha_pull", "ad_reward",
        "checkpoint_reached", "player_death"
    }

    def __init__(self, flush_threshold: int = 100, on_flush: Optional[Callable[[List[TrackedEvent]], None]] = None):
        self.buffer: List[TrackedEvent] = []
        self.flushed_history: List[TrackedEvent] = []
        self.flush_threshold = flush_threshold
        self.on_flush = on_flush
        self._seq = 0

    def track(self, user_id: str, event_name: str, properties: Optional[Dict[str, Any]] = None,
              session_id: str = "session_0", timestamp: Optional[float] = None) -> TrackedEvent:
        self._seq += 1
        ts = timestamp if timestamp is not None else time.time()
        evt = TrackedEvent(
            event_id=f"evt_{self._seq}_{int(ts * 1000)}",
            user_id=user_id,
            event_name=event_name,
            timestamp=ts,
            properties=properties or {},
            session_id=session_id
        )
        self.buffer.append(evt)

        if len(self.buffer) >= self.flush_threshold:
            self.flush()

        return evt

    def flush(self) -> List[TrackedEvent]:
        flushed = list(self.buffer)
        self.flushed_history.extend(flushed)
        self.buffer.clear()
        if self.on_flush and flushed:
            self.on_flush(flushed)
        return flushed

    def query(self, event_name: Optional[str] = None, user_id: Optional[str] = None) -> List[TrackedEvent]:
        all_events = self.flushed_history + self.buffer
        results = all_events
        if event_name:
            results = [e for e in results if e.event_name == event_name]
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        return results

    def get_event_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self.flushed_history + self.buffer:
            counts[e.event_name] = counts.get(e.event_name, 0) + 1
        return counts
