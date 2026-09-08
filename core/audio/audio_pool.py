"""
Audio Pool — 音效对象池
========================
预分配音效播放槽位，防止同一音效重叠噪音和过多实例。
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class AudioSlot:
    """音效播放槽。"""
    slot_id: int
    asset: str = ""
    playing: bool = False
    start_time: float = 0.0
    duration: float = 0.0
    volume: float = 1.0


class AudioPool:
    """
    音效对象池：防止同一音效实例爆炸和重叠噪音。

    功能：
        - 同一音效在 cooldown 内不重复播放（防噪音）
        - 最多 max_instances 个相同音效同时播放
        - 槽满时自动抢占最早的槽

    用法::
        pool = AudioPool(max_instances=8)
        pool.play("sfx/hit.wav", volume=0.8, duration=0.3,
                  cooldown=0.05)   # 50ms内不重复
    """

    def __init__(self, max_instances: int = 8,
                 play_backend: Optional[Callable] = None):
        self.max_instances = max_instances
        self._slots = [AudioSlot(i) for i in range(max_instances)]
        self._last_play_times: dict[str, float] = {}
        self._play_backend = play_backend

    def play(
        self,
        asset: str,
        volume: float = 1.0,
        duration: float = 1.0,
        cooldown: float = 0.0,
        max_same: int = 3,       # 同一音效最多同时播放几个
    ) -> bool:
        """
        播放音效。返回是否成功播放（被冷却或槽满时返回False）。
        """
        now = time.monotonic()

        # 冷却检查
        last = self._last_play_times.get(asset, 0.0)
        if now - last < cooldown:
            return False

        # 同类音效实例数检查
        same_count = sum(1 for s in self._slots
                         if s.playing and s.asset == asset
                         and now - s.start_time < s.duration)
        if same_count >= max_same:
            return False

        # 找空槽
        slot = self._find_free_slot(now)
        if slot is None:
            return False

        # 占用槽
        slot.asset = asset
        slot.playing = True
        slot.start_time = now
        slot.duration = duration
        slot.volume = volume
        self._last_play_times[asset] = now

        if self._play_backend:
            self._play_backend(asset, volume)

        return True

    def update(self):
        """标记已完成播放的槽为空闲（每帧调用）。"""
        now = time.monotonic()
        for slot in self._slots:
            if slot.playing and now - slot.start_time >= slot.duration:
                slot.playing = False

    def active_count(self) -> int:
        return sum(1 for s in self._slots if s.playing)

    def _find_free_slot(self, now: float) -> Optional[AudioSlot]:
        """找到空闲槽；若无空槽则抢占最旧的槽。"""
        self.update()
        for s in self._slots:
            if not s.playing:
                return s
        # 抢占最旧
        return min(self._slots, key=lambda s: s.start_time)
