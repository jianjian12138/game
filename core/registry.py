#!/usr/bin/env python3
"""
registry.py: 游戏开发多智能体工作室大典 (Game Studio Registry)
完整注册 82 位细分专家智能体、114 个专项游戏开发技能与 12 个工程生命周期钩子。

纯 Python 3.9+ 标准库实现，零外部依赖。
"""
from typing import Dict, List, Any

# ==================== 1. 82 位专家子代理 (6 大部门) ====================
STUDIO_DEPARTMENTS = {
    "production": {
        "name": "制作与管理部",
        "description": "掌控产品愿景、敏捷排期、本地化与商业化生命周期",
        "agents": [
            {"id": "executive_producer", "name": "总制作人", "role": "产品立项、愿景把控与资源调度"},
            {"id": "project_lead", "name": "项目主管", "role": "里程碑拆解、Sprint 冲刺与进度把控"},
            {"id": "agile_scrum_master", "name": "敏捷教练", "role": "每日站会、阻碍消除与工序流动优化"},
            {"id": "localization_producer", "name": "本地化制作人", "role": "多语言文案与全球区域文化适配"},
            {"id": "liveops_manager", "name": "运营管理专家", "role": "长线运营、活动配置与玩家留存设计"},
            {"id": "monetization_lead", "name": "商业化设计师", "role": "内购/广告设计与心智激励平衡"},
            {"id": "doc_archivist", "name": "文档归档工程师", "role": "全生命周期 GDD 与技术规格书归档"},
            {"id": "vertical_slice_director", "name": "垂直切片总监", "role": "把控四级梯次生产：CPU纯契约 -> 核心循环 -> 战斗物流 -> 最终高精"},
            {"id": "idea_coroner_chief", "name": "点子验尸官首席审计师", "role": "把控精益游戏四要素、单局微循环 ≤30秒与立项生死判定"},
            {"id": "hypercasual_monetization_expert", "name": "超轻爆款商业化专家", "role": "把控一人公司模式、4MB 极限包体与激励视频广告点位契约"},
            {"id": "commercial_readiness_director", "name": "商用就绪与提审合规总监", "role": "把控微信登录与分享裂变、5步新手打点漏斗、Safe-Area与提审隐私合规"}
        ]
    },
    "design": {
        "name": "游戏策划与叙事部",
        "description": "设计核心玩法循环、数值模型、关卡流与沉浸式叙事",
        "agents": [
            {"id": "lead_game_designer", "name": "主策划", "role": "定义核心玩法循环 (Core Gameplay Loop)"},
            {"id": "system_designer", "name": "系统策划", "role": "设计成长体系、背包与界面流转逻辑"},
            {"id": "level_designer", "name": "关卡设计师", "role": "关卡难度曲线、障碍物与地图拓扑设计"},
            {"id": "narrative_designer", "name": "叙事文案", "role": "世界观构建、剧情对白与角色背景设定"},
            {"id": "combat_balancer", "name": "战斗与数值平衡师", "role": "攻防公式、伤害曲线与掉落概率精算"},
            {"id": "ui_ux_designer", "name": "游戏 UI/UX 设计师", "role": "交互动效、视线流引导与按键人机工效"},
            {"id": "quest_designer", "name": "任务设计师", "role": "主支线任务、成就与阶段目标设计"},
            {"id": "accessibility_specialist", "name": "无障碍辅助专家", "role": "色盲模式、字幕与按键自定义"},
            {"id": "tutorial_designer", "name": "新手引导设计", "role": "心流式首关体验与隐式教学雕琢"},
            {"id": "industrial_tech_tree_planner", "name": "工业科技树与经济策划总监", "role": "DAG 科技依赖拓扑、防死锁与全链路采销平衡仿真"}
        ]
    },
    "engineering": {
        "name": "主程与技术工程部",
        "description": "负责主循环架构、物理碰撞、游戏 AI、着色器与跨端移植",
        "agents": [
            {"id": "lead_architect", "name": "首席架构师", "role": "主循环 (Game Loop)、状态机与 ECS 架构"},
            {"id": "gameplay_programmer", "name": "核心玩法程序员", "role": "玩家操控响应、实体行为与按键映射"},
            {"id": "physics_engineer", "name": "物理碰撞工程师", "role": "AABB/SAT 碰撞检测与重力抛物线算法"},
            {"id": "ai_behavior_engineer", "name": "游戏 AI 工程师", "role": "NPC 行为树 (Behavior Tree) 与 A* 寻路"},
            {"id": "graphics_shader_specialist", "name": "渲染着色器专家", "role": "Canvas 2D 硬件加速与 WebGL Shader 管线"},
            {"id": "network_multiplayer_engineer", "name": "网络联机工程师", "role": "WebSocket 状态同步与帧同步"},
            {"id": "tools_pipeline_engineer", "name": "工具管线工程师", "role": "资源打包与自动化构建工具链"},
            {"id": "audio_programmer", "name": "音频程序员", "role": "Web Audio API 原生合成引擎与空间音频"},
            {"id": "performance_optimizer", "name": "性能优化专家", "role": "60fps 稳帧、对象池 (Object Pool) 调优"},
            {"id": "security_anti_cheat", "name": "安全防护工程师", "role": "代码混淆、防篡改与内存反作弊"},
            {"id": "platform_porting_engineer", "name": "跨平台移植工程师", "role": "Web、Desktop 与 Godot 4 引擎导出"},
            {"id": "ground_truth_reverser", "name": "底层源码逆向工程专家", "role": "从原始汇编/Java/C++ 逆向提取离散 Tick、物理常量与渲染规约"},
            {"id": "patch_sandbox_warden", "name": "补丁沙箱卫士", "role": "掌控 Staging 候选隔离区与 Patch-First 作用域审查，防止小修引发雪崩"},
            {"id": "ast_architect_sentinel", "name": "AST 符号架构哨兵", "role": "全工程多语言符号依赖索引、循环检测与级联重构安全护卫"},
            {"id": "netcode_synchronizer", "name": "网络同步与回滚工程师", "role": "高频定频帧同步 (Lockstep) 与增量状态差分网关架构"},
            {"id": "toolchain_automation_mechanic", "name": "工具链无头调度工程师", "role": "自动感知宿主机 Blender/FFmpeg/Godot 环境并执行无头协同与平滑降级"},
            {"id": "logistics_network_architect", "name": "物流管网拓扑首席架构师", "role": "传送带背压队列、三路路由器物质守恒与电网回路求解"},
            {"id": "flow_field_swarm_specialist", "name": "向量场集群寻路专家", "role": "全图势能梯度场构建与千人蜂群毫秒级无碰撞滑行"},
            {"id": "zero_gc_ecs_director", "name": "零GC数据导向性能总监", "role": "TypedArray 扁平连续内存 SoA 实体池，根绝垃圾回收卡顿"},
            {"id": "cpp_engine_architect", "name": "C++工业级游戏引擎首席架构师", "role": "把控场景图、渲染指令队列、材质着色器管线与合批优化"},
            {"id": "v8_performance_systems_engineer", "name": "极客时间系统工程与V8性能总监", "role": "把控零GC内存排布、结构体扁平化、Hidden Class 稳定化与火焰图调优"},
            {"id": "scene_graph_hierarchy_specialist", "name": "场景图层级与变换矩阵专家", "role": "把控父子嵌套变换、局部/全局矩阵懒求值、脏标记链式扩散"},
            {"id": "render_queue_batching_engineer", "name": "渲染队列与动态合批专家", "role": "把控渲染指令封装、材质状态排序、DrawCall 90%折叠合批"},
            {"id": "pbr_material_pipeline_engineer", "name": "次时代 PBR 着色器与光照管线专家", "role": "主导 HDR 环境光照、切线空间法线着色器与微表面双向反射分布函数 (BRDF)"},
            {"id": "lod_streaming_architect", "name": "超大规模场景 LOD 与流式加载架构师", "role": "主导视锥体剔除与屏幕占比距离驱动的 LOD0/LOD1/LOD2 动态切换状态机"}
        ]
    },
    "art": {
        "name": "美术与视觉部",
        "description": "把控视觉调性、2D/3D 资产、粒子特效与光影氛围",
        "agents": [
            {"id": "art_director", "name": "美术总监", "role": "视觉基调、配色大典与艺术风格把控"},
            {"id": "concept_artist", "name": "概念设计师", "role": "场景氛围与角色概念设定图"},
            {"id": "2d_pixel_vector_artist", "name": "2D/矢量美术", "role": "Canvas 矢量绘制、Spritesheet 精灵图生成"},
            {"id": "3d_modeler", "name": "3D 建模师", "role": "三维网格与基础低模拓扑"},
            {"id": "technical_artist", "name": "技术美术 (TA)", "role": "材质着色、骨骼绑定与渲染优化"},
            {"id": "vfx_particle_specialist", "name": "特效与粒子专家", "role": "爆炸、火焰、烟雾与光刃粒子发生器"},
            {"id": "ui_asset_artist", "name": "UI 资产设计师", "role": "血条、弹窗、计分牌与图标绘制"},
            {"id": "lighting_artist", "name": "光影氛围师", "role": "昼夜交替与后处理 Bloom 发光特效"},
            {"id": "visual_diff_auditor", "name": "视觉真理差分审计师", "role": "将实机捕获与原版黄金帧进行像素级色相与边缘差分比对"},
            {"id": "skeletal_anim_director", "name": "骨骼蒙皮动画总监", "role": "把控 3D 骨骼关节树、顶点权重与关键帧动作表现"},
            {"id": "autotile_bitmask_master", "name": "47瓦片地形转角总工", "role": "8 邻域 Blob 47 掩码自动烘焙与城墙地表无缝拼缝"},
            {"id": "next_gen_sculpting_director", "name": "3A 次时代高模雕刻总监", "role": "主导次时代高精几何雕刻生成、微观拓扑形态与曲面置换"},
            {"id": "retopology_uv_master", "name": "次时代四边面重拓扑与 UV 优化师", "role": "将高模无损重拓扑为规范四边面，展开接缝最少、无拉伸的 UV 坐标"},
            {"id": "pbr_texture_baker", "name": "次时代 PBR 材质烘焙专家", "role": "基于高低模法线摄动算法自动烘焙 Albedo/Normal/Roughness/Metallic/AO 五大物理贴图"},
            {"id": "auto_rigging_skinning_ta", "name": "骨骼自动绑定与蒙皮技师", "role": "标准人体/机械关节树自动配准与热传导蒙皮权重计算"},
            {"id": "lod_mesh_budget_auditor", "name": "LOD 分级与渲染预算审计官", "role": "生成 LOD0/LOD1/LOD2 距离阶梯，构建凸包碰撞体，把控显存与 DrawCall"}
        ]
    },
    "audio": {
        "name": "音频与音乐工程部",
        "description": "打造自适应动态配乐、打击音效与程序化合成器",
        "agents": [
            {"id": "audio_director", "name": "音频总监", "role": "全盘声音风格与响度动态平衡"},
            {"id": "music_composer", "name": "游戏配乐师", "role": "复古 8-bit / 现代电子和弦乐谱编排"},
            {"id": "sfx_designer", "name": "音效设计师", "role": "射击、跳跃、金币、碰撞、受击音效"},
            {"id": "voice_specialist", "name": "语音管理师", "role": "角色人声生成与发音时机控制"},
            {"id": "adaptive_audio_specialist", "name": "自适应音乐专家", "role": "根据战斗紧张度动态切换音轨"},
            {"id": "webaudio_synth_engineer", "name": "WebAudio 合成工程师", "role": "纯原生程序化 Web Audio 振荡器管线 (零外部 mp3)"},
            {"id": "adaptive_audio_master", "name": "动态音频大师", "role": "设计四轨垂直自适应状态机、低通滤波与 3D 空间声场"}
        ]
    },
    "qa": {
        "name": "质量工程与测试部",
        "description": "执行自动化无头试玩、视觉穿模自愈与 60fps 性能审计",
        "agents": [
            {"id": "qa_director", "name": "测试总监", "role": "制定测试矩阵与发布验收门禁"},
            {"id": "gameplay_tester", "name": "玩法功能测试员", "role": "全功能交互路径遍历"},
            {"id": "headless_automation_qa", "name": "无头自动化测试专家", "role": "模拟万次随机输入与极值边界试玩"},
            {"id": "performance_profiler", "name": "性能分析师", "role": "实时帧率 (FPS) 采样与掉帧诊断"},
            {"id": "balance_evaluator", "name": "数值可玩性评估师", "role": "评估通关时长与挫败感指数"},
            {"id": "visual_glitch_inspector", "name": "画面缺陷检测专家", "role": "基于 godogen 截屏算法检测穿模与黑屏"},
            {"id": "compatibility_tester", "name": "跨端兼容性审计", "role": "屏幕分辨率与浏览器跨端兼容性测试"},
            {"id": "security_penetrator", "name": "安全渗透专家", "role": "非法数据拦截与边界溢出攻击测试"},
            {"id": "ghost_bug_hunter", "name": "幽灵 Bug 猎犬专家", "role": "设计极端边界用例与不变量断言，排查穿墙隔空打人与竞态覆盖"},
            {"id": "deterministic_solver_expert", "name": "确定性求解专家", "role": "采用 A*、图拓扑与覆盖算法硬性验证关卡可达性与零物流死锁"},
            {"id": "vlm_aesthetic_critic", "name": "VLM 视觉审美评论家", "role": "利用视觉大模型与启发式算法进行构图、调色板与人机工效打分"},
            {"id": "hardware_profiler_expert", "name": "真机性能剖析专家", "role": "千元低端机 GPU/DrawCall/显存预算与长线发热降频审查"},
            {"id": "toxic_red_team_inquisitor", "name": "刻薄对抗式红蓝军审查官", "role": "践行第一性原则与一票否决权，对伪原型/空壳音效/表单UI/橡皮图章进行无情扼杀"}
        ]
    }
}

