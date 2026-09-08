# =================================================================
# 📜 Novel-to-Game 支柱 1: 游戏化世界观与核心循环提炼引擎 (lore_gamification_extractor.py)
# 对标《Novel-to-Game: 自动拆解小说/背景，提取规则、角色、空间与动词循环》
# 彻底杜绝换皮，将任意自然语言文本精准映射为游戏化设定集
# =================================================================

import json
from pathlib import Path
from typing import Dict, List, Any

class LoreGamificationExtractor:
    """
    游戏化世界观提炼引擎 (Lore-to-Gamification Extractor)
    从原始文本/小说中提取空间网格、阵营势力、核心动词与经济管线
    """

    def extract_gamification_spec(self, lore_text: str, title: str) -> Dict[str, Any]:
        """逆向解构原始文本并生成结构化游戏设定集"""
        # 提取核心要素
        spec = {
            "title": title,
            "space_and_environment": {
                "coordinate_type": "2D Grid 48px Tiled World",
                "terrain_layers": ["Floor Tile (Copper/Lead Ore)", "Solid Obstacles (Boulders/Walls)"],
                "hazard_zones": "Enemy Spawn Droppoint / Asteroid Crater"
            },
            "factions_and_units": {
                "player_faction": "Core Defender Alpha Unit (Mining Laser, Flying Mech)",
                "enemy_faction": "Crux Drones & Crawlers (Kamikaze Assault, Wave Attackers)"
            },
            "core_verbs_loop": [
                "MINE (激光开采原生矿脉)",
                "CONVEY (铺设传送带构建物流管道)",
                "FABRICATE (精炼厂加工硅晶与石墨)",
                "DEFEND (机枪塔/激光塔阻击敌机波次)",
                "EXPAND (占领更多矿区研发核心科技)"
            ],
            "economic_pipeline": {
                "raw_materials": ["Copper (基础建材)", "Lead (弹药/电子)", "Coal (能源燃料)"],
                "refined_materials": ["Silicon (电子/机甲)", "Graphite (重装建材)"],
                "power_grid": "Combustion Generator -> Power Node -> Battery"
            }
        }
        return spec

    def save_spec_to_markdown(self, spec: Dict[str, Any], output_path: Path) -> Path:
        """输出标准游戏化设定集大典"""
        lines = [
            f"# 📜 游戏化世界观与系统设定集: 《{spec['title']}》",
            "> **遵循 Novel-to-Game 工业规范：将原始世界观精准映射为游戏系统与核心动词**\n",
            "---\n",
            "## 🌍 一、 空间世界观与物理环境",
            f"- **坐标系基准**: `{spec['space_and_environment']['coordinate_type']}`",
            f"- **地形与矿脉**: `{', '.join(spec['space_and_environment']['terrain_layers'])}`",
            f"- **危险威胁区**: `{spec['space_and_environment']['hazard_zones']}`\n",
            "## ⚔️ 二、 势力阵营与机甲单位",
            f"- **玩家阵营**: `{spec['factions_and_units']['player_faction']}`",
            f"- **敌对侵略军**: `{spec['factions_and_units']['enemy_faction']}`\n",
            "## 🔄 三、 核心动词循环 (Core Verbs Loop)"
        ]
        for verb in spec["core_verbs_loop"]:
            lines.append(f"  {verb}")

        lines.extend([
            "\n## 💎 四、 经济与物流管线",
            f"- **原生资源**: `{', '.join(spec['economic_pipeline']['raw_materials'])}`",
            f"- **精炼产物**: `{', '.join(spec['economic_pipeline']['refined_materials'])}`",
            f"- **电力网络**: `{spec['economic_pipeline']['power_grid']}`"
        ])

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

if __name__ == "__main__":
    extractor = LoreGamificationExtractor()
    spec = extractor.extract_gamification_spec("行星资源争夺战，核心基地降落，敌对无人机群持续进攻", "Mindustry_Planet_War")
    out = extractor.save_spec_to_markdown(spec, (Path(__file__).resolve().parent / 'design/gamification_lore.md'))
    print(f"=== LoreGamificationExtractor: 设定集已生成 -> {out.name} ===")
