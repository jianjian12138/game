"""
Universal Life Simulation & Raising Game Engine (Article 45 - 《仙乡小千金》 & Volcano Princess Architecture)
Covers:
1. Four-Season Household Budget (四时家计: AP expansion vs Rebellion & Stress Trade-off)
2. Calendar Schedule & Attribute Growth System
3. Skill Gating Bridge (Attributes -> Combat/Social Skill Unlocks)
4. Multi-Dimensional Character State & Event Resolution
"""

import random
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple


class BudgetStrategy(str, Enum):
    CONSERVATIVE = "conservative"  # AP +0, Stress -10, Rebellion -10 (Safe recuperation)
    BALANCED = "balanced"          # AP +3, Stress +5, Rebellion +5   (Steady progression)
    AMBITIOUS = "ambitious"        # AP +8, Stress +20, Rebellion +25 (High risk AP surge)


@dataclass
class ScheduleCourse:
    course_id: str
    name: str
    category: str  # "MARTIAL", "WISDOM", "CHARISMA", "ETIQUETTE", "REST"
    ap_cost: int = 2
    attribute_gains: Dict[str, float] = field(default_factory=dict)
    stress_gain: float = 5.0
    gold_cost: float = 0.0


@dataclass
class SkillGate:
    skill_id: str
    name: str
    req_attribute: str
    req_value: float
    description: str
    combat_effect: str


