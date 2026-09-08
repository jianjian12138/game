#!/usr/bin/env python3
"""
agent_philosophy.py: Agent 核心心智模型与最高研发哲学准则库
最高纲领：
“我们是造 Agent 的，Agent 是开发游戏的，你不要老是转到游戏上！
只有把 Agent 的思想搞对、把 Agent 开发游戏的逻辑搞好，它才能开发好任何游戏！”
"""
from typing import Dict, List, Any

class AgentPhilosophy:
    """Agent 核心研发心智中枢"""

    AXIOM = (
        "我们是造 Agent 的，Agent 是开发游戏的，你不要老是转到游戏上！"
        "只有把 Agent 的思想搞对、把 Agent 开发游戏的逻辑搞好，它才能开发好任何游戏！"
    )

    # 任何商业级游戏在动笔前必须具备的 4 维核心契约 (Four Invariant Pillars)
    REQUIRED_GAME_PILLARS = [
        "characters",      # 1. 角色体系 (必须有多角色/职业/专属被动与外观)
        "skills_build",    # 2. 技能与构筑 (必须有升级三选一技能树与成长联动)
        "waves_boss",      # 3. 关卡与波次 (必须有梯度出怪、危险预警与巨型 Boss)
        "story_goals"      # 4. 目标与外壳 (必须有情境目标、商业主菜单与持久化)
    ]

    @staticmethod
    def print_axiom():
        print("=" * 78)
        print(f"  🌟 Agent 核心最高思想准则:\n  「{AgentPhilosophy.AXIOM}」")
        print("=" * 78)
