"""pipeline/vertical_slice_validator.py — W9 八垂直切片端到端验证编排（真实证据，诚实门禁）。

编排每个切片走完整链路：
  ① slice_prototyper 生成 contract-bearing 可玩 index.html（确定性）；
  ② 用 W7 AudioFactory 真实合成该切片的程序化音频（sfx_*.wav / bgm.wav），落盘到同目录
     —— 这是「已落地的 honest 适配器」接入切片的真实证据，不伪造 AI 音乐；
  ③ 用 W8 PlaytestEngine 在真实浏览器里跑自动试玩闭环，采集 boot/playing/帧数/game_over/restart
     /未捕获异常 的真实证据，聚合诚实 verdict；
  ④ 汇总成 vertical_slices_report.json（每片 status + maturity + 证据路径 + 真实断言）。

防伪红线（13.2）：
  - 无真实浏览器驱动 → 该片 status=NEEDS_RUNTIME_TOOL，绝不把「HTML 存在」粉饰成通过；
  - 即使生成了 HTML，也只有真实浏览器跑通 boot+主循环才记 PASS；
  - game_over/restart 支持与否，由游戏是否真暴露 endMatch/restartMatch 决定，如实标注，
    绝不假装「死亡→重开」闭合。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.runtime_adapter import RuntimeStatus
from pipeline import playtest_engine as pe
from pipeline.slice_prototyper import generate_slice
from pipeline.vertical_slices import VERTICAL_SLICES, SliceSpec

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class SliceValidationResult:
    slice_id: str
    name: str
    genre: str
    status: str = RuntimeStatus.FAIL
    maturity_target: int = 2
    maturity_achieved: int = 0
    playtest_status: str = ""
    episodes_reached_playing: int = 0
    total_frames: int = 0
    game_over_supported: bool = False
    restart_supported: bool = False
    page_error_count: int = 0
    # 防伪真实验证计数（画面真渲染 / 输入真响应）
    pixel_rendered_count: int = 0
    input_reflected_count: int = 0
    assets: Dict[str, Any] = field(default_factory=dict)
    needs_runtime_tool: Optional[str] = None
    evidence_path: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slice_id": self.slice_id, "name": self.name, "genre": self.genre,
            "status": self.status, "maturity_target": self.maturity_target,
            "maturity_achieved": self.maturity_achieved,
            "playtest_status": self.playtest_status,
            "episodes_reached_playing": self.episodes_reached_playing,
            "total_frames": self.total_frames,
            "game_over_supported": self.game_over_supported,
            "restart_supported": self.restart_supported,
            "page_error_count": self.page_error_count,
            "pixel_rendered_count": self.pixel_rendered_count,
            "input_reflected_count": self.input_reflected_count,
            "assets": self.assets, "needs_runtime_tool": self.needs_runtime_tool,
            "evidence_path": self.evidence_path, "error": self.error,
        }


def _attach_audio(spec: SliceSpec, slice_dir: Path) -> Dict[str, Any]:
    """用 W7 AudioFactory 真实合成该切片音频（离线、程序化、确定性）。"""
    try:
        from pipeline.audio_factory import AudioFactory, AudioSpec
    except Exception as exc:
        return {"ok": False, "error": f"audio_factory 不可用: {exc}"}
    audio_dir = slice_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    produced: Dict[str, Any] = {"ok": True, "wavs": [], "provenance": []}
    try:
        # BGM：按切片 sfx_theme 调式真实合成
        bgm_spec = AudioSpec(kind=spec.sfx_theme, name=f"{spec.id}_bgm",
                             duration=2.0, theme=spec.sfx_theme, bpm=120)
        rec = AudioFactory().generate(bgm_spec, backend="procedural_synth", seed=7)
        saved = AudioFactory().save(rec, str(audio_dir))
        produced["wavs"].append("audio/" + Path(saved["wav"]).name)
        produced["provenance"].append({"kind": spec.sfx_theme,
                                        "is_procedural_synth": rec.is_procedural_synth,
                                        "is_ai_generated": rec.is_ai_generated,
                                        "rms": round(rec.rms, 5)})
        # SFX：每个 kind 真实合成
        for k in spec.sfx_kinds:
            sfx_spec = AudioSpec(kind=k, name=f"{spec.id}_{k}", duration=0.4)
            r2 = AudioFactory().generate(sfx_spec, backend="procedural_synth", seed=3)
            sv = AudioFactory().save(r2, str(audio_dir))
            produced["wavs"].append("audio/" + Path(sv["wav"]).name)
            produced["provenance"].append({"kind": k,
                                            "is_procedural_synth": r2.is_procedural_synth,
                                            "is_ai_generated": r2.is_ai_generated,
                                            "rms": round(r2.rms, 5)})
    except Exception as exc:
        produced["ok"] = False
        produced["error"] = f"音频合成失败: {exc}"
    return produced


def validate_slice(spec: SliceSpec, episodes: int = 2, play_seconds: float = 3.0,
                   seed: int = 42, attach_audio: bool = True,
                   evidence_dir: Optional[str] = None) -> SliceValidationResult:
    """对单个切片走完整端到端链路，返回诚实验证结果。"""
    slice_dir = ROOT / "output" / "slices" / spec.id
    res = SliceValidationResult(slice_id=spec.id, name=spec.name,
                                genre=spec.genre, maturity_target=spec.maturity_target)

    # ① 生成 contract-bearing 可玩原型
    try:
        html_path = generate_slice(spec, str(slice_dir))
        res.assets["html"] = str(html_path)
    except Exception as exc:
        res.error = f"切片原型生成失败: {exc}"
        res.status = RuntimeStatus.FAIL
        return res

    # ② 接入 W7 真实程序化音频（honest 适配器）
    if attach_audio:
        res.assets["audio"] = _attach_audio(spec, slice_dir)

    # ③ 真实浏览器自动试玩闭环（W8）
    eng = pe.PlaytestEngine(evidence_dir=evidence_dir or str(ROOT / "output" / "slices" / "evidence"),
                            seed=seed)
    pr = eng.run(str(html_path), episodes=episodes, play_seconds=play_seconds,
                 seed=seed, policy="auto", headless=True)
    res.playtest_status = pr.status
    res.episodes_reached_playing = pr.episodes_reached_playing
    res.total_frames = pr.total_frames
    res.game_over_supported = pr.game_over_supported
    res.restart_supported = pr.restart_supported
    res.page_error_count = pr.page_error_count
    res.pixel_rendered_count = pr.pixel_rendered_count
    res.input_reflected_count = pr.input_reflected_count
    res.needs_runtime_tool = pr.needs_runtime_tool
    res.evidence_path = pr.evidence_path
    res.error = pr.error or res.error

    # ④ 诚实 verdict + 成熟度评估
    if pr.status == RuntimeStatus.NEEDS_RUNTIME_TOOL:
        res.status = RuntimeStatus.NEEDS_RUNTIME_TOOL
    elif pr.status == RuntimeStatus.PASS and pr.page_error_count == 0:
        res.status = RuntimeStatus.PASS
        # 成熟度：boot+可玩骨架 = Slice 2；若还真实支持 game_over/restart 闭合 = 再进阶
        res.maturity_achieved = 2
        if pr.game_over_supported and pr.restart_supported:
            res.maturity_achieved = 3
    else:
        res.status = RuntimeStatus.FAIL
    return res


def validate_all(episodes: int = 2, play_seconds: float = 3.0, seed: int = 42,
                 attach_audio: bool = True, evidence_dir: Optional[str] = None,
                 report_path: Optional[str] = None) -> Dict[str, Any]:
    """端到端验证全部 8 个切片，汇总诚实报告。

    report_path 缺省写入权威聚合报告 output/slices/vertical_slices_report.json；
    单测等调用方传入独立路径，避免覆盖权威报告（防伪证：报告须如实反映最近一次生产/守护运行）。
    """
    results: List[SliceValidationResult] = []
    for spec in VERTICAL_SLICES:
        results.append(validate_slice(spec, episodes=episodes, play_seconds=play_seconds,
                                       seed=seed, attach_audio=attach_audio,
                                       evidence_dir=evidence_dir))
    passed = sum(1 for r in results if r.status == RuntimeStatus.PASS)
    needs_rt = sum(1 for r in results if r.status == RuntimeStatus.NEEDS_RUNTIME_TOOL)
    failed = sum(1 for r in results if r.status == RuntimeStatus.FAIL)
    report = {
        "total": len(results),
        "passed": passed, "needs_runtime_tool": needs_rt, "failed": failed,
        "slices": [r.to_dict() for r in results],
    }
    out_dir = ROOT / "output" / "slices"
    out_dir.mkdir(parents=True, exist_ok=True)
    rpath = Path(report_path) if report_path else (out_dir / "vertical_slices_report.json")
    rpath.parent.mkdir(parents=True, exist_ok=True)
    rpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


__all__ = ["SliceValidationResult", "validate_slice", "validate_all"]
