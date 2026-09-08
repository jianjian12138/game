# =================================================================
# 👥 AI 团队支柱 1: 六大专职角色矩阵与最小权限隔离中枢 (multi_agent_team_matrix.py)
# 对标《未来的游戏开发不是一个 AI，而是一支 AI 团队: Context 隔离与职责解耦》
# =================================================================

import json
from pathlib import Path
from typing import Dict, List, Any

class MultiAgentTeamMatrix:
    """
    AI 游戏开发团队六大专职角色与权限隔离矩阵
    """

    ROLES_DEFINITION = {
        "planner": {
            "name": "规划架构师 (Planner Agent)",
            "primary_duty": "维护全局目标、任务依赖图与 GDD 需求编号",
            "writable_paths": ["design/", "production/epics/"],
            "forbidden_paths": ["src/", "assets/"],
            "model_preference": "Fast & Global Context (极速大上下文)"
        },
        "gameplay_dev": {
            "name": "玩法程序员 (Gameplay Agent)",
            "primary_duty": "实现 State、Physics、Entities 与核心产线逻辑",
            "writable_paths": ["src/core/", "src/world/", "src/entities/", "src/content/"],
            "forbidden_paths": ["assets/", "design/gdd/", "production/releases/"],
            "model_preference": "Strong Reasoning (强代码推理)"
        },
        "ui_designer": {
            "name": "界面交互师 (UI Agent)",
            "primary_duty": "实现 UI Hierarchy、DesignTokens、发光按钮与 HUD",
            "writable_paths": ["src/ui/", "src/render/macroquad_gui.rs"],
            "forbidden_paths": ["src/core/world_basis.rs", "assets/sounds/"],
            "model_preference": "Vision + Frontend Code"
        },
        "asset_artist": {
            "name": "资产美术师 (Asset Agent)",
            "primary_duty": "25 张贴图切片、透明通道修复与 Pre-Cook 资产索引",
            "writable_paths": ["assets/"],
            "forbidden_paths": ["src/", "tests/"],
            "model_preference": "Image Generation & Asset Processor"
        },
        "qa_validator": {
            "name": "质检工程师 (QA Agent / 核心制衡)",
            "primary_duty": "天生不相信其他 Agent！专职运行 Scenario 挑刺与回归验证",
            "writable_paths": ["tests/", "pipeline/"],
            "forbidden_paths": ["src/"],
            "model_preference": "Strict Validation (严谨测试执行)"
        },
        "build_engineer": {
            "name": "发布构建师 (Build Agent)",
            "primary_duty": "配置 Target、执行 Release 编译与 Windows 原生包打包",
            "writable_paths": ["production/releases/"],
            "forbidden_paths": ["src/", "design/"],
            "model_preference": "Deterministic Script Execution"
        }
    }

    def generate_matrix_document(self, output_file: Path) -> Path:
        """生成标准多智能体团队架构大典"""
        lines = [
            "# 👥 AI 游戏开发团队六大核心角色与权限隔离大典",
            "> **遵循现代化 Multi-Agent 铁律：Context 隔离、专人专职、最小权限、制衡协作**\n",
            "---\n"
        ]

        for role_id, info in self.ROLES_DEFINITION.items():
            lines.append(f"## 🔹 {info['name']} (`{role_id}`)")
            lines.append(f"- **核心职责**: `{info['primary_duty']}`")
            lines.append(f"- **允许写入路径 (Writable)**: `{', '.join(info['writable_paths'])}`")
            lines.append(f"- **严禁写入路径 (Forbidden)**: `{', '.join(info['forbidden_paths'])}`")
            lines.append(f"- **推荐模型类别**: `{info['model_preference']}`\n")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(lines), encoding="utf-8")
        return output_file

if __name__ == "__main__":
    matrix = MultiAgentTeamMatrix()
    out = matrix.generate_matrix_document((Path(__file__).resolve().parent / 'docs/architecture/multi_agent_team_matrix.md'))
    print(f"=== MultiAgentTeamMatrix: 团队角色与权限大典已生成 -> {out.name} ===")
