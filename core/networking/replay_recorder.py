"""
Match Replay Recorder and Playback Stream
Serializes deterministic input streams and provides playback seeking and stepping.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class ReplayFrame:
    tick: int
    inputs: Dict[str, Any]
    timestamp: float


class ReplayRecorder:
    """Records and replays game match input streams."""

    def __init__(self, match_id: str, seed: int, player_ids: List[str]):
        self.match_id = match_id
        self.seed = seed
        self.player_ids = player_ids
        self.frames: List[ReplayFrame] = []
        self.is_recording = True
        self.current_playback_index = 0

    def record_tick(self, tick: int, inputs: Dict[str, Any], timestamp: float = 0.0):
        if self.is_recording:
            self.frames.append(ReplayFrame(tick=tick, inputs=inputs, timestamp=timestamp))

    def stop_recording(self):
        self.is_recording = False

    def seek_to_tick(self, tick: int) -> int:
        for idx, f in enumerate(self.frames):
            if f.tick >= tick:
                self.current_playback_index = idx
                return idx
        self.current_playback_index = len(self.frames) - 1
        return self.current_playback_index

    def step_playback(self) -> Optional[ReplayFrame]:
        if self.current_playback_index < len(self.frames):
            frame = self.frames[self.current_playback_index]
            self.current_playback_index += 1
            return frame
        return None

    def export_replay_data(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "seed": self.seed,
            "player_ids": self.player_ids,
            "total_frames": len(self.frames),
            "frames": [{"tick": f.tick, "inputs": f.inputs, "timestamp": f.timestamp} for f in self.frames]
        }
