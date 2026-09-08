"""
Combat Numerical Engine (Article 37: Mathematical Foundations of Combat Systems)
Implements:
1. Multiplicative & Symmetric Penetration Damage Formula (LoL/WoW standard)
2. PRD (Pseudo-Random Distribution) Probability Controller (anti-gambler fallacy, anti-streak)
3. Safe Multiplicative CDR (Cooldown Reduction) with 40% hard cap
4. Synergistic Combat Power (CP) & TTK (Time-To-Kill) Calculator
"""

import math
from typing import Dict, Any, List, Optional, Tuple

class CombatNumericalEngine:
    def __init__(self):
        # Cache for PRD states: event_id -> (current_p, c_value, consecutive_misses)
        self._prd_states: Dict[str, Dict[str, float]] = {}

    # -------------------------------------------------------------
    # 1. 伤害公式 (Damage Formula: Multiplicative & Symmetric)
    # -------------------------------------------------------------
    @staticmethod
    def calculate_damage(
        atk: float,
        defense: float,
        penetration_percent: float = 0.0,
        penetration_flat: float = 0.0,
        attacker_level: int = 1,
        min_damage_floor: float = 1.0,
        level_k_constant: float = 0.0 # If > 0, applies WoW-style level scaling
    ) -> float:
        """
        Damage = ATK * Multiplier.
        Effective DEF = (DEF * (1 - pen_percent)) - pen_flat.
        If DEF >= 0: Multiplier = 100 / (100 + DEF).
        If DEF < 0: Multiplier = 2 - 100 / (100 - DEF).
        """
        # Apply penetration
        effective_def = (defense * (1.0 - max(0.0, min(1.0, penetration_percent)))) - penetration_flat

        # Optional WoW level scaling
        if level_k_constant > 0 and effective_def > 0:
            scale = level_k_constant * attacker_level
            multiplier = scale / (scale + effective_def)
        else:
            # LoL Symmetric Penetration Formula
            if effective_def >= 0:
                multiplier = 100.0 / (100.0 + effective_def)
            else:
                multiplier = 2.0 - (100.0 / (100.0 - effective_def))

        raw_damage = atk * multiplier
        return max(min_damage_floor, raw_damage)

    # -------------------------------------------------------------
    # 2. 伪随机分布 (PRD: Pseudo-Random Distribution)
    # -------------------------------------------------------------
    @staticmethod
    def approximate_prd_c(target_prob: float) -> float:
        """
        Approximates the C constant for a given nominal probability P.
        Derived from DOTA2/Warcraft 3 PRD tables.
        """
        p = max(0.01, min(0.99, target_prob))
        # Good polynomial approximation for C given P:
        # C ≈ P * (0.28 + 0.72 * P) for P <= 0.5
        if p <= 0.5:
            return p * (0.27 + 0.73 * p)
        else:
            return p

    def roll_prd_event(self, event_id: str, target_prob: float, seed_random_val: Optional[float] = None) -> bool:
        """
        Rolls a PRD event with dynamic C-step increment.
        Prevents long streaks of bad luck (anti-gambler fallacy) and prevents consecutive procs.
        """
        import random
        r = random.random() if seed_random_val is None else seed_random_val

        if event_id not in self._prd_states:
            c_val = self.approximate_prd_c(target_prob)
            self._prd_states[event_id] = {
                "current_p": c_val,
                "c_val": c_val,
                "target_prob": target_prob,
                "miss_streak": 0
            }

        state = self._prd_states[event_id]
        # Update target if changed
        if abs(state["target_prob"] - target_prob) > 0.001:
            state["c_val"] = self.approximate_prd_c(target_prob)
            state["target_prob"] = target_prob

        triggered = (r < state["current_p"])
        if triggered:
            # Reset to base C value
            state["current_p"] = state["c_val"]
            state["miss_streak"] = 0
        else:
            # Step up probability for next roll
            state["current_p"] = min(1.0, state["current_p"] + state["c_val"])
            state["miss_streak"] += 1

        return triggered

    def reset_prd(self, event_id: str):
        if event_id in self._prd_states:
            del self._prd_states[event_id]

    # -------------------------------------------------------------
    # 3. 冷却缩减 (Safe Multiplicative CDR & Hard Cap)
    # -------------------------------------------------------------
    @staticmethod
    def calculate_safe_cooldown(
        base_cd: float,
        cdr_sources: List[float],
        min_cd_ratio_cap: float = 0.40 # Hard cap: CD can never drop below 40% of base
    ) -> Tuple[float, float]:
        """
        Computes CDR via multiplicative stacking:
        RemainingRatio = Product(1 - cdr_i).
        FinalCD = max(BaseCD * min_cd_ratio_cap, BaseCD * RemainingRatio).
        Returns: (final_cd, effective_cdr_percent)
        """
        remaining_ratio = 1.0
        for cdr in cdr_sources:
            safe_cdr = max(0.0, min(0.99, cdr))
            remaining_ratio *= (1.0 - safe_cdr)

        # Enforce hard cap
        effective_ratio = max(min_cd_ratio_cap, remaining_ratio)
        final_cd = base_cd * effective_ratio
        effective_cdr = 1.0 - effective_ratio

        return round(final_cd, 3), round(effective_cdr, 4)

    # -------------------------------------------------------------
    # 4. 战力评分与击杀节奏 (Synergistic Combat Power & TTK)
    # -------------------------------------------------------------
    @staticmethod
    def calculate_combat_power(
        hp: float,
        atk: float,
        defense: float,
        crit_rate: float = 0.05,
        crit_dmg: float = 1.5,
        speed: float = 1.0
    ) -> float:
        """
        Non-linear CP formula capturing HP x ATK synergy:
        CP = sqrt(ATK * HP) * speed + DEF * 0.8 + (CritRate * (CritDMG - 1) * 100).
        """
        synergy_core = math.sqrt(max(0.0, atk * hp)) * speed
        def_contrib = defense * 0.8
        crit_score = crit_rate * (crit_dmg - 1.0) * 100.0

        return round(synergy_core + def_contrib + crit_score, 2)

    @staticmethod
    def calculate_ttk(
        target_hp: float,
        target_defense: float,
        attacker_atk: float,
        attack_speed: float,
        crit_rate: float = 0.05,
        crit_dmg: float = 1.5
    ) -> float:
        """
        Computes expected Time-To-Kill (TTK in seconds):
        TTK = TargetHP / (EffectiveDamagePerHit * AttackSpeed).
        """
        base_hit_dmg = CombatNumericalEngine.calculate_damage(attacker_atk, target_defense)
        crit_factor = 1.0 + (crit_rate * (crit_dmg - 1.0))
        effective_dps = base_hit_dmg * crit_factor * attack_speed

        if effective_dps <= 0:
            return 99999.0
        return round(target_hp / effective_dps, 2)
