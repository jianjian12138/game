#!/usr/bin/env python3
"""
core/prompt_template_engine.py: 专家级游戏开发 Prompt 模板库 (Agent v5.0)

为各游戏开发场景提供结构化、高质量的 Prompt 模板：
  - CodeGenPrompt   : 游戏代码生成（HTML5/GDScript/Rust）
  - GDDPrompt       : 游戏设计文档生成
  - ReviewPrompt    : 代码质量审查
  - HealPrompt      : 基于 EvidencePack 的 Bug 修复
  - ScenePrompt     : 程序化场景规格生成
  - NarrativePrompt : 世界观与叙事生成
  - BalancePrompt   : 数值平衡分析

所有 Prompt 均遵循：
  - 角色设定（System Prompt 分离）
  - 约束条件明确化
  - 输出格式规范化
  - Few-shot 示例（关键场景）
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class RenderedPrompt:
    """渲染后的 Prompt 对象"""
    system: str
    user: str
    template_name: str
    variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        return {"system": self.system, "user": self.user}

    def combined(self) -> str:
        """合并为单字符串（用于不支持 system prompt 的场景）"""
        if self.system:
            return f"[ROLE]\n{self.system}\n\n[TASK]\n{self.user}"
        return self.user


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CodeGenPrompt — 游戏代码生成
# ═══════════════════════════════════════════════════════════════════════════════
class CodeGenPrompt:
    SYSTEM = """你是一位顶级全栈游戏开发工程师，精通 HTML5 Canvas、Rust/macroquad、GDScript 和 Web 游戏架构。
你的代码必须满足：
1. 完整可运行 —— 输出的代码直接保存即可在浏览器/引擎中启动，无需任何额外配置
2. 60fps 稳帧 —— 所有渲染逻辑走 requestAnimationFrame，避免 setInterval 
3. 游戏循环完整 —— 必须包含 update(dt) + render() 分离设计
4. 碰撞与物理正确 —— AABB 精确碰撞，无穿模
5. 代码简洁可读 —— 有清晰注释，模块化结构
6. 只输出代码，不输出任何解释文字"""

    @staticmethod
    def for_html5(title: str, genre: str, rules: str = "",
                  width: int = 800, height: int = 600,
                  extra_constraints: str = "") -> RenderedPrompt:
        """HTML5 Canvas 游戏生成"""
        user = f"""请生成一个完整的 HTML5 Canvas 游戏：

**游戏标题**: {title}
**游戏类型**: {genre}
**分辨率**: {width}×{height}
**特殊规则/需求**:
{rules or "无特殊要求，实现标准游戏逻辑"}

{f"**额外约束**: {extra_constraints}" if extra_constraints else ""}

**必须包含的要素**:
- <!DOCTYPE html> 完整 HTML 结构
- <canvas> 元素 id="gameCanvas"
- 键盘/鼠标输入处理
- 开始界面 + 游戏主循环 + 游戏结束界面
- 得分/生命显示
- 所有资产程序化生成（矩形/圆形/多边形），不依赖外部图片

**输出**: 仅输出完整的单文件 HTML 代码，从 <!DOCTYPE html> 开始"""

        return RenderedPrompt(
            system=CodeGenPrompt.SYSTEM,
            user=user,
            template_name="codegen_html5",
            variables={"title": title, "genre": genre, "rules": rules}
        )

    @staticmethod
    def for_rust_macroquad(title: str, genre: str, rules: str = "",
                            extra_constraints: str = "") -> RenderedPrompt:
        """Rust + macroquad 游戏生成"""
        user = f"""请生成一个完整的 Rust + macroquad 游戏项目：

**游戏标题**: {title}
**游戏类型**: {genre}
**特殊规则**:
{rules or "无特殊要求，实现标准游戏逻辑"}

{f"**额外约束**: {extra_constraints}" if extra_constraints else ""}

**代码要求**:
- 使用 macroquad 0.4.x API
- main.rs 包含完整游戏主循环
- 使用 ECS 风格组织组件
- 物理碰撞使用 AABB
- 所有图形程序化绘制（draw_rectangle/draw_circle 等）
- 包含 Cargo.toml 依赖配置

