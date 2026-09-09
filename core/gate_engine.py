"""Versioned G0-G7 gate engine."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from core.artifact_store import ArtifactStore
from core.contracts import EvidencePack, GateDecision


class GateEngine:
    POLICY_VERSION = "release-policy@1.0.0"
    REQUIRED = ("G0", "G1", "G2", "G3", "G4", "G5")

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
