"""
Deterministic Lockstep Frame Synchronization
Manages tick-synchronized inputs, step execution, and state checksum desync detection.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set


@dataclass
class PlayerInput:
    player_id: str
    tick: int
    commands: Dict[str, Any] = field(default_factory=dict)


class LockstepSync:
    """Coordinates deterministic frame ticks across all connected peers."""

    def __init__(self, expected_players: List[str], tick_rate_hz: int = 30):
        self.expected_players: Set[str] = set(expected_players)
        self.tick_rate_hz = tick_rate_hz
        self.current_tick = 0
        # tick -> { player_id -> PlayerInput }
        self.input_buffer: Dict[int, Dict[str, PlayerInput]] = {}
        # tick -> state_checksum
        self.state_checksums: Dict[int, str] = {}
        self.desync_events: List[Dict[str, Any]] = []

    def submit_input(self, player_input: PlayerInput):
        t = player_input.tick
        self.input_buffer.setdefault(t, {})[player_input.player_id] = player_input

    def is_tick_ready(self, tick: int) -> bool:
        """Returns True when all expected players have submitted inputs for the given tick."""
        received = self.input_buffer.get(tick, {})
        return self.expected_players.issubset(received.keys())

    def advance_tick(self, state_dict: Dict[str, Any]) -> Optional[Dict[str, PlayerInput]]:
        """Advances to the next tick if all inputs are ready, records state checksum."""
        if not self.is_tick_ready(self.current_tick):
            return None

        inputs = self.input_buffer[self.current_tick]
        # Calculate state checksum
        state_str = str(sorted(state_dict.items()))
        chk = hashlib.sha256(state_str.encode("utf-8")).hexdigest()[:16]
        self.state_checksums[self.current_tick] = chk

        self.current_tick += 1
        return inputs

    def verify_peer_checksum(self, tick: int, peer_id: str, peer_checksum: str) -> bool:
        local_chk = self.state_checksums.get(tick)
        if local_chk and local_chk != peer_checksum:
            self.desync_events.append({
                "tick": tick,
                "peer_id": peer_id,
                "local_checksum": local_chk,
                "peer_checksum": peer_checksum
            })
            return False
        return True
