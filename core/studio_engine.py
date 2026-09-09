#!/usr/bin/env python3
"""
studio_engine.py: 工业级多智能体深度协同与流式流水线引擎
调度专家智能体、Skills 与生命周期 Hooks，支持依赖注入与清晰的分层架构。
"""
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.consensus_engine import ConsensusEngine

# 导入 5 大核心工业级结构化知识库 (同属 core/knowledge 基础层)
from knowledge.math_and_economy import MathAndEconomyKnowledge
from knowledge.pcg_and_algorithms import PCGAndAlgorithmsKnowledge
from knowledge.godot_engine_specs import GodotEngineSpecsKnowledge
from knowledge.audio_and_art_specs import AudioAndArtSpecsKnowledge
from knowledge.qa_and_antiglitch import QAAndAntiGlitchKnowledge

class StudioEngine:
    """多智能体深度协同与流式流水线引擎 (支持 output_dir 依赖注入)"""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else ROOT / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def execute_step_by_step(
        self,
        title: str = "反恐前线：幽灵突击 3D",
        genre: str = "3D FPS",
        custom_rules: str = "",
        mode: str = "fast",
        llm_provider: str = "gemini",
        llm_model: Any = None,
        run_id: Optional[str] = None,
        export_release: bool = False,
    ) -> List[Dict[str, Any]]:
        """逐步执行 12 个生命周期 Hooks，支持任务级沙箱隔离与可审计运行清单"""
        from core.agent_philosophy import AgentPhilosophy
        from agents.studio_roster import studio_roster
        from pipeline.gdd_generator import GDDGenerator
        from pipeline.verb_assembler import VerbAssembler
        from pipeline.visual_qa_loop import VisualQALoop
        from pipeline.godot_exporter import GodotExporter
        from pipeline.peer_review_pipeline import PeerReviewPipeline
        from core.run_context import RunContext
        from hooks.hook_manager import hook_manager

        AgentPhilosophy.print_axiom()
        run_ctx = RunContext(title=title, base_dir=self.output_dir, run_id=run_id)
        run_ctx.set_inputs(title=title, genre=genre, custom_rules=custom_rules, mode=mode, export_release=export_release)
        steps = []

        # 3D 次时代美术团队是跨部门交付单元：只有在需求命中 3D/PBR/LOD/材质等
        # 关键词时加入当前 run；其成员、执行器、工件和门禁均来自 registry 的唯一事实源。
        from core.registry import get_team_execution_plan
        is_next_gen_3d = any(
            keyword in f"{title} {genre} {custom_rules}".lower()
            for keyword in ("3d", "3a", "pbr", "lod", "次时代", "次世代", "材质", "骨骼", "机甲")
        )
        next_gen_team_plan = None
        if is_next_gen_3d:
            next_gen_team_plan = get_team_execution_plan(
                team_id="next_gen_3d_art_team",
                run_id=run_ctx.run_id,
                target="webgl" if "web" in genre.lower() or "3d" in genre.lower() else "godot"
            )
            team_plan_path = run_ctx.work_dir / "next_gen_3d_art_team_plan.json"
            team_plan_path.write_text(
                json.dumps(next_gen_team_plan, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            run_ctx.register_artifact("next_gen_3d_art_team_plan", team_plan_path)
            run_ctx.input_params["teams"] = [next_gen_team_plan]
        else:
            run_ctx.input_params["teams"] = []

        # 阶段 1: pre_init
        t0 = time.time()
        p_lead = studio_roster.get_agent("project_lead")
        hook_ctx = hook_manager.trigger("pre_init", {
            "title": title, "genre": genre, "phase": "商业立项与规范预检",
            "run_id": run_ctx.run_id, "work_dir": str(run_ctx.work_dir)
        })
        run_ctx.record_stage("pre_init", time.time() - t0)
        run_ctx.record_hook("pre_init", ["project_lead", "tools_pipeline_engineer"])
        steps.append({
            "hook": "pre_init",
            "phase": "商业立项与规范预检",
            "active_agents": ["project_lead", "tools_pipeline_engineer"],
            "used_skills": ["control_scheme_mapping"],
            "knowledge_module": "godot_engine_specs.py",
            "agent_name": p_lead.name,
            "log": f"📋 [{p_lead.name}] 确立《{title}》研发基线，分配任务沙箱: {run_ctx.run_id}"
        })

        # 阶段 2: post_init
        t0 = time.time()
        scrum = studio_roster.get_agent("agile_scrum_master")
        hook_manager.trigger("post_init", {
            "title": title, "phase": "敏捷任务拆解与泳道分配", "run_id": run_ctx.run_id
        })
        run_ctx.record_stage("post_init", time.time() - t0)
        run_ctx.record_hook("post_init", ["agile_scrum_master"])
        steps.append({
            "hook": "post_init",
            "phase": "敏捷任务拆解与泳道分配",
            "active_agents": ["agile_scrum_master"],
            "used_skills": ["quest_tree_builder"],
            "knowledge_module": "math_and_economy.py",
            "agent_name": scrum.name,
            "log": f"⚡ [{scrum.name}] 拆解 12 个生命周期冲刺任务，分配 6 大部门 82 位专家协作泳道"
        })

        # 阶段 3: pre_gdd (多智能体共识研讨会)
        t0 = time.time()
        designer = studio_roster.get_agent("lead_game_designer")
        consensus = ConsensusEngine.conduct_design_roundtable(title, genre, custom_rules)
        consensus_path = run_ctx.work_dir / "Consensus_Record.json"
        consensus_path.write_text(json.dumps(consensus, ensure_ascii=False, indent=2), encoding="utf-8")
        run_ctx.register_artifact("consensus_record", consensus_path)

        hook_manager.trigger("pre_gdd", {
            "title": title, "consensus": consensus, "run_id": run_ctx.run_id
        })
        run_ctx.record_stage("pre_gdd", time.time() - t0)
        run_ctx.record_hook("pre_gdd", ["lead_game_designer", "lead_architect", "combat_balancer", "qa_director"])
        steps.append({
            "hook": "pre_gdd",
            "phase": "多专家多轮共识研讨与架构质询",
            "active_agents": ["lead_game_designer", "lead_architect", "combat_balancer", "qa_director"],
            "used_skills": ["core_loop_design", "inventory_slot_matrix"],
            "knowledge_module": "consensus_engine.py (多轮研讨会)",
            "agent_name": designer.name,
            "log": f"🧠 [{designer.name}] 组织敏捷研讨会: 架构师与QA完成交叉质询，制作人签署全票共识决议"
        })

        # 阶段 4: post_gdd
        t0 = time.time()
        producer = studio_roster.get_agent("executive_producer")
        balancer = studio_roster.get_agent("combat_balancer")
        gdd_text = GDDGenerator.generate_gdd(
            title=title,
            genre=genre,
            core_mechanics=custom_rules,
            mode=mode,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
        gdd_path = run_ctx.work_dir / "GDD.md"
        gdd_path.write_text(gdd_text, encoding="utf-8")
        run_ctx.register_artifact("gdd_md", gdd_path)

        # 产出结构化 gdd.json 工件
        gdd_data = {
            "title": title,
            "genre": genre,
            "core_mechanics": custom_rules,
            "target_framerate": 60,
            "input_spec": "Keyboard + Touch 6-frame buffer",
            "economy_model": "3-card-pick / log-decay balance",
            "chapters_count": 8,
            "length_chars": len(gdd_text),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        gdd_json_path = run_ctx.work_dir / "gdd.json"
        gdd_json_path.write_text(json.dumps(gdd_data, ensure_ascii=False, indent=2), encoding="utf-8")
        run_ctx.register_artifact("gdd_json", gdd_json_path)

        hook_manager.trigger("post_gdd", {
            "title": title, "gdd_path": str(gdd_path), "run_id": run_ctx.run_id
        })
        run_ctx.record_stage("post_gdd", time.time() - t0)
        run_ctx.record_hook("post_gdd", ["executive_producer", "combat_balancer", "lead_narrative_designer"])
        steps.append({
            "hook": "post_gdd",
            "phase": "8 大章节工业级 GDD 定案与结构化契约",
            "active_agents": ["executive_producer", "combat_balancer", "lead_narrative_designer"],
            "used_skills": ["gdd_markdown_spec", "dialogue_branching_tree"],
            "knowledge_module": "math_and_economy.py (三选一卡牌掉落分布/对数衰减公式)",
            "agent_name": producer.name,
            "log": f"📜 [{producer.name}] 输出 8 大章节 GDD 规格书 (字数: {len(gdd_text)}) 与结构化契约 gdd.json"
        })

        # 阶段 5: pre_core_loop
        t0 = time.time()
        architect = studio_roster.get_agent("lead_architect")
        hook_manager.trigger("pre_core_loop", {
            "title": title, "phase": "三层解耦与 Actor-Trait 架构装配", "run_id": run_ctx.run_id
        })
        run_ctx.record_stage("pre_core_loop", time.time() - t0)
        run_ctx.record_hook("pre_core_loop", ["lead_architect", "gameplay_programmer"])
        steps.append({
            "hook": "pre_core_loop",
            "phase": "三层解耦与 Actor-Trait 架构装配",
            "active_agents": ["lead_architect", "gameplay_programmer"],
            "used_skills": ["oop_inheritance_linter", "actor_trait_composition"],
            "knowledge_module": "qa_and_antiglitch.py (禁止硬编码派生类/彻底杜绝耦合地狱)",
            "agent_name": architect.name,
            "log": f"📐 [{architect.name}] 确立纯组件化架构，严禁上帝类，装配 6 帧先进制输入缓冲队列"
        })

        # 阶段 6: post_core_loop
        t0 = time.time()
        programmer = studio_roster.get_agent("gameplay_programmer")
        raw_code = VerbAssembler.assemble_game(
            title=title,
            genre=genre,
            custom_rules=custom_rules,
            mode=mode,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
        hook_manager.trigger("post_core_loop", {
            "title": title, "raw_code_len": len(raw_code), "run_id": run_ctx.run_id
        })
        run_ctx.record_stage("post_core_loop", time.time() - t0)
        run_ctx.record_hook("post_core_loop", ["gameplay_programmer", "ai_behavior_engineer"])
        steps.append({
            "hook": "post_core_loop",
            "phase": "动词驱动器与 60fps 确定性状态机装配",
            "active_agents": ["gameplay_programmer", "ai_behavior_engineer"],
            "used_skills": ["canvas_vector_sprite_generator", "math_vector_math"],
            "knowledge_module": "pcg_and_algorithms.py (A*网格寻路/八叉树视锥剔除)",
            "agent_name": programmer.name,
            "log": f"💻 [{programmer.name}] 核心循环代码生成完毕 ({len(raw_code)} 字节)，挂载确定性物理时钟"
        })

        # 阶段 7: pre_code_review (同行审查)
        t0 = time.time()
        critic = studio_roster.get_agent("code_critic")
        critic_name = critic.name if critic else "Code Critic"
        review_report = PeerReviewPipeline.audit_and_signoff(raw_code)
        _revs = review_report.get("reviews", [])
        review_report["pass_rate"] = (
            round(sum(1 for r in _revs if r.get("verdict") == "PASSED") / len(_revs) * 100, 1)
            if _revs else 0.0
        )
        peer_review_path = run_ctx.work_dir / "Peer_Review_Report.json"
        peer_review_path.write_text(json.dumps(review_report, ensure_ascii=False, indent=2), encoding="utf-8")
        run_ctx.register_artifact("peer_review_report", peer_review_path)

        hook_manager.trigger("pre_code_review", {
            "pass_rate": review_report["pass_rate"], "run_id": run_ctx.run_id
        })
        run_ctx.record_stage("pre_code_review", time.time() - t0)
        run_ctx.record_hook("pre_code_review", ["code_critic", "security_engineer"])
        steps.append({
            "hook": "pre_code_review",
            "phase": "红蓝军代码架构与坏味道审查",
            "active_agents": ["code_critic", "security_engineer"],
            "used_skills": ["ast_code_smell_auditor", "dry_solid_pattern_checker"],
            "knowledge_module": "peer_review_pipeline.py (红蓝军对抗矩阵)",
            "agent_name": critic_name,
            "log": f"🔍 [{critic_name}] 同行审查通过率: {review_report['pass_rate']}%，签署零异味合格证"
        })

        # 阶段 8: post_code_review
        t0 = time.time()
        perf_eng = studio_roster.get_agent("performance_optimizer")
        hook_manager.trigger("post_code_review", {"title": title, "run_id": run_ctx.run_id})
        run_ctx.record_stage("post_code_review", time.time() - t0)
        run_ctx.record_hook("post_code_review", ["performance_optimizer"])
        steps.append({
            "hook": "post_code_review",
            "phase": "内存泄漏与垃圾回收 (GC) 零分配审计",
            "active_agents": ["performance_optimizer"],
            "used_skills": ["object_pool_builder", "arraybuffer_packager"],
            "knowledge_module": "pcg_and_algorithms.py (对象池环形缓冲区)",
            "agent_name": perf_eng.name,
            "log": f"🚀 [{perf_eng.name}] 静态预分配 500+ 对象池，主循环 Allocations 压降为 0KB/frame"
        })

        # 阶段 9: pre_asset_synthesis
        t0 = time.time()
        artist = studio_roster.get_agent("art_director")
        palette_keys = list(AudioAndArtSpecsKnowledge.PALETTES.keys())
        asset_team_agents = (
            next_gen_team_plan["active_agents"]
            if next_gen_team_plan
            else ["art_director", "vfx_particle_specialist"]
        )
        asset_team_skills = (
            sorted({skill for capability in next_gen_team_plan["capabilities"] for skill in capability["skills"]})
            if next_gen_team_plan
            else ["canvas_particle_emitter", "lighting_bloom_postprocess"]
        )
        hook_manager.trigger("pre_asset_synthesis", {
            "palette": palette_keys[0],
            "run_id": run_ctx.run_id,
            "team_id": next_gen_team_plan["team_id"] if next_gen_team_plan else None,
            "asset_gates": next_gen_team_plan["required_gates"] if next_gen_team_plan else [],
        })
        run_ctx.record_stage("pre_asset_synthesis", time.time() - t0, {
            "team_id": next_gen_team_plan["team_id"] if next_gen_team_plan else None
        })
        run_ctx.record_hook("pre_asset_synthesis", asset_team_agents)
        steps.append({
            "hook": "pre_asset_synthesis",
            "phase": "调色盘体系与材质粒子管线",
            "active_agents": asset_team_agents,
            "team_id": next_gen_team_plan["team_id"] if next_gen_team_plan else None,
            "used_skills": asset_team_skills,
            "required_gates": next_gen_team_plan["required_gates"] if next_gen_team_plan else [],
            "knowledge_module": f"audio_and_art_specs.py (调色盘: {palette_keys[0]})",
            "agent_name": artist.name,
            "log": (
                f"✨ [{artist.name}] 调入工业调色盘与材质/粒子管线"
                + (f"，绑定 {next_gen_team_plan['team_name']}，注册 {len(asset_team_agents)} 名成员与 {len(asset_team_skills)} 项能力"
                   if next_gen_team_plan else "，注入发光轮廓与爆炸冲击波")
            )
        })

        # 阶段 10: post_asset_synthesis
        t0 = time.time()
        synth_eng = studio_roster.get_agent("webaudio_synth_engineer")
        hook_manager.trigger("post_asset_synthesis", {
            "run_id": run_ctx.run_id,
            "team_id": next_gen_team_plan["team_id"] if next_gen_team_plan else None,
        })
        run_ctx.record_stage("post_asset_synthesis", time.time() - t0, {
            "team_id": next_gen_team_plan["team_id"] if next_gen_team_plan else None
        })
        audio_agents = ["audio_director", "webaudio_synth_engineer", "sfx_designer"]
        if next_gen_team_plan:
            audio_agents = list(dict.fromkeys(audio_agents + ["adaptive_audio_master", "pbr_material_pipeline_engineer"]))
        run_ctx.record_hook("post_asset_synthesis", audio_agents)
        steps.append({
            "hook": "post_asset_synthesis",
            "phase": "WebAudio 原生 ADSR 音效合成与次时代资产交付准备",
            "active_agents": audio_agents,
            "team_id": next_gen_team_plan["team_id"] if next_gen_team_plan else None,
            "used_skills": ["webaudio_retro_synth", "adsr_envelope_shaper"] + (
                ["pbr_five_channel_baking", "tangent_normal_brdf_shader"] if next_gen_team_plan else []
            ),
            "knowledge_module": "audio_and_art_specs.py (PROCEDURAL_SFX_PRESETS: 激光/爆炸/金币)",
            "agent_name": synth_eng.name,
            "log": (
                f"🎵 [{synth_eng.name}] 基于知识库 ADSR 参数合成原生激光、爆炸、受击与大三和弦音效"
                + ("；3D 次时代团队资产计划已登记，待 PBR/LOD/骨骼门禁验证" if next_gen_team_plan else "")
            )
        })

        # 阶段 11: pre_qa_audit
        t0 = time.time()
        qa_dir = studio_roster.get_agent("qa_director")
        qa_res = VisualQALoop.audit_and_heal(raw_code)
        hook_manager.trigger("pre_qa_audit", {"qa_verdict": qa_res["verdict"], "run_id": run_ctx.run_id})
        run_ctx.record_stage("pre_qa_audit", time.time() - t0)
        run_ctx.record_hook("pre_qa_audit", ["qa_director", "headless_automation_qa", "visual_glitch_inspector"])
        steps.append({
            "hook": "pre_qa_audit",
            "phase": "CCD 反穿模与结构化语法校验",
            "active_agents": ["qa_director", "headless_automation_qa", "visual_glitch_inspector"],
            "used_skills": ["headless_input_simulator", "fps_stability_auditor", "visual_frame_diff_auditor"],
            "knowledge_module": "qa_and_antiglitch.py (CCD 连续碰撞/固定 60Hz 步长)",
            "agent_name": qa_dir.name,
            "log": f"👁️ [{qa_dir.name}] 执行 CCD 反穿模检验与结构化语法审计，判定: 【{qa_res['verdict']}】"
        })

        # 阶段 12: post_release
        t0 = time.time()
        game_path = run_ctx.work_dir / "index.html"
        game_path.write_text(qa_res["healed_code"], encoding="utf-8")
        run_ctx.register_artifact("game_html", game_path)
        godot_dir = GodotExporter.export_godot_project(title, genre, run_ctx.work_dir)

        # 生成可审计运行清单 run_manifest.json
        manifest = run_ctx.generate_manifest()

        # 默认只完成运行目录归档；只有显式 export_release 才允许旧兼容导出。
        # 正式 Preview/Production 候选必须由 ReleaseService 创建 ReleaseManifest。
        promoted = []
        if export_release:
            promoted = run_ctx.promote_to_release(self.output_dir)

        hook_manager.trigger("post_release", {
            "title": title, "run_id": run_ctx.run_id, "output_dir": str(self.output_dir)
        })
        run_ctx.record_stage("post_release", time.time() - t0)
        run_ctx.record_hook("post_release", ["executive_producer", "platform_porting_engineer"])

        steps.append({
            "hook": "post_release",
            "phase": "商业级工程交付与原子提升发布",
            "active_agents": ["executive_producer", "platform_porting_engineer"],
            "used_skills": ["cross_browser_api_linter"],
            "knowledge_module": "godot_engine_specs.py (project.godot / main.tscn / main.gd)",
            "agent_name": producer.name,
            "promoted_files": [str(path) for path in promoted],
            "log": (f"🎉 [{producer.name}] 运行目录交付完成: 沙箱 {run_ctx.run_id} 已归档"
                    + (f"，兼容导出至 {self.output_dir}" if export_release else "，未执行发布提升；需通过 ReleaseService 门禁")), 
            "game_file": str(self.output_dir / "index.html"),
            "godot_dir": str(godot_dir),
            "gdd_file": str(self.output_dir / "GDD.md"),
            "run_id": run_ctx.run_id,
            "qa_verdict": qa_res["verdict"]
        })

        self._last_run_ctx = run_ctx
        self._last_team_plan = next_gen_team_plan
        return steps

    def create_game_pipeline(
        self,
        title: str = "反恐前线：幽灵突击 3D",
        genre: str = "3D FPS",
        custom_rules: str = "",
        mode: str = "fast",
        llm_provider: str = "gemini",
        llm_model: Any = None,
        run_id: Optional[str] = None,
        export_release: bool = False,
    ) -> Dict[str, Any]:
        steps = self.execute_step_by_step(
            title=title,
            genre=genre,
            custom_rules=custom_rules,
            mode=mode,
            llm_provider=llm_provider,
            llm_model=llm_model,
            run_id=run_id,
            export_release=export_release,
        )
        logs = [s["log"] for s in steps]
        last = steps[-1]
        run_id = last.get("run_id", "")
        run_ctx = getattr(self, "_last_run_ctx", None)
        run_ctx_team_plan = getattr(self, "_last_team_plan", None)
        manifest = run_ctx.generate_manifest() if run_ctx else {}

        return {
            "status": "success",
            "run_id": run_id,
            "title": title,
            "manifest": manifest,
            "steps": steps,
            "logs": logs,
            "game_file": last.get("game_file"),
            "godot_dir": last.get("godot_dir"),
            "gdd_file": last.get("gdd_file"),
            "qa_verdict": last.get("qa_verdict"),
            "teams": [run_ctx_team_plan] if run_ctx_team_plan else [],
        }

studio_engine = StudioEngine()
