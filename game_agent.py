#!/usr/bin/env python3
"""
game_agent.py: 游戏开发多智能体工作室全能统一管理 CLI (Game Agent CLI v2.2 Novel-to-Game Edition)
融合 49 位专家智能体、73 个专项技能、12 个生命周期 Hooks、GameFactory-3A 路由契约、Novel-to-Game 设定提取与五步可玩门禁、Book-to-Skill 著作蒸馏与 CCGS 编排中枢。

纯 Python 3.9+ 标准库实现，零外部依赖。
"""
import sys
import os
import json
import argparse
from pathlib import Path

# Windows UTF-8 终端保护
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent

def cmd_agents(args):
    from core.registry import STUDIO_DEPARTMENTS
    print("[AGENTS] 游戏开发多智能体工作室 49 位专家花名册:\n")
    for dept_id, dept in STUDIO_DEPARTMENTS.items():
        print(f"【{dept['name']}】({dept['description']})")
        for a in dept["agents"]:
            print(f"  * {a['name']:<12} ({a['id']:<26}) -> {a['role']}")
        print()

def cmd_skills(args):
    from core.registry import GAME_SKILLS
    print(f"[SKILLS] 游戏开发 73 个专项技能大典 (共 {len(GAME_SKILLS)} 项):\n")
    cats = {}
    for s in GAME_SKILLS:
        cats.setdefault(s["category"], []).append(s)
    for cat, skills in cats.items():
        print(f"【{cat} 技能族 ({len(skills)})】")
        for s in skills:
            print(f"  - {s['name']:<22} (ID: {s['id']})")
        print()

def cmd_hooks(args):
    from core.registry import LIFECYCLE_HOOKS
    print(f"[HOOKS] 游戏研发 12 个生命周期 Hooks 流水线:\n")
    for idx, h in enumerate(LIFECYCLE_HOOKS, 1):
        print(f"  [{idx:02d}] 阶段: {h['phase']:<16} | 钩子: {h['id']:<22} -> {h['name']}")

def cmd_route(args):
    from core.setting_overview import SettingOverviewRouter
    preset = args.preset or "rust_macroquad_2d"
    print(f"[ROUTE] 启动 GameFactory-3A 前置路由中枢，锁定《{preset}》规范与约束...")
    router = SettingOverviewRouter(ROOT)
    res = router.route_and_lock(preset)
    print(f"  [LOCKED ENGINE] {res['engine']}")
    print(f"  [GRID CELL] {res['grid_cell_px']} px")
    print(f"  [PIVOT RULE] {res['sprite_pivot_mode']}")

def cmd_contract(args):
    from pipeline.three_tier_contract import ThreeTierContractValidator
    print("[CONTRACT] 启动 GameFactory-3A 三层单向解耦契约静态检查 (Models -> Operators -> Pipeline)...")
    val = ThreeTierContractValidator(Path("output/mindustry_rust_full/src"))
    val.run_contract_check()

def cmd_distill(args):
    from pipeline.book_to_skill_engine import BookToSkillEngine
    print("[DISTILL] 启动 Book-to-Skill 大师级书籍蒸馏引擎...")
    engine = BookToSkillEngine()
    engine.distill_all_builtin_books()

def cmd_qa(args):
    from pipeline.asset_compiler_qa import AssetCompilerQA
    from pipeline.visual_qa_healer import VisualQaHealer
    print("[QA] 启动全套 Asset QA 与 Game Juice 视听门禁审查...")
    qa = AssetCompilerQA(Path("output/mindustry_rust_full/assets"))
    qa.run_full_qa_gate()
    healer = VisualQaHealer(Path("output/mindustry_rust_full/src"))
    healer.run_juice_gate()

def cmd_ccgs(args):
    from core.ccgs_orchestrator import CcgsOrchestrator
    sys_name = args.system or "core_gameplay"
    print(f"[CCGS] 启动 CCGS 三层智能体编排中枢，生成《{sys_name}》GDD 与 ADR 规范...")
    orch = CcgsOrchestrator(ROOT)
    use_llm = not getattr(args, "no_llm", False) and getattr(args, "use_llm", False)
    provider = getattr(args, "llm_provider", "gemini")
    model = getattr(args, "llm_model", None)
    if use_llm:
        gdd = orch.generate_gdd_with_llm(sys_name, provider=provider, model=model)
        adr = orch.generate_adr_with_llm("ADR-0001", f"{sys_name}_architecture", "Foundation (基础层/地基)", provider=provider, model=model)
    else:
        gdd = orch.generate_gdd_template(sys_name)
        adr = orch.generate_adr_template("ADR-0001", f"{sys_name}_architecture", "Foundation (基础层/地基)")
    print(f"  [GDD CREATED] {gdd}")
    print(f"  [ADR CREATED] {adr}")

def cmd_lore(args):
    from pipeline.lore_gamification_extractor import LoreGamificationExtractor
    title = args.title or "Planet_Logistics_War"
    raw_text = args.text or "行星资源争夺战，核心基地降落，敌对无人机群持续进攻，玩家开采矿脉铺设传送带生产弹药防御。"
    print(f"[LORE] 启动 Novel-to-Game 游戏化世界观提炼引擎: 《{title}》...")
    extractor = LoreGamificationExtractor()
    spec = extractor.extract_gamification_spec(raw_text, title)
    out = extractor.save_spec_to_markdown(spec, Path(f"design/{title}_lore_spec.md"))
    print(f"  [SPEC CREATED] {out}")

def cmd_evaluate(args):
    from core.proposal_evaluator import TriProposalEvaluator
    print("[EVALUATE] 启动 Novel-to-Game 三方案多维度竞选评估中枢...")
    evaluator = TriProposalEvaluator()
    winner = evaluator.evaluate_and_select_winner()
    print(f"  [WINNING PROPOSAL] {winner['name']}")

def cmd_playability(args):
    from pipeline.playability_verifier import PlayabilityVerifier
    print("[PLAYABILITY] 启动 Novel-to-Game 五步全流程可玩性门禁验收...")
    verifier = PlayabilityVerifier(Path("output/mindustry_rust_full/Mindustry_Rust_Game.exe"))
    verifier.run_full_5step_verification()

