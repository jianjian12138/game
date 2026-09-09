"""Release candidate creation with gate and hash preconditions."""
from __future__ import annotations

from typing import Any, Dict, List

from core.artifact_store import ArtifactStore
from core.contracts import ArtifactRef, ReleaseManifest


class ReleaseBlockedError(RuntimeError):
    pass


class ReleaseService:
    def __init__(self, artifact_store: ArtifactStore):
        self.store = artifact_store

    @staticmethod
    def _passed(decisions: List[Dict[str, Any]], required: List[str]) -> bool:
        by_gate = {item.get("gate_id"): item for item in decisions}
        return all(by_gate.get(gate, {}).get("result") == "PASS" for gate in required)

    def create_candidate(
        self,
        *,
        channel: str,
        candidate_artifact: ArtifactRef,
        intent_ref: str,
        spec_ref: str,
        workflow_ref: str,
        evidence_ref: str,
        decisions: List[Dict[str, Any]],
        capability_versions: Dict[str, str] | None = None,
        approval: Dict[str, Any] | None = None,
    ) -> ReleaseManifest:
        if channel not in {"preview", "production"}:
            raise ValueError("channel must be preview or production")
        required = ["G0", "G1", "G2", "G3", "G4", "G5"]
        if not self._passed(decisions, required):
            raise ReleaseBlockedError("G0-G5 must all pass before creating a candidate")
        approval = approval or {}
        if channel == "production":
            if approval.get("role") != "release_manager" or not approval.get("approved"):
                raise ReleaseBlockedError("Production candidate requires release_manager approval")
            if not self._passed(decisions, required + ["G6"]):
                raise ReleaseBlockedError("G6 must pass before creating a production candidate")
        manifest = ReleaseManifest(
            run_id=self.store.run_dir.name,
            release_channel=channel,
            release_status="approved" if channel == "production" else "candidate",
            candidate_artifact=candidate_artifact,
            intent_ref=intent_ref,
            spec_ref=spec_ref,
            workflow_ref=workflow_ref,
            evidence_ref=evidence_ref,
            gate_decision_refs=[item.get("artifact_id", item.get("decision_id", "")) for item in decisions],
            capability_versions=capability_versions or {},
            approval=approval,
        )
        self.store.put_json("ReleaseManifest", manifest.to_dict(), artifact_id=manifest.release_id)
        return manifest
