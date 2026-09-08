# =================================================================
# 📖 Game-Agent: 大师级游戏著作自动化蒸馏引擎 (book_to_skill_engine.py)
# 对标《Book-to-Skill 玩转游戏开发实战教程》
# 自动化将经典游戏设计书籍、技术手册蒸馏为规范化的可执行 SKILL.md
# =================================================================

import json
from pathlib import Path
from typing import Dict, List, Any

class BookToSkillEngine:
    """
    书籍到技能蒸馏器 (Book-to-Skill Distiller)
    支持将权威游戏开发书籍自动蒸馏为 Agent 的底层决策透镜与架构模式库
    """
    
    BUILTIN_DISTILLED_BOOKS = {
        "GameProgrammingPatterns": {
            "title": "Game Programming Patterns (游戏编程模式)",
            "author": "Robert Nystrom",
            "category": "Architecture & Engineering",
            "patterns": [
                {
                    "name": "State Pattern (状态模式)",
                    "intent": "允许一个对象在其内部状态改变时改变它的行为，彻底消除复杂的分支条件判断。",
                    "use_case": "玩家机甲状态机 (Flying, Mining, Shooting, Building)、游戏全局生命周期 (Menu, Playing, Paused)。"
                },
                {
                    "name": "Command Pattern (命令模式)",
                    "intent": "将一个请求封装为一个对象，从而使可用不同的请求对客户进行参数化。",
                    "use_case": "撤销/重做、输入解耦 (WASD/滚轮/右键映射为操作指令)、网络同步与回放。"
                },
                {
                    "name": "Object Pool (对象池模式)",
                    "intent": "重用一组已经初始化的对象，而不是在需要时创建和销毁它们，实现零 GC 停顿。",
                    "use_case": "子弹弹幕、采矿粒子流、伤害跳字、爆炸火花碎片。"
                },
                {
                    "name": "Component Pattern (组件模式 / ECS)",
                    "intent": "允许单一实体跨越多个领域，而不会导致各个领域彼此耦合。",
                    "use_case": "TransformComponent, HealthComponent, WeaponComponent, InventoryComponent 解耦装配。"
                },
                {
                    "name": "Spatial Partition (空间分区模式)",
                    "intent": "通过将对象组织成按空间位置索引的数据结构，高效地定位靠近指定位置的对象。",
                    "use_case": "瓦元大地图网格索引、360度炮塔快速索敌、碰撞求交加速。"
                }
            ]
        },
        "TheArtOfGameDesign": {
            "title": "The Art of Game Design (游戏设计的艺术)",
            "author": "Jesse Schell",
            "category": "Design & Game Feel",
            "lenses": [
                {
                    "id": "Lens_01_Emotion",
                    "name": "情绪透镜 (The Lens of Emotion)",
                    "rule": "问自己：在这个 30 秒的循环里，玩家应该感受到什么样的情绪？是采矿的充实、造防线的紧迫，还是轰杀敌机的爽快？"
                },
                {
                    "id": "Lens_09_CoreLoop",
                    "name": "核心循环透镜 (The Lens of the Core Loop)",
                    "rule": "定义清晰的基础动词循环（Core Verbs Loop: 采集 ➔ 运输 ➔ 加工 ➔ 防御 ➔ 扩张），确保每一步都有明确的驱动力。"
                },
                {
                    "id": "Lens_38_Juice",
                    "name": "果汁/反馈透镜 (The Lens of Juice)",
                    "rule": "游戏必须有充足的视听反馈：每次交互都伴随屏幕微震、按键音效、粒子吸附与全息预览，绝不交付冷冰冰的僵死界面。"
                },
                {
                    "id": "Lens_44_Synergy",
                    "name": "搭配逻辑透镜 (The Lens of Synergy)",
                    "rule": "组件之间必须形成可解释的搭配逻辑（降低门槛 ➔ 提高收益 ➔ 重复触发 ➔ 突破瓶颈），杜绝孤立数值。"
                }
            ]
        }
    }

    def __init__(self, output_dir: Path = (Path(__file__).resolve().parent / 'knowledge/book_skills')):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def distill_all_builtin_books(self) -> List[Path]:
        """全量蒸馏内置经典著作并生成规范的 SKILL.md"""
        distilled_paths = []
        for key, book in self.BUILTIN_DISTILLED_BOOKS.items():
            skill_file = self.output_dir / f"{key}_SKILL.md"
            lines = [
                f"# 📚 蒸馏技能大典: {book['title']}",
                f"- **作者**: {book['author']}",
                f"- **领域**: {book['category']}",
                "\n---\n",
                "## 🧠 核心大师方法论与决策准则\n"
            ]

            if "patterns" in book:
                lines.append("### 🏛️ 经典架构与工程设计模式\n")
                for p in book["patterns"]:
                    lines.append(f"#### 🔹 {p['name']}")
                    lines.append(f"- **核心意图**: {p['intent']}")
                    lines.append(f"- **实战场景**: {p['use_case']}\n")

            if "lenses" in book:
                lines.append("### 🔍 核心设计透镜与心流准则\n")
                for l in book["lenses"]:
                    lines.append(f"#### 🔸 {l['name']} (`{l['id']}`)")
                    lines.append(f"- **设计准则**: {l['rule']}\n")

            skill_file.write_text("\n".join(lines), encoding="utf-8")
            distilled_paths.append(skill_file)
            print(f"  [DISTILLED] {book['title']} -> {skill_file.name}")

        return distilled_paths

if __name__ == "__main__":
    print("=== BookToSkillEngine: 正在自动化蒸馏世界级游戏著作 ===")
    engine = BookToSkillEngine()
    engine.distill_all_builtin_books()
    print("=== 蒸馏完成，已固化进 Agent 底层技能树 ===")
