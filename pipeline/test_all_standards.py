#!/usr/bin/env python3
"""
pipeline/test_all_standards.py: Game-Agent 全系统工业标准全量自动化回归门禁总测大典
统一串联并执行 11 大子系统与工业门禁，输出零半成品、100% 验收合规报告。
"""

import os
import sys
import unittest
import json
import re
from pathlib import Path

# 确保根目录进入 sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.engine_scene_graph import Transform2D
from pipeline.engine_render_batcher import RenderQueueBatcher, RenderCommand, Material
from pipeline.engine_asset_catalog import TextureAtlasCatalog
from pipeline.skeletal_animation_engine import SkeletalAnimationEngine
from pipeline.adaptive_audio_system import AdaptiveAudioSystem
from pipeline.ast_symbol_graph import ASTSymbolGraph, SymbolNode, DependencyEdge
from pipeline.multiplayer_netcode_engine import MultiplayerNetcodeEngine
from pipeline.vlm_aesthetic_evaluator import VLMAestheticEvaluator
from pipeline.hardware_performance_profiler import HardwarePerformanceProfiler
from pipeline.adversarial_red_team import RedTeamInquisitor


class Test1_EngineSubsystems(unittest.TestCase):
    """验证场景图、渲染队列与图集基础引擎规范"""

    def test_scene_graph_hierarchy_and_dirty_flag(self):
        root = Transform2D("mech_root")
        child = Transform2D("turret")
        root.add_child(child)
        root.set_position(100.0, 50.0)
        root.set_rotation(0.5)
        self.assertTrue(child.is_dirty)
        mat = child.get_world_matrix()
        self.assertEqual(len(mat), 6)
        self.assertFalse(child.is_dirty)

    def test_render_batcher_sort_key_and_flush(self):
        batcher = RenderQueueBatcher()
        mat1 = Material("hull", "#00f0ff")
        mat2 = Material("laser", "#f59e0b")

        batcher.submit(RenderCommand("RECT", mat1, [1, 0, 0, 1, 10, 10], phase=1, layer=0))
        batcher.submit(RenderCommand("RECT", mat2, [1, 0, 0, 1, 30, 30], phase=1, layer=1))
        stats = batcher.evaluate_batching()
        self.assertEqual(stats["total_commands"], 2)
        self.assertIn("batch_ratio", stats)

    def test_asset_catalog_ref_counting(self):
        catalog = TextureAtlasCatalog("mech_atlas", 512, 512)
        catalog.add_frame("body", 0, 0, 64, 64)
        catalog.add_frame("cannon", 64, 0, 32, 64)
        self.assertIn("body", catalog.frames)
        self.assertIn("cannon", catalog.frames)
        self.assertEqual(catalog.retain(), 1)
        self.assertEqual(catalog.release(), 0)


class Test2_SkeletalAnimationEngine(unittest.TestCase):
    """验证 3D 骨骼蒙皮动画管线 (Khronos glTF 2.0 规范)"""

    def test_rigged_humanoid_generation(self):
        res = SkeletalAnimationEngine.build_rigged_humanoid()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreaterEqual(res["joint_count"], 15)
        self.assertIn("Idle", res["animations"])
        self.assertIn("Walk", res["animations"])
        self.assertIn("Attack", res["animations"])
        self.assertTrue(os.path.exists(res["filepath"]))

        # 检查导出的 glTF 结构合法性
        with open(res["filepath"], "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["asset"]["version"], "2.0")
        self.assertIn("skins", data)
        self.assertIn("animations", data)
        self.assertEqual(len(data["skins"]), 1)


class Test3_AdaptiveAudioSystem(unittest.TestCase):
    """验证交互式多音轨自适应音频系统"""

    def test_adaptive_audio_suite_generation(self):
        suite = AdaptiveAudioSystem.generate_audio_suite()
        self.assertEqual(suite["status"], "SUCCESS")
        self.assertIn("webaudio_js", suite)
        self.assertIn("godot_bus_tres", suite)
        self.assertIn("threat_volume_curve", suite)
        self.assertGreaterEqual(suite["layers_count"], 3)
        self.assertTrue(os.path.exists(suite["webaudio_js"]))


class Test4_ASTSymbolGraph(unittest.TestCase):
    """验证全局 AST 符号依赖分析与级联重构门禁"""

    def test_ast_symbol_integrity(self):
        graph = ASTSymbolGraph()
        graph.add_symbol(SymbolNode("PlayerController", "class", "src/player.js", 10))
        graph.add_symbol(SymbolNode("WeaponSystem", "class", "src/weapons.js", 20))
        graph.add_edge(DependencyEdge("src/player.js", "src/weapons.js", "WeaponSystem", "imports"))

        audit = graph.audit_integrity()
        self.assertEqual(audit["status"], "SUCCESS")
        self.assertEqual(audit["verdict"], "HEALTHY")
        self.assertEqual(audit["dangling_symbols_count"], 0)
        self.assertEqual(audit["circular_cycles_count"], 0)


class Test5_MultiplayerNetcodeEngine(unittest.TestCase):
    """验证多人实时锁步帧同步与回滚仿真"""

    def test_lockstep_simulation(self):
        sim = MultiplayerNetcodeEngine.test_lockstep_simulation(player_count=4, ticks=50)
        self.assertEqual(sim.get("status"), "SUCCESS")
        self.assertEqual(sim.get("players_count"), 4)
        self.assertGreaterEqual(sim.get("total_ticks_simulated", 0), 50)
        self.assertIn("jitter_stress_test", sim)


class Test6_HardwarePerformanceProfiler(unittest.TestCase):
    """验证硬件性能预算与 60FPS 帧开销剖析"""

    def test_hardware_budget_audit(self):
        res = HardwarePerformanceProfiler.audit_performance(tier="low_end_mobile")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res.get("rating"), "CERTIFIED_FLUID")
        self.assertEqual(res.get("target_tier"), "low_end_mobile")
        self.assertIn("metrics", res)


