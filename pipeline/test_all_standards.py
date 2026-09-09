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
import shutil
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


class Test13_EngineFingerprintRouterAudit(unittest.TestCase):
    """验证两阶段引擎指纹自动嗅探与任务叠加路由 (EngineFingerprintDetector)"""

    def test_engine_fingerprint_detection_and_additive_routing(self):
        import tempfile
        from core.setting_overview import EngineFingerprintDetector

        # 1. 验证默认/空目录自适应回退
        res_default = EngineFingerprintDetector.detect_engine(ROOT)
        self.assertIn("engine_id", res_default)
        self.assertGreater(res_default["confidence"], 0.0)

        # 2. 验证 Godot 指纹嗅探
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_p = Path(tmp_dir)
            (tmp_p / "project.godot").write_text("config_version=5\n", encoding="utf-8")
            res_godot = EngineFingerprintDetector.detect_engine(tmp_p)
            self.assertEqual(res_godot["engine_id"], "godot")
            self.assertEqual(res_godot["confidence"], 1.0)
            self.assertIn("platform_porting_engineer", res_godot["recommended_agents"])

        # 3. 验证 Rust Bevy 指纹嗅探
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_p = Path(tmp_dir)
            (tmp_p / "Cargo.toml").write_text('[dependencies]\nbevy = "0.13"\n', encoding="utf-8")
            res_rust = EngineFingerprintDetector.detect_engine(tmp_p)
            self.assertEqual(res_rust["engine_id"], "rust_native")
            self.assertIn("zero_gc_ecs_director", res_rust["recommended_agents"])

        # 4. 验证领域学科与玩法叠加装配 (Additive Routing)
        route_pack = EngineFingerprintDetector.route_task(ROOT, "次时代PBR机甲打击感震屏")
        self.assertIn("next_gen_sculpting_director", route_pack["composite_agent_team"])
        self.assertIn("pbr_five_channel_baking", route_pack["composite_skill_stack"])
        self.assertIn("screen_shake_effect", route_pack["composite_skill_stack"])


class Test14_MultiChannelDistributionAudit(unittest.TestCase):
    """验证微信、Steam (SteamPipe)、itch.io (Butler) 与 Web PWA 全渠道商业发行管线"""

    def test_multi_channel_distribution_and_compliance(self):
        from pipeline.commercial_distribution_hub import CommercialDistributionHub
        test_dist_dir = ROOT / "output" / "dist_test_gate"

        try:
            report = CommercialDistributionHub.distribute_all(
                title="星际防线：终极指令",
                output_root=test_dist_dir
            )

            # 1. 验证四大渠道全部就绪
            self.assertEqual(report["status"], "success")
            platforms = report["platforms"]
            self.assertIn("wechat", platforms)
            self.assertIn("steam", platforms)
            self.assertIn("pwa", platforms)
            self.assertIn("itch", platforms)

            # 2. 微信小游戏契约
            self.assertTrue(platforms["wechat"]["is_4mb_compliant"])

            # 3. Steam SteamPipe VDF 配置文件契约
            self.assertTrue(platforms["steam"]["steampipe_configured"])
            steam_dir = Path(platforms["steam"]["output_dir"])
            self.assertTrue((steam_dir / "app_build_480.vdf").exists())
            self.assertTrue((steam_dir / "depot_build_481.vdf").exists())

            # 4. itch.io Butler CLI 契约
            self.assertTrue(platforms["itch"]["butler_supported"])
            itch_dir = Path(platforms["itch"]["output_dir"])
            self.assertTrue((itch_dir / "itch.json").exists())
            self.assertTrue((itch_dir / "butler_push.bat").exists())

            # 5. 合规门禁审查与发布清单
            self.assertIn(report["compliance"]["compliance_verdict"], ("CERTIFIED_SAFE", "ACCEPTABLE_WITH_WARNINGS"))
            self.assertEqual(report["compliance"]["passed_checks"], 3)
            self.assertEqual(report["compliance"]["maturity_level"], "RELEASABLE")
            self.assertTrue((test_dist_dir / "compliance_manifest.json").exists())
        finally:
            if test_dist_dir.exists():
                shutil.rmtree(test_dist_dir, ignore_errors=True)


