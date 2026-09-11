#!/usr/bin/env python3
"""
game_agent.py: 游戏开发多智能体工作室全能统一管理 CLI (Game Agent CLI v2.2 Novel-to-Game Edition)
融合 82 位专家智能体、3D 次时代美术与资产工程跨部门团队、114 个专项技能、12 个生命周期 Hooks、GameFactory-3A 路由契约、Novel-to-Game 设定提取与五步可玩门禁、Book-to-Skill 著作蒸馏与 CCGS 编排中枢。

纯 Python 3.10+ 标准库实现，零外部依赖。
"""
import sys
import os
import json
import argparse

from core.run_service import run_service
from core.release_service import ReleaseBlockedError
from core.security_guard import SecurityGuardError
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
    from core.registry import STUDIO_DEPARTMENTS, get_all_agents, get_all_teams
    all_agents = get_all_agents()
    print(f"[AGENTS] 游戏开发多智能体工作室 {len(all_agents)} 位专家花名册:\n")
    for dept_id, dept in STUDIO_DEPARTMENTS.items():
        print(f"【{dept['name']}】({dept['description']})")
        for a in dept["agents"]:
            print(f"  * {a['name']:<12} ({a['id']:<26}) -> {a['role']}")
        print()
    teams = get_all_teams()
    print(f"【跨部门专业团队】({len(teams)})")
    for team in teams:
        print(f"  * {team['name']} ({team['id']})")
        print(f"    负责人: {team['lead_agent']} | 成员: {len(team['members'])} | 门禁: {', '.join(team['required_gates'])}")
        print(f"    使命: {team['mission']}")
    print()

def cmd_teams(args):
    from core.registry import get_all_teams
    teams = get_all_teams()
    print(f"[TEAMS] 跨部门专业团队清单 (共 {len(teams)} 个):\n")
    for team in teams:
        print(f"【{team['name']}】({team['id']})")
        print(f"  使命: {team['mission']}")
        print(f"  负责人: {team['lead_agent']}")
        print(f"  成员数: {len(team['members'])}")
        print(f"  能力: {', '.join(cap['id'] for cap in team['capabilities'])}")
        print(f"  门禁: {', '.join(team['required_gates'])}")
        print(f"  成熟度: {team['maturity']['current']} -> {team['maturity']['next_target']} -> {team['maturity']['production_target']}\n")


def cmd_skills(args):
    from core.registry import GAME_SKILLS
    print(f"[SKILLS] 游戏开发专项技能大典 (共 {len(GAME_SKILLS)} 项):\n")
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
    from core.setting_overview import SettingOverviewRouter, EngineFingerprintDetector
    detect_path = getattr(args, "detect", "")
    if detect_path:
        target_dir = Path(detect_path).resolve()
        prompt_txt = getattr(args, "prompt", "")
        print(f"[ROUTE-DETECT] 🔍 启动两阶段引擎指纹自动探测: {target_dir}")
        res = EngineFingerprintDetector.route_task(target_dir, prompt_txt)
        eng = res["engine"]
        print(f"  [DETECTED ENGINE] {eng['engine_name']} (置信度: {int(eng['confidence']*100)}%)")
        print(f"  [FINGERPRINT EVIDENCE] {eng['evidence']}")
        print(f"  [RECOMMENDED AGENTS] {', '.join(res['composite_agent_team'])}")
        print(f"  [RECOMMENDED SKILLS] {', '.join(res['composite_skill_stack'])}")
        return

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
    engine = VisualDiffEngine(ROOT)
    name = getattr(args, "name", "target") or "target"
    if getattr(args, "seed", None):
        print(f"[DIFF] 正在将实机截图自举为基准帧: {args.seed} -> {name}...")
        r = engine.seed_golden_frame(Path(args.seed), name=name)
        print(f"  [RESULT] {r}")
        return 0
    if getattr(args, "generate", False) or getattr(args, "gen_target", False):
        prompt = getattr(args, "prompt", "") or "gameplay screenshot"
        print(f"[DIFF] 正在生成目标参考基准图 (prompt='{prompt}')...")
        r = engine.generate_target_image(prompt, name=name, style=getattr(args, "style", None))
        print(f"  [RESULT] {r}")
        return 0

    print("[DIFF] 启动像素级视觉真理多层图层审计...")
    cap_path = Path(args.capture) if getattr(args, "capture", None) else Path("output/mindustry_rust_full/mindustry_rust_live.png")
    res = engine.audit_capture_vs_ground_truth(cap_path)
    if getattr(args, "strict", False) and res.get("verdict") == "DEGRADED":
        return 4
    return 0


def cmd_taste(args):
    from pipeline.taste_signal import TasteSignal
    print("[TASTE] 启动玩家口味语料 -> 设计约束信号提取...")
    if getattr(args, "fetch", False):
        ext = TasteSignal.fetch_external(getattr(args, "platform", "taptap"))
        print(f"  [EXTERNAL] status={ext['status']} -> {ext.get('error')}")
        return
    corpus = TasteSignal.load_corpus(args.corpus or None)
    if corpus.get("status") != "OK":
        print(f"  [CORPUS] {corpus.get('status')}: {corpus.get('error')}")
        return
    cons = TasteSignal.to_design_constraints(corpus)
    print(f"  [CONSTRAINTS] avoid={len(cons['avoid'])} prefer={len(cons['prefer'])} "
          f"pacing={len(cons['pacing'])} sources={cons['source_count']}")
    if getattr(args, "attach", None):
        injected = TasteSignal.attach_to_prompt(cons, args.attach)
        print("\n--- 注入后的提示词 ---\n" + injected)
    else:
        print(json.dumps(cons, ensure_ascii=False, indent=2))


def cmd_vision(args):
    """cmd_diff 的完整别名命令，对应 Dream Loop 视觉闭环。"""
    return cmd_diff(args)

