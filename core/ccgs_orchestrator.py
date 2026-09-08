# =================================================================
# 👑 Game-Agent: CCGS 三层智能体协作与 GDD/ADR 编排中枢 (ccgs_orchestrator.py)
# 对标《手把手，教你使用 Claude Code Game Studios》与《未来做游戏是一支 AI 团队》
# 严格执行: 战略层 (Director) ➔ 战术层 (Lead) ➔ 执行层 (Specialist)
# 强制输出: GDD (8大章节) + ADR (Foundation -> Core -> Presentation)
# =================================================================

import json
from pathlib import Path
from typing import Dict, List, Any

class CcgsOrchestrator:
    """
    CCGS 工业级多智能体编排中枢
    负责 GDD 策划案规格化、ADR 架构决策分层与任务 Story 派发
    """

    GDD_CHAPTERS = [
        "1. 概述 (Overview) — 一句话说清楚系统核心定位",
        "2. 玩家体验 (Player Experience) — 30秒/5分钟心流循环",
        "3. 详细规则 (Detailed Rules) — 无歧义的游戏逻辑判定",
        "4. 数值公式 (Formulas) — 完整的数学模型与常数定义",
        "5. 边界情况 (Edge Cases) — 极端输入与异常保护",
        "6. 依赖关系 (Dependencies) — 前置系统与数据流向",
        "7. 可调参数 (Tunable Values) — 策划配置表字典",
        "8. 验收标准 (Acceptance Criteria / AC) — 自动化可测条件"
    ]

    ADR_TIERS = {
        "Foundation (基础层/地基)": "数据持久化、渲染管线选型、系统通信总线（选错全盘重构，必须提前决策）",
        "Core (核心层/承重墙)": "实体组件装配、世界网格物理、物流状态机（业务骨架，影响范围大）",
        "Presentation (表现层/装修)": "UI 动效、HUD 排版、屏幕微震与音效挂载（可快速敏捷迭代）"
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.design_dir = project_root / "design" / "gdd"
        self.docs_dir = project_root / "docs" / "architecture"
        self.design_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def generate_gdd_template(self, system_name: str) -> Path:
        """为指定系统生成标准的 8 大章节 GDD 规范文档"""
        gdd_file = self.design_dir / f"{system_name}_gdd.md"
        content = [
            f"# 🎮 游戏设计文档 (GDD): {system_name.upper()}",
            "> **严格遵循 CCGS 工业级 GDD 规范，杜绝 AI 盲猜与不确定性补全**\n",
            "---\n"
        ]
        for ch in self.GDD_CHAPTERS:
            content.append(f"## {ch}")
            content.append(f"> [待填充] 填写 {system_name} 关于本章节的精确规格与验收边界...\n")
        
        gdd_file.write_text("\n".join(content), encoding="utf-8")
        return gdd_file

    def generate_adr_template(self, adr_id: str, title: str, tier: str) -> Path:
        """生成标准架构决策记录 (ADR)"""
        adr_file = self.docs_dir / f"{adr_id}_{title}.md"
        content = [
            f"# 🏛️ 架构决策记录 (ADR): {adr_id} - {title}",
            f"- **架构层级**: `{tier}`",
            "- **状态**: `Accepted / 锁定`\n",
            "---\n",
            "## 1. Context (决策背景)",
            "> 描述面对的技术选型痛点或系统瓶颈...\n",
            "## 2. Decision (最终决策)",
            "> 选用了何种技术架构/设计模式，决策理由为何...\n",
            "## 3. Alternatives (被否决的替代方案)",
            "> 考虑过哪些方案，为何在此场景下被否决...\n",
            "## 4. Consequences (后果与收益)",
            "> 本次决策带来的核心收益与必须遵守的约束..."
        ]
        adr_file.write_text("\n".join(content), encoding="utf-8")
        return adr_file

    def generate_gdd_with_llm(
        self,
        system_name: str,
        game_context: str = "",
        provider: str = "gemini",
        model: Any = None,
    ) -> Path:
        """调用 LLM 生成具备具体规格与验收边界的系统 GDD"""
        gdd_file = self.design_dir / f"{system_name}_gdd.md"
        try:
            from core.llm_gateway import LLMGateway
            gw = LLMGateway(provider=provider, model=model)
            prompt = (
                f"你是 CCGS 首席游戏架构师。为游戏《{game_context or '商业游戏'}》的子系统【{system_name}】编写 GDD 规格书。\n"
                f"必须严格包含以下 8 大章节，填充具体的技术规格、数值公式与自动化验收指标，杜绝空洞文字：\n"
                + "\n".join(self.GDD_CHAPTERS)
            )
            resp = gw.call(prompt)
            if resp.success and len(resp.text.strip()) > 300:
                gdd_file.write_text(resp.text.strip(), encoding="utf-8")
                return gdd_file
        except Exception as e:
            print(f"[CcgsOrchestrator] LLM 生成 GDD 失败，降级为模板: {e}")
        return self.generate_gdd_template(system_name)

    def generate_adr_with_llm(
        self,
        adr_id: str,
        title: str,
        tier: str,
        problem_statement: str = "",
        provider: str = "gemini",
        model: Any = None,
    ) -> Path:
        """调用 LLM 生成深度技术架构决策记录 (ADR)"""
        adr_file = self.docs_dir / f"{adr_id}_{title}.md"
        try:
            from core.llm_gateway import LLMGateway
            gw = LLMGateway(provider=provider, model=model)
            tier_desc = self.ADR_TIERS.get(tier, tier)
            prompt = (
                f"你是游戏引擎架构总监。撰写架构决策记录 (ADR)：\n"
                f"- 编号: {adr_id}\n- 标题: {title}\n- 层级: {tier} ({tier_desc})\n- 核心痛点: {problem_statement or '系统选型与性能瓶颈'}\n\n"
                f"请输出完整 Markdown 文档，包含: 1. Context 决策背景; 2. Decision 最终决策; 3. Alternatives 否决方案; 4. Consequences 后果与收益。"
            )
            resp = gw.call(prompt)
            if resp.success and len(resp.text.strip()) > 300:
                adr_file.write_text(resp.text.strip(), encoding="utf-8")
                return adr_file
        except Exception as e:
            print(f"[CcgsOrchestrator] LLM 生成 ADR 失败，降级为模板: {e}")
        return self.generate_adr_template(adr_id, title, tier)

if __name__ == "__main__":
    orchestrator = CcgsOrchestrator((Path(__file__).resolve().parent))
    gdd = orchestrator.generate_gdd_template("logistic_conveyor_system")
    adr = orchestrator.generate_adr_template("ADR-0001", "zero_gc_rust_conveyor_stream", "Foundation (基础层/地基)")
    print(f"=== CCGS Orchestrator: 规范化文档已就绪 ===")
    print(f"  [GDD CREATED] {gdd.name}")
    print(f"  [ADR CREATED] {adr.name}")