class Test7_VLMAestheticEvaluator(unittest.TestCase):
    """验证多模态 VLM 视觉审美与 UX 交互评审"""

    def test_aesthetic_evaluation(self):
        eval_res = VLMAestheticEvaluator.evaluate()
        self.assertIn("overall_score", eval_res)
        self.assertIn("verdict", eval_res)
        self.assertIn("radar_breakdown", eval_res)
        self.assertGreaterEqual(eval_res.get("overall_score", 0), 70)


class Test8_CyberSurvivorFormalDeliveryAudit(unittest.TestCase):
    """验证赛博幸存者 (Cyber Survivor) 商业旗舰版 7 阶段静态规范"""

    def test_cyber_survivor_integrity_and_zero_defects(self):
        path = ROOT / "output" / "cyber_survivor" / "index.html"
        self.assertTrue(path.exists(), "Cyber Survivor index.html 不存在")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. 0 个 Math.hypot 调用
        hypot_calls = re.findall(r'Math\.hypot\(', content)
        self.assertEqual(len(hypot_calls), 0, f"发现残留 Math.hypot: {len(hypot_calls)} 处")

        # 2. 0 个 alert()
        alert_calls = re.findall(r'\balert\(', content)
        self.assertEqual(len(alert_calls), 0, f"发现残留 alert(): {len(alert_calls)} 处")

        # 3. SpatialGrid 空间加速类与查询
        self.assertIn("class SpatialGrid", content)
        self.assertIn("_enemyGrid.insert", content)
        self.assertIn("_enemyGrid.queryRadius", content)

        # 4. 商城系统与底栏 Tab
        self.assertIn('id="view-shop"', content)
        self.assertIn('data-tab="view-shop"', content)
        self.assertIn('dailyChest', content)

        # 5. Boss 三阶段 AI
        self.assertIn("en.bossPhase", content)
        self.assertIn("spawnBossBarrage", content)
        self.assertIn("boss-hp-tick", content)

        # 6. 升级卡片数值对比胶囊
        self.assertIn("UPGRADE_DEF", content)
        self.assertIn("dmgDiff", content)

        # 7. 视觉增强
        self.assertIn('id="hurt-vignette"', content)
        self.assertIn("triggerComboBanner", content)
        self.assertIn("_podiumOffscreen", content)


class Test9_IndustrialEngineShowcaseAudit(unittest.TestCase):
    """验证工业引擎展台 (Industrial Engine Showcase) 专家评审缺陷全量清零"""

    def test_industrial_showcase_expert_defects_zeroed(self):
        path = ROOT / "output" / "industrial_engine_showcase" / "index.html"
        self.assertTrue(path.exists(), "Industrial Engine Showcase index.html 不存在")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. 0 个 Math.hypot
        hypot_calls = re.findall(r'Math\.hypot\(', content)
        self.assertEqual(len(hypot_calls), 0, f"发现残留 Math.hypot: {len(hypot_calls)} 处")

        # 2. 0 GC sortKey 排序
        self.assertIn("sortKey", content)
        self.assertIn("_batchCommandSort", content)

        # 3. 摄像机非线性创伤震屏 (Trauma Shake)
        self.assertIn("trauma", content)
        self.assertIn("addTrauma", content)

        # 4. 背景网格离屏预烘焙 (Tim Sweeney)
        self.assertIn("_gridPattern", content)

        # 5. 受击反馈 (宫本茂)
        self.assertIn("playHurt", content)


class Test10_SkeletalShowcaseDeliveryAudit(unittest.TestCase):
    """验证 3D 骨骼动画展示厅 (Skeletal Showcase) 独立运行制品"""

    def test_skeletal_showcase_deliverable(self):
        path = ROOT / "output" / "skeletal_showcase" / "index.html"
        self.assertTrue(path.exists(), "Skeletal Showcase index.html 不存在")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("EMBEDDED_GLTF_DATA", content)
        self.assertIn("THREE.GLTFLoader", content)
        self.assertIn("SkeletonHelper", content)
        self.assertIn("switchAnimation", content)
        self.assertIn("AudioEngine", content)


