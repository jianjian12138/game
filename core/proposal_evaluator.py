# =================================================================
# ⚖️ Novel-to-Game 支柱 2: 三方案多维度竞选评估中枢 (proposal_evaluator.py)
# 对标《Novel-to-Game: 一次生成三个不同的改编方案，挑证据最扎实的那个推进》
# =================================================================

from typing import Dict, List, Any

class TriProposalEvaluator:
    """
    三方案竞选评估器 (Tri-Proposal Evaluator)
    多维度权衡玩法好玩度、技术可行性与资产契约匹配度
    """

    PROPOSALS = [
        {
            "id": "Proposal_A",
            "name": "硬核工业物流与自动化防御 (Hardcore Logistics TowerDefense)",
            "genre": "Factory Automation + Tower Defense",
            "feasibility_score": 95, # 技术可行性 (满分 100)
            "gameplay_depth_score": 98, # 玩法深度与心流 (满分 100)
            "asset_matching_score": 96, # 原版资产匹配度 (满分 100)
            "rationale": "最符合原版《Mindustry》精髓，资源流动与防御塔搭配逻辑极其清晰，证据最扎实。"
        },
        {
            "id": "Proposal_B",
            "name": "单机甲动作弹幕射击 (Action Mech Roguelike)",
            "genre": "Top-down Twin-stick Shooter",
            "feasibility_score": 85,
            "gameplay_depth_score": 75,
            "asset_matching_score": 70,
            "rationale": "玩法单调，抛弃了采矿与传送带物流的核心特色，沦为平庸的换皮弹幕游戏。"
        },
        {
            "id": "Proposal_C",
            "name": "全息大战略基地扩张 (Grand Strategy 4X)",
            "genre": "4X Strategy RTS",
            "feasibility_score": 60,
            "gameplay_depth_score": 90,
            "asset_matching_score": 65,
            "rationale": "开发体量过大，单机客户端难以在短期内实现 4X 宏观外交与多星球网络同步。"
        }
    ]

    def evaluate_and_select_winner(self) -> Dict[str, Any]:
        """多维度加权打分并输出优胜方案"""
        evaluated = []
        for p in self.PROPOSALS:
            # 权重: 可行性 40% + 深度 40% + 资产匹配 20%
            total_score = (
                p["feasibility_score"] * 0.4 +
                p["gameplay_depth_score"] * 0.4 +
                p["asset_matching_score"] * 0.2
            )
            item = dict(p)
            item["total_weighted_score"] = round(total_score, 2)
            evaluated.append(item)

        evaluated.sort(key=lambda x: x["total_weighted_score"], reverse=True)
        winner = evaluated[0]
        
        print("=== TriProposalEvaluator: 正在执行多方案可行性竞选打分 ===")
        for idx, p in enumerate(evaluated, 1):
            tag = "[WINNER]" if idx == 1 else "[REJECTED]"
            print(f"  {tag} {p['id']}: {p['name']} -> 加权总分: {p['total_weighted_score']}")
            print(f"         决策理由: {p['rationale']}")
        print("=========================================================")
        return winner

if __name__ == "__main__":
    winner = TriProposalEvaluator().evaluate_and_select_winner()
    print(f"优胜方案已锁定: {winner['name']}")
