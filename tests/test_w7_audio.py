"""tests/test_w7_audio.py — W7 音频工厂（真实合成 + 诚实防粉饰）。

防伪核心（与 B/C 类、W5/W6 一致）：
  - 每一段音频都是 audio_synth 真实合成的 16-bit PCM WAV 字节，可独立解码/哈希/算能量。
    不靠"文件存在"即判定通过——必须 read_wav 解出非静音、采样率、时长等真实证据。
  - 本环境无真实 AI 音频后端，唯一真实生成器是程序化合成（procedural_synth）；
    绝不把程序化合成标为 is_ai_generated=True；cloud_audio 不可用诚实报 NEEDS_RUNTIME_TOOL。
  - 音色语义（是否"听起来像激光"）需人耳/VLM，如实标注 needs_vlm，不假装自动判过。
  - 默认单测不依赖网络、不依赖 ComfyUI/Godot、不依赖 PIL/numpy（纯标准库）。
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from pipeline import audio_synth
from pipeline.audio_adapter import AudioGenAdapter, AudioGenResult
from pipeline.audio_factory import AudioFactory, AudioQA, AudioSpec

SFX_KINDS = audio_synth.SFX_KINDS


class TestAudioSynthEngine(unittest.TestCase):
    """合成内核必须产出真实可解码、非静音、不削波、确定性的 WAV。"""

    def test_all_seven_sfx_render_valid_wav(self):
        for kind in SFX_KINDS:
            b = audio_synth.render_sfx(kind)
            self.assertTrue(b[:4] == b"RIFF", f"{kind} 不是合法 RIFF/WAV")
            info = audio_synth.read_wav_bytes(b)
            self.assertFalse(info["is_silent"], f"{kind} 静音（假音频）")
            self.assertEqual(info["sample_rate"], 44100)
            self.assertGreater(info["duration"], 0.0)
            self.assertLessEqual(info["peak"], 1.0, f"{kind} 削波")

    def test_bgm_render_valid_and_non_silent(self):
        b = audio_synth.render_bgm("cyberpunk", bars=2, bpm=120)
        info = audio_synth.read_wav_bytes(b)
        self.assertFalse(info["is_silent"], "BGM 静音（假音频）")
        # 2 小节 @120bpm ≈ 4.0s，容差内
        self.assertAlmostEqual(info["duration"], 4.0, delta=0.6)
        self.assertLessEqual(info["peak"], 1.0)

    def test_synthesis_is_deterministic(self):
        # 同 seed 必可复现（即使是无噪声的音效也成立）
        b1 = audio_synth.render_sfx("laser", seed=123)
        b2 = audio_synth.render_sfx("laser", seed=123)
        self.assertEqual(hashlib.sha256(b1).hexdigest(),
                         hashlib.sha256(b2).hexdigest(),
                         "同 seed 必须确定性可复现")
        # 含噪声的音效（hit）不同 seed 应可区分（噪声随机性受 seed 控制）
        h1 = audio_synth.render_sfx("hit", seed=123)
        h2 = audio_synth.render_sfx("hit", seed=999)
        self.assertNotEqual(hashlib.sha256(h1).hexdigest(),
                            hashlib.sha256(h2).hexdigest(),
                            "含噪声音效不同 seed 应可区分")

    def test_read_wav_roundtrip_matches(self):
        b = audio_synth.render_sfx("coin", seed=5)
        info = audio_synth.read_wav_bytes(b)
        self.assertEqual(info["sample_rate"], 44100)
        self.assertEqual(info["channels"], 1)
        self.assertGreater(len(info["samples"]), 100)

    def test_supported_scales_render(self):
        for sc in ("pentatonic", "dorian", "harmonic_minor", "cyberpunk"):
            b = audio_synth.render_bgm(sc, bars=1, bpm=120)
            info = audio_synth.read_wav_bytes(b)
            self.assertFalse(info["is_silent"], f"{sc} BGM 静音")


class TestAudioAdapterHonesty(unittest.TestCase):
    """适配器诚实底线：程序化合成明确非 AI；AI 后端缺失诚实报 NEEDS_RUNTIME_TOOL。"""

    def test_procedural_synth_is_real_and_not_ai(self):
        a = AudioGenAdapter()
        r = a.generate("laser", seed=42)
        self.assertIsInstance(r, AudioGenResult)
        self.assertTrue(r.ok())
        self.assertFalse(r.is_ai_generated, "程序化合成不得伪装成 AI")
        self.assertTrue(r.is_procedural_synth)
        self.assertEqual(r.status, "PROCEDURAL_SYNTH")
        self.assertTrue(r.audio_bytes[:4] == b"RIFF")
        info = audio_synth.read_wav_bytes(r.audio_bytes)
        self.assertFalse(info["is_silent"])

    def test_cloud_audio_backend_unavailable_honest(self):
        a = AudioGenAdapter()
        r = a.generate("laser", backend="cloud_audio")
        self.assertEqual(r.status, "NEEDS_RUNTIME_TOOL")
        self.assertEqual(r.needs_runtime_tool, "cloud_audio")
        self.assertFalse(r.ok(), "不可用后端绝不能产出假音频")
        self.assertFalse(r.audio_bytes, "未出图不得有字节")

    def test_auto_fallback_marks_missing_ai_backend(self):
        a = AudioGenAdapter()
        r = a.generate("explosion", seed=1)  # auto：当前只有程序化合成
        self.assertTrue(r.is_procedural_synth)
        # 无真实 AI 音频后端，必须诚实标注缺失
        self.assertEqual(r.needs_runtime_tool, "cloud_audio")
        self.assertIn("非 AI 生成", r.provenance.get("note", ""))

    def test_bgm_duration_controlled_by_param(self):
        a = AudioGenAdapter()
        r = a.generate("dorian", duration=2.0, bpm=120, seed=3)
        self.assertEqual(r.category, "bgm")
        self.assertAlmostEqual(r.duration, 2.0, delta=0.6)


class TestAudioFactoryQA(unittest.TestCase):
    """工厂：生成 + 入库 QA + 落盘 + 独立校验。"""

    def setUp(self):
        self.factory = AudioFactory()

    def test_sfx_generate_qa_passes(self):
        for kind in SFX_KINDS:
            spec = AudioSpec(kind=kind, name=f"sfx_{kind}")
            rec = self.factory.generate(spec, seed=42)
            self.assertTrue(rec.qa.passed, f"{kind} QA 未通过: {rec.qa.details}")
            self.assertTrue(rec.is_procedural_synth)
            self.assertFalse(rec.is_ai_generated)
            self.assertIn("timbre", rec.qa.needs_vlm, "音色语义必须如实标 needs_vlm")

    def test_bgm_generate_qa_passes(self):
        spec = AudioSpec(kind="cyberpunk", name="bgm_cyberpunk",
                         duration=4.0, bpm=120)
        rec = self.factory.generate(spec, seed=7)
        self.assertTrue(rec.qa.passed, rec.qa.details)
        self.assertAlmostEqual(rec.duration, 4.0, delta=0.6)

    def test_save_writes_wav_and_json(self):
        spec = AudioSpec(kind="hit", name="sfx_hit")
        rec = self.factory.generate(spec, seed=11)
        out = tempfile.mkdtemp()
        saved = self.factory.save(rec, out)
        self.assertTrue(Path(saved["wav"]).exists(), "WAV 未落盘")
        self.assertTrue(Path(saved["json"]).exists(), "JSON 未落盘")
        data = Path(saved["wav"]).read_bytes()
        self.assertTrue(data[:4] == b"RIFF")
        js = json.loads(Path(saved["json"]).read_text(encoding="utf-8"))
        self.assertEqual(js["is_ai_generated"], False)
        self.assertEqual(js["is_procedural_synth"], True)

    def test_verify_file_on_real_output(self):
        spec = AudioSpec(kind="ui_click", name="sfx_ui_click")
        rec = self.factory.generate(spec, seed=8)
        out = tempfile.mkdtemp()
        saved = self.factory.save(rec, out)
        rep = AudioQA.verify_file(saved["wav"], spec)
        self.assertTrue(rep["passed"], rep)
        self.assertFalse(rep["is_silent"])
        # 真文件哈希与 JSON 内 content_hash 一致（真证据链）
        js = json.loads(Path(saved["json"]).read_text(encoding="utf-8"))
        self.assertEqual(rep["content_hash"], js["content_hash"])


@unittest.skipUnless(os.environ.get("W7_REAL_AUDIO") == "1",
                     "需真实落盘+解码回环（env W7_REAL_AUDIO=1）")
class TestW7RealAudio(unittest.TestCase):
    """W7 真实证据：生成 -> 落盘 -> 独立解码 -> 哈希对账，全链路闭环。"""

    def test_full_pipeline_real_files(self):
        f = AudioFactory()
        out = tempfile.mkdtemp()
        for kind in ("laser", "coin", "explosion", "powerup"):
            spec = AudioSpec(kind=kind, name=f"sfx_{kind}")
            rec = f.generate(spec, seed=2024)
            saved = f.save(rec, out)
            wav = Path(saved["wav"])
            self.assertGreater(wav.stat().st_size, 44, f"{kind} WAV 过小（假文件）")
            # 独立解码真实文件（不依赖工厂内部状态）
            info = audio_synth.read_wav(str(wav))
            self.assertFalse(info["is_silent"], f"{kind} 真文件静音")
            self.assertEqual(info["sample_rate"], 44100)
            # 真文件哈希 == provenance content_hash
            real_hash = "sha256:" + hashlib.sha256(wav.read_bytes()).hexdigest()
            self.assertEqual(real_hash, rec.content_hash,
                             f"{kind} 文件哈希与 provenance 不符（粉饰风险）")


if __name__ == "__main__":
    unittest.main(verbosity=2)
