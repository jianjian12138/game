"""
Audio Manager — 统一音频管理器
================================
分层管理 BGM / SFX / 语音，提供淡入淡出和音量控制。
注意：这是一个引擎无关的抽象层，具体播放由平台适配层实现。
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable


class AudioChannel(Enum):
    BGM   = "bgm"    # 背景音乐（同时只能播一首，自动淡入淡出）
    SFX   = "sfx"    # 音效（多实例，使用对象池）
    VOICE = "voice"  # 语音（可打断）
    UI    = "ui"     # UI音效（独立音量，不受游戏静音影响）


@dataclass
class AudioClip:
    """音频剪辑信息。"""
    asset_path: str
    channel: AudioChannel
    volume: float = 1.0
    loop: bool = False
    fade_in: float = 0.0    # 淡入时间（秒）
    fade_out: float = 0.0   # 淡出时间（秒）
    start_time: float = field(default_factory=time.monotonic)


class AudioManager:
    """
    统一音频管理器（引擎无关抽象层）。

    实际播放通过注册 backend_player 回调实现，
    适配 pygame / 微信小游戏 Web Audio / Phaser 等不同后端。

    用法::
        audio = AudioManager()

        # 注册后端播放器（平台适配）
        audio.set_backend(pygame_backend)

        # 播放
        audio.play_bgm("music/boss_theme.ogg", fade_in=1.0)
        audio.play_sfx("sfx/sword.wav")
        audio.stop_bgm(fade_out=2.0)

        # 音量控制
        audio.set_master_volume(0.8)
        audio.set_channel_volume(AudioChannel.SFX, 0.6)
    """

    def __init__(self):
        self._volumes: dict[AudioChannel, float] = {
            ch: 1.0 for ch in AudioChannel
        }
        self._master_volume: float = 1.0
        self._current_bgm: Optional[AudioClip] = None
        self._muted: bool = False

        # 后端播放回调 {channel: callable(clip)}
        self._backend: Optional[Callable] = None
        self._stop_backend: Optional[Callable] = None

        # 播放历史（用于调试）
        self._play_log: list[dict] = []

    # ------------------------------------------------------------------
    # 后端注册
    # ------------------------------------------------------------------

    def set_backend(self, play_fn: Callable, stop_fn: Callable = None):
        """
        注册平台播放后端。

        Args:
            play_fn:  play_fn(asset_path, volume, loop, fade_in) → handle
            stop_fn:  stop_fn(handle, fade_out)
        """
        self._backend = play_fn
        self._stop_backend = stop_fn

    # ------------------------------------------------------------------
    # 播放 API
    # ------------------------------------------------------------------

    def play_bgm(self, asset: str, volume: float = 1.0,
                 loop: bool = True, fade_in: float = 0.5):
        """播放背景音乐（自动停止当前BGM）。"""
        if self._current_bgm:
            self.stop_bgm(fade_out=0.3)

        clip = AudioClip(asset, AudioChannel.BGM, volume, loop, fade_in)
        self._current_bgm = clip
        self._emit(clip)
        print(f"[Audio] BGM: {asset} vol={volume:.1f}")

    def stop_bgm(self, fade_out: float = 0.5):
        """停止背景音乐（带淡出）。"""
        if self._current_bgm and self._stop_backend:
            self._stop_backend(self._current_bgm, fade_out)
        self._current_bgm = None

    def play_sfx(self, asset: str, volume: float = 1.0):
        """播放音效（多实例）。"""
        clip = AudioClip(asset, AudioChannel.SFX, volume)
        self._emit(clip)

    def play_voice(self, asset: str, volume: float = 1.0):
        """播放语音（打断当前语音）。"""
        clip = AudioClip(asset, AudioChannel.VOICE, volume)
        self._emit(clip)

    def play_ui(self, asset: str, volume: float = 0.8):
        """播放UI音效（不受静音影响）。"""
        clip = AudioClip(asset, AudioChannel.UI, volume)
        self._emit(clip)

    # ------------------------------------------------------------------
    # 音量控制
    # ------------------------------------------------------------------

    def set_master_volume(self, vol: float):
        self._master_volume = max(0.0, min(1.0, vol))

    def set_channel_volume(self, channel: AudioChannel, vol: float):
        self._volumes[channel] = max(0.0, min(1.0, vol))

    def get_effective_volume(self, channel: AudioChannel) -> float:
        if self._muted and channel != AudioChannel.UI:
            return 0.0
        return self._master_volume * self._volumes.get(channel, 1.0)

    def mute(self):
        self._muted = True

    def unmute(self):
        self._muted = False

    def toggle_mute(self):
        self._muted = not self._muted

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _emit(self, clip: AudioClip):
        """发送到后端播放器。"""
        effective_vol = clip.volume * self.get_effective_volume(clip.channel)
        self._play_log.append({
            "asset": clip.asset_path,
            "channel": clip.channel.value,
            "volume": effective_vol,
            "time": clip.start_time,
        })
        if self._backend:
            self._backend(clip.asset_path, effective_vol, clip.loop, clip.fade_in)
