"""Minimal versioned schema registry for delivery contracts."""
from __future__ import annotations

from typing import Any, Callable, Dict, Type

from core.contracts import (
    CapabilityDescriptor,
    EvidencePack,
    GameIntent,
    GameSpec,
    GateDecision,
    ReleaseManifest,
    WorkflowPlan,
)


class SchemaRegistry:
    def __init__(self) -> None:
        self._types: Dict[str, Type[Any]] = {
            "GameIntent": GameIntent,
            "GameSpec": GameSpec,
            "CapabilityDescriptor": CapabilityDescriptor,
            "WorkflowPlan": WorkflowPlan,
            "EvidencePack": EvidencePack,
            "GateDecision": GateDecision,
            "ReleaseManifest": ReleaseManifest,
        }

    def resolve(self, artifact_type: str, schema_version: str = "1.0") -> Type[Any]:
        if schema_version != "1.0":
            raise ValueError(f"Unsupported schema version: {artifact_type}@{schema_version}")
        try:
            return self._types[artifact_type]
        except KeyError as exc:
            raise KeyError(f"Unknown artifact type: {artifact_type}") from exc

    def validate_dict(self, value: Dict[str, Any], expected_type: str | None = None) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise TypeError("Artifact must be a JSON object")
        artifact_type = expected_type or value.get("artifact_type")
        if not artifact_type:
            raise ValueError("Artifact is missing artifact_type")
        self.resolve(artifact_type, str(value.get("schema_version", "1.0")))
        if value.get("schema_version", "1.0") != "1.0":
            raise ValueError("Only schema_version 1.0 is supported")
        return value

    def list_types(self) -> list[str]:
        return sorted(self._types)


schema_registry = SchemaRegistry()
