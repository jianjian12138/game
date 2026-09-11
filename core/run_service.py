"""Unified application service for CLI, HTTP, and MCP callers."""
from __future__ import annotations

import json
import shutil
import time

from pathlib import Path
from typing import Any, Dict, Optional

from core.audit_log import AuditLog
from core.artifact_store import ArtifactStore, ArtifactIntegrityError
from core.contracts import EvidencePack, ArtifactRef, GameIntent
from core.workflow_orchestrator import WorkflowOrchestrator
from core.gate_engine import GateEngine
from core.release_service import ReleaseService, ReleaseBlockedError
from core.security_guard import SecurityGuardError, safe_resolve_path
from pipeline.live_service_sandbox import StagingSmoke


class RunService:
    """Compatibility-first service that makes every run contract-driven."""

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = Path(workspace or Path(__file__).resolve().parent.parent)
        self.output_dir = self.workspace / "output" / "runs"
        self.workflow = WorkflowOrchestrator()

    def create_intent(
        self,
        *,
        title: str,
        genre: str = "2D 独立游戏",
        custom_rules: str = "",
        source: str = "unknown",
        subject_id: str = "local",
        target_platforms: Optional[list[str]] = None,
        profile: str = "web_survivor_vertical_v1",
    ) -> GameIntent:
        return GameIntent(
            title=title,
            genre=genre,
            custom_rules=custom_rules,
            target_platforms=target_platforms or ["web"],
            profile=profile,
            created_by={"subject_id": subject_id, "source": source},
        )

    def prepare(self, intent: GameIntent) -> Dict[str, Any]:
        spec = self.workflow.normalize_spec(intent)
        plan = self.workflow.build_plan(intent, spec)
        run_dir = self.output_dir / intent.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        store = ArtifactStore(run_dir)
        audit = AuditLog(run_dir)
        intent_ref = store.put_json("GameIntent", intent.to_dict(), artifact_id=intent.intent_id, producer_capability="intent.normalize")
        spec_ref = store.put_json("GameSpec", spec.to_dict(), artifact_id=spec.spec_id, parent_artifact_id=intent_ref.artifact_id, producer_capability="intent.normalize")
        plan_ref = store.put_json("WorkflowPlan", plan.to_dict(), artifact_id=plan.plan_id, parent_artifact_id=spec_ref.artifact_id, producer_capability="workflow.plan")
        gate_engine = GateEngine(store)
        g0 = gate_engine.evaluate("G0", passed=True, evidence_refs=[intent_ref.artifact_id], reason_codes=[])
        g1 = gate_engine.evaluate("G1", passed=True, evidence_refs=[spec_ref.artifact_id], reason_codes=[])
        g2 = gate_engine.evaluate("G2", passed=True, evidence_refs=[plan_ref.artifact_id], reason_codes=[])
        audit.append("RunPrepared", intent_id=intent.intent_id, spec_id=spec.spec_id, plan_id=plan.plan_id)
        return {"intent": intent, "spec": spec, "plan": plan, "run_dir": run_dir, "store": store, "audit": audit, "gate_engine": gate_engine, "decisions": [g0, g1, g2]}

    def execute_run(self, intent: GameIntent, **kwargs: Any) -> Dict[str, Any]:
        """端到端标准化流水线调度：意图规范化 -> 计划 -> 独立沙箱构建 -> 浏览器运行适配器 -> G0-G5 门禁裁决"""
        prepared = self.prepare(intent)
        from core.studio_engine import StudioEngine
        from pipeline.browser_runtime_adapter import BrowserRuntimeAdapter
        from core.runtime_adapter import RuntimeStatus
        from core.release_service import ReleaseService

        engine = StudioEngine(output_dir=self.workspace / "output")
        result = engine.create_game_pipeline(
            title=intent.title,
            genre=intent.genre,
            custom_rules=intent.custom_rules,
            mode=kwargs.get("mode", "fast"),
            llm_provider=kwargs.get("llm_provider", "gemini"),
            llm_model=kwargs.get("llm_model"),
            run_id=intent.run_id,
            export_release=False,
        )
        run_id = result.get("run_id") or intent.run_id
        # 复用 prepare 阶段的同一工件库与审计链，避免同目录双实例导致哈希链断裂
        actual_dir = prepared["run_dir"]
        store = prepared["store"]
        audit = prepared["audit"]
        audit.append("PipelineCompleted", source="RunService", run_id=run_id)

        # 真实运行适配器探测：按目标平台选择 Web 浏览器或 Godot 无头运行时
        platforms = [str(p).lower() for p in (intent.target_platforms or ["web"])]
        use_godot = any("godot" in p for p in platforms)
        if use_godot:
            from pipeline.godot_runtime_adapter import GodotRuntimeAdapter

            adapter = GodotRuntimeAdapter()
            pre = adapter.preflight("godot")
            runtime_artifact = result.get("godot_dir")
        else:
            adapter = BrowserRuntimeAdapter()
            pre = adapter.preflight("web")
            runtime_artifact = result.get("game_file")

        game_file = result.get("game_file")
        evidence_observations = []
        evidence_errors = []
        evidence_metrics: Dict[str, Any] = {"collected": False}
        runtime_facts = {"adapter": adapter.name, "adapter_version": adapter.version,
                         "target": "godot" if use_godot else "web"}
        runtime_status = RuntimeStatus.NEEDS_RUNTIME_TOOL
        scenario_results: Dict[str, Any] = {}

        if pre.get("can_launch") and runtime_artifact and Path(runtime_artifact).exists():
            session = adapter.launch(Path(runtime_artifact))
            adapter.run_scenarios(session)
            ev_data = adapter.collect_evidence(session)
            adapter.close(session)

            runtime_facts.update(ev_data.get("runtime_facts", {}))
            evidence_metrics = dict(ev_data.get("metrics") or {"collected": False})
            evidence_errors.extend(ev_data.get("errors", []))
            runtime_status = ev_data.get("status", RuntimeStatus.FAIL)
            scenario_results = dict(ev_data.get("scenarios") or {})
            evidence_observations.append({
                "scenario": "browser_runtime_scenarios",
                "status": runtime_status,
                "scenarios": scenario_results
            })
        else:
            reason = pre.get("reason") or pre.get("driver_reason") or "运行工具缺失或构建文件未就绪"
            evidence_errors.append({"code": "RUNTIME_TOOL_MISSING", "message": reason})
            evidence_observations.append({
                "scenario": "runtime_boot",
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "reason": reason
            })

        artifact_refs = store.list_refs()
        evidence = EvidencePack(
            run_id=run_id,
            target="web" if "web" in intent.genre.lower() else "universal",
            observations=evidence_observations,
            references=artifact_refs,
            metrics=evidence_metrics,
            environment=runtime_facts,
            errors=evidence_errors
        )
        evidence_ref = store.put_json("EvidencePack", evidence.to_dict(), artifact_id=evidence.evidence_id, producer_capability="runtime.evidence")

        gate_engine = prepared["gate_engine"]
        # G3: 构建制品必须存在且内容有效，仅「文件存在」不足以放行
        build_ok, build_reasons = self._validate_build_artifact(game_file)
        g3 = gate_engine.evaluate("G3", passed=build_ok, evidence_refs=[evidence_ref.artifact_id], reason_codes=build_reasons)

        # G4: 必须同时满足真实运行 PASS 且指标为真实采集，缺一即为未验证
        g4_pass = runtime_status == RuntimeStatus.PASS and bool(evidence_metrics.get("collected"))
        g4_reasons = []
        if runtime_status != RuntimeStatus.PASS:
            g4_reasons.append(f"runtime_{str(runtime_status).lower()}")
        if not evidence_metrics.get("collected"):
            g4_reasons.append("runtime_metrics_not_collected")
        g4 = gate_engine.evaluate("G4", passed=g4_pass, evidence_refs=[evidence_ref.artifact_id], reason_codes=g4_reasons)

        # G5: 证据与工件完整性核验
        g5 = gate_engine.evaluate_evidence(evidence, gate_id="G5")

        all_decisions = [prepared["decisions"][0], prepared["decisions"][1], prepared["decisions"][2], g3, g4, g5]
        # G6: Preview 候选门禁，只有 G0-G5 全 PASS 才允许提升
        g6 = gate_engine.evaluate_release_gate("G6", all_decisions)
        all_decisions.append(g6)
        audit.append("GatesEvaluated", gates=[d.decision_id for d in all_decisions])

        verified_scenarios = sorted(k for k, v in scenario_results.items() if v.get("status") == RuntimeStatus.PASS)
        unverified_scenarios = sorted(k for k in scenario_results if k not in verified_scenarios)

        # G0-G5 全部通过后，自动形成 G6 Preview 候选清单
        release_manifest = None
        release_eligible = False
        if all(d.result == "PASS" for d in all_decisions):
            release_svc = ReleaseService(store)
            candidate_ref = next((r for r in artifact_refs if "index.html" in r.relative_path), artifact_refs[0] if artifact_refs else None)
            if candidate_ref:
                try:
                    rel_man = release_svc.create_candidate(
                        channel="preview",
                        candidate_artifact=candidate_ref,
                        intent_ref=intent.intent_id,
                        spec_ref=prepared["spec"].spec_id,
                        workflow_ref=prepared["plan"].plan_id,
                        evidence_ref=evidence_ref.artifact_id,
                        decisions=[d.to_dict() for d in all_decisions]
                    )
                    release_manifest = rel_man.to_dict()
                    release_eligible = True
                except Exception as exc:
                    release_error = str(exc)
                    audit.append("ReleaseCandidateFailed", run_id=run_id, error=release_error)
                    evidence_errors.append({"code": "RELEASE_CANDIDATE_FAILED", "message": release_error})

        result.update({
            "contract_version": "1.0",
            "run_id": run_id,
            "intent_id": intent.intent_id,
            "spec_id": prepared["spec"].spec_id,
            "plan_id": prepared["plan"].plan_id,
            "run_dir": str(actual_dir),
            "artifact_integrity": store.verify_all(),
            "evidence_pack_id": evidence.evidence_id,
            "gate_decisions": [d.to_dict() for d in all_decisions],
            "verification_coverage": {
                "verified_scenarios": verified_scenarios,
                "unverified_scenarios": unverified_scenarios,
                "metrics_collected": bool(evidence_metrics.get("collected")),
            },
            "release_eligible": release_eligible,
            "release_manifest": release_manifest,
            "status": "preview_ready" if release_eligible else "run_completed"
        })
        return result

    @staticmethod
    def _validate_build_artifact(game_file: Optional[str]) -> tuple[bool, list]:
        """G3 构建制品内容校验：存在、可读、非空、具备可运行页面结构。"""
        if not game_file:
            return False, ["build_artifact_missing"]
        path = Path(game_file)
        if not path.is_file():
            return False, ["build_artifact_missing"]
        try:
            raw = path.read_bytes()
        except OSError:
            return False, ["build_artifact_unreadable"]
        if not raw:
            return False, ["build_artifact_empty"]

        reasons = []
        text = raw.decode("utf-8", errors="ignore").lower()
        if "<html" not in text and "<!doctype" not in text:
            reasons.append("build_artifact_not_html_document")
        if "<canvas" not in text and "<script" not in text:
            reasons.append("build_artifact_missing_canvas_or_script")
        return (not reasons), reasons

    def run_legacy_pipeline(self, intent: GameIntent, **kwargs: Any) -> Dict[str, Any]:
        return self.execute_run(intent, **kwargs)

    def create_game(self, **kwargs: Any) -> Dict[str, Any]:
        intent = self.create_intent(**kwargs)
        return self.execute_run(intent, **kwargs)

    def _resolve_run_dir(self, run_id: str) -> Path:
        """解析运行目录，拒绝任何穿越出 output/runs 的 run_id。"""
        candidate = (self.output_dir / str(run_id)).resolve()
        safe_resolve_path(candidate, allowed_roots=[self.output_dir])
        return candidate

    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        run_dir = self._resolve_run_dir(run_id)
        if not run_dir.is_dir():
            raise FileNotFoundError(run_id)
        store = ArtifactStore(run_dir)
        store_path = run_dir / "audit"
        return {
            "run_id": run_dir.name,
            "status": "SEALED" if store.sealed else "OPEN",
            "artifact_count": len(store.list_refs()),
            "integrity": store.verify_all(),
            "audit": AuditLog(run_dir).verify() if store_path.is_dir() else {"passed": True, "events": 0, "errors": []},
        }

    # 会产出可分发包的命令：必须挂接到已通过门禁的运行，杜绝旁路发布
    GATED_TOOLS = ("distribute", "submit", "wechat-pack")

    def dispatch_tool(self, tool_id: str, table: Dict[str, Any], args: Any, fallback: Any = None) -> int:
        """CLI 旧工具的统一派发入口：写入审计链，并在发布类命令上强制门禁。

        所有命令（含纯咨询类）都经此入口，保证任何一次调用都能被溯源；
        GATED_TOOLS 中的命令额外校验 ReleaseManifest，缺证一律拒绝执行。
        """
        handler = table.get(tool_id)
        if handler is None:
            if fallback:
                fallback()
            return 1

        audit = AuditLog(self.workspace / "output" / "tool_runs")
        params = {k: v for k, v in vars(args).items() if k != "command"}
        audit.append("ToolInvoked", tool_id=tool_id, params=params)

        if tool_id in self.GATED_TOOLS:
            blocked = self._check_tool_release_gate(tool_id, args)
            if blocked:
                audit.append("ToolBlocked", tool_id=tool_id, reason=blocked)
                print(f"[BLOCKED] {blocked}")
                return 2

        started = time.time()
        try:
            rc = handler(args)
        except Exception as exc:
            audit.append("ToolFailed", tool_id=tool_id, error=f"{exc.__class__.__name__}: {exc}")
            raise
        audit.append("ToolCompleted", tool_id=tool_id, duration_ms=round((time.time() - started) * 1000))
        # 诚实传播命令真实退出码：成功=0；命令自行返回非 0 表示阻断/未通过/环境缺口
        # （如 W8 playtest 的 NEEDS_RUNTIME_TOOL=4），绝不把失败粉饰为 0。
        return int(rc) if rc is not None else 0

    def check_release_gate(self, tool_id: str, run_id: str) -> str:
        """发布类动作的门禁校验（供 CLI / HTTP / MCP 等所有入口复用）。

        返回空串表示放行，非空为阻塞原因。任何入口不得绕过此校验直接产出可分发货。
        """
        run_id = str(run_id or "").strip()
        if not run_id:
            return (f"{tool_id} 属于发布类命令，必须用 --run-id 挂接到某次已通过门禁的运行，"
                    "禁止绕过 ReleaseManifest 直接分发")
        try:
            run_dir = self._resolve_run_dir(run_id)
        except SecurityGuardError:
            return f"非法 run_id: {run_id}"
        if not run_dir.is_dir():
            return f"run 不存在: {run_id}"
        manifests = self._read_payloads(ArtifactStore(run_dir), "ReleaseManifest")
        if not manifests:
            return f"run {run_id} 没有 ReleaseManifest，尚未通过发布门禁，禁止分发"
        return ""

    def _check_tool_release_gate(self, tool_id: str, args: Any) -> str:
        return self.check_release_gate(tool_id, getattr(args, "run_id", ""))

    def list_artifacts(self, run_id: str) -> list[Dict[str, Any]]:
        run_dir = self._resolve_run_dir(run_id)
        return [ref.to_dict() for ref in ArtifactStore(run_dir).list_refs()]

    ORPHAN_RUN_STATES = ("no_artifact_index", "corrupt_artifact_index", "prepared_only", "intent_only")

    @staticmethod
    def classify_run(run_dir: Path) -> str:
        """按工件链完整度给 run 分类。

        prepared_only / intent_only 从未产生 EvidencePack，无法溯源任何验证结论，
        属于孤儿目录；verified / released 才是完整链路。
        """
        index = Path(run_dir) / "artifacts" / "index.json"
        if not index.is_file():
            return "no_artifact_index"
        try:
            data = json.loads(index.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return "corrupt_artifact_index"
        types = {a.get("artifact_type") for a in data.get("artifacts", {}).values()}
        if "ReleaseManifest" in types:
            return "released"
        if "EvidencePack" in types:
            return "verified"
        if "GateDecision" in types:
            return "prepared_only"
        return "intent_only"

    def prune_runs(self, keep_last: int = 8, dry_run: bool = True) -> Dict[str, Any]:
        """清理孤儿与过期 run 目录。

        孤儿 = 从未产生 EvidencePack 的 run（无验证链可溯源），无条件清理；
        其余按保留最近 keep_last 个完整链路 run 处理。dry_run=True 时只报告不删除。
        """
        if not self.output_dir.is_dir():
            return {"removed": [], "kept": 0, "dry_run": dry_run, "reason": "output_dir_missing"}

        classified = []
        for child in self.output_dir.iterdir():
            if not child.is_dir():
                continue
            classified.append((child.stat().st_mtime, child.name, self.classify_run(child)))

        orphans = [name for _, name, state in classified if state in self.ORPHAN_RUN_STATES]
        complete = sorted(
            (mtime, name) for mtime, name, state in classified if state not in self.ORPHAN_RUN_STATES
        )
        keep_names = {name for _, name in complete[-keep_last:]} if keep_last > 0 else set()
        expired = [name for _, name in complete if name not in keep_names]
        removed = sorted(orphans + expired)

        if not dry_run:
            for name in removed:
                target = (self.output_dir / name).resolve()
                # 只允许删除 output/runs 的直接子目录，杜绝任何越界删除
                safe_resolve_path(target, allowed_roots=[self.output_dir])
                if target.parent != self.output_dir.resolve():
                    raise SecurityGuardError(f"拒绝删除非 run 目录: {target}")
                shutil.rmtree(target)

        return {
            "dry_run": dry_run,
            "total": len(classified),
            "keep_last": keep_last,
            "removed": removed,
            "removed_count": len(removed),
            "kept": sorted(keep_names),
            "orphans": sorted(orphans),
            "expired": sorted(expired),
        }

    def promote_to_staging(self, run_id: str, approval: Dict[str, Any]) -> Dict[str, Any]:
        """把 Preview 候选晋升到 Staging：必须真的访问到 staging 部署，且由 qa_manager 批准。

        未配置 STAGING_BASE_URL 或访问不通过时一律拒绝晋升，不做「未部署即通过」的假设。
        """
        run_dir = self._resolve_run_dir(run_id)
        if not run_dir.is_dir():
            raise FileNotFoundError(run_id)
        store = ArtifactStore(run_dir)
        manifest_payloads = self._read_payloads(store, "ReleaseManifest")
        preview = next((m for m in manifest_payloads if m.get("release_channel") == "preview"), None)
        if preview is None:
            raise ReleaseBlockedError("该运行没有 Preview 候选，不能直接晋升到 Staging")
        if (approval or {}).get("role") != "qa_manager" or not approval.get("approved"):
            raise ReleaseBlockedError("Staging 晋升需要 qa_manager 显式批准")

        smoke = StagingSmoke.probe()
        audit = AuditLog(run_dir)
        audit.append("StagingSmoke", run_id=run_id, status=smoke["status"], observed=smoke.get("observed"))
        if smoke["status"] != "PASS":
            raise ReleaseBlockedError("Staging 冒烟未通过: " + "; ".join(smoke["errors"]))

        decisions = self._latest_by_gate(self._read_payloads(store, "GateDecision"))
        manifest = ReleaseService(store).create_candidate(
            channel="staging",
            candidate_artifact=ArtifactRef(**preview["candidate_artifact"]),
            intent_ref=preview["intent_ref"],
            spec_ref=preview["spec_ref"],
            workflow_ref=preview["workflow_ref"],
            evidence_ref=preview["evidence_ref"],
            decisions=decisions,
            capability_versions=preview.get("capability_versions", {}),
            approval=approval,
        )
        audit.append("StagingPromotionApproved", run_id=run_id, approver=approval.get("identity"))
        return self._promotion_summary(manifest, staging_smoke=smoke)

    def rollback(self, run_id: str, reason: str, actor: Dict[str, Any]) -> Dict[str, Any]:
        """发布回滚：把该运行已生效的发布标记为 rolled_back 并留审计。

        注意：真实回滚动作（下架/切流/还原上一版本）依赖部署目标适配器；
        本方法保证的是「回滚决策与证据」可追溯，不谎称已执行远端操作。
        """
        run_dir = self._resolve_run_dir(run_id)
        if not run_dir.is_dir():
            raise FileNotFoundError(run_id)
        store = ArtifactStore(run_dir)
        manifests = self._read_payloads(store, "ReleaseManifest")
        active = [m for m in manifests if m.get("release_status") in ("staged", "approved")]
        if not active:
            raise ReleaseBlockedError("该运行没有已生效的 Staging/Production 发布，无可回滚对象")

        audit = AuditLog(run_dir)
        record = {
            "run_id": run_dir.name,
            "rolled_back": [m.get("release_id") for m in active],
            "channels": sorted({m.get("release_channel") for m in active}),
            "reason": str(reason)[:500],
            "actor": actor,
        }
        audit.append("ReleaseRolledBack", **record)
        return {"status": "rolled_back", **record}

    def promote_to_production(self, run_id: str, approval: Dict[str, Any]) -> Dict[str, Any]:
        """把已通过 G0-G6 的运行提升为生产候选。

        生产提升必须经 release_manager 显式批准；缺少审批或 G7 未通过一律
        抛出 ReleaseBlockedError，绝不用 Preview 资格替代生产审批。
        """
        run_dir = self._resolve_run_dir(run_id)
        if not run_dir.is_dir():
            raise FileNotFoundError(run_id)
        store = ArtifactStore(run_dir)
        gate_engine = GateEngine(store)
        # 同一门禁可能有多条历史裁决（例如上一次提升审批不合规），只取最新一条；
        # G7 本身由本次调用重新裁决，不得把上一次的 G7 当成自己的前置证据。
        decisions = self._latest_by_gate(self._read_payloads(store, "GateDecision"), exclude=("G7",))
        manifest_payloads = self._read_payloads(store, "ReleaseManifest")
        preview = next((m for m in manifest_payloads if m.get("release_channel") == "preview"), None)
        if preview is None:
            raise ReleaseBlockedError("该运行没有 Preview 候选，不能直接提升到生产")
        # Preview -> Staging -> Production：没有 staging 冒烟证据不得直接进生产
        if not any(m.get("release_channel") == "staging" and m.get("release_status") == "staged"
                   for m in manifest_payloads):
            raise ReleaseBlockedError("缺少 Staging 晋升记录，必须先通过 Staging 冒烟才能提升到生产")

        g7 = gate_engine.evaluate_release_gate("G7", decisions, approval=approval)
        if g7.result != "PASS":
            raise ReleaseBlockedError("G7 未通过: " + ", ".join(g7.reason_codes))

        all_decisions = decisions + [g7.to_dict()]
        audit = AuditLog(run_dir)
        candidate_ref = ArtifactRef(**preview["candidate_artifact"])
        manifest = ReleaseService(store).create_candidate(
            channel="production",
            candidate_artifact=candidate_ref,
            intent_ref=preview["intent_ref"],
            spec_ref=preview["spec_ref"],
            workflow_ref=preview["workflow_ref"],
            evidence_ref=preview["evidence_ref"],
            decisions=all_decisions,
            capability_versions=preview.get("capability_versions", {}),
            approval=approval,
        )
        audit.append("ProductionPromotionApproved", run_id=run_id, approver=approval.get("identity"))
        return self._promotion_summary(manifest)

    @staticmethod
    def _promotion_summary(manifest: Any, **extra: Any) -> Dict[str, Any]:
        payload = manifest.to_dict()
        return {"run_id": payload["run_id"], "channel": payload["release_channel"],
                "release_status": payload["release_status"], "release_id": payload["artifact_id"],
                "manifest": payload, **extra}

    @staticmethod
    def _latest_by_gate(payloads: list[Dict[str, Any]], exclude: tuple[str, ...] = ()) -> list[Dict[str, Any]]:
        latest: Dict[str, Dict[str, Any]] = {}
        for payload in payloads:
            gate_id = payload.get("gate_id")
            if not gate_id or gate_id in exclude:
                continue
            latest[gate_id] = payload
        return list(latest.values())

    @staticmethod
    def _read_payloads(store: ArtifactStore, artifact_type: str) -> list[Dict[str, Any]]:
        payloads = []
        for ref in store.list_refs():
            if ref.artifact_type != artifact_type:
                continue
            try:
                payloads.append(json.loads(store.read_bytes(ref.artifact_id).decode("utf-8")))
            except (ArtifactIntegrityError, ValueError):
                continue
        return payloads


run_service = RunService()