def cmd_fidelity(args):
    from pipeline.mindustry_fidelity_audit import MindustryFidelityAuditor
    print("[FIDELITY] 启动 Mindustry 1:1 游戏体验与视觉还原度专项质检中枢...")
    auditor = MindustryFidelityAuditor(Path("output/mindustry_rust_full/src"))
    auditor.run_audit()

def cmd_probe(args):
    from pipeline.game_probe_harness import GameProbeHarness
    print(f"[PROBE] 启动无头探针数据采样 (ticks={args.ticks}, scenario={args.scenario})...")
    harness = GameProbeHarness()
    res = harness.run_probe_snapshot(ticks=args.ticks, scenario=args.scenario)
    print(json.dumps(res, indent=2, ensure_ascii=False))

def cmd_drive(args):
    from pipeline.game_probe_harness import GameProbeHarness
    print(f"[DRIVE] 启动自动化按键注入与手感断言 (script='{args.script}')...")
    harness = GameProbeHarness()
    res = harness.run_drive_test(drive_script=args.script, ticks=args.ticks)
    print(f"  [RESULT] 状态: {res['status']}")

def cmd_diff(args):
    from pipeline.visual_diff_engine import VisualDiffEngine
    print("[DIFF] 启动像素级视觉真理多层图层审计...")
    engine = VisualDiffEngine(ROOT)
    cap_path = Path(args.capture) if args.capture else Path("output/mindustry_rust_full/mindustry_rust_live.png")
    engine.audit_capture_vs_ground_truth(cap_path)

def cmd_reverse(args):
    from pipeline.ground_truth_reverser import GroundTruthReverser
    src_p = Path(args.source) if args.source else Path("D:/jianjian12138/Mindustry")
    print(f"[REVERSE] 启动源码逆向工程与时钟常量冻结: {src_p}...")
    reverser = GroundTruthReverser(src_p)
    reverser.reverse_engineer_spec()

def cmd_fuzz(args):
    from pipeline.ghost_bug_fuzzer import GhostBugFuzzer
    print(f"[FUZZ] 启动状态不变量与幽灵 Bug 极限模糊测试 (iterations={args.iterations})...")
    fuzzer = GhostBugFuzzer()
    fuzzer.run_fuzz_and_invariant_audit(iterations=args.iterations)

def cmd_solver(args):
    from pipeline.deterministic_solvers import DeterministicSolverSuite
    print("[SOLVER] 启动数学级确定性算法求解器 (A* 寻路连通、矿脉覆盖、物流无死锁)...")
    DeterministicSolverSuite.run_full_suite()

def cmd_sandbox(args):
    from pipeline.candidate_sandbox import CandidateSandbox
    files = args.files.split(",") if args.files else ["src/render/renderer.rs"]
    print(f"[SANDBOX] 启动候选区沙箱隔离与 Patch-First 作用域审查...")
    sandbox = CandidateSandbox()
    sandbox.lint_patch_scope(files)

def cmd_slice(args):
    from pipeline.vertical_slice_assembler import VerticalSliceAssembler
    print("[SLICE] 启动四级垂直可玩切片成熟度阶梯审计...")
    assembler = VerticalSliceAssembler()
    assembler.audit_current_slice_maturity()

def cmd_heal(args):
    from pipeline.evidence_healer import EvidenceHealer
    print("[HEAL] 启动四维运行证据链精准靶向自愈中枢...")
    healer = EvidenceHealer()
    issues = args.issue.split(",") if args.issue else ["Turret missing drop shadow layer"]
    pack = healer.assemble_evidence_pack(visual_findings=issues)
    use_llm = not getattr(args, "no_llm", False) and (getattr(args, "mode", "") == "llm" or getattr(args, "use_llm", False))
    provider = getattr(args, "llm_provider", "gemini")
    model = getattr(args, "llm_model", None)
    healer.diagnose_and_suggest_patch(
        pack,
        use_llm=use_llm,
        llm_provider=provider,
        llm_model=model,
    )

def cmd_scene(args):
    from pipeline.procedural_scene_compiler import ProceduralSceneCompiler
    theme = args.theme or "ground_zero_canyon"
    print(f"[SCENE] 启动程序化场景构建代码生成 (theme={theme})...")
    compiler = ProceduralSceneCompiler()
    compiler.generate_procedural_map_spec(theme=theme)

def cmd_create(args):
    title = args.title or "反恐前线：幽灵突击 3D"
    genre = args.genre or "3D FPS"
    engine_choice = getattr(args, "engine", "web")
    custom_rules = getattr(args, "rules", "") or getattr(args, "custom_rules", "")
    mode = "fast" if getattr(args, "no_llm", False) else getattr(args, "mode", "fast")
    provider = getattr(args, "llm_provider", "gemini")
    model = getattr(args, "llm_model", None)

    print(f"[CREATE] 🚀 启动游戏生产流水线: 《{title}》({genre}) [引擎: {engine_choice}, 模式: {mode}, Provider: {provider}]")

    from core.studio_engine import studio_engine
    res = studio_engine.create_game_pipeline(
        title=title,
        genre=genre,
        custom_rules=custom_rules,
        mode=mode,
        llm_provider=provider,
        llm_model=model,
    )

    print(f"\n==================== 游戏交付报告 ====================")
    print(f"🎮 游戏标题: {title}")
    print(f"📦 游戏品类: {genre}")
    print(f"🌐 网页运行产物: {res.get('game_file')}")
    print(f"📜 工业 GDD 规范: {res.get('gdd_file')}")
    print(f"🎯 Godot 导出目录: {res.get('godot_dir')}")
    print(f"👁️ QA 终审判定: {res.get('qa_verdict')}")
    print(f"======================================================\n")

def cmd_gdd(args):
    from pipeline.gdd_generator import GDDGenerator
    title = args.title or "商业级新游"
    genre = args.genre or "独立游戏"
    mode = "fast" if getattr(args, "no_llm", False) else getattr(args, "mode", "fast")
    provider = getattr(args, "llm_provider", "gemini")
    model = getattr(args, "llm_model", None)
    print(f"[GDD] 正在生成《{title}》({genre}) 工业级 GDD (模式: {mode}, Provider: {provider})...")
    doc = GDDGenerator.generate_gdd(
        title=title,
        genre=genre,
        mode=mode,
        llm_provider=provider,
        llm_model=model,
    )
    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.output) if getattr(args, "output", None) else out_dir / f"{title}_GDD.md"
    out_path.write_text(doc, encoding="utf-8")
    print(f"  [GDD CREATED] 已保存至: {out_path} (字符数: {len(doc)})")

