#!/usr/bin/env python3
"""pipeline/human_review.py: 人工审美与合规复核门禁（缺口三）

Agent 能出图、能合成音频、能过结构 QA，但「好不好看 / 有没有版权问题 /
能不能上架」这件事代码判定不了。此前这一环只存在于口头约定里，因此本模块
把它做成可落盘、可追溯、能拦住生产放行的工单。

工单模型：
    create  -> 对某个工件（美术 / 音频 / 出货包）建立复核工单，记录 sha256
    submit  -> 由具名 reviewer 给出 verdict 与逐项 checklist 结论
    status  -> 查询某次运行是否已具备放行所需的人工复核

诚实边界（必须写在报告里，不能省略）：
    1. 无人工签署 = NOT_REVIEWED，绝不因为「流程走完了」就当作通过。
    2. 本模块能证明「有人签署」，不能证明「签署者具备审美或法务资质」。
    3. AI 预评分（如 VLM）只能作为 reviewer 的参考意见，不能代替 verdict。
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

APPROVED = "APPROVED"
REJECTED = "REJECTED"
NEEDS_REVISION = "NEEDS_REVISION"
PENDING = "PENDING"
NOT_REVIEWED = "NOT_REVIEWED"

BLOCKED = "BLOCKED"
CLEARED = "CLEARED"

HUMAN = "human"

# ── 各类工件的默认复核项 ───────────────────────────────────────────────────
DEFAULT_CHECKLIST: Dict[str, List[str]] = {
    "art": [
        "风格一致性（与 StyleBible 是否吻合）",
        "版权与素材来源（训练/参考素材是否可商用）",
        "无可见水印、无残肢与畸变",
        "符合目标年龄分级",
    ],
    "audio": [
        "听感无爆音/削波",
        "无版权素材与未授权采样",
        "音量平衡与循环点自然",
        "符合目标年龄分级",
    ],
    "release": [
        "商店素材合规（尺寸/内容/无误导）",
        "隐私政策与年龄分级声明齐备",
        "AI 生成内容已如实声明",
        "第三方 SDK 已如实声明",
    ],
}

# ── 生产放行必需的人工复核类型 ─────────────────────────────────────────────
PRODUCTION_REQUIRED_KINDS: Tuple[str, ...] = ("art", "audio", "release")

__all__ = ["HumanReviewBoard", "DEFAULT_CHECKLIST", "PRODUCTION_REQUIRED_KINDS",
           "APPROVED", "REJECTED", "NEEDS_REVISION", "PENDING", "NOT_REVIEWED"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class HumanReviewBoard:
    """人工复核工单板：落盘 JSON，按 run_id 聚合，供生产门禁查询。"""

    def __init__(self, review_root: Optional[Path] = None):
        if review_root is None:
            # GAME_REVIEW_ROOT 用于把工单隔离到指定 workspace（测试与多运行并存）
            env_root = (os.environ.get("GAME_REVIEW_ROOT") or "").strip()
            if env_root:
                review_root = Path(env_root)
            else:
                root = Path(__file__).resolve().parent.parent
                review_root = root / "output" / "reviews"
        self.review_root = Path(review_root)

    # ---------- 工单 ----------

    @staticmethod
    def _ticket_id(run_id: str, kind: str, artifact_sha: str) -> str:
        return f"{run_id}__{kind}__{artifact_sha[:12]}"

    def _path_for(self, ticket_id: str) -> Path:
        return self.review_root / f"{ticket_id}.json"

    def create_ticket(self, run_id: str, kind: str, artifact_path: Path,
                      notes: str = "") -> Dict[str, Any]:
        path = Path(artifact_path)
        if not path.is_file():
            raise FileNotFoundError(f"待复核工件不存在: {path}")
        if kind not in DEFAULT_CHECKLIST:
            raise ValueError(f"未知复核类型: {kind}，可选: {', '.join(DEFAULT_CHECKLIST)}")

        artifact_sha = _sha256(path)
        ticket_id = self._ticket_id(run_id, kind, artifact_sha)
        ticket = {
            "ticket_id": ticket_id,
            "run_id": run_id,
            "kind": kind,
            "artifact": str(path),
            "artifact_sha256": artifact_sha,
            "status": PENDING,
            "reviewer": "",
            "verdict": PENDING,
            "checklist": [{"item": name, "result": "pending", "comment": ""}
                          for name in DEFAULT_CHECKLIST[kind]],
            "ai_opinion": None,
            "notes": notes,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        self.review_root.mkdir(parents=True, exist_ok=True)
        self._path_for(ticket_id).write_text(
            json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
        return ticket

    def submit(self, ticket_id: str, reviewer: str, verdict: str,
               checklist_results: Optional[Dict[str, str]] = None,
               notes: str = "", ai_opinion: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not reviewer.strip():
            raise ValueError("复核必须署名：reviewer 不能为空")
        if verdict not in (APPROVED, REJECTED, NEEDS_REVISION):
            raise ValueError(f"verdict 必须是 {APPROVED}/{REJECTED}/{NEEDS_REVISION}")

        path = self._path_for(ticket_id)
        if not path.is_file():
            raise FileNotFoundError(f"工单不存在: {ticket_id}")

        ticket = json.loads(path.read_text(encoding="utf-8"))
        ticket["reviewer"] = reviewer.strip()
        ticket["verdict"] = verdict
        ticket["status"] = verdict
        ticket["notes"] = notes
        ticket["updated_at"] = _now_iso()
        if ai_opinion is not None:
            ticket["ai_opinion"] = ai_opinion
        if checklist_results:
            for entry in ticket["checklist"]:
                result = checklist_results.get(entry["item"])
                if result:
                    entry["result"] = result
        ticket["artifact_sha256_matches"] = self._recheck_sha(ticket)
        path.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
        return ticket

    @staticmethod
    def _recheck_sha(ticket: Dict[str, Any]) -> Optional[bool]:
        path = Path(ticket.get("artifact", ""))
        if not path.is_file():
            return None
        return _sha256(path) == ticket.get("artifact_sha256")

    # ---------- 查询 ----------

    def list_tickets(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.review_root.is_dir():
            return []
        tickets: List[Dict[str, Any]] = []
        for path in sorted(self.review_root.glob("*.json")):
            try:
                ticket = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if run_id and ticket.get("run_id") != run_id:
                continue
            tickets.append(ticket)
        return tickets

    def status(self, run_id: str, required: Iterable[str] = PRODUCTION_REQUIRED_KINDS
               ) -> Dict[str, Any]:
        required = tuple(required)
        tickets = self.list_tickets(run_id)
        by_kind: Dict[str, Dict[str, Any]] = {}
        for ticket in tickets:
            kind = ticket.get("kind", "")
            # 同类型取最新一次结论
            current = by_kind.get(kind)
            if current is None or ticket.get("updated_at", "") >= current.get("updated_at", ""):
                by_kind[kind] = ticket

        missing: List[str] = []
        not_approved: List[str] = []
        for kind in required:
            ticket = by_kind.get(kind)
            if ticket is None:
                missing.append(kind)
            elif ticket.get("verdict") != APPROVED:
                not_approved.append(f"{kind}={ticket.get('verdict')}")

        cleared = not missing and not not_approved
        return {
            "run_id": run_id,
            "status": CLEARED if cleared else BLOCKED,
            "required": list(required),
            "missing": missing,
            "not_approved": not_approved,
            "approved_by": {k: v.get("reviewer") for k, v in by_kind.items()
                            if v.get("verdict") == APPROVED},
            "tickets": list(by_kind.values()),
            "note": ("已有人签署不等同于具备审美或法务资质；本记录仅证明具名复核发生"
                     if cleared else
                     "缺少具名人工复核，生产放行前必须补齐"),
        }

    def production_gate(self, run_id: str,
                        required: Iterable[str] = PRODUCTION_REQUIRED_KINDS) -> Dict[str, Any]:
        """供发布门禁调用：返回 (allowed, reason) 语义的结构。"""
        report = self.status(run_id, required)
        report["allowed"] = report["status"] == CLEARED
        if not report["allowed"]:
            report["reason"] = (f"缺少人工复核：未复核={report['missing'] or '无'}，"
                                f"未通过={report['not_approved'] or '无'}")
        return report
