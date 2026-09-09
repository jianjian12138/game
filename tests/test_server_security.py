import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import server
from core.security_guard import (
    get_configured_token,
    has_valid_bearer_token,
    is_loopback_host,
)


class _AuthProbe:
    def __init__(self, headers, expected_token, require_auth=True):
        self.headers = headers
        self.client_address = ("127.0.0.1", 12345)
        self.server = SimpleNamespace(
            require_auth=require_auth,
            expected_token=expected_token,
        )
        self.responses = []

    def send_json(self, status_code, data):
        self.responses.append((status_code, data))

    _check_auth_and_rate_limit = server.StudioHTTPHandler._check_auth_and_rate_limit


class TestServerSecurity(unittest.TestCase):
    def setUp(self):
        server.global_rate_limiter.clear()

    def test_loopback_detection(self):
        self.assertTrue(is_loopback_host("127.0.0.1"))
        self.assertTrue(is_loopback_host("::1"))
        self.assertTrue(is_loopback_host("localhost"))
        self.assertFalse(is_loopback_host("0.0.0.0"))
        self.assertFalse(is_loopback_host("192.168.1.10"))

    def test_token_is_read_without_mutating_environment(self):
        environ = {"GAME_STUDIO_TOKEN": "  test-token  "}
        self.assertEqual(get_configured_token(environ), "test-token")
        self.assertEqual(environ, {"GAME_STUDIO_TOKEN": "  test-token  "})

    def test_non_loopback_without_token_is_rejected_before_server_creation(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(server, "HTTPServer") as http_server:
            with self.assertRaisesRegex(RuntimeError, "GAME_STUDIO_TOKEN"):
                server.run_server(host="0.0.0.0", port=0)
            http_server.assert_not_called()

    def test_non_loopback_with_token_configures_auth_without_serving(self):
        with patch.dict(os.environ, {"GAME_STUDIO_TOKEN": "test-token"}, clear=True), patch.object(server, "HTTPServer") as http_server:
            fake_server = http_server.return_value
            fake_server.serve_forever.side_effect = KeyboardInterrupt
            with redirect_stdout(io.StringIO()):
                server.run_server(host="0.0.0.0", port=0)
            self.assertTrue(fake_server.require_auth)
            self.assertEqual(fake_server.expected_token, "test-token")

    def test_non_loopback_requires_bearer_token_for_management_requests(self):
        missing = _AuthProbe({}, "test-token")
        self.assertFalse(missing._check_auth_and_rate_limit())
        self.assertEqual(missing.responses[0][0], 401)

        wrong = _AuthProbe({"Authorization": "Bearer wrong"}, "test-token")
        self.assertFalse(wrong._check_auth_and_rate_limit())
        self.assertEqual(wrong.responses[0][0], 401)

        valid = _AuthProbe({"Authorization": "Bearer test-token"}, "test-token")
        self.assertTrue(valid._check_auth_and_rate_limit())
        self.assertEqual(valid.responses, [])

    def test_loopback_without_token_remains_compatible(self):
        probe = _AuthProbe({}, "", require_auth=False)
        self.assertTrue(probe._check_auth_and_rate_limit())
        self.assertEqual(probe.responses, [])

    def test_bearer_parser_does_not_accept_malformed_authorization(self):
        self.assertFalse(has_valid_bearer_token({}, "test-token"))
        self.assertFalse(has_valid_bearer_token({"Authorization": "test-token"}, "test-token"))
        self.assertFalse(has_valid_bearer_token({"Authorization": "Basic test-token"}, "test-token"))
        self.assertTrue(
            has_valid_bearer_token({"Authorization": "bearer test-token"}, "test-token")
        )


if __name__ == "__main__":
    unittest.main()
