# =================================================================
# 🏷️ 构筑搭配支柱 1: 统一规则标签系统 (game_tags.py)
# 对标《构筑玩法的关键是形成可解释的搭配逻辑: 标签提供第一层清晰判断》
# 统一连接技能、装备、弹药、科技与怪物抗性
# =================================================================

from enum import Enum
from typing import Dict, List, Set

class GameTag(str, Enum):
    # 伤害与物理类型
    BALLISTIC = "Ballistic (动能实弹)"
    EXPLOSIVE = "Explosive (高爆范围)"
    ENERGY = "Energy (激光高能)"
    CRYO = "Cryo (低温冰冻)"
    
    # 功能与物流类型
    LOGISTICS = "Logistics (运输管道)"
    MINING = "Mining (资源采集)"
    POWER = "Power (电力能源)"
    OVERCLOCK = "Overclock (超频增幅)"

class TagSynergyMatrix:
    """标签搭配协同结算字典"""

    # 弹药标签对武器属性的乘数加成
    AMMO_SYNERGY_MULTIPLIERS = {
        "copper": {
            "tags": [GameTag.BALLISTIC],
            "damage_mult": 1.0,
            "range_mult": 1.0,
            "reload_mult": 1.0,
            "explanation": "基础动能弹药，稳定低成本"
        },
        "graphite": {
            "tags": [GameTag.BALLISTIC, GameTag.OVERCLOCK],
            "damage_mult": 2.0,
            "range_mult": 1.2,
            "reload_mult": 0.85,
            "explanation": "重装致密弹药，单发伤害翻倍，射程提升 20%"
        },
        "silicon": {
            "tags": [GameTag.ENERGY, GameTag.BALLISTIC],
            "damage_mult": 1.4,
            "range_mult": 1.1,
            "reload_mult": 1.25,
            "explanation": "自导追踪弹药，射速提升 25%，具备弱制导特性"
        }
    }

if __name__ == "__main__":
    print("=== TagSynergyMatrix: 统一标签系统已注册 ===")
    for k, v in TagSynergyMatrix.AMMO_SYNERGY_MULTIPLIERS.items():
        print(f"  [{k.upper()}] 标签: {[t.value for t in v['tags']]} -> 伤害倍率: {v['damage_mult']}x")
