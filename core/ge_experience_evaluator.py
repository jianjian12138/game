"""
GE (Game Experience) Universal Evaluator
Implements the 4-Stage Experience Evaluation Framework from Article 33:
- GE5: Early impression & reward immediacy score (first 5 minutes / early game).
- GE_T60: Threshold ticks/time required to reach passing comprehension (60% mastery/fun).
- GE30: Mid-game 30-min core loop flow & challenge-mastery balance.
- GE180: Long-term system depth, decision entropy, and strategic retention.
"""

from typing import List, Dict, Any, Optional
import math

class GEEvaluationResult:
    def __init__(
        self,
        ge5_score: float,
        ge_t60_ticks: int,
        ge30_score: float,
        ge180_score: float,
        composite_score: float,
        verdict: str,
        diagnostics: List[str]
    ):
        self.ge5_score = round(ge5_score, 2)
        self.ge_t60_ticks = ge_t60_ticks
        self.ge30_score = round(ge30_score, 2)
        self.ge180_score = round(ge180_score, 2)
        self.composite_score = round(composite_score, 2)
        self.verdict = verdict
        self.diagnostics = diagnostics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ge5_score": self.ge5_score,
            "ge_t60_ticks": self.ge_t60_ticks,
            "ge30_score": self.ge30_score,
            "ge180_score": self.ge180_score,
            "composite_score": self.composite_score,
            "verdict": self.verdict,
            "diagnostics": self.diagnostics,
        }

class GEExperienceEvaluator:
    def __init__(self, max_allowed_t60: int = 60):
        self.max_allowed_t60 = max_allowed_t60

    def evaluate_trace(self, trace: List[Dict[str, Any]]) -> GEEvaluationResult:
        """
        trace is a sequential list of tick records:
        {
            "tick": int,
            "action": str,
            "reward": float,          # positive feedback (resources, score, unlocks)
            "frustration": float,     # negative feedback (unclear death, failed clicks, stagnation)
            "mastery": float,         # cumulative mastery/understanding (0.0 ~ 1.0)
            "subsystem": str          # which game system was interacted with
        }
        """
        if not trace:
            return GEEvaluationResult(
                ge5_score=0.0,
                ge_t60_ticks=99999,
                ge30_score=0.0,
                ge180_score=0.0,
                composite_score=0.0,
                verdict="FAIL_EMPTY_TRACE",
                diagnostics=["Trace is empty; game failed to produce any gameplay events."]
            )

        total_ticks = len(trace)
        diagnostics = []

        # 1. Evaluate GE5 (First 15% of ticks, or first 30 ticks)
        early_window = min(total_ticks, max(10, int(total_ticks * 0.15)))
        early_rewards = [trace[i].get("reward", 0.0) for i in range(early_window)]
        early_frustrations = [trace[i].get("frustration", 0.0) for i in range(early_window)]
        
        first_reward_tick = next((i for i, r in enumerate(early_rewards) if r > 0), None)
        if first_reward_tick is None:
            ge5_score = 10.0
            diagnostics.append("GE5 ALERT: Player received zero rewards/juice in early game.")
        else:
            # Reward earlier arrival and low frustration
            reward_speed = max(0.0, 100.0 - (first_reward_tick * 8.0))
            frustration_penalty = sum(early_frustrations) * 15.0
            ge5_score = max(0.0, min(100.0, reward_speed - frustration_penalty + sum(early_rewards) * 5.0))

        # 2. Evaluate GE_T60 (Ticks until cumulative mastery >= 0.60)
        t60_tick = next((t["tick"] for t in trace if t.get("mastery", 0.0) >= 0.60), total_ticks)
        if t60_tick > self.max_allowed_t60:
            diagnostics.append(f"GE_T60 ALERT: Player took {t60_tick} ticks to cross 60% comprehension (limit: {self.max_allowed_t60}).")

        # 3. Evaluate GE30 (Mid-game ticks from 15% to 60%)
        mid_start = early_window
        mid_end = min(total_ticks, int(total_ticks * 0.60))
        if mid_end > mid_start:
            mid_ticks = trace[mid_start:mid_end]
            mid_rewards = sum(t.get("reward", 0.0) for t in mid_ticks)
            mid_frustrations = sum(t.get("frustration", 0.0) for t in mid_ticks)
            flow_ratio = mid_rewards / (mid_frustrations + 1.0)
            ge30_score = max(0.0, min(100.0, flow_ratio * 25.0 + 30.0))
        else:
            ge30_score = ge5_score

        # 4. Evaluate GE180 (Long-term: 60% to 100% ticks, Subsystem Diversity & Entropy)
        late_ticks = trace[mid_end:]
        if late_ticks:
            subsystem_counts: Dict[str, int] = {}
            for t in late_ticks:
                sub = t.get("subsystem", "default")
                subsystem_counts[sub] = subsystem_counts.get(sub, 0) + 1
            
            # Shannon entropy of subsystem interactions
            total_late = len(late_ticks)
            entropy = 0.0
            for count in subsystem_counts.values():
                p = count / total_late
                if p > 0:
                    entropy -= p * math.log2(p)
            
            # Max possible entropy with observed subsystems
            max_entropy = math.log2(max(1, len(subsystem_counts)))
            entropy_ratio = (entropy / max_entropy) if max_entropy > 0 else 0.5
            ge180_score = max(0.0, min(100.0, entropy_ratio * 70.0 + len(subsystem_counts) * 8.0))
        else:
            ge180_score = ge30_score

        # 5. Composite Score & Verdict
        # Weighting: GE5(25%), T60_penalty(25%), GE30(30%), GE180(20%)
        t60_normalized_score = max(0.0, min(100.0, (1.0 - (t60_tick / (self.max_allowed_t60 * 1.5))) * 100.0))
        composite = (ge5_score * 0.25) + (t60_normalized_score * 0.25) + (ge30_score * 0.30) + (ge180_score * 0.20)

        if t60_tick > self.max_allowed_t60 * 1.5:
            verdict = "FAIL_HIGH_FRUSTRATION_T60"
        elif ge5_score < 30.0:
            verdict = "FAIL_POOR_FIRST_IMPRESSION"
        elif composite >= 75.0:
            verdict = "PASS_EXCELLENT_FLOW"
        elif composite >= 60.0:
            verdict = "PASS_ACCEPTABLE"
        else:
            verdict = "FAIL_SUBPAR_EXPERIENCE"

        return GEEvaluationResult(
            ge5_score=ge5_score,
            ge_t60_ticks=t60_tick,
            ge30_score=ge30_score,
            ge180_score=ge180_score,
            composite_score=composite,
            verdict=verdict,
            diagnostics=diagnostics
        )
