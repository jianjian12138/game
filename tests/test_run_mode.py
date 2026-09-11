#!/usr/bin/env python3
"""tests/test_run_mode.py：运行模式分离（本地开发 / 平台对接）

覆盖目标：
  1. 不配置任何渠道/沙箱/Staging/遥测时，本地模式仍能开发出货（不被拖成 PAUSED）。
  2. 本地模式下验证类节点缺工具 → COMPLETED_UNVERIFIED + unverified 点名，
     绝不悄悄写成 COMPLETED（否则就是把「没试玩」说成「已试玩」）。
  3. 平台模式下不允许任何降级，且开工前就把缺的外部依赖摊开列全。
  4. 模式解析：CLI > 环境变量 > 默认 local；非法值退回 local 不炸。
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.orchestrator import NodeResult, NodeStatus  # noqa: E402
from pipeline import autonomous_pipeline as ap  # noqa: E402
from pipeline import run_mode  # noqa: E402


class TestResolveMode(unittest.TestCase):
    def test_default_is_local(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(run_mode.MODE_ENV, None)
            self.assertEqual(run_mode.resolve_mode(None), run_mode.LOCAL)

    def test_cli_wins_over_env(self):
        with mock.patch.dict(os.environ, {run_mode.MODE_ENV: "platform"}):
            self.assertEqual(run_mode.resolve_mode("local"), run_mode.LOCAL)
            self.assertEqual(run_mode.resolve_mode(None), run_mode.PLATFORM)

    def test_invalid_falls_back_to_local(self):
        self.assertEqual(run_mode.resolve_mode("PLATFORM_TYPO"), run_mode.LOCAL)
        with mock.patch.dict(os.environ, {run_mode.MODE_ENV: "nonsense"}):
            self.assertEqual(run_mode.resolve_mode(None), run_mode.LOCAL)

    def test_platform_accepted(self):
        self.assertEqual(run_mode.resolve_mode("platform"), run_mode.PLATFORM)
        self.assertEqual(run_mode.resolve_mode("PLATFORM"), run_mode.PLATFORM)


class TestLocalReadiness(unittest.TestCase):
    """本地体检：只看本地工具链，绝不因渠道/沙箱缺失而阻断。"""

    def test_local_readiness_ignores_platform_env(self):
        # 清空所有平台相关环境变量，本地模式仍应 ready（LLM 可用时）
        cleared = {k: "" for k in (
            "WECHAT_APPID", "WECHAT_APP_SECRET", "STEAM_APP_ID", "STEAM_USERNAME",
            "ITCH_BUTLER_TARGET", "ITCH_API_KEY", "PAYMENT_SANDBOX_URL",
            "PAYMENT_SANDBOX_KEY", "ADS_SANDBOX_URL", "ADS_SANDBOX_KEY",
            "MULTIPLAYER_SANDBOX_URL", "MULTIPLAYER_SANDBOX_KEY",
            "STAGING_BASE_URL", "TELEMETRY_ENDPOINT", "TELEMETRY_KEY")}
        with mock.patch.dict(os.environ, cleared, clear=False):
            rep = run_mode.check_local_readiness(run_mode.LOCAL)
        # 只有 LLM 是必需项；本机已配置端点池 → 不应有 blocking
        blocking = [b for b in rep["blocking"] if b != "LLM 端点池"]
        self.assertEqual(blocking, [], f"本地模式不应被平台依赖阻断: {rep['blocking']}")
        self.assertIn("platform", rep["note"])

    def test_platform_readiness_lists_every_missing_group(self):
        cleared = {k: "" for k in (
            "WECHAT_APPID", "WECHAT_APP_SECRET", "STEAM_APP_ID", "STEAM_USERNAME",
            "ITCH_BUTLER_TARGET", "ITCH_API_KEY", "PAYMENT_SANDBOX_URL",
            "PAYMENT_SANDBOX_KEY", "ADS_SANDBOX_URL", "ADS_SANDBOX_KEY",
            "MULTIPLAYER_SANDBOX_URL", "MULTIPLAYER_SANDBOX_KEY",
            "STAGING_BASE_URL", "TELEMETRY_ENDPOINT", "TELEMETRY_KEY")}
        with mock.patch.dict(os.environ, cleared, clear=False):
            rep = run_mode.check_platform_readiness()
        self.assertFalse(rep["ready"])
        keys = {g["key"] for g in rep["groups"] if g["status"] != run_mode.OK}
        for expect in ("channel_wechat", "channel_steam", "channel_itch",
                       "sandbox_payment", "sandbox_ads", "sandbox_multiplayer",
                       "staging", "telemetry"):
            self.assertIn(expect, keys, f"{expect} 未被列为待补")

    def test_platform_readiness_never_prints_values(self):
        with mock.patch.dict(os.environ, {"WECHAT_APPID": "wx0123456789abcdef"}, clear=False):
            rep = run_mode.check_platform_readiness()
        blob = repr(rep)
        self.assertNotIn("wx0123456789abcdef", blob)


class TestDegradableStopPolicy(unittest.TestCase):
    """本地模式允许验证类降级，但必须点名未验证项。"""

    @staticmethod
    def _results(**mapping):
        return {k: NodeResult(k, v) for k, v in mapping.items()}

    def test_local_degrades_playtest_to_unverified(self):
        res = self._results(assemble=NodeStatus.SUCCEEDED,
                            package=NodeStatus.SUCCEEDED,
                            playtest=NodeStatus.NEEDS_RUNTIME_TOOL)
        st, reason, unverified = ap.HumanStopPolicy.classify(
            res, budget_exceeded=False, release_eligible=False, unresolved_gates=[],
            mode=run_mode.LOCAL, degradable=run_mode.DEGRADABLE_NODES_IN_LOCAL)
        self.assertEqual(st, ap.HumanStopPolicy.STATUS_COMPLETED_UNVERIFIED)
        self.assertEqual(unverified, ["playtest"])
        self.assertNotEqual(st, ap.HumanStopPolicy.STATUS_COMPLETED, "绝不能降级成「已完成」")
        self.assertIn("unverified_only", reason)

    def test_platform_never_degrades(self):
        res = self._results(assemble=NodeStatus.SUCCEEDED,
                            playtest=NodeStatus.NEEDS_RUNTIME_TOOL)
        st, reason, unverified = ap.HumanStopPolicy.classify(
            res, budget_exceeded=False, release_eligible=False, unresolved_gates=[],
            mode=run_mode.PLATFORM, degradable=run_mode.DEGRADABLE_NODES_IN_LOCAL)
        self.assertEqual(st, ap.HumanStopPolicy.STATUS_PAUSED)
        self.assertEqual(unverified, [])

    def test_local_does_not_degrade_non_degradable_node(self):
        """非验证类节点缺工具，本地模式也必须照常停，不能借本地模式蒙混。"""
        res = self._results(assemble=NodeStatus.NEEDS_RUNTIME_TOOL)
        st, _reason, unverified = ap.HumanStopPolicy.classify(
            res, budget_exceeded=False, release_eligible=False, unresolved_gates=[],
            mode=run_mode.LOCAL, degradable=run_mode.DEGRADABLE_NODES_IN_LOCAL)
        self.assertEqual(st, ap.HumanStopPolicy.STATUS_PAUSED)
        self.assertEqual(unverified, [])

    def test_budget_still_pauses_in_local_mode(self):
        res = self._results(assemble=NodeStatus.SUCCEEDED)
        st, reason, _ = ap.HumanStopPolicy.classify(
            res, budget_exceeded=True, release_eligible=False, unresolved_gates=[],
            mode=run_mode.LOCAL, degradable=run_mode.DEGRADABLE_NODES_IN_LOCAL)
        self.assertEqual(st, ap.HumanStopPolicy.STATUS_PAUSED)
        self.assertIn("over_budget", reason)


class TestPlatformPreflightGate(unittest.TestCase):
    """平台模式：开工前就摊牌，避免跑半天才说缺凭据。"""

    def _clear(self):
        return {k: "" for k in (
            "WECHAT_APPID", "WECHAT_APP_SECRET", "STEAM_APP_ID", "STEAM_USERNAME",
            "ITCH_BUTLER_TARGET", "ITCH_API_KEY", "PAYMENT_SANDBOX_URL",
            "PAYMENT_SANDBOX_KEY", "ADS_SANDBOX_URL", "ADS_SANDBOX_KEY",
            "MULTIPLAYER_SANDBOX_URL", "MULTIPLAYER_SANDBOX_KEY",
            "STAGING_BASE_URL", "TELEMETRY_ENDPOINT", "TELEMETRY_KEY")}

    def test_platform_mode_blocks_before_running(self):
        from core.contracts import GameIntent
        intent = GameIntent(title="平台门禁验收", genre="roguelike")
        with mock.patch.dict(os.environ, self._clear(), clear=False):
            out = ap.run_autonomous(intent, episodes=1, play_seconds=0.1,
                                    resume=False, mode=run_mode.PLATFORM)
        self.assertEqual(out["status"], ap.HumanStopPolicy.STATUS_PAUSED)
        self.assertIn("platform_prerequisites_missing", out["stop_reason"])
        self.assertEqual(out["totals"]["total"], 0, "应在开工前就停，不该白跑一轮")
        self.assertTrue(out["platform_gate"]["groups"])
        self.assertIn("local", out["hint"])

    def test_local_mode_runs_without_platform_config(self):
        from core.contracts import GameIntent
        intent = GameIntent(title="本地模式验收", genre="roguelike")

        class _FakePlaytest:
            def __init__(self, *a, **k):
                pass

            def run(self, *a, **k):
                class R:
                    status = "PASS"
                    episodes_reached_playing = 1
                    total_frames = 10
                    game_over_supported = True
                    restart_supported = True
                    page_error_count = 0
                    evidence_path = "evidence"
                    needs_runtime_tool = None
                return R()

        with mock.patch.dict(os.environ, self._clear(), clear=False), \
                mock.patch.object(ap, "PlaytestEngine", _FakePlaytest):
            out = ap.run_autonomous(intent, episodes=1, play_seconds=0.1, resume=False,
                                    art_backend="procedural_placeholder",
                                    mode=run_mode.LOCAL)
        self.assertEqual(out["mode"], run_mode.LOCAL)
        self.assertNotIn(out["status"],
                         (ap.HumanStopPolicy.STATUS_PAUSED, ap.HumanStopPolicy.STATUS_FAILED),
                         f"不配任何平台配置也应能本地开发: {out['stop_reason']}")
        self.assertEqual(out["unverified"], [])
        self.assertTrue(out["package"]["package_dir"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
