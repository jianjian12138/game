"""
Spatial Audio — 3D空间音效
============================
基于距离和方向模拟3D空间音效，用于恐怖游戏环境音和竞速引擎音效。
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class AudioSource:
    """空间音源。"""
    source_id: str
    asset: str
    x: float
    y: float
    max_distance: float = 500.0     # 超出此距离完全听不见
    min_distance: float = 50.0      # 小于此距离为最大音量
    volume: float = 1.0
    loop: bool = False
    active: bool = True


class SpatialAudio:
    """
    2D空间音效计算器（可扩展到3D）。

    计算规则：
        - 距离 < min_distance: 原始音量
        - 距离 > max_distance: 静音
        - 中间: 对数衰减（符合人耳感知）

    用法::
        spatial = SpatialAudio()
        spatial.add_source(AudioSource("monster_growl", "sfx/growl.ogg",
                                        x=300, y=200, max_distance=400))

        # 每帧调用（listener为玩家位置）
        events = spatial.update(listener_x=100, listener_y=150)
        for evt in events:
            audio_manager.play_sfx(evt["asset"], volume=evt["volume"])
    """

    def __init__(self, play_backend: Optional[Callable] = None):
        self._sources: dict[str, AudioSource] = {}
        self._play_backend = play_backend

    def add_source(self, source: AudioSource):
        self._sources[source.source_id] = source

    def remove_source(self, source_id: str):
        self._sources.pop(source_id, None)

    def update_source_position(self, source_id: str, x: float, y: float):
        if source_id in self._sources:
            self._sources[source_id].x = x
            self._sources[source_id].y = y

    def update(self, listener_x: float, listener_y: float) -> list[dict]:
        """
        根据听者位置计算所有音源的有效音量和立体声方位。

        Returns:
            音频事件列表 [{"source_id", "asset", "volume", "pan", "distance"}]
        """
        events = []
        for sid, src in self._sources.items():
            if not src.active:
                continue

            dx = src.x - listener_x
            dy = src.y - listener_y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance >= src.max_distance:
                continue  # 超出范围，跳过

            # 音量衰减（对数曲线）
            if distance <= src.min_distance:
                vol = src.volume
            else:
                t = (distance - src.min_distance) / (src.max_distance - src.min_distance)
                vol = src.volume * (1.0 - t) ** 2   # 二次衰减

            # 立体声定位（-1.0=左，0=中，1.0=右）
            pan = max(-1.0, min(1.0, dx / src.max_distance))

            events.append({
                "source_id": sid,
                "asset": src.asset,
                "volume": vol,
                "pan": pan,
                "distance": distance,
            })

        return events

    def get_nearest_source(self, listener_x: float, listener_y: float,
                           asset_filter: str = None) -> Optional[AudioSource]:
        """返回距听者最近的活跃音源。"""
        nearest = None
        min_dist = float("inf")
        for src in self._sources.values():
            if not src.active:
                continue
            if asset_filter and asset_filter not in src.asset:
                continue
            d = math.sqrt((src.x - listener_x) ** 2 + (src.y - listener_y) ** 2)
            if d < min_dist:
                min_dist = d
                nearest = src
        return nearest
