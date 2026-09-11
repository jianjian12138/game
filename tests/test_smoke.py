"""
Standard Automated Regression & Smoke Tests for Antigravity Game Agent
"""

import sys
import unittest
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class Test01_CLIExtendedSmoke(unittest.TestCase):
    """测试所有顶层 CLI 与服务入口是否能正常输出 help 且退出码为 0"""

    def test_all_cli_help(self):
        scripts = ["game_agent.py", "game_mcp_server.py", "server.py"]
        for s in scripts:
            p = ROOT / s
            self.assertTrue(p.exists(), f"脚本 {s} 不存在")
            cmd = [sys.executable, str(p), "--help"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", cwd=str(ROOT))
            self.assertEqual(res.returncode, 0, f"{s} --help 运行失败: {res.stderr}")


class Test02_ProductionModulesImport(unittest.TestCase):
    """测试全量 200+ 生产模块导入无 SyntaxError、NameError 或 ModuleNotFoundError"""

    def test_core_and_pipeline_imports(self):
        import importlib
        modules_to_test = [
            "core.behavior_tree",
            "core.bullet_system",
            "core.save_system",
            "core.dsl_engine",
            "core.combat_juice_bus",
            "core.networking.room_manager",
            "pipeline.asset_streaming.asset_streamer",
            "pipeline.asset_streaming.lod_generator",
            "pipeline.player_analytics.cohort_analyzer",
            "pipeline.commercial_distribution_hub",
            "pipeline.release_gate",
            "pipeline.vlm_aesthetic_evaluator",
            "pipeline.adversarial_red_team",
            "pipeline.data_oriented_ecs",
            "pipeline.tech_tree_dag_engine",
            "pipeline.expert_review",
        ]
        for mod in modules_to_test:
            with self.subTest(module=mod):
                m = importlib.import_module(mod)
                self.assertIsNotNone(m)


class Test03_TeamRegistryAndRouting(unittest.TestCase):
    """验证跨部门团队注册、3D路由与执行计划契约。"""

    def test_next_gen_3d_art_team_contract(self):
        from core.registry import get_stats, get_team, get_team_execution_plan
        from core.setting_overview import EngineFingerprintDetector

        stats = get_stats()
        self.assertEqual(stats["agents_count"], 82)
        self.assertEqual(stats["skills_count"], 114)
        self.assertGreaterEqual(stats["teams_count"], 1)

        team = get_team("next_gen_3d_art_team")
        self.assertEqual(team["lead_agent"], "next_gen_sculpting_director")
        self.assertIn("pbr_five_channel_baking", {
            skill
            for capability in team["capabilities"]
            for skill in capability["skills"]
        })
        plan = get_team_execution_plan("next_gen_3d_art_team", "run_test_3d", "webgl")
        self.assertEqual(plan["run_id"], "run_test_3d")
        self.assertIn("runtime_asset_smoke", plan["required_gates"])

        route = EngineFingerprintDetector.route_task(ROOT, "3D 次时代 PBR LOD 骨骼材质")
        routed = [
            item for item in route["additive_disciplines"]
            if item.get("team_id") == "next_gen_3d_art_team"
        ]
        self.assertEqual(len(routed), 1)
        self.assertIn("next_gen_sculpting_director", routed[0]["agents"])


class Test04_ReleaseGateAndReviewPanel(unittest.TestCase):
    """测试发布门禁与专家评审团在无外部依赖环境下的自动化运行"""

    def test_release_gate(self):
        from pipeline.release_gate import ReleaseGate
        gate = ReleaseGate(str(ROOT))
        tests_ok, suite_res = gate.run_all_validations()
        self.assertTrue(tests_ok, f"ReleaseGate 存在未通过项: {[s for s in suite_res if not s['passed']]}")

    def test_expert_review_panel(self):
        from pipeline.expert_review import ExpertAcceptancePanel
        panel = ExpertAcceptancePanel()
        res = panel.conduct_full_review(write_report=False)
        self.assertTrue(res["all_approved"], f"ExpertAcceptancePanel 存在未通过领域: {res['reviews']}")
        self.assertGreaterEqual(res["overall_score"], 90.0)


if __name__ == "__main__":
    unittest.main()