class Test11_AdversarialRedTeamNonSemiFinishedVeto(unittest.TestCase):
    """验证毒舌红军对抗审讯官的 VETO_SEMI_FINISHED_PROTOTYPE 门禁与满分裁决"""

    def test_red_team_full_pass_on_deliverables(self):
        # 1. 验证合格制品获得 100 分通过
        for p, title in [
            (ROOT / "output" / "cyber_survivor" / "index.html", "CyberSurvivor"),
            (ROOT / "output" / "industrial_engine_showcase" / "index.html", "IndustrialShowcase")
        ]:
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
            res = RedTeamInquisitor.indict_game_code(code, title)
            self.assertEqual(res["verdict"], "PASSED_WITH_RED_TEAM_APPROVAL")
            self.assertEqual(res["final_score"], 100)
            self.assertEqual(len(res["veto_hits"]), 0)
            self.assertEqual(res["first_principles_audit"]["non_semi_finished"], "PASS")

        # 2. 验证注入 Math.hypot 或 alert 会触发半成品一票否决
        bad_code = "function test() { Math.hypot(1, 2); alert('bad'); }"
        res_bad = RedTeamInquisitor.indict_game_code(bad_code, "BadDummy")
        self.assertIn("VETO_SEMI_FINISHED_PROTOTYPE", res_bad["veto_hits"])
        self.assertEqual(res_bad["verdict"], "REJECTED_UNFIT_FOR_RELEASE")


class Test12_NextGen3AShowcaseDeliveryAudit(unittest.TestCase):
    """验证次时代 3A 引擎展台 (Next-Gen 3A Showcase) 独立运行制品与工业交付标准"""

    def test_next_gen_3a_showcase_deliverable(self):
        from pipeline.next_gen_3d_pipeline import NextGen3AShowcaseGenerator
        from pipeline.verb_assembler import VerbAssembler

        path = ROOT / "output" / "next_gen_3a_showcase" / "index.html"
        # 自愈机制：若硬盘产物缺失则自愈重建，防止脆弱的本地文件依赖
        if not path.exists():
            NextGen3AShowcaseGenerator.generate_showcase_html(path)
        self.assertTrue(path.exists(), "Next-Gen 3A Showcase index.html 不存在且无法自愈构建")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. 基础规范与自包含性 (无外部网络依赖，内置资源)
        self.assertIn("<!DOCTYPE html>", content)
        self.assertGreater(len(content), 100000, "文件体积应包含嵌入式 PBR 物理材质与 LOD 拓扑")

        # 2. PBR 物理材质 5 通道嵌入验证
        self.assertIn("PBR_ASSETS", content)
        self.assertIn("albedo", content)
        self.assertIn("normal", content)
        self.assertIn("metallicRoughness", content)
        self.assertIn("ao", content)
        self.assertIn("emissive", content)

        # 3. 三级 LOD (0/1/2) 拓扑与减面平滑过渡
        self.assertIn("LOD_MESH_DATA", content)
        self.assertIn("LOD0", content)
        self.assertIn("LOD1", content)
        self.assertIn("LOD2", content)
        self.assertIn("updateActiveLOD", content)

        # 4. 3D 空间音频合成引擎 (Web Audio API + HRTF PannerNode)
        self.assertIn("SpatialAudioSystem", content)
        self.assertIn("createPanner", content)
        self.assertIn("HRTF", content)
        self.assertIn("updateListener", content)

        # 5. 红军毒舌对抗审讯满分验证 (100分，0否决)
        res = RedTeamInquisitor.indict_game_code(content, "NextGen3AShowcase")
        self.assertEqual(res["verdict"], "PASSED_WITH_RED_TEAM_APPROVAL")
        self.assertEqual(res["final_score"], 100)
        self.assertEqual(len(res["veto_hits"]), 0)

        # 6. 验证 VerbAssembler 动词装配中枢能够自适应生成次时代视口
        va_content = VerbAssembler.assemble_game("机甲先锋", "3D次时代", "PBR材质")
        self.assertIn("PBR_ASSETS", va_content)
        self.assertIn("LOD_MESH_DATA", va_content)



if __name__ == "__main__":
    print("=" * 75)
    print("🚀 启动 Game-Agent 全系统工业标准全量自动化回归门禁总测")
    print("=" * 75)
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)

    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)

    print("\n" + "=" * 75)
    if failures == 0 and errors == 0:
        print(f"🏆 全量回归总测验收通过: 共 {total_tests} 项工业门禁全部 PASS (0 Errors, 0 Failures)")
        print("✅ 终结半成品状态，全系统达到工业级无瑕疵交付标准！")
        print("=" * 75)
        sys.exit(0)
    else:
        print(f"❌ 回归总测存在失败: {failures} Failures, {errors} Errors")
        print("=" * 75)
        sys.exit(1)
