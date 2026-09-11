#!/usr/bin/env python3
"""pipeline/release_drill.py: 发布门禁故障注入演练

目的不是「跑一遍成功流程」，而是证明门禁真的会拦：
每一条用例都故意制造一种违规输入，断言系统必须拒绝。
任何一条用例没有拦住，演练即为失败。
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.artifact_store import ArtifactStore
from core.contracts import ArtifactRef
from core.gate_engine import GateEngine
from core.release_service import ReleaseService, ReleaseBlockedError
from core.run_service import RunService
from core.security_guard import SecurityGuardError

CHANNELS_REQUIRED = ("G0", "G1", "G2", "G3", "G4", "G5", "G6")


def _build_run(tmp: str, gates: Dict[str, bool], under_output: bool = False) -> ArtifactStore:
    run_dir = Path(tmp) / (Path("output") / "runs" if under_output else ".") / "run_drill"
    store = ArtifactStore(run_dir)
    engine = GateEngine(store)
    for gate_id, passed in gates.items():
        engine.evaluate(gate_id, passed=passed)
    store.put_bytes("GameBuild", b"<html><canvas></canvas></html>", artifact_id="build-drill")
    return store


def _decisions(store: ArtifactStore) -> List[Dict[str, Any]]:
    import json
    return [json.loads(store.read_bytes(ref.artifact_id).decode("utf-8"))
            for ref in store.list_refs() if ref.artifact_type == "GateDecision"]


def _preview_kwargs(store: ArtifactStore) -> Dict[str, Any]:
    ref = next(r for r in store.list_refs() if r.artifact_type == "GameBuild")
    return dict(candidate_artifact=ref, intent_ref="i", spec_ref="s", workflow_ref="w", evidence_ref="e",
                decisions=_decisions(store))


def _expect_blocked(action: Callable[[], Any]) -> str:
    """执行动作，期望被 ReleaseBlockedError 拦下。"""
    try:
        action()
    except ReleaseBlockedError as exc:
        return f"blocked: {exc}"
    return "NOT_BLOCKED"


def run_drill() -> Dict[str, Any]:
    cases: List[Dict[str, Any]] = []

    def record(case: str, expected: str, actual: str) -> None:
        cases.append({"case": case, "expected": expected, "actual": actual,
                      "passed": actual.startswith(expected)})

    with tempfile.TemporaryDirectory() as tmp:
        # 1. G3 失败必须阻断 Preview
        store = _build_run(tmp, {g: g != "G3" for g in CHANNELS_REQUIRED})
        record("g3_fail_blocks_preview", "blocked",
               _expect_blocked(lambda: ReleaseService(store).create_candidate(channel="preview", **_preview_kwargs(store))))

    with tempfile.TemporaryDirectory() as tmp:
        # 2. 缺 G6 裁决不得创建任何候选
        store = _build_run(tmp, {g: g != "G6" for g in CHANNELS_REQUIRED})
        kwargs = _preview_kwargs(store)
        kwargs["decisions"] = [d for d in kwargs["decisions"] if d["gate_id"] != "G6"]
        record("missing_g6_blocks_preview", "blocked",
               _expect_blocked(lambda: ReleaseService(store).create_candidate(channel="preview", **kwargs)))

    with tempfile.TemporaryDirectory() as tmp:
        # 3. 生产候选缺 release_manager 审批必须阻断
        store = _build_run(tmp, {g: True for g in CHANNELS_REQUIRED})
        engine = GateEngine(store)
        decisions = _decisions(store) + [engine.evaluate_release_gate("G7", _decisions(store), approval={
            "role": "developer", "approved": True}).to_dict()]
        kwargs = _preview_kwargs(store)
        kwargs["decisions"] = decisions
        kwargs["approval"] = {"role": "developer", "approved": True}
        record("production_requires_release_manager", "blocked",
               _expect_blocked(lambda: ReleaseService(store).create_candidate(channel="production", **kwargs)))

    # 4. 未经过 Staging 不得直接提升到生产
    with tempfile.TemporaryDirectory() as tmp:
        store = _build_run(tmp, {g: True for g in CHANNELS_REQUIRED}, under_output=True)
        ReleaseService(store).create_candidate(channel="preview", **_preview_kwargs(store))
        service = RunService(workspace=Path(tmp))
        record("production_requires_staging", "blocked",
               _expect_blocked(lambda: service.promote_to_production(
                   "run_drill", {"role": "release_manager", "approved": True, "identity": "alice"})))

    # 5. run_id 路径穿越必须被安全守卫拒绝
    service = RunService()
    try:
        service.get_run_status("../../..")
        actual = "NOT_BLOCKED"
    except SecurityGuardError as exc:
        actual = f"blocked: {exc}"
    except FileNotFoundError:
        actual = "NOT_BLOCKED"
    record("run_id_path_traversal_rejected", "blocked", actual)

    # 6. 工件被篡改后完整性校验必须失败
    with tempfile.TemporaryDirectory() as tmp:
        store = _build_run(tmp, {g: True for g in CHANNELS_REQUIRED})
        ref = next(r for r in store.list_refs() if r.artifact_type == "GameBuild")
        target = Path(tmp) / "run_drill" / ref.relative_path
        target.write_bytes(b"tampered")
        integrity = store.verify_all()
        record("tampered_artifact_detected", "blocked",
               "blocked: artifact integrity check failed" if not integrity.get("passed", True) else "NOT_BLOCKED")

    passed = [c for c in cases if c["passed"]]
    return {
        "status": "PASS" if len(passed) == len(cases) else "FAIL",
        "total": len(cases),
        "passed": len(passed),
        "cases": cases,
    }


class ReleaseDrill:
    @staticmethod
    def run() -> Dict[str, Any]:
        return run_drill()


if __name__ == "__main__":
    report = run_drill()
    print(f"=== 发布门禁故障注入演练: {report['status']} ({report['passed']}/{report['total']}) ===")
    for case in report["cases"]:
        flag = "OK  " if case["passed"] else "FAIL"
        print(f"  [{flag}] {case['case']}: {case['actual'][:100]}")
