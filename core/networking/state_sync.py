"""
Server-Authoritative State Synchronization
Snapshot delta compression, client-side prediction, and server reconciliation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class WorldSnapshot:
    tick: int
    timestamp: float
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class StateSync:
    """Manages world state snapshots, delta compression, and client prediction."""

    def __init__(self):
        self.snapshots: Dict[int, WorldSnapshot] = {}
        self.pending_inputs: List[Dict[str, Any]] = []

    def record_snapshot(self, snapshot: WorldSnapshot):
        self.snapshots[snapshot.tick] = snapshot
        # Prune older than 120 ticks
        cutoff = snapshot.tick - 120
        old_ticks = [t for t in self.snapshots if t < cutoff]
        for ot in old_ticks:
            del self.snapshots[ot]

    def compute_delta(self, from_tick: int, to_tick: int) -> Optional[Dict[str, Any]]:
        snap_from = self.snapshots.get(from_tick)
        snap_to = self.snapshots.get(to_tick)
        if not snap_from or not snap_to:
            return None

        delta: Dict[str, Any] = {}
        for ent_id, to_data in snap_to.entities.items():
            from_data = snap_from.entities.get(ent_id, {})
            ent_diff = {}
            for k, v in to_data.items():
                if from_data.get(k) != v:
                    ent_diff[k] = v
            if ent_diff:
                delta[ent_id] = ent_diff

        return delta

    def reconcile_client(self, server_snapshot: WorldSnapshot,
                         predicted_local_state: Dict[str, Any],
                         apply_input_fn: Any) -> Dict[str, Any]:
        """Rewinds client state to server snapshot and re-applies pending unacknowledged inputs."""
        local_ent = server_snapshot.entities.get("local_player", {})
        reconciled = dict(local_ent)

        # Filter pending inputs newer than server tick
        self.pending_inputs = [inp for inp in self.pending_inputs if inp.get("tick", 0) > server_snapshot.tick]

        # Re-apply remaining inputs
        for inp in self.pending_inputs:
            reconciled = apply_input_fn(reconciled, inp)

        return reconciled