**输出格式**:
```
// === Cargo.toml ===
[package]
...

// === src/main.rs ===
use macroquad::prelude::*;
...
```"""

        return RenderedPrompt(
            system=CodeGenPrompt.SYSTEM,
            user=user,
            template_name="codegen_rust",
            variables={"title": title, "genre": genre}
        )

    @staticmethod
    def for_gdscript(title: str, genre: str, rules: str = "") -> RenderedPrompt:
        """GDScript/Godot 4 游戏生成"""
        user = f"""请生成一个完整的 Godot 4 游戏脚本集：

**游戏标题**: {title}
**游戏类型**: {genre}
**特殊规则**:
{rules or "无特殊要求，实现标准游戏逻辑"}

**代码要求**:
- 使用 Godot 4.x GDScript 语法
- 包含主场景 (Main.gd)、玩家 (Player.gd)、UI (HUD.gd)
- 使用 @export 暴露可调参数
- 遵循信号 (Signal) 驱动架构
- 包含场景树结构说明注释

**输出格式**:
为每个脚本使用独立代码块，标注文件路径"""

        return RenderedPrompt(
            system=CodeGenPrompt.SYSTEM,
            user=user,
            template_name="codegen_gdscript",
            variables={"title": title, "genre": genre}
        )

    @staticmethod
    def retry_with_feedback(original_prompt: RenderedPrompt, violations: List[str],
                             attempt: int = 1) -> RenderedPrompt:
        """验证失败后携带错误信息重试"""
        feedback = "\n".join(f"  - {v}" for v in violations)
        new_user = f"""{original_prompt.user}

