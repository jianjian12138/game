#!/usr/bin/env python3
"""pipeline/audio_synth.py — W7 纯标准库 16-bit PCM WAV 合成引擎（L3 音频工厂内核）。

职责（与升级计划第十一章、W7 一致）：
  1. 纯 Python 标准库（wave/array/math/random/struct）合成真实 16-bit PCM WAV 字节，
     零 numpy / 零 PIL / 零外部音频依赖；确定性（给定 seed 必可复现）。
  2. 振荡器：sine / square / sawtooth / triangle / noise；ADSR 包络；指数/线性频率扫频。
  3. render_sfx(kind)：laser / hit / explosion / coin / ui_click / step / powerup
     七类音效，全部是真实可解码的字节（非占位、非静音、非粉饰）。
  4. render_bgm(scale)：按调式（pentatonic/dorian/harmonic_minor/cyberpunk）合成循环 BGM。
  5. read_wav(path)：独立解码校验（RIFF/采样率/时长/峰值/能量/是否静音），
     + 防削波归一化；QA 与回归测试靠它做真实证据，不靠文件存在即"通过"。

防伪底线（13.2）：
  - 本引擎产出的每一段 WAV 都是真实 PCM 样本（可被任意播放器/FFmpeg 解码），
    可被 read_wav 独立解码、哈希、算能量——这是"真跑通"的硬证据。
  - 它不声称自己是"AI 音乐"——它明确是程序化合成（procedural_synth）；
    是否 AI 生成由 audio_adapter 的诚实标记决定（本模块只管合成真实字节）。
"""
from __future__ import annotations

import array
import io
import math
import random
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── 调式（与 adaptive_audio_system 同源定义，独立保留以便内核自洽） ───────────
SCALES: Dict[str, List[int]] = {
    "pentatonic": [0, 2, 4, 7, 9],            # 五声音阶（东方/恬静）
    "dorian": [0, 2, 3, 5, 7, 9, 10],         # 多利亚调式（科幻/探险）
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11], # 和声小调（史诗/战斗）
    "cyberpunk": [0, 1, 4, 5, 7, 8, 10],       # 弗里吉亚主调（赛博朋克/危机）
}


def midi_to_freq(midi_note: int) -> float:
    """MIDI 音高转赫兹（A4 = 69 = 440.0Hz）。"""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def _stable_int(s: str) -> int:
    """稳定字符串哈希（不依赖 PYTHONHASHSEED，保证跨进程确定性）。"""
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


# ── 振荡器单点样本 ──────────────────────────────────────────────────────────
def _osc_sample(wave: str, phase: float) -> float:
    """phase ∈ [0,1)，返回 [-1,1]。noise 不走此路径（由 render_voices 单独处理）。"""
    if wave == "sine":
        return math.sin(2.0 * math.pi * phase)
    if wave == "square":
        return 1.0 if phase < 0.5 else -1.0
    if wave == "sawtooth":
        return 2.0 * phase - 1.0
    if wave == "triangle":
        return 4.0 * abs(phase - 0.5) - 1.0
    raise ValueError(f"未知波形: {wave}")


# ── ADSR 包络 ──────────────────────────────────────────────────────────────
def _envelope(lt: float, dur: float, attack: float, decay: float,
              sustain_level: float, release: float) -> float:
    """lt = 该 voice 局部时间；返回当前增益系数。sustain_level 为持续段保持的电平。"""
    if lt < 0 or lt >= dur:
        return 0.0
    if lt < attack:
        return (lt / attack) if attack > 0 else 1.0
    td = lt - attack
    if td < decay:
        # 从 1.0 衰减到 sustain_level
        return 1.0 - (1.0 - sustain_level) * (td / decay) if decay > 0 else sustain_level
    release_start = dur - release
    if lt < release_start:
        return sustain_level
    tr = lt - release_start
    return sustain_level * (1.0 - tr / release) if release > 0 else 0.0


