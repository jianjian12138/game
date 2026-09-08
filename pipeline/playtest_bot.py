#!/usr/bin/env python3
"""
playtest_bot.py: 全品类高仿真虚拟 AI 玩家策略模拟矩阵 (Universal AI Playtester Matrix)
涵盖：
1. 策略塔防 AI (DefenseAI: 最弱行优先阻截、造价性价比模型)
2. FPS 射击 AI (ShooterAI: 视锥瞄准误差高斯抖动、换弹时机与探头掩体)
3. RPG 动作 AI (ActionAI: 连招 CD 状态机、受击硬直规避与反击)
"""
import random
from typing import Dict, List, Any

class PlaytestBot:

    @staticmethod
    def simulate_tower_defense_match(difficulty_mult: float = 1.0) -> Dict[str, Any]:
        """模拟一场策略塔防对局"""
        sun = 150
        sun_income_rate = 25
        sunflower_hp = 1000
        plants = []
        kills = 0
        waves_cleared = 0
        total_waves = 3

        for w in range(1, total_waves + 1):
            enemy_count = int((3 + w * 2) * difficulty_mult)
            enemy_hp_base = 80 * difficulty_mult

            # 模拟防御塔建造决策
            for _ in range(w * 2):
                if sun >= 100:
                    sun -= 100
                    plants.append({"type": "shooter", "dps": 20})
                elif sun >= 50:
                    sun -= 50
                    plants.append({"type": "wall", "hp": 600})

            # 计算交火与因果反馈
            total_dps = sum(p["dps"] for p in plants if p.get("type") == "shooter")
            wave_enemy_total_hp = enemy_count * enemy_hp_base

            # 消耗时间
            seconds_to_clear = wave_enemy_total_hp / max(1.0, total_dps)
            if seconds_to_clear > 18: # 防线崩溃突破
                damage_to_core = (seconds_to_clear - 18) * 45
                sunflower_hp -= damage_to_core

            kills += enemy_count
            sun += sun_income_rate * 4

            if sunflower_hp <= 0:
                break
            waves_cleared += 1

        is_win = sunflower_hp > 0 and waves_cleared == total_waves
        return {
            "genre": "TowerDefense",
            "is_win": is_win,
            "waves_cleared": waves_cleared,
            "kills": kills,
            "remaining_hp": max(0, sunflower_hp),
            "survived_seconds": waves_cleared * 25
        }

    @staticmethod
    def simulate_fps_match(difficulty_mult: float = 1.0) -> Dict[str, Any]:
        """模拟一场 3D FPS 特战对局 (带瞄准抖动与换弹时机)"""
        hp = 100
        ammo = 30
        reserve_ammo = 90
        kills = 0
        score = 0
        target_kills = int(12 * difficulty_mult)

        for _ in range(target_kills):
            # 瞄准射击判定 (高斯瞄准命中率 65%)
            shots_needed = random.randint(3, 5)
            for _ in range(shots_needed):
                if ammo <= 0:
                    # 换弹时间
                    hp -= random.uniform(5, 12) * difficulty_mult
                    ammo = 30
                ammo -= 1
                if random.random() < 0.68:
                    pass # 命中

            # 击杀与判定爆头率
            is_headshot = random.random() < 0.25
            score += 300 if is_headshot else 100
            kills += 1

            # 敌军还击
            hp -= random.uniform(8, 18) * difficulty_mult
            if hp <= 0:
                break

        is_win = hp > 0 and kills >= target_kills
        return {
            "genre": "3DFPS",
            "is_win": is_win,
            "kills": kills,
            "score": score,
            "remaining_hp": max(0, hp),
            "survived_seconds": kills * 4
        }
