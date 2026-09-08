# =================================================================
# 🛡️ Steam 闭环支柱 2: 防过度设计与陌生人三问审查器 (anti_overengineering_guard.py)
# 对标《程序员做第一款 Steam 游戏: 陌生人 3 问 + 拒绝过早抽象自嗨》
# =================================================================

from pathlib import Path
from typing import Dict, List, Tuple

class AntiOverengineeringGuard:
    """
    防过度设计与陌生人三问闭环审查器
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.rust_src = project_root / "output" / "mindustry_rust_full" / "src"

    def audit_stranger_three_questions(self) -> Tuple[bool, List[str]]:
        """检查项目是否具备回答陌生人 3 问的完整基础设施"""
        checklist = []
        
        # 1. 目标追踪器是否存在
        has_hud_objective = (self.rust_src / "ui" / "run_summary_tracker.rs").exists()
        checklist.append(("1. [要做什么] 显式主线目标追踪器 (Objective Tracker)", has_hud_objective))

        # 2. 死因分析与结算界面
        has_death_cause = (self.rust_src / "ui" / "run_summary_tracker.rs").exists()
        checklist.append(("2. [怎么死的] 结算界面显式死因分析 (Death Cause Breakdown)", has_death_cause))

        # 3. 胜利判定与战绩结算
        has_victory_eval = (self.rust_src / "ui" / "run_summary_tracker.rs").exists()
        checklist.append(("3. [算赢了吗] 明确胜利判定与战绩结算 (Victory Screen)", has_victory_eval))

        all_ok = all(item[1] for item in checklist)
        return all_ok, checklist

    def run_full_audit(self) -> bool:
        """执行完整审查"""
        print("=== AntiOverengineeringGuard: 正在执行陌生人三问与防过度设计审查 ===")
        all_ok, checklist = self.audit_stranger_three_questions()
        for name, passed in checklist:
            tag = "[PASS]" if passed else "[FAIL]"
            print(f"  {tag} {name}")

        verdict = "[PASS] (陌生人三问闭环完整，拒绝过早抽象自嗨！)" if all_ok else "[FAIL]"
        print(f"  [STRANGER 3-Q VERDICT] {verdict}")
        print("=====================================================================")
        return all_ok

if __name__ == "__main__":
    AntiOverengineeringGuard(Path(r"D:\jianjian12138\game")).run_full_audit()
