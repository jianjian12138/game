"""多端适配器的诚实测试（红线 13.2）。

设计原则（与 test_godot_runtime.py 一致）：
    - 离线（默认）用例验证各端「逻辑正确性」与「缺资源时如实降级」，绝不依赖本机是否装了对应工具。
    - 真实运行用例由环境变量守护（WECHAT_REAL / ANDROID_REAL 等）：仅当本机确有工具才跑，否则跳过。
    - 每个新端缺真实运行时/SDK/构建机时，必须如实返回 NEEDS_RUNTIME_TOOL / NEEDS_SDK / NEEDS_MACOS_BUILDER，
      绝不 PASS；绝不把 web-shell 粉饰成原生。
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.runtime_adapter import RuntimeStatus
from core.host_contract import (
    BrowserContract, GodotContract, MiniProgramContract, NativeContract, get_contract,
)
import pipeline.miniprogram_runtime_adapter as mprat
import pipeline.desktop_shell_adapter as dsrat
import pipeline.android_runtime_adapter as andrat
import pipeline.ios_packaging as ios
import pipeline.store_submission as ss
from core.capability_registry import capability_registry

WECHAT_REAL = os.environ.get("WECHAT_REAL") == "1"
ANDROID_REAL = os.environ.get("ANDROID_REAL") == "1"


def _write_html(path: Path, body: str = "<canvas></canvas>") -> Path:
    path.write_text(f"<!doctype html><html><head></head><body>{body}</body></html>", encoding="utf-8")
    return path


class TestHostContractParsing(unittest.TestCase):
    """四条宿主契约的 parse_evidence 必须落回同一归一化形状，且采不到证据时 available=False。"""

    def test_browser_contract(self):
        c = BrowserContract()
        ev = c.parse_evidence({"frame": 250, "state": "playing", "errors": []})
        self.assertTrue(ev["available"])
        self.assertEqual(ev["frames"], 250)
        self.assertEqual(ev["state"], "playing")
        # 采不到证据：available=False，绝不填数字
        empty = c.parse_evidence(None)
        self.assertFalse(empty["available"])
        self.assertIsNone(empty["frames"])

    def test_godot_contract(self):
        c = GodotContract()
        text = 'GAME_AGENT_PROBE_START\nGAME_AGENT_CONTRACT {"frames": 120}\n'
        ev = c.parse_evidence(text)
        self.assertTrue(ev["available"])
        self.assertEqual(ev["frames"], 120)
        # stderr 含 SCRIPT ERROR -> errors>0
        err_ev = c.parse_evidence("SCRIPT ERROR: Parse Error")
        self.assertGreater(err_ev["errors"], 0)
        # 无 GAME_AGENT_CONTRACT 行 -> 不可用
        self.assertFalse(c.parse_evidence("boot ok").get("available"))

    def test_miniprogram_contract(self):
        c = MiniProgramContract()
        ev = c.parse_evidence({"frames": 90, "state": "playing", "touch_events": 5, "error_count": 0})
        self.assertTrue(ev["available"])
        self.assertEqual(ev["input_events"], 5)
        self.assertFalse(c.parse_evidence(None)["available"])

    def test_native_contract(self):
        c = NativeContract()
        ev = c.parse_evidence({"frames": 60, "state": "playing", "input_events": 3, "errors": 0})
        self.assertTrue(ev["available"])
        self.assertEqual(ev["frames"], 60)
        self.assertFalse(c.parse_evidence(None)["available"])

    def test_get_contract_registry(self):
        for t in ("browser", "godot", "miniprogram", "native"):
            self.assertIsInstance(get_contract(t), (BrowserContract, GodotContract, MiniProgramContract, NativeContract))


class TestGodotRuntimeRefactor(unittest.TestCase):
    """重构后 GodotRuntimeAdapter 必须仍走 GodotContract 解析，且离线诚实。"""

    def test_preflight_needs_runtime_tool_when_no_exe(self):
        a = andrat_import_godot()("")
        res = a.preflight()
        self.assertEqual(res["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)

    def test_run_scenarios_pass_via_contract(self):
        import pipeline.godot_runtime_adapter as grat
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "godot_demo"
            proj.mkdir()
            (proj / "project.godot").write_text('config/name="Demo"\n', encoding="utf-8")
            fake_exe = str(Path(tmp) / "godot_fake.exe")
            a = grat.GodotRuntimeAdapter(godot_executable=fake_exe)
            fake_out = (
                "Godot Engine v4.7.2.stable\nGAME_AGENT_PROBE_START\n"
                'GAME_AGENT_CONTRACT {"frames": 120}\n'
            )
            cp = subprocess.CompletedProcess(args=[], returncode=0, stdout=fake_out, stderr="")
            with mock.patch.object(grat.subprocess, "run", return_value=cp):
                sess = a.launch(proj)
                out = a.run_scenarios(sess)
            self.assertEqual(out["status"], RuntimeStatus.PASS)
            self.assertEqual(out["metrics"]["frames"], 120)

    def test_run_scenarios_fail_on_parse_error(self):
        import pipeline.godot_runtime_adapter as grat
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "godot_demo"
            proj.mkdir()
            (proj / "project.godot").write_text('config/name="Demo"\n', encoding="utf-8")
            fake_exe = str(Path(tmp) / "godot_fake.exe")
            a = grat.GodotRuntimeAdapter(godot_executable=fake_exe)
            cp = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="SCRIPT ERROR: Parse Error: Expected ')'")
            with mock.patch.object(grat.subprocess, "run", return_value=cp):
                sess = a.launch(proj)
                out = a.run_scenarios(sess)
            self.assertEqual(out["status"], RuntimeStatus.FAIL)


def andrat_import_godot():
    import pipeline.godot_runtime_adapter as grat
    return grat.GodotRuntimeAdapter


class TestMiniProgramOfflineHonesty(unittest.TestCase):
    """微信小游戏：缺开发者工具 CLI 一律 NEEDS_RUNTIME_TOOL；静态结构自检不产 PASS。"""

    def test_preflight_needs_runtime_tool_when_no_cli(self):
        a = mprat.MiniProgramRuntimeAdapter(devtools_cli="")
        res = a.preflight()
        self.assertEqual(res["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)
        self.assertFalse(res["can_launch"])

    def test_launch_needs_runtime_tool_when_no_cli(self):
        a = mprat.MiniProgramRuntimeAdapter(devtools_cli="")
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "wechat_demo"
            proj.mkdir()
            (proj / "game.json").write_text("{}", encoding="utf-8")
            sess = a.launch(proj)
            self.assertEqual(sess["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)

    def test_run_scenarios_needs_runtime_tool(self):
        a = mprat.MiniProgramRuntimeAdapter(devtools_cli="")
        sess = a.launch(Path("output/wechat_demo"))
        out = a.run_scenarios(sess)
        self.assertEqual(out["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)

    def test_validate_project_structure_is_static_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "wechat_demo"
            proj.mkdir()
            (proj / "game.json").write_text(json.dumps({"deviceOrientation": "portrait"}), encoding="utf-8")
            (proj / "project.config.json").write_text("{}", encoding="utf-8")
            (proj / "game.js").write_text("wx.createCanvas(); wx.onTouchStart(()=>{});", encoding="utf-8")
            res = mprat.MiniProgramRuntimeAdapter.validate_project_structure(proj)
            self.assertTrue(res["static_valid"])
            # 关键：静态自检通过不代表运行期 PASS，返回里没有 RuntimeStatus.PASS
            self.assertNotIn("status", res)


@unittest.skipUnless(WECHAT_REAL, "设 WECHAT_REAL=1 才在微信开发者工具/真机上验证")
class TestMiniProgramReal(unittest.TestCase):
    def test_real_wechat_run(self):
        a = mprat.MiniProgramRuntimeAdapter()
        self.assertEqual(a.preflight()["status"], RuntimeStatus.PASS)


class TestDesktopShellAdapter(unittest.TestCase):
    """桌面 web-shell：壳工程生成可 PASS（真实文件）；但运行期验证需框架构建链 -> NEEDS_RUNTIME_TOOL。"""

    def test_package_generates_real_files(self):
        a = dsrat.DesktopShellAdapter(framework="electron")
        with tempfile.TemporaryDirectory() as tmp:
            html = _write_html(Path(tmp) / "src.html")
            out = Path(tmp) / "shell"
            res = a.package_desktop_shell(html, out, title="T", slug="t")
            self.assertEqual(res["status"], RuntimeStatus.PASS)
            self.assertTrue(res["web_in_desktop"])
            for f in ("index.html", "package.json", "main.js"):
                self.assertTrue((out / f).is_file(), f"壳工程缺文件: {f}")

    def test_preflight_needs_runtime_tool_when_no_framework(self):
        a = dsrat.DesktopShellAdapter(framework="electron")
        # 本机无 electron/npm 构建链 -> NEEDS_RUNTIME_TOOL
        res = a.preflight()
        self.assertEqual(res["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)

    def test_run_scenarios_needs_runtime_tool(self):
        a = dsrat.DesktopShellAdapter(framework="electron")
        with tempfile.TemporaryDirectory() as tmp:
            html = _write_html(Path(tmp) / "src.html")
            out = Path(tmp) / "shell"
            a.package_desktop_shell(html, out)
            sess = a.launch(out)
            out_res = a.run_scenarios(sess)
            self.assertEqual(out_res["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)


class TestAndroidOfflineHonesty(unittest.TestCase):
    """Android 原生：缺 SDK/adb/keystore 一律 NEEDS_RUNTIME_TOOL；导出同样诚实降级。"""

    def test_preflight_needs_sdk_when_missing(self):
        a = andrat.AndroidRuntimeAdapter(sdk_root="", adb="", keystore="")
        res = a.preflight()
        self.assertEqual(res["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)
        self.assertIn("ANDROID_SDK_ROOT", res["reason"])

    def test_launch_needs_sdk_when_missing(self):
        a = andrat.AndroidRuntimeAdapter(sdk_root="", adb="", keystore="")
        sess = a.launch(Path("output/godot_demo"))
        self.assertEqual(sess["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)

    def test_export_android_needs_sdk(self):
        a = andrat.AndroidRuntimeAdapter(sdk_root="", adb="", keystore="")
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "godot_demo"
            proj.mkdir()
            (proj / "project.godot").write_text('config/name="Demo"\n', encoding="utf-8")
            res = a.export_android(proj)
            self.assertEqual(res["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)


@unittest.skipUnless(ANDROID_REAL, "设 ANDROID_REAL=1 且装好 SDK/adb 才验证")
class TestAndroidReal(unittest.TestCase):
    def test_real_android_run(self):
        a = andrat.AndroidRuntimeAdapter()
        self.assertEqual(a.preflight()["status"], RuntimeStatus.PASS)


class TestIosPackagingHonesty(unittest.TestCase):
    """iOS：本机（Windows）物理不可达 -> NEEDS_MACOS_BUILDER；CI 步骤如实标 unverified。"""

    def test_ios_export_needs_macos_builder(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "godot_demo"
            proj.mkdir()
            (proj / "project.godot").write_text('config/name="Demo"\n', encoding="utf-8")
            res = ios.ios_export(proj)
            self.assertEqual(res["status"], "NEEDS_MACOS_BUILDER")
            self.assertTrue(res["unverified"])

    def test_macos_ci_steps_unverified(self):
        steps = ios.macos_ci_steps()
        self.assertTrue(steps["unverified"])
        self.assertIn("xcodebuild", steps["steps"][3]["run"])


class TestStoreSubmissionNewChannels(unittest.TestCase):
    """商店渠道：新增 appstore / googleplay；缺凭据/工具如实返回，绝不伪 PASS。"""

    def test_specs_include_appstore_googleplay(self):
        self.assertIn("appstore", ss.STORE_SPECS)
        self.assertIn("googleplay", ss.STORE_SPECS)
        self.assertEqual(ss.STORE_SPECS["appstore"]["host_reachability"], "NEEDS_MACOS_BUILDER")
        self.assertEqual(ss.STORE_SPECS["googleplay"]["host_reachability"], "NEEDS_SDK")

    def test_appstore_submit_blocked_when_no_bundle(self):
        sub = ss.StoreSubmission(Path(tempfile.mkdtemp()))
        # 未构建渠道包 -> readiness BLOCKED，提交绝不直接 PASS
        res = sub.submit("appstore", {"title": "T"})
        self.assertIn(res["status"], (ss.BLOCKED, ss.NEEDS_SANDBOX_CREDENTIALS, ss.NEEDS_RUNTIME_TOOL))


class TestCapabilityRegistryMultiPlatform(unittest.TestCase):
    """能力登记：新增 4 个多端能力，maturity 诚实（未验证不为 M2/verified）。

    注意：用全新 CapabilityRegistry() 实例断言，避免受其他测试对共享单例
    （capability_registry 单例会被 test_skill_registry 的 setUp 清空）的影响，保证确定性。
    """

    def test_new_capabilities_registered(self):
        from core.capability_registry import CapabilityRegistry
        reg = CapabilityRegistry()
        ids = {d.capability_id for d in reg.list()}
        for cid in ("wechat.mini", "desktop.shell", "android.native", "ios.native"):
            self.assertIn(cid, ids)

    def test_new_capabilities_not_falsely_verified(self):
        from core.capability_registry import CapabilityRegistry
        reg = CapabilityRegistry()
        for cid in ("wechat.mini", "android.native", "ios.native"):
            d = reg.resolve(cid)
            self.assertEqual(d.maturity, "M0", f"{cid} 未真验证不得标 M2")
        # desktop.shell 是 M1（壳工程生成可用，运行期仍待验证），也不应是 M2
        self.assertEqual(reg.resolve("desktop.shell").maturity, "M1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