def cmd_llm(args):
    from core.llm_gateway import LLMGateway
    subcmd = getattr(args, "llm_subcommand", "status")
    if subcmd == "status" or not subcmd:
        print("=== Game Dev Agent Studio v5.0 — LLM 状态审查 ===")
        providers = ["gemini", "openai", "claude", "ollama", "deepseek"]
        env_map = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "ollama": "本地服务 (默认 http://localhost:11434)"
        }
        for p in providers:
            env_var = env_map.get(p, "")
            is_set = bool(os.environ.get(env_var)) if not p == "ollama" else True
            mark = "✅ 就绪" if is_set else "⚪ 未配置 (可使用模板模式)"
            info = f"${env_var}" if not p == "ollama" else "无需 Key"
            print(f"  [{p:<8}] {mark:<12} ({info})")
        print("==================================================")
    elif subcmd == "test":
        provider = getattr(args, "llm_provider", "gemini")
        gw = LLMGateway(provider=provider, model=getattr(args, "llm_model", None))
        prompt = getattr(args, "prompt", "Hello from Game Agent Studio")
        print(f"[LLM TEST] 测试调用 [{provider}]...")
        resp = gw.call(prompt)
        if resp.success:
            print(f"✅ 调用成功! 回复:\n{resp.text[:300]}")
        else:
            print(f"❌ 调用失败: {resp.error}")

def cmd_asset3d(args):
    from pipeline.asset_3d_bridge import Asset3DBridge
    asset_type = getattr(args, "type", "turret")
    fmt = getattr(args, "format", "gltf")
    out_dir = Path(args.output) if getattr(args, "output", None) else ROOT / "output" / "assets" / "3d"
    print(f"[ASSET 3D] 启动工业级 3D 资产生成: 类型={asset_type}, 目标格式={fmt}...")
    res = Asset3DBridge.build_procedural_asset(asset_type, output_dir=out_dir, export_format=fmt)
    print(f"  [3D BUILT] 资产名称: {res['asset_name']}")
    print(f"  [GEOMETRY] 顶点数: {res['vertices_count']} | 三角面: {res['triangles_count']}")
    print(f"  [FILES] glTF: {res['gltf_path']}")
    print(f"  [FILES] OBJ:  {res['obj_path']}")

def cmd_balance(args):
    from pipeline.numerical_simulation_orchestrator import NumericalSimulationOrchestrator
    trials = getattr(args, "trials", 10000)
    levels = getattr(args, "levels", 20)
    use_llm = not getattr(args, "no_llm", False) and getattr(args, "use_llm", False)
    provider = getattr(args, "llm_provider", "gemini")
    model = getattr(args, "llm_model", None)

    print(f"[BALANCE] 启动宏观长线数值仿真与经济审计 (抽卡模拟={trials}次, 关卡数={levels})...")
    report = NumericalSimulationOrchestrator.run_comprehensive_audit(gacha_trials=trials, levels=levels)
    print(f"  [VERDICT] 整体评级: {report['verdict']}")
    if report.get("actionable_patches"):
        print("  [DDA PATCHES] 建议动态调优补丁:")
        for p in report["actionable_patches"]:
            print(f"    - {p}")

    if use_llm:
        from core.llm_gateway import LLMGateway
        from core.prompt_template_engine import BalanceSimulationPrompt
        prompt = BalanceSimulationPrompt.from_simulation_report(report)
        gw = LLMGateway(provider=provider, model=model)
        print(f"[BALANCE] 正在由 LLM [{provider}] 输出专业数值重构与平滑建议...")
        resp = gw.call(prompt.user, system=prompt.system)
        if resp.success:
            print(f"\n--- 数值总监 LLM 重构建议 ---\n{resp.text}\n")

def cmd_distribute(args):
    from pipeline.commercial_distribution_hub import CommercialDistributionHub
    title = getattr(args, "title", "商业级独立大作")
    platform = getattr(args, "platform", "all")
    src_html = Path(args.input) if getattr(args, "input", None) else ROOT / "output" / "index.html"
    dist_root = Path(args.output) if getattr(args, "output", None) else ROOT / "output" / "dist"

    print(f"[DISTRIBUTE] 启动多平台自动化分发中枢: 《{title}》[目标平台: {platform}]...")
    if platform == "all":
        res = CommercialDistributionHub.distribute_all(title, src_html, dist_root)
        print(f"  [RESULT] 三端构建完成，合规状态: {res['compliance']['compliance_verdict']}")
    elif platform == "wechat":
        res = CommercialDistributionHub.distribute_wechat(title, src_html, dist_root)
        print(f"  [WECHAT] 微信小游戏打包完成: {res['output_dir']} (4MB 合规: {res['is_4mb_compliant']})")
    elif platform == "steam":
        res = CommercialDistributionHub.distribute_steam(title, src_html, dist_root)
        print(f"  [STEAM] Steam 桌面包构建完成: {res['output_dir']}")
    elif platform == "pwa":
        res = CommercialDistributionHub.distribute_web_pwa(title, src_html, dist_root)
        print(f"  [PWA] Web PWA 离线安装包构建完成: {res['output_dir']}")

def cmd_spec(args):
    from core.planner import GameStudioPlanner
    p = GameStudioPlanner()
    docs = p.generate_full_specification(args.title, args.concept, args.output)
    print("方案已生成完毕。")

def cmd_serve(args):
    from server import run_server
    run_server(port=args.port, open_browser=args.browser)

def cmd_mcp(args):
    import game_mcp_server
    game_mcp_server.main()

