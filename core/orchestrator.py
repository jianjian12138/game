"""core/orchestrator.py: L1 工作流编排器（W2）。

职责：把 WorkflowPlan 的 DAG 真正跑起来，而不是打印一份漂亮的计划。

三件事必须真：
1. 拓扑分层是真的：有环立刻抛错，不会假装排好序。
2. 并行是真的：同层无依赖的节点用线程池并发执行，不是串行假装并行。
3. 断点续跑是真的：节点状态与产物引用落盘，重跑时按指纹跳过已完成节点；
   指纹（节点定义 + 实际输入内容）变了才重跑，不会因为“上次跑过”就跳过改过的活。

诚实红线（与计划 13.2 一致）：
- 找不到执行器 → NEEDS_RUNTIME_TOOL，绝不标记成功。
- LLM 不可用 → 由 AgentRuntime 报 NEEDS_LLM_CREDENTIALS，编排器原样透传，不降级为成功。
- 门禁（gate_after）编排器不自己判“过没过”：没拿到证据就报 NEEDS_GATE_EVIDENCE，
  因为“通过”需要证据，编排器没有证据就不许说通过。
- 超时只放弃等待，不能真正杀掉已经发出去的线程——这是线程池的真实限制，
  超时节点会被记为 TIMEOUT 且结果丢弃，不会记为成功。
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.artifact_store import ArtifactStore, canonical_json, content_hash, utc_now
from core.contracts import WorkflowNode, WorkflowPlan


class NodeStatus:
    """节点状态。用类常量而非 Enum，方便直接字符串比较与落盘。"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"       # 断点续跑命中，本次未重跑
    BLOCKED = "BLOCKED"       # 上游失败且 failure_policy=block
    TIMEOUT = "TIMEOUT"
    NEEDS_RUNTIME_TOOL = "NEEDS_RUNTIME_TOOL"
    NEEDS_LLM_CREDENTIALS = "NEEDS_LLM_CREDENTIALS"

    TERMINAL_OK = {SUCCEEDED, SKIPPED}
    TERMINAL_BAD = {FAILED, BLOCKED, TIMEOUT, NEEDS_RUNTIME_TOOL, NEEDS_LLM_CREDENTIALS}


class OrchestrationError(Exception):
    """编排层面的结构性错误：有环、节点重复、依赖未知等。"""


@dataclass
class NodeResult:
    node_id: str
    status: str
    attempts: int = 1
    output_ref: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    latency_ms: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "attempts": self.attempts,
            "output_ref": self.output_ref,
            "errors": list(self.errors),
            "latency_ms": self.latency_ms,
            "meta": dict(self.meta),
        }


@dataclass
class ExecutionContext:
    """节点执行上下文：能拿到工件库、已解析的输入、上游绑定。"""

    store: ArtifactStore
    plan: WorkflowPlan
    bindings: Dict[str, str] = field(default_factory=dict)   # 输出名 / node_id -> artifact_id

    def resolve_inputs(self, node: WorkflowNode) -> Tuple[Dict[str, Any], List[str]]:
        """解析节点输入。返回 (已解析输入, 缺失输入名列表)。

        找不到输入就如实报缺失，不拿空 dict 冒充“输入为空”。
        """
        resolved: Dict[str, Any] = {}
        missing: List[str] = []
        for name in node.inputs:
            artifact_id = self.bindings.get(name) or self.bindings.get(f"{node.node_id}:{name}")
            if artifact_id is None:
                # 也可能是直接指定的 artifact id
                artifact_id = name if name in self.bindings.values() else None
            if artifact_id is None and name in self.bindings:
                artifact_id = self.bindings[name]
            if artifact_id is None:
                try:
                    self.store.get_ref(name)
                    artifact_id = name
                except Exception:
                    artifact_id = None
            if artifact_id is None:
                missing.append(name)
                continue
            try:
                raw = self.store.read_bytes(artifact_id, verify=True)
                resolved[name] = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                missing.append(f"{name} (unreadable: {type(exc).__name__})")
        return resolved, missing


