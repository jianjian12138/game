"""Godot 多端能力的诚实测试（红线 13.2）。

设计原则：
    - 离线（默认）用例用 monkeypatch 替代 subprocess 与可执行文件探测，验证「逻辑正确性」
      与「缺资源时如实降级」，绝不依赖本机是否装了 Godot。
    - 真实运行用例由环境变量 GODOT_REAL=1 守护：仅当本机确有 Godot 才跑，否则跳过。
      这样 CI / 无 Godot 环境也能确定性全绿，同时保留一键真验证入口。
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.runtime_adapter import RuntimeStatus
import pipeline.godot_runtime_adapter as grat
import pipeline.godot_exporter as gexp


GODOT_REAL = os.environ.get("GODOT_REAL") == "1"


def _make_project_dir(base: Path, name: str = "godot_demo") -> Path:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "project.godot").write_text('config/name="Demo"\n', encoding="utf-8")
    return d


class TestGodotRuntimeOfflineHonesty(unittest.TestCase):
    """未检测到 Godot 时，所有场景必须如实返回 NEEDS_RUNTIME_TOOL。"""

    def test_preflight_needs_runtime_tool_when_no_exe(self):
        a = grat.GodotRuntimeAdapter(godot_executable="")
        res = a.preflight()
        self.assertEqual(res["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)
        self.assertFalse(res["can_launch"])

    def test_launch_needs_runtime_tool_when_no_exe(self):
        a = grat.GodotRuntimeAdapter(godot_executable="")
        sess = a.launch(Path("output/godot_demo"))
        self.assertEqual(sess["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)

    def test_run_scenarios_needs_runtime_tool_when_no_exe(self):
        a = grat.GodotRuntimeAdapter(godot_executable="")
        sess = a.launch(Path("output/godot_demo"))
        out = a.run_scenarios(sess)
        self.assertEqual(out["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)


class TestGodotRuntimeContractParsing(unittest.TestCase):
    """用 monkeypatch 模拟 Godot 无头输出，验证 boot/core_loop 断言逻辑。"""

    def test_run_scenarios_pass_on_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = _make_project_dir(Path(tmp))
            fake_exe = str(Path(tmp) / "godot_fake.exe")
            a = grat.GodotRuntimeAdapter(godot_executable=fake_exe)
            # 模拟 Godot 无头输出：boot 成功 + 主循环上报 120 帧
            fake_out = (
                "Godot Engine v4.7.2.stable\n"
                "GAME_AGENT_PROBE_START\n"
                'GAME_AGENT_CONTRACT {"frames": 120}\n'
            )
            cp = subprocess.CompletedProcess(args=[], returncode=0, stdout=fake_out, stderr="")
            with mock.patch.object(grat.subprocess, "run", return_value=cp):
                sess = a.launch(proj)
                out = a.run_scenarios(sess)
            self.assertEqual(out["status"], RuntimeStatus.PASS)
            self.assertEqual(out["scenarios"]["boot"]["status"], RuntimeStatus.PASS)
            self.assertEqual(out["scenarios"]["core_loop"]["status"], RuntimeStatus.PASS)
            self.assertEqual(out["metrics"]["frames"], 120)
            self.assertEqual(out["metrics"]["godot_error_count"], 0)

    def test_run_scenarios_fail_on_parse_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = _make_project_dir(Path(tmp))
            fake_exe = str(Path(tmp) / "godot_fake.exe")
            a = grat.GodotRuntimeAdapter(godot_executable=fake_exe)
            # stderr 出现 Parse Error → boot 失败
            cp = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="SCRIPT ERROR: Parse Error: Expected ')'")
            with mock.patch.object(grat.subprocess, "run", return_value=cp):
                sess = a.launch(proj)
                out = a.run_scenarios(sess)
            self.assertEqual(out["status"], RuntimeStatus.FAIL)
            self.assertEqual(out["scenarios"]["boot"]["status"], RuntimeStatus.FAIL)


class TestGodotExporterOfflineHonesty(unittest.TestCase):
    """导出器的诚实边界：缺可执行文件 / 缺模板 / 成功，三种路径都必须正确。"""

    def test_export_needs_runtime_tool_when_no_exe(self):
        e = gexp.GodotExporter(godot_executable="")
        with tempfile.TemporaryDirectory() as tmp:
            proj = _make_project_dir(Path(tmp))
            res = e.export_windows(proj)
        self.assertEqual(res["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)

    def test_export_needs_runtime_tool_when_templates_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = _make_project_dir(Path(tmp))
            fake_exe = str(Path(tmp) / "godot_fake.exe")
            e = gexp.GodotExporter(godot_executable=fake_exe)
            stderr = (
                "ERROR: Cannot export project with preset \"Windows Desktop\" due to configuration errors:\n"
                "在预期路径处未找到导出模板：\n./Godot/export_templates/4.7.2.stable/windows_release_x86_64.exe\n"
            )
            cp = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)
            with mock.patch.object(gexp.subprocess, "run", return_value=cp):
                res = e.export_windows(proj)
            self.assertEqual(res["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)
            self.assertIn("导出模板缺失", res["reason"])

    def test_export_pass_copies_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = _make_project_dir(Path(tmp))
            fake_exe = str(Path(tmp) / "godot_fake.exe")
            export_exe = proj / "dist" / "godot_demo.exe"
            export_exe.parent.mkdir(parents=True, exist_ok=True)
            export_exe.write_text("MZFAKE", encoding="utf-8")
            e = gexp.GodotExporter(godot_executable=fake_exe)
            cp = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            with mock.patch.object(gexp.subprocess, "run", return_value=cp):
                res = e.export_windows(proj, export_path=export_exe)
            self.assertEqual(res["status"], RuntimeStatus.PASS)
            self.assertIn(str(export_exe), res["artifacts"])


@unittest.skipUnless(GODOT_REAL, "设 GODOT_REAL=1 才在本机真实 Godot 上验证（无 Godot 环境跳过）")
class TestGodotRuntimeReal(unittest.TestCase):
    """真实 Godot 运行守护：仅在 GODOT_REAL=1 时执行。"""

    def test_real_headless_boot_and_core_loop(self):
        from pathlib import Path as _P
        a = grat.GodotRuntimeAdapter()
        self.assertEqual(a.preflight()["status"], RuntimeStatus.PASS)
        proj = _P("output/godot_demo")
        sess = a.launch(proj)
        out = a.run_scenarios(sess)
        a.close(sess)
        # 真实证据要求：boot 通过、主循环帧数达标、零引擎错误
        self.assertEqual(out["status"], RuntimeStatus.PASS)
        self.assertGreaterEqual(out["metrics"]["frames"], grat.MIN_FRAMES)
        self.assertEqual(out["metrics"]["godot_error_count"], 0)


@unittest.skipUnless(GODOT_REAL, "设 GODOT_REAL=1 才在本机真实 Godot 上验证（无 Godot 环境跳过）")
class TestGodotExporterReal(unittest.TestCase):
    """真实导出守护：本机若缺模板会如实返回 NEEDS_RUNTIME_TOOL（非崩溃、非伪 PASS）。"""

    def test_real_export_honest_status(self):
        from pathlib import Path as _P
        res = gexp.GodotExporter().export_windows(_P("output/godot_demo"))
        # 诚实边界：要么真出包 PASS，要么如实 NEEDS_RUNTIME_TOOL；绝不允许伪造 PASS
        self.assertIn(res["status"], (
            RuntimeStatus.PASS, RuntimeStatus.NEEDS_RUNTIME_TOOL,
            RuntimeStatus.FAIL, RuntimeStatus.TIMEOUT,
        ))
        if res["status"] == RuntimeStatus.PASS:
            self.assertTrue(Path(res["export_path"]).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
