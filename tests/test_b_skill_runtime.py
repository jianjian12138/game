"""tests/test_b_skill_runtime.py — B 类确定性算法的真实运行 + 验收 + 防伪（W4）。

B 类不依赖 LLM、不依赖网络：纯函数运行 + 数值断言。所以"它能不能用"的证据
就是一次真实运行 + acceptance 全过 + 可复现。本测试覆盖：
  1. 每项已实现的 B 技能真实运行且验收通过（空 payload 不行，断言不过不行）；
  2. 依赖 DCC/GPU 的 B 技能返回 NEEDS_RUNTIME_TOOL，不伪证；
  3. register_b_skill 的防伪底线（没真跑通 / 没 runtime 记录都不许注册）；
  4. 证据摘要双口径（ever_passed / last_ok）与离线复验发现 stale。
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from core import b_skill_runtime as B
from core.b_skill_runtime import (BATCH1_IMPLEMENTED, BATCH1_RUNTIME_TOOL,
                                  BSkillRuntime, get_spec, spec_ids, verify_all)
from core.capability_registry import capability_registry as _cr
from core.skill_registry import skill_registry as _sr


class TestBImplementedRun(unittest.TestCase):
    """每一项已实现的 B 技能都必须能真实跑通且通过自身数值断言。"""

    def test_all_65_specs_are_covered(self):
        # W4 收尾：B 类共 65 项 = 62 确定性实现 + 3 DCC/GPU 标红（不伪证）
        ids = spec_ids()
        self.assertEqual(len(ids), 65)
        impl = [s for s in ids if get_spec(s).needs_runtime_tool is None]
        rt = [s for s in ids if get_spec(s).needs_runtime_tool]
        self.assertEqual(len(impl), 62)
        self.assertEqual(len(rt), 3)

    def test_every_implemented_spec_runs_and_passes(self):
        rt = BSkillRuntime()
        for sid in BATCH1_IMPLEMENTED:
            with self.subTest(sid):
                r = rt.run_skill(sid)
                self.assertTrue(r.ok, r.errors)
                self.assertEqual(r.runtime, "pure_python")
                # 可复现：同输入（默认 sample）两次结果一致
                r2 = rt.run_skill(sid)
                self.assertEqual(r.payload, r2.payload)

    def test_runtime_tool_skills_are_not_faked(self):
        rt = BSkillRuntime()
        for sid in BATCH1_RUNTIME_TOOL:
            with self.subTest(sid):
                r = rt.run_skill(sid)
                self.assertFalse(r.ok)
                self.assertEqual(r.status, B.BSkillStatus.NEEDS_RUNTIME_TOOL)
                self.assertTrue(r.needs_runtime_tool)
                self.assertIn("不伪证", " ".join(r.errors))

    def test_unknown_spec_is_no_spec(self):
        r = BSkillRuntime().run_skill("no_such_b_skill")
        self.assertEqual(r.status, B.BSkillStatus.NO_SPEC)

    def test_acceptance_rejects_wrong_input(self):
        # aabb 期望重叠却给分离的两个盒，应判 ACCEPTANCE_FAILED
        r = BSkillRuntime().run_skill("aabb_collision_detection", {
            "a": {"x": 0, "y": 0, "w": 2, "h": 2},
            "b": {"x": 9, "y": 9, "w": 2, "h": 2}, "expect_overlap": True})
        self.assertEqual(r.status, B.BSkillStatus.ACCEPTANCE_FAILED)


class TestRegisterBAntiFake(unittest.TestCase):
    """没真跑通 / 没 runtime 记录，都不许注册——这是 B 类防伪底线。"""

    def setUp(self):
        _sr._skills.clear()
        _cr._descriptors.clear()
        from core.skill_classification import apply_classification
        _sr.ingest_from_registry()
        apply_classification(_sr)

    def tearDown(self):
        _sr._skills.clear()
        _cr._descriptors.clear()

    def test_real_pass_registers(self):
        r = BSkillRuntime().run_skill("a_star_pathfinding")
        desc = _sr.register_b_skill("a_star_pathfinding", result=r)
        self.assertEqual(_sr.counts()["B_REGISTERED"], 1)
        self.assertEqual(desc.capability_id, "skill.a_star_pathfinding")

    def test_no_runtime_record_rejected(self):
        r = BSkillRuntime().run_skill("a_star_pathfinding")
        r.runtime = ""  # 抹掉运行证据
        with self.assertRaises(ValueError):
            _sr.register_b_skill("a_star_pathfinding", result=r)

    def test_acceptance_failed_not_registered(self):
        r = BSkillRuntime().run_skill("aabb_collision_detection", {
            "a": {"x": 0, "y": 0, "w": 2, "h": 2},
            "b": {"x": 9, "y": 9, "w": 2, "h": 2}, "expect_overlap": True})
        self.assertFalse(r.ok)
        with self.assertRaises(ValueError):
            _sr.register_b_skill("aabb_collision_detection", result=r)

    def test_runtime_tool_skill_not_registered(self):
        r = BSkillRuntime().run_skill("pbr_five_channel_baking")
        self.assertFalse(r.ok)
        with self.assertRaises(ValueError):
            _sr.register_b_skill("pbr_five_channel_baking", result=r)


class _BHistTmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bcsv_")
        self.runs_root = os.path.join(self.tmp, "output", "runs")
        os.makedirs(self.runs_root, exist_ok=True)
        self.digest = os.path.join(self.tmp, "digest.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_run(self, run_id, results, started_at="2026-09-10 00:00:00"):
        from core.artifact_store import ArtifactStore
        store = ArtifactStore(Path(self.runs_root) / run_id)
        ev = {"artifact_type": "b_skill_verification", "run_id": run_id,
              "started_at": started_at, "elapsed_seconds": 0.1,
              "total": len(results), "ok": sum(1 for r in results if r.get("ok")),
              "failed": sum(1 for r in results if not r.get("ok")),
              "results": results}
        store.put_json("b_skill_verification", ev,
                       artifact_id="art_b_skill_verification")
        for r in results:
            if r.get("payload") and r.get("ok"):
                store.put_json("b_skill_payload", r["payload"],
                               artifact_id=f"art_payload_{r['skill_id']}")


class TestBDigestMerge(_BHistTmp):
    def _res(self, sid, ok, payload=None, error=""):
        return {"skill_id": sid, "status": "OK" if ok else "ACCEPTANCE_FAILED",
                "ok": ok, "runtime": "pure_python", "latency_ms": 1,
                "payload": payload or {}, "errors": [error] if error else []}

    def test_merge_keeps_ever_passed(self):
        self._make_run("run_1", [self._res("a_star_pathfinding", True, {"x": 1})])
        self._make_run("run_2", [self._res("a_star_pathfinding", False, error="短")])
        ev = {"run_id": "run_2", "total": 1, "ok": 0, "failed": 1,
              "results": [self._res("a_star_pathfinding", False, error="短")]}
        B.BSkillRuntime.write_digest(ev, path=self.digest, runs_root=self.runs_root)
        with open(self.digest, encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d["schema_version"], 2)
        self.assertIn("a_star_pathfinding", d["ever_passed"])
        it = next(i for i in d["per_skill"] if i["skill_id"] == "a_star_pathfinding")
        self.assertTrue(it["ever_passed"])
        self.assertFalse(it["last_ok"])
        self.assertEqual(it["pass_run_id"], "run_1")
        self.assertEqual(it["pass_rate"], 0.5)


class TestBAudit(_BHistTmp):
    def test_stale_detected_when_contract_changes(self):
        # 通过时 payload 满足旧验收；改契约后（spec 收紧）应判 stale。
        rid = "run_1"
        self._make_run(rid, [{
            "skill_id": "a_star_pathfinding", "status": "OK", "ok": True,
            "runtime": "pure_python", "latency_ms": 1,
            "payload": {"start": [0, 0], "goal": [7, 7], "path": [[0, 0], [7, 7]],
                        "length": 2, "cost": -1},  # 非相邻跳跃 + cost 错
            "errors": []}])
        with open(self.digest, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 2, "run_id": rid, "ever_passed": ["a_star_pathfinding"],
                       "per_skill": [{"skill_id": "a_star_pathfinding", "ever_passed": True,
                                     "pass_run_id": rid, "pass_payload_sha256": "sha256:x"}]}, f)
        rep = B.BSkillRuntime.audit_evidence(path=self.digest, runs_root=self.runs_root,
                                             write=False)
        self.assertEqual(rep["stale"], 1)
        self.assertEqual(rep["details"][0]["audit"], "stale")

    def test_still_valid_when_contract_unchanged(self):
        rt = BSkillRuntime()
        r = rt.run_skill("score_overflow_checker")
        rid = "run_1"
        self._make_run(rid, [{"skill_id": "score_overflow_checker", "status": "OK",
                              "ok": True, "runtime": "pure_python", "latency_ms": 1,
                              "payload": r.payload, "errors": []}])
        with open(self.digest, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 2, "run_id": rid, "ever_passed": ["score_overflow_checker"],
                       "per_skill": [{"skill_id": "score_overflow_checker", "ever_passed": True,
                                     "pass_run_id": rid, "pass_payload_sha256": "sha256:x"}]}, f)
        rep = B.BSkillRuntime.audit_evidence(path=self.digest, runs_root=self.runs_root,
                                             write=False)
        self.assertEqual(rep["still_valid"], 1)


if __name__ == "__main__":
    unittest.main()