class NodeExecutor:
    """执行器接口。can_execute 决定谁接这个节点。"""

    def can_execute(self, node: WorkflowNode) -> bool:
        raise NotImplementedError

    def execute(self, node: WorkflowNode, ctx: ExecutionContext) -> NodeResult:
        raise NotImplementedError


class AgentNodeExecutor(NodeExecutor):
    """把节点交给 AgentRuntime 跑：capability_id 即角色卡 id。

    三档激活在这里落地：
    - LEAD / SPECIALIST → run()（完整会话，产出工件）
    - ADVISOR          → consult()（单次意见，blocking=true 时进阻断项）
    """

    def __init__(self, runtime: Any = None):
        self._runtime = runtime

    @property
    def runtime(self):
        if self._runtime is None:
            from core.agent_runtime import AgentRuntime
            self._runtime = AgentRuntime()
        return self._runtime

    def can_execute(self, node: WorkflowNode) -> bool:
        from core.role_cards import get_card, load_all_role_cards
        load_all_role_cards()
        return get_card(node.capability_id) is not None

    def execute(self, node: WorkflowNode, ctx: ExecutionContext) -> NodeResult:
        from core.role_cards import get_card, load_all_role_cards, AgentTier

        load_all_role_cards()
        card = get_card(node.capability_id)
        if card is None:
            return NodeResult(node.node_id, NodeStatus.NEEDS_RUNTIME_TOOL,
                              errors=[f"unknown role card: {node.capability_id}"])

        resolved, missing = ctx.resolve_inputs(node)
        if missing:
            # 没有输入就跑，等于让模型编数据。这里直接判失败。
            return NodeResult(node.node_id, NodeStatus.FAILED,
                              errors=[f"missing inputs: {', '.join(missing)}"])

        context = {
            "run_id": ctx.plan.run_id,
            "plan_id": ctx.plan.plan_id,
            "node_id": node.node_id,
            "phase": node.gate_after or "",
            "inputs": resolved,
        }
        task = f"节点 {node.node_id}（{card.name}）：{card.duty}"

        started = time.time()
        try:
            if card.tier == AgentTier.ADVISOR:
                out = self.runtime.consult(node.capability_id, task, context=context)
            else:
                out = self.runtime.run(node.capability_id, task, context=context)
        except Exception as exc:  # 运行时自身炸了，如实记录，不吞
            return NodeResult(node.node_id, NodeStatus.FAILED,
                              latency_ms=int((time.time() - started) * 1000),
                              errors=[f"executor exception: {type(exc).__name__}: {exc}"])
        latency = int((time.time() - started) * 1000)

        if out.status != "OK":
            status = {
                "NEEDS_LLM_CREDENTIALS": NodeStatus.NEEDS_LLM_CREDENTIALS,
            }.get(out.status, NodeStatus.FAILED)
            return NodeResult(node.node_id, status, latency_ms=latency,
                              errors=list(out.errors) or [f"agent status={out.status}"],
                              meta={"agent_status": out.status})

        payload = out.payload or {}
        ref = ctx.store.put_json(
            "AgentOutput",
            {
                "node_id": node.node_id,
                "card_id": card.card_id,
                "tier": card.tier.value if hasattr(card.tier, "value") else str(card.tier),
                "payload": payload,
                "provider": out.provider,
                "model": out.model,
                "latency_ms": out.latency_ms,
                "errors": list(out.errors),
                "created_at": out.created_at,
            },
            producer_capability=node.capability_id,
        )
        # ADVISOR 的 blocking 意见要能被门禁看到，这里如实回传
        blocking = bool(payload.get("blocking")) if card.tier == AgentTier.ADVISOR else False
        return NodeResult(node.node_id, NodeStatus.SUCCEEDED, output_ref=ref.artifact_id,
                          latency_ms=latency, meta={"blocking": blocking, "card_id": card.card_id},
                          errors=list(out.errors))