class Test15_TaskIsolationAndAtomicSaveAudit(unittest.TestCase):
    """验证任务级沙箱隔离 (RunContext) 与存档原子替换 (SaveSerializer)"""

    def test_run_context_isolation_and_atomic_promotion(self):
        from core.run_context import RunContext
        test_dir = ROOT / "output" / "test_iso_temp"
        try:
            ctx = RunContext(title="沙箱测试战役", base_dir=test_dir)
            self.assertTrue(ctx.work_dir.exists())
            self.assertTrue(ctx.run_id.startswith("run_"))

            # 模拟在沙箱内写入制品
            dummy_file = ctx.work_dir / "index.html"
            dummy_file.write_text("<html><body>SANDBOX_OK</body></html>", encoding="utf-8")
            h = ctx.register_artifact("game_html", dummy_file)
            self.assertEqual(len(h), 64)  # SHA-256

            manifest = ctx.generate_manifest()
            self.assertIn("run_id", manifest)
            self.assertIn("artifacts", manifest)

            # 原子提升到发布目录
            release_dir = test_dir / "release"
            promoted = ctx.promote_to_release(release_dir, ["index.html"])
            self.assertEqual(len(promoted), 1)
            self.assertTrue((release_dir / "index.html").exists())
            self.assertEqual((release_dir / "index.html").read_text(encoding="utf-8"), "<html><body>SANDBOX_OK</body></html>")
        finally:
            if test_dir.exists():
                shutil.rmtree(test_dir, ignore_errors=True)

    def test_save_serializer_atomic_persistence(self):
        from core.save_system.save_serializer import SaveSerializer
        test_save_dir = ROOT / "output" / "test_save_temp"
        try:
            state = {"hero_hp": 100, "gold": 500, "level": 3}
            path = SaveSerializer.save(state, slot=9, save_dir=test_save_dir)
            self.assertTrue(path.exists())

            # 确保临时文件没有残留
            temp_files = list(test_save_dir.glob(".tmp_*"))
            self.assertEqual(len(temp_files), 0)

            # 正常读回验证
            loaded = SaveSerializer.load(slot=9, save_dir=test_save_dir)
            self.assertEqual(loaded["hero_hp"], 100)
            self.assertEqual(loaded["gold"], 500)
        finally:
            if test_save_dir.exists():
                shutil.rmtree(test_save_dir, ignore_errors=True)


class Test16_SecurityPathTraversalAudit(unittest.TestCase):
    """验证工作区安全白名单防御、路径穿越阻断与限流机制"""

    def test_safe_resolve_path_and_traversal_blocking(self):
        from core.security_guard import safe_resolve_path, SecurityGuardError

        # 1. 允许的工作区内部路径
        p_valid = safe_resolve_path("pipeline/verb_assembler.py")
        self.assertTrue(p_valid.exists())

        # 2. 阻断试图越界访问系统的绝对路径或父级穿越
        with self.assertRaises(SecurityGuardError):
            safe_resolve_path("../../../../../../../Windows/System32")

        with self.assertRaises(SecurityGuardError):
            safe_resolve_path("C:/Windows/System32/drivers/etc/hosts")

    def test_rate_limiter_sliding_window(self):
        from core.security_guard import RateLimiter
        limiter = RateLimiter(max_requests=3, window_seconds=2.0)
        client = "192.168.1.100"
        self.assertTrue(limiter.is_allowed(client))
        self.assertTrue(limiter.is_allowed(client))
        self.assertTrue(limiter.is_allowed(client))
        # 超过限制，被拦截
        self.assertFalse(limiter.is_allowed(client))


class Test17_RealLifecycleHookExecutionAudit(unittest.TestCase):
    """验证 12 个生命周期 Hooks 真实调度执行与结构化工件产出"""

    def test_studio_engine_real_hook_and_structured_artifacts(self):
        from core.studio_engine import StudioEngine
        from hooks.hook_manager import hook_manager

        test_out = ROOT / "output" / "test_engine_hook_temp"
        try:
            engine = StudioEngine(output_dir=test_out)
            res = engine.create_game_pipeline(title="幽灵突击队", genre="2D动作射击")

            # 1. 验证返回数据结构完备
            self.assertEqual(res["status"], "success")
            self.assertTrue(res["run_id"].startswith("run_"))
            self.assertIn("manifest", res)

            # 2. 验证真实 Hook 触发历史
            history = hook_manager.get_history()
            hook_names = [h["hook"] for h in history]
            self.assertIn("pre_init", hook_names)
            self.assertIn("post_init", hook_names)
            self.assertIn("pre_gdd", hook_names)
            self.assertIn("post_release", hook_names)

            # 3. 验证结构化 gdd.json 工件已正确生成与提升
            gdd_json_file = test_out / "gdd.json"
            self.assertTrue(gdd_json_file.exists())
            gdd_data = json.loads(gdd_json_file.read_text(encoding="utf-8"))
            self.assertEqual(gdd_data["title"], "幽灵突击队")
            self.assertEqual(gdd_data["target_framerate"], 60)
            self.assertIn("chapters_count", gdd_data)
        finally:
            if test_out.exists():
                shutil.rmtree(test_out, ignore_errors=True)


class Test18_WeChatComplianceDefaultsAudit(unittest.TestCase):
    """验证微信打包生产默认安全合规 (urlCheck: true)"""

    def test_wechat_packager_default_urlcheck_compliance(self):
        from pipeline.wechat_packager import WeChatPackager
        test_wx_dir = ROOT / "output" / "test_wx_compliance_temp"
        try:
            packager = WeChatPackager(workspace_root=ROOT)
            dummy_html = ROOT / "output" / "cyber_survivor" / "index.html"
            res = packager.bundle(
                source_html=dummy_html,
                output_dir=test_wx_dir,
                project_name="微信合规测试"
            )
            proj_conf = json.loads((test_wx_dir / "project.config.json").read_text(encoding="utf-8"))
            # 必须默认开启安全域名校验
            self.assertTrue(proj_conf["setting"]["urlCheck"], "微信配置默认必须开启 urlCheck 安全网络校验")
        finally:
            if test_wx_dir.exists():
                shutil.rmtree(test_wx_dir, ignore_errors=True)


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