# ==================== 2. 跨部门专业团队 ====================
# 团队不是新增部门，而是把已有专家、技能、执行器与验收工件绑定为可调度交付单元。
# 其中 next_gen_3d_art_team 是 3D 次时代美术团队的唯一事实来源。
STUDIO_TEAMS = {
    "next_gen_3d_art_team": {
        "id": "next_gen_3d_art_team",
        "name": "3D 次时代美术与资产工程团队",
        "team_type": "cross_department",
        "mission": "负责从高模/拓扑/UV 到 PBR、骨骼、LOD、渲染预算与资产 QA 的可交付 3D 资产闭环",
        "departments": ["art", "engineering", "audio", "qa"],
        "lead_agent": "next_gen_sculpting_director",
        "members": [
            "art_director",
            "3d_modeler",
            "technical_artist",
            "skeletal_anim_director",
            "next_gen_sculpting_director",
            "retopology_uv_master",
            "pbr_texture_baker",
            "auto_rigging_skinning_ta",
            "lod_mesh_budget_auditor",
            "pbr_material_pipeline_engineer",
            "lod_streaming_architect",
            "graphics_shader_specialist",
            "visual_diff_auditor",
            "hardware_profiler_expert",
        ],
        "capabilities": [
            {
                "id": "next_gen_asset_generation",
                "skills": ["next_gen_high_poly_sculpting", "quad_retopology_uv_unwrap"],
                "executors": ["pipeline.asset_3d_bridge:Asset3DBridge"],
                "artifacts": ["asset_manifest", "gltf_asset", "obj_asset"],
                "status": "implemented_procedural_baseline",
            },
            {
                "id": "pbr_texture_baking",
                "skills": ["pbr_five_channel_baking", "tangent_normal_brdf_shader"],
                "executors": ["pipeline.next_gen_3d_pipeline:PBRTextureBaker"],
                "artifacts": ["pbr_channel_manifest", "albedo", "normal", "metallic_roughness", "ao", "emissive"],
                "status": "implemented_procedural_baseline",
            },
            {
                "id": "skeletal_rigging_animation",
                "skills": ["auto_rigging_heat_skinning", "skeletal_skinning_animation"],
                "executors": ["pipeline.skeletal_animation_engine:SkeletalAnimationEngine"],
                "artifacts": ["skeleton_manifest", "skinned_gltf", "animation_clips"],
                "status": "implemented_procedural_baseline",
            },
            {
                "id": "lod_and_render_budget",
                "skills": ["multi_tier_lod_generator", "frustum_culling_quadtree_spatial", "render_queue_material_batching"],
                "executors": ["pipeline.next_gen_3d_pipeline:NextGenMeshBuilder", "pipeline.asset_streaming.lod_generator"],
                "artifacts": ["lod_budget_report", "draw_call_budget", "material_batch_report"],
                "status": "implemented_with_policy_gap",
            },
            {
                "id": "asset_quality_gate",
                "skills": ["hardware_tier_profiling", "pixel_visual_diffing"],
                "executors": ["pipeline.asset_compiler_qa:AssetCompilerQA"],
                "artifacts": ["asset_qa_report", "runtime_asset_smoke_report"],
                "status": "implemented_static_gate",
            },
        ],
        "required_gates": ["asset_schema", "gltf_integrity", "pbr_channels", "skin_weights", "lod_budget", "runtime_asset_smoke"],
        "maturity": {
            "current": "M2_procedural_asset_baseline",
            "next_target": "M3_runtime_verified_3d_assets",
            "production_target": "M4_engine_and_hardware_verified",
        },
    }
}

