#!/usr/bin/env python3
"""
pvz_grid_engine_specs.py: 吸收《PythonPlantsVsZombies》网格策略与分行物理通道大典
核心标准：
1. 5×9 离散空间网格与绝对坐标吸附对齐 (严禁乱扔乱放)
2. 分行独立物理通道 (Row-based Ray Tracing)：行与行之间物理绝缘，优化检测复杂度
3. 僵尸啃咬状态机 (Walk ➔ Eat ➔ Walk)：碰到植物阻挡则持续啃咬，啃碎后继续前行
4. 阳光经济流与卡牌冷却遮罩 (Cooldown Masks)
5. 终极小推车防线 (Lawnmover Safety Net)
"""
from typing import Dict, List, Any

class PvZGridEngineSpecs:
    """植物大战僵尸标准网格策略规范"""

    GRID_ROWS = 5
    GRID_COLS = 9

    # 标准植物卡牌字典
    STANDARD_PLANTS = [
        {
            "id": "sunflower",
            "name": "向日葵",
            "cost": 50,
            "cooldown_sec": 7.5,
            "hp": 300,
            "desc": "每隔 12 秒产出一颗高能量阳光 (+25)"
        },
        {
            "id": "peashooter",
            "name": "豌豆射手",
            "cost": 100,
            "cooldown_sec": 7.5,
            "hp": 300,
            "desc": "当所在行前方有僵尸时，每隔 1.4 秒发射一枚豌豆"
        },
        {
            "id": "wallnut",
            "name": "坚果墙",
            "cost": 50,
            "cooldown_sec": 20.0,
            "hp": 4000,
            "desc": "高耐久护盾，有效阻挡僵尸推进步伐"
        },
        {
            "id": "cherrybomb",
            "name": "樱桃炸弹",
            "cost": 150,
            "cooldown_sec": 35.0,
            "hp": 300,
            "desc": "种植 1 秒后剧烈引爆，消灭 3×3 范围内所有僵尸"
        }
    ]