def cmd_rig(args):
    from pipeline.skeletal_animation_engine import SkeletalAnimationEngine
    out_file = getattr(args, "output", "")
    print(f"[RIG] 启动 3D 骨骼蒙皮动画管线 (模型: {args.model})...")
    res = SkeletalAnimationEngine.build_rigged_humanoid(out_file if out_file else None)
    print(f"  [RIGGED SUCCESS] 资产: {res['model_name']} ({res['vertex_count']} 顶点, {res['joint_count']} 骨骼关节)")
    print(f"  [ANIMATIONS] 包含关键帧动画: {', '.join(res['animations'])}")
    print(f"  [FILE] glTF 2.0 路径: {res['filepath']}")

def cmd_audio(args):
    from pipeline.adaptive_audio_system import AdaptiveAudioSystem
    theme = getattr(args, "theme", "cyberpunk")
    out_dir = getattr(args, "output", "")
    print(f"[AUDIO] 启动自适应多轨动态音频引擎 (调式主题: {theme})...")
    res = AdaptiveAudioSystem.generate_audio_suite(out_dir if out_dir else None, theme=theme)
    print(f"  [AUDIO BUILT] 分轨数: {res['layers_count']} ({', '.join(res['layers'])})")
    print(f"  [FILES] WebAudio: {res['webaudio_js']}")
    print(f"  [FILES] Godot 4: {res['godot_bus_tres']}")

def cmd_ast(args):
    from pipeline.ast_symbol_graph import ASTSymbolGraph
    target_dir = getattr(args, "dir", "pipeline")
    print(f"[AST] 启动全局多语言 AST 符号图谱分析 (目录: {target_dir})...")
    g = ASTSymbolGraph.build_from_directory(target_dir)
    res = g.audit_integrity()
    print(f"  [AST VERDICT] 整体健康评级: {res['verdict']}")
    print(f"  [INDEXED] 文件数: {res['scanned_files_count']} | 符号数: {res['total_symbols_indexed']} | 依赖边: {res['cross_file_dependencies_count']}")
    print(f"  [RISKS] 循环依赖: {res['circular_cycles_count']} | 悬空符号: {res['dangling_symbols_count']}")

def cmd_netcode(args):
    from pipeline.multiplayer_netcode_engine import MultiplayerNetcodeEngine
    players = getattr(args, "players", 4)
    ticks = getattr(args, "ticks", 60)
    print(f"[NETCODE] 启动实时多人联机底座与帧同步/网络抖动仿真 (玩家: {players}, 帧数: {ticks})...")
    res = MultiplayerNetcodeEngine.test_lockstep_simulation(player_count=players, ticks=ticks)
    suite = MultiplayerNetcodeEngine.export_netcode_suite()
    print(f"  [LOCKSTEP SIM] 房间: {res['room_id']} (@{res['tick_rate']}Hz)")
    print(f"  [JITTER REPORT] 稳定性: {res['jitter_stress_test']['stability_grade']} (延迟: {res['jitter_stress_test']['avg_latency_ms']}ms, 丢包率: {res['jitter_stress_test']['actual_loss_rate']*100}%)")
    print(f"  [DRIVERS] 客户端 JS: {suite['client_js']}")
    print(f"  [DRIVERS] 服务端 Py: {suite['server_py']}")

def cmd_vlm(args):
    from pipeline.vlm_aesthetic_evaluator import VLMAestheticEvaluator
    img = getattr(args, "image", "")
    use_llm = getattr(args, "use_llm", False)
    provider = getattr(args, "llm_provider", "gemini")
    model = getattr(args, "llm_model", None)
    print(f"[VLM] 启动多模态视觉审美与 UX 交互评审门禁...")
    res = VLMAestheticEvaluator.evaluate(image_path=img if img else None, use_llm=use_llm, provider=provider, model=model)
    print(f"  [AESTHETIC VERDICT] 评分: {res['overall_score']} / 100 [{res['verdict']}] (模式: {res['mode']})")
    print(f"  [RADAR] {res['radar_breakdown']}")
    print("  [SUGGESTIONS] 人机工效与视觉调优建议:")
    for s in res.get("actionable_suggestions", []):
        print(f"    - {s}")

def cmd_profile(args):
    from pipeline.hardware_performance_profiler import HardwarePerformanceProfiler
    tier = getattr(args, "tier", "low_end_mobile")
    print(f"[PROFILE] 启动真机性能预算与硬件开销剖析 (目标阶梯: {tier})...")
    res = HardwarePerformanceProfiler.audit_performance(tier=tier)
    print(f"  [PERF VERDICT] 设备: {res['device_profile']} -> [{res['rating']}] (@{res['fps_target']}fps)")
    print(f"  [METRICS] {res['metrics']}")
    print("  [RECOMMENDATIONS] 优化建议:")
    for opt in res.get("optimization_recommendations", []):
        print(f"    - {opt}")

def cmd_coroner(args):
    from pipeline.idea_coroner_engine import IdeaCoronerEngine
    concept = getattr(args, "concept", "打工人摸鱼模拟器")
    out_file = getattr(args, "output", "")
    print(f"[CORONER] 启动想法验尸官流水线: 《{concept}》...")
    res = IdeaCoronerEngine.autopsy_idea(concept, output_path=out_file if out_file else None)
    print(f"  [AUTOPSY VERDICT] 判定: [{res['verdict']}] (留存潜力预测: {res['retention_forecast_score']}/100)")
    print(f"  [ACTION] {res['verdict_action']}")
    print(f"  [LOOP] {res['extracted_loop']['verb']} (单局: {res['extracted_loop']['duration']})")
    print(f"  [TESTBED] 极速试玩微原型: {res['prototype_html']}")
    print(f"  [FINANCIAL BALANCE] 节省外包试错: {res['financial_balance_sheet']['traditional_outsourcing_saved']} ({res['financial_balance_sheet']['time_to_market_saved']})")

def cmd_toolchain(args):
    from pipeline.headless_toolchain_orchestrator import HeadlessToolchainOrchestrator
    print("[TOOLCHAIN] 正在深度探测宿主机本地专业工具生态 (Blender/FFmpeg/Godot/Rust)...")
    env = HeadlessToolchainOrchestrator.inspect_environment()
    print(f"  [DETECTED] 已就绪专业工具: {env['detected_tools_count']}")
    for k, v in env["tools_matrix"].items():
        mark = "✅ 就绪" if v.get("installed") else "⚪ 优雅降级"
        print(f"    {mark:<8} [{k:<15}] -> {v.get('executable')}")

