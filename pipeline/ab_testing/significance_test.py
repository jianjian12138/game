"""
Statistical Significance Testing for A/B Experiments
Calculates two-proportion Z-score, p-value via standard normal CDF,
and confidence thresholds without external scientific dependencies.
"""

import math
from typing import Dict, Any


class SignificanceTest:
    """Analytical two-proportion hypothesis testing for conversion rates."""

    @staticmethod
    def _normal_cdf(x: float) -> float:
        """Approximates standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @classmethod
    def test_proportions(cls, n_control: int, conv_control: int,
                         n_variant: int, conv_variant: int,
                         alpha: float = 0.05) -> Dict[str, Any]:
        """
        Two-sided Z-test for difference in proportions.
        p1 = conv_control / n_control
        p2 = conv_variant / n_variant
        """
        if n_control <= 0 or n_variant <= 0:
            return {
                "significant": False, "conclusion": "INCONCLUSIVE", "winner": "NONE",
                "p_value": 1.0, "z_score": 0.0,
                "control_rate": 0.0, "variant_rate": 0.0, "uplift_pct": 0.0,
                "message": "Insufficient sample size"
            }

        p1 = conv_control / float(n_control)
        p2 = conv_variant / float(n_variant)

        # Pooled proportion
        p_pool = (conv_control + conv_variant) / float(n_control + n_variant)

        # Standard error
        denom = p_pool * (1.0 - p_pool) * (1.0 / n_control + 1.0 / n_variant)
        if denom <= 0:
            return {
                "significant": False, "conclusion": "INCONCLUSIVE", "winner": "NONE",
                "p_value": 1.0, "z_score": 0.0,
                "control_rate": round(p1 * 100.0, 2), "variant_rate": round(p2 * 100.0, 2),
                "uplift_pct": 0.0, "message": "Zero variance in samples"
            }

        se = math.sqrt(denom)
        z_score = (p2 - p1) / se

        # Two-tailed p-value
        p_value = 2.0 * (1.0 - cls._normal_cdf(abs(z_score)))
        p_value = max(0.0, min(1.0, p_value))

        uplift = ((p2 - p1) / max(1e-6, p1)) * 100.0 if p1 > 0 else 0.0
        is_sig = (p_value < alpha)

        conclusion = "STATISTICALLY_SIGNIFICANT" if is_sig else "INCONCLUSIVE"
        winner = "VARIANT" if (is_sig and p2 > p1) else ("CONTROL" if (is_sig and p1 > p2) else "NONE")

        return {
            "significant": is_sig,
            "conclusion": conclusion,
            "winner": winner,
            "z_score": round(z_score, 4),
            "p_value": round(p_value, 5),
            "alpha": alpha,
            "confidence_level_pct": round((1.0 - alpha) * 100.0, 1),
            "control_rate": round(p1 * 100.0, 2),
            "variant_rate": round(p2 * 100.0, 2),
            "uplift_pct": round(uplift, 2)
        }
