"""
Audio System — 游戏音频引擎封装
=================================
统一管理 BGM/SFX/语音，提供节拍同步和3D空间音。

用法::
    from core.audio import AudioManager, BeatSyncEngine

    audio = AudioManager()
    audio.play_bgm("music/boss_theme.ogg", volume=0.8)
    audio.play_sfx("sfx/sword_clash.wav", volume=1.0)

    # 节奏游戏
    sync = BeatSyncEngine(bpm=138, offset=0.05)
    sync.start()
    beat_num, beat_frac = sync.current_beat()
"""

from .audio_manager import AudioManager, AudioChannel
from .beat_sync_engine import BeatSyncEngine, BeatEvent
from .spatial_audio import SpatialAudio, AudioSource
from .audio_pool import AudioPool

__all__ = [
    "AudioManager", "AudioChannel",
    "BeatSyncEngine", "BeatEvent",
    "SpatialAudio", "AudioSource",
    "AudioPool",
]
