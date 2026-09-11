"""core/skill_classification.py — 114 项 L2 技能的显式 B/C 分类表（W3c-1）。

为什么要有这张表
──────────────
之前的流程是"机器按文件名相似度找 A 类，找不到的先挂 PENDING"。
这留下 89 项没有归属。W3c 要做的第一件事不是写代码，而是**逐条给出分类和理由**，
让任何一个人都能打开这个文件、指着某一行说"这条分错了"——这是可审计的前提。
分类错了可以改，但没有分类、或者为了凑数硬塞，就是伪证。

判定规则（写死在这里，避免事后口头解释）
──────────────────────────────────────
C 类（绑 LLM）——满足任一：
  (a) 产出主体是自然语言创作：剧情、对白、引导文案、合规文案；
  (b) 产出是设计方案，且验收必须靠语义判断才能断言（如"循环是否闭环"、
      "引导是否隐式"、"经济模型是否自洽"）；
  (c) 产出是对体验 / 审美 / 商业的评估结论，没有可计算的金标准。

B 类（确定性可实现）——
  产出可由确定性算法生成，并用数值断言验收：碰撞、寻路、插值、音频合成、
  序列化、概率分布、性能采集、图像差分等。

A 类（已有现成模块）——已由 core/skill_registry_seeds.py 真实注册，本表不动。

注意：B 类"可实现"不等于"已实现"。本表只回答"该走哪条路"，
不回答"是否已经做完"。做完与否由 skill_registry 的 status 单独表达。
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from core.skill_registry import SkillClass

# ── 24 项 C 类：产出必须经 LLM 生成 + schema/acceptance 校验 ────────────────
C_SKILLS: Dict[str, str] = {
    # ── GDD 策划族（14）────────────────────────────────────────────────
    "core_loop_design":
        "(b) 核心循环是否闭环、单局时长是否成立，只能靠语义判断，无数值金标准。",
    "economy_balance_math":
        "(b) 产出是经济模型的假设与设计意图（产出/消耗/沉淀三端），仿真只能验证假设不能生成假设。",
    "level_curve_progression":
        "(b) 难度曲线是体验判断：什么时候给压力、什么时候给喘息，无标准答案。",
    "control_scheme_mapping":
        "(b) 键位是人机工效判断，依赖玩家手部姿态与目标平台习惯，需设计论证。",
    "narrative_dialogue_branching":
        "(a) 产出主体是分支剧情与对白文本，属自然语言创作。",
    "quest_tree_builder":
        "(a/b) 主支线任务树既含叙事创作，也含依赖结构设计，两者都需语义判断。",
    "inventory_slot_matrix":
        "(b) 道具属性维度与词条体系是内容设计，不是可推导的数据结构。",
    "drop_rate_rng_table":
        "(b) PRD 伪随机本身是确定公式，但『掉什么、稀有度怎么分层、保底怎么设』是设计判断。",
    "camera_viewport_rules":
        "(b) 跟随阻尼、前瞻量与死区是手感设计，调参目标无法用数值断言定义。",
    "score_combo_multiplier":
        "(b) 连击窗口与倍率曲线是奖励节奏设计，属手感范畴。",
    "boss_phase_transition":
        "(b) 阶段切换的戏剧节奏与可读性是设计判断。",
    "ui_hud_wireframe":
        "(b) HUD 信息层级与视线流是设计判断，虽有可用性原则但无唯一解。",
    "tutorial_stealth_guide":
        "(a) 产出是隐式引导的关卡编排与提示文案，属创作。",
    "accessibility_color_blind":
        "(c) 配色方案是否对三类色觉障碍可辨，需评估结论；建议方案亦为设计产出。",
    # ── Logic 族（3）───────────────────────────────────────────────────
    "hypercasual_ad_monetization":
        "(c) 广告点位密度与首日变现节奏是商业判断，需权衡留存与收入。",
    "wechat_social_viral_loop":
        "(a/b) 裂变路径设计 + 分享卡片文案，两者都需创作与判断。",
    "review_privacy_hardening":
        "(a) 隐私弹窗文案、授权时机与未成年人防沉迷说明，主体是合规文案创作。",
    # ── Rendering 族（2）───────────────────────────────────────────────
    "webgl_shader_pipeline":
        "(a) GLSL 源码由 LLM 撰写；生成后必须经真实编译/渲染验证才得声称可用。",
    "tangent_normal_brdf_shader":
        "(a) 同上：微表面 BRDF 的 GLSL 实现属代码生成，验收依赖真机渲染。",
    # ── Audio 族（1）───────────────────────────────────────────────────
    "adaptive_music_layering":
        "(b) 分层配器与过渡点设计是编曲判断，混音引擎只能执行不能决策。",
    # ── QA 族（4）──────────────────────────────────────────────────────
    "difficulty_kill_ratio_eval":
        "(c) 击杀比与挫败感评估是体验结论，无数值金标准。",
    "telemetry_funnel_analytics":
        "(c) 漏斗数值可确定计算，但归因结论与改进建议需语义判断。",
    "first_principles_structural_audit":
        "(c) 第一性原则解构审查，产出是论证而非可计算断言。",
    "anti_rubber_stamp_veto":
        "(c) 反伪通过与多维审美断言，本质是对『通过』本身的再审查，需判断。",
}

# ── 65 项 B 类：可由确定性算法实现并用数值断言验收 ──────────────────────────
B_SKILLS: Dict[str, str] = {
    # ── Logic 族 ───────────────────────────────────────────────────────
    "state_machine_builder": "状态机是确定的图结构，可用转移表断言验收。",
    "aabb_collision_detection": "纯几何判定，可用已知重叠/分离用例数值断言。",
    "sat_polygon_physics": "分离轴定理有确定输出，可用 MTV 向量断言。",
    "a_star_pathfinding": "寻路有确定最优解，可用路径长度与最短性断言。",
    "behavior_tree_evaluator": "行为树执行序列确定，可用 tick 序列断言。",
    "gravity_jump_parabola": "抛物线与跳跃高度是解析解，可直接数值比对。",
    "spatial_grid_partitioning": "网格分区结果确定，可用候选对数量断言。",
    "object_pool_manager": "池化命中率/分配次数可统计断言。",
    "quadtree_collision": "四叉树查询结果是确定集合，可断言。",
    "lerp_smoothing_math": "插值结果是解析值，可直接数值断言。",
    "grid_tilemap_parser": "瓦片解析是确定的映射，可用往返断言。",
    "raycast_line_of_sight": "射线命中点可解析计算，可断言。",
    "cooldown_timer_queue": "定时器队列是确定调度，可用触发序列断言。",
    "save_state_serializer": "序列化可往返断言 + 哈希一致性。",
    "virtual_joystick_touch": "触摸向量换算是确定数学，可断言。",
    "gamepad_api_handler": "手柄输入映射是确定的状态表，可断言。",
    "floating_combat_text": "飘字轨迹是确定插值，位置可断言。",
    "seed_procedural_dungeon": "同种子必须同地图——确定性可强断言。",
    "dual_engine_subsystem_sandbox": "沙盒嵌套是进程/资源隔离规则，可用规则断言。",
    "patch_first_sandboxing": "补丁作用域是路径规则匹配，可确定断言。",
    "logistics_conveyor_network_solving": "物质守恒与背压可用流量守恒断言。",
    "v8_hidden_class_zero_gc_tuning": "内存布局与分配次数可统计断言。",
    # ── Rendering 族 ───────────────────────────────────────────────────
    "canvas_particle_emitter": "粒子位置/存活数可数值断言。",
    "screen_shake_effect": "震屏偏移是衰减函数，可数值断言。",
    "sprite_animation_sheet": "帧索引与时长是确定序列，可断言。",
    "lighting_bloom_postprocess": "亮度阈值与模糊核确定，可用像素统计断言。",
    "procedural_background_stars": "同种子星图确定，可哈希断言。",
    "shockwave_ring_distort": "环半径随时间确定，可数值断言。",
    "trail_ghost_renderer": "残影采样点确定，可断言。",
    "pixel_art_upscaler": "整倍放大是确定像素映射，可逐像素断言。",
    "svg_path_rasterizer": "栅格化可对比覆盖率断言。",
    "damage_flash_white": "受击闪白是确定时长与颜色插值，可断言。",
    "day_night_color_tint": "色相随时间确定，可数值断言。",
    "radial_progress_cooldown": "环形遮罩角度确定，可数值断言。",
    "canvas_scanline_crt": "扫描线是确定像素图案，可断言。",
    "render_queue_material_batching": "合批结果（DrawCall 折叠率）可统计断言。",
    "frustum_culling_quadtree_spatial": "可见集合确定，可断言。",
    "next_gen_high_poly_sculpting":
        "依赖 Blender 无头雕刻；算法可执行但当前缺少 DCC 工具链，属 NEEDS_RUNTIME_TOOL 子类。",
    "quad_retopology_uv_unwrap":
        "重拓扑与 UV 展开是确定几何算法，但需 Blender 执行，属 NEEDS_RUNTIME_TOOL 子类。",
    "pbr_five_channel_baking":
        "烘焙是确定计算，但需 GPU/烘焙器，属 NEEDS_RUNTIME_TOOL 子类。",
    "auto_rigging_heat_skinning": "蒙皮权重是热传导迭代解，可数值断言。",
    # ── Audio 族 ───────────────────────────────────────────────────────
    "webaudio_retro_synth": "波形可逐样本断言。",
    "white_noise_explosion": "噪声包络可统计断言（RMS 衰减曲线）。",
    "adsr_envelope_shaper": "包络四段参数确定，可数值断言。",
    "arpeggio_generator": "琶音音高序列确定，可断言。",
    "pitch_bend_laser_sfx": "频率下潜曲线确定，可断言。",
    "coin_pickup_bell_chime": "双音阶频率与时长确定，可断言。",
    "jump_spring_whistle": "起音调制曲线确定，可断言。",
    "game_over_jingle_chord": "减七和弦音程确定，可断言。",
    "spatial_stereo_panner": "左右增益确定，可数值断言。",
    # ── QA 族 ──────────────────────────────────────────────────────────
    "headless_input_simulator": "注入事件序列确定，可断言。",
    "fps_stability_auditor": "帧耗时可统计断言（p95/掉帧数）。",
    "memory_leak_probe": "堆快照差值可统计断言。",
    "collision_glitch_detector": "穿墙判定是确定几何检测。",
    "boundary_exploit_tester": "越界判定是确定坐标检测。",
    "audio_silence_detector": "静音判定是 Rms 阈值检测，可断言。",
    "score_overflow_checker": "溢出是确定边界检测。",
    "infinite_loop_watchdog": "超时判定确定。",
    "browser_resize_stress": "重绘次数与布局结果可断言。",
    "cross_browser_api_linter": "API 存在性是确定检测。",
    "cli_headless_probing": "探针协议返回可断言。",
    "pixel_visual_diffing": "像素差分有确定数值。",
    "state_invariants_fuzzing": "不变量断言是布尔判定。",
    "hardware_tier_profiling": "采集数据是确定测量。",
    "engine_subsystem_profiling_hud": "HUD 数据来自确定采集。",
}

# 5 个此前被"文件名相似度"误判为 A 类候选的技能（W3b 已发现语义不符并拒绝注册）。
# 这里正式撤销其 A 类判定，避免 counts() 把它们算进 A_DISCOVERED 充数。
DEMOTED_FROM_A: Dict[str, str] = {
    "arpeggio_generator": "此前自动匹配到 LOD 生成器，语义不符，撤销 A 判定 → B。",
    "object_pool_manager": "此前自动匹配到音频对象池，语义不符，撤销 A 判定 → B。",
    "pbr_five_channel_baking": "此前自动匹配到通用 validator，语义不符，撤销 A 判定 → B。",
    "save_state_serializer": "此前自动匹配到 inspector，语义不符，撤销 A 判定 → B。",
    "webgl_shader_pipeline": "此前自动匹配到 runtime_probe，语义不符，撤销 A 判定 → C（GLSL 生成）。",
}


def apply_classification(registry) -> Dict[str, int]:
    """把分类表写进 registry。返回 {"B": n, "C": n, "demoted_from_a": n, "unknown": [...]}。

    已 REGISTERED 的 A 类不动——真跑通过的东西不因为分类表被改写。
    """
    from core.skill_registry import SkillStatus

    if not registry._skills:
        registry.ingest_from_registry()

    stats = {"B": 0, "C": 0, "demoted_from_a": 0, "unknown": []}

    for sid, reason in B_SKILLS.items():
        sk = registry._skills.get(sid)
        if sk is None:
            stats["unknown"].append(sid)
            continue
        if sk.status == SkillStatus.REGISTERED:
            continue
        if sid in DEMOTED_FROM_A:
            stats["demoted_from_a"] += 1
            sk.notes.append(f"demoted from A: {DEMOTED_FROM_A[sid]}")
            sk.candidate_module = None
            sk.candidate_score = 0.0
        sk.cls = SkillClass.B
        sk.status = SkillStatus.NEEDS_IMPLEMENTATION
        sk.notes.append(f"classified B: {reason}")
        stats["B"] += 1

    for sid, reason in C_SKILLS.items():
        sk = registry._skills.get(sid)
        if sk is None:
            stats["unknown"].append(sid)
            continue
        if sk.status == SkillStatus.REGISTERED:
            continue
        if sid in DEMOTED_FROM_A:
            stats["demoted_from_a"] += 1
            sk.notes.append(f"demoted from A: {DEMOTED_FROM_A[sid]}")
            sk.candidate_module = None
            sk.candidate_score = 0.0
        sk.cls = SkillClass.C
        sk.status = SkillStatus.NEEDS_IMPLEMENTATION
        sk.notes.append(f"classified C: {reason}")
        stats["C"] += 1

    return stats


def unclassified(registry) -> List[str]:
    """返回既不是 A 也没进 B/C 表的 skill_id —— 必须为空，否则就是分类漏项。"""
    return [s.skill_id for s in registry._skills.values() if s.cls == SkillClass.UNIMPLEMENTED]


def verify_table() -> Tuple[bool, List[str]]:
    """自检：B/C 表的 id 必须都存在于 GAME_SKILLS，且不得与彼此重叠。"""
    from core.registry import GAME_SKILLS
    valid = {s["id"] for s in GAME_SKILLS}
    problems: List[str] = []
    for sid in list(B_SKILLS) + list(C_SKILLS):
        if sid not in valid:
            problems.append(f"{sid}: 不在 GAME_SKILLS 中")
    both = set(B_SKILLS) & set(C_SKILLS)
    if both:
        problems.append(f"同时出现在 B 和 C: {sorted(both)}")
    for sid in DEMOTED_FROM_A:
        if sid not in valid:
            problems.append(f"DEMOTED {sid}: 不在 GAME_SKILLS 中")
    return (not problems), problems
