#!/usr/bin/env python3
"""
game_domain_modeler.py: 游戏领域建模与四要素推演中枢 (Game Domain Modeler)
Agent 正统研发逻辑第一层：在写任何代码之前，必须先将游戏抽象推演为 4 张结构化领域数据表：
1. 角色体系 (Characters)
2. 技能与升级构筑树 (Skills & Builds)
3. 关卡波次与巨型 Boss (Waves & Bosses)
4. 剧情世界观与核心目标 (Story & Goals)
"""
import json
from typing import Dict, List, Any

class GameDomainModeler:

    @staticmethod
    def deduce_domain_model(title: str, genre: str, concept: str = "") -> Dict[str, Any]:
        """根据创意自主推演完整的 4 维领域数据大典"""
        # 1. 角色体系推演 (3 大差异化职业)
        characters = [
            {
                "id": "char_warrior",
                "name": "狂怒角斗士 · 泰坦",
                "desc": "近战强硬坦克，血厚甲高，初始自带破灭旋风斩",
                "color": "#e63946",
                "hp": 250,
                "speed": 3.8,
                "starting_weapon": "spinning_axe",
                "passive": "受到伤害时反弹 25% 震波并获得 10% 减伤"
            },
            {
                "id": "char_ranger",
                "name": "疾风猎杀者 · 幻影",
                "desc": "高灵动游侠，暴击率极高，初始自带多重穿透飞刀",
                "color": "#2a9d8f",
                "hp": 140,
                "speed": 5.2,
                "starting_weapon": "throwing_knives",
                "passive": "暴击率天然提升 20%，移动速度提升 15%"
            },
            {
                "id": "char_mage",
                "name": "虚空奥术师 · 艾琳",
                "desc": "全域法术轰炸，自带大范围磁铁，初始自带全屏引力落雷",
                "color": "#9d4edd",
                "hp": 110,
                "speed": 4.2,
                "starting_weapon": "lightning_storm",
                "passive": "经验拾取范围增加 80%，法术技能冷却缩短 15%"
            }
        ]

        # 2. 技能构筑与升级三选一树 (主动武器 + 被动增益)
        skills = [
            {
                "id": "throwing_knives",
                "type": "active",
                "name": "穿刺飞刀",
                "icon": "🗡️",
                "desc": "朝最近敌人投掷多枚高速飞刀",
                "max_level": 5,
                "upgrades": [
                    {"level": 1, "desc": "解锁投掷 2 枚飞刀，基础伤害 25"},
                    {"level": 2, "desc": "飞刀数量 +1，伤害提升 20%"},
                    {"level": 3, "desc": "飞刀获得穿透效果，攻击间隔缩短 15%"},
                    {"level": 4, "desc": "飞刀数量 +2，伤害提升 30%"},
                    {"level": 5, "desc": "【终极觉醒】千刃风暴：360度发射8枚高爆飞刀"}
                ]
            },
            {
                "id": "spinning_axe",
                "type": "active",
                "name": "环绕烈焰",
                "icon": "🔥",
                "desc": "召唤灼热火球环绕自身高速旋转",
                "max_level": 5,
                "upgrades": [
                    {"level": 1, "desc": "召唤 2 颗环绕火球，触碰造成 30 点持续灼烧"},
                    {"level": 2, "desc": "旋转速度提升 25%，火球尺寸增大"},
                    {"level": 3, "desc": "火球数量 +1，触碰附加击退效果"},
                    {"level": 4, "desc": "火球数量 +1，灼烧伤害提升 40%"},
                    {"level": 5, "desc": "【终极觉醒】炽天使之翼：火球常驻6颗，引发全屏灼烧"}
                ]
            },
            {
                "id": "lightning_storm",
                "type": "active",
                "name": "雷霆轰顶",
                "icon": "⚡",
                "desc": "随机召唤落雷劈击视野内的敌人",
                "max_level": 5,
                "upgrades": [
                    {"level": 1, "desc": "每 1.8 秒召唤 2 道落雷，造成 60 点范围伤害"},
                    {"level": 2, "desc": "落雷数量 +1，范围扩大 20%"},
                    {"level": 3, "desc": "落雷附加 0.3 秒麻痹硬直，伤害 +25%"},
                    {"level": 4, "desc": "落雷数量 +2，冷却缩短 20%"},
                    {"level": 5, "desc": "【终极觉醒】审判雷暴：每秒轰击全屏所有可见敌人"}
                ]
            },
            {
                "id": "passive_magnet",
                "type": "passive",
                "name": "引力磁石",
                "icon": "🧲",
                "desc": "大幅强化经验水晶与金币的拾取吸引范围",
                "max_level": 3,
                "upgrades": [
                    {"level": 1, "desc": "拾取范围 +50%"},
                    {"level": 2, "desc": "拾取范围 +100%，经验获取量 +10%"},
                    {"level": 3, "desc": "【觉醒】全图磁吸：每隔 60 秒吸附全图所有经验水晶"}
                ]
            },
            {
                "id": "passive_boots",
                "type": "passive",
                "name": "疾风之靴",
                "icon": "👢",
                "desc": "提升移动速度与脱困能力",
                "max_level": 3,
                "upgrades": [
                    {"level": 1, "desc": "移动速度 +15%"},
                    {"level": 2, "desc": "移动速度 +30%，闪避率 +10%"},
                    {"level": 3, "desc": "【觉醒】幻影步：移速 +45%，冲刺时无敌 0.5 秒"}
                ]
            }
        ]

        # 3. 关卡波次与巨型 Boss 时序大典
        waves = [
            {
                "time_start_sec": 0,
                "time_end_sec": 45,
                "enemy_type": "crawler",
                "name": "异星幼虫",
                "hp": 30,
                "speed": 1.2,
                "spawn_interval_sec": 1.0,
                "desc": "基础散兵，测试走位与初始武器清怪效率"
            },
            {
                "time_start_sec": 45,
                "time_end_sec": 120,
                "enemy_type": "stalker",
                "name": "狂暴自爆蛛",
                "hp": 65,
                "speed": 2.2,
                "spawn_interval_sec": 0.6,
                "desc": "高速围拢，具备极大压迫感，考验范围伤害"
            },
            {
                "time_start_sec": 120,
                "time_end_sec": 300,
                "enemy_type": "boss_behemoth",
                "name": "深渊灭绝领主 · 贝希摩斯",
                "hp": 2800,
                "speed": 0.9,
                "spawn_interval_sec": 0.0,
                "is_boss": True,
                "boss_skills": [
                    "冲锋红毯预警 (Charge Slam)",
                    "360度全屏环形弹幕 (Nova Burst)",
                    "召唤护卫虫群 (Summon Minions)"
                ],
                "desc": "关卡终极大 Boss，拥有专属顶部巨型血条与狂暴阶段"
            }
        ]

        # 4. 剧情世界观与终极目标
        story_goals = {
            "title": title,
            "genre": genre,
            "lore": f"在人类边境前哨星系，深空母巢发生异变。你作为特战幸存者，必须抵挡潮水般的虚空虫族侵袭。",
            "primary_objective": "坚持存活至第 3 分钟并击灭【深渊灭绝领主】，开启撤离跃迁门！",
            "fail_condition": "生命值归零阵亡",
            "victory_condition": "消灭巨型 Boss 并完成幸存跃迁"
        }

        return {
            "characters": characters,
            "skills": skills,
            "waves": waves,
            "story_goals": story_goals
        }
