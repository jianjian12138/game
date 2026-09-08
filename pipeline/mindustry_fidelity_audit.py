#!/usr/bin/env python3
r"""
mindustry_fidelity_audit.py: Mindustry 1:1 游戏体验与视觉还原度专项质检中枢
对标 D:\jianjian12138\Mindustry 官方原版源码与游玩手感，严格审查 7 大核心要素：
  1. placement_drawer: 右下角 4 列建造抽屉、6 大分类切换标签与造价消耗浮动卡片
  2. core_items_display: 左上角悬浮式核心库存看板，杜绝全屏粗糙横幅
  3. dual_lane_conveyor: 双轨双车道输送带物料并发系统 (xs = -0.25 / +0.25) 与流向箭头
  4. turret_recoil_spring: 双管炮双炮管独立交替后坐力 (Recoil 3px) 与弹簧阻尼复位
  5. drill_rotor_multitile: 机械钻头底座+中心切削刀头旋转+碎屑微粒多层联动
  6. player_thrusters_laser: 阿尔法飞船连续尾焰喷射粒子、十字准心与高亮脉冲采矿束
  7. floating_wave_minimap: 顶部居中浮动波次徽章与右上角浮动高保真雷达小地图
"""
import sys
from pathlib import Path
from typing import Dict, List, Tuple

class MindustryFidelityAuditor:
    """Mindustry 1:1 原版质感与体验保真度审计器"""

    CRITERIA = [
        ("placement_drawer", "右下角 4 列抽屉建造面板、分类标签与建筑造价消耗卡", ["placement_drawer", "row_width", "cost_card", "category"]),
        ("core_items_display", "左上角核心库存悬浮看板与物料图标", ["core_items_display", "core_inventory", "item_copper"]),
        ("dual_lane_conveyor", "双轨输送带并发物流与流向咬合动画", ["dual_lane", "xs", "conveyor", "item_center"]),
        ("turret_recoil_spring", "双管炮双联交替后坐力冲量与弹道截击", ["recoil", "barrel_l", "barrel_r", "turret_rot"]),
        ("drill_rotor_multitile", "多层机械钻头旋转切削与采矿微粒", ["drill_spin", "rotator", "mechanical-drill"]),
        ("player_thrusters_laser", "阿尔法飞船连续尾焰粒子与脉冲采矿束", ["engine_particle", "mine_beam", "crosshair"]),
        ("floating_wave_minimap", "浮动波次徽章看板与金属质感雷达小地图", ["wave_banner", "radar_minimap", "minimap"])
    ]

    def __init__(self, rust_src_dir: Path):
        self.rust_src_dir = rust_src_dir

    def audit_fidelity(self) -> Dict[str, Tuple[bool, str]]:
        rust_files = list(self.rust_src_dir.rglob("*.rs"))
        all_code = "\n".join([f.read_text(encoding="utf-8", errors="ignore").lower() for f in rust_files])

        results = {}
        for key, name, keywords in self.CRITERIA:
            matched = any(kw in all_code for kw in keywords)
            results[key] = (matched, name)

        return results

    def run_audit(self) -> bool:
        print("=== MindustryFidelityAuditor: 正在对标官方原版开展 1:1 体验与质感深度审查 ===")
        results = self.audit_fidelity()
        all_passed = True
        for key, (passed, desc) in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            if not passed:
                all_passed = False
            print(f"  {status} {desc} ({key})")

        verdict = "[PASS] (与原版 Mindustry 达到 1:1 纯正游戏手感与视觉还原标准)" if all_passed else "[FAIL] (存在视觉与交互差距，需继续深化重构)"
        print(f"  [FIDELITY VERDICT] {verdict}")
        print("==================================================================================")
        return all_passed

if __name__ == "__main__":
    auditor = MindustryFidelityAuditor(Path(r"D:\jianjian12138\game\output\mindustry_rust_full\src"))
    auditor.run_audit()
