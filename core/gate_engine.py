"""Versioned G0-G7 gate engine."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from core.artifact_store import ArtifactStore
from core.contracts import EvidencePack, GateDecision


class GateEngine:
    POLICY_VERSION = "release-policy@1.0.0"
    # G0-G5 是构建与运行门禁；G6 裁决 Preview 候选，G7 裁决生产候选
    REQUIRED = ("G0", "G1", "G2", "G3", "G4", "G5")
    PREVIEW_GATE = "G6"
    PRODUCTION_GATE = "G7"
    PRODUCTION_APPROVER_ROLE = "release_manager"

    def __init__(self, store: ArtifactStore):
        self.store = store

    def evaluate(
        self,
        gate_id: str,
        *,
        passed: bool,
        evidence_refs: Iterable[str] = (),
        reason_codes: Iterable[str] = (),
        blocking: bool = True,
        decided_by: Dict[str, Any] | None = None,
    ) -> GateDecision:
        result = "PASS" if passed else "FAIL"
        decision = GateDecision(
            run_id=self.store.run_dir.name,
            gate_id=gate_id,
            result=result,
            blocking=blocking,
            policy_version=self.POLICY_VERSION,
            evidence_refs=list(evidence_refs),
            reason_codes=list(reason_codes),
            decided_by=decided_by or {"type": "automation", "identity": "GateEngine@1.0.0"},
        )
        self.store.put_json("GateDecision", decision.to_dict(), artifact_id=decision.decision_id)
        return decision

    def evaluate_evidence(self, evidence: EvidencePack, gate_id: str = "G5") -> GateDecision:
        errors = list(evidence.errors)
        refs_ok = all(ref.sha256 and ref.relative_path for ref in evidence.references)
        passed = not errors and refs_ok
        reasons = []
        if errors:
            reasons.append("evidence_errors_present")
        if not refs_ok:
            reasons.append("evidence_reference_incomplete")
        return self.evaluate(gate_id, passed=passed, reason_codes=reasons)

    def can_create_preview(self, decisions: Iterable[GateDecision]) -> bool:
        return {d.gate_id for d in decisions if d.result == "PASS"}.issuperset(self.REQUIRED)

    @staticmethod
    def _gate_results(decisions: Iterable[Any]) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for decision in decisions:
            gate_id = decision.get("gate_id") if isinstance(decision, dict) else getattr(decision, "gate_id", None)
            result = decision.get("result") if isinstance(decision, dict) else getattr(decision, "result", None)
            if gate_id:
                results[gate_id] = result or ""
        return results

    def evaluate_release_gate(
        self,
        gate_id: str,
        decisions: Iterable[Any],
        approval: Dict[str, Any] | None = None,
    ) -> GateDecision:
        """G6/G7 发布门禁裁决。

        G6（Preview 候选）：G0-G5 全部 PASS。
        G7（生产候选）：G0-G6 全部 PASS，且 release_manager 已显式批准。
        审批缺失或角色不符一律 FAIL，绝不用 Preview 资格替代生产审批。
        """
        if gate_id not in (self.PREVIEW_GATE, self.PRODUCTION_GATE):
            raise ValueError("gate_id must be G6 or G7")

        results = self._gate_results(decisions)
        prerequisites = self.REQUIRED if gate_id == self.PREVIEW_GATE else self.REQUIRED + (self.PREVIEW_GATE,)
        reason_codes = [f"gate_not_passed:{g}" for g in prerequisites if results.get(g) != "PASS"]

        if gate_id == self.PRODUCTION_GATE:
            approval = approval or {}
            if approval.get("role") != self.PRODUCTION_APPROVER_ROLE or not approval.get("approved"):
                reason_codes.append(f"approval_required:{self.PRODUCTION_APPROVER_ROLE}")

        refs = []
        for decision in decisions:
            if isinstance(decision, dict):
                refs.append(decision.get("decision_id") or decision.get("artifact_id") or "")
            else:
                refs.append(getattr(decision, "decision_id", ""))
        return self.evaluate(
            gate_id,
            passed=not reason_codes,
            evidence_refs=[r for r in refs if r],
            reason_codes=reason_codes,
        )
