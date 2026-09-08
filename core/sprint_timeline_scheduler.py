# =================================================================
# 📅 一人工作室支柱 1: 15 天敏捷冲刺排期中枢 (sprint_timeline_scheduler.py)
# 对标《一个人6款游戏: 15 天搞定一款，工业化装配流水线》
# =================================================================

import json
from pathlib import Path
from typing import Dict, List, Any

class SprintTimelineScheduler:
    """
    15 天极速敏捷冲刺排期器 (Sprint Timeline Scheduler)
    """

    SPRINT_PHASES = [
        {
            "phase": "Phase 1: 概念与黄金母版锁定",
            "days": "Day 1 ~ Day 3",
            "goals": [
                "锁定 WorldBasis 空间基准与 48px 网格",
                "生成游戏化世界观设定集与四轮需求调研",
                "建立三层单向解耦架构蓝图"
            ],
            "deliverable": "setting_overview.md + GDD"
        },
        {
            "phase": "Phase 2: 资产切片与图集优化",
            "days": "Day 4 ~ Day 8",
            "goals": [
                "25 张核心 Sprite 贴图轴心对齐与透明通道检查",
                "8 个官方原生 OGG 音效流解析",
                "Pre-Cook 预烘焙全量资源至 GPU 显存"
            ],
            "deliverable": "Asset QA 绿灯通过报告"
        },
        {
            "phase": "Phase 3: 核心机制装配与手感打磨",
            "days": "Day 9 ~ Day 12",
            "goals": [
                "装配采矿 ➔ 物流 ➔ 能源 ➔ 防御高整合闭环",
                "注入屏幕微震、全息放置预览与粒子火花",
                "装配四阶 Synergy 搭配规则引擎"
            ],
            "deliverable": "Mindustry_Rust_Game.exe 内部试玩切片"
        },
        {
            "phase": "Phase 4: 自动化 QA 与打包发布",
            "days": "Day 13 ~ Day 15",
            "goals": [
                "运行五步全流程可玩性门禁",
                "单帧耗时压制在 16.6ms 以内 (稳 60 FPS)",
                "一键生成 Native Windows 原生可执行安装包"
            ],
            "deliverable": "最终商业发布包"
        }
    ]

    def generate_schedule_document(self, output_path: Path) -> Path:
        """输出标准 15 天敏捷排期大典"""
        lines = [
            "# 📅 一人工作室 15 天极速敏捷开发排期大典",
            "> **遵循 15 天敏捷装配铁律：以母版为基石，以排期为节奏，实现生产力降维打击**\n",
            "---\n"
        ]

        for p in self.SPRINT_PHASES:
            lines.append(f"## 🚀 {p['phase']} ({p['days']})")
            lines.append("- **核心任务与里程碑**:")
            for g in p["goals"]:
                lines.append(f"  - `{g}`")
            lines.append(f"- **阶段交付物**: `{p['deliverable']}`\n")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

if __name__ == "__main__":
    scheduler = SprintTimelineScheduler()
    out = scheduler.generate_schedule_document(Path(r"D:\jianjian12138\game\production\sprint_schedule.md"))
    print(f"=== SprintTimelineScheduler: 排期大典已生成 -> {out.name} ===")
