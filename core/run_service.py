"""Unified application service for CLI, HTTP, and MCP callers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from core.audit_log import AuditLog
from core.artifact_store import ArtifactStore
from core.contracts import EvidencePack, ArtifactRef, GameIntent
from core.workflow_orchestrator import WorkflowOrchestrator
from core.gate_engine import GateEngine


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
            llm_model=kwargs.get("llm_model")
        )
        run_id = result.get("run_id") or intent.run_id
        actual_dir = self.workspace / "output" / "runs" / run_id
        actual_store = ArtifactStore(actual_dir)
        actual_audit = AuditLog(actual_dir)
        actual_audit.append("PipelineCompleted", source="RunService", run_id=run_id)

        # 真实运行适配器探测 (BrowserRuntimeAdapter)
        game_file = result.get("game_file")
        adapter = BrowserRuntimeAdapter()
        pre = adapter.preflight("web")

        evidence_observations = []
        evidence_errors = []
        evidence_metrics = {"console_error_count": 0, "page_error_count": 0, "network_failure_count": 0}
        runtime_facts = {"adapter": adapter.name}
        runtime_status = RuntimeStatus.NEEDS_RUNTIME_TOOL

        if pre.get("can_launch") and game_file and Path(game_file).exists():
            session = adapter.launch(Path(game_file))
            sc_res = adapter.run_scenarios(session)
            ev_data = adapter.collect_evidence(session)
            adapter.close(session)

            runtime_facts.update(ev_data.get("runtime_facts", {}))
            evidence_metrics.update(ev_data.get("metrics", {}))
            evidence_errors.extend(ev_data.get("errors", []))
            runtime_status = ev_data.get("status", RuntimeStatus.FAIL)
            evidence_observations.append({
                "scenario": "browser_runtime_scenarios",
                "status": runtime_status,
                "scenarios": ev_data.get("scenarios", {})
            })
        else:
            reason = pre.get("reason", "运行工具缺失或构建文件未就绪")
            evidence_errors.append({"code": "RUNTIME_TOOL_MISSING", "message": reason})
            evidence_observations.append({
                "scenario": "runtime_boot",
                "status": RuntimeStatus.NEEDS_RUNTIME_TOOL,
                "reason": reason
            })

        artifact_refs = actual_store.list_refs()
        evidence = EvidencePack(
            run_id=run_id,
            target="web" if "web" in intent.genre.lower() else "universal",
            observations=evidence_observations,
            references=artifact_refs,
            metrics=evidence_metrics,
            environment=runtime_facts,
            errors=evidence_errors
        )
        evidence_ref = actual_store.put_json("EvidencePack", evidence.to_dict(), artifact_id=evidence.evidence_id, producer_capability="runtime.evidence")

        gate_engine = GateEngine(actual_store)
        # G3: 构建制品存在且有效
        build_pass = bool(game_file and Path(game_file).exists())
        g3 = gate_engine.evaluate("G3", passed=build_pass, evidence_refs=[evidence_ref.artifact_id], reason_codes=[] if build_pass else ["build_artifact_missing"])

        # G4: 真实运行场景验证
        g4_pass = (runtime_status == RuntimeStatus.PASS)
        g4_reasons = [] if g4_pass else [f"runtime_{runtime_status.lower()}"]
        g4 = gate_engine.evaluate("G4", passed=g4_pass, evidence_refs=[evidence_ref.artifact_id], reason_codes=g4_reasons)

        # G5: 证据与工件完整性核验
        g5 = gate_engine.evaluate_evidence(evidence, gate_id="G5")

        all_decisions = [prepared["decisions"][0], prepared["decisions"][1], prepared["decisions"][2], g3, g4, g5]
        actual_audit.append("GatesEvaluated", gates=[d.decision_id for d in all_decisions])

        # G0-G5 全部通过后，自动形成 G6 Preview 候选清单
        release_manifest = None
        release_eligible = False
        if all(d.result == "PASS" for d in all_decisions):
            release_svc = ReleaseService(actual_store)
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
                except Exception:
                    pass

        result.update({
            "contract_version": "1.0",
            "run_id": run_id,
            "intent_id": intent.intent_id,
            "spec_id": prepared["spec"].spec_id,
            "plan_id": prepared["plan"].plan_id,
            "run_dir": str(actual_dir),
            "artifact_integrity": actual_store.verify_all(),
            "evidence_pack_id": evidence.evidence_id,
            "gate_decisions": [d.to_dict() for d in all_decisions],
            "release_eligible": release_eligible,
            "release_manifest": release_manifest,
            "status": "preview_ready" if release_eligible else "run_completed"
        })
        return result

    def run_legacy_pipeline(self, intent: GameIntent, **kwargs: Any) -> Dict[str, Any]:
        return self.execute_run(intent, **kwargs)

    def create_game(self, **kwargs: Any) -> Dict[str, Any]:
        intent = self.create_intent(**kwargs)
        return self.execute_run(intent, **kwargs)

    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        run_dir = self.output_dir / run_id
        if not run_dir.is_dir():
            raise FileNotFoundError(run_id)
        store = ArtifactStore(run_dir)
        return {
            "run_id": run_id,
            "status": "SEALED" if store.sealed else "OPEN",
            "artifact_count": len(store.list_refs()),
            "integrity": store.verify_all(),
        }

    def list_artifacts(self, run_id: str) -> list[Dict[str, Any]]:
        run_dir = self.output_dir / run_id
        return [ref.to_dict() for ref in ArtifactStore(run_dir).list_refs()]


run_service = RunService()
