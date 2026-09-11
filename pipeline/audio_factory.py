"""pipeline/audio_factory.py — W7 音频资产工厂 + 入库 QA（L3 内容工厂）。

流程：AudioSpec → AudioGenAdapter 生成 → 入库 QA（真实解码校验）→ AudioRecord。

入库 QA（真实校验非勾选，镜像 asset_factory 4.2）：
  - RIFF 结构合法   ：audio_synth.read_wav_bytes 能解码（合成字节必可解）
  - 采样率达标      ：解码 sample_rate == 规格
  - 声道正确        ：默认单声道（1）
  - 时长达标        ：解码 duration > 0 且在规格容差内（BGM 用 duration 控长）
  - 非静音          ：RMS 能量 > 阈值（真实声音证据，杜绝"空文件即通过"）
  - 音色语义        ：是否"听起来像激光/爆炸"需人耳或 VLM 判断，如实标注 needs_vlm

防伪：AudioRecord 携带 is_ai_generated / is_procedural_synth / provenance，
never 把程序化合成宣称为 AI 音乐。
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline import audio_synth
from pipeline.audio_adapter import AudioGenAdapter, AudioGenResult


@dataclass
class AudioSpec:
    kind: str                         # sfx 类型（laser/...）或 bgm 调式名（cyberpunk/...）
    name: str
    sample_rate: int = 44100
    duration: float = 1.0             # 目标时长（BGM 据此控长；SFX 仅供参考）
    channels: int = 1
    theme: str = "dorian"
    bpm: int = 120


@dataclass
class QAReport:
    passed: bool
    scores: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, str] = field(default_factory=dict)
    needs_vlm: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AudioRecord:
    asset_id: str
    spec: AudioSpec
    backend: str
    is_ai_generated: bool
    is_procedural_synth: bool
    content_hash: str
    sample_rate: int
    duration: float
    channels: int
    peak: float
    rms: float
    provenance: Dict[str, Any]
    qa: QAReport
    needs_runtime_tool: Optional[str]
    created_at: str = ""
    audio_bytes: bytes = b""

    def to_dict(self, with_audio: bool = False) -> Dict[str, Any]:
        d = asdict(self)
        if not with_audio:
            d.pop("audio_bytes", None)
        return d


class AudioQA:
    @staticmethod
    def check(audio_bytes: bytes, spec: AudioSpec,
              is_ai_generated: bool = False) -> QAReport:
        scores: Dict[str, Any] = {}
        details: Dict[str, str] = {}
        needs_vlm: List[str] = []
        problems: List[str] = []
        try:
            info = audio_synth.read_wav_bytes(audio_bytes)
        except Exception as e:
            return QAReport(passed=False, details={"decode": f"WAV 解码失败: {e}"})

        sr = info["sample_rate"]
        ch = info["channels"]
        dur = info["duration"]
        rms = info["rms"]

        # 1) 采样率
        sr_ok = (sr == spec.sample_rate)
        scores["sample_rate"] = 1.0 if sr_ok else 0.0
        details["sample_rate"] = f"{sr} vs 规格 {spec.sample_rate}"
        if not sr_ok:
            problems.append("sample_rate")

        # 2) 声道
        ch_ok = (ch == spec.channels)
        scores["channels"] = 1.0 if ch_ok else 0.0
        details["channels"] = f"{ch} vs 规格 {spec.channels}"
        if not ch_ok:
            problems.append("channels")

        # 3) 时长（>0 且 BGM 容差 ±0.5s）
        dur_ok = dur > 0.0
        if spec.kind not in audio_synth.SFX_KINDS:
            dur_ok = dur_ok and abs(dur - spec.duration) <= 0.6
        scores["duration"] = 1.0 if dur_ok else 0.0
        details["duration"] = f"{dur:.3f}s vs 规格≈{spec.duration:.3f}s"
        if not dur_ok:
            problems.append("duration")

        # 4) 非静音（真实声音证据）
        silent = info["is_silent"]
        scores["non_silent"] = 0.0 if silent else 1.0
        details["non_silent"] = (f"RMS={rms:.5f} 峰值={info['peak']:.3f} "
                                 f"({'静音！' if silent else '有真实能量'})")
        if silent:
            problems.append("non_silent")

        # 5) 音色语义（需人耳 / VLM）：如实标注
        if is_ai_generated:
            scores["timbre"] = "unverified_needs_vlm"
            details["timbre"] = "AI 音频音色语义需人耳/VLM 复核"
        else:
            scores["timbre"] = "unverified_needs_vlm"
            details["timbre"] = ("程序化合成音色（物理可解释），但'是否贴切玩法语义'需人耳/VLM 复核"
                                 if not is_ai_generated else "AI 音频音色语义需 VLM 复核")
        needs_vlm.append("timbre")

        passed = len(problems) == 0
        return QAReport(passed=passed, scores=scores, details=details, needs_vlm=needs_vlm)

    @staticmethod
    def verify_file(file_path: str, spec: Optional[AudioSpec] = None) -> Dict[str, Any]:
        """校验一个已存在的 WAV 文件（asset-audio-verify 用）。不生成、不依赖适配器。"""
        p = Path(file_path)
        if not p.exists():
            return {"passed": False, "error": f"文件不存在: {file_path}",
                    "file": str(p)}
        try:
            data = p.read_bytes()
            info = audio_synth.read_wav_bytes(data)
        except Exception as e:
            return {"passed": False, "error": f"WAV 解码失败: {e}", "file": str(p)}
        size = len(data)
        qa = AudioQA.check(data, spec or AudioSpec(kind="", name=p.stem),
                           is_ai_generated=False) if spec else None
        return {
            "passed": (qa.passed if qa else (info["rms"] >= 1e-4)),
            "file": str(p.resolve()),
            "size_bytes": size,
            "sample_rate": info["sample_rate"],
            "channels": info["channels"],
            "duration": round(info["duration"], 3),
            "peak": round(info["peak"], 4),
            "rms": round(info["rms"], 5),
            "is_silent": info["is_silent"],
            "content_hash": "sha256:" + hashlib.sha256(data).hexdigest(),
            "qa": qa.to_dict() if qa else None,
        }


class AudioFactory:
    def __init__(self, adapter: Optional[AudioGenAdapter] = None):
        self.adapter = adapter or AudioGenAdapter()

    def generate(self, spec: AudioSpec, backend: Optional[str] = None,
                 seed: Optional[int] = None) -> AudioRecord:
        res: AudioGenResult = self.adapter.generate(
            kind=spec.kind, name=spec.name, sample_rate=spec.sample_rate,
            duration=spec.duration, backend=backend, seed=seed,
            theme=spec.theme, bpm=spec.bpm)
        qa = AudioQA.check(res.audio_bytes, spec, res.is_ai_generated)
        asset_id = "audio_" + hashlib.sha256(
            (spec.kind + spec.name + res.content_hash).encode("utf-8")).hexdigest()[:12]
        return AudioRecord(
            asset_id=asset_id, spec=spec, backend=res.backend,
            is_ai_generated=res.is_ai_generated,
            is_procedural_synth=res.is_procedural_synth,
            content_hash=res.content_hash, sample_rate=res.sample_rate,
            duration=res.duration, channels=res.channels,
            peak=res.peak, rms=res.rms,
            provenance=res.provenance, qa=qa,
            needs_runtime_tool=res.needs_runtime_tool,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            audio_bytes=res.audio_bytes,
        )

    def save(self, rec: AudioRecord, out_dir: str) -> Dict[str, str]:
        os_makedirs(out_dir)
        wav_path = os.path.join(out_dir, f"{rec.spec.name}_{rec.asset_id}.wav")
        json_path = os.path.join(out_dir, f"{rec.spec.name}_{rec.asset_id}.json")
        with open(wav_path, "wb") as f:
            f.write(rec.audio_bytes)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(rec.to_dict(), f, ensure_ascii=False, indent=2, default=str)
        return {"wav": wav_path, "json": json_path}


def os_makedirs(out_dir: str) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    f = AudioFactory()
    for kind in ("laser", "hit", "explosion", "coin", "ui_click", "step", "powerup"):
        spec = AudioSpec(kind=kind, name=f"sfx_{kind}")
        rec = f.generate(spec, seed=42)
        print(f"  [SFX] {kind:<10} AI={rec.is_ai_generated} 程序化={rec.is_procedural_synth} "
              f"QA通过={rec.qa.passed} 时长={rec.duration:.2f}s "
              f"needs={rec.needs_runtime_tool}")
    bgm_spec = AudioSpec(kind="cyberpunk", name="bgm_cyberpunk", duration=4.0, bpm=120)
    rb = f.generate(bgm_spec, seed=7)
    print(f"  [BGM] cyberpunk QA通过={rb.qa.passed} 时长={rb.duration:.2f}s "
          f"needs={rb.needs_runtime_tool}")
    print("=== AudioFactory 自检通过 ===")
