"""
Automated Markdown Insight Reporter
Generates comprehensive daily/weekly game health, funnel drop-off,
and retention summary reports.
"""

from typing import Dict, Any


class InsightReporter:
    """Formats telemetry summaries into professional Markdown operational reports."""

    @staticmethod
    def generate_report(game_title: str, funnel_data: Dict[str, Any],
                        cohort_data: Dict[str, Any], event_counts: Dict[str, int]) -> str:
        lines = []
        lines.append(f"# [{game_title}] Operational Telemetry & Health Report")
        lines.append("")
        lines.append("## 1. High-Level Activity Summary")
        lines.append(f"- **Total Active Users Tracked**: {funnel_data.get('total_users', 0)}")
        lines.append(f"- **Total Events Logged**: {sum(event_counts.values())}")
        lines.append(f"- **Core Event Distribution**:")
        for ev, cnt in sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:6]:
            lines.append(f"  - `{ev}`: {cnt}")
        lines.append("")

        lines.append("## 2. Onboarding & Milestone Funnel")
        lines.append(f"- **Overall Conversion**: {funnel_data.get('overall_conversion_pct', 0.0)}%")
        lines.append(f"- **Primary Churn Bottleneck**: `{funnel_data.get('biggest_drop_step', 'None')}`")
        lines.append("")
        lines.append("| Step | Milestone | Users | Drop-off Count | Drop-off Rate | Conversion from Start |")
        lines.append("|:---|:---|:---|:---|:---|:---|")
        for s in funnel_data.get("steps_data", []):
            lines.append(f"| {s['step_index']} | {s['step_name']} | {s['user_count']} | {s['dropoff_count']} | {s['dropoff_pct']}% | {s['conversion_from_start_pct']}% |")
        lines.append("")

        lines.append("## 3. Cohort Retention Matrix")
        cohorts = cohort_data.get("cohorts", {})
        if cohorts:
            lines.append("| Cohort | Initial Size | D0 | D1 | D3 | D7 | D14 | D30 |")
            lines.append("|:---|:---|:---|:---|:---|:---|:---|:---|")
            for cname, cinfo in cohorts.items():
                ret = cinfo.get("retention", {})
                lines.append(f"| {cname} | {cinfo.get('cohort_size', 0)} | {ret.get('D0', 0)}% | {ret.get('D1', 0)}% | {ret.get('D3', 0)}% | {ret.get('D7', 0)}% | {ret.get('D14', 0)}% | {ret.get('D30', 0)}% |")
        else:
            lines.append("*No cohort data available for this window.*")
        lines.append("")

        lines.append("## 4. Actionable Tuning Recommendations")
        biggest_drop = funnel_data.get("biggest_drop_step", "None")
        if biggest_drop != "None":
            lines.append(f"1. **Streamline `{biggest_drop}`**: Largest drop-off observed here. Review difficulty, tutorial clarity, or reward pacing.")
        lines.append("2. **Tune D1 Hook**: Ensure early sessions deliver high tactile satisfaction (Game Feel Juice) within the first 3 minutes.")

        return "\n".join(lines)
