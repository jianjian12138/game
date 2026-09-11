#!/usr/bin/env python3
"""
taste_signal.py: 玩家口味语料 -> 游戏设计约束 (Player Taste Signal)

对应公众号文章《把做 AI 游戏流程录成 Skill》的核心洞察：
    AI 不知道什么叫好玩。真实玩家在 TapTap / Steam 评论区的吐槽与偏好，
    才是玩法设计约束的真正来源。把外部玩家信号收回来，再反哺到做游戏的提示词。

本模块把"结构化玩家语料"转为可注入提示词的 avoid / prefer / pacing / visual 设计约束。

诚实边界：
- 外部实时采集 (fetch_external) 默认不实现（反爬 / 合规 / 需凭据），
  返回 NEEDS_NETWORK 并诚实降级回退至本地种子语料，不伪装爬取。
- 种子语料 knowledge/player_taste_spec.json 是人工整理的代表性样本，
  不是实时抓取的语料；若接了真实采集，应替换该文件并通过 fetch_external 落盘。
- 本模块为零依赖纯标准库实现。
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union

DEFAULT_CORPUS = Path(__file__).resolve().parent.parent / "knowledge" / "player_taste_spec.json"


class TasteSignal:
    """玩家口味信号采集与约束注入。"""

    @classmethod
    def load_corpus(cls, path: Optional[str] = None) -> Dict[str, Any]:
        """读取结构化玩家口味语料（本地 JSON），兼容全量 spec 字段与 entries 列表。"""
        p = Path(path) if path else DEFAULT_CORPUS
        if not p.exists():
            return {
                "status": "NEEDS_CORPUS",
                "error": f"语料文件不存在: {p}",
                "entries": [],
                "avoid_patterns": [],
                "prefer_patterns": [],
                "visual_constraints": {},
                "taste_profiles": {},
            }
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            res = {"status": "OK"}
            res.update(data)
            if "entries" not in res:
                res["entries"] = []
            return res
        except (OSError, ValueError) as e:
            return {"status": "ERROR", "error": str(e), "entries": []}

    @classmethod
    def load_local_taste(cls, path: Optional[str] = None) -> Dict[str, Any]:
        """别名方法，等价于 load_corpus。"""
        return cls.load_corpus(path)

    @classmethod
    def to_design_constraints(
        cls,
        corpus: Optional[Union[Dict[str, Any], str]] = None,
        genre: str = ""
    ) -> Dict[str, Any]:
        """把语料条目聚合成 avoid / prefer / pacing / visual 四类设计约束，支持品类分群过滤。

        自适应支持参数形式：
        - to_design_constraints() -> 默认加载本地语料
        - to_design_constraints(genre="3D FPS")
        - to_design_constraints("3D FPS")
        - to_design_constraints(corpus_dict, genre="3D FPS")
        """
        if isinstance(corpus, str) and not genre:
            genre = corpus
            corpus = None

        if corpus is None:
            corpus = cls.load_corpus()

        entries = corpus.get("entries", []) if isinstance(corpus, dict) else []
        avoid, prefer, pacing, visual_items = [], [], [], []

        # 从根 spec 中提取默认规则
        root_avoids = corpus.get("avoid_patterns", []) if isinstance(corpus, dict) else []
        root_prefers = corpus.get("prefer_patterns", []) if isinstance(corpus, dict) else []
        visual_dict = corpus.get("visual_constraints", {}) if isinstance(corpus, dict) else {}

        g_lower = (genre or "").lower()
        is_hardcore = any(k in g_lower for k in ("魂", "动作", "fps", "射击", "hardcore", "arpg"))
        is_casual = any(k in g_lower for k in ("休闲", "挂机", "放置", "小镇", "casual", "三消"))
        is_rogue = any(k in g_lower for k in ("肉鸽", "rogue", "卡牌", "card"))

        # 品类特化补充
        profiles = corpus.get("taste_profiles", {}) if isinstance(corpus, dict) else {}
        if is_hardcore and "hardcore" in profiles:
            prefer.extend(profiles["hardcore"].get("prefer", []))
            avoid.extend(profiles["hardcore"].get("avoid", []))
        elif is_casual and "casual" in profiles:
            prefer.extend(profiles["casual"].get("prefer", []))
            avoid.extend(profiles["casual"].get("avoid", []))

        for e in entries:
            if not isinstance(e, dict):
                continue
            seg = (e.get("genre_segment") or "all").lower()
            if seg != "all":
                if seg == "hardcore" and not is_hardcore:
                    continue
                if seg == "casual" and is_hardcore and not is_casual:
                    continue
                if seg == "roguelike" and not is_rogue:
                    continue

            sig = (e.get("signal") or "").lower()
            cat = (e.get("category") or "").lower()
            txt = e.get("constraint") or e.get("text") or ""
            if not txt:
                continue

            if cat == "visual":
                visual_items.append(txt)

            if sig in ("avoid", "negative", "dislike"):
                avoid.append(txt)
            elif sig in ("prefer", "positive", "like"):
                prefer.append(txt)
            elif sig in ("pacing", "节奏"):
                pacing.append(txt)

        # 结合基础根规则
        for a in root_avoids:
            if a not in avoid:
                avoid.append(a)
        for p in root_prefers:
            if p not in prefer:
                prefer.append(p)

        # 结构化 visual 字典与条目
        visual_payload = {
            "hud_safe_zone": visual_dict.get("hud_safe_zone", "HUD 视平线与按键保持边缘对齐，杜绝遮挡"),
            "contrast_indicators": visual_dict.get("contrast_indicators", "技能前摇与判定具备高对比度警示"),
            "screen_shake_layering": visual_dict.get("screen_shake_layering", "伤害浮字与顿帧层级分明，创伤震屏分层"),
            "rules": visual_items
        }

        return {
            "status": "OK",
            "avoid": avoid,
            "prefer": prefer,
            "pacing": pacing,
            "visual": visual_payload,
            "genre_filter": genre or "all",
            "source_count": len(entries),
            "sources": [e.get("source", "") for e in entries if isinstance(e, dict) and e.get("source")],
        }

    @classmethod
    def attach_to_prompt(
        cls,
        arg1: Union[str, Dict[str, Any]],
        arg2: Union[str, Dict[str, Any]]
    ) -> str:
        """把设计约束注入到游戏生成提示词尾部。自适应支持 (prompt, constraints) 或 (constraints, prompt)。"""
        if isinstance(arg1, str) and isinstance(arg2, dict):
            base_prompt = arg1
            constraints = arg2
        elif isinstance(arg1, dict) and isinstance(arg2, str):
            constraints = arg1
            base_prompt = arg2
        else:
            return str(arg1)

        if not constraints or constraints.get("status") != "OK":
            return base_prompt

        block = ["\n### 玩家品味约束 (Player Taste Constraints)"]
        if constraints.get("avoid"):
            block.append("- [避坑底线 - 严禁出现]: " + "；".join(constraints["avoid"][:5]))
        if constraints.get("prefer"):
            block.append("- [偏好增强 - 强烈建议]: " + "；".join(constraints["prefer"][:5]))
        
        visual = constraints.get("visual")
        if isinstance(visual, dict):
            vis_lines = []
            if "hud_safe_zone" in visual:
                vis_lines.append(f"安全区: {visual['hud_safe_zone']}")
            if "contrast_indicators" in visual:
                vis_lines.append(f"判定高对比: {visual['contrast_indicators']}")
            if "screen_shake_layering" in visual:
                vis_lines.append(f"震屏顿帧: {visual['screen_shake_layering']}")
            if vis_lines:
                block.append("- [视觉交互工业标准]: " + "；".join(vis_lines))
        elif isinstance(visual, list) and visual:
            block.append("- [视觉交互工业标准]: " + "；".join(visual[:3]))

        if constraints.get("pacing"):
            block.append("- [节奏与心流]: " + "；".join(constraints["pacing"][:3]))

        return base_prompt.rstrip() + "\n" + "\n".join(block) + "\n"

    @classmethod
    def fetch_external(
        cls,
        platform: str = "taptap",
        channel: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """外部实时采集桩。默认不实现（反爬 / 合规 / 需凭据），诚实返回 NEEDS_NETWORK 并附带本地降级语料。"""
        target = channel or platform
        return {
            "status": "NEEDS_NETWORK",
            "needs_runtime_tool": "external_review_crawler",
            "platform": target,
            "fallback": True,
            "data": cls.load_corpus(),
            "error": (f"外部 {target} 评论实时采集未接入(反爬/合规/需凭据)，"
                      "诚实降级使用本地规范语料 player_taste_spec.json"),
        }


if __name__ == "__main__":
    corpus = TasteSignal.load_corpus()
    cons = TasteSignal.to_design_constraints(corpus)
    print(json.dumps(cons, ensure_ascii=False, indent=2))
