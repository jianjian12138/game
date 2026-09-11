#!/usr/bin/env python3
"""pipeline/live_service_sandbox.py: 支付 / 广告 / 联机 沙箱链路冒烟

诚实边界（红线 13.2）：
    未配置沙箱端点与凭据时返回 NEEDS_SANDBOX_CREDENTIALS；
    端点不可达、超时或非 2xx 一律 FAIL。
    绝不用「模块存在」「配置已解析」或本地模拟响应冒充沙箱通过——
    只有真正收到对端 HTTP 响应并校验通过才给出 PASS。

凭据隔离：
    沙箱端点必须是 https，或指向回环地址（本地联调）；
    明文 http 访问远端会直接拒绝，避免把沙箱密钥打到公网。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from core.security_guard import is_loopback_host

NEEDS_SANDBOX_CREDENTIALS = "NEEDS_SANDBOX_CREDENTIALS"
PASS = "PASS"
FAIL = "FAIL"

SANDBOX_SPECS: Dict[str, Dict[str, str]] = {
    "payment": {
        "url_env": "PAYMENT_SANDBOX_URL",
        "key_env": "PAYMENT_SANDBOX_KEY",
        "health_path": "/health",
        "label": "支付沙箱",
    },
    "ads": {
        "url_env": "ADS_SANDBOX_URL",
        "key_env": "ADS_SANDBOX_KEY",
        "health_path": "/health",
        "label": "广告沙箱",
    },
    "multiplayer": {
        "url_env": "MULTIPLAYER_SANDBOX_URL",
        "key_env": "MULTIPLAYER_SANDBOX_KEY",
        "health_path": "/health",
        "label": "联机沙箱",
    },
}

DEFAULT_TIMEOUT_S = 8.0


class LiveServiceSandbox:
    """支付 / 广告 / 联机三类在线服务的沙箱冒烟。"""

    @classmethod
    def resolve_config(cls, kind: str) -> Dict[str, Any]:
        spec = SANDBOX_SPECS.get(kind)
        if not spec:
            return {"kind": kind, "ready": False, "reason": f"未知的沙箱类型: {kind}"}
        url = (os.environ.get(spec["url_env"]) or "").strip()
        key = (os.environ.get(spec["key_env"]) or "").strip()
        missing = [name for name, value in ((spec["url_env"], url), (spec["key_env"], key)) if not value]
        if missing:
            return {"kind": kind, "label": spec["label"], "ready": False,
                    "reason": "缺少沙箱配置: " + ", ".join(missing)}
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"kind": kind, "ready": False, "reason": f"沙箱端点协议非法: {url}"}
        if parsed.scheme == "http" and not is_loopback_host(parsed.hostname or ""):
            return {"kind": kind, "ready": False,
                    "reason": "明文 http 只允许回环地址，远端沙箱必须使用 https"}
        return {"kind": kind, "label": spec["label"], "ready": True, "url": url,
                "health_path": spec["health_path"], "key_present": bool(key), "reason": None}

    @classmethod
    def preflight(cls, kind: str) -> Dict[str, Any]:
        config = cls.resolve_config(kind)
        return {
            "kind": kind,
            "status": PASS if config.get("ready") else NEEDS_SANDBOX_CREDENTIALS,
            "can_run": bool(config.get("ready")),
            "reason": config.get("reason"),
        }

    @classmethod
    def smoke(cls, kind: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
        config = cls.resolve_config(kind)
        result: Dict[str, Any] = {
            "kind": kind,
            "label": config.get("label", kind),
            "status": NEEDS_SANDBOX_CREDENTIALS,
            "observed": None,
            "errors": [],
        }
        if not config.get("ready"):
            result["errors"].append(config.get("reason") or "沙箱不可用")
            return result

        url = config["url"].rstrip("/") + config["health_path"]
        key = (os.environ.get(SANDBOX_SPECS[kind]["key_env"]) or "").strip()
        request = urllib.request.Request(url, method="GET", headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "game-agent-live-service-sandbox/1.0",
        })

        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                body = response.read(2048).decode("utf-8", errors="ignore")
                status_code = response.status
        except urllib.error.HTTPError as exc:
            body = exc.read(512).decode("utf-8", errors="ignore") if hasattr(exc, "read") else ""
            status_code = exc.code
            result["errors"].append(f"沙箱返回非 2xx: HTTP {status_code}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            result["status"] = FAIL
            result["errors"].append(f"沙箱端点不可达: {exc.__class__.__name__}: {exc}")
            result["observed"] = {"url": url, "latency_ms": round((time.time() - started) * 1000)}
            return result

        latency_ms = round((time.time() - started) * 1000)
        observed: Dict[str, Any] = {"url": url, "status_code": status_code, "latency_ms": latency_ms,
                                    "body_excerpt": body[:200]}
        result["observed"] = observed

        if not 200 <= status_code < 300:
            result["status"] = FAIL
            if not result["errors"]:
                result["errors"].append(f"沙箱返回非 2xx: HTTP {status_code}")
            return result

        # 支付/广告/联机的健康响应必须能自证身份，避免把任意 200 页面当成沙箱可用
        claimed = None
        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                claimed = payload.get("service") or payload.get("kind") or payload.get("status")
        except (ValueError, TypeError):
            claimed = None
        observed["claimed_service"] = claimed
        if kind not in (claimed or ""):
            result["status"] = FAIL
            result["errors"].append(f"沙箱响应未自证服务身份 (期望包含 {kind}，实得 {claimed!r})")
            return result

        result["status"] = PASS
        return result

    @classmethod
    def smoke_all(cls, timeout_s: float = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
        results = {kind: cls.smoke(kind, timeout_s=timeout_s) for kind in SANDBOX_SPECS}
        return {
            "status": PASS if all(r["status"] == PASS for r in results.values()) else FAIL,
            "results": results,
            "passed": sorted(k for k, r in results.items() if r["status"] == PASS),
            "not_configured": sorted(k for k, r in results.items() if r["status"] == NEEDS_SANDBOX_CREDENTIALS),
            "failed": sorted(k for k, r in results.items() if r["status"] == FAIL),
        }


class StagingSmoke:
    """Staging 环境真实冒烟：Preview → Staging 晋升前必须真的访问到 staging 部署。

    未配置 STAGING_BASE_URL 时返回 NEEDS_SANDBOX_CREDENTIALS，
    绝不允许「没部署过就算通过」。
    """

    @classmethod
    def probe(cls, timeout_s: float = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
        url = (os.environ.get("STAGING_BASE_URL") or "").strip()
        if not url:
            return {"status": NEEDS_SANDBOX_CREDENTIALS, "observed": None,
                    "errors": ["未配置 STAGING_BASE_URL，无法证明 staging 环境已部署"]}
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"status": FAIL, "observed": None, "errors": [f"STAGING_BASE_URL 协议非法: {url}"]}
        if parsed.scheme == "http" and not is_loopback_host(parsed.hostname or ""):
            return {"status": FAIL, "observed": None,
                    "errors": ["明文 http 只允许回环地址，staging 必须使用 https"]}

        started = time.time()
        try:
            request = urllib.request.Request(url, method="GET", headers={"User-Agent": "game-agent-staging-smoke/1.0"})
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                status_code = response.status
                body = response.read(512).decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            body = ""
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"status": FAIL, "errors": [f"staging 不可达: {exc.__class__.__name__}: {exc}"],
                    "observed": {"url": url, "latency_ms": round((time.time() - started) * 1000)}}

        observed = {"url": url, "status_code": status_code, "latency_ms": round((time.time() - started) * 1000),
                    "body_excerpt": body[:200]}
        if not 200 <= status_code < 300:
            return {"status": FAIL, "observed": observed, "errors": [f"staging 返回非 2xx: HTTP {status_code}"]}
        return {"status": PASS, "observed": observed, "errors": []}


__all__ = ["LiveServiceSandbox", "StagingSmoke", "SANDBOX_SPECS", "NEEDS_SANDBOX_CREDENTIALS"]
