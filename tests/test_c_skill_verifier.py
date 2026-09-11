"""tests/test_c_skill_verifier.py — 证据摘要的跨运行合并与历史复校验（W3c-4）。

为什么要为"记录证据的方式"单独写测试：
实测同一套契约、不同时段/不同模型，单次全量通过率在 17/24 ~ 22/24 之间波动。
如果证据只记单次结果，它就会被波动牵着走——今天夸大、明天抹掉已经拿到过的
真实通过。所以下面三条性质一旦坏了，C 类技能的证据就退化成一句无法核对的断言：

  1. 历史运行必须能被合并读回，而不是每次覆盖；
  2. ever_passed（历史至少一次通过）与 last_ok（最近一次）是两个口径，不许互相冒充；
  3. 历史通过必须能用**当前**契约复校验，契约改过之后旧通过不得继续冒充成立。

全部测试离线运行，不调用 LLM、不依赖 output/ 里的真实工件。
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest import mock

from core import c_skill_verifier as _csv
from core.artifact_store import ArtifactStore
from core.c_skill_verifier import (CSkillVerifier, restore_registrations)
from core.capability_registry import capability_registry as _cr
from core.skill_registry import skill_registry as _sr


def _res(sid: str, ok: bool, provider: str = "openai_compat",
         model: str = "m1", payload: Optional[Dict[str, Any]] = None,
         error: str = "") -> Dict[str, Any]:
    """构造一条 result 记录（结构与 LLMSkillResult.to_dict() 一致）。"""
    return {
        "skill_id": sid,
        "status": "OK" if ok else "SCHEMA_INVALID",
        "ok": ok,
        "provider": provider,
        "model": model,
        "attempts": 1,
        "latency_ms": 100,
        "payload": payload if payload else {},
        "errors": [error] if error else [],
    }


def _make_run(root: str, run_id: str, results: List[Dict[str, Any]],
              started_at: str = "2026-09-10 00:00:00") -> str:
    """在临时 output/runs/ 下造一个验证 run（含证据工件 + 逐项 payload 工件）。"""
    store = ArtifactStore(Path(root) / run_id)
    ev = {
        "artifact_type": "c_skill_verification",
        "run_id": run_id,
        "started_at": started_at,
        "elapsed_seconds": 1.0,
        "available_providers": ["openai_compat"],
        "total": len(results),
        "ok": sum(1 for r in results if r.get("ok")),
        "failed": sum(1 for r in results if not r.get("ok")),
        "results": results,
    }
    store.put_json("c_skill_verification", ev,
                   artifact_id="art_c_skill_verification")
    for r in results:
        if r.get("payload"):
            store.put_json("c_skill_payload", r["payload"],
                           artifact_id=f"art_payload_{r['skill_id']}")
    return run_id


class _TmpRoot(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="csv_test_")
        self.runs_root = os.path.join(self.tmp, "output", "runs")
        os.makedirs(self.runs_root, exist_ok=True)
        self.digest = os.path.join(self.tmp, "digest.json")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def read_digest(self) -> Dict[str, Any]:
        with open(self.digest, "r", encoding="utf-8") as f:
            return json.load(f)


class TestCollectHistory(_TmpRoot):
    """历史工件必须能被读回；读不回的不能编。"""

    def test_reads_runs_in_order(self):
        _make_run(self.runs_root, "run_20260910_000000_aaaaaaaa",
                  [_res("core_loop_design", True, payload={"a": 1})],
                  started_at="2026-09-10 00:00:00")
        _make_run(self.runs_root, "run_20260910_010000_bbbbbbbb",
                  [_res("core_loop_design", False, error="长度不足")],
                  started_at="2026-09-10 01:00:00")
        runs = CSkillVerifier.collect_history(self.runs_root)
        self.assertEqual(len(runs), 2)
        self.assertEqual([r["run_id"] for r in runs],
                         ["run_20260910_000000_aaaaaaaa",
                          "run_20260910_010000_bbbbbbbb"])
        self.assertEqual(runs[0]["ok"], 1)
        self.assertEqual(runs[1]["failed"], 1)

    def test_skips_runs_without_verification_artifact(self):
        """不是验证 run / 工件损坏的目录一律跳过，不猜、不补。"""
        _make_run(self.runs_root, "run_20260910_000000_aaaaaaaa",
                  [_res("core_loop_design", True, payload={"a": 1})])
        os.makedirs(os.path.join(self.runs_root, "run_other_thing"), exist_ok=True)
        (Path(self.runs_root) / "loose_file.txt").write_text("x", encoding="utf-8")
        runs = CSkillVerifier.collect_history(self.runs_root)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["run_id"], "run_20260910_000000_aaaaaaaa")

    def test_missing_root_returns_empty(self):
        self.assertEqual(CSkillVerifier.collect_history(
            os.path.join(self.tmp, "nope")), [])


class TestWriteDigestMerge(_TmpRoot):
    """schema_version=2：ever_passed 与 last_ok 必须分开，且互不冒充。"""

    def test_merge_keeps_ever_passed_and_last_ok(self):
        rid1 = _make_run(self.runs_root, "run_20260910_000000_aaaaaaaa", [
            _res("core_loop_design", True, provider="openai_compat",
                 model="gemini", payload={"x": 1}),
            _res("ui_hud_wireframe", False, error="anchor 太短"),
        ], started_at="2026-09-10 00:00:00")
        rid2 = _make_run(self.runs_root, "run_20260910_010000_bbbbbbbb", [
            _res("core_loop_design", False, provider="openai_compat",
                 model="glm", error="steps 太短"),
            _res("ui_hud_wireframe", False, error="anchor 太短"),
        ], started_at="2026-09-10 01:00:00")

        ev = {"run_id": rid2, "started_at": "2026-09-10 01:00:00",
              "total": 2, "ok": 0, "failed": 2,
              "results": [_res("core_loop_design", False, model="glm",
                               error="steps 太短"),
                          _res("ui_hud_wireframe", False, error="anchor 太短")]}
        CSkillVerifier.write_digest(ev, path=self.digest,
                                    runs_root=self.runs_root)
        d = self.read_digest()

        self.assertEqual(d["schema_version"], 2)
        self.assertEqual(d["ever_passed"], ["core_loop_design"])
        self.assertEqual(d["last_run"], {"total": 2, "ok": 0, "failed": 2})
        self.assertEqual(len(d["history_runs"]), 2)

        core = next(i for i in d["per_skill"] if i["skill_id"] == "core_loop_design")
        self.assertTrue(core["ever_passed"])
        self.assertFalse(core["last_ok"])          # 最近一次确实失败了
        self.assertEqual(core["history_runs"], 2)
        self.assertEqual(core["pass_rate"], 0.5)
        self.assertEqual(core["pass_run_id"], rid1)   # 通过证据来自那一次
        self.assertEqual(core["pass_model"], "gemini")
        self.assertEqual(core["last_model"], "glm")   # 不是最近一次的模型
        self.assertIsNotNone(core["pass_payload_sha256"])

        hud = next(i for i in d["per_skill"] if i["skill_id"] == "ui_hud_wireframe")
        self.assertFalse(hud["ever_passed"])
        self.assertIsNone(hud["pass_run_id"])
        self.assertEqual(hud["pass_rate"], 0.0)
        self.assertIn("不可混用", d["note"])

    def test_no_merge_uses_only_current_run(self):
        _make_run(self.runs_root, "run_20260910_000000_aaaaaaaa",
                  [_res("core_loop_design", True, payload={"x": 1})])
        ev = {"run_id": "run_now", "total": 1, "ok": 0, "failed": 1,
              "results": [_res("core_loop_design", False)]}
        CSkillVerifier.write_digest(ev, path=self.digest, merge_history=False,
                                    runs_root=self.runs_root)
        d = self.read_digest()
        self.assertEqual(d["ever_passed"], [])
        self.assertEqual(len(d["history_runs"]), 1)

    def test_no_llm_does_not_merge_history_into_a_good_number(self):
        """没跑就是没跑：不许拿历史通过把"本次 0 项"粉饰成"通过 N 项"。"""
        _make_run(self.runs_root, "run_20260910_000000_aaaaaaaa",
                  [_res("core_loop_design", True, payload={"x": 1})])
        from core.llm_skill_adapter import LLMSkillStatus
        ev = {"status": LLMSkillStatus.NEEDS_LLM_CREDENTIALS,
              "run_id": None, "total": 24, "ok": 0, "failed": 24, "results": []}
        CSkillVerifier.write_digest(ev, path=self.digest,
                                    runs_root=self.runs_root)
        d = self.read_digest()
        self.assertEqual(d["ever_passed"], [])
        self.assertEqual(d["per_skill"], [])
        self.assertEqual(d["last_run"]["ok"], 0)


class TestRestoreUsesEverPassed(_TmpRoot):
    """回放注册按"历史真实通过"，用通过那次的端点证据，不是最近一次。"""

    def setUp(self) -> None:
        super().setUp()
        _sr._skills.clear()
        _cr._descriptors.clear()
        _sr.ingest_from_registry()
        from core.skill_registry_seeds import apply_default_seeds
        from core.skill_classification import apply_classification
        apply_default_seeds()
        apply_classification(_sr)
        # C 类技能必须先落到 NEEDS_IMPLEMENTATION，否则注册会被跳过
        for sid in ("core_loop_design", "ui_hud_wireframe",
                    "level_curve_progression"):
            self.assertEqual(_sr._skills[sid].cls, "C")

    def tearDown(self) -> None:
        _sr._skills.clear()
        _cr._descriptors.clear()
        super().tearDown()

    def _write(self, per_skill: List[Dict[str, Any]],
               schema_version: int = 2) -> None:
        with open(self.digest, "w", encoding="utf-8") as f:
            json.dump({"schema_version": schema_version, "run_id": "run_x",
                       "ever_passed": [i["skill_id"] for i in per_skill
                                       if i.get("ever_passed")],
                       "per_skill": per_skill}, f, ensure_ascii=False)

    def test_ever_passed_registers_even_if_last_run_failed(self):
        self._write([
            {"skill_id": "core_loop_design", "ever_passed": True,
             "last_ok": False, "pass_run_id": "run_1", "pass_at": "2026-09-10 00:00",
             "pass_provider": "openai_compat", "pass_model": "gemini-3.6-flash",
             "pass_attempts": 2, "pass_payload_sha256": "sha256:abc",
             "pass_rate": 0.5},
        ])
        n = restore_registrations(_sr, path=self.digest)
        self.assertEqual(n, 1)
        self.assertEqual(_sr.counts()["C_REGISTERED"], 1)
        note = _sr._skills["core_loop_design"].notes[-1]
        self.assertIn("run_1", note)
        self.assertIn("gemini-3.6-flash", note)

    def test_never_passed_not_registered(self):
        self._write([
            {"skill_id": "ui_hud_wireframe", "ever_passed": False,
             "last_ok": False, "pass_rate": 0.0},
        ])
        self.assertEqual(restore_registrations(_sr, path=self.digest), 0)
        self.assertEqual(_sr.counts()["C_REGISTERED"], 0)

    def test_ever_passed_without_provider_is_rejected(self):
        """没有端点记录 = 没有调用证据，即使是 ever_passed 也不许注册。"""
        self._write([
            {"skill_id": "level_curve_progression", "ever_passed": True,
             "pass_provider": "", "pass_model": ""},
        ])
        self.assertEqual(restore_registrations(_sr, path=self.digest), 0)

    def test_v1_digest_falls_back_to_ok(self):
        """旧摘要没有 ever_passed 字段，退回 ok——同样是当时真实结果。"""
        self._write([
            {"skill_id": "core_loop_design", "ok": True, "provider": "openai_compat",
             "model": "glm-4-flash", "attempts": 1, "latency_ms": 100,
             "payload_sha256": "sha256:def"},
            {"skill_id": "ui_hud_wireframe", "ok": False},
        ], schema_version=1)
        self.assertEqual(restore_registrations(_sr, path=self.digest), 1)

    def test_missing_digest_registers_nothing(self):
        self.assertEqual(restore_registrations(
            _sr, path=os.path.join(self.tmp, "nope.json")), 0)


class TestAuditEvidence(_TmpRoot):
    """历史通过必须能用当前契约复校验；契约一改，旧通过就该被判失效。"""

    _FAKE_SCHEMA = {
        "type": "object",
        "required": ["a"],
        "properties": {"a": {"type": "string", "minLength": 5}},
    }

    def _spec(self):
        return SimpleNamespace(output_schema=self._FAKE_SCHEMA,
                               acceptance=[], custom=None)

    def _audit(self, per_skill, payloads):
        """payloads: {skill_id: payload}，写进 pass_run_id 指向的 run。"""
        rid = "run_20260910_000000_aaaaaaaa"
        _make_run(self.runs_root, rid, [
            _res(sid, True, payload=payloads.get(sid) or {"a": "hello"})
            for sid in payloads])
        with open(self.digest, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 2, "run_id": rid,
                       "ever_passed": [i["skill_id"] for i in per_skill],
                       "per_skill": per_skill}, f, ensure_ascii=False)
        with mock.patch.object(_csv, "get_spec", lambda sid: self._spec()):
            return CSkillVerifier.audit_evidence(
                path=self.digest, runs_root=self.runs_root, write=False)

    def test_valid_and_stale_are_reported_separately(self):
        rep = self._audit(
            [{"skill_id": "good", "ever_passed": True, "pass_run_id": "run_20260910_000000_aaaaaaaa"},
             {"skill_id": "bad", "ever_passed": True, "pass_run_id": "run_20260910_000000_aaaaaaaa"}],
            {"good": {"a": "hello"}, "bad": {"a": "hi"}})
        self.assertEqual(rep["still_valid"], 1)
        self.assertEqual(rep["stale"], 1)
        states = {d["skill_id"]: d["audit"] for d in rep["details"]}
        self.assertEqual(states, {"good": "still_valid", "bad": "stale"})

    def test_missing_payload_is_not_guessed(self):
        rep = self._audit(
            [{"skill_id": "gone", "ever_passed": True,
              "pass_run_id": "run_that_was_cleaned"}],
            {"gone": {"a": "hello"}})
        self.assertEqual(rep["missing"], 1)
        self.assertEqual(rep["details"][0]["audit"], "missing")

    def test_never_passed_reported_as_no_pass_record(self):
        _make_run(self.runs_root, "run_20260910_000000_aaaaaaaa", [])
        with open(self.digest, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 2, "run_id": "r",
                       "ever_passed": [],
                       "per_skill": [{"skill_id": "never", "ever_passed": False}]}, f)
        with mock.patch.object(_csv, "get_spec", lambda sid: self._spec()):
            rep = CSkillVerifier.audit_evidence(
                path=self.digest, runs_root=self.runs_root, write=False)
        self.assertEqual(rep["no_pass_record"], 1)
        self.assertEqual(rep["still_valid"], 0)

    def test_audit_report_is_written(self):
        out = os.path.join(self.tmp, "audit.json")
        _make_run(self.runs_root, "run_20260910_000000_aaaaaaaa", [])
        with open(self.digest, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 2, "run_id": "r", "ever_passed": [],
                       "per_skill": []}, f)
        CSkillVerifier.audit_evidence(path=self.digest, runs_root=self.runs_root,
                                      write=True, audit_path=out)
        self.assertTrue(os.path.exists(out))
        with open(out, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f)["artifact_type"], "c_skill_audit")

    def test_missing_digest_reports_error(self):
        rep = CSkillVerifier.audit_evidence(
            path=os.path.join(self.tmp, "nope.json"), write=False)
        self.assertIn("error", rep)


if __name__ == "__main__":
    unittest.main()
