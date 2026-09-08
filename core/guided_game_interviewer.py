# =================================================================
# 📋 Book-to-Skill 支柱 1: 四轮问答式需求引导调研中枢 (guided_game_interviewer.py)
# 对标《Book-to-Skill: 问答式需求调研，先需求后架构最后开发》
# =================================================================

import json
from pathlib import Path
from typing import Dict, List, Any

class GuidedGameInterviewer:
    """
    四轮需求引导调研器 (Guided Game Interviewer)
    """

    FOUR_ROUNDS_QUESTIONNAIRE = [
        {
            "round": 1,
            "theme": "游戏类型与 30 秒核心心流体验 (Genre & Core Flow)",
            "questions": [
                "1.1 您希望开发什么核心品类的游戏？(如: 2D 网格物流塔防 / 动作射击 / 空间探索)",
                "1.2 玩家在 30 秒的基础循环中做出的最频繁动作是什么？(如: 采矿、铺设传送带、建造机枪塔)"
            ]
        },
        {
            "round": 2,
            "theme": "机制系统与升级深度 (Mechanics & Upgrade Tree)",
            "questions": [
                "2.1 防御塔与机甲有哪些初始类型？(如: 双管机枪塔、激光炮、采矿机甲)",
                "2.2 科技树与升级如何组织？(如: DAG 有向无环图、消耗铜矿/石墨解锁)"
            ]
        },
        {
            "round": 3,
            "theme": "经济管线与难度瓶颈 (Economy & Difficulty Balance)",
            "questions": [
                "3.1 核心资源种类与流通方式是什么？(如: 铜矿、铅矿、煤炭通过传送带流入核心)",
                "3.2 敌军波次进攻的压力曲线如何递增？(如: 每波增加 20% 敌机，带精英机甲)"
            ]
        },
        {
            "round": 4,
            "theme": "视觉风格与平台性能预算 (Aesthetics & Performance)",
            "questions": [
                "4.1 美术与 UI 视觉基调是什么？(如: 暗色磨砂玻璃拟态 + 官方金黄强调色)",
                "4.2 目标运行平台与性能指标？(如: Windows Native 60 FPS 垂直同步零掉帧)"
            ]
        }
    ]

    def generate_interview_spec(self, answers: Dict[str, str], output_file: Path) -> Path:
        """根据调研回答生成标准需求调研规格大典"""
        lines = [
            "# 📋 四轮需求引导调研结果大典 (Guided Interview Spec)",
            "> **遵循 Book-to-Skill 铁律：先需求 ➔ 后架构 ➔ 最后开发，杜绝凭空盲猜**\n",
            "---\n"
        ]

        for q_group in self.FOUR_ROUNDS_QUESTIONNAIRE:
            lines.append(f"## 🔹 第 {q_group['round']} 轮: {q_group['theme']}")
            for q in q_group["questions"]:
                q_id = q.split(".")[0].strip()
                ans = answers.get(q_id, "已按工业黄金母版标准默认配置")
                lines.append(f"- **问题**: {q}")
                lines.append(f"- **决策结果**: `{ans}`\n")

        output_file.write_text("\n".join(lines), encoding="utf-8")
        return output_file

if __name__ == "__main__":
    interviewer = GuidedGameInterviewer()
    out = interviewer.generate_interview_spec(
        {
            "1": "2D 工业物流与沙盒塔防 (Mindustry 模式)",
            "2": "DAG 科技树 + 415 建筑体系",
            "3": "多矿物流 + 电网协同 + 弹药补给",
            "4": "暗色磨砂玻璃 + 60 FPS 纯 Rust 硬件加速"
        },
        (Path(__file__).resolve().parent / 'design/interview_spec.md')
    )
    print(f"=== GuidedGameInterviewer: 需求规格大典已生成 -> {out.name} ===")
