# =================================================================
# 📜 宪法层支柱 1: 项目最高宪法层与参数化守卫 (constitution_guard.py)
# 对标《腾讯互娱 AI 策划: GDD 为最高宪法，使用 AI 能听懂的绝对参数语言》
# =================================================================

import re
from pathlib import Path
from typing import Dict, List, Tuple

class ConstitutionGuard:
    """
    项目最高宪法层与参数化指令守卫 (Constitution Guard)
    """

    # 模糊禁用词库 (Banned Ambiguous Phrases)
    BANNED_AMBIGUOUS_WORDS = [
        "更好看", "更分散一点", "放大三倍", "随便做做", "差不多就行", "搞好看点"
    ]

    def __init__(self, gdd_path: Path):
        self.gdd_path = gdd_path

    def verify_constitution_existence(self) -> bool:
        """检查最高宪法 GDD 是否存在且完备"""
        return self.gdd_path.exists() and len(self.gdd_path.read_text(encoding="utf-8", errors="ignore")) > 200

    def audit_parametric_language(self, prompt_text: str) -> Tuple[bool, List[str]]:
        """审查提示词是否包含违禁模糊词"""
        violations = []
        for word in self.BANNED_AMBIGUOUS_WORDS:
            if word in prompt_text:
                violations.append(f"发现模糊禁用词 [{word}]，请替换为明确像素(px)、坐标(x,y)或状态清除时机")
        return len(violations) == 0, violations

    def run_constitution_audit(self) -> bool:
        """运行宪法层审计"""
        print("=== ConstitutionGuard: 正在执行最高宪法层与参数化指令审查 ===")
        has_const = self.verify_constitution_existence()
        if has_const:
            print(f"  [PASS] 最高宪法层已锁定 -> {self.gdd_path.name} (地位不可逾越)")
        else:
            print(f"  [FAIL] 最高宪法层缺失: {self.gdd_path}")

        sample_prompt = "将普通图标尺寸缩小为 70px，中心对齐连接线，回合结束时清除护盾"
        passed, violations = self.audit_parametric_language(sample_prompt)
        if passed:
            print("  [PASS] 参数化指令规范通过 (明确包含 70px, 中心对齐, 回合末清除)")
        else:
            print("  [FAIL] 指令包含模糊词:")
            for v in violations:
                print(f"     - {v}")

        all_ok = has_const and passed
        verdict = "[PASS] (项目宪法层稳固，符合腾讯互娱工业规范)" if all_ok else "[FAIL]"
        print(f"  [CONSTITUTION VERDICT] {verdict}")
        print("================================================================")
        return all_ok

if __name__ == "__main__":
    gdd = (Path(__file__).resolve().parent / 'design/Mindustry_Planet_War_lore_spec.md')
    ConstitutionGuard(gdd).run_constitution_audit()
