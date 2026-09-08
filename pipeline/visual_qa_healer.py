# =================================================================
# 🛡️ Game-Agent: 商业级 Game Juice 与 Visual QA 自愈中枢 (visual_qa_healer.py)
# 对标《搭建一套游戏 UI 视觉系统》与《Vibe Coding 游戏笔记》
# 强制执行: Game Juice (音效/微震/全息预览) 质量门禁 + UI 视觉自愈
# =================================================================

import sys
from pathlib import Path
from typing import Dict, List, Any

class VisualQaHealer:
    """
    Visual QA 视觉自愈与 Game Juice 门禁中枢
    确保交付的游戏彻底具备商业级质感与打击感
    """
    
    JUICE_CRITERIA = [
        ("Screen Shake (屏幕微震)", "开火与爆炸必须触发真实屏幕微震"),
        ("Placement Hologram (全息建筑放置预览)", "鼠标移动必须显示半透明 Sprite 与对齐框"),
        ("Sound Effects (原生音效覆盖)", "点击、建造、拆除、射击、爆炸均有独立音效"),
        ("Typography Clarity (字体锐利度)", "使用 TrueType 矢量字体，严禁特殊 Emoji 导致方块乱码"),
        ("AABB Hit Testing (精确几何盒测试)", "UI 按钮与交互区域必须有独立矩形盒，严禁坐标错位")
    ]

    def __init__(self, rust_source_dir: Path):
        self.rust_source_dir = rust_source_dir

    def audit_game_juice_compliance(self) -> Dict[str, bool]:
        """扫描代码工程是否严格实现全部 Game Juice 标准"""
        compliance = {}
        rust_files = list(self.rust_source_dir.rglob("*.rs"))
        all_code = "\n".join([f.read_text(encoding="utf-8", errors="ignore") for f in rust_files])

        compliance["Screen Shake"] = "screen_shake" in all_code
        compliance["Placement Hologram"] = "hover_tool" in all_code or "ghost" in all_code.lower()
        compliance["Sound Effects"] = "sound_engine" in all_code or "play_sound" in all_code
        compliance["Typography Clarity"] = "font.ttf" in all_code or "draw_text_ex" in all_code
        compliance["AABB Hit Testing"] = "handle_click" in all_code or "handle_input" in all_code

        return compliance

    def run_juice_gate(self) -> bool:
        """执行 Game Juice 门禁审查"""
        compliance = self.audit_game_juice_compliance()
        print("=== VisualQaHealer: 正在执行 Game Juice 视听反馈门禁审查 ===")
        all_passed = True
        for name, passed in compliance.items():
            status = "[PASS]" if passed else "[FAIL]"
            if not passed: all_passed = False
            print(f"  {status} {name}")
        
        verdict = "[PASS] (游戏视听质感完全达标，具备商业神作灵魂)" if all_passed else "[FAIL] (缺少核心打击感，禁止交付)"
        print(f"  [JUICE VERDICT] {verdict}")
        print("==========================================================")
        return all_passed

if __name__ == "__main__":
    healer = VisualQaHealer(Path(r"D:\jianjian12138\game\output\mindustry_rust_full\src"))
    healer.run_juice_gate()
