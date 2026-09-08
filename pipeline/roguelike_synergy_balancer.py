"""
Roguelike Synergy Balancer
Monte-Carlo evaluator for item synergy interactions, damage multipliers,
and game-breaking combo detection.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple


@dataclass
class ItemDef:
    item_id: str
    name: str
    rarity: str
    tags: List[str]
    base_dps_bonus: float = 0.0
    base_hp_bonus: float = 0.0


@dataclass
class SynergyRule:
    tag: str
    tier_thresholds: Dict[int, float]  # count -> multiplier bonus (e.g. 2 -> 1.25, 4 -> 1.80)


class RoguelikeSynergyBalancer:
    """Simulates random runs, item drafts, and analyzes DPS / survival distributions."""

    def __init__(self):
        self.rules: Dict[str, SynergyRule] = {
            "fire": SynergyRule("fire", {2: 1.20, 4: 1.60, 6: 2.50}),
            "lightning": SynergyRule("lightning", {2: 1.15, 4: 1.50, 6: 2.20}),
            "poison": SynergyRule("poison", {2: 1.10, 4: 1.40, 6: 2.00}),
            "crit": SynergyRule("crit", {2: 1.25, 4: 1.70, 6: 2.60}),
            "armor": SynergyRule("armor", {2: 1.30, 4: 1.80, 6: 2.40}),
        }

        # Item catalog
        self.item_pool: List[ItemDef] = [
            ItemDef("item_fire_dagger", "Flame Dagger", "COMMON", ["fire", "crit"], base_dps_bonus=10.0),
            ItemDef("item_fire_cloak", "Cinder Cloak", "COMMON", ["fire", "armor"], base_hp_bonus=50.0),
            ItemDef("item_fire_orb", "Magma Core", "RARE", ["fire"], base_dps_bonus=25.0),
            ItemDef("item_inferno_crown", "Inferno Crown", "EPIC", ["fire", "crit"], base_dps_bonus=60.0),

            ItemDef("item_spark_wand", "Spark Wand", "COMMON", ["lightning"], base_dps_bonus=12.0),
            ItemDef("item_storm_boots", "Storm Strider", "RARE", ["lightning", "crit"], base_dps_bonus=20.0),
            ItemDef("item_thunder_hammer", "Mjolnir's Echo", "EPIC", ["lightning"], base_dps_bonus=55.0),

            ItemDef("item_toxic_vial", "Venom Flask", "COMMON", ["poison"], base_dps_bonus=8.0),
            ItemDef("item_viper_fang", "Viper Fang", "RARE", ["poison", "crit"], base_dps_bonus=22.0),
            ItemDef("item_plague_mask", "Plague Doctor Mask", "EPIC", ["poison", "armor"], base_dps_bonus=40.0, base_hp_bonus=80.0),

            ItemDef("item_iron_plate", "Reinforced Cuirass", "COMMON", ["armor"], base_hp_bonus=80.0),
            ItemDef("item_tower_shield", "Aegis Wall", "RARE", ["armor"], base_hp_bonus=180.0),
            ItemDef("item_lucky_coin", "Gambler's Coin", "COMMON", ["crit"], base_dps_bonus=8.0),
            ItemDef("item_assassin_ring", "Shadow Signet", "RARE", ["crit"], base_dps_bonus=25.0),
        ]

    def evaluate_build(self, items: List[ItemDef], base_dps: float = 50.0, base_hp: float = 200.0) -> Dict[str, Any]:
        tag_counts: Dict[str, int] = {}
        flat_dps = base_dps
        flat_hp = base_hp

        for item in items:
            flat_dps += item.base_dps_bonus
            flat_hp += item.base_hp_bonus
            for t in item.tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1

        # Calculate synergy multipliers
        total_dps_mult = 1.0
        total_hp_mult = 1.0
        triggered_synergies = []

        for tag, count in tag_counts.items():
            if tag in self.rules:
                rule = self.rules[tag]
                # Find highest satisfied tier
                best_threshold = 0
                best_mult = 1.0
                for th, mult in sorted(rule.tier_thresholds.items()):
                    if count >= th:
                        best_threshold = th
                        best_mult = mult

                if best_threshold > 0:
                    triggered_synergies.append({"tag": tag, "tier": best_threshold, "multiplier": best_mult})
                    if tag == "armor":
                        total_hp_mult *= best_mult
                    else:
                        total_dps_mult *= best_mult

        final_dps = round(flat_dps * total_dps_mult, 1)
        final_hp = round(flat_hp * total_hp_mult, 1)
        # Power score = geometric combination of offense and defense
        power_score = round((final_dps ** 0.6) * (final_hp ** 0.4), 1)

        return {
            "items_count": len(items),
            "tag_counts": tag_counts,
            "triggered_synergies": triggered_synergies,
            "flat_dps": flat_dps,
            "dps_multiplier": round(total_dps_mult, 2),
            "final_dps": final_dps,
            "final_hp": final_hp,
            "power_score": power_score
        }

    def simulate_runs(self, num_runs: int = 500, items_per_run: int = 6) -> Dict[str, Any]:
        """Simulates random drafts and analyzes power distribution for balance anomalies."""
        scores = []
        dps_list = []
        extreme_op_count = 0
        dead_run_count = 0

        for _ in range(num_runs):
            chosen_items = random.choices(self.item_pool, k=items_per_run)
            res = self.evaluate_build(chosen_items)
            scores.append(res["power_score"])
            dps_list.append(res["final_dps"])

            # Flag runaway multipliers (>3.0x base power)
            if res["dps_multiplier"] >= 2.5:
                extreme_op_count += 1
            elif len(res["triggered_synergies"]) == 0:
                dead_run_count += 1

        avg_score = sum(scores) / float(len(scores))
        max_score = max(scores)
        min_score = min(scores)
        avg_dps = sum(dps_list) / float(len(dps_list))

        op_ratio = (extreme_op_count / num_runs) * 100.0
        dead_ratio = (dead_run_count / num_runs) * 100.0

        # Assessment
        anomalies = []
        if op_ratio > 15.0:
            anomalies.append(f"HIGH_OP_RISK: {op_ratio:.1f}% runs triggered game-breaking multiplier tiers")
        if dead_ratio > 25.0:
            anomalies.append(f"SYNERGY_STARVATION: {dead_ratio:.1f}% runs failed to trigger any synergy")

        status = "BALANCED" if not anomalies else "NEEDS_TUNING"

        return {
            "num_runs": num_runs,
            "items_per_run": items_per_run,
            "avg_power_score": round(avg_score, 1),
            "max_power_score": max_score,
            "min_power_score": min_score,
            "avg_dps": round(avg_dps, 1),
            "op_run_ratio_pct": round(op_ratio, 1),
            "dead_run_ratio_pct": round(dead_ratio, 1),
            "status": status,
            "anomalies": anomalies
        }


if __name__ == "__main__":
    balancer = RoguelikeSynergyBalancer()
    report = balancer.simulate_runs(num_runs=1000, items_per_run=6)
    print("=== ROGUELIKE SYNERGY BALANCER REPORT ===")
    print(f"Runs: {report['num_runs']} | Avg Power: {report['avg_power_score']} (Min: {report['min_power_score']}, Max: {report['max_power_score']})")
    print(f"Avg DPS: {report['avg_dps']} | OP Ratio: {report['op_run_ratio_pct']}% | Dead Run Ratio: {report['dead_run_ratio_pct']}%")
    print(f"Status: {report['status']} | Anomalies: {report['anomalies']}")
