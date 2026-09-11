"""tests/test_env_check.py — 环境自检总表与 .env 加载的验收。

覆盖两件事：
  1. env-check 聚合四个缺口的体检结果，缺项如实列出，不打印凭据值。
  2. .env 解析正确（跳过注释、剥离引号、不覆盖已存在的环境变量），
     且入口可显式加载——原先只有导入 llm_gateway 才加载，
     会让「填了 .env 却报未配置」。
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from core.llm_gateway import _load_dotenv
from pipeline.env_check import MISSING, OK, UNREACHABLE, IDENTITY_UNVERIFIED, EnvCheck


class _StatsHandler(BaseHTTPRequestHandler):
    payload: dict = {}

    def do_GET(self):  # noqa: N802 - stdlib 约定
        body = json.dumps(self.payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def _serve(payload: dict) -> HTTPServer:
    handler = type("BoundHandler", (_StatsHandler,), {"payload": payload})
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class TestEnvCheck(unittest.TestCase):
    def setUp(self):
        self.saved = {k: os.environ.pop(k, None) for k in (
            "COMFYUI_URL", "GODOT_PATH", "WECHAT_APPID", "WECHAT_CI_KEY_PATH",
            "STEAM_USER", "STEAM_APP_ID", "ITCH_BUTLER_TARGET", "PWA_DEPLOY_BASE_URL",
            "PAYMENT_SANDBOX_URL", "PAYMENT_SANDBOX_KEY", "ADS_SANDBOX_URL", "ADS_SANDBOX_KEY",
            "MULTIPLAYER_SANDBOX_URL", "MULTIPLAYER_SANDBOX_KEY", "STAGING_BASE_URL",
            "TELEMETRY_ENDPOINT", "TELEMETRY_KEY")}

    def tearDown(self):
        for key, value in self.saved.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value

    def test_aggregate_report_structure(self):
        report = EnvCheck(probe=False).run()
        self.assertEqual(len(report["groups"]), 5)
        self.assertGreater(report["total"], 0)
        self.assertEqual(report["status"], MISSING)
        self.assertGreater(report["pending_count"], 0)

    def test_no_probe_never_prints_credentials(self):
        os.environ["PAYMENT_SANDBOX_KEY"] = "SUPERSECRET123456"
        os.environ["WECHAT_APPID"] = "wx0123456789abcdef"
        report = EnvCheck(probe=False).run()
        blob = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("SUPERSECRET123456", blob)
        self.assertNotIn("wx0123456789abcdef", blob)

    def test_comfyui_identity_verified(self):
        server = _serve({"system": {"os": "nt"}, "devices": [{"name": "RTX"}]})
        try:
            os.environ["COMFYUI_URL"] = f"http://127.0.0.1:{server.server_port}"
            rows = EnvCheck(probe=True).check_toolchain()
            comfy = next(r for r in rows if r["item"] == "ComfyUI 出图服务")
            self.assertEqual(comfy["status"], OK)
        finally:
            server.shutdown()
            server.server_close()

    def test_comfyui_wrong_service_is_unverified(self):
        server = _serve({"hello": "world"})
        try:
            os.environ["COMFYUI_URL"] = f"http://127.0.0.1:{server.server_port}"
            rows = EnvCheck(probe=True).check_toolchain()
            comfy = next(r for r in rows if r["item"] == "ComfyUI 出图服务")
            self.assertEqual(comfy["status"], IDENTITY_UNVERIFIED)
        finally:
            server.shutdown()
            server.server_close()

    def test_comfyui_unreachable(self):
        os.environ["COMFYUI_URL"] = "http://127.0.0.1:9"
        rows = EnvCheck(probe=True).check_toolchain()
        comfy = next(r for r in rows if r["item"] == "ComfyUI 出图服务")
        self.assertEqual(comfy["status"], UNREACHABLE)

    def test_channels_group_reports_pending(self):
        rows = EnvCheck(probe=False).check_channels()
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["owner"] == "human" for r in rows))
        self.assertTrue(any(r["status"] != OK for r in rows))


class TestDotEnvLoading(unittest.TestCase):
    def test_parses_comments_quotes_and_does_not_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "# 这是注释\n"
                "\n"
                "PAYMENT_SANDBOX_URL=https://sandbox.example.com\n"
                'PAYMENT_SANDBOX_KEY="quoted-key"\n'
                "ALREADY_SET=from_file\n",
                encoding="utf-8")
            os.environ["ALREADY_SET"] = "from_environ"
            try:
                _load_dotenv(env_file)
                self.assertEqual(os.environ["PAYMENT_SANDBOX_URL"], "https://sandbox.example.com")
                self.assertEqual(os.environ["PAYMENT_SANDBOX_KEY"], "quoted-key")
                self.assertEqual(os.environ["ALREADY_SET"], "from_environ")
            finally:
                for key in ("PAYMENT_SANDBOX_URL", "PAYMENT_SANDBOX_KEY", "ALREADY_SET"):
                    os.environ.pop(key, None)

    def test_missing_file_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            _load_dotenv(Path(tmp) / "not_exists.env")


if __name__ == "__main__":
    unittest.main(verbosity=2)
