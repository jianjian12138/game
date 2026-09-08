"""
Beat Sync Engine — 节拍同步引擎
==================================
基于系统时钟精确跟踪音乐节拍位置，为节奏游戏提供节拍事件。
支持BPM检测、延迟补偿、节拍订阅。
"""

from __future__ import annotations
import time
import math
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class BeatEvent:
    """节拍事件。"""
    beat_number: int        # 第几拍（从0开始）
    timestamp: float        # 系统时间戳
    beat_fraction: float    # 拍内进度（0.0–1.0）
    measure: int            # 第几小节
    beat_in_measure: int    # 在小节内的拍号


class BeatSyncEngine:
    """
    节拍同步引擎：精确跟踪BPM并发布节拍事件。

    用法::
        sync = BeatSyncEngine(bpm=138, offset=0.05, time_signature=4)
        sync.start()

        # 每帧调用
        events = sync.tick()
        for evt in events:
            if evt.beat_in_measure == 0:
                flash_screen()   # 每小节第一拍闪屏

        # 查询当前位置
        beat, frac = sync.current_beat()
        note_pos = sync.beat_to_seconds(1.5)  # 1.5拍对应的时间
    """

    def __init__(
        self,
        bpm: float = 120.0,
        offset: float = 0.0,       # 音频延迟补偿（秒）
        time_signature: int = 4,   # 拍号分子（每小节几拍）
    ):
        self.bpm = bpm
        self.offset = offset
        self.time_signature = time_signature
        self._spb = 60.0 / bpm     # 每拍秒数

        self._start_time: Optional[float] = None
        self._last_beat: int = -1
        self._subscribers: list[Callable[[BeatEvent], None]] = []
        self._running: bool = False

    # ------------------------------------------------------------------
    # 控制
    # ------------------------------------------------------------------

    def start(self, start_time: Optional[float] = None):
        """开始计时。start_time 为音频实际开始时间（默认当前时间）。"""
        self._start_time = (start_time or time.monotonic()) - self.offset
        self._last_beat = -1
        self._running = True

    def stop(self):
        self._running = False
        self._start_time = None

    def resync(self, audio_position_seconds: float):
        """重新同步（音频seek后调用）。"""
        if self._running:
            self._start_time = time.monotonic() - audio_position_seconds - self.offset

    # ------------------------------------------------------------------
    # 每帧调用
    # ------------------------------------------------------------------

    def tick(self) -> list[BeatEvent]:
        """
        每帧调用，返回本帧触发的节拍事件列表。
        正常情况下每帧0个事件，节拍时1个事件。
        """
        if not self._running or self._start_time is None:
            return []

        elapsed = time.monotonic() - self._start_time
        current_beat = int(elapsed / self._spb)

        events = []
        while self._last_beat < current_beat:
            self._last_beat += 1
            evt = BeatEvent(
                beat_number=self._last_beat,
                timestamp=self._start_time + self._last_beat * self._spb,
                beat_fraction=0.0,
                measure=self._last_beat // self.time_signature,
                beat_in_measure=self._last_beat % self.time_signature,
            )
            events.append(evt)
            for sub in self._subscribers:
                sub(evt)

        return events

    # ------------------------------------------------------------------
    # 查询 API
    # ------------------------------------------------------------------

    def current_beat(self) -> tuple[float, float]:
        """
        返回 (beat_number, beat_fraction)。
        beat_number:  浮点拍号（如 4.5 = 第5拍的中间）
        beat_fraction: 当前拍内进度（0.0–1.0）
        """
        if not self._running or self._start_time is None:
            return 0.0, 0.0
        elapsed = time.monotonic() - self._start_time
        raw_beat = elapsed / self._spb
        beat_num = math.floor(raw_beat)
        beat_frac = raw_beat - beat_num
        return float(beat_num), beat_frac

    def beat_to_seconds(self, beat: float) -> float:
        """将拍号转换为从开始的秒数。"""
        return beat * self._spb + self.offset

    def seconds_to_beat(self, seconds: float) -> float:
        """将秒数转换为拍号。"""
        return (seconds - self.offset) / self._spb

    def elapsed_seconds(self) -> float:
        """已播放时间（秒）。"""
        if not self._running or self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def subscribe(self, callback: Callable[[BeatEvent], None]):
        """订阅节拍事件。callback(BeatEvent)"""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        if callback in self._subscribers:
            self._subscribers.remove(callback)
