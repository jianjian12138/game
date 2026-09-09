"""Executable capability descriptors built from the existing registry."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from core.contracts import CapabilityDescriptor
from core.registry import STUDIO_TEAMS


class CapabilityRegistry:
    def __init__(self) -> None:
        self._descriptors: Dict[str, CapabilityDescriptor] = {}
        self._register_builtin()

    def _register_builtin(self) -> None:
        builtins = [
            CapabilityDescriptor(
                capability_id="intent.normalize", version="1.0.0", kind="normalizer",
                accepts=[{"type": "GameIntent", "schema_version": "1.0"}],
                produces=[{"type": "GameSpec", "schema_version": "1.0"}],
                implementation={"module": "core.contracts", "entrypoint": "GameSpec"},
                permissions={"filesystem": "none", "network": "disabled", "process": "none"},
                resource_limits={"timeout_seconds": 10, "max_memory_mb": 128},
                evidence_requirements=["input_hash", "output_hash"], maturity="M1",
            ),
            CapabilityDescriptor(
                capability_id="team.next_gen_3d_art", version="1.0.0", kind="team",
                accepts=[{"type": "GameSpec", "schema_version": "1.0"}],
                produces=[{"type": "asset_manifest", "schema_version": "1.0"}],
                implementation={"module": "core.registry", "entrypoint": "next_gen_3d_art_team"},
                permissions={"filesystem": "run_workspace", "network": "disabled", "process": "allowlist"},
                resource_limits={"timeout_seconds": 300, "max_memory_mb": 1024},
                evidence_requirements=["team_plan", "asset_hashes", "runtime_asset_smoke"], maturity="M2",
            ),
            CapabilityDescriptor(
                capability_id="gate.release", version="1.0.0", kind="gate",
                accepts=[{"type": "EvidencePack", "schema_version": "1.0"}],
                produces=[{"type": "GateDecision", "schema_version": "1.0"}],
                implementation={"module": "core.gate_engine", "entrypoint": "GateEngine.evaluate"},
                permissions={"filesystem": "run_read_only", "network": "disabled", "process": "none"},
                resource_limits={"timeout_seconds": 30, "max_memory_mb": 256},
                evidence_requirements=["evidence_hash", "policy_version"], maturity="M1",
            ),
        ]
        for descriptor in builtins:
            self.register(descriptor)

    def register(self, descriptor: CapabilityDescriptor) -> None:
        key = f"{descriptor.capability_id}@{descriptor.version}"
        if key in self._descriptors:
            raise ValueError(f"Capability already registered: {key}")
        self._descriptors[key] = descriptor

    def resolve(self, capability_id: str, version: str | None = None) -> CapabilityDescriptor:
        if version:
            return self._descriptors[f"{capability_id}@{version}"]
        candidates = [d for d in self._descriptors.values() if d.capability_id == capability_id]
        if not candidates:
            raise KeyError(capability_id)
        return sorted(candidates, key=lambda d: d.version)[-1]

    def list(self) -> List[CapabilityDescriptor]:
        return list(self._descriptors.values())

    def as_dict(self) -> List[Dict[str, Any]]:
        return [descriptor.to_dict() for descriptor in self.list()]


capability_registry = CapabilityRegistry()
