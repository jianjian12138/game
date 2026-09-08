"""
DSL Dialects — 方言包
======================
每个方言负责特定领域的 DSL 语法扩展。
"""

from .card_effect_dsl import CardEffectDSL
from .bullet_pattern_dsl import BulletPatternDSL
from .skill_effect_dsl import SkillEffectDSL
from .chart_note_dsl import ChartNoteDSL

__all__ = [
    "CardEffectDSL",
    "BulletPatternDSL",
    "SkillEffectDSL",
    "ChartNoteDSL",
]
