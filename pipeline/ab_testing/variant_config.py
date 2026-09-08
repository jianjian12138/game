"""
A/B Testing Variant Configuration
Defines parameter overrides and traffic weights for experiment variants.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class VariantConfig:
    variant_id: str
    name: str
    weight: float = 1.0  # relative weight for traffic allocation
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def get_param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)
