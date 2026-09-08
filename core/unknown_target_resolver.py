# =================================================================
# 🎯 原型反思支柱 1: 最大未知数靶心决策中枢 (unknown_target_resolver.py)
# 对标《先做原型可能是错的: 开工前先明确当前最不知道答案的到底是什么》
# =================================================================

from enum import Enum
from pathlib import Path
from typing import Dict, List, Any

class UnknownCategory(str, Enum):
    MICRO_VERB_JOY = "Micro-Verb Joy (核心动词手感与微心流)"
    SYSTEM_INTEGRATION = "System Integration (机制搭配与能量物流闭环)"
    TECH_BENCHMARK = "Tech Benchmark (60 FPS 物理与零 GC 基准)"
    VISUAL_SHADER = "Visual Shader (美术渲染与着色器表现)"

class UnknownTargetResolver:
    """
    最大未知数靶心决策器 (Single Biggest Unknown Resolver)
    """

    def resolve_sprint_target(self, project_stage: str) -> Dict[str, Any]:
        """根据当前研发阶段精准锚定唯一攻坚靶心"""
        if project_stage == "concept_stage":
            return {
                "target_type": UnknownCategory.MICRO_VERB_JOY,
                "question": "玩家在 3 秒内的基础采矿/开火动作是否具备足够的爽感与即时正反馈？",
                "recommended_action": "搭建 1x1 最小核心动词沙盒，测试屏幕微震、音效与跳字反馈，严禁直接铺设全量大地图"
            }
        elif project_stage == "mechanics_stage":
            return {
                "target_type": UnknownCategory.SYSTEM_INTEGRATION,
                "question": "采矿 ➔ 物流 ➔ 发电 ➔ 炮塔供给 4 阶 Synergy 链条是否能顺畅自洽？",
                "recommended_action": "运行 10 步高整合度状态机模拟测试"
            }
        else:
            return {
                "target_type": UnknownCategory.TECH_BENCHMARK,
                "question": "大规模实体碰撞与分层渲染是否能在 16.6ms 内稳定完成？",
                "recommended_action": "运行 FrameProfiler 执行单帧冻结检测"
            }

    def generate_target_document(self, stage: str, output_file: Path) -> Path:
        """输出标准靶心规格书"""
        info = self.resolve_sprint_target(stage)
        lines = [
            "# 🎯 当前 Sprint 最大未知数靶心决策书",
            "> **遵循开发铁律：不做大而全的盲目原型，聚焦当前唯一最值得被证明的问题**\n",
            "---\n",
            f"## 🔹 核心靶心类别: `{info['target_type'].value}`",
            f"- **攻坚核心问题**: `{info['question']}`",
            f"- **执行验证策略**: `{info['recommended_action']}`\n",
            "---\n## 🛠️ 交付标准: 靶心验证 100% 闭环后方可进入下一阶段扩建！"
        ]

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(lines), encoding="utf-8")
        return output_file

if __name__ == "__main__":
    resolver = UnknownTargetResolver()
    out = resolver.generate_target_document("concept_stage", Path(r"D:\jianjian12138\game\design\unknown_validation_target.md"))
    print(f"=== UnknownTargetResolver: 靶心决策书已生成 -> {out.name} ===")
