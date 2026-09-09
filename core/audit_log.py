"""Append-only JSONL audit events for runs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict

from core.contracts import canonical_json, utc_now


class AuditLog:
    def __init__(self, run_dir: Path):
        self.audit_dir = Path(run_dir) / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.audit_dir / "events.jsonl"
        self.chain_path = self.audit_dir / "events.sha256"
        self._last_hash = self.chain_path.read_text(encoding="utf-8").strip() if self.chain_path.exists() else ""

    def append(self, event_type: str, **payload: Any) -> Dict[str, Any]:
        event = {"event_type": event_type, "created_at": utc_now(), "previous_hash": self._last_hash, "payload": payload}
        encoded = (canonical_json(event) + "\n").encode("utf-8")
        with self.path.open("ab") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        self._last_hash = hashlib.sha256(encoded).hexdigest()
        self.chain_path.write_text(self._last_hash, encoding="utf-8")
        return event

    def verify(self) -> Dict[str, Any]:
        previous = ""
        errors = []
        if not self.path.exists():
            return {"passed": True, "events": 0, "errors": []}
        count = 0
        for line in self.path.read_bytes().splitlines(keepends=True):
            try:
                event = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(str(exc))
                continue
            if event.get("previous_hash", "") != previous:
                errors.append(f"event {count} previous hash mismatch")
            previous = hashlib.sha256(line).hexdigest()
            count += 1
        if self.chain_path.exists() and self.chain_path.read_text(encoding="utf-8").strip() != previous:
            errors.append("chain head mismatch")
        return {"passed": not errors, "events": count, "errors": errors}
