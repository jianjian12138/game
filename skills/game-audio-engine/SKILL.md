---
name: game-audio-engine
description: |
  多通道音频与节拍同步引擎（Game Audio & Beat-Sync Engine）工程规范。
  专治音效实例爆发导致浏览器爆音卡顿、音游BPM漂移不同步、空间3D音效衰减失真等问题。
  涵盖多通道管理（AudioManager）、高精单调时钟节拍引擎（BeatSyncEngine）、
  2D空间立体声衰减（SpatialAudio）及固定容量音效对象池（AudioPool）。
---

# 多通道音频与节拍同步引擎工程规范

## 1. 核心架构

- **AudioManager (`core/audio/audio_manager.py`)**：
  BGM/SFX/Voice/UI 通道分流，提供静音、音量控制与跨端播放适配回调。
- **BeatSyncEngine (`core/audio/beat_sync_engine.py`)**：
  单调时钟（Monotonic clock）驱动，消除音视频微小漂移，提供每拍/每小节精准事件派发。
- **SpatialAudio (`core/audio/spatial_audio.py`)**：
  2D空间声源距离平方反比衰减与立体声（Stereo Panning）左右声道平滑计算。
- **AudioPool (`core/audio/audio_pool.py`)**：
  固定容量并发池，防止机关枪/弹幕音效重叠导致爆音与 GC 压力。
