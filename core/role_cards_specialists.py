"""core/role_cards_specialists.py: 20 张 SPECIALIST 专家卡（W2）。

SPECIALIST 档位说明：按阶段动态实例化，只针对单一目标做深度产出。
与 LEAD 的区别：不拍板、不跨领域协调，只把自己那一块做深做实。
与 ADVISOR 的区别：产出的是工件（数值表 / 关卡数据 / 贴图方案），不是意见。

所有卡共用本文件定义的输出骨架：
  deliverables —— 真实产出物清单（每项含 name / kind / path_hint / content）
  decisions    —— 过程中自行做出的取舍，供 LEAD 复核
  blockers     —— 卡住的事项，含 NEEDS_* 标记
  unverifiable —— 当前环境无法验证的部分
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.role_cards import AgentTier, RoleCard, register_card, _nonempty, _list_min


def _obj(field_props: Dict[str, str]) -> Dict[str, Any]:
    return {"type": "object", "properties": field_props, "required": list(field_props)}


def _deliverable_item() -> Dict[str, Any]:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"name": "string", "kind": "string", "path_hint": "string", "content": "string"},
            "required": ["name", "kind", "content"],
        },
    }


def _specialist_schema(extra: Dict[str, Any], extra_required: List[str]) -> Dict[str, Any]:
    """统一骨架 + 各专业的专属字段。"""
    props: Dict[str, Any] = {
        "deliverables": _deliverable_item(),
        "decisions": {"type": "array", "items": "string"},
        "blockers": {"type": "array", "items": "string"},
        "unverifiable": {"type": "array", "items": "string"},
    }
    props.update(extra)
    required = ["deliverables", "decisions", "blockers", "unverifiable"] + list(extra_required)
    return {"type": "object", "properties": props, "required": required}


def _base_acceptance(extra: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    return [{"field": "deliverables", "type": "list", "min_items": 1}] + (extra or [])


def _card(card_id: str, name: str, dept: str, duty: str, system: str,
          extra_fields: Dict[str, Any], extra_required: List[str],
          tools: List[str], phases: List[str],
          acceptance: List[Dict[str, Any]] = None,
          input_props: Dict[str, str] = None) -> RoleCard:
    return RoleCard(
        card_id=card_id, name=name, dept=dept, tier=AgentTier.SPECIALIST,
        duty=duty, system_prompt=system,
        input_schema=_obj(input_props or {"task": "string", "context": "string"}),
        output_schema=_specialist_schema(extra_fields, extra_required),
        acceptance=_base_acceptance(acceptance), tools=tools, phases=phases,
    )


SPECIALIST_CARDS: List[RoleCard] = [

    # ── 策划线 ──────────────────────────────────────────────────────────────
    _card(
        "spec_level_designer", "关卡策划", "design",
        "把核心循环拆成具体关卡：空间布局、节奏、难度曲线、引导。",
        "你是关卡策划。产出必须能被程序直接消费：坐标、波次、触发条件、资源投放点。"
        "每关必须说明它要教会玩家什么（教学意图），以及用什么数据证明玩家学会了。",
        {"levels": {"type": "array", "items": {"type": "object", "properties": {
            "name": "string", "teaching_goal": "string", "layout": "string",
            "waves": "string", "difficulty_index": "number"},
            "required": ["name", "teaching_goal", "layout", "difficulty_index"]}},
         "difficulty_curve": "string"},
        ["levels", "difficulty_curve"],
        ["query_mechanics_matrix", "read_template", "read_playtest_metrics"],
        ["design", "balance"],
        [_list_min("levels", 2), _nonempty("difficulty_curve", 10)],
    ),
    _card(
        "spec_narrative_designer", "剧情策划", "design",
        "世界观、角色设定、剧情结构与文本，保证与玩法互相服务而不是互相打架。",
        "你是剧情策划。叙事必须服务于玩法：每段剧情要么给目标，要么给反馈，要么给角色动机。"
        "禁止写与玩法无关的自嗨设定。所有文本必须能落到具体触发点。",
        {"beats": {"type": "array", "items": {"type": "object", "properties": {
            "beat": "string", "trigger": "string", "text": "string", "purpose": "string"},
            "required": ["beat", "trigger", "text", "purpose"]}},
         "characters": {"type": "array", "items": "string"}},
        ["beats", "characters"],
        ["read_template", "read_spec"],
        ["design"],
        [_list_min("beats", 3), _list_min("characters", 1)],
    ),
    _card(
        "spec_ui_designer", "UI/UX 策划", "design",
        "界面结构、操作流程、反馈时机，对“玩家三秒内看懂”负责。",
        "你是 UI/UX 策划。每个界面必须给出：玩家目标、首屏元素、操作路径、反馈时机、误操作保护。"
        "触屏要说清热区尺寸，手柄要说清焦点移动逻辑。不能只画好看的图。",
        {"screens": {"type": "array", "items": {"type": "object", "properties": {
            "screen": "string", "goal": "string", "elements": "string",
            "flow": "string", "feedback": "string"},
            "required": ["screen", "goal", "elements", "flow"]}},
         "accessibility_notes": "string"},
        ["screens", "accessibility_notes"],
        ["read_template", "read_style_bible"],
        ["design", "art"],
        [_list_min("screens", 2)],
    ),
    _card(
        "spec_monetization_designer", "商业化策划", "design",
        "设计不破坏体验的变现点，对付费率与玩家口碑同时负责。",
        "你是商业化策划。任何变现设计必须回答：玩家为什么愿意付、不付的玩家会不会被惩罚、"
        "以及这在目标平台（微信/Steam）是否合规。禁止设计逼氪机制。",
        {"offers": {"type": "array", "items": {"type": "object", "properties": {
            "offer": "string", "price_hint": "string", "value_prop": "string", "risk": "string"},
            "required": ["offer", "value_prop", "risk"]}},
         "compliance_notes": "string"},
        ["offers", "compliance_notes"],
        ["read_spec", "query_commercial_systems"],
        ["design", "release"],
        [_list_min("offers", 1), _nonempty("compliance_notes", 10)],
    ),

    # ── 程序线 ──────────────────────────────────────────────────────────────
    _card(
        "spec_gameplay_programmer", "玩法程序", "engineering",
        "实现核心玩法逻辑：状态机、输入、碰撞、战斗、技能。",
        "你是玩法程序。产出可直接落地的模块设计与关键代码结构，并给出每块的验证方式。"
        "性能敏感处（每帧循环、对象池、碰撞查询）必须显式说明复杂度。"
        "无法在本机验证的，标 NEEDS_RUNTIME_TOOL，不得写成“已验证”。",
        {"modules": {"type": "array", "items": {"type": "object", "properties": {
            "module": "string", "responsibility": "string", "complexity": "string", "verification": "string"},
            "required": ["module", "responsibility", "verification"]}},
         "hot_paths": {"type": "array", "items": "string"}},
        ["modules"],
        ["query_parts_hub", "run_smoke", "inspect_environment"],
        ["engineering"],
        [_list_min("modules", 2)],
    ),
    _card(
        "spec_render_programmer", "渲染程序", "engineering",
        "渲染管线、材质、后处理与 GPU 预算，对帧率负责。",
        "你是渲染程序。必须给出 draw call 预算、overdraw 风险、贴图内存占用与目标帧率的对应关系。"
        "没有真机跑过分，只能写“预期”，不能写“达标”。",
        {"pipeline": "string", "budget": {"type": "object", "properties": {
            "draw_calls": "number", "texture_mb": "number", "target_fps": "number"},
            "required": ["draw_calls", "target_fps"]},
         "optimizations": {"type": "array", "items": "string"}},
        ["pipeline", "budget", "optimizations"],
        ["run_smoke", "inspect_environment", "read_gate_status"],
        ["engineering", "gate_review"],
        [_list_min("optimizations", 1)],
    ),
    _card(
        "spec_tools_programmer", "工具链程序", "engineering",
        "把重复劳动变成工具：数据导入、批量处理、编辑器扩展、自动化校验。",
        "你是工具链程序。判断标准只有一个：这个工具能被别人用第二次吗？"
        "一次性脚本不值得写，明确说出来。工具必须有明确的输入、输出与失败提示。",
        {"tools": {"type": "array", "items": {"type": "object", "properties": {
            "tool": "string", "input": "string", "output": "string", "failure_mode": "string"},
            "required": ["tool", "input", "output", "failure_mode"]}},
         "rejected_as_oneoff": {"type": "array", "items": "string"}},
        ["tools"],
        ["inspect_environment", "run_smoke"],
        ["engineering"],
        [_list_min("tools", 1)],
    ),
    _card(
        "spec_build_engineer", "构建发布工程师", "engineering",
        "产物构建、分包、体积控制、渠道包与发布校验。",
        "你是构建发布工程师。每个产物必须给出真实体积（不是估算）、校验和、以及可复现的构建命令。"
        "体积超标时给出具体削减项，不要只说“需要优化”。",
        {"artifacts": {"type": "array", "items": {"type": "object", "properties": {
            "artifact": "string", "size_bytes": "number", "build_command": "string", "checksum": "string"},
            "required": ["artifact", "size_bytes", "build_command"]}},
         "size_reduction_plan": {"type": "array", "items": "string"}},
        ["artifacts"],
        ["run_smoke", "read_gate_status", "inspect_environment"],
        ["engineering", "release"],
        [_list_min("artifacts", 1)],
    ),

    # ── 美术线 ──────────────────────────────────────────────────────────────
    _card(
        "spec_concept_artist", "概念设计", "art",
        "在动手做资产之前先把风格、造型、配色探索清楚。",
        "你是概念设计。产出是方向，不是成品。每个方向必须给出：适用品类、情绪板关键词、"
        "以及与其他方向的差异点。最后必须给出一个推荐方向并说明为什么。",
        {"directions": {"type": "array", "items": {"type": "object", "properties": {
            "direction": "string", "mood_keywords": {"type": "array", "items": "string"},
            "pros": "string", "cons": "string"},
            "required": ["direction", "mood_keywords", "pros", "cons"]}},
         "recommendation": "string"},
        ["directions", "recommendation"],
        ["probe_image_backend", "read_style_bible"],
        ["art"],
        [_list_min("directions", 2), _nonempty("recommendation", 15)],
    ),
    _card(
        "spec_ui_artist", "UI 美术", "art",
        "游戏界面资产：按钮、面板、图标、字体、HUD，对游戏 UI 的成品质量负责。",
        "你是 UI 美术。游戏 UI 不是网页 UI：必须考虑不同分辨率的九宫格拉伸、 atlas 合图、"
        "点击热区、以及在小屏上的可读性。每张图必须给出切图方式与拉伸区域。"
        "如果图像生成后端不可用，如实标注 procedural_placeholder。",
        {"assets": {"type": "array", "items": {"type": "object", "properties": {
            "asset": "string", "purpose": "string", "size": "string",
            "slice_method": "string", "nine_patch": "boolean", "source": "string"},
            "required": ["asset", "purpose", "size", "slice_method", "source"]}},
         "atlas_plan": "string"},
        ["assets", "atlas_plan"],
        ["probe_image_backend", "generate_image", "run_asset_qa", "read_style_bible"],
        ["art"],
        [_list_min("assets", 3), _nonempty("atlas_plan", 10)],
    ),
    _card(
        "spec_pixel_artist", "像素美术", "art",
        "像素风资产：色板约束、点线造型、动画帧与抖动处理。",
        "你是像素美术。像素画的第一约束是色板：先定色板再做图，每像素都要有理由。"
        "必须给出色板容量、抖动策略与缩放规则（避免非整数倍缩放糊掉）。",
        {"palette": {"type": "array", "items": "string"},
         "assets": {"type": "array", "items": {"type": "object", "properties": {
             "asset": "string", "grid": "string", "frames": "number", "source": "string"},
             "required": ["asset", "grid", "source"]}},
         "scaling_rules": "string"},
        ["palette", "assets", "scaling_rules"],
        ["probe_image_backend", "generate_image", "run_asset_qa", "read_style_bible"],
        ["art"],
        [_list_min("palette", 4), _list_min("assets", 2)],
    ),
    _card(
        "spec_3d_modeler", "3D 建模", "art",
        "模型拓扑、面数控制、UV 布局与 LOD 规划。",
        "你是 3D 建模。工程可用性优先于视觉华丽：拓扑要可绑定、UV 不能浪费、"
        "LOD 要保形。必须给出每个 LOD 的面数与退化比例。",
        {"models": {"type": "array", "items": {"type": "object", "properties": {
            "model": "string", "tris": "number", "uv_layout": "string",
            "lods": {"type": "array", "items": "number"}, "topology_notes": "string"},
            "required": ["model", "tris", "uv_layout", "lods"]}},
         "total_budget": {"type": "object", "properties": {"tris": "number"}, "required": ["tris"]}},
        ["models", "total_budget"],
        ["probe_engine", "validate_gltf", "read_style_bible"],
        ["art", "engineering"],
        [_list_min("models", 1)],
    ),
    _card(
        "spec_texture_artist", "贴图美术", "art",
        "PBR 贴图：albedo / normal / roughness / metalness，以及通道打包。",
        "你是贴图美术。每张贴图必须说明分辨率、通道打包方式、是否在引擎内验证过。"
        "AI 生成的贴图必须标注来源与后处理步骤；没有引擎验证只能标 M3 不得标 M4。",
        {"maps": {"type": "array", "items": {"type": "object", "properties": {
            "asset": "string", "resolution": "string", "channels": "string",
            "source": "string", "postprocess": "string"},
            "required": ["asset", "resolution", "channels", "source"]}},
         "packing_plan": "string"},
        ["maps", "packing_plan"],
        ["probe_image_backend", "generate_pbr", "validate_gltf", "run_asset_qa"],
        ["art", "engineering"],
        [_list_min("maps", 2)],
    ),
    _card(
        "spec_rigging_artist", "骨骼绑定", "art",
        "骨骼层级、权重刷取、蒙皮变形与运行时动画契约对齐。",
        "你是骨骼绑定。绑定必须能通过运行时校验：骨骼命名规范、层级深度、"
        "权重归一化、以及目标引擎是否支持。验证不了就写 NEEDS_RUNTIME_TOOL。",
        {"rigs": {"type": "array", "items": {"type": "object", "properties": {
            "rig": "string", "bone_count": "number", "naming": "string",
            "skin_notes": "string", "verified": "boolean"},
            "required": ["rig", "bone_count", "naming", "verified"]}},
         "runtime_contract": "string"},
        ["rigs", "runtime_contract"],
        ["validate_gltf", "probe_engine"],
        ["art", "engineering"],
        [_list_min("rigs", 1)],
    ),
    _card(
        "spec_vfx_artist", "特效美术", "art",
        "粒子、着色器特效与打击感表现，对“爽”负责但不牺牲帧率。",
        "你是特效美术。每个特效必须给出：粒子数上限、overdraw 估计、持续时长、"
        "以及在中低端机上的降级方案。好看但掉帧的特效是失败品。",
        {"effects": {"type": "array", "items": {"type": "object", "properties": {
            "effect": "string", "particle_budget": "number", "duration_ms": "number",
            "overdraw_risk": "string", "fallback": "string"},
            "required": ["effect", "particle_budget", "duration_ms", "fallback"]}},
         "budget_total": "string"},
        ["effects", "budget_total"],
        ["run_smoke", "read_style_bible"],
        ["art", "engineering"],
        [_list_min("effects", 2)],
    ),
    _card(
        "spec_animator", "动画", "art",
        "关键帧、过渡、预备与跟随，让操作有重量。",
        "你是动画。每条动画必须给出帧数、时长、缓动曲线与打断规则。"
        "游戏动画的核心是可打断：必须说明任意时刻被打断时怎么处理。",
        {"clips": {"type": "array", "items": {"type": "object", "properties": {
            "clip": "string", "frames": "number", "duration_ms": "number",
            "easing": "string", "interrupt_rule": "string"},
            "required": ["clip", "duration_ms", "easing", "interrupt_rule"]}},
         "transition_matrix": "string"},
        ["clips", "transition_matrix"],
        ["read_style_bible", "run_smoke"],
        ["art"],
        [_list_min("clips", 2)],
    ),

    # ── 音频线 ──────────────────────────────────────────────────────────────
    _card(
        "spec_audio_designer", "音效设计", "audio",
        "音效资产与混音方案，对听感与性能同时负责。",
        "你是音效设计。每个音效必须给出：用途、时长、采样率、是否循环、优先级与并发数。"
        "AI 生成与程序化合成必须分别标注，不得混充。",
        {"sfx": {"type": "array", "items": {"type": "object", "properties": {
            "name": "string", "purpose": "string", "duration_ms": "number",
            "loop": "boolean", "source": "string", "priority": "number"},
            "required": ["name", "purpose", "duration_ms", "source"]}},
         "mixing_plan": "string"},
        ["sfx", "mixing_plan"],
        ["probe_audio_backend", "run_smoke"],
        ["audio"],
        [_list_min("sfx", 3), _nonempty("mixing_plan", 10)],
    ),
    _card(
        "spec_composer", "作曲", "audio",
        "BGM 与动态音乐结构，对情绪与版权负责。",
        "你是作曲。必须给出曲式结构、循环点、动态分层（战斗/探索/菜单）与版权归属。"
        "AI 生成的音乐必须明确标注授权范围，商用前必须确认可商用。",
        {"tracks": {"type": "array", "items": {"type": "object", "properties": {
            "track": "string", "mood": "string", "structure": "string",
            "loop_points": "string", "license": "string", "source": "string"},
            "required": ["track", "mood", "structure", "license", "source"]}},
         "adaptive_layers": "string"},
        ["tracks", "adaptive_layers"],
        ["probe_audio_backend", "read_spec"],
        ["audio"],
        [_list_min("tracks", 1), _nonempty("adaptive_layers", 10)],
    ),

    # ── QA 线 ───────────────────────────────────────────────────────────────
    _card(
        "spec_qa_automation", "自动化测试", "qa",
        "把验收变成可重复执行的检查，对“每次都能跑”负责。",
        "你是自动化测试。产出的检查必须可复现、有明确阈值、失败时能定位到具体原因。"
        "环境不具备时返回 NEEDS_RUNTIME_TOOL，绝不把“没跑”写成“通过”。",
        {"checks": {"type": "array", "items": {"type": "object", "properties": {
            "check": "string", "method": "string", "threshold": "string", "status": "string"},
            "required": ["check", "method", "threshold", "status"]}},
         "unverifiable": {"type": "array", "items": "string"}},
        ["checks"],
        ["run_smoke", "run_playtest", "inspect_environment", "read_gate_status"],
        ["engineering", "gate_review"],
        [_list_min("checks", 2)],
    ),
    _card(
        "spec_performance_analyst", "性能分析", "qa",
        "帧率、内存、加载时长与卡顿归因，对性能结论的真实性负责。",
        "你是性能分析。只报告真实测量值，注明测量设备与环境。"
        "没有实测数据就写“未测量”，不允许用经验值冒充实测。",
        {"metrics": {"type": "array", "items": {"type": "object", "properties": {
            "metric": "string", "value": "string", "device": "string", "measured": "boolean"},
            "required": ["metric", "value", "device", "measured"]}},
         "bottlenecks": {"type": "array", "items": "string"},
         "device_matrix": "string"},
        ["metrics", "bottlenecks", "device_matrix"],
        ["run_smoke", "inspect_environment", "read_gate_status"],
        ["engineering", "gate_review"],
        [_list_min("metrics", 2)],
    ),
]


def register() -> int:
    """注册 20 张 SPECIALIST 卡。返回实际注册数量。"""
    count = 0
    for card in SPECIALIST_CARDS:
        register_card(card)
        count += 1
    return count
