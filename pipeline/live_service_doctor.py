#!/usr/bin/env python3
"""pipeline/live_service_doctor.py: 线上服务体检（缺口二）

已有能力：pipeline/live_service_sandbox.py 能真实冒烟，缺凭据如实报
NEEDS_SANDBOX_CREDENTIALS，未配置 Staging 一律拒绝晋升。这部分不用重做。

本模块补的是两个真实缺口：

    1. 缺口清单：现在只说「没配」，没说「去哪拿 / 服务端要满足什么」。
       本模块逐项输出 status / detail / how_to_fix / owner。

    2. 身份自证（假绿风险）：原冒烟只要对端返回 2xx 就判 PASS，
       意味着把 URL 错配成任意一个可达站点也会「通过」。
       本模块要求服务端的 /health 自报家门：
           {"service": "payment", "status": "ok", "environment": "sandbox"}
       字段不匹配即判 IDENTITY_UNVERIFIED，绝不用连通性冒充服务可用。

服务端契约由本模块给出可直接运行的参考实现（--emit-reference），
丁建照着把真实服务暴露出来即可，不需要猜格式。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from core.security_guard import is_loopback_host
from pipeline.live_service_sandbox import SANDBOX_SPECS

PASS = "PASS"
MISSING = "MISSING"
INVALID = "INVALID"
UNREACHABLE = "UNREACHABLE"
IDENTITY_UNVERIFIED = "IDENTITY_UNVERIFIED"

HUMAN = "human"

DEFAULT_TIMEOUT_S = 8.0

# ── /health 自证契约：服务端必须这样回答 ───────────────────────────────────
HEALTH_CONTRACT_DOC = (
    "服务端 GET /health 必须返回 JSON："
    '{"service": "<payment|ads|multiplayer|game>", "status": "ok", "environment": "<sandbox|staging>"}'
)

SANDBOX_APPLY_HOWTO: Dict[str, str] = {
    "payment": "向支付服务商申请沙箱环境，拿到沙箱 API 地址与沙箱密钥（不是生产密钥）",
    "ads": "向广告平台申请测试广告位与沙箱报表接口；激励视频需可回调的测试回调地址",
    "multiplayer": "部署联机中继/匹配服务，或申请第三方联机服务的沙箱实例",
}

REFERENCE_SERVER_PY = '''#!/usr/bin/env python3
"""线上服务 /health 参考实现（符合 game-agent 身份自证契约）

直接运行：python reference_health_server.py --service payment --environment sandbox --port 8787
然后配置：PAYMENT_SANDBOX_URL=http://127.0.0.1:8787   PAYMENT_SANDBOX_KEY=<任意沙箱密钥>
即可让 python game_agent.py live-doctor 判为 PASS。