---
**[自动重试 #{attempt}] 上次生成存在以下问题，请修复：**
{feedback}

请重新生成，确保以上所有问题均已解决。"""

        return RenderedPrompt(
            system=original_prompt.system,
            user=new_user,
            template_name=f"{original_prompt.template_name}_retry{attempt}",
            variables=original_prompt.variables
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GDDPrompt — 游戏设计文档生成
# ═══════════════════════════════════════════════════════════════════════════════
class GDDPrompt:
    SYSTEM = """你是一位拥有 15 年经验的 3A 游戏设计总监，精通游戏设计文档（GDD）撰写标准。
你的 GDD 必须：
1. 结构完整 —— 覆盖核心玩法、数值体系、关卡流、叙事、UI 等全章节
2. 可执行性 —— 每个系统描述都足够具体，程序员可以直接实现
3. 数值有依据 —— 关键参数给出推导过程或参考依据
4. 使用 Markdown 格式，清晰分层"""

    @staticmethod
    def full_gdd(title: str, genre: str, concept: str,
                  target_audience: str = "休闲/核心玩家",
                  platform: str = "Web / PC") -> RenderedPrompt:
        """完整 GDD 生成"""
        user = f"""请为以下游戏生成完整的游戏设计文档（GDD）：

**游戏名称**: {title}
**游戏类型**: {genre}
**核心概念**: {concept}
**目标受众**: {target_audience}
**目标平台**: {platform}

**GDD 必须包含以下章节**:

# 1. 执行摘要（Executive Summary）
- 一句话定位
- 核心差异化卖点
- 市场定位

# 2. 核心玩法循环（Core Gameplay Loop）
- 主循环图（文字版流程图）
- 微循环（每局操作节奏）
- 宏循环（长期成长驱动）

# 3. 游戏机制详规（Mechanics Specification）
- 角色/实体系统
- 核心动词（玩家能做什么）
- 输赢条件
- 规则边界

# 4. 数值体系（Numerical Design）
- 基础数值公式
- 成长曲线（等级/关卡）
- 平衡参数表

# 5. 关卡设计纲领（Level Design Brief）
- 难度曲线规划
- 关卡类型分类
- 首关（Tutorial）设计

# 6. UI/UX 规范（Interface Design）
- 主界面布局
- HUD 元素清单
- 操作映射

# 7. 音频风格指南（Audio Brief）
- 音乐风格参考
- 关键 SFX 清单

# 8. 技术约束（Technical Constraints）
- 目标帧率与性能预算
- 资源预算
- 技术栈选型理由

请生成完整的 Markdown GDD 文档："""

        return RenderedPrompt(
            system=GDDPrompt.SYSTEM,
            user=user,
            template_name="gdd_full",
            variables={"title": title, "genre": genre, "concept": concept}
        )

    @staticmethod
    def adr(title: str, decision_id: str, problem: str, options: List[str],
             chosen: str, rationale: str) -> RenderedPrompt:
        """架构决策记录 (ADR)"""
        options_text = "\n".join(f"  - {o}" for o in options)
        user = f"""请生成一份架构决策记录（ADR）：

**项目**: {title}
**决策编号**: {decision_id}
**待解决问题**: {problem}
**备选方案**:
{options_text}
**选择方案**: {chosen}
**决策理由**: {rationale}

请输出标准 ADR Markdown 格式，包含：背景、决策、后果、执行计划"""

        return RenderedPrompt(
            system=GDDPrompt.SYSTEM,
            user=user,
            template_name="adr",
            variables={"decision_id": decision_id}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ReviewPrompt — 代码质量审查
# ═══════════════════════════════════════════════════════════════════════════════
class ReviewPrompt:
    SYSTEM = """你是一位严格的游戏代码审查专家，精通性能优化、游戏循环设计和跨平台兼容性。
审查报告必须：
1. 定位具体问题（引用代码行号或代码片段）
2. 区分严重程度：CRITICAL / WARNING / SUGGESTION
3. 给出具体修复方案，而非泛泛建议
4. 输出 JSON 格式结构化报告"""

    @staticmethod
    def review_game_code(code: str, language: str = "html5",
                          focus_areas: Optional[List[str]] = None) -> RenderedPrompt:
        areas = focus_areas or ["性能", "游戏循环", "碰撞检测", "内存管理", "用户体验"]
        areas_text = "、".join(areas)
        user = f"""请对以下 {language.upper()} 游戏代码进行专业审查：

**重点审查领域**: {areas_text}

**代码**:
```{language}
{code[:6000]}{'...[已截断]' if len(code) > 6000 else ''}
```

**输出 JSON 格式**:
```json
{{
  "overall_score": 0-100,
  "summary": "总体评价",
  "issues": [
    {{
      "severity": "CRITICAL|WARNING|SUGGESTION",
      "category": "性能|游戏循环|碰撞|内存|UX",
      "description": "问题描述",
      "location": "代码位置描述",
      "fix": "具体修复方案"
    }}
  ],
  "passed_checks": ["通过的检查项"],
  "is_fully_qualified": true/false
}}
```"""

        return RenderedPrompt(
            system=ReviewPrompt.SYSTEM,
            user=user,
            template_name="review_code",
            variables={"language": language}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. HealPrompt — 基于 EvidencePack 的 Bug 精准修复
# ═══════════════════════════════════════════════════════════════════════════════
class HealPrompt:
    SYSTEM = """你是一位专注游戏 Bug 修复的外科手术级工程师。
你必须：
1. 基于提供的四维证据（视觉/运行时/日志/玩家反馈）精准定位根因
2. 生成最小化侵入性的 Patch（只改动必要代码，不引入新功能）
3. 输出 unified diff 格式的补丁，可直接 git apply
4. 说明修复理由和潜在副作用"""

    @staticmethod
    def from_evidence_pack(evidence_pack: Dict[str, Any],
                            source_code: str = "") -> RenderedPrompt:
        """基于 EvidencePack 生成修复 Prompt"""
        visual = "\n".join(f"  - {v}" for v in evidence_pack.get("visual_findings", []))
        runtime = "\n".join(f"  - {v}" for v in evidence_pack.get("runtime_errors", []))
        logs = "\n".join(f"  - {v}" for v in evidence_pack.get("log_anomalies", []))
        feedback = "\n".join(f"  - {v}" for v in evidence_pack.get("player_feedback", []))

        code_block = f"""
**当前源码**（部分）:
```
{source_code[:4000]}{'...[已截断]' if len(source_code) > 4000 else ''}
```""" if source_code else ""

        user = f"""请根据以下四维证据生成精准 Bug 修复方案：

**视觉异常**:
{visual or "  无"}

**运行时错误**:
{runtime or "  无"}

**日志异常**:
{logs or "  无"}

**玩家反馈**:
{feedback or "  无"}

{code_block}

**输出格式**:
```json
{{
  "root_cause": "根因分析",
  "affected_components": ["受影响的模块"],
  "patch": "unified diff 格式补丁，或具体修改代码",
  "fix_rationale": "修复理由",
  "side_effects": "潜在副作用说明",
  "verification_steps": ["验证步骤"]
}}
```"""

        return RenderedPrompt(
            system=HealPrompt.SYSTEM,
            user=user,
            template_name="heal_from_evidence",
            variables={"evidence_pack": evidence_pack}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ScenePrompt — 程序化场景生成
# ═══════════════════════════════════════════════════════════════════════════════
class ScenePrompt:
    SYSTEM = """你是一位专业的程序化内容生成（PCG）工程师，精通地图生成算法和游戏关卡设计。
生成的场景规格必须：
1. 数值精确 —— 所有坐标、大小、数量均为具体数字
2. 可重现 —— 提供随机种子和生成算法描述
3. 可玩性验证 —— 确保有明确的通路和挑战节奏
4. 输出 JSON 结构化规格"""

    @staticmethod
    def generate_scene(theme: str, width: int = 2048, height: int = 1024,
                        difficulty: str = "medium",
                        game_genre: str = "strategy") -> RenderedPrompt:
        user = f"""请为以下游戏场景生成程序化地图规格：

**场景主题**: {theme}
**地图尺寸**: {width} × {height} 像素
**难度**: {difficulty}
**游戏类型**: {game_genre}

**输出 JSON 格式**:
```json
{{
  "seed": 随机整数,
  "theme": "{theme}",
  "dimensions": {{"width": {width}, "height": {height}}},
  "terrain_layers": [
    {{"type": "地形类型", "coverage": 0-1, "pattern": "算法名"}}
  ],
  "spawn_points": [
    {{"id": "player_start", "x": 0, "y": 0, "radius": 50}}
  ],
  "resource_nodes": [
    {{"type": "资源类型", "count": 数量, "cluster_radius": 像素}}
  ],
  "obstacles": [
    {{"type": "障碍类型", "density": 0-1, "placement_rule": "规则描述"}}
  ],
  "objectives": [
    {{"id": "目标ID", "type": "类型", "position": {{"x": 0, "y": 0}}}}
  ],
  "difficulty_modifiers": {{"enemy_count": 0, "resource_multiplier": 1.0}},
  "generation_algorithm": "算法描述",
  "validation": {{"has_clear_path": true, "min_path_width": 64}}
}}
```"""

        return RenderedPrompt(
            system=ScenePrompt.SYSTEM,
            user=user,
            template_name="scene_generate",
            variables={"theme": theme, "width": width, "height": height}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. NarrativePrompt — 世界观与叙事生成
# ═══════════════════════════════════════════════════════════════════════════════
class NarrativePrompt:
    SYSTEM = """你是一位游戏叙事总监，精通沉浸式世界观构建和机制咬合型叙事设计。
你的叙事必须：
1. 与核心机制强耦合 —— 世界观解释玩法存在的合理性
2. 角色有动机 —— 每个关键角色有清晰的欲望和恐惧
3. 信息分层 —— 表层文本/中层暗示/深层秘密三层结构
4. 可游戏化 —— 叙事元素可转化为游戏事件和任务"""

    @staticmethod
    def lore_extraction(raw_text: str, title: str,
                         game_genre: str = "action") -> RenderedPrompt:
        """从原始文本提取游戏化世界观"""
        user = f"""请将以下原始背景文本提炼为游戏化世界观设定集：

**游戏标题**: {title}
**游戏类型**: {game_genre}

**原始背景文本**:
{raw_text[:3000]}

**输出格式（Markdown）**:

## 世界观核心设定
## 主要阵营与势力
## 核心冲突（可游戏化的对立关系）
## 玩家角色定位
## 关键 NPC 档案（每个含：姓名/动机/与玩家关系）
## 游戏化世界事件（可作为任务/关卡触发器）
## 设定与机制咬合点（世界观如何解释核心玩法）"""

        return RenderedPrompt(
            system=NarrativePrompt.SYSTEM,
            user=user,
            template_name="narrative_lore",
            variables={"title": title}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 7. BalancePrompt — 数值平衡分析
# ═══════════════════════════════════════════════════════════════════════════════
class BalancePrompt:
    SYSTEM = """你是一位游戏数值策划专家，擅长用数学建模验证游戏平衡性。
你必须：
1. 给出具体的数值公式和推导过程
2. 识别数值陷阱（碾压区间/死区/负向反馈循环）
3. 提供可操作的调整建议（具体到参数数值）
4. 使用表格清晰呈现数值对比"""

    @staticmethod
    def analyze_balance(game_config: Dict[str, Any],
                         focus: str = "全面平衡分析") -> RenderedPrompt:
        import json as _json
        user = f"""请对以下游戏数值配置进行平衡性分析：

**分析重点**: {focus}

**游戏数值配置**:
```json
{_json.dumps(game_config, ensure_ascii=False, indent=2)[:3000]}
```

**输出要求**:
1. 数值合理性评分（0-100）
2. 识别的平衡问题清单
3. 推荐的调整方案（具体数值）
4. 关键公式验证"""

        return RenderedPrompt(
            system=BalancePrompt.SYSTEM,
            user=user,
            template_name="balance_analyze",
            variables={"focus": focus}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 8. BalanceSimulationPrompt — 蒙特卡洛宏观数值仿真与自适应调优
# ═══════════════════════════════════════════════════════════════════════════════
class BalanceSimulationPrompt:
    SYSTEM = """你是一位资深游戏经济与战斗数值总监（曾在多款千万级流水卡牌与商业手游担任数值架构师）。
你精通蒙特卡洛抽卡模拟、马尔可夫链资源流动、通货膨胀调谐与心流挫败点平滑算法。
你的建议必须具备可落地性：
1. 给出根因剖析（如保底梯度偏软/产销倒挂/关卡断崖）
2. 给出具体的修改常数（如 将基础爆率从 0.006 调整为 0.008）
3. 输出结构化参数补丁字典"""

    @staticmethod
    def from_simulation_report(report: Dict[str, Any], game_title: str = "商业游戏") -> RenderedPrompt:
        gacha = report.get("gacha_simulation", {})
        econ = report.get("economy_simulation", {})
        flow = report.get("flow_channel_stress", {})
        user = f"""请分析以下《{game_title}》的百万次数值与经济仿真报告，并给出自适应调参方案：

**1. 抽卡蒙特卡洛数据**:
- 期望抽数: {gacha.get('expected_pulls_to_up_ssr')} 抽
- P50中位数: {gacha.get('p50_median_pulls')} 抽 / P90大倒霉抽数: {gacha.get('p90_unlucky_pulls')} 抽
- 硬保底触发率: {gacha.get('hard_pity_trigger_rate_pct')}%
- 诊断: {gacha.get('suggestion')}

**2. 30天经济通胀走势**:
- 宏观通胀倍率: {econ.get('inflation_ratio')}x
- 经济健康状态: {econ.get('economic_health')}
- 诊断: {econ.get('diagnosis')}

**3. 关卡心流与卡点检测**:
- 关卡通过率走势: {flow.get('pass_rates_trend')}
- 严重卡点: {flow.get('detected_chokepoints')}

**要求**:
请输出 Markdown 分析报告，并在末尾提供可直接应用的 ```json 数值调优配置表补丁。"""
        return RenderedPrompt(
            system=BalanceSimulationPrompt.SYSTEM,
            user=user,
            template_name="balance.simulation",
            variables={"title": game_title}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 注册表：模板名 → 类映射
# ═══════════════════════════════════════════════════════════════════════════════
PROMPT_REGISTRY = {
    "codegen": CodeGenPrompt,
    "gdd":     GDDPrompt,
    "review":  ReviewPrompt,
    "heal":    HealPrompt,
    "scene":   ScenePrompt,
    "narrative": NarrativePrompt,
    "balance": BalancePrompt,
    "balance_simulation": BalanceSimulationPrompt,
}


def list_templates() -> Dict[str, str]:
    """列出所有可用模板"""
    return {
        "codegen.html5":       "HTML5 Canvas 游戏代码生成",
        "codegen.rust":        "Rust/macroquad 游戏代码生成",
        "codegen.gdscript":    "Godot 4 GDScript 游戏生成",
        "gdd.full":            "完整 GDD 游戏设计文档",
        "gdd.adr":             "架构决策记录 (ADR)",
        "review.code":         "游戏代码质量审查",
        "heal.evidence":       "基于 EvidencePack 的 Bug 修复",
        "scene.generate":      "程序化场景地图生成",
        "narrative.lore":      "世界观与叙事提炼",
        "balance.analyze":     "数值平衡性分析",
    }


if __name__ == "__main__":
    # 快速验证：打印各模板预览
    print("=== Prompt Template Engine — 模板预览 ===\n")
    for name, desc in list_templates().items():
        print(f"  📝 {name:<28} {desc}")

    print("\n=== CodeGenPrompt HTML5 示例 ===")
    p = CodeGenPrompt.for_html5("太空射击", "2D射击", "玩家控制飞船左右移动，子弹自动向上发射")
    print(f"System: {p.system[:80]}...")
    print(f"User:   {p.user[:200]}...")
