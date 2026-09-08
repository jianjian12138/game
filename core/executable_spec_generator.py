# =================================================================
# 📋 可执行规格支柱 1: Schema-First 结构优先规格生成器 (executable_spec_generator.py)
# 对标《先定数据结构，再填内容: 从散文到 0 问号可执行规格》
# =================================================================

from pathlib import Path
from typing import Dict, List, Any

class ExecutableSpecGenerator:
    """
    Schema-First 结构优先规格生成器
    """

    # 1. 第一步: 先定死数据结构 (Schema 列)
    SKILL_SCHEMA_COLUMNS = [
        "技能名称", "能量消耗", "冷却时间(s)", "施放方式", "基础固定伤害", "状态/增益标签"
    ]

    def __init__(self, output_file: Path):
        self.output_file = output_file

    def generate_full_spec(self) -> Path:
        """第二步: 一次性填满所有行，绝无空项与散文问号"""
        rows = [
            ["激光采矿束", "0", "0.0", "持续引导", "+15 (开采)", "HarvestPulse (采矿脉冲)"],
            ["超载过载", "25", "12.0", "自身范围", "+0 (加成)", "Overdrive (攻速提升50%)"],
            ["双管齐射", "5", "0.8", "定向弹道", "+32 (穿甲)", "PhysicalArmorPiercing"],
            ["电弧震荡波", "18", "4.5", "扇形区域", "+65 (电击)", "ShockParalysis (麻痹0.5s)"],
            ["维修力场", "30", "15.0", "环形范围", "+0 (治疗)", "NanoRepair (持续修建筑)"],
            ["自爆反冲", "0", "0.0", "被动触发", "+120 (爆炸)", "FinalDetonation (亡语自爆)"],
            ["聚能穿透炮", "40", "6.0", "直线贯穿", "+210 (能量)", "PierceLine (穿透3目标)"],
            ["重力减速网", "20", "8.0", "地表投掷", "+10 (控制)", "GravitySlow (减速60%)"],
            ["燃烧弹幕", "15", "3.0", "多重弹道", "+45 (火焰)", "BurningDot (点燃3.0s)"],
            ["能量护盾阵", "35", "18.0", "定点部署", "+0 (防护)", "ForceShield (吸收150伤)"],
            ["轨道空投支援", "50", "25.0", "全局召唤", "+0 (空投)", "SupplyDrop (投送50铜)"],
            ["湮灭核打击", "100", "45.0", "全屏打击", "+500 (毁灭)", "TacticalNuke (清场核爆)"]
        ]

        lines = [
            "# 📋 可执行技能与战斗规格表 (Executable Skill Spec)",
            "> **遵循工业铁律：先定 Schema 数据结构，再填完整内容；固定值无模糊问号**\n",
            "| " + " | ".join(self.SKILL_SCHEMA_COLUMNS) + " |",
            "| " + " | ".join(["---"] * len(self.SKILL_SCHEMA_COLUMNS)) + " |"
        ]

        for r in rows:
            lines.append("| " + " | ".join(r) + " |")

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text("\n".join(lines), encoding="utf-8")
        return self.output_file

if __name__ == "__main__":
    out = ExecutableSpecGenerator((Path(__file__).resolve().parent / 'design/skills_executable_spec.md')).generate_full_spec()
    print(f"=== ExecutableSpecGenerator: 规格表生成成功 -> {out.name} ===")
