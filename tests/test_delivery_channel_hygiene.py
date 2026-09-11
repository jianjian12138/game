"""tests/test_delivery_channel_hygiene.py — 交付卫生与渠道体检门禁验收。

覆盖两件事：
  1. Agent 交付给用户时，秘密文件与明文密钥必须被检出、排除、打码（不外泄）。
  2. 外部渠道体检必须如实报出「缺什么 / 谁负责 / 怎么补」，且永不打印凭据值。

诚实红线：
  - 扫描结论是「未命中已知模式」，不是「绝对无泄露」；测试也按此口径断言。
  - 测试用的密钥串是构造的假值，不接触任何真实凭据；不依赖网络与真实商店账号。
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline import delivery_hygiene as dh
from pipeline import store_submission as ss
from pipeline.channel_doctor import ChannelDoctor, HUMAN, INVALID, MISSING, NEEDS_HUMAN, OK

ROOT = Path(__file__).resolve().parent.parent

FAKE_OPENAI_KEY = "sk-TESTONLY0123456789abcdef"
FAKE_WECHAT_APPID_OK = "wx0123456789abcdef"
FAKE_WECHAT_APPID_BAD = "wxZZZ-not-hex-appid"


def _png_bytes(width: int, height: int) -> bytes:
    """最小 PNG 头（仅用于尺寸解析，非完整图像），避免引入图像库依赖。"""
    return (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
            + struct.pack(">II", width, height) + b"\x00" * 24)


class TestRedact(unittest.TestCase):
    def test_openai_style_key_is_redacted(self):
        text = f'api key = "{FAKE_OPENAI_KEY}"'
        out = dh.redact(text)
        self.assertNotIn(FAKE_OPENAI_KEY, out)
        self.assertIn(dh.REDACTED, out)

    def test_private_key_block_is_redacted(self):
        out = dh.redact("-----BEGIN RSA PRIVATE KEY-----\nabcdef\n")
        self.assertIn(dh.REDACTED, out)

    def test_json_secret_value_is_redacted(self):
        out = dh.redact(json.dumps({"apiKey": FAKE_OPENAI_KEY}))
        self.assertNotIn(FAKE_OPENAI_KEY, out)

    def test_normal_text_untouched(self):
        text = "python game_agent.py channel-doctor --json"
        self.assertEqual(dh.redact(text), text)

    def test_redact_values_by_exact_value(self):
        token = "SUPERSECRETTOKEN123"
        out = dh.redact_values(f"--token {token} --other", [token])
        self.assertNotIn(token, out)
        self.assertIn("--other", out)


class TestScanAndAudit(unittest.TestCase):
    def test_clean_dir_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('hello')\n", encoding="utf-8")
            report = dh.audit_delivery(root)
            self.assertEqual(report["status"], dh.CLEAN)
            self.assertTrue(report["deliverable"])
            self.assertEqual(report["findings"], [])

    def test_env_file_is_flagged_by_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("SOME_KEY=whatever\n", encoding="utf-8")
            report = dh.audit_delivery(root)
            self.assertEqual(report["status"], dh.LEAK)
            self.assertIn("secret_filename", [f["rule"] for f in report["findings"]])

    def test_llm_endpoints_json_is_flagged_by_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "config"
            root.mkdir()
            (root / "llm_endpoints.json").write_text("{}", encoding="utf-8")
            report = dh.audit_delivery(root.parent)
            self.assertEqual(report["status"], dh.LEAK)

    def test_plaintext_key_in_python_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "leak.py").write_text(f'KEY = "{FAKE_OPENAI_KEY}"\n', encoding="utf-8")
            report = dh.audit_delivery(root)
            self.assertEqual(report["status"], dh.LEAK)
            self.assertIn("openai_style_key", [f["rule"] for f in report["findings"]])

    def test_finding_snippet_is_itself_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "leak.py").write_text(f'KEY = "{FAKE_OPENAI_KEY}"\n', encoding="utf-8")
            report = dh.audit_delivery(root)
            blob = json.dumps(report["findings"], ensure_ascii=False)
            self.assertNotIn(FAKE_OPENAI_KEY, blob)


class TestSanitizeCopy(unittest.TestCase):
    def test_secret_files_excluded_and_product_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dst = Path(tmp) / "dst"
            src.mkdir()
            (src / ".env").write_text("REAL_SECRET=value123\n", encoding="utf-8")
            (src / "config").mkdir()
            (src / "config" / "llm_endpoints.json").write_text(
                json.dumps({"apiKey": FAKE_OPENAI_KEY}), encoding="utf-8")
            (src / "main.py").write_text("print('ok')\n", encoding="utf-8")

            result = dh.sanitize_copy(src, dst)

            self.assertEqual(result["status"], dh.CLEAN)
            self.assertFalse((dst / ".env").exists())
            self.assertFalse((dst / "config" / "llm_endpoints.json").exists())
            self.assertTrue((dst / "main.py").exists())
            reasons = {item["reason"] for item in result["excluded_files"]}
            self.assertTrue(any("secret_filename" in r for r in reasons))

    def test_content_scan_blocks_unlisted_secret_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dst = Path(tmp) / "dst"
            src.mkdir()
            (src / "notes.txt").write_text(f"my key is {FAKE_OPENAI_KEY}\n", encoding="utf-8")
            (src / "keep.txt").write_text("nothing secret here\n", encoding="utf-8")

            result = dh.sanitize_copy(src, dst)

            self.assertFalse((dst / "notes.txt").exists())
            self.assertTrue((dst / "keep.txt").exists())
            self.assertTrue(any("content_scan" in i["reason"] for i in result["excluded_files"]))


class TestChannelDoctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.dist = self.root / "dist"
        self.assets = self.root / "store_assets"
        self.dist.mkdir()
        self.assets.mkdir()
        self.saved_env = {
            k: os.environ.pop(k, None)
            for k in ("WECHAT_APPID", "WECHAT_CI_KEY_PATH", "STEAM_USER",
                      "STEAM_APP_ID", "ITCH_BUTLER_TARGET", "PWA_DEPLOY_BASE_URL")
        }

    def tearDown(self):
        for key, value in self.saved_env.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value
        self.tmp.cleanup()

    def test_missing_credentials_reported_as_human_blocking(self):
        doctor = ChannelDoctor(self.dist, self.root / "none.json", self.assets)
        report = doctor.diagnose("wechat")
        self.assertEqual(report["status"], NEEDS_HUMAN)
        self.assertGreater(report["blocking_human"], 0)
        cred_checks = [c for c in report["checks"] if c["item"].startswith("凭据")]
        self.assertTrue(all(c["status"] == MISSING for c in cred_checks))
        self.assertTrue(all(c["owner"] == HUMAN for c in cred_checks))
        self.assertTrue(all(c["how_to_fix"] for c in cred_checks))

    def test_invalid_credential_format_is_not_silently_ok(self):
        os.environ["WECHAT_APPID"] = FAKE_WECHAT_APPID_BAD
        doctor = ChannelDoctor(self.dist, self.root / "none.json", self.assets)
        report = doctor.diagnose("wechat")
        check = next(c for c in report["checks"] if c["item"] == "凭据 WECHAT_APPID")
        self.assertEqual(check["status"], INVALID)

    def test_valid_credential_format_passes(self):
        os.environ["WECHAT_APPID"] = FAKE_WECHAT_APPID_OK
        key_file = self.root / "private.key"
        key_file.write_text("dummy", encoding="utf-8")
        os.environ["WECHAT_CI_KEY_PATH"] = str(key_file)
        doctor = ChannelDoctor(self.dist, self.root / "none.json", self.assets)
        report = doctor.diagnose("wechat")
        for name in ("凭据 WECHAT_APPID", "凭据 WECHAT_CI_KEY_PATH"):
            check = next(c for c in report["checks"] if c["item"] == name)
            self.assertEqual(check["status"], OK, name)

    def test_credential_value_never_appears_in_report(self):
        os.environ["WECHAT_APPID"] = FAKE_WECHAT_APPID_OK
        doctor = ChannelDoctor(self.dist, self.root / "none.json", self.assets)
        report = doctor.diagnose("wechat")
        self.assertNotIn(FAKE_WECHAT_APPID_OK, json.dumps(report, ensure_ascii=False))

    def test_human_materials_listed_with_reason(self):
        doctor = ChannelDoctor(self.dist, self.root / "none.json", self.assets)
        report = doctor.diagnose("steam")
        self.assertTrue(report["human_materials"])
        for mat in report["human_materials"]:
            self.assertTrue(mat["item"] and mat["how"] and mat["why"])

    def test_missing_package_attributed_to_agent(self):
        doctor = ChannelDoctor(self.dist, self.root / "none.json", self.assets)
        report = doctor.diagnose("itch")
        pkg = next(c for c in report["checks"] if c["item"] == "渠道分发包")
        self.assertEqual(pkg["status"], MISSING)
        self.assertEqual(pkg["owner"], "agent")

    def test_asset_size_checked_for_real(self):
        (self.assets / "cover.png").write_bytes(_png_bytes(315, 250))
        (self.assets / "screenshot_1.png").write_bytes(_png_bytes(640, 360))
        doctor = ChannelDoctor(self.dist, self.root / "none.json", self.assets)
        report = doctor.diagnose("itch")
        cover = next(c for c in report["checks"] if c["item"] == "素材 cover")
        shot = next(c for c in report["checks"] if c["item"] == "素材 screenshot_1")
        self.assertEqual(cover["status"], OK)
        self.assertEqual(shot["status"], INVALID)
        self.assertIn("640x360", shot["detail"])

    def test_unknown_channel_reports_error(self):
        doctor = ChannelDoctor(self.dist, self.root / "none.json", self.assets)
        report = doctor.diagnose("nintendo")
        self.assertIn("errors", report)

    def test_diagnose_all_covers_all_specs(self):
        doctor = ChannelDoctor(self.dist, self.root / "none.json", self.assets)
        payload = doctor.diagnose_all()
        self.assertEqual(len(payload["channels"]), len(ss.STORE_SPECS))
        self.assertEqual(payload["needs_human"], list(ss.STORE_SPECS))


class TestSubmissionRedaction(unittest.TestCase):
    """上架命令与上传器输出在进入返回结构/落盘报告前必须打码。"""

    def test_dry_run_command_is_redacted(self):
        secret_token = "CHANNELSECRET123456"
        channel = "_test_channel"
        spec = {
            "label": "Test Channel",
            "package_subdir": "_test",
            "credential_env": ("_TEST_CHANNEL_TOKEN",),
            "uploader": "python",
            "upload_args": lambda bundle, meta: ["-c", f"print('{secret_token}')"],
            "required_metadata": ["title", "version"],
            "required_assets": [],
            "max_package_mb": None,
        }
        ss.STORE_SPECS[channel] = spec
        os.environ["_TEST_CHANNEL_TOKEN"] = secret_token
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "dist" / "_test").mkdir(parents=True)
                service = ss.StoreSubmission(root / "dist", root / "submission")
                # 找不到 python 可执行文件时，本用例只验证打码路径不走真实执行，
                # 因此这里改用 dry_run=False 之外的分支：READY 前会先返回 NEEDS_RUNTIME_TOOL。
                meta = {"title": "t", "version": "1.0.0", "privacy_policy_url": "https://example.com/p",
                        "age_rating": "12+", "third_party_sdks": []}
                result = service.submit(channel, meta, dry_run=True)
                if result["status"] == ss.READY:
                    for arg in result["command"]:
                        self.assertNotIn(secret_token, arg)
                else:
                    self.assertEqual(result["status"], ss.NEEDS_RUNTIME_TOOL)
        finally:
            os.environ.pop("_TEST_CHANNEL_TOKEN", None)
            ss.STORE_SPECS.pop(channel, None)

    def test_bundle_report_is_redacted_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "dist" / "itch").mkdir(parents=True)
            service = ss.StoreSubmission(root / "dist", root / "submission")
            meta = {"title": "t", "short_desc": "s", "long_desc": "l", "keywords": "k",
                    "category": "c", "age_rating": "12+", "version": "1.0.0",
                    "privacy_policy_url": f"https://example.com/p?token={FAKE_OPENAI_KEY}",
                    "third_party_sdks": []}
            report = service.build_bundle("itch", meta)
            on_disk = (Path(report["bundle_path"]) / "store_metadata.json").read_text(encoding="utf-8")
            self.assertNotIn(FAKE_OPENAI_KEY, on_disk)
            readiness = (Path(report["bundle_path"]) / "readiness_report.json").read_text(encoding="utf-8")
            self.assertNotIn(FAKE_OPENAI_KEY, readiness)


if __name__ == "__main__":
    unittest.main(verbosity=2)