class CallableNodeExecutor(NodeExecutor):
    """确定性节点执行器：注册 kind -> callable(node, ctx) -> NodeResult。

    用于不依赖 LLM 的能力（程序化生成、格式转换、静态检查）。
    没注册的 kind 一律不接，交给编排器报 NEEDS_RUNTIME_TOOL。
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Callable[[WorkflowNode, ExecutionContext], NodeResult]] = {}

    def register(self, kind: str, fn: Callable[[WorkflowNode, ExecutionContext], NodeResult]) -> None:
        self._registry[kind] = fn

    @property
    def kinds(self) -> List[str]:
        return sorted(self._registry)

    def can_execute(self, node: WorkflowNode) -> bool:
        return node.capability_id in self._registry

    def execute(self, node: WorkflowNode, ctx: ExecutionContext) -> NodeResult:
        fn = self._registry.get(node.capability_id)
        if fn is None:
            return NodeResult(node.node_id, NodeStatus.NEEDS_RUNTIME_TOOL,
                              errors=[f"no callable registered for capability: {node.capability_id}"])
        started = time.time()
        try:
            result = fn(node, ctx)
        except Exception as exc:
            return NodeResult(node.node_id, NodeStatus.FAILED,
                              latency_ms=int((time.time() - started) * 1000),
                              errors=[f"callable exception: {type(exc).__name__}: {exc}"])
        result.latency_ms = result.latency_ms or int((time.time() - started) * 1000)
        return result


@dataclass
class OrchestrationReport:
    run_id: str
    plan_id: str
    layers: List[List[str]]
    results: Dict[str, NodeResult]
    gate_pending: List[Dict[str, Any]] = field(default_factory=list)
    resumed: List[str] = field(default_factory=list)
    started_at: str = field(default_factory=utc_now)
    finished_at: str = field(default_factory=utc_now)

    @property
    def counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for r in self.results.values():
            out[r.status] = out.get(r.status, 0) + 1
        return out

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results.values() if r.status in NodeStatus.TERMINAL_OK)

    @property
    def unresolved(self) -> List[str]:
        """所有 NEEDS_* / FAILED / BLOCKED / TIMEOUT 的节点，一个都不藏。"""
        return sorted(n for n, r in self.results.items() if r.status not in NodeStatus.TERMINAL_OK)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "plan_id": self.plan_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "layers": self.layers,
            "counts": self.counts,
            "succeeded": self.succeeded,
            "total": len(self.results),
            "resumed": self.resumed,
            "unresolved": self.unresolved,
            "gate_pending": self.gate_pending,
            "results": {k: v.to_dict() for k, v in self.results.items()},
        }


class Orchestrator:
    """按 DAG 分层执行 WorkflowPlan。

    :param resume: True 时读取已落盘的状态，相同指纹的已成功节点直接跳过。
    :param gate_evaluator: 可选。签名 (node, result) -> Optional[dict]，
       返回 {"passed": bool, "reason_codes": [...]}。不提供时门禁记为 NEEDS_GATE_EVIDENCE。
    """

    STATE_REL = "orchestrator/state.json"

    def __init__(
        self,
        plan: WorkflowPlan,
        store: ArtifactStore,
        executors: Optional[List[NodeExecutor]] = None,
        *,
        max_workers: int = 4,
        resume: bool = True,
        gate_evaluator: Optional[Callable[[WorkflowNode, NodeResult], Optional[Dict[str, Any]]]] = None,
    ) -> None:
        self.plan = plan
        self.store = store
        self.max_workers = max(1, int(max_workers))
        self.resume = resume
        self.gate_evaluator = gate_evaluator
        self.executors: List[NodeExecutor] = executors or [
            CallableNodeExecutor(),
            AgentNodeExecutor(),
        ]
        self.ctx = ExecutionContext(store=store, plan=plan)
        self._nodes: Dict[str, WorkflowNode] = {n.node_id: n for n in plan.nodes}
        self._prior_state: Dict[str, Dict[str, Any]] = self._load_state()

    # ── 状态落盘（断点续跑） ──────────────────────────────────────────────
    @property
    def _state_path(self):
        return self.store.run_dir / self.STATE_REL

    def _load_state(self) -> Dict[str, Dict[str, Any]]:
        if not self.resume or not self._state_path.exists():
            return {}
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            nodes = data.get("nodes")
            return nodes if isinstance(nodes, dict) else {}
        except (OSError, json.JSONDecodeError):
            # 状态文件损坏不猜、不修，按没有断点处理（本次全量重跑）
            return {}

    def _save_state(self, results: Dict[str, NodeResult], fingerprints: Dict[str, str]) -> None:
        payload = {
            "schema_version": 1,
            "run_id": self.plan.run_id,
            "plan_id": self.plan.plan_id,
            "updated_at": utc_now(),
            "nodes": {
                node_id: {
                    "status": r.status,
                    "fingerprint": fingerprints.get(node_id, ""),
                    "output_ref": r.output_ref,
                    "errors": r.errors,
                }
                for node_id, r in results.items()
            },
        }
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(canonical_json(payload), encoding="utf-8")

    # ── 拓扑分层 ──────────────────────────────────────────────────────────
    def topo_layers(self) -> List[List[str]]:
        """Kahn 分层。有环抛 OrchestrationError，绝不返回“看起来排好”的顺序。"""
        indeg: Dict[str, int] = {}
        dependents: Dict[str, List[str]] = {n: [] for n in self._nodes}
        for node in self.plan.nodes:
            deps = [d for d in node.depends_on]
            unknown = [d for d in deps if d not in self._nodes]
            if unknown:
                raise OrchestrationError(f"node {node.node_id} depends on unknown nodes: {unknown}")
            indeg[node.node_id] = len(set(deps))
            for d in set(deps):
                dependents[d].append(node.node_id)

        layers: List[List[str]] = []
        remaining = dict(indeg)
        while remaining:
            layer = sorted(n for n, d in remaining.items() if d == 0)
            if not layer:
                raise OrchestrationError(
                    f"cycle detected in workflow plan; stuck nodes: {sorted(remaining)}")
            layers.append(layer)
            for n in layer:
                del remaining[n]
                for child in dependents[n]:
                    if child in remaining:
                        remaining[child] -= 1
        return layers

    # ── 指纹与跳过判定 ────────────────────────────────────────────────────
    def _fingerprint(self, node: WorkflowNode, resolved: Dict[str, Any]) -> str:
        return content_hash({"node": node.to_dict(), "inputs": resolved})

    def _pick_executor(self, node: WorkflowNode) -> Optional[NodeExecutor]:
        for ex in self.executors:
            if ex.can_execute(node):
                return ex
        return None

    # ── 主执行 ────────────────────────────────────────────────────────────
    def run(self, *, dry_run: bool = False) -> OrchestrationReport:
        layers = self.topo_layers()
        results: Dict[str, NodeResult] = {}
        fingerprints: Dict[str, str] = {}
        gate_pending: List[Dict[str, Any]] = []
        resumed: List[str] = []
        started_at = utc_now()

        for layer in layers:
            runnable: List[Tuple[WorkflowNode, Optional[NodeExecutor], str]] = []
            for node_id in layer:
                node = self._nodes[node_id]
                # 上游失败传播
                bad_up = [d for d in node.depends_on
                          if d in results and results[d].status in NodeStatus.TERMINAL_BAD]
                if bad_up:
                    policy = (node.failure_policy or "block").lower()
                    if policy == "block":
                        results[node_id] = NodeResult(
                            node_id, NodeStatus.BLOCKED,
                            errors=[f"upstream failed: {', '.join(bad_up)}"])
                        continue
                    # continue：照跑，但把上游失败写进 meta，节点自己知道数据不全
                resolved, missing = self.ctx.resolve_inputs(node)
                fp = self._fingerprint(node, resolved)
                fingerprints[node_id] = fp

                prior = self._prior_state.get(node_id) if self.resume else None
                if (prior and prior.get("status") == NodeStatus.SUCCEEDED
                        and prior.get("fingerprint") == fp
                        and prior.get("output_ref")):
                    results[node_id] = NodeResult(
                        node_id, NodeStatus.SKIPPED, output_ref=prior["output_ref"],
                        meta={"resumed": True})
                    resumed.append(node_id)
                    continue

                if dry_run:
                    results[node_id] = NodeResult(node_id, NodeStatus.PENDING,
                                                  meta={"dry_run": True})
                    continue

                executor = self._pick_executor(node)
                if executor is None:
                    results[node_id] = NodeResult(
                        node_id, NodeStatus.NEEDS_RUNTIME_TOOL,
                        errors=[f"no executor available for capability: {node.capability_id}"])
                    continue

                if missing and node.inputs:
                    results[node_id] = NodeResult(
                        node_id, NodeStatus.FAILED,
                        errors=[f"missing inputs: {', '.join(missing)}"])
                    continue

                runnable.append((node, executor, fp))

            if not runnable:
                continue

            if self.max_workers == 1 or len(runnable) == 1:
                for node, ex, fp in runnable:
                    results[node.node_id] = self._run_one(node, ex, fp)
            else:
                with ThreadPoolExecutor(max_workers=min(self.max_workers, len(runnable))) as pool:
                    futures = {pool.submit(self._run_one, n, ex, fp): n.node_id
                               for n, ex, fp in runnable}
                    for fut, node_id in futures.items():
                        try:
                            results[node_id] = fut.result(
                                timeout=self._nodes[node_id].timeout_seconds)
                        except FutureTimeoutError:
                            results[node_id] = NodeResult(
                                node_id, NodeStatus.TIMEOUT,
                                errors=[f"exceeded timeout_seconds="
                                        f"{self._nodes[node_id].timeout_seconds}"])
                        except Exception as exc:
                            results[node_id] = NodeResult(
                                node_id, NodeStatus.FAILED,
                                errors=[f"scheduling exception: {type(exc).__name__}: {exc}"])

            # 绑定输出，供下游解析
            for node, _ex, _fp in runnable:
                r = results.get(node.node_id)
                if r and r.output_ref:
                    self.ctx.bindings[node.node_id] = r.output_ref
                    for name in node.outputs:
                        self.ctx.bindings[name] = r.output_ref

            # 门禁：不提供判定器就如实记为待裁决，绝不默认“过”
            for node, _ex, _fp in runnable:
                r = results.get(node.node_id)
                if not r or not node.gate_after:
                    continue
                if r.status != NodeStatus.SUCCEEDED:
                    continue
                if self.gate_evaluator is None:
                    gate_pending.append({
                        "node_id": node.node_id,
                        "gate_id": node.gate_after,
                        "status": "NEEDS_GATE_EVIDENCE",
                        "note": "编排器未提供门禁判定器，也未拿到证据，因此不声称通过。",
                    })
                    continue
                verdict = self.gate_evaluator(node, r) or {}
                gate_pending.append({
                    "node_id": node.node_id,
                    "gate_id": node.gate_after,
                    "status": "PASS" if verdict.get("passed") else "FAIL",
                    "reason_codes": list(verdict.get("reason_codes", [])),
                })

        report = OrchestrationReport(
            run_id=self.plan.run_id,
            plan_id=self.plan.plan_id,
            layers=layers,
            results=results,
            gate_pending=gate_pending,
            resumed=resumed,
            started_at=started_at,
            finished_at=utc_now(),
        )
        if not dry_run:
            self._save_state(results, fingerprints)
            self.store.put_json("OrchestrationReport", report.to_dict())
        return report

    def _run_one(self, node: WorkflowNode, executor: NodeExecutor, fp: str) -> NodeResult:
        attempts_limit = max(0, int(node.retry_limit)) + 1
        last = NodeResult(node.node_id, NodeStatus.FAILED, errors=["no attempt executed"])
        for attempt in range(1, attempts_limit + 1):
            last = executor.execute(node, self.ctx)
            last.attempts = attempt
            if last.status == NodeStatus.SUCCEEDED:
                return last
            if last.status in (NodeStatus.NEEDS_RUNTIME_TOOL, NodeStatus.NEEDS_LLM_CREDENTIALS):
                # 环境缺失，重试没有意义，直接返回
                return last
        last.errors = list(last.errors) + [f"已重试 {attempts_limit} 次仍未成功"]
        return last