# ==================== 3. 12 个生命周期 Hooks ====================
LIFECYCLE_HOOKS = [
    {"id": "pre_init", "name": "环境与依赖预检", "phase": "Initialization"},
    {"id": "post_init", "name": "工程脚手架就绪", "phase": "Initialization"},
    {"id": "pre_gdd", "name": "策划前置分析与竞品提炼", "phase": "Design & GDD"},
    {"id": "post_gdd", "name": "GDD 评审与封板确认", "phase": "Design & GDD"},
    {"id": "pre_architecture", "name": "架构师状态机与实体设计", "phase": "Architecture"},
    {"id": "post_architecture", "name": "类契约与接口冻结", "phase": "Architecture"},
    {"id": "pre_code_generation", "name": "代码生成与按键绑定准备", "phase": "Implementation"},
    {"id": "post_code_generation", "name": "核心游戏循环与物理代码装配", "phase": "Implementation"},
    {"id": "pre_asset_synthesis", "name": "粒子特效与音频配置", "phase": "Asset Synthesis"},
    {"id": "post_asset_synthesis", "name": "WebAudio 与 Canvas 资产注入", "phase": "Asset Synthesis"},
    {"id": "pre_qa_audit", "name": "无头试玩与 godogen 视觉自愈", "phase": "QA & Verification"},
    {"id": "post_release", "name": "最终打包交付与服务发布", "phase": "Release"}
]