@dataclass
class DaughterProfile:
    name: str = "Ling"
    age: int = 14
    round: int = 1
    max_rounds: int = 16  # 4 quarters * 4 years (Age 14 to 18)
    base_ap: int = 10
    ap_bonus: int = 0
    current_ap: int = 10
    stress: float = 0.0          # 0~100 (High stress causes illness)
    rebellion: float = 0.0       # 0~100 (High rebellion causes course slacking)
    attributes: Dict[str, float] = field(default_factory=lambda: {
        "martial": 20.0,
        "wisdom": 20.0,
        "charisma": 20.0,
        "etiquette": 20.0,
        "morality": 50.0,
        "wealth": 100.0
    })
    unlocked_skills: List[str] = field(default_factory=list)
    affinity: Dict[str, float] = field(default_factory=dict)
    active_budget_strategy: BudgetStrategy = BudgetStrategy.BALANCED
    event_log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LifeSimRaisingEngine:
    """
    Universal Life-Sim engine handling schedule execution, mental state trade-offs,
    and attribute-to-skill gating.
    """

    def __init__(self):
        self.courses: Dict[str, ScheduleCourse] = {}
        self.skill_gates: List[SkillGate] = []
        self._init_defaults()

    def _init_defaults(self):
        # Register standard courses
        self.register_course(ScheduleCourse(
            course_id="c_sword",
            name="练剑修武",
            category="MARTIAL",
            ap_cost=2,
            attribute_gains={"martial": 8.0, "stamina": 4.0},
            stress_gain=6.0
        ))
        self.register_course(ScheduleCourse(
            course_id="c_scrolls",
            name="研读经史",
            category="WISDOM",
            ap_cost=2,
            attribute_gains={"wisdom": 8.0, "morality": 3.0},
            stress_gain=5.0
        ))
        self.register_course(ScheduleCourse(
            course_id="c_etiquette",
            name="研习礼仪",
            category="ETIQUETTE",
            ap_cost=2,
            attribute_gains={"etiquette": 8.0, "charisma": 4.0},
            stress_gain=5.0
        ))
        self.register_course(ScheduleCourse(
            course_id="c_tea",
            name="品茗游园",
            category="REST",
            ap_cost=2,
            attribute_gains={"morality": 2.0},
            stress_gain=-18.0
        ))

        # Register Skill Gates
        self.register_skill_gate(SkillGate(
            skill_id="sk_parry_wind",
            name="回风守月",
            req_attribute="martial",
            req_value=50.0,
            description="剑式轻灵，化守为攻，抵挡伤害并反震对手",
            combat_effect="DEFLECT_COUNTER"
        ))
        self.register_skill_gate(SkillGate(
            skill_id="sk_zen_mind",
            name="清心普善",
            req_attribute="wisdom",
            req_value=60.0,
            description="静心体悟，抚平杂念，化解戾气与心魔",
            combat_effect="CLEANSE_STRESS"
        ))
        self.register_skill_gate(SkillGate(
            skill_id="sk_charm_diplomacy",
            name="惊鸿仪态",
            req_attribute="etiquette",
            req_value=60.0,
            description="言笑晏晏，进退有据，大幅提升NPC结交好感倍率",
            combat_effect="SOCIAL_CHARM_BOOST"
        ))

    def register_course(self, course: ScheduleCourse):
        self.courses[course.course_id] = course

    def register_skill_gate(self, gate: SkillGate):
        self.skill_gates.append(gate)

    def apply_four_season_budget(self, profile: DaughterProfile, strategy: BudgetStrategy) -> Dict[str, Any]:
        """
        '四时家计' Seasonal Budget Negotiation:
        Expands AP at the cost of elevated Stress and Rebellion.
        """
        profile.active_budget_strategy = strategy
        if strategy == BudgetStrategy.CONSERVATIVE:
            profile.ap_bonus = 0
            profile.stress = max(0.0, profile.stress - 10.0)
            profile.rebellion = max(0.0, profile.rebellion - 10.0)
            msg = "四时家计: 谨身节用，性情温顺，精力平缓"
        elif strategy == BudgetStrategy.BALANCED:
            profile.ap_bonus = 3
            profile.stress = min(100.0, profile.stress + 5.0)
            profile.rebellion = min(100.0, profile.rebellion + 5.0)
            msg = "四时家计: 平衡度日，作息稳健，额外精力+3"
        elif strategy == BudgetStrategy.AMBITIOUS:
            profile.ap_bonus = 8
            profile.stress = min(100.0, profile.stress + 20.0)
            profile.rebellion = min(100.0, profile.rebellion + 25.0)
            msg = "四时家计: 严苛期许，额外精力+8，但叛逆与压力大幅飙升！"

        profile.current_ap = profile.base_ap + profile.ap_bonus
        profile.event_log.append(msg)
        return {
            "strategy": strategy.value,
            "total_ap": profile.current_ap,
            "stress": profile.stress,
            "rebellion": profile.rebellion,
            "message": msg
        }

    def execute_course(self, profile: DaughterProfile, course_id: str) -> Dict[str, Any]:
        """
        Executes a single course block, arbitrates rebellion slacking,
        updates attributes, and checks skill unlocks.
        """
        if course_id not in self.courses:
            raise KeyError(f"Course '{course_id}' not found")

        course = self.courses[course_id]
        if profile.current_ap < course.ap_cost:
            return {"success": False, "reason": "INSUFFICIENT_AP"}

        profile.current_ap -= course.ap_cost

        # Rebellion check: if rebellion > 50, probability of slacking off
        is_slacking = False
        rebel_chance = max(0.0, (profile.rebellion - 40.0) / 100.0)
        if random.random() < rebel_chance and course.category != "REST":
            is_slacking = True
            profile.event_log.append(f"【叛逆怠工】女儿在《{course.name}》课上心不在焉，收益折半！")

        multiplier = 0.5 if is_slacking else 1.0
        gains = {}
        for attr, val in course.attribute_gains.items():
            delta = val * multiplier
            profile.attributes[attr] = profile.attributes.get(attr, 0.0) + delta
            gains[attr] = delta

        # Stress adjustment
        profile.stress = max(0.0, min(100.0, profile.stress + course.stress_gain))

        # Check Skill Unlocks
        new_skills = self._check_skill_gates(profile)

        return {
            "success": True,
            "course": course.name,
            "slacking": is_slacking,
            "gains": gains,
            "current_stress": profile.stress,
            "remaining_ap": profile.current_ap,
            "new_skills": new_skills
        }

    def comfort_and_gift(self, profile: DaughterProfile, ap_cost: int = 2) -> Dict[str, Any]:
        """Parental interaction to soothe stress and quell rebellion."""
        if profile.current_ap < ap_cost:
            return {"success": False, "reason": "INSUFFICIENT_AP"}
        profile.current_ap -= ap_cost
        profile.stress = max(0.0, profile.stress - 25.0)
        profile.rebellion = max(0.0, profile.rebellion - 15.0)
        msg = "亲子谈心: 细致安抚，压力-25，叛逆-15"
        profile.event_log.append(msg)
        return {"success": True, "stress": profile.stress, "rebellion": profile.rebellion}

    def _check_skill_gates(self, profile: DaughterProfile) -> List[str]:
        new_unlocked = []
        for gate in self.skill_gates:
            if gate.name not in profile.unlocked_skills:
                curr = profile.attributes.get(gate.req_attribute, 0.0)
                if curr >= gate.req_value:
                    profile.unlocked_skills.append(gate.name)
                    new_unlocked.append(gate.name)
                    profile.event_log.append(f"【领悟新技】由于{gate.req_attribute}达到{curr}，习得绝技《{gate.name}》！")
        return new_unlocked

    def advance_round(self, profile: DaughterProfile) -> Dict[str, Any]:
        profile.round += 1
        # Year advance every 4 quarters
        if (profile.round - 1) % 4 == 0:
            profile.age += 1
        # Reset AP
        profile.current_ap = profile.base_ap + profile.ap_bonus
        return {
            "current_round": profile.round,
            "age": profile.age,
            "is_game_ended": profile.round > profile.max_rounds
        }
