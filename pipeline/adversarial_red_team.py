#!/usr/bin/env python3
"""
pipeline/adversarial_red_team.py: 毒舌红军对抗审讯中枢 (Hostile Red-Team Inquisitor)

坚决杜绝“既当裁判员又当运动员”与“形式主义关键词搜索放水”！
红军核心天职:
1. 预设代码是有罪的、预设交付物是劣质玩具 Demo、以挑刺与否决为唯一 KPI。
2. 设立 5 大一票否决硬门禁 (Hard Vetoes):
   - VETO_GEOMETRIC_LAZINESS: 几何画圆偷懒一票否决 (严禁用裸 ctx.arc 画圆充当角色与怪物)
   - VETO_WEB_FORM_UI: 扁平网页表单味一票否决 (严禁无 3D 物理按压反馈的扁平按钮与裸露系统 Emoji)
   - VETO_EMPTY_AUDIO_BGM: 哑巴无背景节拍一票否决 (严禁只有两声单音哔哔、无持续 BGM 时钟调度)
   - VETO_RUBBER_STAMP_FRAUD: 欺骗作弊一票否决 (严禁用未使用的伪变量欺骗审查、或无出口死锁)
   - VETO_MONETIZATION_DEADEND: 商业死胡同否决 (严禁无真实奖励回调的广告桩或缺少合规忠告)
3. 输出客观、不留情面的《红军对抗挑刺裁决书 (Red-Team Hostile Indictment)》。
"""

