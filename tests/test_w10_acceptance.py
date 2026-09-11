"""tests/test_w10_acceptance.py — W10 长时程自主生产管线总验收（诚实、可无人值守、三处停）。

防伪核心（与计划 13.2、W5–W9 一致）：
  - 自主管线把一句话意图经 core/orchestrator 真实 DAG 编排：装配→(真机试玩∥打包)→门禁→发布候选。
  - 默认单测不依赖真实浏览器：用 mock 替换外部浏览器运行工具（诚实只 mock 外部依赖，
    verdict 映射/预算/门禁/打包/记忆逻辑全部走真实代码），稳定验证全链路与「三处停」诚实性。
  - 真机试玩仅在 W10_REAL_BROWSER=1 时跑（与 W9 同策略），断言真实 PASS + 真实证据落盘。
  - 三处停（缺运行工具 / 超预算 / 缺 LLM 凭据）由 HumanStopPolicy 显式分类，绝不假装完成。
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from core.contracts import GameIntent
from core.orchestrator import NodeResult, NodeStatus
from core.runtime_adapter import RuntimeStatus
from pipeline import autonomous_pipeline as ap

ROOT = Path(__file__).resolve().parent.parent
W10_REAL_BROWSER = os.environ.get("W10_REAL_BROWSER") == "1"


# ── 外部浏览器依赖的诚实替身（仅替身运行工具，verdict 逻辑保持真实） ──────────
class _FakePlaytest:
    def __init__(self, evidence_dir: str = "", seed: int = 42):
        self.evidence_dir = evidence_dir

    def run(self, html_path, episodes=2, play_seconds=3.0, seed=42, policy="auto", headless=True):
        return self._make(evidence_dir=self.evidence_dir, status=RuntimeStatus.PASS)

    def _make(self, evidence_dir: str, status: str):
        class _R:
            pass
        r = _R()
        r.status = status
        r.episodes_reached_playing = 2
        r.total_frames = 300
        r.game_over_supported = True
        r.restart_supported = True
        r.page_error_count = 0
        r.needs_runtime_tool = (status == RuntimeStatus.NEEDS_RUNTIME_TOOL)
        ev_dir = Path(evidence_dir)
        ev_dir.mkdir(parents=True, exist_ok=True)
        r.evidence_path = str(ev_dir / "fake_evidence.json")
        ev_dir.joinpath("fake_evidence.json").write_text(
            json.dumps({"fake": True, "status": status}), encoding="utf-8")
        return r


class _FakePlaytestNeedsRT(_FakePlaytest):
    def run(self, html_path, episodes=2, play_seconds=3.0, seed=42, policy="auto", headless=True):
        return self._make(evidence_dir=self.evidence_dir, status=RuntimeStatus.NEEDS_RUNTIME_TOOL)


def _make_intent(title: str = "W10 回归测试 节奏游戏", genre: str = "节奏") -> GameIntent:
    return GameIntent(title=title, genre=genre, custom_rules="")


class TestBudgetController(unittest.TestCase):
    """预算控制：超预算即上报，不硬撑。"""

    def test_charge_and_exceed(self):
        bc = ap.BudgetController(limit_usd=10.0,
                                 cost_table={"assemble.build": 6.0, "playtest.run": 6.0})
        self.assertFalse(bc.exceeded)
        bc.charge("assemble.build")
        self.assertFalse(bc.exceeded)
        bc.charge("playtest.run")
        self.assertTrue(bc.exceeded)
        self.assertAlmostEqual(bc.estimated_usd, 12.0)

    def test_no_cost_table_zero_estimate(self):
        bc = ap.BudgetController(limit_usd=100.0)
        bc.charge("assemble.build")
        self.assertEqual(bc.estimated_usd, 0.0)
        self.assertFalse(bc.exceeded)


class TestHumanStopPolicy(unittest.TestCase):
    """三处停 + 完成/失败分类：显式诚实，绝不假装完成。"""

    @staticmethod
    def _results(*statuses):
        res = {}
        for i, s in enumerate(statuses):
            res[f"n{i}"] = NodeResult(f"n{i}", s)
        return res

    def test_completed_when_release_eligible(self):
        res = self._results(NodeStatus.SUCCEEDED, NodeStatus.SUCCEEDED, NodeStatus.SUCCEEDED)
        st, reason, unverified = ap.HumanStopPolicy.classify(res, budget_exceeded=False,
                                                  release_eligible=True, unresolved_gates=[])
        self.assertEqual(st, ap.HumanStopPolicy.STATUS_COMPLETED)
        self.assertIn("preview", reason)

    def test_paused_over_budget(self):
        res = self._results(NodeStatus.SUCCEEDED)
        st, reason, unverified = ap.HumanStopPolicy.classify(res, budget_exceeded=True,
                                                  release_eligible=False, unresolved_gates=[])
        self.assertEqual(st, ap.HumanStopPolicy.STATUS_PAUSED)
        self.assertIn("over_budget", reason)

    def test_paused_missing_runtime_tool(self):
        res = self._results(NodeStatus.SUCCEEDED, NodeStatus.NEEDS_RUNTIME_TOOL)
        st, reason, unverified = ap.HumanStopPolicy.classify(res, budget_exceeded=False,
                                                  release_eligible=False, unresolved_gates=[])
        self.assertEqual(st, ap.HumanStopPolicy.STATUS_PAUSED)
        self.assertIn("missing_runtime_tool", reason)

    def test_paused_missing_credentials(self):
        res = self._results(NodeStatus.SUCCEEDED, NodeStatus.NEEDS_LLM_CREDENTIALS)
        st, reason, unverified = ap.HumanStopPolicy.classify(res, budget_exceeded=False,
                                                  release_eligible=False, unresolved_gates=[])
        self.assertEqual(st, ap.HumanStopPolicy.STATUS_PAUSED)
        self.assertIn("missing_credentials", reason)

    def test_failed_unresolved_gates(self):
        res = self._results(NodeStatus.SUCCEEDED)
        st, reason, unverified = ap.HumanStopPolicy.classify(res, budget_exceeded=False,
                                                  release_eligible=False, unresolved_gates=["G3"])
        self.assertEqual(st, ap.HumanStopPolicy.STATUS_FAILED)
        self.assertIn("unresolved_gates", reason)


class TestAutonomousOffline(unittest.TestCase):
    """浏览器依赖被 mock，验证 DAG 装配/预算/门禁/打包/记忆全链路（离线、确定、快速）。"""

    def test_run_autonomous_completed_with_package(self):
        with mock.patch.object(ap, "PlaytestEngine", _FakePlaytest):
            out = ap.run_autonomous(_make_intent(), episodes=1, play_seconds=1.0, seed=7,
                                    resume=False, art_backend="procedural_placeholder")
        self.assertEqual(out["status"], ap.HumanStopPolicy.STATUS_COMPLETED, out)
        # 真实可上架包在磁盘（index.html + 清单 + 合规 + 音频）
        pkg = out["package"]
        self.assertIsNotNone(pkg["package_dir"])
        pkg_dir = Path(pkg["package_dir"])
        self.assertTrue((pkg_dir / "index.html").exists())
        self.assertTrue((pkg_dir / "package_manifest.json").exists())
        self.assertTrue((pkg_dir / "compliance_checklist.json").exists())
        audio = list((pkg_dir / "audio").glob("*.wav")) if (pkg_dir / "audio").is_dir() else []
        self.assertGreaterEqual(len(audio), 1, "W7 程序化音频应被打包")
        art = list((pkg_dir / "assets").glob("*.png")) if (pkg_dir / "assets").is_dir() else []
        prov = list((pkg_dir / "assets").glob("*.json")) if (pkg_dir / "assets").is_dir() else []
        self.assertEqual(len(art), 1, "自主包应包含一张美术资产")
        self.assertGreaterEqual(len(prov), 1, "美术资产必须带 provenance JSON")
        # 默认离线验收显式使用程序化后端，不能冒充 AI
        self.assertFalse(out["package"]["art_is_ai_generated"])
        # 门禁 G0–G6 全 PASS（含真实试玩 PASS → G4 → G6 预览资格）
        self.assertEqual(out["gates"].get("G6"), "PASS", out["gates"])
        self.assertEqual(out["gates"].get("G4"), "PASS", out["gates"])
        # 项目记忆已写，且含 autonomous_decision
        mem = Path(out["memory_path"])
        self.assertTrue(mem.exists())
        lines = [json.loads(l) for l in mem.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertIn("autonomous_decision", [d["kind"] for d in lines])
        # 验收报告自洽：试玩 PASS → 已验证场景含 boot_to_play
        self.assertEqual(out["acceptance"]["playtest_status"], RuntimeStatus.PASS)
        self.assertIn("boot_to_play", out["acceptance"]["verified_scenarios"])
        # 预算未超
        self.assertFalse(out["budget"]["exceeded"])

    def test_run_autonomous_needs_runtime_tool_paused(self):
        """缺浏览器驱动时的行为按模式分档（本地开发不该被验证类缺口拖死）。

        local    → COMPLETED_UNVERIFIED：包照出，但点名 playtest 未验证，
                   绝不能写成 COMPLETED（否则等于把「没试玩」说成「已试玩」）。
        platform → PAUSED：平台对接模式下不允许任何降级，缺工具就是停。
        """
        # ── 平台模式：不降级，照旧人停 ──
        with mock.patch.object(ap, "PlaytestEngine", _FakePlaytestNeedsRT):
            out = ap.run_autonomous(_make_intent(title="W10 NEEDS_RT 回归 platform"),
                                    episodes=1, play_seconds=1.0, seed=7, resume=False,
                                    art_backend="procedural_placeholder", mode="platform")
        if out["status"] == ap.HumanStopPolicy.STATUS_PAUSED and "platform_prerequisites" in out["stop_reason"]:
            pass  # 本机未配平台依赖 → 开工前就被拦，同样符合预期
        else:
            self.assertEqual(out["status"], ap.HumanStopPolicy.STATUS_PAUSED, out)
            self.assertIn("missing_runtime_tool", out["stop_reason"], out)

        # ── 本地模式：降级为「已完成但未验证」，且点名未验证项 ──
        with mock.patch.object(ap, "PlaytestEngine", _FakePlaytestNeedsRT):
            out = ap.run_autonomous(_make_intent(title="W10 NEEDS_RT 回归 local"),
                                    episodes=1, play_seconds=1.0, seed=7, resume=False,
                                    art_backend="procedural_placeholder")
        self.assertEqual(out["status"], ap.HumanStopPolicy.STATUS_COMPLETED_UNVERIFIED, out)
        self.assertEqual(out["unverified"], ["playtest"])
        self.assertIn("unverified_only", out["stop_reason"])
        # 关键：绝不能悄悄变成 COMPLETED
        self.assertNotEqual(out["status"], ap.HumanStopPolicy.STATUS_COMPLETED)
        # failure_policy=continue：即便试玩缺工具，装配+打包仍产出真实包
        self.assertIsNotNone(out["package"]["package_dir"])
        self.assertTrue(Path(out["package"]["package_dir"]).exists())

    def test_run_autonomous_over_budget_paused(self):
        # 注入成本表触发超预算 → 人停 PAUSED/over_budget（三处停之一）
        out = ap.run_autonomous(_make_intent(title="W10 超预算 回归"),
                                cost_table={"assemble.build": 999.0},
                                episodes=1, play_seconds=1.0, seed=7, resume=False,
                                art_backend="procedural_placeholder")
        self.assertEqual(out["status"], ap.HumanStopPolicy.STATUS_PAUSED, out)
        self.assertIn("over_budget", out["stop_reason"])
        self.assertTrue(out["budget"]["exceeded"])


@unittest.skipUnless(W10_REAL_BROWSER, "需真实浏览器，设 W10_REAL_BROWSER=1 运行真机试玩")
class TestAutonomousRealBrowser(unittest.TestCase):
    """真机试玩门禁：真实浏览器跑通 boot+主循环，断言真实 PASS + 真实证据落盘。"""

    def test_run_autonomous_real_playtest_pass(self):
        out = ap.run_autonomous(_make_intent(title="W10 真机试玩 回归"),
                                episodes=2, play_seconds=3.0, seed=42, resume=False,
                                art_backend="procedural_placeholder")
        self.assertEqual(out["acceptance"]["playtest_status"], RuntimeStatus.PASS, out)
        self.assertEqual(out["status"], ap.HumanStopPolicy.STATUS_COMPLETED, out)
        self.assertIsNotNone(out["package"]["package_dir"])
        self.assertTrue(Path(out["package"]["package_dir"]).exists())
        self.assertTrue(Path(out["memory_path"]).exists())


@unittest.skipUnless(os.environ.get("W10_REAL_COMFYUI") == "1",
                     "需本机 ComfyUI+SDXL，设 W10_REAL_COMFYUI=1 运行真实 AIGC 出货")
class TestAutonomousRealAIGC(unittest.TestCase):
    """真实 W5→W10：ComfyUI 出图、独立 provenance、PNG 随包落盘。"""

    def test_real_aigc_art_is_in_package(self):
        out = ap.run_autonomous(_make_intent(title="W10 真 AIGC 美术出货", genre="节奏"),
                                episodes=1, play_seconds=1.0, seed=42, resume=False,
                                art_backend="comfyui_local")
        self.assertEqual(out["status"], ap.HumanStopPolicy.STATUS_COMPLETED, out)
        self.assertTrue(out["package"]["art_is_ai_generated"], out)
        pkg_dir = Path(out["package"]["package_dir"])
        pngs = list((pkg_dir / "assets").glob("*.png"))
        jsons = list((pkg_dir / "assets").glob("*.json"))
        self.assertEqual(len(pngs), 1)
        self.assertGreaterEqual(len(jsons), 1)
        rec = json.loads(jsons[0].read_text(encoding="utf-8"))
        self.assertTrue(rec["is_ai_generated"])
        self.assertEqual(rec["provenance"]["generator"], "comfyui_local")
        self.assertIn("sd_xl_base_1.0", rec["provenance"]["model"])
        self.assertTrue(rec["content_hash"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
