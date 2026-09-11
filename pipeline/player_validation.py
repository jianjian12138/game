#!/usr/bin/env python3
"""pipeline/player_validation.py: 真实玩家验证与遥测接入（缺口四）

已有能力：pipeline/player_analytics 具备埋点、漏斗、留存、热力图等分析模块，
A/B 实验框架（pipeline/ab_testing）也齐备。缺的不是算法，是**真实数据**。

本模块解决三件事：

    1. 遥测接入体检：TELEMETRY_ENDPOINT / TELEMETRY_KEY 是否配置，
       端点 /health 是否自证身份（与 live_service_doctor 同一套契约）。

    2. 试点队列登记：真实玩家来自哪里、多少人、什么时间窗、如何招募，
       落盘为可追溯的 cohort 记录，而不是口头说「找了些人试玩」。

    3. 数据真实性判定（防伪核心）：
       事件必须自带来源标记才能计入真实指标。
           properties.source in {real_player, playtest, beta, store}  -> 真实
           properties.simulated=True 或 source in {simulated, synthetic, bot, mock} -> 模拟
           无标记 -> UNKNOWN，不计入真实指标
       模拟数据单独统计并在报告里标明「不得用于宣称留存/付费/时长」。
       没有任何真实事件时如实返回 NO_REAL_PLAYER_DATA，绝不用模拟数据凑数。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from core.security_guard import is_loopback_host

PASS = "PASS"
MISSING = "MISSING"
INVALID = "INVALID"
UNREACHABLE = "UNREACHABLE"
IDENTITY_UNVERIFIED = "IDENTITY_UNVERIFIED"
NO_REAL_PLAYER_DATA = "NO_REAL_PLAYER_DATA"

HUMAN = "human"

REAL_SOURCE_VALUES = ("real_player", "playtest", "beta", "store", "live")
SIMULATED_MARKERS = ("simulated", "synthetic", "bot", "mock", "generated")

DEFAULT_TIMEOUT_S = 8.0

HEALTH_CONTRACT_DOC = (
    '遥测服务端 GET /health 必须返回 '
    '{"service": "telemetry", "status": "ok", "environment": "<sandbox|staging|production>"}'
)

__all__ = ["PlayerValidation", "REAL_SOURCE_VALUES", "SIMULATED_MARKERS",
           "NO_REAL_PLAYER_DATA", "classify_event"]


def classify_event(event: Dict[str, Any]) -> str:
    """判定单条事件归属：real / simulated / unknown。"""
    props = event.get("properties") or {}
    if not isinstance(props, dict):
        return "unknown"
    if props.get("simulated") is True:
        return "simulated"
    source = str(props.get("source", "")).strip().lower()
    if source in SIMULATED_MARKERS:
        return "simulated"
    if source in REAL_SOURCE_VALUES:
        return "real"
    return "unknown"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PlayerValidation:
    """真实玩家验证：遥测接入 + 试点登记 + 数据真实性判定。"""

    def __init__(self, validation_root: Optional[Path] = None,
                 timeout_s: float = DEFAULT_TIMEOUT_S):
        if validation_root is None:
            env_root = (os.environ.get("GAME_PLAYER_VALIDATION_ROOT") or "").strip()
            if env_root:
                validation_root = Path(env_root)
            else:
                root = Path(__file__).resolve().parent.parent
                validation_root = root / "output" / "player_validation"
        self.validation_root = Path(validation_root)
        self.cohort_path = self.validation_root / "cohorts.json"
        self.timeout_s = timeout_s

    # ---------- 遥测端点 ----------

    def check_telemetry_endpoint(self) -> List[Dict[str, Any]]:
        checks: List[Dict[str, Any]] = []
        url = (os.environ.get("TELEMETRY_ENDPOINT") or "").strip()
        key = (os.environ.get("TELEMETRY_KEY") or "").strip()

        if not url:
            checks.append({
                "item": "配置 TELEMETRY_ENDPOINT", "status": MISSING, "owner": HUMAN,
                "detail": "环境变量未设置",
                "how_to_fix": "部署遥测接收服务后在 .env 配置 TELEMETRY_ENDPOINT（远端必须 https）",
            })
        else:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                checks.append({
                    "item": "配置 TELEMETRY_ENDPOINT", "status": INVALID, "owner": HUMAN,
                    "detail": "不是合法的 http/https 地址", "how_to_fix": "填写完整地址，如 https://telemetry.example.com",
                })
            elif parsed.scheme == "http" and not is_loopback_host(parsed.hostname):
                checks.append({
                    "item": "配置 TELEMETRY_ENDPOINT", "status": INVALID, "owner": HUMAN,
                    "detail": "远端使用明文 http", "how_to_fix": "远端改用 https；明文 http 仅允许本地联调",
                })
            else:
                checks.append({
                    "item": "配置 TELEMETRY_ENDPOINT", "status": PASS, "owner": HUMAN,
                    "detail": f"已设置，主机 {parsed.hostname}", "how_to_fix": "",
                })

        if not key:
            checks.append({
                "item": "配置 TELEMETRY_KEY", "status": MISSING, "owner": HUMAN,
                "detail": "环境变量未设置",
                "how_to_fix": "在遥测服务端生成 ingest key 后写入 .env 的 TELEMETRY_KEY",
            })
        else:
            checks.append({
                "item": "配置 TELEMETRY_KEY", "status": PASS, "owner": HUMAN,
                "detail": f"已设置（长度 {len(key)}，值不打印）", "how_to_fix": "",
            })

        if url and urlparse(url).scheme in ("http", "https") and urlparse(url).hostname:
            probe = self.probe_telemetry(url.rstrip("/"), key)
            checks.append({
                "item": "真实探测遥测 /health",
                "status": probe["status"], "owner": HUMAN,
                "detail": probe.get("detail", ""),
                "how_to_fix": probe.get("how_to_fix", HEALTH_CONTRACT_DOC),
                "latency_ms": probe.get("latency_ms"),
            })
        else:
            checks.append({
                "item": "真实探测遥测 /health", "status": MISSING, "owner": HUMAN,
                "detail": "端点未配置，未做真实探测", "how_to_fix": "先配置 TELEMETRY_ENDPOINT",
            })
        return checks

    def probe_telemetry(self, base_url: str, key: str) -> Dict[str, Any]:
        request = urllib.request.Request(base_url + "/health", method="GET", headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "game-agent-player-validation/1.0",
        })
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                code = response.getcode()
                raw = response.read(4096).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return {"status": UNREACHABLE, "detail": f"/health 返回 HTTP {exc.code}",
                    "latency_ms": int((time.time() - started) * 1000)}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"status": UNREACHABLE, "detail": f"无法连接：{type(exc).__name__}",
                    "latency_ms": int((time.time() - started) * 1000)}
        latency_ms = int((time.time() - started) * 1000)

        if code >= 400:
            return {"status": UNREACHABLE, "detail": f"/health 返回 HTTP {code}", "latency_ms": latency_ms}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"status": IDENTITY_UNVERIFIED, "detail": "/health 返回的不是 JSON",
                    "latency_ms": latency_ms, "how_to_fix": HEALTH_CONTRACT_DOC}
        if not isinstance(payload, dict) or str(payload.get("service", "")).strip() != "telemetry":
            return {"status": IDENTITY_UNVERIFIED,
                    "detail": f"/health 自报 service={payload.get('service', '空')}，期望 telemetry",
                    "latency_ms": latency_ms, "how_to_fix": HEALTH_CONTRACT_DOC}
        if str(payload.get("status", "")).strip().lower() not in ("ok", "healthy", "up"):
            return {"status": IDENTITY_UNVERIFIED,
                    "detail": f"/health 自报 status={payload.get('status', '空')}",
                    "latency_ms": latency_ms, "how_to_fix": HEALTH_CONTRACT_DOC}
        return {"status": PASS, "detail": "遥测服务身份自证通过", "latency_ms": latency_ms}

    # ---------- 试点队列 ----------

    def register_cohort(self, cohort_id: str, source: str, size: int,
                        window_days: int, contact: str = "", notes: str = "") -> Dict[str, Any]:
        if not cohort_id.strip():
            raise ValueError("cohort_id 不能为空")
        if not source.strip():
            raise ValueError("必须写明玩家来源（如：内部员工 / 社群招募 / 商店测试渠道）")
        if size <= 0:
            raise ValueError("size 必须为正整数")

        cohorts = self.list_cohorts()
        record = {
            "cohort_id": cohort_id.strip(),
            "source": source.strip(),
            "size": int(size),
            "window_days": int(window_days),
            "contact": contact.strip(),
            "notes": notes,
            "registered_at": _now_iso(),
        }
        cohorts = [c for c in cohorts if c.get("cohort_id") != record["cohort_id"]]
        cohorts.append(record)
        self.validation_root.mkdir(parents=True, exist_ok=True)
        self.cohort_path.write_text(json.dumps(cohorts, ensure_ascii=False, indent=2), encoding="utf-8")
        return record

    def list_cohorts(self) -> List[Dict[str, Any]]:
        if not self.cohort_path.is_file():
            return []
        try:
            data = json.loads(self.cohort_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    # ---------- 事件真实性 ----------

    @staticmethod
    def load_events(events_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        path = Path(events_path)
        real: List[Dict[str, Any]] = []
        simulated: List[Dict[str, Any]] = []
        unknown: List[Dict[str, Any]] = []
        if not path.is_file():
            return real, simulated, unknown
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                bucket = classify_event(event)
                (real if bucket == "real" else simulated if bucket == "simulated" else unknown).append(event)
        return real, simulated, unknown

    def summarize(self, events_path: Optional[Path]) -> Dict[str, Any]:
        if not events_path:
            return {"status": NO_REAL_PLAYER_DATA, "reason": "未指定事件文件",
                    "real_events": 0, "real_players": 0, "simulated_events": 0, "unknown_events": 0}

        real, simulated, unknown = self.load_events(events_path)
        players = {str(e.get("user_id", "")) for e in real if str(e.get("user_id", ""))}
        summary: Dict[str, Any] = {
            "events_path": str(events_path),
            "real_events": len(real),
            "real_players": len(players),
            "simulated_events": len(simulated),
            "unknown_events": len(unknown),
        }
        if real:
            timestamps = [float(e.get("timestamp", 0)) for e in real if e.get("timestamp") is not None]
            summary["first_event"] = _iso_from_ts(min(timestamps)) if timestamps else None
            summary["last_event"] = _iso_from_ts(max(timestamps)) if timestamps else None
            summary["status"] = PASS
            summary["note"] = "存在标记为真实来源的事件；留存等指标需基于这些事件计算"
        else:
            summary["status"] = NO_REAL_PLAYER_DATA
            summary["note"] = ("没有可判定为真实来源的玩家事件；"
                               "不得用模拟/无来源事件宣称留存、时长或付费")
        return summary

    def diagnose(self, events_path: Optional[Path] = None) -> Dict[str, Any]:
        telemetry = self.check_telemetry_endpoint()
        cohorts = self.list_cohorts()
        summary = self.summarize(events_path)

        cohort_check = {
            "item": "真实玩家试点队列",
            "status": PASS if cohorts else MISSING,
            "owner": HUMAN,
            "detail": f"已登记 {len(cohorts)} 个试点，覆盖 {sum(int(c.get('size', 0)) for c in cohorts)} 人"
                      if cohorts else "未登记任何真实玩家试点",
            "how_to_fix": "" if cohorts else
                          "用 player-cohort 登记招募来源、人数与时间窗；"
                          "没有真实玩家就没有留存与付费数据",
        }
        data_check = {
            "item": "真实玩家事件数据",
            "status": summary.get("status", NO_REAL_PLAYER_DATA),
            "owner": HUMAN,
            "detail": (f"真实事件 {summary.get('real_events', 0)} 条 / 真实玩家 "
                       f"{summary.get('real_players', 0)} 人；模拟 {summary.get('simulated_events', 0)} 条；"
                       f"无来源标记 {summary.get('unknown_events', 0)} 条"),
            "how_to_fix": "" if summary.get("status") == PASS else
                          "接入遥测并让客户端事件带 properties.source=real_player，"
                          "否则无法证明数据来自真人",
        }

        checks = telemetry + [cohort_check, data_check]
        blocking = [c for c in checks if c["status"] != PASS]
        return {
            "status": PASS if not blocking else NO_REAL_PLAYER_DATA,
            "ready": not blocking,
            "checks": checks,
            "cohorts": cohorts,
            "data_summary": summary,
            "note": "模拟事件仅用于功能自测，不得用于对外宣称留存/付费/时长",
        }


def _iso_from_ts(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat(timespec="seconds")