import os
import sys
import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# -----------------------------------------------------------------------------
# 毒舌红军审讯官 (RedTeamInquisitor)
# -----------------------------------------------------------------------------
class RedTeamInquisitor:
    """残酷毒舌红军对抗审讯官"""

    @classmethod
    def indict_game_code(cls, html_or_js: str, title: str = "目标游戏") -> Dict[str, Any]:
        """对游戏前端源码实施全面残酷对抗审讯"""
        indictments = []
        veto_hits = []
        penalties = 0

        # =====================================================================
        # 1. 探针一: 几何画圆偷懒审查 (VETO_GEOMETRIC_LAZINESS)
        # 检查是否直接用单个 ctx.arc 画圆充当主角或怪物，缺乏肢体、朝向、装甲或服饰
        # =====================================================================
        has_draw_player = bool(re.search(r'function\s+drawPlayer|const\s+drawPlayer\s*=', html_or_js))
        has_draw_bug_or_enemy = bool(re.search(r'function\s+draw(Bug|Enemy|Supervisor|Boss)|const\s+draw\w+\s*=', html_or_js))

        # 检查是否仅用简单的 ctx.arc 充当角色绘制核心
        pure_arc_regex = re.compile(r'ctx\.beginPath\(\);\s*ctx\.arc\([^)]+\);\s*ctx\.fill\(\);', re.DOTALL)
        pure_arcs = pure_arc_regex.findall(html_or_js)

        # 检查是否有高阶复合图元 (带圆角矩形、多边形路径、肢体偏移或朝向翻转)
        has_squash_and_stretch = bool("Math.sin" in html_or_js and ("walkCycle" in html_or_js or "bounce" in html_or_js))
        has_facing_flip = bool("ctx.scale(" in html_or_js or "scale(-1" in html_or_js or "facingRight" in html_or_js)
        has_composite_limbs = bool("roundRect" in html_or_js or "fillRect" in html_or_js or "ellipse" in html_or_js)

        if pure_arcs and (not has_draw_player or not has_composite_limbs):
            veto_hits.append("VETO_GEOMETRIC_LAZINESS")
            indictments.append("【致命否决】角色/怪物涉嫌用极简几何圆圈糊弄！缺乏肢体结构、骨骼迈步与服装装甲，依然是大学生 Demo 水准！")
            penalties += 35
        elif not has_squash_and_stretch or not has_facing_flip:
            indictments.append("【严重扣分】角色缺乏方向翻转 (FlipX) 或缺少行走时挤压拉伸 (Squash & Stretch) 弹性动画，动作生硬！")
            penalties += 15

        # =====================================================================
        # 2. 探针二: 网页表单味与按键物理反馈审查 (VETO_WEB_FORM_UI)
        # 检查按钮是否具备 3D 物理按压下沉行程、是否有实体游戏质感
        # =====================================================================
        has_button_active_displacement = bool(
            re.search(r':active\s*\{[^}]*translateY\(\s*[2-6]px\s*\)', html_or_js) or
            re.search(r'btn-game[^}]+:active', html_or_js) or
            re.search(r'box-shadow:\s*0\s+[1-3]px\s+0', html_or_js)
        )
        has_game_3d_buttons = bool("btn-game" in html_or_js or "box-shadow: 0 6px 0" in html_or_js or "box-shadow: 0 7px 0" in html_or_js)
        has_bottom_dock = bool("bottom-dock" in html_or_js or "dock-item" in html_or_js or "tab-view" in html_or_js)

        # 检查是否充斥廉价扁平网页按钮
        has_flat_web_buttons = bool(re.search(r'\.btn\s*\{[^}]*background:\s*#[0-9a-fA-F]{6};[^}]*border:\s*none', html_or_js)) and not has_game_3d_buttons

        if has_flat_web_buttons or not has_button_active_displacement:
            veto_hits.append("VETO_WEB_FORM_UI")
            indictments.append("【致命否决】UI 充满浓烈网页表单味！按键缺乏 3D 厚度下沉与实体手柄行程阻尼，像填问卷表单而非商业手游！")
            penalties += 30

        if not has_bottom_dock:
            indictments.append("【体验扣分】缺乏商业小游戏标配底栏导航 (Dock/TabBar)，所有界面生硬垂直堆叠！")
            penalties += 15

        # =====================================================================
        # 3. 探针三: 哑巴无背景音乐审查 (VETO_EMPTY_AUDIO_BGM)
        # 检查是否有基于时钟的持续背景音乐驱动，还是只有两声单音哔哔
        # =====================================================================
        has_scheduled_bgm = bool(
            re.search(r'(setInterval|setTimeout|AudioContext\.currentTime)[^}]+(tickBgm|stepBgm|bassNotes|kick|snare)', html_or_js, re.DOTALL) or
            ("AudioEngine" in html_or_js and "startBgm" in html_or_js and "bassNotes" in html_or_js)
        )
        has_audio_api = bool("AudioContext" in html_or_js or "webkitAudioContext" in html_or_js)

        if not has_audio_api:
            veto_hits.append("VETO_EMPTY_AUDIO_BGM")
            indictments.append("【致命否决】完全缺乏 WebAudio 声音引擎，属于无声哑巴程序！")
            penalties += 40
        elif not has_scheduled_bgm:
            veto_hits.append("VETO_EMPTY_AUDIO_BGM")
            indictments.append("【致命否决】仅有偶尔触发的单音音效，缺乏 120BPM 持续驱动肾上腺素的动态背景音乐 (BGM)！")
            penalties += 30

        # =====================================================================
        # 4. 探针四: 欺诈变量与橡皮图章死锁审查 (VETO_RUBBER_STAMP_FRAUD)
        # 检查是否有声明了却根本没有被调用的假对象/假变量试图糊弄检查
        # =====================================================================
        # 检查是否有假 SPRITE_MAP
        if "const SPRITE_MAP = {}" in html_or_js and "SPRITE_MAP[" not in html_or_js:
            veto_hits.append("VETO_RUBBER_STAMP_FRAUD")
            indictments.append("【欺诈否决】检测到声明了空的 SPRITE_MAP 却从未在渲染中使用，涉嫌恶意欺骗关键词审查！")
            penalties += 40

        # 检查是否存在未闭合或永远无法通关的死逻辑
        has_gameover_or_win = bool("showGameOver" in html_or_js or "triggerPlayerDeath" in html_or_js)
        if not has_gameover_or_win:
            veto_hits.append("VETO_RUBBER_STAMP_FRAUD")
            indictments.append("【致命否决】缺少胜负与死亡状态机闭环，玩家进入游戏后将无限困于死局！")
            penalties += 30

        # =====================================================================
        # 5. 探针五: 商业化断路与合规审查 (VETO_MONETIZATION_DEADEND)
        # 检查是否有真实的广告回调发放与国家健康游戏忠告
        # =====================================================================
        has_healthy_advice = "抵制不良游戏，拒绝盗版游戏" in html_or_js
        has_reward_callbacks = bool(
            re.search(r'(showRewardAd|trackAdAction|btnWatchReviveAd|btnWatchDoubleAd)[^}]+(onRewarded|gold\s*\+=|hp\s*=|hasRevived\s*=)', html_or_js)
        )

        if not has_healthy_advice:
            veto_hits.append("VETO_MONETIZATION_DEADEND")
            indictments.append("【合规否决】缺少国家健康游戏忠告 48 字声明，提审微信必被驳回！")
            penalties += 25

        if not has_reward_callbacks:
            veto_hits.append("VETO_MONETIZATION_DEADEND")
            indictments.append("【商业否决】广告观看后没有真实游戏内道具/复活发放闭环，属于断路伪广告！")
            penalties += 25

        # =====================================================================
        # 6. 探针六: C++ 工业游戏引擎架构与合批审查 (VETO_ENGINE_ARCH_DEFICIENCY)
        # 针对工业级标杆项目，强制检查场景图、动态合批、视锥裁剪与 Profiler HUD
        # =====================================================================
        is_industrial_target = "industrial" in title.lower() or "engine" in title.lower() or "mindustry" in title.lower()
        if is_industrial_target:
            has_engine_transform = bool("TransformNode" in html_or_js or "worldMatrix" in html_or_js or "localMatrix" in html_or_js)
            has_render_batcher = bool("BatchRenderer" in html_or_js or "RenderCommand" in html_or_js or "RenderQueue" in html_or_js)
            has_profiler_hud = bool("EngineProfilerHUD" in html_or_js or "prof-fps" in html_or_js or "drawCalls" in html_or_js)
            has_frustum_culling = bool("culled" in html_or_js.lower() or "cull" in html_or_js.lower() or "viewport" in html_or_js.lower())

            if not has_engine_transform:
                veto_hits.append("VETO_ENGINE_ARCH_DEFICIENCY")
                indictments.append("【引擎架构否决】工业级游戏缺失 TransformNode 场景图父子层级变换，依然用散落变量计算坐标！")
                penalties += 35

            if not has_render_batcher:
                veto_hits.append("VETO_ENGINE_ARCH_DEFICIENCY")
                indictments.append("【引擎架构否决】工业级游戏缺失 BatchRenderer 渲染指令队列与动态合批，随处裸调 ctx 绘制！")
                penalties += 35

            if not has_profiler_hud:
                veto_hits.append("VETO_ENGINE_ARCH_DEFICIENCY")
                indictments.append("【引擎架构否决】工业级游戏缺失 EngineProfilerHUD 全景运行时分析器，黑盒运行缺乏透明可观测性！")
                penalties += 25

            if not has_frustum_culling:
                veto_hits.append("VETO_ENGINE_ARCH_DEFICIENCY")
                indictments.append("【引擎架构否决】工业级游戏缺失视锥与视口裁剪算法 (Frustum Culling)，视野外实体未做剔除！")
                penalties += 20

        # =====================================================================
        # 6. 探针六: 半成品原型一票否决审查 (VETO_SEMI_FINISHED_PROTOTYPE)
        # 严查代码中是否残留 Math.hypot 热路径开方、生产环境 alert() 阻塞弹窗等半成品特征
        # =====================================================================
        has_hypot_call = bool(re.search(r'Math\.hypot\(', html_or_js))
        has_alert_call = bool(re.search(r'\balert\(', html_or_js))

        if has_hypot_call:
            veto_hits.append("VETO_SEMI_FINISHED_PROTOTYPE")
            indictments.append("【半成品一票否决】代码中残留 Math.hypot() 调用！违背 V8 零开方与 60FPS 帧预算工业标准！")
            penalties += 35

        if has_alert_call:
            veto_hits.append("VETO_SEMI_FINISHED_PROTOTYPE")
            indictments.append("【半成品一票否决】生产代码中包含阻塞式 alert() 弹窗！违背现代游戏平滑 Toast 交互标准！")
            penalties += 35

        # =====================================================================
        # 综合裁决 (Verdict Calculation)
        # 只要触发任何一项 VETO，分数直接封顶在 45 分，判定绝不姑息！
        # =====================================================================
        raw_score = max(0, 100 - penalties)
        if veto_hits:
            final_score = min(45, raw_score)
            verdict = "REJECTED_UNFIT_FOR_RELEASE"
        elif final_score := raw_score:
            verdict = "PASSED_WITH_RED_TEAM_APPROVAL" if final_score >= 80 else "NEEDS_HEAVY_REWORK"

        return {
            "title": title,
            "verdict": verdict,
            "final_score": final_score,
            "is_release_blocked": (verdict != "PASSED_WITH_RED_TEAM_APPROVAL"),
            "veto_count": len(veto_hits),
            "veto_hits": veto_hits,
            "indictments": indictments,
            "first_principles_audit": {
                "visual_truth": "PASS" if "VETO_GEOMETRIC_LAZINESS" not in veto_hits else "FAIL_PRIMITIVE",
                "ui_ergonomics": "PASS" if "VETO_WEB_FORM_UI" not in veto_hits else "FAIL_WEB_FORM",
                "acoustic_immersion": "PASS" if "VETO_EMPTY_AUDIO_BGM" not in veto_hits else "FAIL_SILENT",
                "logic_integrity": "PASS" if "VETO_RUBBER_STAMP_FRAUD" not in veto_hits else "FAIL_FRAUD",
                "commercial_contract": "PASS" if "VETO_MONETIZATION_DEADEND" not in veto_hits else "FAIL_DEADEND",
                "non_semi_finished": "PASS" if "VETO_SEMI_FINISHED_PROTOTYPE" not in veto_hits else "FAIL_SEMI_FINISHED"
            }
        }

    @classmethod
    def indict_file(cls, file_path: str) -> Dict[str, Any]:
        p = Path(file_path)
        if not p.exists():
            return {
                "title": p.name,
                "verdict": "REJECTED_UNFIT_FOR_RELEASE",
                "final_score": 0,
                "overall_score": 0,
                "is_release_blocked": True,
                "veto_count": 1,
                "veto_hits": ["FILE_NOT_FOUND"],
                "hard_vetoes_triggered": [{"id": "FILE_NOT_FOUND", "name": "文件不存在", "detail": f"无法读取目标文件: {file_path}"}],
                "indictments": [f"【文件不存在】无法读取目标文件: {file_path}"],
                "brutal_feedback": [f"【文件不存在】无法读取目标文件: {file_path}"],
                "pillars_breakdown": {},
                "first_principles_audit": {}
            }
        content = p.read_text(encoding="utf-8", errors="ignore")
        return cls.indict_game_code(content, title=p.name)

    @classmethod
    def audit_game(cls, target_path: str) -> Dict[str, Any]:
        """顶层门面方法：对目标游戏执行第一性原则审查与对抗式审讯"""
        raw = cls.indict_file(target_path)
        
        # 组装结构化五大支柱状态
        veto_set = set(raw.get("veto_hits", []))
        hard_veto_meta = {
            "VETO_GEOMETRIC_LAZINESS": ("裸几何画圆偷懒否决", "角色/怪物缺乏复合肢体与动画绘制，用几何圈充当游戏"),
            "VETO_WEB_FORM_UI": ("扁平网页表单UI否决", "按键无 3D 位移反馈，缺少游戏级圆角与光影阶梯"),
            "VETO_EMPTY_AUDIO_BGM": ("哑巴无背景音乐否决", "缺少持续 BGM 合成时钟与音阶序列调度器"),
            "VETO_RUBBER_STAMP_FRAUD": ("形式主义欺骗否决", "存在死循环、无出口代码或未使用的伪变量"),
            "VETO_MONETIZATION_DEADEND": ("商业死胡同否决", "广告契约无真实闭环回调或缺少 48 字健康忠告合规"),
            "VETO_ENGINE_ARCH_DEFICIENCY": ("C++引擎架构缺失否决", "工业级项目缺失 TransformNode 场景图、BatchRenderer 动态合批、视锥裁剪或 Profiler HUD")
        }

        hard_vetoes_triggered = []
        for v in raw.get("veto_hits", []):
            name, desc = hard_veto_meta.get(v, (v, "命中硬性违规条款"))
            hard_vetoes_triggered.append({"id": v, "name": name, "detail": desc})

        pillars = {
            "visual_truth": {
                "name": "视觉真理 (非裸圈复合绘制)",
                "max": 20,
                "score": 0 if "VETO_GEOMETRIC_LAZINESS" in veto_set else 20,
                "verdict": "FAIL" if "VETO_GEOMETRIC_LAZINESS" in veto_set else "PASS"
            },
            "ui_tactility": {
                "name": "触觉工效 (3D下陷与手势安全区)",
                "max": 20,
                "score": 0 if "VETO_WEB_FORM_UI" in veto_set else 20,
                "verdict": "FAIL" if "VETO_WEB_FORM_UI" in veto_set else "PASS"
            },
            "acoustic_synth": {
                "name": "听觉节拍 (原生WebAudio BGM驱动)",
                "max": 20,
                "score": 0 if "VETO_EMPTY_AUDIO_BGM" in veto_set else 20,
                "verdict": "FAIL" if "VETO_EMPTY_AUDIO_BGM" in veto_set else "PASS"
            },
            "logic_completeness": {
                "name": "逻辑闭环 (零伪变量与真实肉鸽选择)",
                "max": 20,
                "score": 0 if "VETO_RUBBER_STAMP_FRAUD" in veto_set else 20,
                "verdict": "FAIL" if "VETO_RUBBER_STAMP_FRAUD" in veto_set else "PASS"
            },
            "monetization_readiness": {
                "name": "商业合规 (三大广告闭环与合规忠告)",
                "max": 20,
                "score": 0 if "VETO_MONETIZATION_DEADEND" in veto_set else 20,
                "verdict": "FAIL" if "VETO_MONETIZATION_DEADEND" in veto_set else "PASS"
            }
        }

        return {
            "title": raw.get("title", Path(target_path).name),
            "target_path": str(target_path),
            "verdict": raw.get("verdict"),
            "overall_score": raw.get("final_score", 0),
            "final_score": raw.get("final_score", 0),
            "is_release_blocked": raw.get("is_release_blocked", True),
            "hard_vetoes_triggered": hard_vetoes_triggered,
            "pillars_breakdown": pillars,
            "brutal_feedback": raw.get("indictments", []),
            "indictments": raw.get("indictments", [])
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        target = sys.argv[1]
        print(f"=== 正在运行毒舌红军对抗审讯中枢: {target} ===")
        res = RedTeamInquisitor.indict_file(target)
        print(f"\n[审讯结果]: 判定={res['verdict']}, 得分={res['final_score']}")
        print(f"命中否决项 ({len(res['veto_hits'])} 项): {res['veto_hits']}")
        if res['indictments']:
            for ind in res['indictments']:
                print(f"  ❌ {ind}")
        else:
            print("  🎉 0 否决通过！全指标符合工业游戏标准！")
        print(f"第一性原则维度评分: {res.get('first_principles_audit', {})}")
        sys.exit(0 if not res['is_release_blocked'] else 1)

    print("=== 正在运行毒舌红军对抗审讯中枢 (RedTeamInquisitor) 自检 ===")
    
    # 1. 负向反例测试: 喂给红军一个圆圈糊弄的垃圾代码
    bad_code = """
    <html><body>
    <button class="btn" style="background:#000; border:none;">Click</button>
    <script>
      const canvas = document.getElementById('c');
      const ctx = canvas.getContext('2d');
      function drawPlayer() {
        ctx.beginPath();
        ctx.arc(100, 100, 20, 0, Math.PI * 2);
        ctx.fill();
      }
    </script>
    </body></html>
    """
    res_bad = RedTeamInquisitor.indict_game_code(bad_code, "劣质Demo反例")
    print(f"\n[负向测试 - 垃圾代码审讯结果]: 判定={res_bad['verdict']}, 得分={res_bad['final_score']}")
    print(f"命中否决项 ({len(res_bad['veto_hits'])} 项): {res_bad['veto_hits']}")
    for ind in res_bad["indictments"]:
        print(f"  ❌ {ind}")
    assert res_bad["is_release_blocked"], "红军竟然对劣质代码放水了！"

    # 2. 正向标杆测试: 检验当前生成的赛博幸存者
    cyber_path = ROOT / "output" / "cyber_survivor" / "index.html"
    if cyber_path.exists():
        res_good = RedTeamInquisitor.indict_file(str(cyber_path))
        print(f"\n[正向测试 - 《赛博幸存者》重塑版审讯结果]: 判定={res_good['verdict']}, 得分={res_good['final_score']}")
        print(f"命中否决项: {res_good['veto_hits']}")
        print(f"第一性原则维度评分: {res_good['first_principles_audit']}")
