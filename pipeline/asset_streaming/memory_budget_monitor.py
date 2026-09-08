"""
WeChat Minigame Package & Memory Budget Monitor
Enforces 4MB first-package limit and monitors runtime memory thresholds.
"""

from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class MemoryReport:
    first_package_bytes: int
    first_package_limit_bytes: int
    first_package_ratio_pct: float
    total_package_bytes: int
    is_first_package_compliant: bool
    heavy_assets: List[Dict[str, Any]]
    recommendations: List[str]


class MemoryBudgetMonitor:
    """Audits game package file sizes and active memory allocations against strict WeChat thresholds."""

    WECHAT_FIRST_PACKAGE_LIMIT = 4 * 1024 * 1024  # 4MB
    WECHAT_TOTAL_PACKAGE_LIMIT = 20 * 1024 * 1024 # 20MB

    def __init__(self, first_package_limit: int = WECHAT_FIRST_PACKAGE_LIMIT):
        self.limit = first_package_limit

    def audit_package(self, asset_sizes: Dict[str, int]) -> MemoryReport:
        total = sum(asset_sizes.values())
        ratio = (total / float(self.limit)) * 100.0
        is_compliant = total <= self.limit

        # Find heaviest assets (>200KB)
        heavy = []
        for path, sz in sorted(asset_sizes.items(), key=lambda x: x[1], reverse=True):
            if sz > 200 * 1024:
                heavy.append({"asset": path, "size_kb": round(sz / 1024.0, 1)})

        recs = []
        if not is_compliant:
            recs.append(f"OVER_BUDGET: Package exceeds 4MB WeChat limit by {round((total - self.limit)/1024/1024, 2)}MB.")
            recs.append("ACTION: Split audio BGM and heavy textures into dynamic subpackages or CDN streaming.")
        elif ratio > 85.0:
            recs.append(f"WARNING: Package at {ratio:.1f}% capacity. Approaching 4MB limit.")
        else:
            recs.append(f"HEALTHY: Package is within WeChat budget ({ratio:.1f}% used).")

        return MemoryReport(
            first_package_bytes=total,
            first_package_limit_bytes=self.limit,
            first_package_ratio_pct=round(ratio, 1),
            total_package_bytes=total,
            is_first_package_compliant=is_compliant,
            heavy_assets=heavy,
            recommendations=recs
        )
