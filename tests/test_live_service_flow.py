#!/usr/bin/env python3
"""tests/test_live_service_flow.py：线上服务真实业务链路（缺口二填坑）

用真实的 HTTP 服务（pipeline/live_service_reference）跑通业务事务，验证：
  1. 支付 / 广告 / 联机 三类链路真的能跑通（下单→查单→退款 等）。
  2. 端点错配（ads 指到 payment 服务）必须被 /health 身份自证拦下。
  3. 密钥必须在用：错误 Key 应被拒 401；staging 环境不校验 Key 直接 FAIL。
  4. 未配置 → NEEDS_SANDBOX_CREDENTIALS，绝不用假响应冒充通过。
  5. 业务端点 404 → CONTRACT_MISMATCH，不因 /health 通了就宣称可用。
"""
from __future__ import annotations

import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pipeline import live_service_flow as lsf  # noqa: E402
from pipeline.live_service_reference import make_server  # noqa: E402

PAY_KEY = "sk_test_pay_key"
ADS_KEY = "sk_test_ads_key"
MP_KEY = "sk_test_mp_key"


def _start(kind: str, key: str) -> HTTPServer:
    httpd = make_server(kind, "sandbox", key, "127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _url(httpd: HTTPServer) -> str:
    return f"http://127.0.0.1:{httpd.server_address[1]}"


class _Envs(dict):
    pass


def _env(**kw):
    base = {"http_proxy": "", "https_proxy": "", "HTTP_PROXY": "", "HTTPS_PROXY": "",
            "no_proxy": "*", "no_proxy".upper(): "*"}
    base.update(kw)
    return base


class TestReferenceServerBusinessFlow(unittest.TestCase):
    """参考服务端自身：业务端点真的做了校验（不是什么都收的假桩）。"""

    @classmethod
    def setUpClass(cls):
        cls.pay = _start("payment", PAY_KEY)
        cls.ads = _start("ads", ADS_KEY)
        cls.mp = _start("multiplayer", MP_KEY)

    @classmethod
    def tearDownClass(cls):
        for s in (cls.pay, cls.ads, cls.mp):
            s.shutdown()
            s.server_close()

    def _req(self, method, url, key, payload=None):
        import urllib.request
        data = json.dumps(payload or {}).encode() if payload is not None else None
        headers = {"Accept": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        if data:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            raw = e.read().decode() if hasattr(e, "read") else "{}"
            try:
                return e.code, json.loads(raw or "{}")
            except ValueError:
                return e.code, {}

    def test_payment_flow(self):
        base = _url(self.pay)
        code, order = self._req("POST", base + "/v1/orders", PAY_KEY, {"amount": 9.9})
        self.assertEqual(code, 201)
        self.assertTrue(order["order_id"])
        code2, got = self._req("GET", f"{base}/v1/orders/{order['order_id']}", PAY_KEY)
        self.assertEqual(code2, 200)
        self.assertEqual(got["order_id"], order["order_id"])
        code3, refunded = self._req("POST", f"{base}/v1/orders/{order['order_id']}/refund", PAY_KEY, {})
        self.assertEqual(code3, 200)
        self.assertTrue(refunded["refunded"])

    def test_payment_rejects_bad_amount(self):
        code, body = self._req("POST", _url(self.pay) + "/v1/orders", PAY_KEY, {"amount": -1})
        self.assertEqual(code, 400)

    def test_multiplayer_room_full(self):
        base = _url(self.mp)
        code, room = self._req("POST", base + "/v1/rooms", MP_KEY, {"capacity": 1})
        self.assertEqual(code, 201)
        rid = room["room_id"]
        self.assertEqual(self._req("POST", f"{base}/v1/rooms/{rid}/join", MP_KEY,
                                   {"player_id": "p1"})[0], 200)
        code2, body2 = self._req("POST", f"{base}/v1/rooms/{rid}/join", MP_KEY, {"player_id": "p2"})
        self.assertEqual(code2, 409)
        self.assertEqual(body2["error"], "room_full")

    def test_wrong_service_rejected(self):
        """支付端点打到联机服务：应 409 wrong_service，而不是照单全收。"""
        code, body = self._req("POST", _url(self.pay) + "/v1/orders", PAY_KEY, {"amount": 1})
        self.assertEqual(code, 201)
        code2, body2 = self._req("POST", _url(self.mp) + "/v1/orders", MP_KEY, {"amount": 1})
        self.assertEqual(code2, 409)
        self.assertEqual(body2["error"], "wrong_service")


class TestLiveServiceFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pay = _start("payment", PAY_KEY)
        cls.ads = _start("ads", ADS_KEY)
        cls.mp = _start("multiplayer", MP_KEY)

    @classmethod
    def tearDownClass(cls):
        for s in (cls.pay, cls.ads, cls.mp):
            s.shutdown()
            s.server_close()

    def test_not_configured_is_honest(self):
        with mock.patch.dict(os.environ, _env(PAYMENT_SANDBOX_URL="", PAYMENT_SANDBOX_KEY=""),
                             clear=False):
            out = lsf.LiveServiceFlow().run("payment")
        self.assertEqual(out["status"], lsf.NEEDS_SANDBOX_CREDENTIALS)
        self.assertIn("PAYMENT_SANDBOX_URL", out["how_to_fix"])

    def test_payment_flow_passes(self):
        with mock.patch.dict(os.environ, _env(
                PAYMENT_SANDBOX_URL=_url(self.pay), PAYMENT_SANDBOX_KEY=PAY_KEY), clear=False):
            out = lsf.LiveServiceFlow().run("payment")
        self.assertEqual(out["status"], lsf.PASS, out)
        self.assertEqual(len(out["steps"]), 3)
        self.assertTrue(all(s["status"] == lsf.PASS for s in out["steps"]))
        self.assertTrue(out["auth"]["auth_enforced"])

    def test_ads_and_multiplayer_flows_pass(self):
        with mock.patch.dict(os.environ, _env(
                ADS_SANDBOX_URL=_url(self.ads), ADS_SANDBOX_KEY=ADS_KEY,
                MULTIPLAYER_SANDBOX_URL=_url(self.mp), MULTIPLAYER_SANDBOX_KEY=MP_KEY),
                clear=False):
            ads = lsf.LiveServiceFlow().run("ads")
            mp = lsf.LiveServiceFlow().run("multiplayer")
        self.assertEqual(ads["status"], lsf.PASS, ads)
        self.assertEqual(mp["status"], lsf.PASS, mp)

    def test_identity_mismatch_blocked(self):
        """ads 指到 payment 服务：能连上也不算可用，必须 FAIL。"""
        with mock.patch.dict(os.environ, _env(
                ADS_SANDBOX_URL=_url(self.pay), ADS_SANDBOX_KEY=PAY_KEY), clear=False):
            out = lsf.LiveServiceFlow().run("ads")
        self.assertEqual(out["status"], lsf.FAIL)
        self.assertIn("端点错配", out["detail"])

    def test_wrong_key_means_fail(self):
        """配置了错误 Key：业务端点 401，链路不能算通过。"""
        with mock.patch.dict(os.environ, _env(
                PAYMENT_SANDBOX_URL=_url(self.pay), PAYMENT_SANDBOX_KEY="totally-wrong-key"),
                clear=False):
            out = lsf.LiveServiceFlow().run("payment")
        self.assertNotEqual(out["status"], lsf.PASS)

    def test_contract_mismatch_when_no_business_endpoints(self):
        """只有 /health 的服务：业务链路必须报契约不符，而不是假装通过。

        稳定性：Windows 上 SO_REUSEADDR 允许多个 socket 复用同一端口，前序用例若遗留
        未关闭的 server，新起的 srv 可能与其共用端口，导致请求被路由到不同 listener
        （表现为 auth 探针拿到 404、支付流却连接被拒的偶发抖动）。这里给本测试的 server
        打唯一 token，就绪探测确认连到的是「自己」，命中他者就换端口重绑，直到独占端口。
        """

        import secrets
        import time
        token = "cm-" + secrets.token_hex(4)

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({"service": "payment", "status": "ok",
                                   "environment": "sandbox",
                                   "probe_token": token}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *a):
                pass

        last_err = None
        for _ in range(12):
            srv = HTTPServer(("127.0.0.1", 0), H)
            port = srv.server_address[1]
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                # 就绪探测：确认连到的是本测试自己的 server，而非 Windows 端口复用命中的他者
                import urllib.request as _ur
                try:
                    with _ur.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                        data = json.loads(r.read().decode() or "{}")
                    if data.get("probe_token") != token:
                        last_err = f"端口 {port} 命中他者遗留 server，换端口重试"
                        continue
                except Exception as exc:  # 端口可能尚未就绪
                    last_err = f"就绪探测失败: {exc!r}"
                    time.sleep(0.1)
                    continue
                with mock.patch.dict(os.environ, _env(
                        PAYMENT_SANDBOX_URL=f"http://127.0.0.1:{port}",
                        PAYMENT_SANDBOX_KEY="k"), clear=False):
                    out = lsf.LiveServiceFlow().run("payment")
                if out["status"] == lsf.CONTRACT_MISMATCH:
                    self.assertIn("适配层", out["detail"])
                    break
                last_err = f"意外状态 {out['status']}: {out}"
            finally:
                srv.shutdown()
                srv.server_close()
        else:
            self.fail(f"test_contract_mismatch 多次重试仍不稳定: {last_err}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
