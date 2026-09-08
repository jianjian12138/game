"""
Game Science Principles Automated Guard
Translates the Game Science 10 Principles (Feng Ji) into automated quality checks:
1. Executable-First (原则4 & 10): Zero unverified plans; code must be runnable without TODO placeholders.
2. Core Highlight First (原则3): Must have 1-2 distinct standout mechanisms, not 10 bland ones.
3. Fun as Bottom-line (原则5): Requires passing GE evaluation (GE_T60 <= limit).
4. Density Injection (原则7): When fun is low or bottlenecks occur, prescribes density enhancement (hit-stop, screenshake, sfx).
"""

from typing import Dict, Any, List, Optional
import re

class GameScienceAuditResult:
    def __init__(self, passed: bool, score: float, violations: List[str], recommendations: List[str]):
        self.passed = passed
        self.score = round(score, 2)
        self.violations = violations
        self.recommendations = recommendations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "violations": self.violations,
            "recommendations": self.recommendations,
        }

class GameSciencePrinciplesGuard:
    def __init__(self):
        pass

    def audit_delivery(
        self,
        code_content: str,
        has_runnable_entry: bool,
        standout_mechanics: List[str],
        ge_t60_ticks: int,
        max_allowed_t60: int = 60,
        has_game_juice: bool = True
    ) -> GameScienceAuditResult:
        violations = []
        recommendations = []
        score = 100.0

        # Check 1: [原则4 & 原则10] 可体验的版本胜过满纸雄文 / 理念廉价行动可贵
        if not has_runnable_entry:
            violations.append("VIOLATION_P4_NO_RUNNABLE_ENTRY: Delivery lacks a directly executable main entrypoint.")
            recommendations.append("Principle 4: Provide a runnable build/entrypoint instead of abstract documentation.")
            score -= 30.0

        # Check for placeholder comments
        todo_matches = re.findall(r'(?i)//\s*todo|#\s*todo|//\s*placeholder|#\s*placeholder', code_content)
        if todo_matches:
            violations.append(f"VIOLATION_P10_PLACEHOLDERS_FOUND: Code contains {len(todo_matches)} TODO/placeholder tags.")
            recommendations.append("Principle 10: Eliminate placeholders. Deliver fully implemented logic.")
            score -= min(30.0, len(todo_matches) * 10.0)

        # Check 2: [原则3] 发现亮点，先于消灭缺陷
        if len(standout_mechanics) == 0:
            violations.append("VIOLATION_P3_NO_STANDOUT_HIGHLIGHT: Delivery has no declared core highlight/USP.")
            recommendations.append("Principle 3: Prioritize 1-2 distinct standout mechanisms that wow the player before polishing generic systems.")
            score -= 20.0
        elif len(standout_mechanics) > 3:
            violations.append("VIOLATION_P3_OVERDILUTED_HIGHLIGHTS: More than 3 highlights declared; focus is diluted.")
            recommendations.append("Principle 3: Focus deeply on 1-2 core hooks to avoid a bland, unfocused experience.")
            score -= 10.0

        # Check 3: [原则5] 好玩是目标，也是底线
        if ge_t60_ticks > max_allowed_t60:
            violations.append(f"VIOLATION_P5_UNACCEPTABLE_T60: GE_T60 ({ge_t60_ticks}) exceeds max threshold ({max_allowed_t60}). Game onboarding is frustrating.")
            recommendations.append("Principle 5: Fun is the baseline. Refactor onboarding flow to shorten time-to-fun.")
            score -= 25.0

        # Check 4: [原则7] 走投无路，提升密度
        if not has_game_juice:
            violations.append("VIOLATION_P7_LACKING_FEEDBACK_DENSITY: Delivery missing essential game juice (screenshake/hit-stop/sound).")
            recommendations.append("Principle 7: Boost sensory & interaction density! Add 3~6 frame hit-stop, screenshake, and responsive sound effects.")
            score -= 20.0

        score = max(0.0, score)
        passed = (score >= 70.0 and len(violations) == 0 or (len(violations) == 1 and score >= 75.0))

        return GameScienceAuditResult(
            passed=passed,
            score=score,
            violations=violations,
            recommendations=recommendations
        )
