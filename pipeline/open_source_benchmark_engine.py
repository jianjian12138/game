"""
Open Source Benchmark Engine (开源手游架构标杆引擎)
基于全球 418 款开源游戏（涵盖 Onslaught Arena、Alien Invasion、Diablo JS、Mario HTML5、Monster Wants Candy 等）
提炼的工业化游戏架构标准、资产管线范式与交付度量门禁。
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

ROOT = Path(__file__).resolve().parent.parent

class OpenSourceBenchmarkEngine:
    """开源游戏架构与资产标准评测中枢"""

    BENCHMARK_HEROES = [
        {
            "name": "Onslaught Arena",
            "repo": "lostdecade/onslaught_arena",
            "genre": "Action Arena Roguelike",
            "key_patterns": [
                "SpriteSheet 贴图逐帧动画（战士挥砍、受击、死亡多帧）",
                "瓦片地牢地图（石砖材质地表、墙体光影遮挡）",
                "地面持久化战损贴花（Decals 血迹喷溅）",
                "打击停顿（Hit-stop）与受击击退（Knockback）",
                "多通道音效合成与 BGM 循环"
            ]
        },
        {
            "name": "Alien Invasion",
            "repo": "cykod/AlienInvasion",
            "genre": "Arcade Shooter",
            "key_patterns": [
                "对象池管理（Object Pooling）高频子弹与粒子",
                "分层星空视差滚动（Parallax Scrolling）",
                "步进式波次行为树调度器（Wave Spawner）",
                "像素级掩码护盾破坏（Destructible Shields）"
            ]
        },
        {
            "name": "Monster Wants Candy",
            "repo": "EnclaveGames/Monster-Wants-Candy-demo",
            "genre": "Casual Action",
            "key_patterns": [
                "弹性形变动画（Squash & Stretch 体积守恒）",
                "多巴胺粒子爆开与连击浮字",
                "响应式自适应屏幕比例与安全区裁切"
            ]
        },
        {
            "name": "Diablo JavaScript",
            "repo": "mitallast/diablo-js",
            "genre": "Action RPG",
            "key_patterns": [
                "等距瓦片地图（Isometric Tilemap）深度排序",
                "装备词条与天赋数值树闭环",
                "法术投射物与地面范围火海（Flame Pools）"
            ]
        }
    ]

    @classmethod
    def load_full_database(cls) -> List[Dict[str, str]]:
        db_path = ROOT / "scratch" / "parsed_games_db.json"
        if not db_path.exists():
            db_path = ROOT / "parsed_games_db.json"
        if db_path.exists():
            with open(db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    @classmethod
    def audit_commercial_readiness_against_benchmarks(cls, html_source: str) -> Dict[str, Any]:
        """对标 418 款开源游戏，审查代码是否达到商业级游戏交付门槛"""
        indictments = []
        strengths = []
        score = 100

        # 1. 真实精灵图与贴图动画审查 (Sprite Sheet & Multi-frame)
        has_sprite_atlas = ("SpriteAtlas" in html_source or "SpriteSheet" in html_source or 
                            ("drawImage" in html_source and ("frameX" in html_source or "frameY" in html_source or "sWidth" in html_source or "sx" in html_source)))
        has_procedural_sprites = ("generateSprite" in html_source or "pixelMatrix" in html_source or "PALETTE" in html_source or "SpriteSheetEngine" in html_source)
        if not (has_sprite_atlas or has_procedural_sprites):
            score -= 30
            indictments.append("【资产缺失】缺乏像素/位图精灵图集与帧动画系统，仍停留于几何画圆阶段")
        else:
            strengths.append("具备完整的精灵图集与逐帧动作动画驱动")

        # 2. 地牢瓦片地图审查 (Tilemap System)
        has_tilemap = ("Tilemap" in html_source or "tileMap" in html_source or "TILES" in html_source or "renderTiles" in html_source or "renderDungeon" in html_source or "DungeonTilemap" in html_source)
        if not has_tilemap:
            score -= 25
            indictments.append("【环境单调】缺乏瓦片地牢或纹理地板系统，背景为空白或裸线条网格")
        else:
            strengths.append("具备高质量瓦片地牢地图与环境材质贴合系统")

        # 3. Game Feel 核心准则审查 (Hit-stop & Squash & Trauma Shake)
        has_hit_stop = ("hitStop" in html_source or "sleepFrames" in html_source or "freezeTimer" in html_source)
        has_squash = ("scaleX" in html_source or "scaleY" in html_source or "squash" in html_source or "stretch" in html_source)
        has_flash = ("flashWhite" in html_source or "hurtFlash" in html_source or "flashTimer" in html_source)
        if not (has_hit_stop and has_flash):
            score -= 20
            indictments.append("【手感生硬】缺乏打击顿帧(Hit-stop)与受击高亮闪白(Flash-white)，攻击反馈不达标")
        else:
            strengths.append("具备打击顿帧、受击闪白与定向击退手感四件套")

        # 4. 对象池与战损贴花审查 (Decals & Object Pooling)
        has_decals = ("decals" in html_source or "bloodSplatter" in html_source or "scorchMarks" in html_source or "decal" in html_source)
        if not has_decals:
            score -= 10
            indictments.append("【细节欠缺】地面缺乏受击血痕/弹坑等战损贴花(Decals)持久化")
        else:
            strengths.append("具备地面动态战损与血迹贴花持久化表现")

        # 5. 音频多通道审查 (Polyphonic Audio Synthesis)
        has_multi_audio = ("AudioEngine" in html_source and ("bgm" in html_source or "playTone" in html_source))
        if not has_multi_audio:
            score -= 15
            indictments.append("【音频单一】缺乏多通道复音合成或分轨音效")
        else:
            strengths.append("具备 WebAudio 实时多通道复音合成与动态打击音效")

        verdict = "BENCHMARK_CERTIFIED" if score >= 85 else "PROTOTYPE_REJECTED"

        return {
            "score": max(0, score),
            "verdict": verdict,
            "strengths": strengths,
            "indictments": indictments,
            "benchmarks_referenced": [b["name"] for b in cls.BENCHMARK_HEROES]
        }

if __name__ == "__main__":
    print("=== OpenSourceBenchmarkEngine 开源手游标杆引擎 ===")
    heroes = OpenSourceBenchmarkEngine.BENCHMARK_HEROES
    print(f"Loaded {len(heroes)} benchmark architectural templates:")
    for h in heroes:
        print(f"  [{h['name']}] ({h['genre']}) - Repo: {h['repo']}")
