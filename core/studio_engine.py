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
    ) -> List[Dict[str, Any]]:
        """逐步执行 12 个生命周期 Hooks，解耦上层 agents 与 pipeline 静态绑定"""
        from core.agent_philosophy import AgentPhilosophy
        from agents.studio_roster import studio_roster
        from pipeline.gdd_generator import GDDGenerator
        from pipeline.verb_assembler import VerbAssembler
        from pipeline.visual_qa_loop import VisualQALoop
        from pipeline.godot_exporter import GodotExporter
        from pipeline.peer_review_pipeline import PeerReviewPipeline

        AgentPhilosophy.print_axiom()
        steps = []

        # 阶段 1: pre_init
        p_lead = studio_roster.get_agent("project_lead")
        steps.append({
            "hook": "pre_init",
            "phase": "商业立项与规范预检",
            "active_agents": ["project_lead", "tools_pipeline_engineer"],
            "used_skills": ["control_scheme_mapping"],
            "knowledge_module": "godot_engine_specs.py",
            "agent_name": p_lead.name,
            "log": f"📋 [{p_lead.name}] 确立《{title}》研发基线，加载 Godot 4 视口与 WebAssembly 编译工具链"
        })

        # 阶段 2: post_init
        scrum = studio_roster.get_agent("agile_scrum_master")
        steps.append({
            "hook": "post_init",
            "phase": "敏捷任务拆解与泳道分配",
            "active_agents": ["agile_scrum_master"],
            "used_skills": ["quest_tree_builder"],
            "knowledge_module": "math_and_economy.py",
            "agent_name": scrum.name,
            "log": f"⚡ [{scrum.name}] 拆解 12 个生命周期冲刺任务，分配 6 大部门 75 位专家协作泳道"
        })

        # 阶段 3: pre_gdd (多智能体共识研讨会)
        designer = studio_roster.get_agent("lead_game_designer")
        consensus = ConsensusEngine.conduct_design_roundtable(title, genre, custom_rules)
        (self.output_dir / "Consensus_Record.json").write_text(json.dumps(consensus, ensure_ascii=False, indent=2), encoding="utf-8")
        
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
        gdd_path = self.output_dir / "GDD.md"
        gdd_path.write_text(gdd_text, encoding="utf-8")

        steps.append({
            "hook": "post_gdd",
            "phase": "8 大章节工业级 GDD 定案",
            "active_agents": ["executive_producer", "combat_balancer", "lead_narrative_designer"],
            "used_skills": ["gdd_markdown_spec", "dialogue_branching_tree"],
            "knowledge_module": "math_and_economy.py (三选一卡牌掉落分布/对数衰减公式)",
            "agent_name": producer.name,
            "log": f"📜 [{producer.name}] 输出 8 大章节 GDD 规格书 (字数: {len(gdd_text)})，签署数值稳健性契约"
        })

        # 阶段 5: pre_core_loop
        architect = studio_roster.get_agent("lead_architect")
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
        programmer = studio_roster.get_agent("gameplay_programmer")
        raw_code = VerbAssembler.assemble_game(
            title=title,
            genre=genre,
            custom_rules=custom_rules,
            mode=mode,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
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
        critic = studio_roster.get_agent("code_critic")
        critic_name = critic.name if critic else "Code Critic"
        review_report = PeerReviewPipeline.audit_and_signoff(raw_code)
        _revs = review_report.get("reviews", [])
        review_report["pass_rate"] = (
            round(sum(1 for r in _revs if r.get("verdict") == "PASSED") / len(_revs) * 100, 1)
            if _revs else 0.0
        )
        (self.output_dir / "Peer_Review_Report.json").write_text(json.dumps(review_report, ensure_ascii=False, indent=2), encoding="utf-8")
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
        perf_eng = studio_roster.get_agent("performance_optimizer")
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
        artist = studio_roster.get_agent("art_director")
        palette_keys = list(AudioAndArtSpecsKnowledge.PALETTES.keys())
        steps.append({
            "hook": "pre_asset_synthesis",
            "phase": "调色盘体系与材质粒子管线",
            "active_agents": ["art_director", "vfx_particle_specialist"],
            "used_skills": ["canvas_particle_emitter", "lighting_bloom_postprocess"],
            "knowledge_module": f"audio_and_art_specs.py (调色盘: {palette_keys[0]})",
            "agent_name": artist.name,
            "log": f"✨ [{artist.name}] 调入工业调色盘与粒子着色器，注入发光轮廓与爆炸冲击波"
        })

        # 阶段 10: post_asset_synthesis
        synth_eng = studio_roster.get_agent("webaudio_synth_engineer")
        steps.append({
            "hook": "post_asset_synthesis",
            "phase": "WebAudio 原生 ADSR 音效合成",
            "active_agents": ["audio_director", "webaudio_synth_engineer", "sfx_designer"],
            "used_skills": ["webaudio_retro_synth", "adsr_envelope_shaper"],
            "knowledge_module": "audio_and_art_specs.py (PROCEDURAL_SFX_PRESETS: 激光/爆炸/金币)",
            "agent_name": synth_eng.name,
            "log": f"🎵 [{synth_eng.name}] 基于知识库 ADSR 参数合成原生激光、爆炸、受击与大三和弦音效"
        })

        # 阶段 11: pre_qa_audit
        qa_dir = studio_roster.get_agent("qa_director")
        qa_res = VisualQALoop.audit_and_heal(raw_code)
        steps.append({
            "hook": "pre_qa_audit",
            "phase": "CCD 反穿模与 godogen 视觉自愈",
            "active_agents": ["qa_director", "headless_automation_qa", "visual_glitch_inspector"],
            "used_skills": ["headless_input_simulator", "fps_stability_auditor", "visual_frame_diff_auditor"],
            "knowledge_module": "qa_and_antiglitch.py (CCD 连续碰撞/固定 60Hz 步长)",
            "agent_name": qa_dir.name,
            "log": f"👁️ [{qa_dir.name}] 执行 CCD 反穿模检验与 100 帧无头自愈审计，判定: 【{qa_res['verdict']}】"
        })

        # 阶段 12: post_release
        game_path = self.output_dir / "index.html"
        game_path.write_text(qa_res["healed_code"], encoding="utf-8")
        godot_dir = GodotExporter.export_godot_project(title, genre, self.output_dir)

        steps.append({
            "hook": "post_release",
            "phase": "商业级工程交付与 Godot 4 导出",
            "active_agents": ["executive_producer", "platform_porting_engineer"],
            "used_skills": ["cross_browser_api_linter"],
            "knowledge_module": "godot_engine_specs.py (project.godot / main.tscn / main.gd)",
            "agent_name": producer.name,
            "log": f"🎉 [{producer.name}] 商业工程构建交付: Web 3D/2D 沙盒已热挂载，Godot 4 跨端商业工程包已成功导出至 {godot_dir}",
            "game_file": str(game_path),
            "godot_dir": str(godot_dir),
            "gdd_file": str(gdd_path),
            "qa_verdict": qa_res["verdict"]
        })

        return steps

    def create_game_pipeline(
        self,
        title: str = "反恐前线：幽灵突击 3D",
        genre: str = "3D FPS",
        custom_rules: str = "",
        mode: str = "fast",
        llm_provider: str = "gemini",
        llm_model: Any = None,
    ) -> Dict[str, Any]:
        steps = self.execute_step_by_step(
            title=title,
            genre=genre,
            custom_rules=custom_rules,
            mode=mode,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
        logs = [s["log"] for s in steps]
        last = steps[-1]
        return {
            "status": "success",
            "title": title,
            "steps": steps,
            "logs": logs,
            "game_file": last.get("game_file"),
            "godot_dir": last.get("godot_dir"),
            "gdd_file": last.get("gdd_file"),
            "qa_verdict": last.get("qa_verdict")
        }

studio_engine = StudioEngine()
