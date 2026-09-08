"""
Level & Onboarding Funnel Analyzer
Computes conversion rates, step-by-step dropoff percentages,
and pinpoints player churn bottlenecks.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from .event_tracker import TrackedEvent


@dataclass
class FunnelStep:
    name: str
    event_name: str
    filter_key: Optional[str] = None
    filter_val: Optional[Any] = None


class FunnelAnalyzer:
    """Evaluates user progression through defined sequence of milestone steps."""

    def __init__(self, steps: List[FunnelStep]):
        self.steps = steps

    def analyze(self, events: List[TrackedEvent]) -> Dict[str, Any]:
        if not self.steps:
            return {"steps_data": [], "total_users": 0, "overall_conversion_pct": 0.0}

        # Group events by user_id and sort chronologically
        user_events: Dict[str, List[TrackedEvent]] = {}
        for e in events:
            user_events.setdefault(e.user_id, []).append(e)

        for u in user_events:
            user_events[u].sort(key=lambda x: x.timestamp)

        step_user_sets: List[set] = [set() for _ in self.steps]

        # For each user, check how far down the sequential funnel they reached
        for uid, evts in user_events.items():
            step_idx = 0
            for e in evts:
                if step_idx < len(self.steps):
                    req_step = self.steps[step_idx]
                    matches_event = (e.event_name == req_step.event_name)
                    matches_filter = True
                    if req_step.filter_key:
                        matches_filter = (e.properties.get(req_step.filter_key) == req_step.filter_val)

                    if matches_event and matches_filter:
                        step_user_sets[step_idx].add(uid)
                        step_idx += 1

        total_users = len(user_events)
        step_counts = [len(s) for s in step_user_sets]

        steps_data = []
        for i, step in enumerate(self.steps):
            cnt = step_counts[i]
            prev_cnt = step_counts[i - 1] if i > 0 else (step_counts[0] if step_counts else 1)
            dropoff = (prev_cnt - cnt) if prev_cnt > 0 else 0
            dropoff_pct = (dropoff / max(1, prev_cnt)) * 100.0 if prev_cnt > 0 else 0.0
            conv_from_start = (cnt / max(1, step_counts[0])) * 100.0 if step_counts[0] > 0 else 0.0

            steps_data.append({
                "step_index": i + 1,
                "step_name": step.name,
                "user_count": cnt,
                "dropoff_count": dropoff,
                "dropoff_pct": round(dropoff_pct, 1),
                "conversion_from_start_pct": round(conv_from_start, 1)
            })

        overall_conv = steps_data[-1]["conversion_from_start_pct"] if steps_data else 0.0
        biggest_drop_step = max(steps_data, key=lambda s: s["dropoff_pct"]) if steps_data else None

        return {
            "total_users": total_users,
            "starting_users": step_counts[0] if step_counts else 0,
            "finished_users": step_counts[-1] if step_counts else 0,
            "overall_conversion_pct": overall_conv,
            "biggest_drop_step": biggest_drop_step["step_name"] if biggest_drop_step else "None",
            "steps_data": steps_data
        }
