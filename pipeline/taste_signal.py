#!/usr/bin/env python3
"""
taste_signal.py: 玩家口味语料 -> 游戏设计约束 (Player Taste Signal)

对应公众号文章《把做 AI 游戏流程录成 Skill》的核心洞察：
    AI 不知道什么叫好玩。真实玩家在 TapTap / Steam 评论区的吐槽与偏好，
    才是玩法设计约束的真正来源。把外部玩家信号收回来，再反哺到做游戏的提示词。

本模块把"结构化玩家语料"转为可注入提示词的 avoid / prefer / pacing 三类约束。

诚实边界：
- 外部实时采集 (fetch_external) 默认不实现（反爬 / 合规 / 需凭据），
  返回 NEEDS_NETWORK，不伪装爬取。
- 种子语料 knowledge/player_taste_spec.json 是人工整理的代表性样本，
  不是实时抓取的语料；若接了真实采集，应替换该文件并通过 fetch_external 落盘。
- 本模块为零依赖纯标准库实现。
"""
import json
from pathlib import Path
from typing import Dict, Any

DEFAULT_CORPUS = Path(__file__).resolve().parent.parent / "knowledge" / "player_taste_spec.json"


class TasteSignal:
    """玩家口味信号采集与约束注入。"""

    @staticmethod
    def load_corpus(path: str = None) -> Dict[str, Any]:
        """读取结构化玩家口味语料（本地 JSON）。"""
        p = Path(path) if path else DEFAULT_CORPUS
        if not p.exists():
            return {"status": "NEEDS_CORPUS", "error": f"语料文件不存在: {p}", "entries": []}
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return {"status": "OK", "entries": data.get("entries", [])}
        except (OSError, ValueError) as e:
            return {"status": "ERROR", "error": str(e), "entries": []}

    @staticmethod
    def to_design_constraints(corpus: Dict[str, Any]) -> Dict[str, Any]:
        """把语料条目聚合成 avoid / prefer / pacing 三类设计约束。"""
        entries = corpus.get("entries", []) if isinstance(corpus, dict) else []
        avoid, prefer, pacing = [], [], []
        for e in entries:
            if not isinstance(e, dict):
                continue
            sig = (e.get("signal") or "").lower()
            txt = e.get("constraint") or e.get("text") or ""
            if not txt:
                continue
            if sig in ("avoid", "negative", "dislike"):
                avoid.append(txt)
            elif sig in ("prefer", "positive", "like"):
                prefer.append(txt)
            elif sig in ("pacing", "节奏"):
                pacing.append(txt)
        return {
            "status": "OK",
            "avoid": avoid,
            "prefer": prefer,
            "pacing": pacing,
            "source_count": len(entries),
            "sources": [e.get("source", "") for e in entries if e.get("source")],
        }

    @staticmethod
    def attach_to_prompt(constraints: Dict[str, Any], base_prompt: str) -> str:
        """把设计约束注入到游戏生成提示词尾部。约束缺失或异常时原样返回。"""
        if not constraints or constraints.get("status") != "OK":
            return base_prompt
        block = ["[玩家口味约束-注入]"]
        if constraints.get("avoid"):
            block.append("避免(玩家真实吐槽): " + "; ".join(constraints["avoid"]))
        if constraints.get("prefer"):
            block.append("优先(玩家上头点): " + "; ".join(constraints["prefer"]))
        if constraints.get("pacing"):
            block.append("节奏: " + "; ".join(constraints["pacing"]))
        return base_prompt + "\n" + "\n".join(block)

    @staticmethod
    def fetch_external(platform: str = "taptap") -> Dict[str, Any]:
        """外部实时采集桩。默认不实现（反爬 / 合规 / 需凭据），诚实返回 NEEDS_NETWORK。"""
        return {
            "status": "NEEDS_NETWORK",
            "needs_runtime_tool": "external_review_crawler",
            "platform": platform,
            "error": (f"外部 {platform} 评论实时采集未接入(反爬/合规/需凭据)，"
                      "请用本地语料 player_taste_spec.json 或显式提供采集结果"),
        }


if __name__ == "__main__":
    corpus = TasteSignal.load_corpus()
    cons = TasteSignal.to_design_constraints(corpus)
    print(json.dumps(cons, ensure_ascii=False, indent=2))
