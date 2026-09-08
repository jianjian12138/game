"""
Experiment Manager for A/B Testing
Deterministic hash-based bucketing, lifecycle state management,
and metric accumulation per variant.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from .variant_config import VariantConfig


@dataclass
class Experiment:
    experiment_id: str
    name: str
    variants: List[VariantConfig]
    status: str = "RUNNING"  # "DRAFT", "RUNNING", "CONCLUDED"
    winning_variant_id: Optional[str] = None
    target_metric: str = "conversion"
    metric_counts: Dict[str, int] = field(default_factory=dict)
    metric_conversions: Dict[str, int] = field(default_factory=dict)
    metric_values: Dict[str, float] = field(default_factory=dict)

    def get_variant_by_id(self, vid: str) -> Optional[VariantConfig]:
        for v in self.variants:
            if v.variant_id == vid:
                return v
        return None


class ExperimentManager:
    """Manages active experiments, assigns variants via SHA-256 bucketing."""

    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}

    def create_experiment(self, exp_id: str, name: str, variants: List[VariantConfig],
                          target_metric: str = "conversion") -> Experiment:
        exp = Experiment(
            experiment_id=exp_id,
            name=name,
            variants=variants,
            status="RUNNING",
            target_metric=target_metric
        )
        for v in variants:
            exp.metric_counts[v.variant_id] = 0
            exp.metric_conversions[v.variant_id] = 0
            exp.metric_values[v.variant_id] = 0.0
        self.experiments[exp_id] = exp
        return exp

    def assign_variant(self, exp_id: str, user_id: str) -> Optional[VariantConfig]:
        exp = self.experiments.get(exp_id)
        if not exp or exp.status != "RUNNING" or not exp.variants:
            return None

        # Deterministic hash to bucket 0..9999
        seed_str = f"{exp_id}:{user_id}"
        hash_val = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:8], 16)
        bucket = (hash_val % 10000) / 100.0  # 0.00 to 99.99

        total_weight = sum(v.weight for v in exp.variants)
        accum = 0.0
        for v in exp.variants:
            span = (v.weight / max(1e-6, total_weight)) * 100.0
            accum += span
            if bucket < accum:
                exp.metric_counts[v.variant_id] += 1
                return v

        # Fallback to last variant
        v = exp.variants[-1]
        exp.metric_counts[v.variant_id] += 1
        return v

    def record_conversion(self, exp_id: str, variant_id: str, value: float = 1.0):
        exp = self.experiments.get(exp_id)
        if exp and variant_id in exp.metric_conversions:
            exp.metric_conversions[variant_id] += 1
            exp.metric_values[variant_id] += value

    def conclude_experiment(self, exp_id: str, winning_variant_id: str):
        exp = self.experiments.get(exp_id)
        if exp:
            exp.status = "CONCLUDED"
            exp.winning_variant_id = winning_variant_id