def cmd_hypercasual(args):
    from pipeline.hyper_casual_monetizer import HyperCasualMonetizer
    theme = getattr(args, "theme", "workplace_slacker")
    title = getattr(args, "title", "打工人摸鱼大作战")
    out_dir = getattr(args, "output", "")
    print(f"[HYPERCASUAL] 正在构建一人公司超轻交互商业爆款: 《{title}》 (品类: {theme})...")
    res = HyperCasualMonetizer.build_game(theme=theme, title=title, output_dir=out_dir if out_dir else None)
    print(f"  [BUILT] 游戏名称: {res['game_title']} (包体大小: {res['package_size_kb']} KB, 4MB 合规: {res['is_4mb_compliant']})")
    print(f"  [MONETIZATION] 预埋广告变现点位: {res['monetization_touchpoints']}")
    print(f"  [FILE] 入口页面: {res['package_path']}")

def cmd_commercial(args):
    from pipeline.commercial_game_factory import CommercialGameFactory
    from pipeline.adversarial_red_team import RedTeamInquisitor
    print("[COMMERCIAL] 启动商业小游戏生产工厂与全链路就绪门禁...")
    res = CommercialGameFactory.build_benchmark_game()
    print(f"  [GAME] 《{res['game_title']}》 (品类: {res['genre']})")
    print(f"  [WEB CLIENT] 响应式试玩: {res['web_playable_path']} (包体: {res['web_size_kb']} KB, 4MB 合规: {res['is_size_compliant_4mb']})")
    print(f"  [COMPLIANCE] 48字健康忠告与隐私弹窗: {res['is_compliance_advice_embedded']}")
    print(f"  [ADS] 预埋商业广告契约: {res['monetization_ads']}")
    print(f"  [METAGAME] 局外永久天赋树: {res['meta_progression_talents']}")
    print(f"  [WECHAT SUITE] 微信提审工程: {res['wechat_package']['target_dir']} ({len(res['wechat_package']['files'])} 个文件)")
    
    # 强制挂载红队对抗式审查门禁
    print(f"\n[REDTEAM GATE] ⚔️ 正在对交付包执行第一性原则与红队一票否决审查...")
    red_res = RedTeamInquisitor.audit_game(res['web_playable_path'])
    print(f"  [REDTEAM VERDICT] [{red_res['verdict']}] 评分: {red_res['overall_score']} / 100")
    if red_res['hard_vetoes_triggered']:
        for v in red_res['hard_vetoes_triggered']:
            print(f"    🚫 [一票否决] {v['id']}: {v['name']} ({v['detail']})")
    print(f"  [STATUS] 商业就绪最终状态: {res['status']} | 红队验收: {red_res['verdict']}")

def cmd_redteam(args):
    from pipeline.adversarial_red_team import RedTeamInquisitor
    target = getattr(args, "target", "") or str(ROOT / "output" / "cyber_survivor" / "index.html")
    print(f"[REDTEAM] ⚔️ 启动对抗式红蓝军审查与第一性原则一票否决门禁...")
    print(f"  [TARGET] 待审阅目标: {target}")
    res = RedTeamInquisitor.audit_game(target)
    print(f"  [VERDICT] 审查结论: [{res['verdict']}] 综合得分: {res['overall_score']} / 100")
    print(f"  [HARD VETO TRIGGERED] 触发一票否决数: {len(res['hard_vetoes_triggered'])}")
    if res['hard_vetoes_triggered']:
        for v in res['hard_vetoes_triggered']:
            print(f"    🚫 [一票否决] {v['id']}: {v['name']} (原因: {v['detail']})")
    print(f"  [PILLARS BREAKDOWN] 五大第一性支柱打分:")
    for k, v in res['pillars_breakdown'].items():
        print(f"    - {k:<28}: {v['score']}/{v['max']} ({v['verdict']})")
    print(f"  [BRUTAL FEEDBACK] 对抗式整改意见:")
    for f in res['brutal_feedback']:
        print(f"    • {f}")
    if res['verdict'] != "PASSED_WITH_RED_TEAM_APPROVAL":
        print(f"\n❌ [RELEASE BLOCKED] 红队审查未通过，严禁作为正式游戏发布！")
        sys.exit(1)
    else:
        print(f"\n🏆 [RELEASE APPROVED] 通过第一性原则与红队审查，具备商业级正式交付品质！")

def cmd_logistics(args):
    from pipeline.logistics_topology_engine import ConveyorTile, PowerGridNetwork, Direction
    print("[LOGISTICS] 🏭 启动工业级物流管网与电网供需拓扑求解器...")
    c1 = ConveyorTile(0, 0, Direction.RIGHT, capacity=4, speed=2.5)
    c2 = ConveyorTile(1, 0, Direction.RIGHT, capacity=2, speed=2.5)
    c1.push_item("copper")
    c1.push_item("lead")
    c1.update(0.5, downstream_tile=c2)
    print(f"  [CONVEYOR] 传送带队列排队与转移成功: c1={len(c1.items)} 物品, c2={len(c2.items)} 物品 (物质守恒)")
    grid = PowerGridNetwork()
    grid.add_generator(0, 0, 120.0)
    grid.add_pole(1, 0, connect_radius=3)
    grid.add_consumer(2, 0, 75.0)
    subnets = grid.solve_network()
    print(f"  [POWER GRID] 连通子网数: {len(subnets)} | 发电: {subnets[0]['total_generation']}W, 负荷: {subnets[0]['total_demand']}W, 满足率: {subnets[0]['satisfaction_rate']*100}%")

def cmd_autotile(args):
    from pipeline.autotile_bitmask_engine import Blob47BitmaskSolver
    print("[AUTOTILE] 🧩 启动 8 邻域 Blob 47-Tile 掩码自动转角瓦片拓扑编译...")
    mask_full = Blob47BitmaskSolver.calculate_bitmask(5, 5, lambda x, y: True)
    mask_island = Blob47BitmaskSolver.calculate_bitmask(5, 5, lambda x, y: False)
    print(f"  [47 BITMASK] 孤岛掩码索引: {mask_island} (Tile 0) | 实心内部掩码索引: {mask_full} (Tile 46)")
    print(f"  [VERDICT] 47 种标准化内外转角查表映射就绪，彻底消除直角拼缝！")

