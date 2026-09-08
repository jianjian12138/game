"""
A/B Testing Experiment Dashboard
Generates Markdown summary dashboards with statistical test verdicts and recommendations.
"""

from typing import Dict, Any
from .experiment_manager import Experiment
from .significance_test import SignificanceTest


class ABDashboard:
    """Renders comprehensive experiment result dashboards."""

    @staticmethod
    def render_experiment_report(experiment: Experiment) -> str:
        lines = []
        lines.append(f"# [A/B Test Report] {experiment.name} (`{experiment.experiment_id}`)")
        lines.append(f"- **Status**: `{experiment.status}`")
        lines.append(f"- **Target Metric**: `{experiment.target_metric}`")
        if experiment.winning_variant_id:
            lines.append(f"- **Declared Winner**: `{experiment.winning_variant_id}`")
        lines.append("")

        lines.append("## 1. Variant Performance Table")
        lines.append("| Variant | Name | Traffic Weight | Participants | Conversions | Conversion Rate | Total Value |")
        lines.append("|:---|:---|:---|:---|:---|:---|:---|")

        variants = experiment.variants
        for v in variants:
            vid = v.variant_id
            count = experiment.metric_counts.get(vid, 0)
            conv = experiment.metric_conversions.get(vid, 0)
            rate = (conv / max(1, count)) * 100.0 if count > 0 else 0.0
            val = experiment.metric_values.get(vid, 0.0)
            lines.append(f"| `{vid}` | {v.name} | {v.weight} | {count} | {conv} | {rate:.2f}% | {val:.1f} |")
        lines.append("")

        lines.append("## 2. Statistical Significance Analysis")
        if len(variants) >= 2:
            control = variants[0]
            for var in variants[1:]:
                n_c = experiment.metric_counts.get(control.variant_id, 0)
                c_c = experiment.metric_conversions.get(control.variant_id, 0)
                n_v = experiment.metric_counts.get(var.variant_id, 0)
                c_v = experiment.metric_conversions.get(var.variant_id, 0)

                test_res = SignificanceTest.test_proportions(n_c, c_c, n_v, c_v)
                lines.append(f"### Comparison: `{control.variant_id}` (Control) vs `{var.variant_id}` (Variant)")
                lines.append(f"- **Control Rate**: {test_res['control_rate']}% | **Variant Rate**: {test_res['variant_rate']}%")
                lines.append(f"- **Relative Uplift**: `{test_res['uplift_pct']}%`")
                lines.append(f"- **Z-Score**: `{test_res['z_score']}` | **p-value**: `{test_res['p_value']}`")
                lines.append(f"- **Verdict**: `{test_res['conclusion']}` (Confidence: {test_res.get('confidence_level_pct', 95.0)}%)")
                lines.append(f"- **Recommended Decision**: {'Ship Variant ' + var.variant_id if test_res['winner'] == 'VARIANT' else 'Hold / Continue Experiment'}")
                lines.append("")
        else:
            lines.append("*Need at least 2 variants to compute significance.*")

        return "\n".join(lines)
