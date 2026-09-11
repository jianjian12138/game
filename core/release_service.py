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
        if channel not in {"preview", "staging", "production"}:
            raise ValueError("channel must be preview, staging or production")
        required = ["G0", "G1", "G2", "G3", "G4", "G5"]
        if not self._passed(decisions, required):
            raise ReleaseBlockedError("G0-G5 must all pass before creating a candidate")
        if not self._passed(decisions, ["G6"]):
            raise ReleaseBlockedError("G6 (Preview 候选门禁) must pass before creating a candidate")
        approval = approval or {}
        if channel == "production":
            if approval.get("role") != "release_manager" or not approval.get("approved"):
                raise ReleaseBlockedError("Production candidate requires release_manager approval")
            if not self._passed(decisions, ["G7"]):
                raise ReleaseBlockedError("G7 (生产候选门禁) must pass before creating a production candidate")
            # 人工审美与合规复核：G7 只证明机器门禁通过，AI 出图/合成音频的
            # 审美、版权与合规问题必须由具名的人签字，代码判定不了。
            from pipeline.human_review import HumanReviewBoard
            review_gate = HumanReviewBoard().production_gate(self.store.run_dir.name)
            if not review_gate["allowed"]:
                raise ReleaseBlockedError(
                    f"生产候选需人工复核(art/audio/release)全部 APPROVED：{review_gate.get('reason')}")
        manifest = ReleaseManifest(
            run_id=self.store.run_dir.name,
            release_channel=channel,
            release_status={"preview": "candidate", "staging": "staged",
                            "production": "approved"}[channel],
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