# ==================== 3. 73 个专项游戏开发 Skills ====================
GAME_SKILLS = [
    # GDD 策划族 (15)
    {"id": "core_loop_design", "category": "GDD", "name": "核心玩法循环设计"},
    {"id": "economy_balance_math", "category": "GDD", "name": "数值经济平衡建模"},
    {"id": "level_curve_progression", "category": "GDD", "name": "关卡难度曲线规划"},
    {"id": "control_scheme_mapping", "category": "GDD", "name": "输入控制与键位映射"},
    {"id": "narrative_dialogue_branching", "category": "GDD", "name": "分支剧情与对白设计"},
    {"id": "quest_tree_builder", "category": "GDD", "name": "主支线任务树生成"},
    {"id": "inventory_slot_matrix", "category": "GDD", "name": "背包网格与道具属性表"},
    {"id": "combat_damage_formula", "category": "GDD", "name": "攻防伤害计算公式"},
    {"id": "drop_rate_rng_table", "category": "GDD", "name": "掉落概率与伪随机发生"},
    {"id": "camera_viewport_rules", "category": "GDD", "name": "摄像机视口跟随规则"},
    {"id": "score_combo_multiplier", "category": "GDD", "name": "得分连击与奖励机制"},
    {"id": "boss_phase_transition", "category": "GDD", "name": "Boss 多阶段变身机制"},
    {"id": "ui_hud_wireframe", "category": "GDD", "name": "HUD 仪表盘线框布局"},
    {"id": "tutorial_stealth_guide", "category": "GDD", "name": "沉浸式新手引导流程"},
    {"id": "accessibility_color_blind", "category": "GDD", "name": "色盲色弱无障碍配色"},

    # 逻辑与物理族 (20)
    {"id": "state_machine_builder", "category": "Logic", "name": "有限状态机 (FSM) 架构"},
    {"id": "aabb_collision_detection", "category": "Logic", "name": "AABB 轴对齐包围盒碰撞"},
    {"id": "sat_polygon_physics", "category": "Logic", "name": "SAT 分离轴定理多边形物理"},
    {"id": "a_star_pathfinding", "category": "Logic", "name": "A* 寻路网格导航算法"},
    {"id": "behavior_tree_evaluator", "category": "Logic", "name": "AI 行为树状态决策"},
    {"id": "gravity_jump_parabola", "category": "Logic", "name": "重力加速度与跳跃抛物线"},
    {"id": "spatial_grid_partitioning", "category": "Logic", "name": "空间网格分区与宽相过滤"},
    {"id": "object_pool_manager", "category": "Logic", "name": "高频实体对象池复用"},
    {"id": "quadtree_collision", "category": "Logic", "name": "四叉树空间索引加速"},
    {"id": "lerp_smoothing_math", "category": "Logic", "name": "平滑插值 (Lerp) 运动"},
    {"id": "bullet_hell_pattern_gen", "category": "Logic", "name": "弹幕花样数学轨迹发生器"},
    {"id": "grid_tilemap_parser", "category": "Logic", "name": "瓦片地图 (Tilemap) 解析"},
    {"id": "raycast_line_of_sight", "category": "Logic", "name": "视线光线投射 (Raycast)"},
    {"id": "cooldown_timer_queue", "category": "Logic", "name": "技能冷却时间队列"},
    {"id": "save_state_serializer", "category": "Logic", "name": "存档数据序列化与还原"},
    {"id": "event_driven_msg_bus", "category": "Logic", "name": "事件驱动观察者总线"},
    {"id": "virtual_joystick_touch", "category": "Logic", "name": "移动端虚拟摇杆触摸转换"},
    {"id": "gamepad_api_handler", "category": "Logic", "name": "手柄原生 Gamepad API 驱动"},
    {"id": "floating_combat_text", "category": "Logic", "name": "飘字暴击伤害发生器"},
    {"id": "seed_procedural_dungeon", "category": "Logic", "name": "随机种子地牢生成算法"},

    # 渲染与着色器族 (15)
    {"id": "canvas_particle_emitter", "category": "Rendering", "name": "Canvas 2D 高性能粒子发射器"},
    {"id": "webgl_shader_pipeline", "category": "Rendering", "name": "WebGL 基础着色器管线"},
    {"id": "screen_shake_effect", "category": "Rendering", "name": "屏幕打击感震屏特效"},
    {"id": "sprite_animation_sheet", "category": "Rendering", "name": "精灵表帧动画播放器"},
    {"id": "lighting_bloom_postprocess", "category": "Rendering", "name": "后处理高光 Bloom 辉光"},
    {"id": "procedural_background_stars", "category": "Rendering", "name": "视差多层星空背景发生器"},
    {"id": "shockwave_ring_distort", "category": "Rendering", "name": "爆炸冲击波环形扭曲"},
    {"id": "trail_ghost_renderer", "category": "Rendering", "name": "高速移动残影渲染"},
    {"id": "pixel_art_upscaler", "category": "Rendering", "name": "像素风整倍无损缩放"},
    {"id": "svg_path_rasterizer", "category": "Rendering", "name": "SVG 矢量图形栅格化"},
    {"id": "damage_flash_white", "category": "Rendering", "name": "受击白色闪烁高亮材质"},
    {"id": "day_night_color_tint", "category": "Rendering", "name": "昼夜颜色渐变色相调节"},
    {"id": "fog_of_war_alpha_mask", "category": "Rendering", "name": "战争迷雾 Alpha 遮罩"},
    {"id": "radial_progress_cooldown", "category": "Rendering", "name": "环形技能冷却遮罩渲染"},
    {"id": "canvas_scanline_crt", "category": "Rendering", "name": "复古 CRT 电视扫描线滤镜"},

    # 音频合成族 (10)
    {"id": "webaudio_retro_synth", "category": "Audio", "name": "WebAudio 原生 8-bit 复古合成器"},
    {"id": "white_noise_explosion", "category": "Audio", "name": "白噪声爆炸与破裂合成"},
    {"id": "adsr_envelope_shaper", "category": "Audio", "name": "ADSR 动态音量包络塑形器"},
    {"id": "arpeggio_generator", "category": "Audio", "name": "多和弦 Arpeggio 琶音发生器"},
    {"id": "adaptive_music_layering", "category": "Audio", "name": "自适应多轨音乐动态混音"},
    {"id": "pitch_bend_laser_sfx", "category": "Audio", "name": "激光射线音调下潜音效"},
    {"id": "coin_pickup_bell_chime", "category": "Audio", "name": "金币获取清脆双音阶音效"},
    {"id": "jump_spring_whistle", "category": "Audio", "name": "跳跃弹簧起音调制"},
    {"id": "game_over_jingle_chord", "category": "Audio", "name": "Game Over 减七和弦悲壮音效"},
    {"id": "spatial_stereo_panner", "category": "Audio", "name": "左右声道空间立体声平移"},

    # QA 自动化族 (13)
    {"id": "headless_input_simulator", "category": "QA", "name": "无头高频随机按键注入器"},
    {"id": "fps_stability_auditor", "category": "QA", "name": "60fps 实时帧率与掉帧审计"},
    {"id": "memory_leak_probe", "category": "QA", "name": "JS Heap 对象池泄漏探针"},
    {"id": "collision_glitch_detector", "category": "QA", "name": "高速穿墙与卡死碰撞检测"},
    {"id": "boundary_exploit_tester", "category": "QA", "name": "地图边界溢出渗透测试"},
    {"id": "visual_frame_diff_auditor", "category": "QA", "name": "godogen 视觉截屏差异比对"},
    {"id": "audio_silence_detector", "category": "QA", "name": "音频管线未触发与静音排查"},
    {"id": "score_overflow_checker", "category": "QA", "name": "计分器整数溢出与负分排查"},
    {"id": "infinite_loop_watchdog", "category": "QA", "name": "主循环卡死与死循环看门狗"},
    {"id": "browser_resize_stress", "category": "QA", "name": "视口动态拉伸与重绘适配测试"},
    {"id": "difficulty_kill_ratio_eval", "category": "QA", "name": "击杀比与挫败感数值模型评估"},
    {"id": "save_load_integrity_test", "category": "QA", "name": "存档读档数据一致性校验"},
    {"id": "cross_browser_api_linter", "category": "QA", "name": "Canvas/WebAudio 跨浏览器兼容校验"},
    {"id": "cli_headless_probing", "category": "QA", "name": "无头探针与按键驱动协议"},
    {"id": "pixel_visual_diffing", "category": "QA", "name": "像素级视觉特征差分比对"},
    {"id": "state_invariants_fuzzing", "category": "QA", "name": "状态不变量与竞态条件模糊测试"},
    {"id": "discrete_tick_physics_freeze", "category": "Logic", "name": "离散时钟与原生常量冻结"},
    {"id": "dual_engine_subsystem_sandbox", "category": "Logic", "name": "双引擎沙盒无缝嵌套机制"},
    {"id": "deterministic_path_solving", "category": "Logic", "name": "确定性地图与拓扑求解"},
    {"id": "patch_first_sandboxing", "category": "Logic", "name": "候选区补丁优先沙箱隔离"},
    {"id": "vertical_slice_milestoning", "category": "GDD", "name": "垂直切片阶梯装配管理"},
    {"id": "evidence_pack_targeted_healing", "category": "QA", "name": "四维证据链靶向自愈"},
    {"id": "procedural_scene_scripting", "category": "Rendering", "name": "程序化场景代码生成与引擎调度"},
    {"id": "skeletal_skinning_animation", "category": "Rendering", "name": "3D 骨骼关节绑定与关键帧动画插值"},
    {"id": "adaptive_multitrack_audio", "category": "Audio", "name": "多轨垂直自适应混音与低通滤波 DSP"},
    {"id": "ast_symbol_dependency_graph", "category": "Logic", "name": "跨文件多语言 AST 符号图谱与级联重构"},
    {"id": "lockstep_multiplayer_netcode", "category": "Logic", "name": "定频帧同步、状态差分与网络抖动模拟"},
    {"id": "vlm_aesthetic_ux_critique", "category": "QA", "name": "多模态视觉审美、色彩调和与 UX 人机工效门禁"},
    {"id": "hardware_tier_profiling", "category": "QA", "name": "典型硬件阶梯 DrawCall、显存与发热降频剖析"},
    {"id": "idea_coroner_autopsy", "category": "GDD", "name": "极速想法验尸与微原型构建"},
    {"id": "headless_toolchain_orchestration", "category": "Logic", "name": "本地专业工具无头调度与平滑降级"},
    {"id": "hypercasual_ad_monetization", "category": "Logic", "name": "超轻交互 ≤30秒变现收敛与广告契约"},
    {"id": "wechat_social_viral_loop", "category": "Logic", "name": "微信开放数据域与动态带参分享卡片裂变"},
    {"id": "telemetry_funnel_analytics", "category": "QA", "name": "5步新手引导留存与广告转化率埋点分析"},
    {"id": "review_privacy_hardening", "category": "Logic", "name": "微信隐私授权弹窗与未成年人防沉迷合规加固"},
    {"id": "adversarial_red_team_inquisition", "category": "QA", "name": "对抗式红队攻防审查与一票否决门禁"},
    {"id": "first_principles_structural_audit", "category": "QA", "name": "第一性原则结构与语义解构审查"},
    {"id": "anti_rubber_stamp_veto", "category": "QA", "name": "反伪通过与真实多维审美断言校验"},
    {"id": "logistics_conveyor_network_solving", "category": "Logic", "name": "传送带队列排队与物质守恒背压求解"},
    {"id": "autotile_47_bitmask_compilation", "category": "Rendering", "name": "8 邻域 Blob 47 自动转角瓦片烘焙"},
    {"id": "flow_field_swarm_navigation", "category": "Logic", "name": "全局势能向量场与千人同屏滑行寻路"},
    {"id": "data_oriented_typedarray_ecs", "category": "Logic", "name": "连续内存 TypedArray 零 GC 实体池"},
    {"id": "tech_tree_dag_economic_balance", "category": "GDD", "name": "有向无环图科技树拓扑与工业供需平衡"},
    {"id": "scene_graph_transform_hierarchy", "category": "Rendering", "name": "场景图父子层级变换矩阵与脏标记懒计算"},
    {"id": "render_queue_material_batching", "category": "Rendering", "name": "渲染指令队列、多通道排序与动态材质合批"},
    {"id": "v8_hidden_class_zero_gc_tuning", "category": "Logic", "name": "V8隐藏类稳定化与 TypedArray 零GC热循环"},
    {"id": "frustum_culling_quadtree_spatial", "category": "Rendering", "name": "摄像机视锥裁剪与空间索引加速"},
    {"id": "engine_subsystem_profiling_hud", "category": "QA", "name": "实时DrawCall/帧耗时/合批率/GC开销全景剖析HUD"},
    {"id": "next_gen_high_poly_sculpting", "category": "Rendering", "name": "次时代高保真多边形雕刻与拓扑"},
    {"id": "quad_retopology_uv_unwrap", "category": "Rendering", "name": "四边面重拓扑与接缝无损 UV 展开"},
    {"id": "pbr_five_channel_baking", "category": "Rendering", "name": "PBR 物理着色五通道贴图烘焙"},
    {"id": "auto_rigging_heat_skinning", "category": "Rendering", "name": "骨骼自动装配与热传导蒙皮权重计算"},
    {"id": "multi_tier_lod_generator", "category": "Rendering", "name": "LOD0/1/2 多级细节减面与距离平滑过渡"},
    {"id": "tangent_normal_brdf_shader", "category": "Rendering", "name": "切线空间法线与微表面双向反射分布函数"}
]

