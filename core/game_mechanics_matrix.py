# =================================================================
# ⚙️ 游戏机制支柱 1: 系统 · 操作 · 规则三位一体矩阵 (game_mechanics_matrix.py)
# 对标《游戏玩法分析之一：游戏机制（深度 · 广度 · 整合度）》
# 显式定义每个游戏组件的系统归属、操作动词与运作规则
# =================================================================

import json
from pathlib import Path
from typing import Dict, List, Any

class GameMechanicsMatrix:
    """
    游戏机制三位一体矩阵 (Systems-Actions-Rules Matrix)
    """

    MECHANICS_REGISTRY = {
        "mechanical_drill": {
            "name": "机械钻头 (Mechanical Drill)",
            "system": "Resource Mining System (采矿子系统)",
            "actions": [
                "HOVER: 全息显示采矿覆盖范围与可采矿石类型",
                "PLACE: 扣除 12 铜矿放置在矿脉上",
                "DECONSTRUCT: 鼠标右键拆除并返还 100% 资源"
            ],
            "rules": {
                "mining_speed": "0.4 物品/秒 (铜/铅/煤炭)",
                "hardness_tier": 1,
                "power_requirement": "无需电力 (基础机械式)",
                "output_rule": "自动将矿物排出至相邻 4 方向的传送带或存储容器"
            }
        },
        "conveyor_belt": {
            "name": "传送带 (Conveyor Belt)",
            "system": "Logistics & Supply Pipeline (物流与输送子系统)",
            "actions": [
                "DRAG_PLACE: 鼠标按住拖拽直线连续铺设",
                "ROTATE: 滚轮或按 R 顺时针旋转输送朝向",
                "CONNECT: 自动与相邻同向传送带建立链条"
            ],
            "rules": {
                "throughput": "4.5 物品/秒",
                "capacity": "每格最多容纳 4 个物品单元",
                "flow_rule": "遇阻挡自动停止推进，遇分流器自动 1:1 分流"
            }
        },
        "duo_turret": {
            "name": "双管炮塔 (Duo Turret)",
            "system": "Combat Defense System (防御与火力子系统)",
            "actions": [
                "PLACE: 扣除 35 铜矿部署在关键要道",
                "MANUAL_AIM: 玩家机甲靠近时可右键接管射击视角",
                "UPGRADE: 接入科技树解锁穿甲弹药"
            ],
            "rules": {
                "range": "150.0 像素半径 (360 度旋转)",
                "fire_rate": "2.5 发/秒",
                "ammo_intake": "接收铜矿 (单发伤害 9) 或石墨 (单发伤害 18, 射程 +20%)",
                "synergy_rule": "弹药充足时自主追踪最近敌机，弹药耗尽时进入待机状态"
            }
        },
        "combustion_generator": {
            "name": "火力发电机 (Combustion Generator)",
            "system": "Power & Energy Grid (电力与能源子系统)",
            "actions": [
                "PLACE: 部署并自动连接 100px 范围内的电网节点",
                "FEED_COAL: 传送带送入煤炭/木材自动点火"
            ],
            "rules": {
                "power_output": "60 能量/秒",
                "fuel_duration": "每块煤炭燃烧 1.5 秒",
                "synergy_rule": "供电充足时为邻近钻机提供 +50% 采矿超频加速"
            }
        }
    }

    def generate_matrix_document(self, output_file: Path) -> Path:
        """生成标准机制三位一体大典"""
        lines = [
            "# ⚙️ 游戏机制三位一体大典: 系统 (System) · 操作 (Action) · 规则 (Rule)",
            "> **遵循经典游戏机制设计哲学：兼具系统深度、广度与高整合度涌现**\n",
            "---\n"
        ]

        for key, m in self.MECHANICS_REGISTRY.items():
            lines.append(f"## 🔹 {m['name']}")
            lines.append(f"- **系统归属 (System)**: `{m['system']}`")
            lines.append("- **支持操作 (Actions / Verbs)**:")
            for a in m["actions"]:
                lines.append(f"  - `{a}`")
            lines.append("- **运作规则与公式 (Rules & Formulas)**:")
            for rk, rv in m["rules"].items():
                lines.append(f"  - **{rk}**: `{rv}`")
            lines.append("\n---\n")

        output_file.write_text("\n".join(lines), encoding="utf-8")
        return output_file

if __name__ == "__main__":
    matrix = GameMechanicsMatrix()
    doc = matrix.generate_matrix_document(Path(r"D:\jianjian12138\game\knowledge\game_mechanics_matrix.md"))
    print(f"=== GameMechanicsMatrix: 机制大典已生成 -> {doc.name} ===")