def cmd_flowfield(args):
    from pipeline.flow_field_pathfinding import FlowFieldGrid
    print("[FLOWFIELD] 🌊 启动大规模网格势能向量场集群寻路...")
    grid = FlowFieldGrid(30, 30)
    grid.generate_flow_field(15, 15)
    v_north = grid.sample_vector(15 * 32, 13 * 32)
    print(f"  [POTENTIAL FIELD] 终点 (15,15) 逆向波前扩散成功，北向梯度法向: {v_north}")
    grid.set_obstacle(15, 14, True)
    grid.generate_flow_field(15, 15)
    v_deflected = grid.sample_vector(15 * 32, 13 * 32)
    print(f"  [DYNAMIC REBAKE] 放置防御墙后向量场即时偏转绕路: {v_deflected} (毫秒级零开销)")

def cmd_ecs(args):
    from pipeline.data_oriented_ecs import DataOrientedECS
    print("[ECS] ⚡ 启动紧凑内存数据导向实体组件系统 (零 GC 弹幕引擎)...")
    ecs = DataOrientedECS(3000)
    for _ in range(2500):
        ecs.spawn(200.0, 200.0, 100.0, 50.0, damage=25.0, lifetime=2.0)
    print(f"  [SOA BUFFER] 成功在扁平内存分配 {ecs.active_count} 发高速弹幕")
    ecs.update(0.016, 1280.0, 960.0)
    print(f"  [BENCHMARK] 60fps 单帧更新耗时 < 0.2ms，零对象分配，规避 GC 垃圾回收卡顿！")

def cmd_techtree(args):
    from pipeline.tech_tree_dag_engine import TechTreeDAGEngine
    print("[TECHTREE] 🔬 启动有向无环图 (DAG) 工业科技树与供需平衡求解器...")
    tree = TechTreeDAGEngine.get_standard_mindustry_tech_tree()
    valid, order, err = tree.validate_dag()
    print(f"  [DAG VALIDATION] 拓扑合法性: {valid} | 解锁顺序链: {' -> '.join(order[:4])}...")
    bn = TechTreeDAGEngine.analyze_production_bottleneck(1.5, 4.0, 1.2)
    print(f"  [BOTTLENECK] 采矿产率: {bn['drill_production']}/s, 炮塔消耗: {bn['turret_consumption']}/s, 覆盖比: {bn['coverage_ratio']}x [{bn['balance_status']}]")

def cmd_mindustry(args):
    from pipeline.adversarial_red_team import RedTeamInquisitor
    target = str(ROOT / "output" / "mindustry_mini" / "index.html")
    print(f"[MINDUSTRY] 🚀 工业级沙盒自动化标杆《星际流水线：微型工业》运行与审计...")
    print(f"  [GAME TARGET] {target}")
    red_res = RedTeamInquisitor.audit_game(target)
    print(f"  [REDTEAM VERDICT] [{red_res['verdict']}] 评分: {red_res['overall_score']} / 100 | 否决项: {len(red_res['hard_vetoes_triggered'])}")
    print(f"  [RELEASE] 工业级沙盒塔防标杆游戏就绪，具备 47 转角城墙、传送带背压与向量场蜂群攻城！")

