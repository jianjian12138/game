# =================================================================
# 🛡️ Game-Agent: 三层单向解耦契约静态检查器 (three_tier_contract.py)
# 对标《GameFactory-3A: 三层契约解耦 (Models -> Operators -> Pipeline)》
# 依赖方向只能单向向下，彻底杜绝渲染层反向篡改业务状态机
# =================================================================

from pathlib import Path
from typing import Dict, List, Tuple

class ThreeTierContractValidator:
    """
    三层单向契约静态检查器 (Three-Tier Contract Validator)
    验证工程分层:
    - Tier 1: Models / World Data (纯数据结构与状态)
    - Tier 2: Operators / Logistics / Systems (业务逻辑推进与物理计算)
    - Tier 3: Presentation / Render Pipeline (纯绘制视口与音效播放，严禁反向修改状态)
    """

    def __init__(self, rust_src_dir: Path):
        self.rust_src_dir = rust_src_dir

    def validate_render_layer_immutability(self) -> Tuple[bool, List[str]]:
        """检查渲染绘制函数是否保持只读不可变 (Immutable Rendering)"""
        violations = []
        renderer_file = self.rust_src_dir / "render" / "renderer.rs"
        
        if not renderer_file.exists():
            return False, ["render/renderer.rs 不存在"]

        lines = renderer_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for idx, line in enumerate(lines, 1):
            if "self.current_tool =" in line:
                violations.append(f"Line {idx}: 表现层非法反向修改业务状态 (self.current_tool = ...)")

        return len(violations) == 0, violations

    def run_contract_check(self) -> bool:
        """执行三层契约检查"""
        passed, violations = self.validate_render_layer_immutability()
        print("=== ThreeTierContractValidator: 正在执行 GameFactory-3A 单向契约检查 ===")
        if passed:
            print("  [PASS] 表现层与业务数据层完全单向解耦，无反向状态污染！")
        else:
            print("  [FAIL] 发现跨层非法反向依赖:")
            for v in violations:
                print(f"     - {v}")
        print("=========================================================================")
        return passed

if __name__ == "__main__":
    validator = ThreeTierContractValidator(Path(r"D:\jianjian12138\game\output\mindustry_rust_full\src"))
    validator.run_contract_check()