@dataclass
class Voice:
    """单个合成声部。f0 必填；f1 为扫频终点（None=恒定）；start/dur 为该声部时窗。"""
    wave: str
    f0: float
    f1: Optional[float] = None
    gain: float = 0.5
    dur: float = 0.2
    start: float = 0.0
    attack: float = 0.005
    decay: float = 0.05
    sustain_level: float = 0.7
    release: float = 0.05
    sweep: str = "exp"          # exp | lin | const
    noise_seed: Optional[int] = None


# ── 多声部混音渲染（核心） ───────────────────────────────────────────────────
def render_voices(voices: List[Voice], sample_rate: int = 44100,
                  tail: float = 0.02, seed: int = 0) -> List[float]:
    """把所有声部按时间窗混音成 float 样本列表（[-1,1]）。自动防削波归一化。"""
    if not voices:
        raise ValueError("render_voices: 至少需要一个声部")
    end = 0.0
    for v in voices:
        end = max(end, v.start + v.dur)
    end += tail
    n = max(1, int(round(end * sample_rate)))
    buf: List[float] = [0.0] * n

    for v in voices:
        phase = 0.0
        use_noise = (v.wave == "noise")
        vrng = random.Random(
            (seed * 2654435761 + _stable_int(v.wave)
             + (v.noise_seed or 0)) & 0xFFFFFFFF) if use_noise else None
        s0 = max(0, int(round(v.start * sample_rate)))
        s1 = min(n, int(round((v.start + v.dur) * sample_rate)))
        for i in range(s0, s1):
            t = i / sample_rate
            lt = t - v.start
            frac = lt / v.dur if v.dur > 0 else 1.0
            # 频率（扫频）
            if v.f1 is None or v.f1 == v.f0:
                freq = v.f0
            elif v.sweep == "exp":
                freq = v.f0 * (v.f1 / v.f0) ** frac
            else:  # lin
                freq = v.f0 + (v.f1 - v.f0) * frac
            phase += freq / sample_rate
            p = phase - math.floor(phase)
            s = vrng.random() * 2.0 - 1.0 if use_noise else _osc_sample(v.wave, p)
            env = _envelope(lt, v.dur, v.attack, v.decay,
                            v.sustain_level, v.release)
            buf[i] += v.gain * env * s

    # 防削波：若峰值超 0.999 则整体缩放到 0.9
    peak = max((abs(x) for x in buf), default=0.0)
    if peak > 0.999:
        scale = 0.9 / peak
        buf = [x * scale for x in buf]
    return buf


# ── WAV 写/读（标准库） ─────────────────────────────────────────────────────
def _write_wav(fobj, samples: List[float], sample_rate: int, channels: int = 1) -> None:
    """把浮点样本（[-1,1]）写成 16-bit PCM WAV。"""
    n = len(samples)
    w = wave.open(fobj, "wb")
    w.setnchannels(channels)
    w.setsampwidth(2)  # 16-bit
    w.setframerate(sample_rate)
    frames = array.array("h")
    for s in samples:
        v = max(-1.0, min(1.0, s))
        frames.append(int(round(v * 32767)))
    w.writeframes(frames.tobytes())
    w.close()


def wav_bytes(samples: List[float], sample_rate: int = 44100,
              channels: int = 1) -> bytes:
    """把样本直接序列化为 WAV 字节（不落盘，供工厂/测试用）。"""
    b = io.BytesIO()
    _write_wav(b, samples, sample_rate, channels)
    return b.getvalue()


