"""Immutable, content-addressed artifacts for a single Game-Agent run."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from core.contracts import ArtifactRef, canonical_json, content_hash, utc_now


class ArtifactIntegrityError(RuntimeError):
    pass


class ArtifactStore:
    """Filesystem artifact store with create-only semantics after sealing."""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir).resolve()
        self.artifacts_dir = self.run_dir / "artifacts"
        self.blobs_dir = self.artifacts_dir / "blobs" / "sha256"
        self.index_path = self.artifacts_dir / "index.json"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        self._index = self._load_index()
        self._sealed = False

    def _load_index(self) -> Dict[str, Any]:
        if not self.index_path.exists():
            return {"schema_version": 1, "run_id": self.run_dir.name, "sealed": False, "artifacts": {}}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError(f"Cannot read artifact index: {exc}") from exc
        if not isinstance(data.get("artifacts"), dict):
            raise ArtifactIntegrityError("Artifact index has invalid artifacts map")
        return data

    def _write_index(self) -> None:
        payload = canonical_json(self._index).encode("utf-8")
        tmp = self.index_path.with_suffix(".tmp")
        tmp.write_bytes(payload)
        os.replace(tmp, self.index_path)

    def seal(self) -> None:
        self._index["sealed"] = True
        self._index["sealed_at"] = utc_now()
        self._sealed = True
        self._write_index()

    @property
    def sealed(self) -> bool:
        return self._sealed or bool(self._index.get("sealed"))

    def put_bytes(
        self,
        artifact_type: str,
        data: bytes,
        *,
        schema_version: str = "1.0",
        artifact_id: Optional[str] = None,
        parent_artifact_id: Optional[str] = None,
        producer_capability: Optional[str] = None,
        relative_name: Optional[str] = None,
    ) -> ArtifactRef:
        if self.sealed:
            raise ArtifactIntegrityError("Run is sealed; artifacts are immutable")
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        artifact_id = artifact_id or f"art_{digest.split(':', 1)[1][:20]}"
        existing = self._index["artifacts"].get(artifact_id)
        if existing:
            if existing.get("sha256") != digest:
                raise ArtifactIntegrityError(f"Artifact ID already exists with a different hash: {artifact_id}")
            return ArtifactRef(**{k: existing[k] for k in ArtifactRef.__dataclass_fields__ if k in existing})

        raw_hash = digest.split(":", 1)[1]
        blob_path = self.blobs_dir / raw_hash[:2] / raw_hash[2:4] / raw_hash
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        if blob_path.exists():
            if hashlib.sha256(blob_path.read_bytes()).hexdigest() != raw_hash:
                raise ArtifactIntegrityError(f"Content-addressed blob is corrupted: {blob_path}")
        else:
            tmp = blob_path.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, blob_path)

        relative_path = str(blob_path.relative_to(self.run_dir)).replace("\\", "/")
        ref = ArtifactRef(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            schema_version=schema_version,
            run_id=self.run_dir.name,
            sha256=digest,
            relative_path=relative_path,
            size_bytes=len(data),
        )
        record = ref.to_dict()
        record.update({
            "parent_artifact_id": parent_artifact_id,
            "producer_capability": producer_capability,
            "created_at": utc_now(),
            "relative_name": relative_name,
        })
        self._index["artifacts"][artifact_id] = record
        self._write_index()
        return ref

    def put_json(self, artifact_type: str, value: Dict[str, Any], **kwargs: Any) -> ArtifactRef:
        data = dict(value)
        data.setdefault("artifact_type", artifact_type)
        data.setdefault("schema_version", kwargs.get("schema_version", "1.0"))
        data["content_hash"] = content_hash({k: v for k, v in data.items() if k != "content_hash"})
        return self.put_bytes(artifact_type, canonical_json(data).encode("utf-8"), **kwargs)

    def get_ref(self, artifact_id: str) -> ArtifactRef:
        record = self._index["artifacts"].get(artifact_id)
        if not record:
            raise KeyError(artifact_id)
        return ArtifactRef(**{k: record[k] for k in ArtifactRef.__dataclass_fields__ if k in record})

    def read_bytes(self, artifact_id: str, verify: bool = True) -> bytes:
        ref = self.get_ref(artifact_id)
        path = self.run_dir / ref.relative_path
        data = path.read_bytes()
        if verify and "sha256:" + hashlib.sha256(data).hexdigest() != ref.sha256:
            raise ArtifactIntegrityError(f"Artifact hash mismatch: {artifact_id}")
        return data

    def verify_all(self) -> Dict[str, Any]:
        errors = []
        checked = 0
        for artifact_id in self._index["artifacts"]:
            checked += 1
            try:
                self.read_bytes(artifact_id, verify=True)
            except (OSError, KeyError, ArtifactIntegrityError) as exc:
                errors.append({"artifact_id": artifact_id, "error": str(exc)})
        return {"run_id": self.run_dir.name, "checked": checked, "passed": not errors, "errors": errors}

    def list_refs(self) -> list[ArtifactRef]:
        return [self.get_ref(artifact_id) for artifact_id in self._index["artifacts"]]