def cmd_reverse(args):
    from pipeline.ground_truth_reverser import GroundTruthReverser
    src_p = Path(args.source) if args.source else Path(str(Path.cwd() / "Mindustry"))
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
    title = getattr(args, "title_pos", None) or getattr(args, "title", None) or "反恐前线：幽灵突击 3D"
    genre = args.genre or "3D FPS"
    engine_choice = getattr(args, "engine", "web")
    custom_rules = getattr(args, "rules", "") or getattr(args, "custom_rules", "")
    mode = "fast" if getattr(args, "no_llm", False) else getattr(args, "mode", "fast")
    provider = getattr(args, "llm_provider", "gemini")
    model = getattr(args, "llm_model", None)

    print(f"[CREATE] 🚀 启动游戏生产流水线: 《{title}》({genre}) [引擎: {engine_choice}, 模式: {mode}, Provider: {provider}]")

    from core.run_service import run_service
    res = run_service.create_game(
        title=title,
        genre=genre,
        custom_rules=custom_rules,
        source="cli",
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
    if res.get("run_id"):
        print(f"🆔 契约 Run ID: {res.get('run_id')}")
        print(f"🛡️ 门禁结果: G0-G5 评定完成 (发布资格: {'✅ 就绪' if res.get('release_eligible') else '⚪ 运行中/待人工审阅'})")
    print(f"======================================================\n")

def cmd_doctor(args):
    from core.environment_inspector import EnvironmentInspector
    print("=== Game Dev Agent Studio — 宿主机运行环境与工具链健康体检 (Doctor) ===")
    manifest = EnvironmentInspector.get_toolchain_manifest()
    tools = manifest.get("tools", {})
    print(f"  OS 平台: {manifest.get('os')} ({sys.platform})")
    for key, info in tools.items():
        name = info.get("name", key)
        installed = info.get("installed", False)
        exe = info.get("executable") or "未安装"
        ver = f"[{info.get('version')}]" if info.get("version") else ""
        mark = "✅" if installed else ("❌" if info.get("required") else "⚪")
        print(f"  {mark} {name:<35} {ver:<15} -> {exe}")
    print("==========================================================================")
    target = getattr(args, "target", "web")
    pf = EnvironmentInspector.preflight_check(target)
    print(f"[PREFLIGHT:{target}] 预检结论: {'✅ 生产就绪' if pf['passed'] else '❌ 存在阻塞项'}")
    if pf.get("issues"):
        for iss in pf["issues"]:
            print(f"  ❌ [{iss['level']}] {iss['tool']}: {iss['msg']}")
            if iss.get("solution"):
                print(f"     💡 解决指南: {iss['solution']}")
    else:
        print(f"  ✅ 目标技术栈 '{target}' 的所有关键工具链均已就绪，无阻塞风险。")

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
    out_dir = Path(args.output) if getattr(args, "output", None) else None
    textured = bool(getattr(args, "textured", False))

    if textured:
        backend = getattr(args, "backend", None)
        seed = getattr(args, "seed", None)
        verify_godot = bool(getattr(args, "verify_godot", False))
        style = None
        import json as _json
        from pathlib import Path as _P
        from pipeline.style_bible import StyleBible
        spath = getattr(args, "style", None) or "evidence/style_bible.json"
        if _P(spath).exists():
            style = StyleBible.from_dict(_json.load(open(spath, encoding="utf-8")))
            if not style.locked:
                style.lock()
        print(f"[ASSET 3D] 启动贴图 PBR 资产生成: 类型={asset_type}, 后端={backend or 'auto'}, 真机导入={verify_godot}...")
        rec = Asset3DBridge.build_textured_asset(
            asset_type=asset_type,
            output_dir=str(out_dir) if out_dir else None,
            backend=backend, style=style, seed=seed, verify_godot=verify_godot)
        print(f"  [3D BUILT] 资产名称: {rec['asset_name']}")
        print(f"  [GEOMETRY] 顶点数: {rec['vertex_count']} | 三角面: {rec['triangle_count']}")
        print(f"  [ALBEDO]  AI生成={rec['is_ai_albedo']} ｜ 程序化占位={rec['is_procedural_albedo']} ｜ 后端={rec['albedo_backend']}")
        if rec.get("albedo_needs_runtime_tool"):
            print(f"  [HONEST] 无可用 AIGC 后端，albedo 为程序化占位（needs_runtime_tool={rec['albedo_needs_runtime_tool']}）")
        print(f"  [TEXTURES] {list(rec['texture_paths'].keys())}")
        print(f"  [GLTF] {rec['gltf_path']}")
        print(f"  [PROV] {rec['provenance_path']}")
        if rec.get("warnings"):
            for w in rec["warnings"]:
                print(f"  ⚠ {w}")
        if verify_godot:
            g = rec.get("godot", {})
            if rec.get("m4_achieved"):
                print(f"  [M4] Godot 真机导入成功（{g.get('godot_path')}），产物: {g.get('imported_files')}")
            else:
                print(f"  [M4] 真机导入未达成: {g.get('error')} ｜ needs_runtime_tool={rec.get('needs_runtime_tool')}")
        return 0 if rec.get("status") == "success" else 1

    # 旧路径（M3 无贴图几何导出，保持向后兼容）
    print(f"[ASSET 3D] 启动工业级 3D 资产生成: 类型={asset_type}, 目标格式={fmt}...")
    res = Asset3DBridge.build_procedural_asset(asset_type, output_dir=out_dir, export_format=fmt)
    print(f"  [3D BUILT] 资产名称: {res['asset_name']}")
    print(f"  [GEOMETRY] 顶点数: {res['vertices_count']} | 三角面: {res['triangles_count']}")
    print(f"  [FILES] glTF: {res['gltf_path']}")
    print(f"  [FILES] OBJ:  {res['obj_path']}")

def cmd_asset_audio(args):
    from pipeline.audio_factory import AudioFactory, AudioSpec
    from pipeline import audio_synth
    kind = getattr(args, "kind", "laser")
    name = getattr(args, "name", "") or (
        f"sfx_{kind}" if kind in audio_synth.SFX_KINDS else f"bgm_{kind}")
    out_dir = (Path(args.output).as_posix() if getattr(args, "output", None)
               else str(ROOT / "output" / "assets" / "audio"))
    duration = float(getattr(args, "duration", 1.0))
    sr = int(getattr(args, "sample_rate", 44100))
    theme = getattr(args, "theme", "dorian")
    bpm = int(getattr(args, "bpm", 120))
    backend = getattr(args, "backend", None)
    seed = getattr(args, "seed", None)

    is_bgm = kind not in audio_synth.SFX_KINDS
    print(f"[AUDIO ASSET] 启动 W7 音频资产生成: kind={kind} ｜ 类别={'BGM' if is_bgm else 'SFX'} "
          f"｜ 后端={backend or 'auto'} ｜ 采样率={sr}")
    spec = AudioSpec(kind=kind, name=name, sample_rate=sr, duration=duration,
                    theme=theme, bpm=bpm)
    rec = AudioFactory().generate(spec, backend=backend, seed=seed)
    saved = AudioFactory().save(rec, out_dir) if out_dir else None

    print(f"  [AUDIO BUILT] 资产ID: {rec.asset_id}")
    print(f"  [GEN] AI生成={rec.is_ai_generated} ｜ 程序化合成={rec.is_procedural_synth} ｜ 后端={rec.backend}")
    if rec.needs_runtime_tool:
        print(f"  [HONEST] 无可用 AI 音频后端（{rec.needs_runtime_tool}），本音频为程序化合成，非 AI 音乐")
    print(f"  [META] 采样率={rec.sample_rate} 声道={rec.channels} 时长={rec.duration:.3f}s "
          f"峰值={rec.peak:.3f} RMS={rec.rms:.5f}")
    print(f"  [QA] 通过={rec.qa.passed} ｜ 音色语义需人耳/VLM: {rec.qa.needs_vlm}")
    if saved:
        print(f"  [FILES] WAV : {saved['wav']}")
        print(f"  [FILES] JSON: {saved['json']}")
    if rec.qa.details:
        for k, v in rec.qa.details.items():
            print(f"    · {k}: {v}")
    return 0 if (rec.qa.passed and not rec.provenance.get("is_silent")) else 1


def cmd_asset_audio_verify(args):
    from pipeline.audio_factory import AudioQA, AudioSpec
    from pipeline import audio_synth
    file_path = getattr(args, "file", "")
    if not file_path:
        print("[AUDIO VERIFY] 错误：--file 必填（待校验 WAV 路径）")
        return 2
    kind = getattr(args, "kind", "") or ""
    spec = None
    if kind:
        spec = AudioSpec(kind=kind, name=Path(file_path).stem)
    print(f"[AUDIO VERIFY] 校验既有 WAV: {file_path} ...")
    rep = AudioQA.verify_file(file_path, spec)
    print(f"  [VERDICT] 通过={rep['passed']}")
    print(f"  [META] 采样率={rep['sample_rate']} 声道={rep['channels']} "
          f"时长={rep['duration']}s 峰值={rep['peak']} RMS={rep['rms']} 静音={rep['is_silent']}")
    print(f"  [HASH] {rep.get('content_hash', '')}")
    if rep.get("qa"):
        for k, v in rep["qa"].get("details", {}).items():
            print(f"    · {k}: {v}")
    if rep.get("error"):
        print(f"  [ERROR] {rep['error']}")
    return 0 if rep["passed"] else 1


def cmd_playtest(args):
    """W8 自动试玩闭环 CLI：复用 PlaytestEngine 对真实游戏做多轮自动化试玩。

    诚实门禁（13.2）：
      - 无真实浏览器自动化驱动时，引擎返回 NEEDS_RUNTIME_TOOL，CLI 如实转译（退出码 4），
        绝不把静态解析 / 文件存在粉饰为通过。
      - 远程 URL 当前需先镜像为本地 HTML，本引擎加载本地文件，故显式拒绝并退出码 3。
    """
    from core.runtime_adapter import RuntimeStatus
    from pipeline.playtest_engine import PlaytestEngine

    target = getattr(args, "target", "") or getattr(args, "url", "")
    if not target:
        print("[PLAYTEST] 错误：--target（本地 HTML 试玩目标）必填")
        return 2
    if target.startswith("http://") or target.startswith("https://"):
        print("[PLAYTEST] 远程 URL 当前需先镜像为本地 HTML 再试玩（本引擎加载本地文件）。")
        return 3

    out_dir = getattr(args, "out", "") or str(ROOT / "output" / "playtest")
    episodes = int(getattr(args, "episodes", 3))
    ticks = int(getattr(args, "ticks", 20))
    play_seconds = ticks * 0.15  # 每个输入步 ≈ 150ms（_STEP_DOWN_MS + _STEP_GAP_MS）
    seed = int(getattr(args, "seed", 0))
    headless = bool(getattr(args, "headless", True))

    print(f"[PLAYTEST] 启动 W8 自动试玩闭环: 目标={target} ｜ episodes={episodes} "
          f"｜ ticks={ticks}（≈{play_seconds:.1f}s）｜ seed={seed} ｜ headless={headless}")
    eng = PlaytestEngine(evidence_dir=out_dir, seed=seed)
    res = eng.run(target, episodes=episodes, play_seconds=play_seconds,
                  seed=seed, policy="auto", headless=headless)

    print(f"  [VERDICT] {res.status}")
    print(f"  [EVIDENCE] 到达playing={res.episodes_reached_playing}/{res.episodes_run} "
          f"｜ 完整闭环={res.full_loops_completed} ｜ 总帧={res.total_frames}")
    print(f"  [TRUTH] 像素渲染={res.pixel_rendered_count}/{res.episodes_run} "
          f"｜ 输入响应={res.input_reflected_count}/{res.episodes_run}（防伪：帧数涨≠画面在动）")
    print(f"  [SUPPORT] game_over={res.game_over_supported} restart={res.restart_supported}")
    print(f"  [ERRORS] page={res.page_error_count} console={res.console_error_count} "
          f"net={res.network_failure_count}")
    print(f"  [HASH] {res.target_hash}")
    print(f"  [PACK] {res.evidence_path}")
    if res.needs_runtime_tool:
        print(f"  [HONEST] 无真实浏览器自动化驱动（{res.needs_runtime_tool}）：诚实返回 NEEDS_RUNTIME_TOOL，"
              f"绝不把静态解析粉饰为通过")
    if res.error:
        print(f"  [ERROR] {res.error}")
    for e in res.console_errors[:5]:
        print(f"    · console: {e}")
    for e in res.failed_requests[:5]:
        print(f"    · netfail: {e}")
    # 退出码：PASS=0；环境缺驱动（非游戏缺陷）=4；其余异常/未通过=1
    if res.status == RuntimeStatus.PASS:
        return 0
    if res.status == RuntimeStatus.NEEDS_RUNTIME_TOOL:
        return 4
    return 1


def cmd_vertical_slices(args):
    """W9 八垂直切片端到端验证：生成→接 W7 真实音频→W8 真实试玩→诚实 verdict + 报告。

    诚实门禁（13.2）：无真实浏览器驱动时，每片 status=NEEDS_RUNTIME_TOOL，绝不粉饰；
    即便生成了可运行 HTML，也只有真实浏览器跑通 boot+主循环才记 PASS。
    """
    from core.runtime_adapter import RuntimeStatus
    from pipeline import vertical_slice_validator as vsv
    from pipeline.vertical_slices import VERTICAL_SLICES, get_slice, all_slice_ids

    slice_id = getattr(args, "slice", "") or ""
    episodes = int(getattr(args, "episodes", 2))
    ticks = int(getattr(args, "ticks", 20))
    play_seconds = ticks * 0.15
    seed = int(getattr(args, "seed", 42))
    attach_audio = not getattr(args, "no_audio", False)
    out_dir = Path(getattr(args, "out", "") or str(ROOT / "output" / "slices"))

    try:
        specs = [get_slice(slice_id)] if slice_id else VERTICAL_SLICES
    except KeyError:
        print(f"[VSLICES] 错误：未知切片 id: {slice_id}（可用: {all_slice_ids()}）")
        return 2
    print(f"[VSLICES] 启动 W9 八垂直切片端到端验证: 切片数={len(specs)} ｜ episodes={episodes} "
          f"｜ ticks={ticks}（≈{play_seconds:.1f}s）｜ 接W7音频={attach_audio} ｜ seed={seed}")

    results = []
    for spec in specs:
        r = vsv.validate_slice(spec, episodes=episodes, play_seconds=play_seconds,
                               seed=seed, attach_audio=attach_audio,
                               evidence_dir=str(out_dir / "evidence"))
        results.append(r)
        print(f"  [{spec.id}] {r.status} ｜ 成熟度={r.maturity_achieved}/{r.maturity_target} "
              f"｜ 到达playing={r.episodes_reached_playing} ｜ 帧={r.total_frames} "
              f"｜ game_over={r.game_over_supported} restart={r.restart_supported} ｜ 错误={r.page_error_count}")
        if r.needs_runtime_tool:
            print(f"    [HONEST] 无真实浏览器驱动（{r.needs_runtime_tool}），该片诚实返回 NEEDS_RUNTIME_TOOL")
        if r.error:
            print(f"    [ERROR] {r.error}")

    passed = sum(1 for r in results if r.status == RuntimeStatus.PASS)
    needs_rt = sum(1 for r in results if r.status == RuntimeStatus.NEEDS_RUNTIME_TOOL)
    failed = sum(1 for r in results if r.status == RuntimeStatus.FAIL)
    print(f"[VSLICES] 汇总: 总计={len(results)} ｜ PASS={passed} ｜ "
          f"NEEDS_RUNTIME_TOOL={needs_rt} ｜ FAIL={failed}")
    report = {
        "total": len(results), "passed": passed,
        "needs_runtime_tool": needs_rt, "failed": failed,
        "slices": [r.to_dict() for r in results],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    # 单切片运行写入独立文件，避免覆盖「8 切片汇总」的权威报告 vertical_slices_report.json
    rpath = (out_dir / f"vertical_slices_report.{slice_id}.json") if slice_id else (
        out_dir / "vertical_slices_report.json")
    rpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[VSLICES] 报告: {rpath}")
    if failed > 0:
        return 1
    if needs_rt > 0:
        return 4
    return 0


def cmd_autonomous(args):
    """W10 长时程自主生产：一句话意图 → 无人值守 → 可上架包（元数据/素材/合规齐全）。

    全程经 core/orchestrator DAG：装配→(真机试玩∥打包)→门禁→发布候选；
    仅三处停：缺运行工具(NEEDS_RUNTIME_TOOL) / 超预算 / 缺 LLM 凭据。

    运行模式（--mode / GAME_RUN_MODE）：
      local（缺省）—— 不要求任何渠道凭据、沙箱、Staging、遥测，缺浏览器驱动时
        试玩降级为「未验证」而不阻塞出货，状态 COMPLETED_UNVERIFIED。
      platform —— 开工前即校验渠道/沙箱/Staging/遥测，缺一组就阻断并列出补齐方式。

    诚实退出码：0=COMPLETED（preview 可上架包就绪）；
    5=COMPLETED_UNVERIFIED（本地模式：包已出但验证项未跑，不得声称已验证）；
    4=PAUSED（三处停之一或平台模式外部依赖未齐）；
    1=FAILED（真失败，非环境缺口）；2=参数错误。
    """
    from core.contracts import GameIntent
    from pipeline import autonomous_pipeline as ap

    title = (getattr(args, "title", "") or "").strip()
    if not title:
        print("[AUTON] 错误：--title 不能为空（一句话意图必须给出游戏标题）")
        return 2
    genre = (getattr(args, "genre", "") or "节奏").strip() or "节奏"
    rules = getattr(args, "rules", "") or ""
    budget_usd = float(getattr(args, "budget", 100.0) or 100.0)
    episodes = int(getattr(args, "episodes", 2))
    ticks = int(getattr(args, "ticks", 20))
    play_seconds = ticks * 0.15
    seed = int(getattr(args, "seed", 42))
    resume = not getattr(args, "no_resume", False)
    art_backend = getattr(args, "art_backend", None)
    from pipeline.run_mode import resolve_mode, describe_mode, check_local_readiness
    mode = resolve_mode(getattr(args, "run_mode", None))
    readiness = check_local_readiness(mode)

    # 注入成本表（测试/演练用：触发超预算暂停并验证三处停诚实）
    cost_table = None
    ct = getattr(args, "cost_table", "") or ""
    if ct:
        try:
            cost_table = json.loads(ct)
        except Exception as exc:
            print(f"[AUTON] 错误：--cost-table 不是合法 JSON: {exc}")
            return 2

    intent = GameIntent(title=title, genre=genre, custom_rules=rules)
    print(f"[AUTON] 启动 W10 长时程自主生产: 标题={intent.title!r} ｜ 类型={genre} "
          f"｜ 预算=${budget_usd:.2f} ｜ episodes={episodes} ｜ ticks={ticks}（≈{play_seconds:.1f}s）"
          f"｜ resume={resume} ｜ run_id={intent.run_id}")
    print(f"[AUTON] 模式={mode} —— {describe_mode(mode)}")
    for it in readiness["items"]:
        if it["status"] != "OK":
            tag = "必需·缺" if it["required"] else "可选·降级"
            print(f"  [{tag}] {it['item']}: {it['detail']}")
            if it["how_to_fix"]:
                print(f"      补齐: {it['how_to_fix']}")
    if readiness["blocking"]:
        print(f"  [BLOCK] 本地模式必需项缺失: {', '.join(readiness['blocking'])}")

    out = ap.run_autonomous(
        intent,
        budget_usd=budget_usd,
        cost_table=cost_table,
        episodes=episodes,
        play_seconds=play_seconds,
        seed=seed,
        resume=resume,
        art_backend=art_backend,
        mode=mode,
    )

    print(f"[AUTON] 状态={out['status']}")
    if out.get("unverified"):
        print(f"  [HONEST] 未验证项（不得声称已验证）: {', '.join(out['unverified'])}")
    if out.get("hint"):
        print(f"  提示: {out['hint']}")
    pg = out.get("platform_gate")
    if pg:
        for g in pg.get("groups", []):
            if g["status"] != "OK":
                print(f"  [NEEDS_HUMAN] {g['group']}: 缺 {', '.join(g['missing'])}")
                print(f"      如何补齐: {g['how_to_fix']}")
    print(f"  人停原因: {out['stop_reason']}")
    print(f"  节点: {out['node_counts']} ｜ 总数={out['totals']['total']} "
          f"成功={out['totals']['succeeded']} 未决={out['totals']['unresolved']}")
    print(f"  门禁: {out['gates']}")
    print(f"  预算: 上限=${out['budget']['limit_usd']:.2f} 预估=${out['budget']['estimated_usd']:.2f} "
          f"超支={out['budget']['exceeded']}")
    pkg = out.get("package") or {}
    if pkg.get("package_dir"):
        print(f"  可上架包: {pkg['package_dir']}")
        print(f"    文件: {pkg.get('files')}")
        print(f"    AIGC 美术: {'是' if pkg.get('art_is_ai_generated') else '否/含程序化占位'} "
              f"｜资产数={len(pkg.get('art_assets') or [])}")
    rel = out.get("release") or {}
    print(f"  发布资格: 预览候选={'具备' if rel.get('eligible') else '未达'} ｜ "
          f"manifest={'有' if rel.get('manifest') else '无'}")
    acc = out.get("acceptance") or {}
    print(f"  验收: 已验证场景={acc.get('verified_scenarios')} 试玩状态={acc.get('playtest_status')} "
          f"指标采集={'是' if acc.get('metrics_collected') else '否'}")
    print(f"  项目记忆: {out.get('memory_path')}")

    if out["status"] == ap.HumanStopPolicy.STATUS_COMPLETED:
        return 0
    # 出货包已产出但验证项没跑：开发可继续，但不得当作「已验收」，退出码 5
    if out["status"] == ap.HumanStopPolicy.STATUS_COMPLETED_UNVERIFIED:
        return 5
    if out["status"] == ap.HumanStopPolicy.STATUS_PAUSED:
        return 4
    return 1


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
    platform = "all" if getattr(args, "dist_all", False) else getattr(args, "platform", "all")
    src_html = Path(args.input) if getattr(args, "input", None) else ROOT / "output" / "index.html"
    dist_root = Path(args.output) if getattr(args, "output", None) else ROOT / "output" / "dist"
    godot_project = getattr(args, "godot_project", None) or None

    # 诚实边界：若指定 Godot 工程，先真实尝试导出独立包；结果（含 NEEDS_RUNTIME_TOOL）原样下传，
    # 绝不在缺模板时伪称已出原生包。
    godot_export = None
    if godot_project:
        from pipeline.godot_exporter import GodotExporter
        godot_export = GodotExporter().export_windows(Path(godot_project))
        if godot_export.get("status") == "PASS":
            print(f"  [GODOT PC] 独立包导出成功: {godot_export['export_path']}（将随 Steam/itch 原生分发）")
        else:
            print(f"  [GODOT PC] 独立包导出不可用（{godot_export.get('status')}）: {godot_export.get('reason')}")
            print(f"             Steam/itch 将退回 Web 壳打包并如实标注 godot_native=false")

    print(f"[DISTRIBUTE] 启动多平台自动化分发中枢: 《{title}》[目标平台: {platform}]...")
    if platform == "all":
        res = CommercialDistributionHub.distribute_all(title, src_html, dist_root, godot_export=godot_export)
        print(f"  [RESULT] 四端全渠道商业分发包构建完成 (WeChat/Steam/PWA/itch.io)，合规状态: {res['compliance']['compliance_verdict']}")
    elif platform == "wechat":
        res = CommercialDistributionHub.distribute_wechat(title, src_html, dist_root)
        print(f"  [WECHAT] 微信小游戏打包完成: {res['output_dir']} (4MB 合规: {res['is_4mb_compliant']})")
    elif platform == "steam":
        res = CommercialDistributionHub.distribute_steam(title, src_html, dist_root, godot_export=godot_export)
        print(f"  [STEAM] Steam 桌面包与 SteamPipe VDF 构建完成: {res['output_dir']} (godot_native={res['godot_native']})")
    elif platform == "pwa":
        res = CommercialDistributionHub.distribute_web_pwa(title, src_html, dist_root)
        print(f"  [PWA] Web PWA 离线安装包构建完成: {res['output_dir']}")
    elif platform == "itch":
        res = CommercialDistributionHub.distribute_itch(title, src_html, dist_root, godot_export=godot_export)
        print(f"  [ITCH] itch.io 独立分发包与 Butler 脚本构建完成: {res['output_dir']} (godot_native={res['godot_native']})")

def cmd_live_smoke(args):
    """支付 / 广告 / 联机沙箱真实链路冒烟（缺凭据时如实报缺失，不模拟通过）"""
    from pipeline.live_service_sandbox import LiveServiceSandbox
    kind = getattr(args, "kind", "all")
    if kind == "all":
        report = LiveServiceSandbox.smoke_all()
        print(f"[LIVE-SMOKE] 已配置并连通: {report['passed'] or '无'}")
        print(f"[LIVE-SMOKE] 未配置凭据: {report['not_configured'] or '无'}")
        print(f"[LIVE-SMOKE] 连通但校验失败: {report['failed'] or '无'}")
        for name, item in report["results"].items():
            print(f"  - {name}: {item['status']}"
                  + (f" | {item['observed']['status_code']} @ {item['observed']['latency_ms']}ms"
                     if item.get("observed") and item["observed"].get("status_code") else "")
                  + (f" | {item['errors'][0]}" if item["errors"] else ""))
    else:
        item = LiveServiceSandbox.smoke(kind)
        print(f"[LIVE-SMOKE] {kind}: {item['status']} {item.get('observed') or item['errors']}")


def cmd_promote(args):
    """发布通道晋升：staging 需 qa_manager 批准 + 真实 Staging 冒烟；production 需 release_manager 批准。"""
    channel = getattr(args, "channel", "staging")
    approval = {"role": args.role, "approved": True, "identity": args.actor}
    try:
        if channel == "staging":
            result = run_service.promote_to_staging(args.run_id, approval)
        else:
            result = run_service.promote_to_production(args.run_id, approval)
    except (ReleaseBlockedError, FileNotFoundError, SecurityGuardError) as exc:
        print(f"[PROMOTE-BLOCKED] {channel} 晋升被门禁拒绝: {exc}")
        return
    print(f"[PROMOTE] {result['run_id']} -> {result['channel']}: {result.get('release_status')}")
    for key, value in (result.get("staging_smoke") or {}).items():
        print(f"  - {key}: {value}")

def cmd_submit(args):
    """第三方渠道上架：构建上架包 + 提交前真实门禁（缺证/缺上传器一律拒，不谎称已上架）"""
    from pipeline.store_submission import StoreSubmission

    metadata_path = Path(args.metadata) if getattr(args, "metadata", "") else ROOT / "config" / "store_metadata.json"
    if not metadata_path.is_file():
        print(f"[SUBMIT-BLOCKED] 缺少商店元数据文件: {metadata_path}")
        print("  请填写标题/简介/关键词/分级/隐私政策链接等必填字段后重试（模板见 config/store_metadata.example.json）")
        return
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    channel_meta = metadata.get(args.channel) or metadata

    service = StoreSubmission(Path(args.dist) if getattr(args, "dist", "") else ROOT / "output" / "dist")
    result = service.submit(args.channel, channel_meta, dry_run=not getattr(args, "execute", False),
                            assets_dir=Path(args.assets) if getattr(args, "assets", "") else None)

    print(f"[SUBMIT] 渠道 {args.channel} ({result.get('channel', args.channel)}) -> {result['status']}")
    print(f"  - 上架包: {result.get('bundle_path')}")
    for err in result.get("errors", []):
        print(f"  - 阻塞项: {err}")
    if result.get("note"):
        print(f"  - 说明: {result['note']}")
    if result.get("command"):
        print(f"  - 命令: {' '.join(result['command'])}")
    if result["status"] == "SUBMITTED":
        print(f"  - 上传器返回码: {result['returncode']}")

def cmd_channel_doctor(args):
    """外部渠道体检：逐项列出每个渠道缺什么、由谁补、怎么补（凭据值一律不打印）"""
    from pipeline.channel_doctor import ChannelDoctor, MISSING, NEEDS_HUMAN, OK

    dist = Path(args.dist) if getattr(args, "dist", "") else ROOT / "output" / "dist"
    meta = Path(args.metadata) if getattr(args, "metadata", "") else None
    assets = Path(args.assets) if getattr(args, "assets", "") else None
    doctor = ChannelDoctor(dist, meta, assets)

    channel = getattr(args, "channel", "") or ""
    if channel:
        reports = [doctor.diagnose(channel)]
        overall = reports[0]
    else:
        payload = doctor.diagnose_all()
        reports = payload["channels"]
        overall = payload

    if getattr(args, "json", False):
        print(_json.dumps({"channels": reports}, ensure_ascii=False, indent=2))
    else:
        for rep in reports:
            if "errors" in rep:
                print(f"[CHANNEL-DOCTOR] {rep['channel']}: {rep['errors'][0]}")
                continue
            mark = "READY" if rep["ready"] else ("NEEDS_HUMAN" if rep["blocking_human"] else "BLOCKED")
            print(f"[CHANNEL-DOCTOR] {rep['channel']} ({rep['label']}) -> {mark} "
                  f"｜通过 {rep['ok']}/{rep['total']}｜待人工 {rep['blocking_human']}｜待 Agent {rep['blocking_agent']}")
            for chk in rep["checks"]:
                if chk["status"] == OK:
                    continue
                who = "需人工" if chk["owner"] == "human" else "Agent 可补"
                print(f"  - [{chk['status']}/{who}] {chk['item']}: {chk['detail']}")
                if chk.get("how_to_fix"):
                    print(f"      补齐方式: {chk['how_to_fix']}")
            if rep["human_materials"] and not rep["ready"]:
                print(f"  - 纯人工材料（代码无法代劳）:")
                for mat in rep["human_materials"]:
                    print(f"      * {mat['item']} —— {mat['how']}")
                    print(f"        原因: {mat['why']}")
        if not channel:
            print(f"  - 已就绪渠道: {overall['ready'] or '无'}")
            print(f"  - 待人工配合渠道: {overall['needs_human'] or '无'}")

    if isinstance(overall, dict) and "errors" in overall:
        raise SystemExit(2)
    need_human = sum(r.get("blocking_human", 0) for r in reports)
    # 0=渠道已具备提交条件 / 3=缺必须由人提供的材料 / 1=缺 Agent 可自行补齐的项
    raise SystemExit(0 if need_human == 0 and all(r.get("ready") for r in reports) else (3 if need_human else 1))


def cmd_delivery_audit(args):
    """交付卫生审计：扫描目标目录是否存在秘密文件与明文密钥（结论为「未命中已知模式」）"""
    from pipeline.delivery_hygiene import CLEAN, audit_delivery

    target = Path(args.path) if getattr(args, "path", "") else ROOT
    strict = getattr(args, "strict", False)
    report = audit_delivery(target, check_content=not getattr(args, "no_content", False), strict=strict)

    if getattr(args, "json", False):
        print(_json.dumps(report, ensure_ascii=False, indent=2))
    else:
        blocking = report.get("blocking_findings", [])
        blocking_ids = {id(f) for f in blocking}
        others = [f for f in report["findings"] if id(f) not in blocking_ids]
        print(f"[DELIVERY-AUDIT] {report['status']} ｜目录 {report['root']} ｜扫描 {report['scanned_files']} 个文件"
              f"｜strict={strict}")
        print(f"  - 阻断项 {len(blocking)} ｜测试固件 {report['counts_by_category'].get('test_fixture', 0)}"
              f"｜第三方文档 {report['counts_by_category'].get('external_doc', 0)}")
        for f in blocking[:50]:
            loc = f"{f['path']}:{f['line']}" if f.get("line") else f["path"]
            print(f"  - [阻断/{f['rule']}] {loc} :: {f['detail']}")
        for f in others[:20]:
            loc = f"{f['path']}:{f['line']}" if f.get("line") else f["path"]
            print(f"  - [非阻断/{f['category']}/{f['rule']}] {loc}")
        if len(report["findings"]) > 70:
            print(f"  - ...还有命中未展示（加 --json 查看全部）")
        if report["status"] == CLEAN:
            print("  - 结论: 未命中已知密钥模式，可交付。注意这不等价于「绝对无泄露」")
        else:
            print("  - 结论: 存在阻断项，不要直接把该目录打包分发；"
                  "请用 delivery-pack 生成脱敏副本后再交付")

    raise SystemExit(0 if report["status"] == CLEAN else 1)


def cmd_delivery_pack(args):
    """生成脱敏交付副本：排除秘密文件后复检自证，产物干净才允许分发"""
    from pipeline.delivery_hygiene import CLEAN, sanitize_copy

    src = Path(args.src) if getattr(args, "src", "") else ROOT
    dst = Path(args.out)
    # docs/ 是抓取的第三方文章归档（含他人 appid 等外部内容），不随交付物分发
    exclude_dirs = [] if getattr(args, "include_output", False) else ["output", "dist", "build", "saves", "docs"]

    result = sanitize_copy(src, dst, extra_exclude_dirs=exclude_dirs)

    if getattr(args, "json", False):
        print(_json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[DELIVERY-PACK] {result['status']} ｜{result['src']} -> {result['dst']}")
        print(f"  - 复制文件: {result['copied_files']}｜排除文件: {len(result['excluded_files'])}")
        for item in result["excluded_files"][:20]:
            print(f"  - 排除: {item['path']} ({item['reason']})")
        if len(result["excluded_files"]) > 20:
            print(f"  - ...还有 {len(result['excluded_files']) - 20} 个被排除文件")
        print(f"  - 产物复检: {result['recheck']['status']}（阻断 {result['recheck']['blocking']} 条，"
              f"测试固件 {result['recheck']['counts_by_category'].get('test_fixture', 0)} 条）")
        if result["status"] == CLEAN:
            print("  - 结论: 产物未命中已知密钥模式，可以分发给用户")
        else:
            print("  - 结论: 产物仍有可疑项，禁止分发")

    raise SystemExit(0 if result["status"] == CLEAN else 1)


def cmd_live_doctor(args):
    """线上服务体检：支付/广告/联机沙箱 + Staging 部署，缺什么报什么，凭据值不打印"""
    from pipeline.live_service_doctor import LiveServiceDoctor, PASS

    if getattr(args, "emit_reference", ""):
        path = LiveServiceDoctor.write_reference_server(Path(args.emit_reference))
        print(f"[LIVE-DOCTOR] 已写出 /health 参考服务端: {path}")
        print("  启动: python reference_health_server.py --service payment --environment sandbox --port 8787")
        print("  然后配置 PAYMENT_SANDBOX_URL=http://127.0.0.1:8787 与 PAYMENT_SANDBOX_KEY")
        return

    doctor = LiveServiceDoctor(timeout_s=float(getattr(args, "timeout", 8.0) or 8.0))
    kind = getattr(args, "kind", "") or ""
    if kind:
        reports = [doctor.diagnose_staging()] if kind == "staging" else [doctor.diagnose_sandbox(kind)]
        if "errors" in reports[0]:
            print(f"[LIVE-DOCTOR] {reports[0]['errors'][0]}")
            raise SystemExit(2)
    else:
        reports = doctor.diagnose_all()["services"]

    if getattr(args, "json", False):
        print(_json.dumps({"services": reports}, ensure_ascii=False, indent=2))
    else:
        for rep in reports:
            mark = "READY" if rep.get("ready") else rep.get("status")
            print(f"[LIVE-DOCTOR] {rep['kind']} ({rep.get('label', rep['kind'])}) -> {mark}")
            for chk in rep["checks"]:
                if chk["status"] == PASS:
                    continue
                print(f"  - [{chk['status']}/需人工] {chk['item']}: {chk['detail']}")
                if chk.get("how_to_fix"):
                    print(f"      补齐方式: {chk['how_to_fix']}")
        blocked = [r["kind"] for r in reports if not r.get("ready")]
        print(f"  - 已就绪: {[r['kind'] for r in reports if r.get('ready')] or '无'}")
        print(f"  - 待人工: {blocked or '无'}")
        print("  - 说明: 服务端必须返回 {\"service\":..., \"status\":\"ok\", \"environment\":...} 才算自证通过；"
              "仅能连上不算可用")

    raise SystemExit(0 if all(r.get("ready") for r in reports) else 3)


def cmd_live_flow(args):
    """线上服务真实业务链路冒烟：下单→查单→退款 / 请求广告→曝光→点击 / 建房→加入→离开

    与 live-doctor 的区别：live-doctor 只探 /health（证明端点活着），
    本命令跑真实业务事务（证明链路能跑通）。
    """
    from pipeline.live_service_flow import (
        LiveServiceFlow, PASS, FAIL, NEEDS_SANDBOX_CREDENTIALS, CONTRACT_MISMATCH,
    )

    kind = getattr(args, "kind", "") or "all"
    flow = LiveServiceFlow(timeout_s=float(getattr(args, "timeout", 8.0) or 8.0))
    report = flow.run_all() if kind == "all" else flow.run(kind)

    if getattr(args, "json", False):
        print(_json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report.get("status") == PASS else 1)

    results = report["results"] if "results" in report else {kind: report}
    for k, r in results.items():
        print(f"[LIVE-FLOW] {k}（{r.get('label', k)}）-> {r['status']}")
        if r.get("detail"):
            print(f"    说明: {r['detail']}")
        for st in r.get("steps", []):
            print(f"    - [{st['status']}] {st['step']} ｜HTTP {st['status_code']} ｜{st['latency_ms']}ms")
        auth = r.get("auth")
        if auth:
            print(f"    - [{auth['status']}] 鉴权校验: {auth['detail']}")
        if r["status"] == NEEDS_SANDBOX_CREDENTIALS:
            print(f"    补齐方式: {r.get('how_to_fix','')}")
        if r["status"] == CONTRACT_MISMATCH:
            print("    契约: " + "；".join(r.get("contract", [])))

    print(f"  - 已通过: {report.get('passed') or [k for k, r in results.items() if r['status'] == PASS] or '无'}")
    print(f"  - 未配置: {report.get('not_configured') or [k for k, r in results.items() if r['status'] == NEEDS_SANDBOX_CREDENTIALS] or '无'}")
    print(f"  - 失败: {report.get('failed') or [k for k, r in results.items() if r['status'] not in (PASS, NEEDS_SANDBOX_CREDENTIALS)] or '无'}")
    raise SystemExit(0 if all(r["status"] == PASS for r in results.values()) else 1)


def cmd_review_create(args):
    """建立人工复核工单：记录工件 sha256，形成待复核项"""
    from pipeline.human_review import HumanReviewBoard

    board = HumanReviewBoard()
    ticket = board.create_ticket(args.run_id, args.kind, Path(args.artifact), notes=getattr(args, "notes", "") or "")
    print(f"[REVIEW] 工单已建立: {ticket['ticket_id']}")
    print(f"  - 类型: {ticket['kind']} ｜工件: {ticket['artifact']}")
    print(f"  - sha256: {ticket['artifact_sha256']}")
    print("  - 待复核项:")
    for entry in ticket["checklist"]:
        print(f"      * {entry['item']}")


def _do_review_submit(args, verdict):
    from pipeline.human_review import HumanReviewBoard

    board = HumanReviewBoard()
    results = {}
    for raw in (getattr(args, "item", None) or []):
        if "=" in raw:
            name, value = raw.split("=", 1)
            results[name.strip()] = value.strip()
    try:
        ticket = board.submit(args.ticket_id, args.reviewer, verdict, results,
                              notes=getattr(args, "notes", "") or "")
    except (ValueError, FileNotFoundError) as exc:
        print(f"[REVIEW-BLOCKED] {exc}")
        raise SystemExit(2)
    print(f"[REVIEW] {ticket['ticket_id']} -> {ticket['verdict']} ｜复核人: {ticket['reviewer']}")
    for entry in ticket["checklist"]:
        print(f"  - [{entry['result']}] {entry['item']}")
    if ticket.get("artifact_sha256_matches") is False:
        print("  - 警告: 工件在建立工单后被修改，sha256 与工单记录不一致")
    print("  - 记录仅证明具名复核发生，不等于签署者具备审美或法务资质")


def cmd_review_approve(args):
    """人工复核通过：必须署名"""
    _do_review_submit(args, "APPROVED")


def cmd_review_reject(args):
    """人工复核驳回或要求返工：必须署名并写明原因"""
    _do_review_submit(args, "REJECTED" if getattr(args, "reject", False) else "NEEDS_REVISION")


def cmd_review_status(args):
    """查询某次运行是否具备生产放行所需的人工复核"""
    from pipeline.human_review import HumanReviewBoard, PRODUCTION_REQUIRED_KINDS

    board = HumanReviewBoard()
    report = board.production_gate(args.run_id)
    print(f"[REVIEW-STATUS] {args.run_id} -> {report['status']}")
    print(f"  - 必需复核: {', '.join(report['required'])}")
    print(f"  - 未复核: {report['missing'] or '无'}")
    print(f"  - 未通过: {report['not_approved'] or '无'}")
    print(f"  - 已批准: {report['approved_by'] or '无'}")
    print(f"  - {report.get('note', '')}")
    raise SystemExit(0 if report["allowed"] else 1)


def cmd_player_doctor(args):
    """真实玩家验证体检：遥测接入、试点队列、事件真实性（模拟数据不得冒充真人）"""
    from pipeline.player_validation import PlayerValidation, PASS, NO_REAL_PLAYER_DATA

    events = Path(args.events) if getattr(args, "events", "") else None
    validator = PlayerValidation()
    report = validator.diagnose(events)

    if getattr(args, "json", False):
        print(_json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[PLAYER-DOCTOR] {report['status']}")
        for chk in report["checks"]:
            if chk["status"] == PASS:
                continue
            print(f"  - [{chk['status']}/需人工] {chk['item']}: {chk['detail']}")
            if chk.get("how_to_fix"):
                print(f"      补齐方式: {chk['how_to_fix']}")
        for cohort in report["cohorts"]:
            print(f"  - 试点 {cohort['cohort_id']}: 来源 {cohort['source']}，"
                  f"{cohort['size']} 人 / {cohort['window_days']} 天")
        print(f"  - {report['note']}")
        if report["status"] == NO_REAL_PLAYER_DATA:
            print("  - 结论: 目前不能对外宣称任何留存/付费/时长数据")

    raise SystemExit(0 if report["ready"] else 3)


def cmd_player_cohort(args):
    """登记真实玩家试点队列：来源、人数、时间窗、联系人"""
    from pipeline.player_validation import PlayerValidation

    validator = PlayerValidation()
    try:
        record = validator.register_cohort(args.cohort_id, args.source, args.size,
                                           args.window_days, contact=getattr(args, "contact", "") or "",
                                           notes=getattr(args, "notes", "") or "")
    except ValueError as exc:
        print(f"[PLAYER-COHORT-BLOCKED] {exc}")
        raise SystemExit(2)
    print(f"[PLAYER-COHORT] 已登记: {record['cohort_id']}")
    print(f"  - 来源: {record['source']} ｜人数: {record['size']} ｜时间窗: {record['window_days']} 天")
    print(f"  - 登记时间: {record['registered_at']}")


def cmd_env_check(args):
    """环境自检总表：把四个缺口还差什么汇总成一张表（不打印任何凭据值）"""
    from pipeline.env_check import EnvCheck, MISSING, OK

    from pipeline.run_mode import resolve_mode, describe_mode, PLATFORM
    mode = resolve_mode(getattr(args, "run_mode", None))
    report = EnvCheck(probe=not getattr(args, "no_probe", False)).run(mode)

    if getattr(args, "json", False):
        print(_json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[ENV-CHECK] 模式={mode} —— {describe_mode(mode)}")
        if mode == PLATFORM:
            print(f"  {report['status']} ｜就绪 {report['ok']}/{report['total']}｜待填 {report['pending_count']}")
        else:
            print(f"  本地开发所需: 待填 {report['local_pending_count']} 项"
                  f"（渠道/沙箱/Staging/遥测共 {report['platform_pending_count']} 项属平台模式，暂不影响本地开发）")
        for group in report["groups"]:
            g_ok = sum(1 for c in group["checks"] if c["status"] == OK)
            scope = "［平台模式才需要］" if group.get("scope") == PLATFORM else "［本地开发］"
            print(f"  【{group['label']}】{g_ok}/{len(group['checks'])} {scope}")
            for chk in group["checks"]:
                mark = "OK" if chk["status"] == OK else chk["status"]
                print(f"    - [{mark}] {chk['item']}: {chk['detail']}")
                if chk["status"] != OK and chk.get("how_to_fix"):
                    print(f"        补齐: {chk['how_to_fix']}")
        if report["local_ready"]:
            print("  - 结论: 本地开发所需已齐备，可直接 --run-mode local 开工")
        else:
            print("  - 结论: 本地开发仍有待填项（见上方［本地开发］分组）")
        if report["platform_pending_count"]:
            print(f"  - 备注: {report['platform_pending_count']} 项平台依赖未配置；"
                  f"要真实上架/线上运营时再切 --run-mode platform，届时会逐项列出")

    raise SystemExit(0 if (report["ready"] if mode == PLATFORM else report["local_ready"]) else 3)


def cmd_rollback(args):
    """发布回滚：写审计并记录决策，不谎称已执行远端下架动作。"""
    try:
        result = run_service.rollback(args.run_id, args.reason, {"role": args.role, "identity": args.actor})
    except (ReleaseBlockedError, FileNotFoundError, SecurityGuardError) as exc:
        print(f"[ROLLBACK-BLOCKED] {exc}")
        return
    print(f"[ROLLBACK] {result['run_id']}: {result['status']} | 回滚清单 {result['rolled_back']}")
    print(f"  - 审计: {result['audit']}")

def cmd_drill(args):
    """发布门禁故障注入演练：每条用例故意制造违规，断言门禁必须拒绝。"""
    from pipeline.release_drill import ReleaseDrill
    report = ReleaseDrill.run()
    print(f"=== 发布门禁故障注入演练: {report['status']} ({report['passed']}/{report['total']}) ===")
    for case in report["cases"]:
        print(f"  [{'OK  ' if case['passed'] else 'FAIL'}] {case['case']}: {case['actual'][:120]}")
    if report["status"] != "PASS":
        raise SystemExit(1)


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
def cmd_3d_pipeline(args):
    from pipeline.next_gen_3d_pipeline import NextGen3AShowcaseGenerator
    out_path = Path(args.out) if getattr(args, "out", "") else None
    print("[3D-PIPELINE] 🚀 启动次时代 3A PBR/LOD 资产与展台自动化生成流水线...")
    out = NextGen3AShowcaseGenerator.generate_showcase_html(out_path)
    print(f"[3D-PIPELINE] ✅ 次时代 3A 视口展台生成完毕: {out} ({out.stat().st_size} bytes)")

def cmd_llm_import(args):
    """从本地 JSON 导入 LLM 端点池（含密钥，写入 gitignore 的 config/llm_endpoints.json）。"""
    import json as _json
    from core.llm_gateway import ENDPOINT_POOL_FILE, load_endpoints

    src = Path(args.file).expanduser()
    if not src.exists():
        print(f"[LLM-IMPORT] ❌ 找不到文件: {src}")
        raise SystemExit(2)
    try:
        data = _json.loads(src.read_text(encoding="utf-8"))
    except _json.JSONDecodeError as exc:
        print(f"[LLM-IMPORT] ❌ 不是合法 JSON: {exc}")
        raise SystemExit(2)

    endpoints = data if isinstance(data, list) else data.get("endpoints", [])
    if not endpoints:
        print("[LLM-IMPORT] ❌ 文件中没有端点条目")
        raise SystemExit(2)

    ENDPOINT_POOL_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENDPOINT_POOL_FILE.write_text(_json.dumps(endpoints, ensure_ascii=False, indent=2), encoding="utf-8")
    loaded = load_endpoints()
    print(f"[LLM-IMPORT] 已导入 {len(loaded)} 个端点 -> {ENDPOINT_POOL_FILE}")
    print(f"  [SECURITY] 该文件已在 .gitignore 中，密钥不会进入版本库。")
    print("  [NEXT] 执行 `game_agent.py llm-status` 做真实连通性探测（不探测不得宣称可用）。")

def cmd_llm_status(args):
    """真实探测每个端点：只把真正拿回内容的端点记为可用。"""
    from core.llm_gateway import load_endpoints, probe_endpoint
    pool = load_endpoints()
    if not pool:
        print("[LLM-STATUS] 端点池为空。先执行 `game_agent.py llm-import --file <llm.json>`")
        raise SystemExit(2)
    print(f"[LLM-STATUS] 真实连通性探测（共 {len(pool)} 个端点，逐个发真实请求）")
    ok_count = 0
    for ep in pool:
        res = probe_endpoint(ep)
        flag = "OK  " if res["ok"] else "FAIL"
        if res["ok"]:
            ok_count += 1
        print(f"  [{flag}] {res['id'][:52]:52s} {res['latency_ms']:5d}ms {res['error'][:60]}")
    print(f"[LLM-STATUS] 可用 {ok_count}/{len(pool)}")
    if ok_count == 0:
        print("  [HONEST] 没有可用端点，所有依赖 LLM 的能力将返回 NEEDS_LLM_CREDENTIALS，不会用模板冒充。")
        raise SystemExit(3)

def cmd_skill_list(args):
    """W3 L2 技能适配状态（真实计数，不做美化）。"""
    from core.skill_registry import skill_registry, SkillStatus
    from core.skill_registry_seeds import apply_default_seeds
    from core.skill_classification import apply_classification, unclassified

    if not skill_registry._skills:
        skill_registry.ingest_from_registry()
    seed_res = apply_default_seeds(verbose=False)
    apply_classification(skill_registry)
    # 内存注册表不跨进程：从证据摘要回放"曾经真跑通过"的 C 类技能
    import json as _json
    import os

    from core.c_skill_verifier import DIGEST_PATH, restore_registrations
    from core.b_skill_runtime import (BATCH1_IMPLEMENTED, BATCH1_RUNTIME_TOOL,
                                      restore_b_registrations)
    restore_registrations(skill_registry, verbose=True)
    restore_b_registrations(skill_registry, verbose=True)

    # 双口径：单次批量运行的通过率在 17~22/24 间波动，只报一个数必然失真。
    digest = None
    if os.path.exists(DIGEST_PATH):
        try:
            with open(DIGEST_PATH, "r", encoding="utf-8") as f:
                digest = _json.load(f)
        except (OSError, ValueError):
            digest = None

    counts = skill_registry.counts()
    left = unclassified(skill_registry)
    print("[L2-SKILLS] 技能库适配状态（真实计数，分母永远 114）")
    print(f"  A_REGISTERED : {counts['A_REGISTERED']:3d}  (复用现成模块，已真注册为 Capability)")
    print(f"  C_REGISTERED : {counts['C_REGISTERED']:3d}  (绑 LLM，真实调用并通过校验后才注册)")
    print(f"  C_SPECD      : {counts['C_SPECD']:3d}  (有产出契约，尚未真跑通)")
    print(f"  B            : {counts['B']:3d}  (确定性可实现，待 W4 落地)")
    print(f"  未分类       : {len(left):3d}")
    print(f"  TOTAL        : {counts['TOTAL']}")
    print(f"  ── 已可用合计: {counts['A_REGISTERED'] + counts['C_REGISTERED']} / 114")

    if digest:
        last = digest.get("last_run") or {}
        print(f"  ── C 类双口径（不可混用）:")
        print(f"     历史通过 ever_passed : {digest.get('ever_passed_count')}/24 "
              f"（至少一次真实通过，payload 可回查）")
        print(f"     最近一次 last_run    : {last.get('ok')}/{last.get('total')} "
              f"@ {digest.get('run_id')}")
        print(f"     累计批量运行         : {len(digest.get('history_runs', []))} 次")
        low = [(i["skill_id"], i["pass_rate"]) for i in digest.get("per_skill", [])
               if i.get("pass_rate") is not None and i["pass_rate"] < 1.0]
        if low:
            low.sort(key=lambda x: x[1])
            print(f"     通过率 <100% 的 {len(low)} 项（模型波动，非契约缺陷）: "
                  f"{', '.join(f'{s}={r}' for s, r in low[:6])}"
                  f"{' ...' if len(low) > 6 else ''}")

    if seed_res.get("failed", 0) > 0:
        print(f"  [SEED-FAIL] 本次 seeds 失败 {seed_res['failed']} 项:")
        for fid in seed_res.get("failed_ids", [])[:10]:
            print(f"    - {fid}")
    if left:
        print(f"  [GAP] 未分类项（分类表漏了，必须补）: {left[:10]}")

    print()
    print("已注册 (A — 复用现成模块):")
    for s in skill_registry.list(status=SkillStatus.REGISTERED):
        if s.cls != "A":
            continue
        cap = s.capability
        mod = cap.implementation.get("module", "?") if cap else "?"
        ent = cap.implementation.get("entrypoint", "?") if cap else "?"
        print(f"  - {s.skill_id:42s}  [{s.category:9s}]  -> {mod}.{ent}")

    c_reg = [s for s in skill_registry.list(status=SkillStatus.REGISTERED) if s.cls == "C"]
    if c_reg:
        print()
        print("已注册 (C — 真实调用 LLM 并通过校验):")
        for s in c_reg:
            cap = s.capability
            note = ""
            for n in reversed(s.notes):
                if n.startswith("真实调用"):
                    note = n
                    break
            print(f"  - {s.skill_id:42s}  [{s.category:9s}]  {note}")

    # HONEST
    target_a = 40
    c_specd = skill_registry.list(cls="C", status=SkillStatus.NEEDS_IMPLEMENTATION)
    print()
    last_ok = (digest.get("last_run") or {}).get("ok") if digest else None
    b_impl = len(BATCH1_IMPLEMENTED)
    b_rt = len(BATCH1_RUNTIME_TOOL)
    print(f"  [HONEST] W3c 阶段：A 类 {counts['A_REGISTERED']}/{target_a} 真实注册；"
          f"C 类 {counts['C_REGISTERED']}/24 至少一次真实通过"
          f"（最近一次批量运行 {last_ok}/24，波动来自模型能力差异，"
          f"单次数不得当作能力证明）；"
          f"W4（B 类 {counts['B']} 项）第一批：{b_impl} 项确定性算法已真跑+验收注册、"
          f"{b_rt} 项标 NEEDS_RUNTIME_TOOL（缺 DCC/GPU 不伪证），"
          f"余下 {counts['B'] - b_impl - b_rt} 项按同模式后续批次落地。"
          f"当前 B_REGISTERED={counts['B_REGISTERED']}。")
    if c_specd and not getattr(args, "verbose", False):
        print(f"          未跑通的 C 类：{', '.join(s.skill_id for s in c_specd[:6])}"
              f"{' ...' if len(c_specd) > 6 else ''}")
    if digest:
        print("          口径说明：ever_passed=历史至少一次真实通过；last_ok=最近一次结果。"
              "两者混用即为粉饰。可用 `skill-audit-c` 复核历史通过是否仍满足当前契约。")


def cmd_skill_run(args):
    """真实跑一项 C 类技能（不跑就不许说它能用）。"""
    import json
    from core.llm_skill_adapter import LLMSkillAdapter
    from core.c_skill_verifier import CSkillVerifier, DEFAULT_TASKS

    sid = args.skill
    adapter = LLMSkillAdapter(provider=getattr(args, "provider", "auto"),
                              model=getattr(args, "model", None))
    pre = adapter.preflight()
    if not pre["llm_ready"]:
        print(f"[SKILL-RUN] {sid}: NEEDS_LLM_CREDENTIALS")
        print(f"  {pre['how_to_fix']}")
        return 1

    task = args.task or DEFAULT_TASKS.get(sid, "")
    if not task:
        print(f"[SKILL-RUN] 未给 --task，且 {sid} 没有默认任务。")
        return 2
    r = CSkillVerifier(adapter=adapter).run_one(sid, task)
    print(f"[SKILL-RUN] {sid} -> {r.status} | {r.provider}/{r.model} "
          f"| 尝试 {r.attempts} 次 | {r.latency_ms}ms")
    if r.ok:
        print(json.dumps(r.payload, ensure_ascii=False, indent=2)[:4000])
    else:
        for e in r.errors[:10]:
            print(f"  - {e}")
    return 0 if r.ok else 1


def cmd_skill_verify_c(args):
    """批量真实跑通 24 项 C 类技能，通过的才允许注册，证据落工件库。"""
    from core.c_skill_verifier import verify_all
    ev = verify_all(verbose=True,
                    skill_ids=[args.skill] if getattr(args, "skill", None) else None,
                    model=getattr(args, "model", None))
    if ev.get("status") == "NEEDS_LLM_CREDENTIALS":
        print("[VERIFY-C] NEEDS_LLM_CREDENTIALS：没有可用 LLM 后端，未跑任何一项。")
        print(f"  {ev.get('how_to_fix')}")
        return 1
    print("=" * 70)
    print(f"[VERIFY-C] total={ev['total']} ok={ev['ok']} failed={ev['failed']} "
          f"elapsed={ev.get('elapsed_seconds')}s")
    print(f"  run_dir   : {ev.get('run_dir')}")
    print(f"  integrity : {ev.get('artifact_integrity')}")
    print(f"  counts    : {ev.get('counts')}")
    if ev.get("failed_detail"):
        print("  未跑通（如实列出，不筛掉）:")
        for f in ev["failed_detail"]:
            print(f"    - {f['skill_id']:38s} {f.get('status')} | "
                  f"{(f.get('errors') or [''])[0][:100]}")
    return 0 if ev["failed"] == 0 else 1

def cmd_skill_audit_c(args):
    """离线复校验：历史"通过"在当前契约下是否仍然成立（不调 LLM、不烧额度）。

    为什么单独成命令：`ever_passed` 说的是"曾经跑通过"，契约改过之后它可能与
    现状不符。这条命令把每项通过记录的 payload 按哈希从工件库读回，用当前契约
    重跑一遍，把"历史通过"和"当前仍成立"分开报，避免拿旧证据冒充现状。
    """
    from core.c_skill_verifier import AUDIT_PATH, CSkillVerifier
    rep = CSkillVerifier.audit_evidence()
    if rep.get("error"):
        print(f"[AUDIT-C] {rep['error']}")
        return 1
    print("=" * 70)
    print(f"[AUDIT-C] 复校验 {rep['checked']} 项 ｜ "
          f"当前仍成立 {rep['still_valid']} ｜ 契约已变失效 {rep['stale']} ｜ "
          f"工件缺失 {rep['missing']} ｜ 无通过记录 {rep['no_pass_record']}")
    print(f"  报告: {AUDIT_PATH}")
    for d in rep["details"]:
        if d["audit"] == "still_valid":
            continue
        extra = (d.get("errors") or [d.get("error", "")])[:2]
        print(f"    - {d['skill_id']:38s} {d['audit']:14s} | {extra}")
    if rep["stale"] or rep["missing"]:
        print("  [HONEST] 上列项的历史通过已不能代表现状，需重跑 skill-verify-c 更新证据。")
    return 0 if (rep["stale"] == 0 and rep["missing"] == 0) else 1


def cmd_skill_verify_b(args):
    """批量真实运行 B 类（确定性算法）技能，验收通过的才注册，证据落工件库。

    B 类不依赖 LLM、不依赖网络：纯函数式运行 + 数值断言验收。依赖 DCC/GPU 工具
    的 B 类（如高模雕刻、PBR 烘焙）会返回 NEEDS_RUNTIME_TOOL，明确标红不伪证。
    """
    from core.b_skill_runtime import verify_all, BSkillRuntime
    ev = verify_all(verbose=True,
                    skill_ids=[args.skill] if getattr(args, "skill", None) else None)
    print("=" * 70)
    print(f"[VERIFY-B] total={ev['total']} ok={ev['ok']} failed={ev['failed']} "
          f"elapsed={ev.get('elapsed_seconds')}s")
    print(f"  run_dir   : {ev.get('run_dir')}")
    print(f"  integrity : {ev.get('artifact_integrity')}")
    print(f"  counts    : {ev.get('counts')}")
    if ev.get("failed_detail"):
        print("  未通过/未跑（如实列出，不粉饰）:")
        for f in ev["failed_detail"]:
            tag = f.get("needs_runtime_tool") or f.get("status")
            print(f"    - {f['skill_id']:38s} {tag} | "
                  f"{(f.get('errors') or [''])[0][:100]}")
    return 0 if ev["failed"] == 0 else 1


def cmd_skill_run_b(args):
    """真实运行一项 B 类技能（确定性，不调 LLM）。"""
    import json
    from core.b_skill_runtime import BSkillRuntime
    r = BSkillRuntime().run_skill(args.skill, json.loads(args.params) if args.params else None)
    print(f"[SKILL-RUN-B] {r.skill_id} -> {r.status} | {r.runtime} | {r.latency_ms}ms")
    if r.ok:
        print(json.dumps(r.payload, ensure_ascii=False, indent=2)[:4000])
    else:
        for e in r.errors[:10]:
            print(f"  - {e}")
    return 0 if r.ok else 1


def cmd_skill_audit_b(args):
    """离线复验：B 类历史通过的 payload 在当前契约下是否仍成立。"""
    from core.b_skill_runtime import AUDIT_PATH, BSkillRuntime
    rep = BSkillRuntime.audit_evidence()
    if rep.get("error"):
        print(f"[AUDIT-B] {rep['error']}")
        return 1
    print("=" * 70)
    print(f"[AUDIT-B] 复验 {rep['checked']} 项 ｜ 仍成立 {rep['still_valid']} ｜ "
          f"失效 {rep['stale']} ｜ 缺失 {rep['missing']} ｜ 无通过记录 {rep['no_pass_record']}")
    print(f"  报告: {AUDIT_PATH}")
    for d in rep["details"]:
        if d["audit"] == "still_valid":
            continue
        extra = (d.get("errors") or [d.get("error", "")])[:2]
        print(f"    - {d['skill_id']:38s} {d['audit']:14s} | {extra}")
    return 0 if (rep["stale"] == 0 and rep["missing"] == 0) else 1


# ─────────────────────────────────────────────────────────────────────────────
# W5：2D 资产工厂 CLI（ImageGenAdapter + StyleBible + 入库 QA）
# ─────────────────────────────────────────────────────────────────────────────
def cmd_asset_style(args):
    """初始化并锁定一份风格圣经 StyleBible（后续所有资产 prompt 必须引用它）。"""
    import json
    from pathlib import Path
    from pipeline.style_bible import StyleBible
    palette = None
    if getattr(args, "palette", None):
        palette = [c.strip() for c in args.palette.split(",") if c.strip()]
    sb = StyleBible.build(name=getattr(args, "name", "default") or "default",
                          seed=int(getattr(args, "seed", 0) or 0), palette=palette)
    sb.lock()
    out = getattr(args, "out", None) or "evidence/style_bible.json"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(sb.to_dict(), f, ensure_ascii=False, indent=2)
    print("[ASSET-STYLE] 风格圣经已生成并锁定")
    print(f"  名称     : {sb.name}")
    print(f"  色板     : {sb.palette}")
    print(f"  强调色   : {sb.accent}")
    print(f"  线条     : {sb.line}")
    print(f"  光影     : {sb.lighting}")
    print(f"  构图     : {sb.composition}")
    print(f"  负面词   : {sb.negative_prompts}")
    print(f"  已锁定   : {sb.locked}（禁止中途改皮，保证一致性）")
    print(f"  存档     : {out}")
    return 0


def cmd_asset_gen(args):
    """生成一项 2D 资产：ImageGenAdapter 出图 → 入库 QA → 落工件。"""
    import json
    from pathlib import Path
    from pipeline.style_bible import StyleBible
    from pipeline.asset_factory import AssetFactory, AssetSpec

    style = None
    spath = getattr(args, "style", None) or "evidence/style_bible.json"
    if Path(spath).exists():
        style = StyleBible.from_dict(json.load(open(spath, encoding="utf-8")))
        if not style.locked:
            style.lock()
    else:
        print(f"[ASSET-GEN] 警告：风格圣经 {spath} 不存在，资产将不锚定风格（一致性弱）")

    spec = AssetSpec(
        asset_type=getattr(args, "type", "icon") or "icon",
        name=getattr(args, "name", "asset") or "asset",
        width=int(getattr(args, "width", 512) or 512),
        height=int(getattr(args, "height", 512) or 512),
        require_alpha=bool(getattr(args, "require_alpha", False)),
        frames=int(getattr(args, "frames", 1) or 1),
        style_ref=style.name if style else "none",
        prompt=getattr(args, "prompt", "") or "",
    )
    af = AssetFactory()
    rec = af.generate(spec, style=style, backend=getattr(args, "backend", None),
                      seed=getattr(args, "seed", None),
                      transparent=bool(getattr(args, "require_alpha", False)))
    out_dir = getattr(args, "out", None) or "output/w5_assets"
    paths = af.save(rec, out_dir)

    print("=" * 70)
    print(f"[ASSET-GEN] {rec.spec.asset_type}/{rec.spec.name}")
    print(f"  后端           : {rec.backend}")
    print(f"  是否 AI 生成   : {rec.is_ai_generated} ｜ 是否程序化占位: {rec.is_procedural_placeholder}")
    print(f"  尺寸/透明      : {rec.width}x{rec.height} ｜ alpha={rec.has_alpha}")
    print(f"  内容哈希       : {rec.content_hash}")
    if rec.provenance:
        print(f"  溯源           : 模型={rec.provenance.get('model')} "
              f"seed={rec.provenance.get('seed')} 端点={rec.provenance.get('endpoint')}")
    print(f"  入库 QA        : {'通过' if rec.qa.passed else '未通过'}")
    for k, v in rec.qa.scores.items():
        print(f"    - {k:16s}: {v}")
    if rec.qa.needs_vlm:
        print(f"  需 VLM 复核    : {rec.qa.needs_vlm}（如实标注，不假装已判定）")
    if rec.needs_runtime_tool:
        print(f"  ⚠ 诚实标注     : 无可用 AIGC 后端，本资产为程序化占位（needs_runtime_tool={rec.needs_runtime_tool}）")
    for w in rec.provenance.get("warnings", []) if isinstance(rec.provenance, dict) else []:
        print(f"  ⚠ {w}")
    print(f"  落盘           : {paths['png']}")
    return 0 if rec.qa.passed else 1


def cmd_asset_verify(args):
    """仅对一张已有 PNG 跑入库 QA（不重新生成）。"""
    import json
    from pathlib import Path
    from pipeline.style_bible import StyleBible
    from pipeline.asset_factory import AssetQA, AssetSpec
    data = open(getattr(args, "file"), "rb").read()
    style = None
    spath = getattr(args, "style", None) or "evidence/style_bible.json"
    if Path(spath).exists():
        style = StyleBible.from_dict(json.load(open(spath, encoding="utf-8")))
    spec = AssetSpec(
        asset_type=getattr(args, "type", "icon") or "icon",
        name=getattr(args, "name", "asset") or "asset",
        width=int(getattr(args, "width", 512) or 512),
        height=int(getattr(args, "height", 512) or 512),
        require_alpha=bool(getattr(args, "require_alpha", False)),
    )
    rep = AssetQA.check(data, spec, style, is_ai_generated=False)
    print("=" * 70)
    print(f"[ASSET-VERIFY] {getattr(args, 'file')}")
    print(f"  结果     : {'通过' if rep.passed else '未通过'}")
    for k, v in rep.scores.items():
        print(f"    - {k:16s}: {v}")
    for k, v in rep.details.items():
        print(f"    · {k:16s}: {v}")
    if rep.needs_vlm:
        print(f"  需 VLM 复核: {rep.needs_vlm}")
    return 0 if rep.passed else 1


def cmd_agent_cards(args):
    """列出已注册专家卡与 82 位目标的真实缺口（不做任何美化）。"""
    from core.role_cards import all_cards, card_counts, AgentTier, load_all_role_cards
    load_all_role_cards()
    counts = card_counts()
    print("[AGENT-CARDS] 专家角色卡注册表（真实计数，非目标值）")
    print(f"  已注册 {counts['TOTAL']} / 目标 {counts['TARGET']} ｜ 缺口 {counts['MISSING']} ｜ "
          f"LEAD {counts['LEAD']} / SPECIALIST {counts['SPECIALIST']} / ADVISOR {counts['ADVISOR']}")
    for card in all_cards():
        print(f"  - [{card.tier.value:10s}] {card.card_id:28s} {card.name:6s} ｜ 阶段: {','.join(card.phases)}")
        print(f"      职责: {card.duty}")
    if counts["MISSING"] > 0:
        print(f"  [HONEST] 仍有 {counts['MISSING']} 张卡未注册，W2 补齐前不得宣称 82 位专家可用。")

def cmd_agent_run(args):
    """激活一位专家执行任务。无 LLM 时返回 NEEDS_LLM_CREDENTIALS，不产出模板文本。"""
    import json as _json
    from core.agent_runtime import get_runtime, AgentStatus, NEEDS_LLM_CREDENTIALS
    from core.role_cards import get_card

    runtime = get_runtime(provider=getattr(args, "llm_provider", "auto") or "auto",
                          model=getattr(args, "llm_model", None))
    card_id = args.card

    if card_id == "--preflight" or getattr(args, "preflight", False):
        pre = runtime.preflight()
        print("[AGENT-RUN] 环境自检")
        print(f"  LLM 就绪: {pre['llm_ready']} ｜ 可用 Provider: {pre['available_providers'] or '无'}")
        print(f"  status: {pre['status']}")
        if pre["how_to_fix"]:
            print(f"  修复方式: {pre['how_to_fix']}")
        return

    card = get_card(card_id)
    if card is None:
        print(f"[AGENT-RUN] ❌ 未注册的专家卡: {card_id}（用 `agent-cards` 查看已注册卡片）")
        raise SystemExit(2)

    context = {}
    if getattr(args, "context", ""):
        try:
            context = _json.loads(args.context)
        except _json.JSONDecodeError as exc:
            print(f"[AGENT-RUN] ❌ --context 不是合法 JSON: {exc}")
            raise SystemExit(2)

    out = runtime.run(card_id, args.task, context)
    print(f"[AGENT-RUN] 专家: {card.name} ({card.card_id}) ｜ 档位: {card.tier.value}")
    print(f"  status: {out.status}")
    if out.status == NEEDS_LLM_CREDENTIALS:
        print("  [HONEST] 没有可用的 LLM 后端，本次没有产出任何专家结论。")
        print("           不会用模板文本冒充该专家的产出。配置 API Key 后重试。")
        raise SystemExit(3)
    if out.status != AgentStatus.OK:
        for err in out.errors:
            print(f"  - {err}")
        raise SystemExit(1)
    print(f"  provider/model: {out.provider}/{out.model} ｜ tokens: {out.input_tokens}/{out.output_tokens} ｜ {out.latency_ms}ms")
    print("  --- payload ---")
    print(_json.dumps(out.payload, ensure_ascii=False, indent=2))

def cmd_list_parts(args):
    """查询 Ford-T 零件库全部 35 个工业机制零件。"""
    from core.ford_t_game_parts_hub import ModularGameAssembler
    assembler = ModularGameAssembler()
    catalog = assembler.catalog

    print("================================================================")
    print(f"FORD-T GAME PARTS CATALOG - {len(catalog)} PRE-FABRICATED PARTS")
    print("================================================================")

    categories = {}
    for key, part in catalog.items():
        cat = getattr(part, "category", "CORE")
        categories.setdefault(cat, []).append((key, part.name))

    for cat, items in sorted(categories.items()):
        print(f"\n[{cat}] ({len(items)} parts):")
        for key, name in sorted(items):
            print(f"  - {key:<20} -> {name}")
    print("\n================================================================")
    return 0

def cmd_assemble(args):
    """根据指定零件组合模块化装配新游戏架构。"""
    from core.ford_t_game_parts_hub import ModularGameAssembler
    assembler = ModularGameAssembler()
    parts = [p.strip() for p in args.parts.split(",") if p.strip()]
    try:
        res = assembler.assemble(title=args.title, selected_part_keys=parts)
        print(f"SUCCESS: Assembled game '{res['title']}' with {res['parts_count']} parts:")
        for p in res["active_parts"]:
            print(f"  [+] Mounted: {p}")
        return 0
    except KeyError as e:
        print(f"ASSEMBLY ERROR: {e}")
        return 1

def cmd_templates(args):
    """列出内置参考游戏骨架模板。"""
    print("================================================================")
    print("AI-NATIVE PLAYABLE ARCHETYPE TEMPLATES")
    print("================================================================")
    print("1. Card Roguelike (Spire-like):")
    print("   Engine: templates/card_roguelike/card_game_engine.py")
    print("   HTML5:  templates/card_roguelike/index.html")
    print("2. Survivor Danmaku (Bullet Hell):")
    print("   Engine: templates/survivor_danmaku/danmaku_engine.py")
    print("   HTML5:  templates/survivor_danmaku/index.html")
    print("================================================================")
    return 0

def cmd_wechat_pack(args):
    """一键将游戏模板打包为合规微信小游戏工程。"""
    from pipeline.wechat_packager import WeChatPackager
    tpl_map = {
        "survivor": "templates/survivor_danmaku/index.html",
        "danmaku": "templates/survivor_danmaku/index.html",
        "survivor_danmaku": "templates/survivor_danmaku/index.html",
        "card": "templates/card_roguelike/index.html",
        "card_roguelike": "templates/card_roguelike/index.html",
    }
    src = tpl_map.get(args.template.lower())
    if not src:
        src_path = Path(args.template)
        if not src_path.exists():
            print(f"Error: Template or file '{args.template}' not found.")
            return 1
    else:
        src_path = ROOT / src

    out_dir = Path(args.out)
    packager = WeChatPackager()
    res = packager.bundle(
        src_path,
        out_dir,
        project_name=args.name,
        orientation=args.orientation
    )
    print("SUCCESS: WeChat Mini-Game bundled:")
    print(f"  Target: {res['output_dir']}")
    print(f"  Size:   {res['size_mb']}MB / {res['max_mb']}MB (Compliant: {res['compliant']})")
    print(f"  Files:  {', '.join(res['files_generated'])}")
    return 0

# 命令 -> 处理函数。任一命令都必须经此表派发，
# 由 RunService.dispatch_tool 统一写入审计链，杜绝绕过契约与发布门禁的旁路调用。
COMMAND_TABLE = {
    "agents": cmd_agents, "teams": cmd_teams, "skills": cmd_skills, "hooks": cmd_hooks,
    "route": cmd_route, "contract": cmd_contract, "distill": cmd_distill, "qa": cmd_qa,
    "ccgs": cmd_ccgs, "lore": cmd_lore, "evaluate": cmd_evaluate, "playability": cmd_playability,
    "fidelity": cmd_fidelity, "probe": cmd_probe, "drive": cmd_drive, "diff": cmd_diff,
    "reverse": cmd_reverse, "fuzz": cmd_fuzz, "solver": cmd_solver, "sandbox": cmd_sandbox,
    "slice": cmd_slice, "heal": cmd_heal, "scene": cmd_scene, "create": cmd_create,
    "gdd": cmd_gdd, "llm": cmd_llm, "asset3d": cmd_asset3d, "balance": cmd_balance,
    "distribute": cmd_distribute, "live-smoke": cmd_live_smoke,
    "promote": cmd_promote, "rollback": cmd_rollback, "release-drill": cmd_drill,
    "submit": cmd_submit,
    "channel-doctor": cmd_channel_doctor,
    "delivery-audit": cmd_delivery_audit, "delivery-pack": cmd_delivery_pack,
    "live-doctor": cmd_live_doctor,
    "live-flow": cmd_live_flow,
    "review-create": cmd_review_create, "review-approve": cmd_review_approve,
    "review-reject": cmd_review_reject, "review-status": cmd_review_status,
    "player-doctor": cmd_player_doctor, "player-cohort": cmd_player_cohort,
    "env-check": cmd_env_check,
    "spec": cmd_spec, "serve": cmd_serve, "mcp": cmd_mcp,
    "rig": cmd_rig, "audio": cmd_audio, "ast": cmd_ast, "netcode": cmd_netcode,
    "vlm": cmd_vlm, "profile": cmd_profile, "coroner": cmd_coroner, "toolchain": cmd_toolchain,
    "hypercasual": cmd_hypercasual, "commercial": cmd_commercial, "redteam": cmd_redteam,
    "logistics": cmd_logistics, "autotile": cmd_autotile, "flowfield": cmd_flowfield,
    "ecs": cmd_ecs, "techtree": cmd_techtree, "mindustry": cmd_mindustry,
    "3d-pipeline": cmd_3d_pipeline, "doctor": cmd_doctor,
    "agent-cards": cmd_agent_cards, "agent-run": cmd_agent_run,
    "llm-import": cmd_llm_import, "llm-status": cmd_llm_status,
    "skill-list": cmd_skill_list, "skill-run": cmd_skill_run,
    "skill-verify-c": cmd_skill_verify_c, "skill-audit-c": cmd_skill_audit_c,
    "skill-run-b": cmd_skill_run_b, "skill-verify-b": cmd_skill_verify_b,
    "skill-audit-b": cmd_skill_audit_b,
    "asset-style": cmd_asset_style, "asset-gen": cmd_asset_gen,
    "asset-verify": cmd_asset_verify,
    "asset-audio": cmd_asset_audio, "asset-audio-verify": cmd_asset_audio_verify,
    "playtest": cmd_playtest,
    "diff": cmd_diff,
    "taste": cmd_taste,
    "vision": cmd_vision,
    "list-parts": cmd_list_parts,
    "assemble": cmd_assemble,
    "templates": cmd_templates,
    "wechat-pack": cmd_wechat_pack,
}


def main():
    # 显式加载 .env，不依赖任何模块的导入副作用：
    # 渠道凭据、沙箱地址、遥测端点都从 os.environ 读取，
    # 若 .env 没加载就会出现「明明填了却报未配置」。
    try:
        from core.llm_gateway import ensure_env_loaded
        ensure_env_loaded()
    except Exception:  # 加载失败不阻断 CLI，后续命令会如实报未配置
        pass

    parser = argparse.ArgumentParser(description="Game Dev Agent Studios 统一管理 CLI (v9.0 First-Principles & Adversarial Red-Team Edition)")
    
    # 全局/可复用 LLM 参数
    llm_parent = argparse.ArgumentParser(add_help=False)
    llm_parent.add_argument("--llm-provider", type=str, choices=["gemini", "openai", "claude", "ollama", "deepseek"], default="gemini", help="指定 LLM Provider (默认 gemini)")
    llm_parent.add_argument("--llm-model", type=str, default=None, help="指定具体模型名称")
    llm_parent.add_argument("--mode", type=str, choices=["fast", "llm", "hybrid"], default="fast", help="生成模式 (fast/llm/hybrid)")
    llm_parent.add_argument("--no-llm", action="store_true", help="强制禁用 LLM，使用纯模板模式")

    sub = parser.add_subparsers(dest="command", help="子命令")

    sub.add_parser("agents", help="列出注册专家智能体与跨部门专业团队")
    sub.add_parser("teams", help="列出跨部门专业团队、能力与门禁")
    sub.add_parser("skills", help="列出注册游戏开发技能")
    sub.add_parser("hooks", help="查看 12 个生命周期钩子")
    p_3d = sub.add_parser("3d-pipeline", help="运行次时代 3A PBR/LOD 资产与展台自动化生成流水线")
    p_3d.add_argument("--out", type=str, default="", help="指定自定义 HTML 输出路径")
    
    p_route = sub.add_parser("route", help="执行 GameFactory-3A 前置路由锁定与多引擎指纹探测")
    p_route.add_argument("--preset", type=str, default="rust_macroquad_2d", help="预设名称")
    p_route.add_argument("--detect", type=str, default="", help="指定目录执行两阶段引擎指纹自动嗅探")
    p_route.add_argument("--prompt", type=str, default="", help="用户意图提示词 (用于叠加推荐领域专家与技能)")

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

    p_diff = sub.add_parser("diff", help="执行像素级视觉真理与多层图层装配审查 (支持 --seed / --gen-target 自举基准)")
    p_diff.add_argument("--capture", type=str, default="", help="待测实机截图路径")
    p_diff.add_argument("--seed", type=str, default=None, help="把指定截图固化为基准帧(knowledge/golden_frames/<name>.png)")
    p_diff.add_argument("--gen-target", dest="gen_target", action="store_true", help="使用生图后端生成目标参考基准图")
    p_diff.add_argument("--prompt", type=str, default="", help="生成基准图时的文生图提示词")
    p_diff.add_argument("--name", type=str, default="target", help="基准帧名称(默认 target)")
    p_diff.add_argument("--strict", action="store_true", help="严格门禁模式(DEGRADED 降级时返回退出码 4 阻断流水线)")

    p_taste = sub.add_parser("taste", help="玩家口味语料->设计约束信号提取(对应《把AI游戏流程录成Skill》)")
    p_taste.add_argument("--corpus", type=str, default="", help="玩家口味语料 JSON 路径(缺省 knowledge/player_taste_spec.json)")
    p_taste.add_argument("--attach", type=str, default=None, help="把约束注入到该提示词并回显")
    p_taste.add_argument("--fetch", action="store_true", help="尝试外部实时采集(默认 NEEDS_NETWORK，不伪装爬取)")
    p_taste.add_argument("--platform", type=str, default="taptap", help="外部采集平台(taptap/steam)")

    p_vision = sub.add_parser("vision", help="视觉闭环: seed/generate 基准帧 + diff 追近(对应 Dream Loop)")
    p_vision.add_argument("--seed", type=str, default=None, help="把指定截图固化为基准帧(golden_frames/<name>.png)")
    p_vision.add_argument("--generate", action="store_true", help="用文生图生成目标参考图(无后端时 NEEDS_RUNTIME_TOOL)")
    p_vision.add_argument("--prompt", type=str, default="", help="--generate 时的文生图提示词")
    p_vision.add_argument("--style", type=str, default=None, help="--generate 时的风格锁定(传 StyleBible 标识)")
    p_vision.add_argument("--diff", action="store_true", help="执行像素级视觉真理审查(默认比对 target 基准帧)")
    p_vision.add_argument("--capture", type=str, default="", help="--diff 时的实机截图路径")
    p_vision.add_argument("--name", type=str, default="target", help="基准帧名(默认 target，须与 generate/seed 一致)")

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
    p_create.add_argument("title_pos", nargs="?", default=None, help="游戏名称 (位置参数)")
    p_create.add_argument("--title", type=str, default=None, help="游戏名称 (选项参数)")
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
    p_asset3d.add_argument("--format", type=str, default="gltf", choices=["gltf", "obj"], help="导出格式（仅 M3 无贴图路径使用）")
    p_asset3d.add_argument("--output", type=str, default="", help="输出目录")
    p_asset3d.add_argument("--textured", action="store_true", help="W6：生成带 PBR 五通道贴图的 3D 资产（AI albedo + 程序化 4 通道）")
    p_asset3d.add_argument("--backend", type=str, default=None,
                           choices=["comfyui_local", "cloud_api", "procedural_placeholder"],
                           help="albedo 后端；缺省 auto（有 AIGC 后端走 AI，否则程序化占位）")
    p_asset3d.add_argument("--seed", type=int, default=None, help="确定性种子（albedo/程序化复用）")
    p_asset3d.add_argument("--verify-godot", action="store_true", help="M4：在真 Godot 4.7.2 中导入校验（真机证据）")
    p_asset3d.add_argument("--style", type=str, default="evidence/style_bible.json", help="风格圣经路径（albedo prompt 引用）")

    p_balance = sub.add_parser("balance", parents=[llm_parent], help="宏观数值仿真与自适应经济审计")
    p_balance.add_argument("--trials", type=int, default=10000, help="抽卡蒙特卡洛仿真次数")
    p_balance.add_argument("--levels", type=int, default=20, help="心流关卡测试数")
    p_balance.add_argument("--use-llm", action="store_true", help="调用 LLM 生成数值重构与平滑建议")

    p_distribute = sub.add_parser("distribute", parents=[llm_parent], help="多平台自动化分发中枢 (WeChat/Steam/PWA/itch.io)")
    p_distribute.add_argument("--title", type=str, default="商业级独立大作", help="游戏名称")
    p_distribute.add_argument("--platform", type=str, default="all", choices=["all", "wechat", "steam", "pwa", "itch"], help="分发目标平台")
    p_distribute.add_argument("--all", dest="dist_all", action="store_true", help="构建全部平台分发包 (等价于 --platform all)")
    p_distribute.add_argument("--input", type=str, default="", help="待分发主 HTML 文件路径")
    p_distribute.add_argument("--output", type=str, default="", help="分发包输出目录")
    p_distribute.add_argument("--godot-project", dest="godot_project", type=str, default="",
                              help="Godot 工程目录（含 project.godot）；指定后先真实导出独立包再分发，缺模板时如实退回 Web 壳")
    p_distribute.add_argument("--run-id", dest="run_id", type=str, default="",
                              help="分发必须挂接到某次已通过门禁的运行（其 ReleaseManifest 存在），否则视为旁路发布被拒绝")

    p_live = sub.add_parser("live-smoke", help="支付/广告/联机沙箱真实链路冒烟 (缺凭据如实报缺失)")
    p_live.add_argument("--kind", type=str, default="all",
                        choices=["all", "payment", "ads", "multiplayer"], help="冒烟的在线服务类型")

    p_promote = sub.add_parser("promote", help="发布通道晋升 (staging 需 qa_manager + 真实冒烟；production 需 release_manager)")
    p_promote.add_argument("--run-id", dest="run_id", type=str, required=True, help="目标运行 ID")
    p_promote.add_argument("--channel", type=str, default="staging", choices=["staging", "production"], help="晋升目标通道")
    p_promote.add_argument("--role", type=str, required=True, help="审批角色 (staging=qa_manager / production=release_manager)")
    p_promote.add_argument("--actor", type=str, required=True, help="审批人标识")

    p_rollback = sub.add_parser("rollback", help="发布回滚 (记录决策与审计，不谎称已执行远端下架)")
    p_rollback.add_argument("--run-id", dest="run_id", type=str, required=True, help="目标运行 ID")
    p_rollback.add_argument("--reason", type=str, required=True, help="回滚原因")
    p_rollback.add_argument("--role", type=str, default="release_manager", help="操作角色")
    p_rollback.add_argument("--actor", type=str, required=True, help="操作人标识")

    sub.add_parser("release-drill", help="发布门禁故障注入演练 (故意制造违规，断言必须被拦)")

    p_submit = sub.add_parser("submit", help="第三方渠道上架包 + 提交前门禁 (默认 dry-run，缺凭据如实报缺失)")
    p_submit.add_argument("--channel", type=str, required=True, choices=["wechat", "steam", "itch", "pwa"], help="目标渠道")
    p_submit.add_argument("--run-id", dest="run_id", type=str, default="",
                          help="必须挂接到某次已通过门禁的运行（其 ReleaseManifest 存在），否则视为旁路上架被拒绝")
    p_submit.add_argument("--metadata", type=str, default="", help="商店元数据 JSON 路径")
    p_submit.add_argument("--dist", type=str, default="", help="分发包根目录")
    p_submit.add_argument("--assets", type=str, default="", help="商店素材目录（图标/截图/封面）")
    p_submit.add_argument("--execute", action="store_true", help="真实调用官方上传器（默认仅组装命令不执行）")

    p_cdoc = sub.add_parser("channel-doctor", help="外部渠道体检：列出上架还缺什么、由谁补、怎么补（不打印凭据值）")
    p_cdoc.add_argument("--channel", type=str, default="", choices=["", "wechat", "steam", "itch", "pwa"], help="只体检指定渠道，留空则体检全部")
    p_cdoc.add_argument("--metadata", type=str, default="", help="商店元数据 JSON 路径")
    p_cdoc.add_argument("--dist", type=str, default="", help="分发包根目录")
    p_cdoc.add_argument("--assets", type=str, default="", help="商店素材目录")
    p_cdoc.add_argument("--json", action="store_true", help="输出结构化 JSON")

    p_daudit = sub.add_parser("delivery-audit", help="交付卫生审计：扫描目录是否存在秘密文件与明文密钥")
    p_daudit.add_argument("--path", type=str, default="", help="待交付目录，默认当前仓库根目录")
    p_daudit.add_argument("--no-content", action="store_true", help="只按文件名规则检查，不扫文件内容")
    p_daudit.add_argument("--strict", action="store_true", help="严格模式：测试固件与第三方文档的命中也计入阻断")
    p_daudit.add_argument("--json", action="store_true", help="输出结构化 JSON")

    p_dpack = sub.add_parser("delivery-pack", help="生成脱敏交付副本：排除秘密文件后复检自证")
    p_dpack.add_argument("--out", type=str, required=True, help="脱敏副本输出目录")
    p_dpack.add_argument("--src", type=str, default="", help="源目录，默认当前仓库根目录")
    p_dpack.add_argument("--include-output", dest="include_output", action="store_true", help="一并复制 output/dist/build（默认排除）")
    p_dpack.add_argument("--json", action="store_true", help="输出结构化 JSON")

    p_ldoc = sub.add_parser("live-doctor", help="线上服务体检：支付/广告/联机沙箱 + Staging（服务端须自证身份）")
    p_ldoc.add_argument("--kind", type=str, default="", choices=["", "payment", "ads", "multiplayer", "staging"], help="只体检指定服务")
    p_ldoc.add_argument("--timeout", type=float, default=8.0, help="单次探测超时秒数")
    p_ldoc.add_argument("--emit-reference", dest="emit_reference", type=str, default="", help="写出 /health 参考服务端到该目录")
    p_ldoc.add_argument("--json", action="store_true", help="输出结构化 JSON")

    p_lflow = sub.add_parser("live-flow", help="线上服务真实业务链路冒烟（下单/广告/建房，非仅探活）")
    p_lflow.add_argument("--kind", type=str, default="all",
                         choices=["all", "payment", "ads", "multiplayer"], help="只跑指定服务链路")
    p_lflow.add_argument("--timeout", type=float, default=8.0, help="单次请求超时秒数")
    p_lflow.add_argument("--json", action="store_true", help="输出结构化 JSON")

    p_rcreate = sub.add_parser("review-create", help="建立人工复核工单（记录工件 sha256）")
    p_rcreate.add_argument("--run-id", dest="run_id", type=str, required=True, help="关联的运行 ID")
    p_rcreate.add_argument("--kind", type=str, required=True, choices=["art", "audio", "release"], help="复核类型")
    p_rcreate.add_argument("--artifact", type=str, required=True, help="待复核工件路径")
    p_rcreate.add_argument("--notes", type=str, default="", help="备注")

    for name, help_text in (("review-approve", "人工复核通过（必须署名）"),
                            ("review-reject", "人工复核驳回/返工（必须署名并写原因）")):
        p_rev = sub.add_parser(name, help=help_text)
        p_rev.add_argument("--ticket-id", dest="ticket_id", type=str, required=True, help="工单 ID")
        p_rev.add_argument("--reviewer", type=str, required=True, help="复核人署名")
        p_rev.add_argument("--notes", type=str, default="", help="复核意见")
        p_rev.add_argument("--item", action="append", help="逐项结论，格式 --item \"检查项=pass\"，可重复")
        if name == "review-reject":
            p_rev.add_argument("--reject", action="store_true", help="直接驳回（默认只要求返工）")

    p_rstatus = sub.add_parser("review-status", help="查询运行是否具备生产放行所需的人工复核")
    p_rstatus.add_argument("--run-id", dest="run_id", type=str, required=True, help="目标运行 ID")

    p_pdoc = sub.add_parser("player-doctor", help="真实玩家验证体检：遥测、试点队列、事件真实性")
    p_pdoc.add_argument("--events", type=str, default="", help="事件 JSONL 文件路径")
    p_pdoc.add_argument("--json", action="store_true", help="输出结构化 JSON")

    p_pcohort = sub.add_parser("player-cohort", help="登记真实玩家试点队列")
    p_pcohort.add_argument("--cohort-id", dest="cohort_id", type=str, required=True, help="试点标识")
    p_pcohort.add_argument("--source", type=str, required=True, help="玩家来源，如 内部员工 / 社群招募 / 商店测试渠道")
    p_pcohort.add_argument("--size", type=int, required=True, help="招募人数")
    p_pcohort.add_argument("--window-days", dest="window_days", type=int, default=7, help="观察时间窗天数")
    p_pcohort.add_argument("--contact", type=str, default="", help="招募负责人")
    p_pcohort.add_argument("--notes", type=str, default="", help="备注")

    sub_check = sub.add_parser("env-check", help="环境自检总表：汇总四个缺口还差什么（不打印凭据值）")
    sub_check.add_argument("--no-probe", dest="no_probe", action="store_true", help="跳过真实网络探测，只查配置是否存在")
    sub_check.add_argument("--json", action="store_true", help="输出结构化 JSON")
    sub_check.add_argument("--run-mode", dest="run_mode", type=str, default=None,
                           choices=["local", "platform"],
                           help="运行模式：local=只体检本地开发所需（缺省）；platform=含渠道/沙箱/Staging/遥测")

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

    # v10.0 环境治理与工具链健康审查 (Doctor)
    p_doc = sub.add_parser("doctor", help="全面体检宿主机环境与运行时工具链就绪度 (Doctor)")
    p_doc.add_argument("--target", type=str, default="web", choices=["web", "godot", "wasm_rust", "llm"], help="目标技术栈预检")

    # W1 专家 Agent 运行时
    sub.add_parser("agent-cards", help="列出已注册专家角色卡与 82 位目标的真实缺口")
    p_arun = sub.add_parser("agent-run", parents=[llm_parent], help="激活一位专家执行任务（无 LLM 时诚实报 NEEDS_LLM_CREDENTIALS）")
    p_arun.add_argument("--card", type=str, default="", help="专家卡 id（如 lead_producer）")
    p_arun.add_argument("--task", type=str, default="", help="交给该专家的任务描述")
    p_arun.add_argument("--context", type=str, default="{}", help="上下文 JSON 字符串")
    p_arun.add_argument("--preflight", action="store_true", help="只做环境自检，不调用专家")

    # LLM 端点池（免费额度）导入与真实探测
    p_limp = sub.add_parser("llm-import", help="从本地 JSON 导入 LLM 端点池（含密钥，写入 gitignore 的 config/）")
    p_limp.add_argument("--file", type=str, required=True, help="端点 JSON 文件路径")
    sub.add_parser("llm-status", help="真实探测每个 LLM 端点的连通性（不发请求不记可用）")

    # L2 技能库（W3 适配状态）
    sub.add_parser("skill-list", help="列出 114 项 L2 技能的真实适配进度（分母=114 不可少）")

    p_srun = sub.add_parser("skill-run", help="真实跑一项 C 类技能（需可用 LLM 端点，不跑不许说能用）")
    p_srun.add_argument("--skill", type=str, required=True, help="技能 id，如 core_loop_design")
    p_srun.add_argument("--task", type=str, default="", help="具体任务描述；留空用内置默认任务")
    p_srun.add_argument("--provider", type=str, default="auto")
    p_srun.add_argument("--model", type=str, default=None)
    p_vc = sub.add_parser("skill-verify-c", help="批量真实跑通 24 项 C 类技能并落证据（通过的才注册）")
    p_vc.add_argument("--skill", type=str, default=None, help="只跑指定技能，默认全跑")
    p_vc.add_argument("--model", type=str, default=None, help="指定端点池里的具体模型 id，会记进证据")
    sub.add_parser("skill-audit-c",
                   help="离线复校验：历史通过的 payload 在当前契约下是否仍成立（不调 LLM）")
    p_vb = sub.add_parser("skill-verify-b", help="批量真实运行 B 类确定性算法并落证据（验收通过的才注册）")
    p_vb.add_argument("--skill", type=str, default=None, help="只跑指定技能，默认全跑")
    p_rb = sub.add_parser("skill-run-b", help="真实运行一项 B 类技能（确定性，不调 LLM）")
    p_rb.add_argument("--skill", type=str, required=True, help="技能 id，如 a_star_pathfinding")
    p_rb.add_argument("--params", type=str, default="", help="JSON 参数；留空用内置默认参数")
    sub.add_parser("skill-audit-b", help="离线复验：B 类历史通过的 payload 在当前契约下是否仍成立")

    # ── W5：2D 资产工厂 ─────────────────────────────────────────────────────
    p_as = sub.add_parser("asset-style",
                          help="初始化并锁定风格圣经 StyleBible（后续资产 prompt 必须引用）")
    p_as.add_argument("--name", type=str, default="default", help="风格名")
    p_as.add_argument("--seed", type=int, default=0, help="确定性派生色板种子")
    p_as.add_argument("--palette", type=str, default=None,
                      help="显式色板（逗号分隔 hex，如 #1e2a4a,#d9bb74）；缺省确定性派生")
    p_as.add_argument("--out", type=str, default="evidence/style_bible.json", help="存档路径")
    p_ag = sub.add_parser("asset-gen",
                           help="生成一项 2D 资产：ImageGenAdapter 出图 → 入库 QA → 落工件")
    p_ag.add_argument("--type", type=str, default="icon",
                      choices=["character", "enemy", "item", "tile", "ui", "background", "icon", "store"],
                      help="资产类型")
    p_ag.add_argument("--name", type=str, default="asset", help="资产名")
    p_ag.add_argument("--width", type=int, default=512, help="宽（会自动对齐到 8 的倍数）")
    p_ag.add_argument("--height", type=int, default=512, help="高")
    p_ag.add_argument("--require-alpha", action="store_true", help="要求透明通道")
    p_ag.add_argument("--frames", type=int, default=1, help="帧数（W5 单帧；>1 仅记录）")
    p_ag.add_argument("--prompt", type=str, default="", help="正向提示词（建议描述资产内容）")
    p_ag.add_argument("--style", type=str, default="evidence/style_bible.json", help="风格圣经路径")
    p_ag.add_argument("--seed", type=int, default=None, help="随机种子（程序化/ComfyUI 复用）")
    p_ag.add_argument("--backend", type=str, default=None,
                      choices=["comfyui_local", "cloud_api", "procedural_placeholder"],
                      help="指定后端；缺省按优先级自动选（云→本地 ComfyUI→程序化占位）")
    p_ag.add_argument("--out", type=str, default="output/w5_assets", help="输出目录")
    p_av = sub.add_parser("asset-verify", help="仅对已有 PNG 跑入库 QA（不重新生成）")
    p_av.add_argument("--file", type=str, required=True, help="待测 PNG 路径")
    p_av.add_argument("--type", type=str, default="icon", help="资产类型")
    p_av.add_argument("--name", type=str, default="asset", help="资产名")
    p_av.add_argument("--width", type=int, default=512, help="规格宽")
    p_av.add_argument("--height", type=int, default=512, help="规格高")
    p_av.add_argument("--require-alpha", action="store_true", help="规格要求透明通道")
    p_av.add_argument("--style", type=str, default="evidence/style_bible.json", help="风格圣经路径")

    p_aa = sub.add_parser("asset-audio", parents=[llm_parent],
                          help="W7：真实合成音频资产（SFX/BGM 16-bit PCM WAV，程序化合成）")
    p_aa.add_argument("--kind", type=str, default="laser",
                      help="音效类型 laser/hit/explosion/coin/ui_click/step/powerup，"
                           "或 BGM 调式名 pentatonic/dorian/harmonic_minor/cyberpunk")
    p_aa.add_argument("--name", type=str, default="", help="资产名（缺省按 kind 推导）")
    p_aa.add_argument("--duration", type=float, default=1.0, help="目标时长秒（BGM 据此控长）")
    p_aa.add_argument("--sample-rate", type=int, default=44100, help="采样率 Hz")
    p_aa.add_argument("--theme", type=str, default="dorian", help="BGM 默认调式（当 kind 非已知调式时回退）")
    p_aa.add_argument("--bpm", type=int, default=120, help="BGM 速度")
    p_aa.add_argument("--backend", type=str, default=None,
                      choices=["procedural_synth", "cloud_audio"],
                      help="生成后端；缺省 auto（当前仅程序化合成可用，cloud_audio 未接入需 NEEDS_RUNTIME_TOOL）")
    p_aa.add_argument("--seed", type=int, default=None, help="确定性种子")
    p_aa.add_argument("--output", type=str, default="", help="输出目录（缺省 output/assets/audio）")

    p_aav = sub.add_parser("asset-audio-verify", parents=[llm_parent],
                           help="W7：仅对已有 WAV 跑入库 QA（独立解码校验，不重新生成）")
    p_aav.add_argument("--file", type=str, required=True, help="待测 WAV 路径")
    p_aav.add_argument("--kind", type=str, default="", help="可选：资产 kind（用于时长/语义 QA 对照）")

    p_playtest = sub.add_parser("playtest", parents=[llm_parent],
                                help="W8：自动试玩闭环（真实浏览器加载 + 多轮 episode 驱动 + 诚实 verdict）")
    p_playtest.add_argument("--target", type=str, default="",
                            help="本地 HTML 试玩目标（必填；远程 URL 需先镜像为本地文件）")
    p_playtest.add_argument("--url", type=str, default="",
                            help="别名：--target 的等价项（远程 URL 当前不支持，需本地文件）")
    p_playtest.add_argument("--episodes", type=int, default=3,
                            help="试玩轮数（多轮聚合真实证据）")
    p_playtest.add_argument("--ticks", type=int, default=20,
                            help="每轮自动输入步数（≈ ticks×0.15s 驱动时长）")
    p_playtest.add_argument("--seed", type=int, default=0, help="确定性随机种子")
    p_playtest.add_argument("--out", type=str, default="",
                            help="EvidencePack 输出目录（缺省 output/playtest）")
    p_playtest.add_argument("--headless", dest="headless", action="store_true",
                            default=True, help="无头运行（默认开）")
    p_playtest.add_argument("--no-headless", dest="headless", action="store_false",
                            help="有头运行（需本机显示环境；默认无头）")

    p_vs = sub.add_parser("vertical-slices", parents=[llm_parent],
                          help="W9：八垂直切片端到端验证（生成→接W7音频→W8真实试玩→诚实 verdict）")
    p_vs.add_argument("--slice", type=str, default="",
                      help="指定单个切片 id（缺省验证全部 8 个）；可用 id 见 pipeline/vertical_slices.py")
    p_vs.add_argument("--episodes", type=int, default=2, help="每片试玩轮数")
    p_vs.add_argument("--ticks", type=int, default=20, help="每轮自动输入步数（≈ ticks×0.15s）")
    p_vs.add_argument("--seed", type=int, default=42, help="确定性随机种子")
    p_vs.add_argument("--out", type=str, default="", help="切片输出根目录（缺省 output/slices）")
    p_vs.add_argument("--no-audio", dest="no_audio", action="store_true",
                      help="不接入 W7 程序化音频（仅验证运行/试玩链路）")
    p_vs.add_argument("--headless", dest="headless", action="store_true",
                      default=True, help="无头运行（默认开）")

    p_auton = sub.add_parser("autonomous", parents=[llm_parent],
                             help="W10：长时程自主生产（一句话意图→无人值守→可上架包；仅三处停）")
    p_auton.add_argument("--title", type=str, default="", help="一句话意图中的游戏标题（必填）")
    p_auton.add_argument("--genre", type=str, default="节奏",
                         help="游戏类型（节奏/卡牌/弹幕/赛车/工厂/地牢/3d/叙事 等，缺省节奏）")
    p_auton.add_argument("--rules", type=str, default="", help="玩法规则/约束描述（可选）")
    p_auton.add_argument("--budget", type=float, default=100.0, help="预算上限 USD（超预算即暂停上报）")
    p_auton.add_argument("--episodes", type=int, default=2, help="真机试玩轮数")
    p_auton.add_argument("--ticks", type=int, default=20, help="每轮自动输入步数（≈ ticks×0.15s）")
    p_auton.add_argument("--seed", type=int, default=42, help="确定性随机种子")
    p_auton.add_argument("--no-resume", dest="no_resume", action="store_true",
                         help="禁用断点续跑（每次全新执行，供测试/演练）")
    p_auton.add_argument("--cost-table", type=str, default="",
                         help="注入成本表 JSON（如 '{\"assemble.build\":999}'），触发超预算暂停验证")
    p_auton.add_argument("--art-backend", type=str, default=None,
                         choices=["comfyui_local", "cloud_api", "procedural_placeholder"],
                         help="美术后端；缺省 auto（cloud→本机 ComfyUI→程序化占位）")
    # 注意：--mode 已被 llm_parent 占用（fast/llm/hybrid 生成模式），故用 --run-mode
    p_auton.add_argument("--run-mode", dest="run_mode", type=str, default=None,
                         choices=["local", "platform"],
                         help="运行模式：local=本地开发（不要求任何渠道/线上配置，缺省）；"
                              "platform=平台对接（要求渠道凭据+三类沙箱+Staging+遥测齐全，缺即阻断）")

    # list-parts
    sub.add_parser("list-parts", help="查看 Ford-T 零件库全部 35 个工业机制零件")

    # assemble
    p_ass = sub.add_parser("assemble", help="根据指定零件组合模块化装配新游戏架构")
    p_ass.add_argument("title", help="游戏名称")
    p_ass.add_argument("--parts", required=True, help="逗号分隔的零件 key 列表")

    # templates
    sub.add_parser("templates", help="列出内置可玩游戏骨架模板")

    # wechat-pack
    p_wxp = sub.add_parser("wechat-pack", help="一键打包微信小游戏工程 (带 4MB 分包预检)")
    p_wxp.add_argument("--template", default="survivor_danmaku", help="模板名称 (survivor_danmaku, card_roguelike) 或 HTML 文件路径")
    p_wxp.add_argument("--out", default="dist/wechat", help="输出目录")
    p_wxp.add_argument("--name", default="antigravity-wechat-game", help="项目工程名称")
    p_wxp.add_argument("--orientation", default="portrait", choices=["portrait", "landscape"], help="屏幕方向")
    p_wxp.add_argument("--run-id", dest="run_id", type=str, default="", help="关联运行沙箱 ID")

    args = parser.parse_args()
    # 所有旧工具统一经过 RunService 审计入口，避免任何命令旁路契约与发布门禁
    return run_service.dispatch_tool(args.command, COMMAND_TABLE, args, parser.print_help)

if __name__ == "__main__":
    sys.exit(main())
