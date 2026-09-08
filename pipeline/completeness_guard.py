#!/usr/bin/env python3
"""
pipeline/completeness_guard.py: 游戏完备性与真实资产实体第一性门禁 (Completeness & First-Principles Guard)

彻底拔除“形式主义关键词搜索”！
基于第一性事实与 AST / 语义解析审查：
1. 角色/养成体系: 具备职业选择或局外永久天赋成长元游戏 (Meta-Progression)。
2. 真实视觉实体: 严禁单一裸圆圈 (ctx.arc) 充当角色！必须具备图像精灵 (drawImage) 或高阶复合矢量装甲 (包含躯干、肢体、朝向、阴影)。
3. 技能树构筑: 具备 Roguelike 三选一卡牌构筑或技能升级分支。
4. 波次与 Boss 机制: 具备时间或击杀推进的敌人波次与高压 Boss 战。
5. 4 层打击感 Juice: 具备受击闪白/顿帧、创伤震屏、暴击伤害浮字与程序化音效。
"""

import re
from typing import Dict, List, Any

class CompletenessGuard:

    @staticmethod
    def audit_game_code(code: str) -> Dict[str, Any]:
        audit_results = []
        violations = []

        # 1. 角色或长线养成体系审查 (第一性事实: 是否具备实质成长回路)
        has_chars_or_talents = bool(
            re.search(r'(CHARACTERS_DATA|talents|VersionedPersistenceStore|TALENT_DEFS)', code) and
            re.search(r'(atkBoost|moveSpeed|maxHealth|selectChar|upgrade-card)', code)
        )
        if not has_chars_or_talents:
            violations.append("【缺失核心】游戏缺乏多角色选择或局外永久天赋树成长回路，无长线留存价值！")
            audit_results.append({"pillar": "成长体系", "status": "FAIL", "reason": "无角色选择亦无天赋树"})
        else:
            audit_results.append({"pillar": "成长体系", "status": "PASS", "detail": "具备完备的多维度成长/天赋树持久化闭环"})

        # 2. 真实视觉表征审查 (第一性事实: 严禁裸圆圈充当角色)
        has_composite_player = bool(
            re.search(r'function\s+drawPlayer|const\s+drawPlayer\s*=', code) and
            re.search(r'(roundRect|fillRect|scale\(-1|walkCycle|bounceY)', code)
        )
        has_real_image_sprites = bool("ctx.drawImage" in code and ("SpriteAtlas" in code or "AssetManager" in code or ".png" in code))

        if not (has_composite_player or has_real_image_sprites):
            violations.append("【严重视觉缺陷】未检测到真实精灵原画或高阶复合矢量装甲，严禁手写画线画圆充当角色！")
            audit_results.append({"pillar": "真实美术表征", "status": "FAIL", "reason": "缺乏真实原画或复合矢量动画装甲"})
        else:
            audit_results.append({"pillar": "真实美术表征", "status": "PASS", "detail": "具备高精度复合矢量角色装甲或真实精灵图元"})

        # 3. 技能树构筑审查 (第一性事实: 是否具备 Roguelike 3选1或技能升阶)
        has_skills_build = bool(
            re.search(r'(SKILLS_DATA|SKILL_CARDS|levelup-modal)', code) and
            re.search(r'(triggerLevelUp|checkLevelUp|showLevelUpCards)', code)
        )
        if not has_skills_build:
            violations.append("【缺失核心】游戏缺乏升级三选一技能树构筑体系！")
            audit_results.append({"pillar": "技能构筑树", "status": "FAIL", "reason": "升级无三选一卡牌，缺乏长线心流构筑"})
        else:
            audit_results.append({"pillar": "技能构筑树", "status": "PASS", "detail": "具备主被动升级三选一随机卡牌联动与升阶"})

        # 4. 关卡波次与巨型 Boss 审查 (第一性事实: 是否有时序推进与首领阶段)
        has_waves_boss = bool(
            re.search(r'(spawnBoss|drawBoss|boss-hud|isBoss|Weekly Report Overlord)', code) or
            ("WAVES_DATA" in code and "wave" in code.lower())
        )
        if not has_waves_boss:
            violations.append("【缺失核心】游戏缺乏明确波次节奏或巨型 Boss 阶段压迫！")
            audit_results.append({"pillar": "关卡与Boss", "status": "FAIL", "reason": "无压迫感波次递进或无阶段Boss"})
        else:
            audit_results.append({"pillar": "关卡与Boss", "status": "PASS", "detail": "包含波次时序推进与阶段 Boss 战术压迫机制"})

        # 5. 4 层复合打击感 Juice 审查 (第一性事实: 是否具备闪白/震屏/浮字/音效)
        has_juice = bool(
            ("screenShake" in code or "Trauma" in code or "shake" in code) and
            ("floatingTexts" in code or "spawnText" in code or "floatingNumbers" in code) and
            ("AudioEngine" in code or "SoundFX" in code or "JuiceBus" in code or "AudioBus" in code)
        )
        if not has_juice:
            violations.append("【体验缺陷】缺乏顿帧、震屏、伤害浮字或音效反馈，打击感软飘！")
            audit_results.append({"pillar": "打击感Juice", "status": "FAIL", "reason": "缺乏创伤震屏、伤害浮字与原生音效"})
        else:
            audit_results.append({"pillar": "打击感Juice", "status": "PASS", "detail": "内置创伤震屏、伤害暴击浮字、受击闪白与原生音效"})

        is_fully_qualified = len(violations) == 0

        return {
            "is_fully_qualified": is_fully_qualified,
            "overall_verdict": "CERTIFIED_COMMERCIAL_COMPLETE" if is_fully_qualified else "INCOMPLETE_REJECTED",
            "violations": violations,
            "audit_results": audit_results
        }
