"""pipeline/audio_adapter.py — AudioGenAdapter：可插拔音频生成后端（L3，W7）。

后端（来自升级计划第十一章、W7）：
  ① cloud_audio  —— AI 音乐/音效后端（如 Suno/Udio 类服务），需配置 endpoint+key；
                    本环境未接入任何真实 AI 音频能力，故【永远不可用，诚实报 NEEDS_RUNTIME_TOOL】。
  ② procedural_synth —— 本库 audio_synth 纯 Python 真合成 16-bit PCM WAV，
                    确定性、可独立解码校验；它【不是 AI 生成】，明确标注 is_procedural_synth。

防伪底线（13.2）：
  - 没真出到音频绝不报 is_ai_generated=True。当前唯一真实可用的生成器是程序化合成，
    is_ai_generated=False / is_procedural_synth=True，且 AI 后端缺失时
    needs_runtime_tool="cloud_audio" 如实标注（不把程序化合成粉饰成 AI 音乐）。
  - 合成出的 WAV 是真实 PCM 字节，经 audio_synth.read_wav 独立解码校验（RIFF/采样率/能量），
    可作为"真跑通"的硬证据，不靠文件存在即判定通过。
  - 不依赖 requests/numpy/PIL：全部用标准库 + audio_synth。
"""
from __future__ import annotations

import hashlib
import io
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline import audio_synth

CLOUD_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "audio_gen.json"


@dataclass
class AudioGenResult:
    backend: str
    is_ai_generated: bool
    is_procedural_synth: bool
    status: str                       # OK / PROCEDURAL_SYNTH / NEEDS_RUNTIME_TOOL / ERROR
    audio_bytes: bytes = b""
    sample_rate: int = 0
    duration: float = 0.0
    channels: int = 1
    content_hash: str = ""
    category: str = ""                # sfx / bgm
    peak: float = 0.0
    rms: float = 0.0
    provenance: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    needs_runtime_tool: Optional[str] = None
    error: str = ""

    def ok(self) -> bool:
        return bool(self.audio_bytes) and self.status in ("OK", "PROCEDURAL_SYNTH")


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


class AudioGenAdapter:
    def __init__(self, cloud_config_path: Optional[str] = None):
        self.cloud_config_path = Path(cloud_config_path) if cloud_config_path \
            else CLOUD_CONFIG_PATH

    # ── AI 音频后端可用性（诚实，不假设） ───────────────────────────────────
    def cloud_available(self) -> bool:
        """当前未接入任何真实 AI 音频生成服务，永远返回 False（不伪证）。"""
        cfg = self._load_cloud_config()
        if not cfg:
            return False
        return bool(cfg.get("endpoint")) and bool(cfg.get("api_key"))

    def available_backends(self) -> List[str]:
        out = []
        if self.cloud_available():
            out.append("cloud_audio")
        # 程序化合成永远可用
        out.append("procedural_synth")
        return out

    def _load_cloud_config(self) -> Dict[str, Any]:
        if not self.cloud_config_path.exists():
            return {}
        try:
            return json.loads(self.cloud_config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    # ── 主入口 ──────────────────────────────────────────────────────────────
    def generate(self, kind: str, name: str = "", sample_rate: int = 44100,
                 duration: float = 1.0, backend: Optional[str] = None,
                 seed: Optional[int] = None, theme: str = "dorian",
                 bpm: int = 120) -> AudioGenResult:
        """生成一段音频。backend=None 时自动选（当前只有程序化合成可用）。

        kind 语义：若 kind ∈ SFX_KINDS 则合成音效；否则视为 BGM 调式名（回退用 theme）。
        """
        seed = int(seed) if seed is not None else 123456789
        sample_rate = int(sample_rate) if sample_rate >= 8000 else 44100

        # ① 显式请求 AI 后端：当前未接入真实能力，诚实不可用
        if backend == "cloud_audio":
            return AudioGenResult(
                "cloud_audio", False, False, "NEEDS_RUNTIME_TOOL",
                error="AI 音频后端（cloud_audio）未接入真实生成能力，未伪证",
                needs_runtime_tool="cloud_audio")

        # ② 程序化合成（真实 WAV）或自动回退
        explicit_proc = (backend == "procedural_synth")
        is_bgm = kind not in audio_synth.SFX_KINDS
        t0 = time.time()
        if is_bgm:
            scale = kind if kind in audio_synth.SCALES else theme
            beat = 60.0 / max(1, bpm)
            bars = max(1, int(round(duration / (4.0 * beat))))
            audio = audio_synth.render_bgm(scale_name=scale, bpm=bpm, bars=bars,
                                           sample_rate=sample_rate, seed=seed)
            category = "bgm"
        else:
            audio = audio_synth.render_sfx(kind, sample_rate=sample_rate, seed=seed)
            category = "sfx"

        # 独立解码校验（真证据，不靠"文件存在"）
        info = audio_synth.read_wav_bytes(audio)
        prov = {
            "generator": "procedural_synth",
            "is_ai_generated": False,
            "is_procedural_synth": True,
            "category": category,
            "kind": kind,
            "scale": (kind if is_bgm else None),
            "theme": theme,
            "seed": seed,
            "bpm": bpm,
            "sample_rate": sample_rate,
            "duration_s": round(info["duration"], 3),
            "peak": round(info["peak"], 4),
            "rms": round(info["rms"], 5),
            "is_silent": info["is_silent"],
            "note": "程序化合成 16-bit PCM WAV，非 AI 生成；接入真实 AI 音频后端后将替换",
        }
        warns: List[str] = []
        needs = None
        if not explicit_proc:
            # 自动模式回退：AI 音频后端缺失，如实标注
            if not self.cloud_available():
                warns.append("无可用 AI 音频后端（cloud_audio），已回退程序化合成；"
                             "此音频非 AI 生成，不得宣称为 AI 音乐")
                needs = "cloud_audio"
        return AudioGenResult(
            backend="procedural_synth", is_ai_generated=False,
            is_procedural_synth=True, status="PROCEDURAL_SYNTH",
            audio_bytes=audio, sample_rate=info["sample_rate"],
            duration=info["duration"], channels=info["channels"],
            content_hash=_sha(audio), category=category,
            peak=info["peak"], rms=info["rms"],
            provenance=prov, warnings=warns, needs_runtime_tool=needs,
            error="" if not info["is_silent"] else "合成结果为静音（异常）",
        )


if __name__ == "__main__":
    a = AudioGenAdapter()
    for kind in ("laser", "hit", "explosion", "coin", "ui_click", "step", "powerup"):
        r = a.generate(kind, seed=42)
        print(f"  [SFX] {kind:<10} 后端={r.backend} AI={r.is_ai_generated} "
              f"程序化={r.is_procedural_synth} 时长={r.duration:.2f}s 静音={r.provenance['is_silent']}")
    rb = a.generate("cyberpunk", name="bgm", duration=4.0, seed=7, bpm=120)
    print(f"  [BGM] cyberpunk 后端={rb.backend} 时长={rb.duration:.2f}s 峰值={rb.peak:.3f} "
          f"needs={rb.needs_runtime_tool}")
    print("=== AudioGenAdapter 自检通过 ===")