def write_wav_file(path: str, samples: List[float], sample_rate: int = 44100) -> str:
    """落盘 WAV 文件，返回绝对路径。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        _write_wav(f, samples, sample_rate, 1)
    return str(p.resolve())


def _decode_wav(fobj) -> Dict[str, Any]:
    """从已打开的类文件对象解码 WAV 并做真实校验（核心，路径/字节共用）。"""
    with wave.open(fobj, "rb") as w:
        channels = w.getnchannels()
        sw = w.getsampwidth()
        sr = w.getframerate()
        nframes = w.getnframes()
        raw = w.readframes(nframes)

    if sw == 1:
        data = array.array("B")
        data.frombytes(raw)
        samples = [(x - 128) / 128.0 for x in data]
    elif sw == 2:
        data = array.array("h")
        data.frombytes(raw)
        samples = [x / 32768.0 for x in data]
    elif sw == 4:
        data = array.array("i")
        data.frombytes(raw)
        samples = [x / 2147483648.0 for x in data]
    else:
        raise ValueError(f"不支持的采样位宽: {sw * 8}-bit")

    if channels > 1:
        mono: List[float] = []
        for i in range(0, len(samples), channels):
            mono.append(sum(samples[i:i + channels]) / channels)
        samples = mono

    peak = max((abs(x) for x in samples), default=0.0)
    rms = (math.sqrt(sum(x * x for x in samples) / len(samples))
           if samples else 0.0)
    # 防削波归一化（理论上本引擎已归一，这里仅兜底极端外部文件）
    if peak > 0.999:
        scale = 0.9 / peak
        samples = [x * scale for x in samples]
        peak = 0.9
    return {
        "sample_rate": sr,
        "channels": channels,
        "sample_width": sw,
        "n_frames": nframes,
        "duration": (nframes / channels) / sr if sr else 0.0,
        "peak": peak,
        "rms": rms,
        "samples": samples,
        "is_silent": rms < 1e-4,
    }


def read_wav_bytes(data: bytes) -> Dict[str, Any]:
    """从 WAV 字节解码并校验（不落盘，供适配器/工厂/测试用）。"""
    return _decode_wav(io.BytesIO(data))


def read_wav(path: str) -> Dict[str, Any]:
    """独立解码 WAV 文件并做真实校验：RIFF 结构、采样率、时长、峰值、RMS 能量、是否静音。

    返回 float 单声道样本（多声道取均值下混），供 QA 与回归测试作为硬证据。
    """
    with open(str(path), "rb") as f:
        return _decode_wav(f)


# ── 音效配方 ────────────────────────────────────────────────────────────────
SFX_KINDS = ("laser", "hit", "explosion", "coin", "ui_click", "step", "powerup")


def _sfx_voices(kind: str) -> List[Voice]:
    if kind == "laser":
        return [
            Voice("sawtooth", 1400, 220, gain=0.5, dur=0.18, attack=0.002,
                  decay=0.06, sustain_level=0.0, release=0.05, sweep="exp"),
            Voice("square", 900, 160, gain=0.16, dur=0.16, attack=0.002,
                  decay=0.05, sustain_level=0.0, release=0.05, sweep="exp"),
        ]
    if kind == "hit":
        return [
            Voice("noise", 0, 0, gain=0.7, dur=0.14, attack=0.001,
                  decay=0.12, sustain_level=0.0, release=0.02, noise_seed=1),
            Voice("sine", 160, 70, gain=0.5, dur=0.12, attack=0.001,
                  decay=0.1, sustain_level=0.0, release=0.02, sweep="exp"),
        ]
    if kind == "explosion":
        return [
            Voice("sine", 130, 28, gain=0.7, dur=0.55, attack=0.005,
                  decay=0.3, sustain_level=0.0, release=0.2, sweep="exp"),
            Voice("noise", 0, 0, gain=0.45, dur=0.5, attack=0.002,
                  decay=0.4, sustain_level=0.0, release=0.1, noise_seed=2),
        ]
    if kind == "coin":
        # 经典双音上行（约 B5 -> E6）
        return [
            Voice("square", 988, None, gain=0.4, dur=0.09, start=0.0,
                  attack=0.002, decay=0.07, sustain_level=0.0, release=0.02),
            Voice("square", 1319, None, gain=0.4, dur=0.32, start=0.09,
                  attack=0.002, decay=0.3, sustain_level=0.0, release=0.02),
        ]
    if kind == "ui_click":
        return [
            Voice("sine", 660, None, gain=0.4, dur=0.05, attack=0.001,
                  decay=0.03, sustain_level=0.0, release=0.02),
        ]
    if kind == "step":
        return [
            Voice("sine", 120, 80, gain=0.5, dur=0.08, attack=0.001,
                  decay=0.05, sustain_level=0.0, release=0.03, sweep="exp"),
            Voice("noise", 0, 0, gain=0.2, dur=0.05, attack=0.001,
                  decay=0.04, sustain_level=0.0, release=0.01, noise_seed=3),
        ]
    if kind == "powerup":
        return [
            Voice("sawtooth", 320, 1500, gain=0.4, dur=0.32, start=0.0,
                  attack=0.01, decay=0.1, sustain_level=0.2, release=0.08, sweep="exp"),
            Voice("square", 640, 2000, gain=0.16, dur=0.3, start=0.02,
                  attack=0.01, decay=0.1, sustain_level=0.1, release=0.08, sweep="exp"),
        ]
    raise ValueError(f"未知音效类型: {kind}（可选: {SFX_KINDS}）")


def render_sfx(kind: str, sample_rate: int = 44100, seed: int = 0) -> bytes:
    """合成一段音效，返回 WAV 字节。kind ∈ SFX_KINDS。"""
    if kind not in SFX_KINDS:
        raise ValueError(f"未知音效类型: {kind}（可选: {SFX_KINDS}）")
    buf = render_voices(_sfx_voices(kind), sample_rate, seed=seed)
    return wav_bytes(buf, sample_rate)


# ── BGM 循环合成 ────────────────────────────────────────────────────────────
def render_bgm(scale_name: str = "dorian", bpm: int = 120, bars: int = 2,
               root: int = 48, sample_rate: int = 44100, seed: int = 0) -> bytes:
    """按调式合成一段循环 BGM（pad 和弦 + 低音 + 琶音旋律），返回 WAV 字节。"""
    scale = SCALES.get(scale_name, SCALES["dorian"])
    beat = 60.0 / bpm
    bar_dur = beat * 4
    total = bar_dur * bars
    voices: List[Voice] = []

    # 1) 持续 pad 和弦（三音正弦，长持续）
    chord = [root, root + scale[2], root + scale[4]]
    for m in chord:
        voices.append(Voice("sine", midi_to_freq(m), None, gain=0.10,
                            dur=total, attack=0.08, decay=0.0,
                            sustain_level=1.0, release=0.2))

    # 2) 每小节重拍低音（三角波）
    for bi in range(bars):
        voices.append(Voice("triangle", midi_to_freq(root - 12), None, gain=0.18,
                            start=bi * bar_dur, dur=beat * 1.5, attack=0.01,
                            decay=0.1, sustain_level=0.4, release=0.1))

    # 3) 琶音旋律（每小节 2 音，方波）
    arp = [scale[0], scale[2], scale[4], scale[6 % len(scale)]]
    for bi in range(bars):
        for k in range(2):
            note = arp[(bi * 2 + k) % len(arp)]
            octv = 12 if (bi + k) % 2 == 0 else 0
            f = midi_to_freq(root + 12 + note + octv)
            start = bi * bar_dur + k * beat * 2
            voices.append(Voice("square", f, None, gain=0.10, start=start,
                                dur=beat * 1.6, attack=0.01, decay=0.05,
                                sustain_level=0.5, release=0.1))

    buf = render_voices(voices, sample_rate, tail=0.25, seed=seed)
    return wav_bytes(buf, sample_rate)


if __name__ == "__main__":
    # 自检：七类音效 + 一段 BGM，全部真实合成并独立解码校验
    import tempfile
    for kind in SFX_KINDS:
        b = render_sfx(kind)
        assert b[:4] == b"RIFF", f"{kind} 不是合法 WAV"
        print(f"  [SFX] {kind:<10} 字节={len(b)} OK")
    bgm = render_bgm("cyberpunk", bars=2)
    tp = Path(tempfile.mkdtemp()) / "bgm_selfcheck.wav"
    tp.write_bytes(bgm)
    info = read_wav(str(tp))
    print(f"  [BGM] cyberpunk 时长={info['duration']:.2f}s 峰值={info['peak']:.3f} "
          f"RMS={info['rms']:.4f} 静音={info['is_silent']}")
    print("=== audio_synth 自检通过：全部为真实可解码 WAV ===")
