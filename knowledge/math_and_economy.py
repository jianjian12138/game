#!/usr/bin/env python3
"""
math_and_economy.py: 战斗数值模型、经济系统与平衡性公式知识库
为策划与数值平衡师智能体提供工业级战斗攻防、暴击、PRD伪随机与经验曲线算法。
"""
import math
import random
from typing import Dict, List, Tuple, Any

class MathAndEconomyKnowledge:

    # 1. 经典攻防伤害公式 (三大流派)
    @staticmethod
    def calc_subtractive_damage(attack: float, defense: float, skill_multiplier: float = 1.0, variance: float = 0.05) -> int:
        """减法伤害模型 (经典MMO/梦幻西游/魔兽早期)
        公式: 实际伤害 = Max(1, 攻击 - 防御) * 技能倍率 * (1 ± 浮动率)
        """
        raw = max(1.0, attack - defense) * skill_multiplier
        factor = 1.0 + random.uniform(-variance, variance)
        return int(round(raw * factor))

    @staticmethod
    def calc_division_armor_damage(attack: float, armor: float, armor_constant: float = 100.0, skill_multiplier: float = 1.0) -> int:
        """除法护甲免伤模型 (英雄联盟/DOTA2/暗黑/无畏契约)
        公式: 减伤比例 = 护甲 / (护甲 + C), 实际伤害 = 攻击 * (1 - 减伤比例) * 技能倍率
        特点: 护甲收益永不溢出且绝无一刀秒杀/完全破不了防的极端崩溃。
        """
        damage_reduction = armor / (armor + armor_constant)
        damage = attack * (1.0 - damage_reduction) * skill_multiplier
        return max(1, int(round(damage)))

    # 2. PRD 伪随机暴击/抽卡分布算法 (DOTA 2 / 原神防挫败机制)
    # 理论常数对照表 (将真实暴击概率映射到 PRD 步进增量 C)
    PRD_C_TABLE = {
        0.05: 0.00380, 0.10: 0.01475, 0.15: 0.03222, 0.20: 0.05570,
        0.25: 0.08474, 0.30: 0.11895, 0.35: 0.15798, 0.40: 0.20155,
        0.50: 0.30210, 0.60: 0.42265, 0.75: 0.66667
    }

    @staticmethod
    def evaluate_prd_roll(target_prob: float, consecutive_fails: int) -> Tuple[bool, int]:
        """执行一次防挫败伪随机判定 (PRD)
        返回: (是否触发暴击/掉落, 新的连续失败次数)
        """
        # 寻找最接近的 C 增量
        closest_p = min(MathAndEconomyKnowledge.PRD_C_TABLE.keys(), key=lambda k: abs(k - target_prob))
        c_step = MathAndEconomyKnowledge.PRD_C_TABLE[closest_p]

        current_chance = c_step * (consecutive_fails + 1)
        roll = random.random()

        if roll <= current_chance:
            return True, 0  # 命中，重置失败计数
        else:
            return False, consecutive_fails + 1  # 未命中，累积失败补偿

    # 3. 角色等级与经验值指数曲线
    @staticmethod
    def calc_level_exp_requirement(level: int, base_exp: int = 100, exponent: float = 1.8) -> int:
        """计算指定等级升级所需的经验值
        公式: Exp(L) = Base * (L ^ Exponent)
        """
        return int(round(base_exp * (level ** exponent)))

    # 4. 经济循环与体力恢复模型
    @staticmethod
    def calc_stamina_recovery(last_timestamp: float, current_timestamp: float, current_stamina: int, max_stamina: int = 120, recovery_interval_sec: int = 360) -> Tuple[int, float]:
        """计算自然恢复体力
        每 6 分钟 (360s) 恢复 1 点，不超过最大体力
        返回: (新体力值, 剩余未折算的时间戳偏移)
        """
        elapsed = current_timestamp - last_timestamp
        recovered_points = int(elapsed // recovery_interval_sec)
        rem_seconds = elapsed % recovery_interval_sec

        new_stamina = min(max_stamina, current_stamina + recovered_points)
        return new_stamina, current_timestamp - rem_seconds
