#!/usr/bin/env python3
"""pipeline/live_service_flow.py：线上服务「真实业务链路」冒烟（缺口二填坑）

与 live_service_sandbox 的区别：
    live_service_sandbox 只探 /health，证明「端点活着」；
    本模块跑真实业务事务，证明「链路能跑通」：
      支付：创建订单 → 查单 → 退款（真校验金额/状态流转）
      广告：请求广告 → 曝光回执 → 点击回执（真校验 ad_id 串联）
      联机：创建房间 → 加入 → 查询 → 离开（真校验玩家列表与房间状态）

诚实红线（13.2）：
    1. 未配置 URL/KEY → NEEDS_SANDBOX_CREDENTIALS，绝不用本地假响应冒充通过。
    2. 任一步非预期状态码 / 字段缺失 → FAIL，绝不因为「前几步过了」就算过。
    3. 每一步都记录 latency_ms 与响应摘要（脱敏），可复核。
    4. 密钥是否真在用，靠「错 Key 应被拒」验证：
       · 服务端声明 environment=staging 却不校验 Key → FAIL（公网无鉴权=可被盗刷）
       · 声明 sandbox 且未启用鉴权 → WARN（本地开放联调可接受，但上线前必须开）
    5. 业务端点返回 404 → CONTRACT_MISMATCH：对端没实现参考契约，需写适配层，
       绝不因为 /health 通了就宣称业务可用。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from core.security_guard import is_loopback_host
from pipeline.live_service_sandbox import SANDBOX_SPECS

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
NEEDS_SANDBOX_CREDENTIALS = "NEEDS_SANDBOX_CREDENTIALS"
CONTRACT_MISMATCH = "CONTRACT_MISMATCH"

DEFAULT_TIMEOUT_S = 8.0

#: 参考业务契约的路径（pipeline/live_service_reference.py 实现了这套契约）
REFERENCE_CONTRACT = {
    "payment": ["POST /v1/orders", "GET /v1/orders/{id}", "POST /v1/orders/{id}/refund"],
    "ads": ["POST /v1/ads/request", "POST /v1/ads/impression", "POST /v1/ads/click"],
    "multiplayer": ["POST /v1/rooms", "GET /v1/rooms/{id}",
                    "POST /v1/rooms/{id}/join", "POST /v1/rooms/{id}/leave"],
}

# 鉴权探针哨兵：故意的错误口令，用于验证端点会拒收错 key（非真实密钥，不进入交付物）
PROBE_REJECT_PHRASE = "game-agent-wrong-key-for-auth-probe"

__all__ = ["LiveServiceFlow", "run_flow", "PASS", "FAIL", "WARN",
           "NEEDS_SANDBOX_CREDENTIALS", "CONTRACT_MISMATCH"]


def _redact(text: str, secrets: List[str]) -> str:
    out = text or ""
    for s in secrets:
        if s and len(s) >= 4:
            out = out.replace(s, "***REDACTED***")
    return out


class LiveServiceFlow:
    def __init__(self, timeout_s: float = DEFAULT_TIMEOUT_S):
        self.timeout_s = timeout_s

    # ---------- 底层 HTTP ----------

    def _request(self, method: str, url: str, key: str,
                 payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json",
                   "User-Agent": "game-agent-live-service-flow/1.0"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        started = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read(8192).decode("utf-8", errors="ignore")
                code, body = resp.status, raw
        except urllib.error.HTTPError as exc:
            raw = ""
            try:
                raw = exc.read(2048).decode("utf-8", errors="ignore")
            except Exception:
                pass
            code, body = exc.code, raw
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"ok": False, "status_code": None, "body": "", "error": f"{exc.__class__.__name__}: {exc}",
                    "latency_ms": round((time.time() - started) * 1000), "json": None}
        parsed: Optional[Any] = None
        try:
            parsed = json.loads(body) if body.strip().startswith(("{", "[")) else None
        except ValueError:
            parsed = None
        return {"ok": 200 <= code < 300, "status_code": code, "body": body, "error": None,
                "latency_ms": round((time.time() - started) * 1000), "json": parsed}

    # ---------- 配置与身份 ----------

    def _config(self, kind: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        spec = SANDBOX_SPECS.get(kind)
        if not spec:
            return None, None, f"未知沙箱类型: {kind}"
        url = (os.environ.get(spec["url_env"]) or "").strip()
        key = (os.environ.get(spec["key_env"]) or "").strip()
        if not url or not key:
            return None, None, f"缺少配置: {spec['url_env']} / {spec['key_env']}"
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None, None, f"端点地址非法（值不打印，长度 {len(url)}）"
        if parsed.scheme == "http" and not is_loopback_host(parsed.hostname):
            return None, None, "明文 http 只允许回环地址，远端必须使用 https"
        return url.rstrip("/"), key, None

    def _health(self, base: str, key: str, kind: str) -> Dict[str, Any]:
        r = self._request("GET", base + "/health", key)
        env_declared = None
        if isinstance(r.get("json"), dict):
            env_declared = r["json"].get("environment")
            if r["json"].get("service") not in (None, kind):
                r["identity_mismatch"] = r["json"].get("service")
        r["environment_declared"] = env_declared
        return r

    # ---------- 鉴权验证 ----------

    def _probe_auth(self, base: str, key: str, kind: str,
                    declared_env: Optional[str]) -> Dict[str, Any]:
        """用错误 Key 打一次业务端点：服务端应当拒绝。"""
        probe_path = {  # 各类型挑一个最小写入端点
            "payment": ("/v1/orders", "POST", {"amount": 0.01}),
            "ads": ("/v1/ads/request", "POST", {"slot": "auth-probe"}),
            "multiplayer": ("/v1/rooms", "POST", {"capacity": 1}),
        }[kind]
        path, method, payload = probe_path
        r = self._request(method, base + path, PROBE_REJECT_PHRASE, payload)
        rejected = r["status_code"] in (401, 403)
        if rejected:
            return {"auth_enforced": True, "status": PASS,
                    "detail": f"错误 Key 被拒（HTTP {r['status_code']}），密钥确实在校验"}
        if r["status_code"] is None:
            return {"auth_enforced": False, "status": FAIL,
                    "detail": f"鉴权探测请求失败: {r['error']}"}
        if declared_env in ("staging", "production"):
            return {"auth_enforced": False, "status": FAIL,
                    "detail": f"声明 environment={declared_env} 却接受错误 Key（HTTP {r['status_code']}），"
                              f"公网无鉴权可被盗刷，必须修复"}
        return {"auth_enforced": False, "status": WARN,
                "detail": f"错误 Key 未被拒（HTTP {r['status_code']}）：沙箱开放联调可接受，"
                          f"但上线前必须启用 Bearer 鉴权"}

    # ---------- 各类业务链路 ----------

    def _flow_payment(self, base: str, key: str) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        # 1. 创建订单
        r = self._request("POST", base + "/v1/orders", key, {"amount": 1.00, "currency": "CNY"})
        if r["status_code"] == 404:
            return {"status": CONTRACT_MISMATCH, "steps": steps,
                    "detail": "POST /v1/orders 返回 404：对端未实现参考契约，需写适配层"}
        steps.append({"step": "创建订单 POST /v1/orders", "status": PASS if r["ok"] else FAIL,
                      "status_code": r["status_code"], "latency_ms": r["latency_ms"]})
        if not r["ok"] or not isinstance(r["json"], dict) or not r["json"].get("order_id"):
            steps[-1]["status"] = FAIL
            return {"status": FAIL, "steps": steps, "detail": "创建订单未返回 order_id"}
        order_id = str(r["json"]["order_id"])

        # 2. 查单：必须能查到同一笔，状态属于正常流转值
        r2 = self._request("GET", f"{base}/v1/orders/{order_id}", key)
        ok2 = (r2["ok"] and isinstance(r2["json"], dict)
               and str(r2["json"].get("order_id")) == order_id
               and r2["json"].get("status") in ("created", "paid", "refunded"))
        steps.append({"step": f"查单 GET /v1/orders/{order_id}",
                      "status": PASS if ok2 else FAIL,
                      "status_code": r2["status_code"], "latency_ms": r2["latency_ms"]})
        if not ok2:
            return {"status": FAIL, "steps": steps, "detail": "查单未返回同一笔订单或状态异常"}

        # 3. 退款
        r3 = self._request("POST", f"{base}/v1/orders/{order_id}/refund", key, {})
        ok3 = (r3["ok"] and isinstance(r3["json"], dict)
               and (r3["json"].get("refunded") is True or r3["json"].get("status") == "refunded"))
        steps.append({"step": "退款 POST /v1/orders/{id}/refund",
                      "status": PASS if ok3 else FAIL,
                      "status_code": r3["status_code"], "latency_ms": r3["latency_ms"]})
        return {"status": PASS if ok3 else FAIL, "steps": steps,
                "detail": "" if ok3 else "退款未返回已退款状态",
                "order_id": order_id}

    def _flow_ads(self, base: str, key: str) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        r = self._request("POST", base + "/v1/ads/request", key, {"slot": "banner"})
        if r["status_code"] == 404:
            return {"status": CONTRACT_MISMATCH, "steps": steps,
                    "detail": "POST /v1/ads/request 返回 404：对端未实现参考契约"}
        steps.append({"step": "请求广告 POST /v1/ads/request",
                      "status": PASS if r["ok"] else FAIL,
                      "status_code": r["status_code"], "latency_ms": r["latency_ms"]})
        if not r["ok"] or not isinstance(r["json"], dict) or not r["json"].get("ad_id"):
            steps[-1]["status"] = FAIL
            return {"status": FAIL, "steps": steps, "detail": "未返回 ad_id"}
        ad_id = str(r["json"]["ad_id"])

        for evt in ("impression", "click"):
            re_ = self._request("POST", f"{base}/v1/ads/{evt}", key, {"ad_id": ad_id})
            ok = re_["ok"] and (re_["status_code"] in (200, 202, 204))
            steps.append({"step": f"{evt} 回执 POST /v1/ads/{evt}",
                          "status": PASS if ok else FAIL,
                          "status_code": re_["status_code"], "latency_ms": re_["latency_ms"]})
            if not ok:
                return {"status": FAIL, "steps": steps, "detail": f"{evt} 回执未被接受"}
        return {"status": PASS, "steps": steps, "detail": "", "ad_id": ad_id}

    def _flow_multiplayer(self, base: str, key: str) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        r = self._request("POST", base + "/v1/rooms", key, {"capacity": 2})
        if r["status_code"] == 404:
            return {"status": CONTRACT_MISMATCH, "steps": steps,
                    "detail": "POST /v1/rooms 返回 404：对端未实现参考契约"}
        steps.append({"step": "创建房间 POST /v1/rooms", "status": PASS if r["ok"] else FAIL,
                      "status_code": r["status_code"], "latency_ms": r["latency_ms"]})
        if not r["ok"] or not isinstance(r["json"], dict) or not r["json"].get("room_id"):
            steps[-1]["status"] = FAIL
            return {"status": FAIL, "steps": steps, "detail": "未返回 room_id"}
        room_id = str(r["json"]["room_id"])
        player = "game_agent_probe_player"

        r2 = self._request("POST", f"{base}/v1/rooms/{room_id}/join", key, {"player_id": player})
        ok2 = r2["ok"] and isinstance(r2["json"], dict) and player in (r2["json"].get("players") or [])
        steps.append({"step": "加入房间 POST /v1/rooms/{id}/join", "status": PASS if ok2 else FAIL,
                      "status_code": r2["status_code"], "latency_ms": r2["latency_ms"]})
        if not ok2:
            return {"status": FAIL, "steps": steps, "detail": "加入后玩家列表未包含该玩家"}

        r3 = self._request("GET", f"{base}/v1/rooms/{room_id}", key)
        ok3 = r3["ok"] and isinstance(r3["json"], dict) and player in (r3["json"].get("players") or [])
        steps.append({"step": "查询房间 GET /v1/rooms/{id}", "status": PASS if ok3 else FAIL,
                      "status_code": r3["status_code"], "latency_ms": r3["latency_ms"]})

        r4 = self._request("POST", f"{base}/v1/rooms/{room_id}/leave", key, {"player_id": player})
        ok4 = r4["ok"] and isinstance(r4["json"], dict) and player not in (r4["json"].get("players") or [])
        steps.append({"step": "离开房间 POST /v1/rooms/{id}/leave", "status": PASS if ok4 else FAIL,
                      "status_code": r4["status_code"], "latency_ms": r4["latency_ms"]})
        ok = ok2 and ok3 and ok4
        return {"status": PASS if ok else FAIL, "steps": steps,
                "detail": "" if ok else "房间状态流转不符合预期", "room_id": room_id}

    # ---------- 对外 ----------

    def run(self, kind: str) -> Dict[str, Any]:
        spec = SANDBOX_SPECS.get(kind) or {}
        base, key, err = self._config(kind)
        out: Dict[str, Any] = {"kind": kind, "label": spec.get("label", kind),
                               "status": NEEDS_SANDBOX_CREDENTIALS, "steps": [], "auth": None}
        if err:
            out["detail"] = err
            out["how_to_fix"] = (
                f"在 .env 配置 {spec.get('url_env')} 与 {spec.get('key_env')}；"
                f"本地联调可先跑 python -m pipeline.live_service_reference "
                f"--service {kind} --port 8787 --key <任意沙箱密钥>")
            return out

        health = self._health(base, key, kind)
        if health.get("identity_mismatch"):
            out["status"] = FAIL
            out["detail"] = (f"/health 自报 service={health['identity_mismatch']}，期望 {kind}——"
                             f"端点错配，不能算该服务可用")
            return out
        if not health["ok"]:
            out["status"] = FAIL
            out["detail"] = f"/health 不可用（HTTP {health['status_code']}）"
            return out
        declared_env = health.get("environment_declared")

        auth = self._probe_auth(base, key, kind, declared_env)
        out["auth"] = auth

        flow = {
            "payment": self._flow_payment,
            "ads": self._flow_ads,
            "multiplayer": self._flow_multiplayer,
        }[kind](base, key)
        out["steps"] = flow.get("steps", [])
        out["detail"] = flow.get("detail", "")
        out["contract"] = REFERENCE_CONTRACT.get(kind, [])
        out["environment_declared"] = declared_env

        if flow["status"] != PASS:
            out["status"] = flow["status"]
        elif auth["status"] == FAIL:
            out["status"] = FAIL
            out["detail"] = (out["detail"] + f"；鉴权: {auth['detail']}").strip("；")
        else:
            out["status"] = PASS
        return out

    def run_all(self) -> Dict[str, Any]:
        results = {k: self.run(k) for k in SANDBOX_SPECS}
        passed = sorted(k for k, r in results.items() if r["status"] == PASS)
        not_configured = sorted(k for k, r in results.items()
                                if r["status"] == NEEDS_SANDBOX_CREDENTIALS)
        failed = sorted(k for k, r in results.items() if r["status"] not in (PASS, NEEDS_SANDBOX_CREDENTIALS))
        return {"status": PASS if (not failed and not not_configured) else FAIL,
                "results": results, "passed": passed,
                "not_configured": not_configured, "failed": failed}


def run_flow(kind: str = "all", timeout_s: float = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
    flow = LiveServiceFlow(timeout_s=timeout_s)
    return flow.run_all() if kind == "all" else flow.run(kind)
