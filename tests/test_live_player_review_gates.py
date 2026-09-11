"""tests/test_live_player_review_gates.py — 缺口二/三/四的门禁验收。

缺口二 线上服务：缺凭据如实报缺失；**连通不等于可用**，服务端必须自证身份。
缺口三 人工复核：无具名签署就是没复核，G7 全绿也不放行生产。
缺口四 真实玩家：没有真实来源标记的事件，一律不得计入留存/付费/时长。

测试用本地 HTTP 服务模拟对端，不依赖外网与真实账号。
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from pipeline.human_review import APPROVED, BLOCKED, CLEARED, HumanReviewBoard
from pipeline.live_service_doctor import (
    IDENTITY_UNVERIFIED, INVALID, MISSING, PASS, UNREACHABLE, LiveServiceDoctor,
)
from pipeline.player_validation import NO_REAL_PLAYER_DATA, PlayerValidation, classify_event


class _HealthHandler(BaseHTTPRequestHandler):
    payload: dict = {}
    raw_body: str = ""

    def do_GET(self):  # noqa: N802 - stdlib 约定
        body = self.raw_body.encode("utf-8") if self.raw_body else json.dumps(self.payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def _serve(payload: dict = None, raw_body: str = "") -> HTTPServer:
    handler = type("BoundHandler", (_HealthHandler,), {"payload": payload or {}, "raw_body": raw_body})
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class TestLiveServiceDoctor(unittest.TestCase):
    def setUp(self):
        self.saved = {k: os.environ.pop(k, None) for k in (
            "PAYMENT_SANDBOX_URL", "PAYMENT_SANDBOX_KEY", "ADS_SANDBOX_URL", "ADS_SANDBOX_KEY",
            "MULTIPLAYER_SANDBOX_URL", "MULTIPLAYER_SANDBOX_KEY", "STAGING_BASE_URL")}

    def tearDown(self):
        for key, value in self.saved.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value

    def test_missing_config_reports_how_to_fix(self):
        report = LiveServiceDoctor().diagnose_sandbox("payment")
        self.assertFalse(report["ready"])
        self.assertEqual(report["checks"][0]["status"], MISSING)
        self.assertTrue(report["checks"][0]["how_to_fix"])
        self.assertEqual(report["checks"][0]["owner"], "human")

    def test_plaintext_http_to_remote_is_rejected(self):
        os.environ["PAYMENT_SANDBOX_URL"] = "http://sandbox.example.com"
        os.environ["PAYMENT_SANDBOX_KEY"] = "dummy-key"
        report = LiveServiceDoctor().diagnose_sandbox("payment")
        self.assertEqual(report["checks"][0]["status"], INVALID)
        self.assertIn("https", report["checks"][0]["how_to_fix"])

    def test_unreachable_endpoint(self):
        os.environ["PAYMENT_SANDBOX_URL"] = "http://127.0.0.1:9"
        os.environ["PAYMENT_SANDBOX_KEY"] = "dummy-key"
        report = LiveServiceDoctor().diagnose_sandbox("payment")
        probe = report["checks"][-1]
        self.assertEqual(probe["status"], UNREACHABLE)

    def test_identity_contract_passes_on_loopback(self):
        server = _serve({"service": "payment", "status": "ok", "environment": "sandbox"})
        try:
            os.environ["PAYMENT_SANDBOX_URL"] = f"http://127.0.0.1:{server.server_port}"
            os.environ["PAYMENT_SANDBOX_KEY"] = "dummy-key"
            report = LiveServiceDoctor().diagnose_sandbox("payment")
            self.assertTrue(report["ready"], report["checks"])
            self.assertEqual(report["checks"][-1]["status"], PASS)
        finally:
            server.shutdown()
            server.server_close()

    def test_wrong_service_identity_is_not_pass(self):
        """防伪核心：能连通但自报家门不对，绝不能算作服务可用。"""
        server = _serve({"service": "someone-else", "status": "ok", "environment": "sandbox"})
        try:
            os.environ["PAYMENT_SANDBOX_URL"] = f"http://127.0.0.1:{server.server_port}"
            os.environ["PAYMENT_SANDBOX_KEY"] = "dummy-key"
            report = LiveServiceDoctor().diagnose_sandbox("payment")
            probe = report["checks"][-1]
            self.assertEqual(probe["status"], IDENTITY_UNVERIFIED)
            self.assertFalse(report["ready"])
        finally:
            server.shutdown()
            server.server_close()

    def test_non_json_health_is_unverified(self):
        server = _serve(raw_body="<html>ok</html>")
        try:
            os.environ["ADS_SANDBOX_URL"] = f"http://127.0.0.1:{server.server_port}"
            os.environ["ADS_SANDBOX_KEY"] = "dummy-key"
            report = LiveServiceDoctor().diagnose_sandbox("ads")
            self.assertEqual(report["checks"][-1]["status"], IDENTITY_UNVERIFIED)
        finally:
            server.shutdown()
            server.server_close()

    def test_staging_requires_environment_field(self):
        server = _serve({"service": "game", "status": "ok", "environment": "production"})
        try:
            os.environ["STAGING_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
            report = LiveServiceDoctor().diagnose_staging()
            self.assertEqual(report["checks"][-1]["status"], IDENTITY_UNVERIFIED)
        finally:
            server.shutdown()
            server.server_close()

    def test_staging_passes_with_correct_environment(self):
        server = _serve({"service": "game", "status": "ok", "environment": "staging"})
        try:
            os.environ["STAGING_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
            report = LiveServiceDoctor().diagnose_staging()
            self.assertTrue(report["ready"], report["checks"])
        finally:
            server.shutdown()
            server.server_close()

    def test_reference_server_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = LiveServiceDoctor.write_reference_server(Path(tmp))
            self.assertTrue(path.is_file())
            self.assertIn("def do_GET", path.read_text(encoding="utf-8"))


class TestHumanReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.saved = os.environ.get("GAME_REVIEW_ROOT")
        os.environ["GAME_REVIEW_ROOT"] = str(self.root / "reviews")
        self.board = HumanReviewBoard()
        self.artifact = self.root / "hero.png"
        self.artifact.write_bytes(b"png-bytes")

    def tearDown(self):
        if self.saved is not None:
            os.environ["GAME_REVIEW_ROOT"] = self.saved
        else:
            os.environ.pop("GAME_REVIEW_ROOT", None)
        self.tmp.cleanup()

    def test_ticket_records_sha256(self):
        ticket = self.board.create_ticket("run_1", "art", self.artifact)
        self.assertEqual(len(ticket["artifact_sha256"]), 64)
        self.assertEqual(ticket["status"], "PENDING")
        self.assertTrue(ticket["checklist"])

    def test_missing_artifact_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.board.create_ticket("run_1", "art", self.root / "nope.png")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            self.board.create_ticket("run_1", "unknown_kind", self.artifact)

    def test_submit_requires_named_reviewer(self):
        ticket = self.board.create_ticket("run_1", "art", self.artifact)
        with self.assertRaises(ValueError):
            self.board.submit(ticket["ticket_id"], "   ", APPROVED)

    def test_submit_rejects_invalid_verdict(self):
        ticket = self.board.create_ticket("run_1", "art", self.artifact)
        with self.assertRaises(ValueError):
            self.board.submit(ticket["ticket_id"], "alice", "MAYBE")

    def test_status_blocked_until_all_kinds_approved(self):
        for kind in ("art", "audio", "release"):
            path = self.root / f"{kind}.bin"
            path.write_bytes(f"{kind}".encode())
            ticket = self.board.create_ticket("run_1", kind, path)
            self.board.submit(ticket["ticket_id"], "alice", APPROVED)
        self.assertEqual(self.board.status("run_1")["status"], CLEARED)

    def test_partial_approval_still_blocked(self):
        ticket = self.board.create_ticket("run_1", "art", self.artifact)
        self.board.submit(ticket["ticket_id"], "alice", APPROVED)
        report = self.board.status("run_1")
        self.assertEqual(report["status"], BLOCKED)
        self.assertIn("audio", report["missing"])
        self.assertFalse(self.board.production_gate("run_1")["allowed"])

    def test_no_review_at_all_is_blocked(self):
        report = self.board.status("run_2")
        self.assertEqual(report["status"], BLOCKED)
        self.assertEqual(sorted(report["missing"]), ["art", "audio", "release"])

    def test_modified_artifact_is_flagged(self):
        ticket = self.board.create_ticket("run_1", "art", self.artifact)
        self.artifact.write_bytes(b"tampered-bytes")
        updated = self.board.submit(ticket["ticket_id"], "alice", APPROVED)
        self.assertFalse(updated["artifact_sha256_matches"])


class TestPlayerValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.saved_env = {k: os.environ.pop(k, None) for k in ("TELEMETRY_ENDPOINT", "TELEMETRY_KEY")}
        self.saved_root = os.environ.get("GAME_PLAYER_VALIDATION_ROOT")
        os.environ["GAME_PLAYER_VALIDATION_ROOT"] = str(self.root / "pv")
        self.validator = PlayerValidation()

    def tearDown(self):
        for key, value in self.saved_env.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value
        if self.saved_root is not None:
            os.environ["GAME_PLAYER_VALIDATION_ROOT"] = self.saved_root
        else:
            os.environ.pop("GAME_PLAYER_VALIDATION_ROOT", None)
        self.tmp.cleanup()

    def test_classify_event_sources(self):
        self.assertEqual(classify_event({"properties": {"source": "real_player"}}), "real")
        self.assertEqual(classify_event({"properties": {"source": "beta"}}), "real")
        self.assertEqual(classify_event({"properties": {"simulated": True}}), "simulated")
        self.assertEqual(classify_event({"properties": {"source": "synthetic"}}), "simulated")
        self.assertEqual(classify_event({"properties": {}}), "unknown")

    def _events_file(self, events):
        path = self.root / "events.jsonl"
        path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
        return path

    def test_simulated_events_do_not_count_as_real(self):
        path = self._events_file([
            {"user_id": "bot_1", "event_name": "level_start", "timestamp": 1.0,
             "properties": {"source": "simulated"}},
            {"user_id": "p_1", "event_name": "level_start", "timestamp": 2.0,
             "properties": {"source": "real_player"}},
        ])
        summary = self.validator.summarize(path)
        self.assertEqual(summary["real_events"], 1)
        self.assertEqual(summary["simulated_events"], 1)
        self.assertEqual(summary["real_players"], 1)
        self.assertEqual(summary["status"], PASS)

    def test_no_real_data_is_reported_honestly(self):
        path = self._events_file([
            {"user_id": "bot_1", "event_name": "level_start", "timestamp": 1.0,
             "properties": {"source": "synthetic"}},
        ])
        summary = self.validator.summarize(path)
        self.assertEqual(summary["status"], NO_REAL_PLAYER_DATA)
        self.assertEqual(summary["real_players"], 0)
        self.assertIn("不得", summary["note"])

    def test_untagged_source_is_not_real(self):
        path = self._events_file([{"user_id": "p_1", "event_name": "level_start", "timestamp": 1.0}])
        summary = self.validator.summarize(path)
        self.assertEqual(summary["real_events"], 0)
        self.assertEqual(summary["unknown_events"], 1)
        self.assertEqual(summary["status"], NO_REAL_PLAYER_DATA)

    def test_cohort_registration_validation(self):
        with self.assertRaises(ValueError):
            self.validator.register_cohort("c1", "", 10, 7)
        with self.assertRaises(ValueError):
            self.validator.register_cohort("c1", "社群招募", 0, 7)
        record = self.validator.register_cohort("c1", "社群招募", 30, 14, contact="丁建")
        self.assertEqual(record["size"], 30)
        self.assertEqual(len(self.validator.list_cohorts()), 1)

    def test_telemetry_missing_reports_how_to_fix(self):
        report = self.validator.diagnose(None)
        self.assertFalse(report["ready"])
        checks = {c["item"]: c for c in report["checks"]}
        self.assertEqual(checks["配置 TELEMETRY_ENDPOINT"]["status"], MISSING)
        self.assertTrue(checks["配置 TELEMETRY_ENDPOINT"]["how_to_fix"])

    def test_telemetry_identity_contract(self):
        server = _serve({"service": "telemetry", "status": "ok", "environment": "staging"})
        try:
            os.environ["TELEMETRY_ENDPOINT"] = f"http://127.0.0.1:{server.server_port}"
            os.environ["TELEMETRY_KEY"] = "ingest-key"
            report = self.validator.diagnose(None)
            checks = {c["item"]: c for c in report["checks"]}
            self.assertEqual(checks["真实探测遥测 /health"]["status"], PASS)
        finally:
            server.shutdown()
            server.server_close()

    def test_telemetry_wrong_service_unverified(self):
        server = _serve({"service": "ads", "status": "ok", "environment": "sandbox"})
        try:
            os.environ["TELEMETRY_ENDPOINT"] = f"http://127.0.0.1:{server.server_port}"
            os.environ["TELEMETRY_KEY"] = "ingest-key"
            report = self.validator.diagnose(None)
            checks = {c["item"]: c for c in report["checks"]}
            self.assertEqual(checks["真实探测遥测 /health"]["status"], IDENTITY_UNVERIFIED)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