def get_all_agents() -> List[Dict[str, Any]]:
    agents = []
    for dept_id, dept in STUDIO_DEPARTMENTS.items():
        for a in dept["agents"]:
            a_copy = dict(a)
            a_copy["department_id"] = dept_id
            a_copy["department_name"] = dept["name"]
            agents.append(a_copy)
    return agents

def get_all_teams() -> List[Dict[str, Any]]:
    """返回跨部门团队清单，供 CLI/HTTP/MCP 与工作流编排统一使用。"""
    return [dict(team) for team in STUDIO_TEAMS.values()]


def get_team(team_id: str) -> Dict[str, Any]:
    """按 ID 返回团队定义；未知团队返回空字典。"""
    team = STUDIO_TEAMS.get(team_id)
    return dict(team) if team else {}


def get_team_execution_plan(team_id: str, run_id: str, target: str = "webgl") -> Dict[str, Any]:
    """将团队元数据展开成一次可审计的执行计划。"""
    team = get_team(team_id)
    if not team:
        raise KeyError(f"Unknown studio team: {team_id}")
    return {
        "schema_version": 1,
        "team_id": team["id"],
        "team_name": team["name"],
        "run_id": run_id,
        "target": target,
        "lead_agent": team["lead_agent"],
        "active_agents": team["members"],
        "capabilities": team["capabilities"],
        "required_gates": team["required_gates"],
        "maturity": team["maturity"],
        "execution_mode": "procedural_baseline_with_runtime_verification",
    }


def get_stats() -> Dict[str, int]:
    return {
        "departments_count": len(STUDIO_DEPARTMENTS),
        "teams_count": len(STUDIO_TEAMS),
        "agents_count": len(get_all_agents()),
        "skills_count": len(GAME_SKILLS),
        "hooks_count": len(LIFECYCLE_HOOKS)
    }
