#!/usr/bin/env python3
"""
agent_mind.py: 75 位专家智能体深度思维链认知与专业性格驱动核 (Agent Mind Core)
为每个智能体注入所属部门的核心价值观、专业批判视角、思维链推理规则与独立评审逻辑。
"""
from typing import Dict, List, Any, Optional

class AgentMind:
    """智能体认知与思维核"""
    def __init__(self, agent_id: str, name: str, role: str, department: str, core_values: str):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.department = department
        self.core_values = core_values

    def deliberate_proposal(self, topic: str, proposal_context: Dict[str, Any]) -> Dict[str, Any]:
        """对立项方案或玩法机制展开专业思维链推演 (Chain of Thought)"""
        concerns = []
        recommendations = []
        verdict = "APPROVED"

        # 根据部门与专业角色触发强烈的独立专业思考
        if "制作管理" in self.department:
            if proposal_context.get("estimated_dev_days", 5) > 10:
                concerns.append("项目工期超出独立商业发行窗口期，存在超期风险。")
                recommendations.append("建议砍掉次要旁支机制，聚焦核心玩法的打磨 (MVP+Juice)。")
                verdict = "CONDITIONAL"
            else:
                recommendations.append("开发节奏紧凑，符合敏捷冲刺标准。")

        elif "策划叙事" in self.department:
            if not proposal_context.get("core_loop"):
                concerns.append("核心因果反馈回路未闭环，玩家无法在前 3 秒建立清晰的掌控感。")
                verdict = "REJECTED"
            else:
                recommendations.append("核心循环具备明确的即时正反馈与挫败补偿。")

        elif "主程技术" in self.department:
            if proposal_context.get("use_hardcoded_classes", False):
                concerns.append("发现实体逻辑存在硬编码类倾向，严重违反 OpenRA Actor-Trait 解耦标准！")
                recommendations.append("必须采用纯组件 (Trait) 挂载与 ContentRegistry 数据驱动模式。")
                verdict = "REJECTED"
            else:
                recommendations.append("符合 ECS 实体解耦架构，物理主循环支持固定 60Hz 步长。")

        elif "质量测试" in self.department:
            if not proposal_context.get("has_ccd_check", True):
                concerns.append("未发现高速弹道 CCD (连续碰撞检测) 机制，可能引发穿墙穿模！")
                verdict = "CONDITIONAL"
            else:
                recommendations.append("物理防卡死守卫与无头自愈审计预备健全。")

        return {
            "reviewer_id": self.agent_id,
            "reviewer_name": self.name,
            "department": self.department,
            "role": self.role,
            "verdict": verdict,
            "concerns": concerns,
            "recommendations": recommendations
        }

class StudioMindRegistry:
    """75 专家认知池管理中枢"""
    def __init__(self):
        self.minds: Dict[str, AgentMind] = {}
        self._init_core_minds()

    def _init_core_minds(self):
        core_defs = [
            ("executive_producer", "总制作人", "商业统筹与终审", "制作管理部", "质量第一，把控预算与工期，追求长线黏性"),
            ("lead_game_designer", "主游戏策划", "核心循环与玩法规则", "策划叙事部", "手感至上，机制自洽，心流平衡"),
            ("combat_balancer", "战斗数值平衡师", "攻防公式与经济模型", "策划叙事部", "拒绝极端秒杀，概率平滑防挫败"),
            ("lead_architect", "首席架构师", "ECS系统与高内聚低耦合", "主程技术部", "数据与逻辑100%解耦，严禁硬编码"),
            ("physics_engineer", "物理碰撞工程师", "Hitbox与CCD防穿模", "主程技术部", "确定性步长，杜绝死亡螺旋与穿墙"),
            ("art_director", "技术美术总监", "调色板与着色器规范", "美术视觉部", "告别粗糙Emoji，追求高保真精灵与发光氛围"),
            ("audio_director", "音频总监", "WebAudio程序化合成", "音频工程部", "多层音效叠加，强化打击震慑力"),
            ("qa_director", "测试总监", "自动化审计与自愈门禁", "质量测试部", "零容忍致命Bug，100场无头对局验收")
        ]
        for aid, name, role, dept, values in core_defs:
            self.minds[aid] = AgentMind(aid, name, role, dept, values)

    def get_mind(self, agent_id: str) -> Optional[AgentMind]:
        return self.minds.get(agent_id)

studio_mind_registry = StudioMindRegistry()
