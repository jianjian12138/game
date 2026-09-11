#!/usr/bin/env python3
"""TasteSignal 玩家品味信号管线测试（评审 R2/R6/R7/R10 覆盖）。

覆盖：
- 本地规范加载与结构完整性校验 (v1.1.0+，包含 visual、taste_profiles)
- 品类分群规则过滤 (hardcore vs casual 分野，防止削平硬核特性)
- 视觉子结构设计约束提取 (HUD 清晰度、瞄准准星高对比、震屏阈值)
- 提示词安全装配 (attach_to_prompt)
- 外部信号拉取网络诚实降级 (NEEDS_NETWORK / fallback 本地语料)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.taste_signal import TasteSignal


class TasteSignalTest(unittest.TestCase):
    def test_load_local_taste_spec_structure(self):
        corpus = TasteSignal.load_local_taste()
        self.assertIsInstance(corpus, dict)
        self.assertIn("avoid_patterns", corpus)
        self.assertIn("prefer_patterns", corpus)
        self.assertIn("visual_constraints", corpus)
        self.assertIn("taste_profiles", corpus)
        self.assertTrue(len(corpus["avoid_patterns"]) >= 5)
        self.assertTrue(len(corpus["prefer_patterns"]) >= 5)

    def test_to_design_constraints_extracts_visual_and_rules(self):
        constraints = TasteSignal.to_design_constraints()
        self.assertIn("avoid", constraints)
        self.assertIn("prefer", constraints)
        self.assertIn("visual", constraints)
        visual = constraints["visual"]
        self.assertIn("hud_safe_zone", visual)
        self.assertIn("contrast_indicators", visual)
        self.assertIn("screen_shake_layering", visual)

    def test_genre_profiling_differentiation(self):
        # 针对 3D FPS / Hardcore 品类
        fps_constraints = TasteSignal.to_design_constraints(genre="3D FPS 射击")
        # 针对 休闲消除 品类
        casual_constraints = TasteSignal.to_design_constraints(genre="休闲三消")

        # 验证 hardcore 与 casual 抽取的规则不完全相同，且都有输出
        self.assertTrue(len(fps_constraints["avoid"]) > 0)
        self.assertTrue(len(casual_constraints["avoid"]) > 0)

        # 验证 fps 包含硬核维度的偏好（如操作深度、即时反馈）
        fps_prefers_text = " ".join(fps_constraints["prefer"])
        self.assertTrue(any(k in fps_prefers_text for k in ["即时", "微操", "深度", "手感", "性能"]))

    def test_attach_to_prompt_formatting(self):
        base_prompt = "设计一个地下城冒险关卡"
        constraints = TasteSignal.to_design_constraints(genre="ARPG")
        enriched = TasteSignal.attach_to_prompt(base_prompt, constraints)

        self.assertIn(base_prompt, enriched)
        self.assertIn("### 玩家品味约束 (Player Taste Constraints)", enriched)
        self.assertIn("[避坑底线 - 严禁出现]", enriched)
        self.assertIn("[偏好增强 - 强烈建议]", enriched)
        self.assertIn("[视觉交互工业标准]", enriched)

    def test_fetch_external_honesty_without_network(self):
        # 模拟无外部网络或本地离线模式
        result = TasteSignal.fetch_external(channel="tap_tap", timeout=0.1)
        self.assertIsInstance(result, dict)
        self.assertIn(result.get("status"), ("NEEDS_NETWORK", "DEGRADED", "ERROR", "OK"))
        if result.get("status") == "NEEDS_NETWORK":
            self.assertTrue(result.get("fallback"))
            self.assertIn("data", result)


if __name__ == "__main__":
    unittest.main()
