"""Versioned delivery contracts for Game-Agent.

The contracts are intentionally standard-library only. They provide lightweight
validation and canonical serialization for CLI, HTTP, MCP, workflow, and gate
layers without adding a schema dependency to the project.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json


SCHEMA_VERSION = "1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def new_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256((prefix + ":" + canonical_json(value)).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


@dataclass
class ArtifactRef:
    artifact_id: str
    artifact_type: str
    schema_version: str = SCHEMA_VERSION
    run_id: str = ""
    sha256: str = ""
    relative_path: str = ""
    size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class GameIntent:
    title: str
    genre: str
    target_platforms: List[str] = field(default_factory=lambda: ["web"])
    custom_rules: str = ""
    profile: str = "web_survivor_vertical_v1"
    run_id: str = ""
    intent_id: str = ""
    created_at: str = field(default_factory=utc_now)
    created_by: Dict[str, Any] = field(default_factory=lambda: {"subject_id": "local", "source": "unknown"})
    out_of_scope: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)

    artifact_type: str = field(init=False, default="GameIntent")
    schema_version: str = field(init=False, default=SCHEMA_VERSION)

    def __post_init__(self) -> None:
        self.title = str(self.title).strip()[:160]
        self.genre = str(self.genre).strip()[:80]
        if not self.title:
            raise ValueError("GameIntent.title must not be empty")
        if not self.intent_id:
            self.intent_id = new_id("intent", {"title": self.title, "genre": self.genre, "rules": self.custom_rules})
        if not self.run_id:
            self.run_id = new_id("run", {"intent_id": self.intent_id, "created_at": self.created_at})

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "artifact_id": self.intent_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "title": self.title,
            "genre": self.genre,
            "target_platforms": self.target_platforms,
            "custom_rules": self.custom_rules,
            "profile": self.profile,
            "out_of_scope": self.out_of_scope,
            "constraints": self.constraints,
        }
        data["content_hash"] = content_hash({k: v for k, v in data.items() if k != "content_hash"})
        return data


@dataclass
class GameSpec:
    intent_ref: str
    run_id: str
    title: str
    genre: str
    target_platforms: List[str]
    core_loop: List[str]
    acceptance_scenarios: List[str]
    non_functional: Dict[str, Any] = field(default_factory=dict)
    asset_requirements: Dict[str, Any] = field(default_factory=dict)
    out_of_scope: List[str] = field(default_factory=list)
    spec_id: str = ""
    created_at: str = field(default_factory=utc_now)

    artifact_type: str = field(init=False, default="GameSpec")
    schema_version: str = field(init=False, default=SCHEMA_VERSION)

    def __post_init__(self) -> None:
        if not self.spec_id:
            self.spec_id = new_id("spec", {"intent_ref": self.intent_ref, "run_id": self.run_id})
        if not self.core_loop:
            raise ValueError("GameSpec.core_loop must contain at least one step")
        if not self.acceptance_scenarios:
            raise ValueError("GameSpec.acceptance_scenarios must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "artifact_id": self.spec_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "intent_ref": self.intent_ref,
            "title": self.title,
            "genre": self.genre,
            "target_platforms": self.target_platforms,
            "core_loop": self.core_loop,
            "acceptance_scenarios": self.acceptance_scenarios,
            "non_functional": self.non_functional,
            "asset_requirements": self.asset_requirements,
            "out_of_scope": self.out_of_scope,
        }
        data["content_hash"] = content_hash({k: v for k, v in data.items() if k != "content_hash"})
        return data


@dataclass
class CapabilityDescriptor:
    capability_id: str
    version: str
    kind: str
    accepts: List[Dict[str, Any]]
    produces: List[Dict[str, Any]]
    implementation: Dict[str, Any]
    permissions: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    evidence_requirements: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    failure_policy: str = "block"
    maturity: str = "M1"

    artifact_type: str = field(init=False, default="CapabilityDescriptor")
    schema_version: str = field(init=False, default=SCHEMA_VERSION)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "version": self.version,
            "kind": self.kind,
            "accepts": self.accepts,
            "produces": self.produces,
            "implementation": self.implementation,
            "permissions": self.permissions,
            "resource_limits": self.resource_limits,
            "evidence_requirements": self.evidence_requirements,
            "preconditions": self.preconditions,
            "failure_policy": self.failure_policy,
            "maturity": self.maturity,
        }


@dataclass
class WorkflowNode:
    node_id: str
    capability_id: str
    capability_version: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    gate_after: Optional[str] = None
    retry_limit: int = 0
    timeout_seconds: int = 120
    failure_policy: str = "block"

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class WorkflowPlan:
    run_id: str
    intent_ref: str
    spec_ref: str
    profile: str
    nodes: List[WorkflowNode]
    plan_id: str = ""
    created_at: str = field(default_factory=utc_now)

    artifact_type: str = field(init=False, default="WorkflowPlan")
    schema_version: str = field(init=False, default=SCHEMA_VERSION)

    def __post_init__(self) -> None:
        if not self.plan_id:
            self.plan_id = new_id("plan", {"run_id": self.run_id, "nodes": [n.node_id for n in self.nodes]})
        ids = {n.node_id for n in self.nodes}
        for node in self.nodes:
            missing = set(node.depends_on) - ids
            if missing:
                raise ValueError(f"WorkflowPlan node {node.node_id} depends on unknown nodes: {sorted(missing)}")

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "artifact_id": self.plan_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "intent_ref": self.intent_ref,
            "spec_ref": self.spec_ref,
            "profile": self.profile,
            "nodes": [node.to_dict() for node in self.nodes],
        }
        data["content_hash"] = content_hash({k: v for k, v in data.items() if k != "content_hash"})
        return data


@dataclass
class EvidencePack:
    run_id: str
    target: str
    observations: List[Dict[str, Any]] = field(default_factory=list)
    references: List[ArtifactRef] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    evidence_id: str = ""
    created_at: str = field(default_factory=utc_now)

    artifact_type: str = field(init=False, default="EvidencePack")
    schema_version: str = field(init=False, default=SCHEMA_VERSION)

    def __post_init__(self) -> None:
        if not self.evidence_id:
            self.evidence_id = new_id("evidence", {"run_id": self.run_id, "target": self.target, "created_at": self.created_at})

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "artifact_id": self.evidence_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "target": self.target,
            "observations": self.observations,
            "references": [ref.to_dict() for ref in self.references],
            "metrics": self.metrics,
            "environment": self.environment,
            "errors": self.errors,
        }
        data["content_hash"] = content_hash({k: v for k, v in data.items() if k != "content_hash"})
        return data


@dataclass
class GateDecision:
    run_id: str
    gate_id: str
    result: str
    blocking: bool
    policy_version: str
    evidence_refs: List[str] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)
    decided_by: Dict[str, Any] = field(default_factory=lambda: {"type": "automation"})
    decision_id: str = ""
    created_at: str = field(default_factory=utc_now)

    artifact_type: str = field(init=False, default="GateDecision")
    schema_version: str = field(init=False, default=SCHEMA_VERSION)

    def __post_init__(self) -> None:
        self.result = self.result.upper()
        if self.result not in {"PASS", "FAIL", "BLOCKED", "SKIPPED"}:
            raise ValueError(f"Unknown gate decision result: {self.result}")
        if not self.decision_id:
            # seed 必须包含裁决内容：同一次运行里同一门禁可能被重新裁决（例如先 FAIL 后修复再 PASS），
            # 只用 run_id+gate_id+created_at 会撞出同一个 id 却内容不同，被工件库判为哈希冲突。
            self.decision_id = new_id("decision", {
                "run_id": self.run_id,
                "gate_id": self.gate_id,
                "created_at": self.created_at,
                "result": self.result,
                "reason_codes": list(self.reason_codes),
            })

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "artifact_id": self.decision_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "gate_id": self.gate_id,
            "result": self.result,
            "blocking": self.blocking,
            "policy_version": self.policy_version,
            "evidence_refs": self.evidence_refs,
            "reason_codes": self.reason_codes,
            "decided_by": self.decided_by,
        }
        data["content_hash"] = content_hash({k: v for k, v in data.items() if k != "content_hash"})
        return data


@dataclass
class ReleaseManifest:
    run_id: str
    release_channel: str
    release_status: str
    candidate_artifact: ArtifactRef
    intent_ref: str
    spec_ref: str
    workflow_ref: str
    evidence_ref: str
    gate_decision_refs: List[str]
    capability_versions: Dict[str, str] = field(default_factory=dict)
    dependency_lock: Dict[str, Any] = field(default_factory=dict)
    approval: Dict[str, Any] = field(default_factory=dict)
    rollback_ref: Optional[str] = None
    release_id: str = ""
    created_at: str = field(default_factory=utc_now)

    artifact_type: str = field(init=False, default="ReleaseManifest")
    schema_version: str = field(init=False, default=SCHEMA_VERSION)

    def __post_init__(self) -> None:
        if self.release_channel not in {"preview", "staging", "production"}:
            raise ValueError("release_channel must be preview, staging or production")
        if self.release_status not in {"candidate", "staged", "approved", "released", "revoked", "rolled_back"}:
            raise ValueError("invalid release_status")
        if not self.release_id:
            self.release_id = new_id("release", {"run_id": self.run_id, "channel": self.release_channel, "created_at": self.created_at})

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "artifact_id": self.release_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "release_channel": self.release_channel,
            "release_status": self.release_status,
            "candidate_artifact": self.candidate_artifact.to_dict(),
            "intent_ref": self.intent_ref,
            "spec_ref": self.spec_ref,
            "workflow_ref": self.workflow_ref,
            "evidence_ref": self.evidence_ref,
            "gate_decision_refs": self.gate_decision_refs,
            "capability_versions": self.capability_versions,
            "dependency_lock": self.dependency_lock,
            "approval": self.approval,
            "rollback_ref": self.rollback_ref,
        }
        data["content_hash"] = content_hash({k: v for k, v in data.items() if k != "content_hash"})
        return data