生产/Staging 部署时请换成真实框架，但 /health 的返回结构必须保持一致：
    {"service": ..., "status": "ok", "environment": ...}
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    service = "payment"
    environment = "sandbox"

    def do_GET(self) -> None:  # noqa: N802 - stdlib 约定
        if self.path.rstrip("/").endswith("/health"):
            body = json.dumps({
                "service": self.service,
                "status": "ok",
                "environment": self.environment,
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="payment",
                        choices=["payment", "ads", "multiplayer", "game"])
    parser.add_argument("--environment", default="sandbox", choices=["sandbox", "staging"])
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    handler = type("BoundHandler", (HealthHandler,),
                   {"service": args.service, "environment": args.environment})
    server = HTTPServer(("127.0.0.1", args.port), handler)
    print(f"health server on http://127.0.0.1:{args.port}/health "
          f"service={args.service} environment={args.environment}")
    server.serve_forever()


if __name__ == "__main__":
    main()
'''

__all__ = ["LiveServiceDoctor", "diagnose_all", "PASS", "MISSING", "IDENTITY_UNVERIFIED"]


class LiveServiceDoctor:
    """支付 / 广告 / 联机沙箱 + Staging 部署的逐项体检。"""

    def __init__(self, timeout_s: float = DEFAULT_TIMEOUT_S):
        self.timeout_s = timeout_s

    # ---------- 凭据与环境 ----------

    @staticmethod
    def _credential_check(env_name: str, hint: str) -> Dict[str, Any]:
        raw = (os.environ.get(env_name) or "").strip()
        if not raw:
            return {
                "item": f"配置 {env_name}", "status": MISSING, "owner": HUMAN,
                "detail": "环境变量未设置",
                "how_to_fix": f"在 .env（已被 gitignore）中设置 {env_name}；{hint}",
            }
        return {
            "item": f"配置 {env_name}", "status": PASS, "owner": HUMAN,
            "detail": f"已设置（长度 {len(raw)}，值不打印）", "how_to_fix": "",
        }

    @staticmethod
    def _url_check(env_name: str, allow_http_loopback: bool = True) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        raw = (os.environ.get(env_name) or "").strip()
        if not raw:
            return None, {
                "item": f"配置 {env_name}", "status": MISSING, "owner": HUMAN,
                "detail": "环境变量未设置",
                "how_to_fix": f"在 .env 中设置 {env_name}；远端必须为 https，本地联调可用 http://127.0.0.1:<port>",
            }
        parsed = urlparse(raw)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None, {
                "item": f"配置 {env_name}", "status": INVALID, "owner": HUMAN,
                "detail": f"不是合法的 http/https 地址（值不打印，长度 {len(raw)}）",
                "how_to_fix": "填写完整地址，例如 https://sandbox.example.com",
            }
        if parsed.scheme == "http" and not (allow_http_loopback and is_loopback_host(parsed.hostname)):
            return None, {
                "item": f"配置 {env_name}", "status": INVALID, "owner": HUMAN,
                "detail": "远端地址使用了明文 http",
                "how_to_fix": "远端一律改用 https；明文 http 仅允许回环地址（本地联调）",
            }
        return raw.rstrip("/"), {
            "item": f"配置 {env_name}", "status": PASS, "owner": HUMAN,
            "detail": f"已设置，主机 {parsed.hostname}，协议 {parsed.scheme}", "how_to_fix": "",
        }

    # ---------- 真实探测 + 身份自证 ----------

    def probe_health(self, base_url: str, health_path: str, key: str,
                     required_service: Optional[str] = None,
                     required_environment: Optional[str] = None) -> Dict[str, Any]:
        """真实访问 /health，并校验对端自报身份。连通不等于正确。"""
        url = base_url + health_path
        request = urllib.request.Request(url, method="GET", headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "game-agent-live-service-doctor/1.0",
        })
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                status_code = response.getcode()
                raw = response.read(4096).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return {"status": UNREACHABLE, "http_status": exc.code,
                    "detail": f"/health 返回 HTTP {exc.code}",
                    "latency_ms": int((time.time() - started) * 1000)}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"status": UNREACHABLE, "http_status": None,
                    "detail": f"无法连接 {url}：{type(exc).__name__}",
                    "latency_ms": int((time.time() - started) * 1000)}
        latency_ms = int((time.time() - started) * 1000)

        if status_code >= 400:
            return {"status": UNREACHABLE, "http_status": status_code,
                    "detail": f"/health 返回 HTTP {status_code}", "latency_ms": latency_ms}

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"status": IDENTITY_UNVERIFIED, "http_status": status_code,
                    "detail": "/health 返回的不是 JSON，无法自证身份",
                    "latency_ms": latency_ms, "how_to_fix": HEALTH_CONTRACT_DOC}

        if not isinstance(payload, dict):
            return {"status": IDENTITY_UNVERIFIED, "http_status": status_code,
                    "detail": "/health 返回的 JSON 不是对象", "latency_ms": latency_ms,
                    "how_to_fix": HEALTH_CONTRACT_DOC}

        service = str(payload.get("service", "")).strip()
        environment = str(payload.get("environment", "")).strip()
        health = str(payload.get("status", "")).strip().lower()

        if health not in ("ok", "healthy", "up"):
            return {"status": IDENTITY_UNVERIFIED, "http_status": status_code,
                    "detail": f"/health 自报状态为 {health or '空'}，不是 ok",
                    "latency_ms": latency_ms, "how_to_fix": HEALTH_CONTRACT_DOC}

        if required_service and service != required_service:
            return {"status": IDENTITY_UNVERIFIED, "http_status": status_code,
                    "detail": f"/health 自报 service={service or '空'}，期望 {required_service}；"
                              f"端点可能配错成了别的服务",
                    "latency_ms": latency_ms, "how_to_fix": HEALTH_CONTRACT_DOC}

        if required_environment and environment != required_environment:
            return {"status": IDENTITY_UNVERIFIED, "http_status": status_code,
                    "detail": f"/health 自报 environment={environment or '空'}，期望 {required_environment}",
                    "latency_ms": latency_ms, "how_to_fix": HEALTH_CONTRACT_DOC}

        return {"status": PASS, "http_status": status_code,
                "detail": f"身份自证通过（service={service or '-'}，environment={environment or '-'}）",
                "latency_ms": latency_ms}

    # ---------- 单项体检 ----------

    def diagnose_sandbox(self, kind: str) -> Dict[str, Any]:
        spec = SANDBOX_SPECS.get(kind)
        if spec is None:
            return {"kind": kind, "status": INVALID, "checks": [],
                    "errors": [f"未知沙箱类型: {kind}，可选: {', '.join(SANDBOX_SPECS)}"]}

        checks: List[Dict[str, Any]] = []
        url, url_check = self._url_check(spec["url_env"])
        checks.append(url_check)
        checks.append(self._credential_check(spec["key_env"], SANDBOX_APPLY_HOWTO.get(kind, "")))

        ready = url is not None and checks[1]["status"] == PASS
        probe: Dict[str, Any] = {"status": MISSING, "detail": "凭据未齐，未做真实探测"}
        if ready:
            key = (os.environ.get(spec["key_env"]) or "").strip()
            probe = self.probe_health(url, spec["health_path"], key,
                                      required_service=kind, required_environment="sandbox")
        checks.append({
            "item": f"真实探测 {spec['label']} /health",
            "status": probe["status"], "owner": HUMAN,
            "detail": probe.get("detail", ""),
            "how_to_fix": probe.get("how_to_fix", SANDBOX_APPLY_HOWTO.get(kind, "")),
            "latency_ms": probe.get("latency_ms"),
        })

        blocking = [c for c in checks if c["status"] != PASS]
        return {
            "kind": kind, "label": spec["label"],
            "status": PASS if not blocking else blocking[0]["status"],
            "ready": not blocking,
            "checks": checks,
        }

    def diagnose_staging(self) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []
        url, url_check = self._url_check("STAGING_BASE_URL", allow_http_loopback=True)
        checks.append(url_check)

        if url is None:
            checks.append({"item": "真实探测 Staging /health", "status": MISSING, "owner": HUMAN,
                           "detail": "未配置，未做真实探测",
                           "how_to_fix": "先部署预发布环境，再在 .env 配置 STAGING_BASE_URL"})
        else:
            probe = self.probe_health(url, "/health", "", required_service=None,
                                      required_environment="staging")
            checks.append({
                "item": "真实探测 Staging /health",
                "status": probe["status"], "owner": HUMAN,
                "detail": probe.get("detail", ""),
                "how_to_fix": probe.get("how_to_fix", HEALTH_CONTRACT_DOC),
                "latency_ms": probe.get("latency_ms"),
            })

        blocking = [c for c in checks if c["status"] != PASS]
        return {
            "kind": "staging", "label": "Staging 预发布环境",
            "status": PASS if not blocking else blocking[0]["status"],
            "ready": not blocking,
            "checks": checks,
        }

    def diagnose_all(self) -> Dict[str, Any]:
        reports = [self.diagnose_sandbox(k) for k in SANDBOX_SPECS]
        staging = self.diagnose_staging()
        reports.append(staging)
        return {
            "services": reports,
            "ready": [r["kind"] for r in reports if r.get("ready")],
            "blocked": [r["kind"] for r in reports if not r.get("ready")],
        }

    # ---------- 参考实现 ----------

    @staticmethod
    def write_reference_server(out_dir: Path, filename: str = "reference_health_server.py") -> Path:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        path.write_text(REFERENCE_SERVER_PY, encoding="utf-8")
        return path


def diagnose_all(timeout_s: float = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
    return LiveServiceDoctor(timeout_s).diagnose_all()
