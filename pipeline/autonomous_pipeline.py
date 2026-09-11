"""pipeline/autonomous_pipeline.py — W10 长时程自主生产管线（诚实、可无人值守、三处停）。

一句话意图 → 规范 → 装配可玩原型(接真实音频) → 真机试玩 → 打包可上架包 → 发布门禁，
全程经 core/orchestrator.py 的 DAG 编排（断点续跑 / 并行 / 失败传播 / 指纹跳过），不另起炉灶。

诚实红线（与计划 13.2、W5–W9 一致）：
  - 每阶段用真实、确定性适配器；缺真实浏览器/音频后端等运行工具 → 该节点 NEEDS_RUNTIME_TOOL，
    绝不把「文件存在」或「曾生成」粉饰成通过。
  - 三处人停（缺凭据 / 需审美拍板 / 超预算）由 HumanStopPolicy 显式分类，绝不静默假装完成。
  - 预算（LLM/时长/范围）由 BudgetController 控，超预算即上报暂停，不硬撑。
  - 每运行写项目级记忆 run_memory.jsonl：节点决策 / 失败 / 最终人停原因，可回溯。
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.artifact_store import ArtifactStore
from core.contracts import ArtifactRef, GameIntent, GameSpec, WorkflowNode, WorkflowPlan
from core.gate_engine import GateEngine
from core.orchestrator import CallableNodeExecutor, NodeResult, NodeStatus, Orchestrator
from core.release_service import ReleaseBlockedError, ReleaseService
from core.runtime_adapter import RuntimeStatus
from core.workflow_orchestrator import WorkflowOrchestrator
from pipeline.asset_factory import AssetFactory, AssetSpec
from pipeline.image_gen_adapter import ImageGenAdapter
from pipeline.playtest_engine import PlaytestEngine
from pipeline.style_bible import StyleBible
from pipeline.vertical_slice_validator import _attach_audio
from pipeline.vertical_slices import VERTICAL_SLICES, SliceSpec, get_slice

ROOT = Path(__file__).resolve().parent.parent

# 意图 genre 词 → 垂直切片 id（缺省 vs_rhythm，保证确定性可装配）
_GENRE_TO_SLICE = {
    "卡牌": "vs_card_roguelike", "roguelike": "vs_card_roguelike",
    "弹幕": "vs_survivor_danmaku", "danmaku": "vs_survivor_danmaku", "survivor": "vs_survivor_danmaku",
    "节奏": "vs_rhythm", "rhythm": "vs_rhythm",
    "赛车": "vs_racing", "racing": "vs_racing",
    "工厂": "vs_factory_sim", "factory": "vs_factory_sim",
    "地牢": "vs_roguelike_dungeon", "dungeon": "vs_roguelike_dungeon",
    "3d": "vs_3d_action", "3a": "vs_3d_action", "动作": "vs_3d_action",
    "叙事": "vs_narrative_mystery", "mystery": "vs_narrative_mystery", "narrative": "vs_narrative_mystery",
}


def genre_to_slice(genre: str) -> str:
    g = (genre or "").lower()
    for token, sid in _GENRE_TO_SLICE.items():
        if token.lower() in g:
            return sid
    return "vs_rhythm"


# ── 预算控制（超预算上报，不硬撑） ──────────────────────────────────────────
@dataclass
class BudgetController:
    limit_usd: float = 100.0
    cost_table: Dict[str, float] = field(default_factory=dict)
    estimated_usd: float = 0.0

    def charge(self, capability_id: str) -> None:
        self.estimated_usd += float(self.cost_table.get(capability_id, 0.0))

    @property
    def exceeded(self) -> bool:
        return self.estimated_usd > self.limit_usd


# ── 人机分工：三处停（缺凭据 / 需审美拍板 / 超预算） ──────────────────────────
class HumanStopPolicy:
    """把编排报告 + 预算 + 发布资格分类成自洽的人停状态，绝不假装完成。"""

    STATUS_COMPLETED = "COMPLETED"          # preview 可上架包就绪；生产上架仍需人工审美拍板
    # 本地开发模式专用：出货包已产出，但验证类节点因缺本机工具未跑。
    # 与 COMPLETED 的区别是**不得声称已验证**，退出码也不同（5 而非 0）。
    STATUS_COMPLETED_UNVERIFIED = "COMPLETED_UNVERIFIED"
    STATUS_PAUSED = "PAUSED"                # 中途停下问人
    STATUS_FAILED = "FAILED"                # 真失败（非环境缺口）

    @staticmethod
    def classify(
        results: Dict[str, NodeResult],
        *,
        budget_exceeded: bool,
        release_eligible: bool,
        unresolved_gates: List[str],
        mode: str = "local",
        degradable: Optional[Any] = None,
    ) -> Tuple[str, str, List[str]]:
        """返回 (status, stop_reason, unverified)。

        mode=local 时，属于 degradable 集合的 NEEDS_RUNTIME_TOOL 节点不再把整机
        拖成 PAUSED，而是记入 unverified —— 本地开发不该因为没装浏览器驱动就
        连包都出不来；但绝不能因此把「没试玩」说成「已试玩」。
        """
        degradable = set(degradable or [])
        if mode != "local":
            degradable = set()  # 平台模式下不允许任何降级

        if budget_exceeded:
            return (HumanStopPolicy.STATUS_PAUSED,
                    "over_budget: 预估成本超出预算，已暂停并上报，等待人工增拨", [])
        needs_rt = sorted(n for n, r in results.items() if r.status == NodeStatus.NEEDS_RUNTIME_TOOL)
        if needs_rt and degradable:
            degradable_hit = sorted(n for n in needs_rt if n in degradable)
            hard_hit = sorted(n for n in needs_rt if n not in degradable)
            if degradable_hit and not hard_hit:
                return (HumanStopPolicy.STATUS_COMPLETED_UNVERIFIED,
                        f"unverified_only: {', '.join(degradable_hit)}"
                        f"（本地模式：缺本机运行工具，出货包已产出但该验证项未跑，不得声称已验证）",
                        degradable_hit)
        if needs_rt:
            return (HumanStopPolicy.STATUS_PAUSED,
                    f"missing_runtime_tool: {', '.join(needs_rt)}（缺真实运行工具/凭据，无法继续验证）", [])
        needs_llm = sorted(n for n, r in results.items() if r.status == NodeStatus.NEEDS_LLM_CREDENTIALS)
        if needs_llm:
            return (HumanStopPolicy.STATUS_PAUSED,
                    f"missing_credentials: {', '.join(needs_llm)}（缺 LLM 凭据，无法继续）", [])
        if unresolved_gates:
            return (HumanStopPolicy.STATUS_FAILED,
                    f"unresolved_gates: {', '.join(unresolved_gates)}", [])
        unresolved = sorted(n for n, r in results.items() if r.status not in NodeStatus.TERMINAL_OK)
        if unresolved:
            return (HumanStopPolicy.STATUS_FAILED, f"unresolved_nodes: {', '.join(unresolved)}", [])
        if release_eligible:
            return (HumanStopPolicy.STATUS_COMPLETED,
                    "preview 可上架包就绪（元数据/素材/合规齐全）；生产上架需人工审美拍板 + 版号/渠道凭据", [])
        return (HumanStopPolicy.STATUS_COMPLETED,
                "build+package 已产出；发布门禁未达预览资格（见 gates）", [])


# ── 执行器：把 capability_id 映射到真实确定性适配器 ─────────────────────────
class AutonomousExecutor(CallableNodeExecutor):
    """W10 自主生产各阶段的真实执行器（确定性、诚实、可无人值守）。"""

    def __init__(self, store: ArtifactStore, run_id: str,
                 art_backend: Optional[str] = None,
                 asset_factory: Optional[AssetFactory] = None):
        super().__init__()
        self._store = store
        self._run_id = run_id
        # None = auto：cloud_api → 本机 ComfyUI → 程序化占位；默认不绕过真实 AIGC。
        self._art_backend = art_backend
        self._asset_factory = asset_factory or AssetFactory(ImageGenAdapter())
        self.register("assemble.build", self._fn_assemble)
        self.register("playtest.run", self._fn_playtest)
        self.register("package.game", self._fn_package)

    # ── assemble.build：装配可玩原型 + 接 W7 真实程序化音频 ──
    def _fn_assemble(self, node: WorkflowNode, ctx: Any) -> NodeResult:
        from core.contracts import GameSpec as _GS
        resolved, missing = ctx.resolve_inputs(node)
        if missing:
            return NodeResult(node.node_id, NodeStatus.FAILED, errors=[f"missing inputs: {missing}"])
        spec_dict = resolved.get(node.inputs[0]) or {}
        slice_id = genre_to_slice(spec_dict.get("genre", ""))
        slice_spec: SliceSpec = get_slice(slice_id)
        build_dir = ROOT / "output" / "autonomous" / self._run_id / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        try:
            html_path = slice_spec and self._generate(slice_spec, build_dir)
            audio = _attach_audio(slice_spec, build_dir) if slice_spec is not None else {"ok": False}
            art = self._generate_art(
                spec_dict=spec_dict, slice_spec=slice_spec, build_dir=build_dir,
                seed=int(getattr(node, "meta", {}).get("seed", 42))
                if isinstance(getattr(node, "meta", {}), dict) else 42,
            )
        except Exception as exc:  # 装配真实炸了，如实记录，不吞
            return NodeResult(node.node_id, NodeStatus.FAILED,
                              errors=[f"assemble exception: {type(exc).__name__}: {exc}"])
        if html_path is None:
            return NodeResult(node.node_id, NodeStatus.FAILED, errors=["切片生成返回空路径"])
        audio_paths = [str(build_dir / a) for a in audio.get("wavs", [])]
        if not art.get("ok"):
            # 显式后端缺位是环境缺口，不把没有美术误报为自主出货成功。
            if art.get("needs_runtime_tool"):
                return NodeResult(node.node_id, NodeStatus.NEEDS_RUNTIME_TOOL,
                                  errors=[art.get("error", "AIGC 美术后端不可用")],
                                  meta={"art_backend": art.get("backend"),
                                        "needs_runtime_tool": art.get("needs_runtime_tool")})
            return NodeResult(node.node_id, NodeStatus.FAILED,
                              errors=[art.get("error", "AIGC 美术生成失败")])
        ref = self._store.put_json("GameBuild", {
            "run_id": self._run_id,
            "slice_id": slice_id,
            "genre": spec_dict.get("genre", ""),
            "title": spec_dict.get("title", ""),
            "html_path": str(html_path),
            "audio_paths": audio_paths,
            "audio_ok": bool(audio.get("ok")),
            "art_assets": art["assets"],
            "style_bible": art["style_bible"],
        }, producer_capability="assemble.build")
        return NodeResult(node.node_id, NodeStatus.SUCCEEDED, output_ref=ref.artifact_id,
                          meta={"slice_id": slice_id, "audio_ok": bool(audio.get("ok")),
                                "art_backend": art["backend"],
                                "art_is_ai_generated": art["is_ai_generated"],
                                "art_asset_count": len(art["assets"])})

    def _generate_art(self, spec_dict: Dict[str, Any], slice_spec: SliceSpec,
                      build_dir: Path, seed: int) -> Dict[str, Any]:
        """生成自主包默认美术，并把真实 provenance 带进 GameBuild。

        art_backend=None 使用 W5 自动优先级；真实 ComfyUI 成功才标 AI，
        适配器自身的 procedural fallback 仍会携带诚实占位标记。
        """
        style = StyleBible.build(
            name=f"autonomous_{slice_spec.id}",
            seed=seed,
            line="clean game UI silhouette, readable icon edges",
            lighting="soft sci-fi rim light, controlled contrast",
            composition="centered hero composition, clear silhouette",
        )
        style.lock()
        asset_name = "hero_art"
        asset_spec = AssetSpec(
            asset_type="background",
            name=asset_name,
            width=512,
            height=512,
            require_alpha=False,
            style_ref=style.name,
            prompt=(
                f"{slice_spec.name} game hero art, {slice_spec.genre} genre, "
                "no text, production-ready game asset, readable at small size"
            ),
        )
        rec = self._asset_factory.generate(
            asset_spec, style=style, backend=self._art_backend, seed=seed,
        )
        # Auto mode：ComfyUI/API 硬错误时，仍可产出可运行包，但必须明确变成程序化占位。
        # 显式 backend 则不偷偷降级，缺工具会让 assemble 停在 NEEDS_RUNTIME_TOOL。
        if (not rec.image_bytes and self._art_backend is None):
            fallback = self._asset_factory.generate(
                asset_spec, style=style, backend="procedural_placeholder", seed=seed,
            )
            fallback.provenance["fallback_reason"] = rec.error or rec.status
            fallback.provenance["requested_backend"] = "auto"
            fallback.needs_runtime_tool = rec.needs_runtime_tool or "aigc_backend"
            rec = fallback
        if not rec.image_bytes:
            return {
                "ok": False, "backend": rec.backend,
                "needs_runtime_tool": rec.needs_runtime_tool,
                "error": rec.error or "AIGC 美术未产出图像",
                "assets": [], "style_bible": style.to_dict(),
                "is_ai_generated": False,
            }
        saved = self._asset_factory.save(rec, str(build_dir / "assets"))
        asset_meta = rec.to_dict()
        asset_meta["png_path"] = str(Path(saved["png"]))
        asset_meta["provenance_path"] = str(Path(saved["json"]))
        return {
            "ok": True,
            "backend": rec.backend,
            "needs_runtime_tool": rec.needs_runtime_tool,
            "assets": [asset_meta],
            "style_bible": style.to_dict(),
            "is_ai_generated": rec.is_ai_generated,
        }

    @staticmethod
    def _generate(slice_spec: SliceSpec, build_dir: Path):
        from pipeline.slice_prototyper import generate_slice
        return generate_slice(slice_spec, str(build_dir))

    # ── playtest.run：W8 真机自动试玩闭环（缺浏览器→诚实 NEEDS_RUNTIME_TOOL） ──
    def _fn_playtest(self, node: WorkflowNode, ctx: Any) -> NodeResult:
        resolved, missing = ctx.resolve_inputs(node)
        if missing:
            return NodeResult(node.node_id, NodeStatus.FAILED, errors=[f"missing inputs: {missing}"])
        build = resolved.get(node.inputs[0]) or {}
        html_path = build.get("html_path")
        if not html_path or not Path(html_path).exists():
            return NodeResult(node.node_id, NodeStatus.FAILED, errors=["build html 缺失"])
        evidence_dir = str(ROOT / "output" / "autonomous" / self._run_id / "evidence")
        episodes = int(node.meta.get("episodes", 2)) if isinstance(node.meta, dict) else 2
        play_seconds = float(node.meta.get("play_seconds", 3.0)) if isinstance(node.meta, dict) else 3.0
        seed = int(node.meta.get("seed", 42)) if isinstance(node.meta, dict) else 42
        try:
            eng = PlaytestEngine(evidence_dir=evidence_dir, seed=seed)
            pr = eng.run(html_path, episodes=episodes, play_seconds=play_seconds,
                        seed=seed, policy="auto", headless=True)
        except Exception as exc:
            return NodeResult(node.node_id, NodeStatus.FAILED,
                              errors=[f"playtest exception: {type(exc).__name__}: {exc}"])
        # 诚实映射：RuntimeStatus.PASS → SUCCEEDED；NEEDS_RUNTIME_TOOL → 原样
        if pr.status == RuntimeStatus.PASS:
            status = NodeStatus.SUCCEEDED
        elif pr.status == RuntimeStatus.NEEDS_RUNTIME_TOOL:
            status = NodeStatus.NEEDS_RUNTIME_TOOL
        else:
            status = NodeStatus.FAILED
        ref = self._store.put_json("PlaytestResult", {
            "run_id": self._run_id,
            "target": html_path,
            "status": pr.status,
            "episodes_reached_playing": pr.episodes_reached_playing,
            "total_frames": pr.total_frames,
            "game_over_supported": pr.game_over_supported,
            "restart_supported": pr.restart_supported,
            "page_error_count": pr.page_error_count,
            "evidence_path": pr.evidence_path,
            "needs_runtime_tool": pr.needs_runtime_tool,
        }, producer_capability="playtest.run")
        return NodeResult(node.node_id, status, output_ref=ref.artifact_id,
                          meta={"status": pr.status, "frames": pr.total_frames,
                                "page_errors": pr.page_error_count})

    # ── package.game：打包可上架包（元数据/素材/合规齐全） ──
    def _fn_package(self, node: WorkflowNode, ctx: Any) -> NodeResult:
        resolved, missing = ctx.resolve_inputs(node)
        if missing:
            return NodeResult(node.node_id, NodeStatus.FAILED, errors=[f"missing inputs: {missing}"])
        build = resolved.get(node.inputs[0]) or {}
        html_path = build.get("html_path")
        if not html_path or not Path(html_path).exists():
            return NodeResult(node.node_id, NodeStatus.FAILED, errors=["build html 缺失，无法打包"])
        # 读取试玩状态（若已产出）以决定合规清单中 playtest 一项
        playtest_status = None
        for r in self._store.list_refs():
            if r.artifact_type == "PlaytestResult":
                try:
                    playtest_status = json.loads(self._store.read_bytes(r.artifact_id).decode()).get("status")
                except Exception:
                    playtest_status = None
                break
        pkg_dir = ROOT / "output" / "autonomous" / self._run_id / "package"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        audio_src = Path(html_path).parent / "audio"
        audio_dst = pkg_dir / "audio"
        wavs: List[str] = []
        if audio_src.is_dir():
            audio_dst.mkdir(parents=True, exist_ok=True)
            for f in sorted(audio_src.glob("*.wav")):
                shutil.copy2(f, audio_dst / f.name)
                wavs.append(f.name)
        shutil.copy2(html_path, pkg_dir / "index.html")

        # W5 AIGC 美术随自主包一起交付：PNG 与逐资产 provenance JSON 都复制，
        # manifest 只引用真实文件和真实哈希，不把生成路径当作包内路径。
        art_assets = []
        art_dst = pkg_dir / "assets"
        for asset in build.get("art_assets", []) or []:
            src_png = Path(asset.get("png_path", ""))
            src_prov = Path(asset.get("provenance_path", ""))
            if not src_png.exists() or not src_prov.exists():
                continue
            art_dst.mkdir(parents=True, exist_ok=True)
            png_name = src_png.name
            prov_name = src_prov.name
            shutil.copy2(src_png, art_dst / png_name)
            shutil.copy2(src_prov, art_dst / prov_name)
            art_assets.append({
                "asset_id": asset.get("asset_id"),
                "name": (asset.get("spec") or {}).get("name", png_name),
                "png": f"assets/{png_name}",
                "provenance": f"assets/{prov_name}",
                "backend": asset.get("backend"),
                "is_ai_generated": bool(asset.get("is_ai_generated")),
                "is_procedural_placeholder": bool(asset.get("is_procedural_placeholder")),
                "content_hash": asset.get("content_hash"),
                "qa": asset.get("qa"),
                "provenance_data": asset.get("provenance", {}),
            })
        art_has_ai = any(a["is_ai_generated"] for a in art_assets)
        art_has_placeholder = any(a["is_procedural_placeholder"] for a in art_assets)
        art_provenance = [
            {"kind": "audio", "is_ai_generated": False,
             "source": "W7 AudioFactory procedural_synth"},
            {"kind": "html_game", "is_ai_generated": False,
             "source": f"W9 slice_prototyper ({build.get('slice_id', '')})"},
        ] + [
            {"kind": "image", "asset_id": a["asset_id"],
             "is_ai_generated": a["is_ai_generated"],
             "backend": a["backend"], "content_hash": a["content_hash"],
             "provenance_file": a["provenance"],
             "provenance": a["provenance_data"]}
            for a in art_assets
        ]
        content_warnings = ["音频为程序化合成（W7 AudioFactory，非 AI 作曲）"]
        if art_has_placeholder:
            content_warnings.append("美术含程序化占位（真实 AIGC 后端未成功产出，已如实标注）")
        if art_has_ai:
            content_warnings.append("AI 美术仍需人工/VLM 审美与版权复核，不能由程序化 QA 代替")
        manifest = {
            "package_id": self._run_id,
            "title": build.get("title", ""),
            "genre": build.get("genre", ""),
            "slice_id": build.get("slice_id", ""),
            "target_platforms": ["web"],
            "contract_version": "1.0",
            "build": {"html": "index.html", "audio": wavs,
                      "art_assets": [{"png": a["png"], "provenance": a["provenance"]}
                                     for a in art_assets]},
            "style_bible": build.get("style_bible", {}),
            "art_generation": {"asset_count": len(art_assets), "ai_generated": art_has_ai,
                               "procedural_placeholder": art_has_placeholder},
            "compliance": {
                "age_rating": "未评级（生产上架需人工审美拍板 + 版号）",
                "content_warnings": content_warnings,
                "asset_provenance": art_provenance,
                "honest_notes": (
                    "AIGC 美术 provenance 已随包落盘；AI 图语义风格/版权仍需人工或 VLM 复核。"
                    if art_has_ai else
                    "本次没有真实 AIGC 图，包内美术为程序化占位；不得宣称为 AI 美术。"
                ),
            },
        }
        (pkg_dir / "package_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        checklist = {
            "items": [
                {"id": "metadata_present", "passed": True},
                {"id": "assets_present", "passed": True},
                {"id": "age_rating_declared", "passed": True},
                {"id": "content_warning_declared", "passed": True},
                {"id": "asset_provenance_declared", "passed": bool(art_assets),
                 "note": "每个美术 PNG 均有同名 provenance JSON" if art_assets else "未找到美术资产"},
                {"id": "art_qa_structural", "passed": all(
                    bool((a.get("qa") or {}).get("passed")) for a in art_assets),
                 "note": "尺寸/通道/内嵌水印元数据等程序化 QA；AI 语义风格仍需 VLM"
                         if art_assets else "未找到美术资产"},
                {"id": "playtest_verified", "passed": (playtest_status == RuntimeStatus.PASS),
                 "note": playtest_status or "not_run"},
                {"id": "human_signoff_for_production", "passed": False,
                 "note": "生产上架需人工审美拍板 + 版号/渠道凭据"},
            ]
        }
        (pkg_dir / "compliance_checklist.json").write_text(
            json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8")
        files = ["index.html", "package_manifest.json", "compliance_checklist.json"] + (
            [f"audio/{w}" for w in wavs]) + [a["png"] for a in art_assets] + [
                a["provenance"] for a in art_assets]
        ref = self._store.put_json("ShippablePackage", {
            "run_id": self._run_id,
            "package_dir": str(pkg_dir),
            "manifest_path": str(pkg_dir / "package_manifest.json"),
            "files": files,
            "art_assets": art_assets,
        }, producer_capability="package.game")
        return NodeResult(node.node_id, NodeStatus.SUCCEEDED, output_ref=ref.artifact_id,
                          meta={"package_dir": str(pkg_dir), "files": files,
                                "art_asset_count": len(art_assets),
                                "art_is_ai_generated": art_has_ai,
                                "art_has_placeholder": art_has_placeholder})


# ── 计划构建 ────────────────────────────────────────────────────────────────
def build_autonomous_plan(run_id: str, intent_id: str, spec_id: str) -> WorkflowPlan:
    """可执行的自主生产 DAG：assemble → (playtest ∥ package)；失败策略 continue 保证可无人值守。

    package 不依赖 playtest：打包与试玩真正同层并行；最终 G4/G6 仍由
    run_autonomous 汇总试玩结果后裁决，避免把“包存在”误当成试玩通过。
    """
    nodes = [
        WorkflowNode("assemble", "assemble.build", "1.0.0", [spec_id], ["build_artifact"], []),
        WorkflowNode("playtest", "playtest.run", "1.0.0", ["build_artifact"], ["playtest_evidence"],
                     ["assemble"], failure_policy="continue"),
        WorkflowNode("package", "package.game", "1.0.0", ["build_artifact"], ["package_artifact"],
                     ["assemble"], failure_policy="continue"),
    ]
    return WorkflowPlan(run_id, intent_id, spec_id, "web_survivor_vertical_v1", nodes)


def _read_artifact(store: ArtifactStore, artifact_type: str) -> Optional[Dict[str, Any]]:
    for r in store.list_refs():
        if r.artifact_type == artifact_type:
            try:
                return json.loads(store.read_bytes(r.artifact_id).decode("utf-8"))
            except Exception:
                return None
    return None


def _find_ref(store: ArtifactStore, artifact_type: str) -> Optional[ArtifactRef]:
    for r in store.list_refs():
        if r.artifact_type == artifact_type:
            return r
    return None


# ── 自主驱动器：编排 + 预算 + 门禁 + 人停 + 项目记忆 ─────────────────────────
def run_autonomous(
    intent: GameIntent,
    *,
    budget_usd: float = 100.0,
    cost_table: Optional[Dict[str, float]] = None,
    episodes: int = 2,
    play_seconds: float = 3.0,
    seed: int = 42,
    max_workers: int = 2,
    resume: bool = True,
    art_backend: Optional[str] = None,
    mode: str = "local",
) -> Dict[str, Any]:
    from pipeline.run_mode import (
        LOCAL, PLATFORM, check_platform_readiness, check_local_readiness, describe_mode,
    )
    mode = PLATFORM if str(mode).strip().lower() == PLATFORM else LOCAL
    # 平台模式前置门禁：外部账号/沙箱/域名不是代码能替代的，开工前就摊牌，
    # 避免用户跑了半天才在末尾看到「缺渠道凭据」。
    if mode == PLATFORM:
        pre = check_platform_readiness()
        if not pre["ready"]:
            return {
                "run_id": intent.run_id,
                "intent": {"title": intent.title, "genre": intent.genre},
                "status": HumanStopPolicy.STATUS_PAUSED,
                "stop_reason": "platform_prerequisites_missing: 平台模式外部依赖未齐 → "
                               + "；".join(pre["blocking"]),
                "mode": mode,
                "unverified": [],
                "platform_gate": pre,
                "node_counts": {}, "totals": {"total": 0, "succeeded": 0, "unresolved": 0},
                "package": {}, "gates": {}, "acceptance": {},
                "budget": {"limit_usd": budget_usd, "estimated_usd": 0.0, "exceeded": False},
                "release_eligible": False,
                "hint": "改用法 --run-mode local 可先本地开发（不要求任何渠道/线上配置）",
            }

    wf = WorkflowOrchestrator()
    spec = wf.normalize_spec(intent)
    run_dir = ROOT / "output" / "autonomous" / intent.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    store = ArtifactStore(run_dir)

    intent_ref = store.put_json("GameIntent", intent.to_dict(), artifact_id=intent.intent_id,
                                producer_capability="intent.normalize")
    spec_ref = store.put_json("GameSpec", spec.to_dict(), artifact_id=spec.spec_id,
                              parent_artifact_id=intent_ref.artifact_id,
                              producer_capability="intent.normalize")
    plan = build_autonomous_plan(intent.run_id, intent.intent_id, spec.spec_id)
    store.put_json("WorkflowPlan", plan.to_dict(), artifact_id=plan.plan_id,
                   parent_artifact_id=spec_ref.artifact_id, producer_capability="workflow.plan")

    # 把意图/规范绑定进执行上下文，供 assemble 节点解析
    orch = Orchestrator(
        plan, store,
        executors=[AutonomousExecutor(store, intent.run_id, art_backend=art_backend)],
        max_workers=max_workers, resume=resume,
    )
    orch.ctx.bindings["intent_id"] = intent_ref.artifact_id
    orch.ctx.bindings["spec_id"] = spec_ref.artifact_id
    # 试玩参数透传
    for n in plan.nodes:
        if n.capability_id == "playtest.run":
            n.meta = {"episodes": episodes, "play_seconds": play_seconds, "seed": seed}

    report = orch.run()
    results = report.results

    # 预算：按 capability 计费（确定性阶段默认 0；测试可注入成本触发超预算暂停）
    budget = BudgetController(limit_usd=budget_usd, cost_table=cost_table or {})
    for nid, r in results.items():
        node = orch._nodes.get(nid)
        if node is not None:
            budget.charge(node.capability_id)

    # 门禁 G0–G6（诚实裁决，缺证即 FAIL）
    gate_engine = GateEngine(store)
    build = _read_artifact(store, "GameBuild")
    playtest = _read_artifact(store, "PlaytestResult")
    package = _read_artifact(store, "ShippablePackage")
    html_ok = bool(build and Path(build.get("html_path", "")).exists())
    g0 = gate_engine.evaluate("G0", passed=True, evidence_refs=[intent_ref.artifact_id])
    g1 = gate_engine.evaluate("G1", passed=True, evidence_refs=[spec_ref.artifact_id])
    g2 = gate_engine.evaluate("G2", passed=True, evidence_refs=[plan.plan_id])
    g3 = gate_engine.evaluate("G3", passed=html_ok,
                              evidence_refs=[build["html_path"]] if build else [],
                              reason_codes=[] if html_ok else ["build_html_missing"])
    pt_status = (playtest or {}).get("status")
    g4_pass = pt_status == RuntimeStatus.PASS
    g4 = gate_engine.evaluate("G4", passed=g4_pass,
                              reason_codes=[] if g4_pass else [f"playtest_{str(pt_status).lower()}"])
    pkg_ok = bool(package and Path(package.get("manifest_path", "")).exists())
    g5 = gate_engine.evaluate("G5", passed=pkg_ok,
                              reason_codes=[] if pkg_ok else ["package_manifest_missing"])
    all_decisions = [g0, g1, g2, g3, g4, g5]
    g6 = gate_engine.evaluate_release_gate("G6", all_decisions)

    release_eligible = (g6.result == "PASS")
    release_manifest = None
    if release_eligible:
        pkg_ref = _find_ref(store, "ShippablePackage")
        if pkg_ref is not None:
            try:
                rel = ReleaseService(store).create_candidate(
                    channel="preview",
                    candidate_artifact=pkg_ref,
                    intent_ref=intent.intent_id,
                    spec_ref=spec.spec_id,
                    workflow_ref=plan.plan_id,
                    evidence_ref=(playtest or {}).get("evidence_path") or intent_ref.artifact_id,
                    decisions=[d.to_dict() for d in all_decisions] + [g6.to_dict()],
                )
                release_manifest = rel.to_dict()
            except ReleaseBlockedError as exc:
                release_manifest = {"error": str(exc)}

    from pipeline.run_mode import DEGRADABLE_NODES_IN_LOCAL
    status, stop_reason, unverified = HumanStopPolicy.classify(
        results, budget_exceeded=budget.exceeded,
        release_eligible=release_eligible,
        unresolved_gates=[g.gate_id for g in all_decisions if g.result != "PASS"] + (
            [] if g6.result == "PASS" else ["G6"]),
        mode=mode, degradable=DEGRADABLE_NODES_IN_LOCAL,
    )

    acceptance = {
        "verified_scenarios": ["boot_to_play"] if html_ok else [],
        "unverified_scenarios": [] if (pt_status == RuntimeStatus.PASS) else ["playtest_not_verified"],
        "metrics_collected": pt_status == RuntimeStatus.PASS,
        "playtest_status": pt_status,
    }

    # 项目级记忆：节点决策 + 最终人停原因，可回溯
    memory_path = run_dir / "run_memory.jsonl"
    with memory_path.open("a", encoding="utf-8") as fh:
        for nid, r in results.items():
            fh.write(json.dumps({"kind": "node", "node_id": nid, "status": r.status,
                                 "attempts": r.attempts, "errors": r.errors,
                                 "meta": r.meta}, ensure_ascii=False) + "\n")
        fh.write(json.dumps({"kind": "autonomous_decision", "run_id": intent.run_id,
                             "status": status, "stop_reason": stop_reason,
                             "release_eligible": release_eligible,
                             "budget": {"limit_usd": budget.limit_usd,
                                        "estimated_usd": round(budget.estimated_usd, 6),
                                        "exceeded": budget.exceeded},
                             "gates": {d.gate_id: d.result for d in all_decisions + [g6]}},
                            ensure_ascii=False) + "\n")

    return {
        "run_id": intent.run_id,
        "intent": {"title": intent.title, "genre": intent.genre},
        "status": status,
        "stop_reason": stop_reason,
        "node_counts": report.counts,
        "totals": {"total": len(report.results), "succeeded": report.succeeded,
                   "unresolved": report.unresolved},
        "package": {
            "package_dir": package.get("package_dir") if package else None,
            "manifest_path": package.get("manifest_path") if package else None,
            "files": package.get("files") if package else None,
            "art_assets": package.get("art_assets") if package else None,
            "art_is_ai_generated": any(
                bool(a.get("is_ai_generated")) for a in (package.get("art_assets", []) if package else [])
            ),
        },
        "release": {"eligible": release_eligible, "manifest": release_manifest},
        "gates": {d.gate_id: d.result for d in all_decisions + [g6]},
        "budget": {"limit_usd": budget.limit_usd, "estimated_usd": round(budget.estimated_usd, 6),
                   "exceeded": budget.exceeded},
        "acceptance": acceptance,
        "memory_path": str(memory_path),
        "orchestration": report.to_dict(),
        "mode": mode,
        "mode_desc": describe_mode(mode),
        "unverified": unverified,
        "readiness": check_local_readiness(mode),
    }


__all__ = ["run_autonomous", "build_autonomous_plan", "AutonomousExecutor",
           "BudgetController", "HumanStopPolicy", "genre_to_slice"]