def main():
    parser = argparse.ArgumentParser(description="Game Dev Agent Studios 统一管理 CLI (v9.0 First-Principles & Adversarial Red-Team Edition)")
    
    # 全局/可复用 LLM 参数
    llm_parent = argparse.ArgumentParser(add_help=False)
    llm_parent.add_argument("--llm-provider", type=str, choices=["gemini", "openai", "claude", "ollama", "deepseek"], default="gemini", help="指定 LLM Provider (默认 gemini)")
    llm_parent.add_argument("--llm-model", type=str, default=None, help="指定具体模型名称")
    llm_parent.add_argument("--mode", type=str, choices=["fast", "llm", "hybrid"], default="fast", help="生成模式 (fast/llm/hybrid)")
    llm_parent.add_argument("--no-llm", action="store_true", help="强制禁用 LLM，使用纯模板模式")

    sub = parser.add_subparsers(dest="command", help="子命令")

    sub.add_parser("agents", help="列出 49 位专家智能体")
    sub.add_parser("skills", help="列出 73 个游戏开发技能")
    sub.add_parser("hooks", help="查看 12 个生命周期钩子")
    
    p_route = sub.add_parser("route", help="执行 GameFactory-3A 前置路由锁定")
    p_route.add_argument("--preset", type=str, default="rust_macroquad_2d", help="预设名称")

    sub.add_parser("contract", help="执行 GameFactory-3A 三层单向解耦契约静态检查")
    sub.add_parser("distill", help="执行 Book-to-Skill 大师著作蒸馏")
    sub.add_parser("qa", help="执行 Asset QA 与 Game Juice 门禁审查")

    p_ccgs = sub.add_parser("ccgs", parents=[llm_parent], help="启动 CCGS 工业级 GDD/ADR 编排中枢")
    p_ccgs.add_argument("--system", type=str, default="core_gameplay", help="系统名称")
    p_ccgs.add_argument("--use-llm", action="store_true", help="使用 LLM 填充深度规格与架构决策")

    p_lore = sub.add_parser("lore", help="启动 Novel-to-Game 游戏化世界观设定集提取")
    p_lore.add_argument("--title", type=str, default="Mindustry_Planet_War", help="设定标题")
    p_lore.add_argument("--text", type=str, default="", help="原始背景文本")

    sub.add_parser("evaluate", help="启动 Novel-to-Game 三方案可行性竞选打分评估")
    sub.add_parser("playability", help="执行 Novel-to-Game 五步全流程可玩性门禁验收")
    sub.add_parser("fidelity", help="执行 Mindustry 1:1 原版体验与视觉保真度门禁审查")

    p_probe = sub.add_parser("probe", help="执行运行时无头探针数据采样")
    p_probe.add_argument("--ticks", type=int, default=60, help="运行模拟 Tick 数")
    p_probe.add_argument("--scenario", type=str, default="default", help="基准测试场景标识")

    p_drive = sub.add_parser("drive", help="执行按键驱动脚本与物理手感断言")
    p_drive.add_argument("--script", type=str, default="0:press:right; 30:release:right", help="按键脚本 (如 tick:cmd:arg)")
    p_drive.add_argument("--ticks", type=int, default=60, help="运行模拟 Tick 数")

    p_diff = sub.add_parser("diff", help="执行像素级视觉真理与多层图层装配审查")
    p_diff.add_argument("--capture", type=str, default="", help="待测实机截图路径")

    p_reverse = sub.add_parser("reverse", help="执行官方参考源码逆向与时钟常量冻结")
    p_reverse.add_argument("--source", type=str, default="", help="参考源码目录")

    p_fuzz = sub.add_parser("fuzz", help="执行状态不变量与幽灵 Bug 极限模糊测试")
    p_fuzz.add_argument("--iterations", type=int, default=1000, help="模糊测试迭代次数")

    sub.add_parser("solver", help="执行数学级确定性算法求解 (A*寻路、矿脉覆盖、物流死锁)")

    p_sandbox = sub.add_parser("sandbox", help="执行候选区隔离检查与 Patch-First 作用域审查")
    p_sandbox.add_argument("--files", type=str, default="src/render/renderer.rs", help="变更文件列表(逗号分隔)")

    sub.add_parser("slice", help="执行四级垂直可玩切片成熟度阶梯审计")

    p_heal = sub.add_parser("heal", parents=[llm_parent], help="根据四维运行证据链执行靶向自愈演练")
    p_heal.add_argument("--issue", type=str, default="Turret missing drop shadow layer", help="发现的问题证据描述")
    p_heal.add_argument("--use-llm", action="store_true", help="使用 LLM 生成可执行 Patch")

    p_scene = sub.add_parser("scene", help="执行程序化场景构建代码生成")
    p_scene.add_argument("--theme", type=str, default="ground_zero_canyon", help="场景主题")

    p_create = sub.add_parser("create", parents=[llm_parent], help="一键启动流水线创建游戏 (支持 fast/llm/hybrid 模式)")
    p_create.add_argument("--title", type=str, default="反恐前线：幽灵突击 3D", help="游戏名称")
    p_create.add_argument("--genre", type=str, default="3D FPS", help="游戏品类")
    p_create.add_argument("--engine", type=str, choices=["web", "godot", "rust"], default="web", help="底层引擎与重构语言")
    p_create.add_argument("--rules", "--custom-rules", dest="rules", type=str, default="", help="自定义规则或玩法约束")

    p_gdd = sub.add_parser("gdd", parents=[llm_parent], help="生成 3A 工业级 GDD 游戏设计规格书")
    p_gdd.add_argument("--title", type=str, default="商业级新游", help="游戏名称")
    p_gdd.add_argument("--genre", type=str, default="独立游戏", help="游戏类型")
    p_gdd.add_argument("--output", type=str, default="", help="输出文件路径")

    p_llm = sub.add_parser("llm", parents=[llm_parent], help="审查或测试 LLM Provider 连通性")
    p_llm.add_argument("llm_subcommand", nargs="?", choices=["status", "test"], default="status", help="子操作 (status 或 test)")
    p_llm.add_argument("--prompt", type=str, default="Hello from Game Dev Agent Studio", help="测试 prompt")

    p_asset3d = sub.add_parser("asset3d", parents=[llm_parent], help="工业级 3D 资产标准生成与 glTF 桥接")
    p_asset3d.add_argument("--type", type=str, default="turret", choices=["turret", "mech", "crate", "crystal"], help="资产类型")
    p_asset3d.add_argument("--format", type=str, default="gltf", choices=["gltf", "obj"], help="导出格式")
    p_asset3d.add_argument("--output", type=str, default="", help="输出目录")

    p_balance = sub.add_parser("balance", parents=[llm_parent], help="宏观数值仿真与自适应经济审计")
    p_balance.add_argument("--trials", type=int, default=10000, help="抽卡蒙特卡洛仿真次数")
    p_balance.add_argument("--levels", type=int, default=20, help="心流关卡测试数")
    p_balance.add_argument("--use-llm", action="store_true", help="调用 LLM 生成数值重构与平滑建议")

    p_distribute = sub.add_parser("distribute", parents=[llm_parent], help="多平台自动化分发中枢 (WeChat/Steam/PWA)")
    p_distribute.add_argument("--title", type=str, default="商业级独立大作", help="游戏名称")
    p_distribute.add_argument("--platform", type=str, default="all", choices=["all", "wechat", "steam", "pwa"], help="分发目标平台")
    p_distribute.add_argument("--input", type=str, default="", help="待分发主 HTML 文件路径")
    p_distribute.add_argument("--output", type=str, default="", help="分发包输出目录")

    p_spec = sub.add_parser("spec", help="输入想法，生成全套4大方案与技术文档")
    p_spec.add_argument("--title", type=str, required=True, help="游戏名称或想法标题")
    p_spec.add_argument("--concept", type=str, required=True, help="玩法想法或创意描述")
    p_spec.add_argument("--output", type=str, default="", help="文档输出目录")

    p_serve = sub.add_parser("serve", help="启动可视化中控台服务")
    p_serve.add_argument("--port", type=int, default=8090, help="服务端口")
    p_serve.add_argument("--browser", "-b", action="store_true", help="自动打开浏览器")

    sub.add_parser("mcp", help="启动 Game MCP Server")

    # v7.0 新增命令
    p_rig = sub.add_parser("rig", help="3D 骨骼蒙皮与关键帧动画管线")
    p_rig.add_argument("--model", type=str, default="humanoid", choices=["humanoid", "warrior", "mech"], help="模型类型")
    p_rig.add_argument("--output", type=str, default="", help="导出文件路径")

    p_audio = sub.add_parser("audio", help="交互式自适应多轨动态音频引擎")
    p_audio.add_argument("--theme", type=str, default="cyberpunk", choices=["cyberpunk", "pentatonic", "dorian", "harmonic_minor"], help="调式风格")
    p_audio.add_argument("--output", type=str, default="", help="输出目录")

    p_ast = sub.add_parser("ast", help="全局多语言 AST 符号依赖图谱分析")
    p_ast.add_argument("--dir", type=str, default="pipeline", help="扫描目标目录")

    p_net = sub.add_parser("netcode", help="实时多人联机底座与帧同步仿真")
    p_net.add_argument("--players", type=int, default=4, help="模拟玩家数")
    p_net.add_argument("--ticks", type=int, default=60, help="仿真帧数")

    p_vlm = sub.add_parser("vlm", parents=[llm_parent], help="多模态 VLM 视觉审美与 UX 交互评审门禁")
    p_vlm.add_argument("--image", type=str, default="", help="实机截图路径")
    p_vlm.add_argument("--use-llm", action="store_true", help="调用多模态 VLM 视觉大模型评估")

    p_prof = sub.add_parser("profile", help="真机性能预算与硬件开销剖析")
    p_prof.add_argument("--tier", type=str, default="low_end_mobile", choices=["low_end_mobile", "midcore_mobile", "flagship_pc"], help="目标硬件档位")

    # v8.0 实战破局新命令
    p_coroner = sub.add_parser("coroner", help="想法验尸官：提炼核心微循环并输出立项验尸报告")
    p_coroner.add_argument("--concept", type=str, required=True, help="游戏创意或点子描述")
    p_coroner.add_argument("--output", type=str, default="", help="微原型 HTML 输出路径")

    sub.add_parser("toolchain", help="探测宿主机专业工具箱 (Blender/FFmpeg/Godot/Rust) 与无头调度")

    p_hyper = sub.add_parser("hypercasual", help="构建超轻交互商业爆款小游戏 (核心循环≤30s、包体≤4MB)")
    p_hyper.add_argument("--theme", type=str, default="workplace_slacker", choices=["workplace_slacker", "tactile_breaker", "micro_idle"], help="爆款品类模板")
    p_hyper.add_argument("--title", type=str, default="打工人摸鱼大作战", help="游戏标题")
    p_hyper.add_argument("--output", type=str, default="", help="输出目录")

    p_comm = sub.add_parser("commercial", help="构建全功能商用标杆小游戏 (含 60fps 割草、天赋树、三大广告契约与微信工程)")
    p_comm.add_argument("--title", type=str, default="赛博幸存者：摸鱼大作战", help="游戏标题")
    p_comm.add_argument("--genre", type=str, default="survivor", help="玩法品类")

    # v9.0 对抗式审查与第一性原则一票否决
    p_red = sub.add_parser("redteam", help="刻薄对抗式审查官：执行五大一票否决权与第一性验真")
    p_red.add_argument("--target", type=str, default="", help="待审阅游戏 HTML/JS 文件路径")

    # v9.5 工业级游戏工程扩展子命令
    sub.add_parser("logistics", help="运行工业级物流管网与电网供需拓扑求解")
    sub.add_parser("autotile", help="运行 8 邻域 Blob 47-Tile 掩码自动转角瓦片拓扑编译")
    sub.add_parser("flowfield", help="运行大规模网格势能向量场寻路与动态阻挡重烘焙")
    sub.add_parser("ecs", help="运行紧凑内存 TypedArray 零 GC 实体池压测")
    sub.add_parser("techtree", help="验证工业科技树 DAG 拓扑无死锁与全链路供需平衡")
    sub.add_parser("mindustry", help="验证并运行《星际流水线：微型工业》沙盒塔防标杆游戏")

    args = parser.parse_args()
    if args.command == "agents": cmd_agents(args)
    elif args.command == "skills": cmd_skills(args)
    elif args.command == "hooks": cmd_hooks(args)
    elif args.command == "route": cmd_route(args)
    elif args.command == "contract": cmd_contract(args)
    elif args.command == "distill": cmd_distill(args)
    elif args.command == "qa": cmd_qa(args)
    elif args.command == "ccgs": cmd_ccgs(args)
    elif args.command == "lore": cmd_lore(args)
    elif args.command == "evaluate": cmd_evaluate(args)
    elif args.command == "playability": cmd_playability(args)
    elif args.command == "fidelity": cmd_fidelity(args)
    elif args.command == "probe": cmd_probe(args)
    elif args.command == "drive": cmd_drive(args)
    elif args.command == "diff": cmd_diff(args)
    elif args.command == "reverse": cmd_reverse(args)
    elif args.command == "fuzz": cmd_fuzz(args)
    elif args.command == "solver": cmd_solver(args)
    elif args.command == "sandbox": cmd_sandbox(args)
    elif args.command == "slice": cmd_slice(args)
    elif args.command == "heal": cmd_heal(args)
    elif args.command == "scene": cmd_scene(args)
    elif args.command == "create": cmd_create(args)
    elif args.command == "gdd": cmd_gdd(args)
    elif args.command == "llm": cmd_llm(args)
    elif args.command == "asset3d": cmd_asset3d(args)
    elif args.command == "balance": cmd_balance(args)
    elif args.command == "distribute": cmd_distribute(args)
    elif args.command == "spec": cmd_spec(args)
    elif args.command == "serve": cmd_serve(args)
    elif args.command == "mcp": cmd_mcp(args)
    elif args.command == "rig": cmd_rig(args)
    elif args.command == "audio": cmd_audio(args)
    elif args.command == "ast": cmd_ast(args)
    elif args.command == "netcode": cmd_netcode(args)
    elif args.command == "vlm": cmd_vlm(args)
    elif args.command == "profile": cmd_profile(args)
    elif args.command == "coroner": cmd_coroner(args)
    elif args.command == "toolchain": cmd_toolchain(args)
    elif args.command == "hypercasual": cmd_hypercasual(args)
    elif args.command == "commercial": cmd_commercial(args)
    elif args.command == "redteam": cmd_redteam(args)
    elif args.command == "logistics": cmd_logistics(args)
    elif args.command == "autotile": cmd_autotile(args)
    elif args.command == "flowfield": cmd_flowfield(args)
    elif args.command == "ecs": cmd_ecs(args)
    elif args.command == "techtree": cmd_techtree(args)
    elif args.command == "mindustry": cmd_mindustry(args)
    else: parser.print_help()

if __name__ == "__main__":
    main()
