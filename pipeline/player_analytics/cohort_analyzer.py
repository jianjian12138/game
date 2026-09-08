"""
Player Cohort & Retention Analysis
Calculates D1, D3, D7, D14, D30 retention matrices for player lifecycle evaluation.
"""

from typing import Dict, List, Any, Set, Optional
from .event_tracker import TrackedEvent


class CohortAnalyzer:
    """Groups users into installation day cohorts and tracks retention curves."""

    def __init__(self, day_duration_sec: float = 86400.0):
        self.day_duration_sec = day_duration_sec

    def analyze(self, events: List[TrackedEvent], base_start_time: Optional[float] = None) -> Dict[str, Any]:
        if not events:
            return {"cohorts": {}}

        min_time = base_start_time if base_start_time is not None else min(e.timestamp for e in events)

        # 1. Determine each user's first seen day (cohort day) and active days
        user_first_day: Dict[str, int] = {}
        user_active_days: Dict[str, Set[int]] = {}

        for e in events:
            day = int((e.timestamp - min_time) // self.day_duration_sec)
            uid = e.user_id
            user_active_days.setdefault(uid, set()).add(day)
            if uid not in user_first_day or day < user_first_day[uid]:
                user_first_day[uid] = day

        # 2. Group users into cohorts
        cohort_users: Dict[int, Set[str]] = {}
        for uid, cday in user_first_day.items():
            cohort_users.setdefault(cday, set()).add(uid)

        # 3. Compute retention for D0, D1, D3, D7, D14, D30
        tracked_intervals = [0, 1, 3, 7, 14, 30]
        cohort_results: Dict[str, Any] = {}

        for cday in sorted(cohort_users.keys()):
            users_in_cohort = cohort_users[cday]
            size = len(users_in_cohort)
            retention_data: Dict[str, float] = {}

            for interval in tracked_intervals:
                target_day = cday + interval
                retained = sum(1 for u in users_in_cohort if target_day in user_active_days.get(u, set()))
                pct = (retained / max(1, size)) * 100.0
                retention_data[f"D{interval}"] = round(pct, 1)

            cohort_results[f"Cohort_Day_{cday}"] = {
                "cohort_day": cday,
                "cohort_size": size,
                "retention": retention_data
            }

        return {
            "total_users": len(user_first_day),
            "cohorts": cohort_results
        }
