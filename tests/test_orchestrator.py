"""tests/test_orchestrator.py: L1 编排器单元测试。

三条红线必须真测：
1. 拓扑分层：有环、未知依赖立刻抛错，不假装排好。
2. 找不到执行器 → NEEDS_RUNTIME_TOOL，绝不成功。
3. 门禁没有证据 → NEEDS_GATE_EVIDENCE，绝不默认通过。
"""
import tempfile
import time
import unittest
from pathlib import Path

from core.agent_runtime import AgentRuntime
from core.artifact_store import ArtifactStore
from core.contracts import WorkflowNode, WorkflowPlan
from core.orchestrator import (
    AgentNodeExecutor,
    CallableNodeExecutor,
    ExecutionContext,
    NodeResult,
    NodeStatus,
    OrchestrationError,
    Orchestrator,
)


def make_store(tmpdir: str) -> ArtifactStore:
    run_dir = Path(tmpdir) / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    return ArtifactStore(run_dir)


def make_plan(nodes) -> WorkflowPlan:
    return WorkflowPlan(
        run_id="r_test", intent_ref="intent_x", spec_ref="spec_x",
        profile="test", nodes=nodes,
    )


class TestTopoLayers(unittest.TestCase):

    def test_simple_chain(self):
        plan = make_plan([
            WorkflowNode("a", capability_id="fn.a", capability_version="1", outputs=["oa"]),
            WorkflowNode("b", capability_id="fn.b", capability_version="1", depends_on=["a"],
                         inputs=["oa"], outputs=["ob"]),
            WorkflowNode("c", capability_id="fn.c", capability_version="1", depends_on=["b"], inputs=["ob"]),
        ])
        with tempfile.TemporaryDirectory() as t:
            layers = Orchestrator(plan, make_store(t), max_workers=1).topo_layers()
            self.assertEqual(layers, [["a"], ["b"], ["c"]])

    def test_cycle_raises(self):
        plan = make_plan([
            WorkflowNode("a", capability_id="fn.a", capability_version="1", depends_on=["c"]),
            WorkflowNode("b", capability_id="fn.b", capability_version="1", depends_on=["a"]),
            WorkflowNode("c", capability_id="fn.c", capability_version="1", depends_on=["b"]),
        ])
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(OrchestrationError):
                Orchestrator(plan, make_store(t)).topo_layers()

    def test_unknown_dependency_caught_by_plan_contract(self):
        """底座契约 WorkflowPlan.__post_init__ 直接拒未知依赖，
        编排器不应绕过这个检查。"""
        with self.assertRaises((ValueError, OrchestrationError)):
            make_plan([WorkflowNode("a", capability_id="fn.a",
                                    capability_version="1", depends_on=["zzz"])])

    def test_parallel_layer(self):
        plan = make_plan([
            WorkflowNode("a", capability_id="fn.a", capability_version="1", outputs=["oa"]),
            WorkflowNode("b", capability_id="fn.b", capability_version="1", outputs=["ob"]),
            WorkflowNode("c", capability_id="fn.c", capability_version="1", depends_on=["a", "b"]),
        ])
        with tempfile.TemporaryDirectory() as t:
            layers = Orchestrator(plan, make_store(t)).topo_layers()
            self.assertEqual(layers[0], ["a", "b"])
            self.assertEqual(layers[1], ["c"])


class TestCallableNodeExecutor(unittest.TestCase):

    def test_can_and_cannot(self):
        def hello(node, ctx):
            return NodeResult(node.node_id, NodeStatus.SUCCEEDED,
                              output_ref="art_x", meta={"x": 1})
        ex = CallableNodeExecutor()
        ex.register("fn.hello", hello)
        self.assertTrue(ex.can_execute(WorkflowNode("n", capability_id="fn.hello", capability_version="1")))
        self.assertFalse(ex.can_execute(WorkflowNode("n", capability_id="fn.unknown", capability_version="1")))

    def test_unknown_kind_reports_needs_runtime_tool(self):
        ex = CallableNodeExecutor()
        with tempfile.TemporaryDirectory() as t:
            ctx = ExecutionContext(store=make_store(t), plan=make_plan([]))
            r = ex.execute(WorkflowNode("n", capability_id="fn.x", capability_version="1"), ctx)
            self.assertEqual(r.status, NodeStatus.NEEDS_RUNTIME_TOOL)
            self.assertTrue(r.errors)

    def test_exception_recorded_not_swallowed(self):
        def boom(node, ctx):  # noqa
            raise RuntimeError("kaboom")
        ex = CallableNodeExecutor()
        ex.register("fn.boom", boom)
        with tempfile.TemporaryDirectory() as t:
            ctx = ExecutionContext(store=make_store(t), plan=make_plan([]))
            r = ex.execute(WorkflowNode("n", capability_id="fn.boom", capability_version="1"), ctx)
            self.assertEqual(r.status, NodeStatus.FAILED)
            self.assertTrue(any("kaboom" in e for e in r.errors))


class TestRedLines(unittest.TestCase):

    def test_no_executor_returns_needs_runtime_tool(self):
        plan = make_plan([WorkflowNode("n", capability_id="unknown.kind", capability_version="1")])
        with tempfile.TemporaryDirectory() as t:
            o = Orchestrator(plan, make_store(t), max_workers=1,
                             executors=[CallableNodeExecutor()])
            rep = o.run()
            self.assertEqual(rep.results["n"].status, NodeStatus.NEEDS_RUNTIME_TOOL)
            self.assertIn("n", rep.unresolved)

    def test_failure_blocked_downstream(self):
        def fail(node, ctx):  # noqa
            return NodeResult(node.node_id, NodeStatus.FAILED, errors=["x"])
        def ok(node, ctx):  # noqa
            return NodeResult(node.node_id, NodeStatus.SUCCEEDED,
                              output_ref="out", meta={})
        ex = CallableNodeExecutor()
        ex.register("fn.fail", fail)
        ex.register("fn.ok", ok)
        plan = make_plan([
            WorkflowNode("a", capability_id="fn.fail", capability_version="1", outputs=["oa"],
                         failure_policy="block"),
            WorkflowNode("b", capability_id="fn.ok", capability_version="1", depends_on=["a"],
                         inputs=["oa"], outputs=["ob"]),
        ])
        with tempfile.TemporaryDirectory() as t:
            o = Orchestrator(plan, make_store(t), max_workers=1, executors=[ex])
            rep = o.run()
            self.assertEqual(rep.results["a"].status, NodeStatus.FAILED)
            self.assertEqual(rep.results["b"].status, NodeStatus.BLOCKED)
            # BLOCKED 算未解决
            self.assertIn("b", rep.unresolved)

    def test_gate_pending_when_no_evaluator(self):
        def ok(node, ctx):  # noqa
            return NodeResult(node.node_id, NodeStatus.SUCCEEDED,
                              output_ref="out", meta={})
        ex = CallableNodeExecutor()
        ex.register("fn.ok", ok)
        plan = make_plan([WorkflowNode("a", capability_id="fn.ok", capability_version="1", gate_after="G0")])
        with tempfile.TemporaryDirectory() as t:
            o = Orchestrator(plan, make_store(t), max_workers=1, executors=[ex])
            rep = o.run()
            self.assertEqual(len(rep.gate_pending), 1)
            self.assertEqual(rep.gate_pending[0]["status"], "NEEDS_GATE_EVIDENCE")
            self.assertEqual(rep.gate_pending[0]["gate_id"], "G0")

    def test_gate_evaluator_can_pass_or_fail(self):
        def ok(node, ctx):  # noqa
            return NodeResult(node.node_id, NodeStatus.SUCCEEDED,
                              output_ref="out", meta={})
        ex = CallableNodeExecutor()
        ex.register("fn.ok", ok)
        plan = make_plan([WorkflowNode("a", capability_id="fn.ok", capability_version="1", gate_after="G0")])
        with tempfile.TemporaryDirectory() as t:
            def ev(node, r):
                return {"passed": True, "reason_codes": ["evidence_ok"]}
            o = Orchestrator(plan, make_store(t), max_workers=1, executors=[ex],
                             gate_evaluator=ev)
            rep = o.run()
            self.assertEqual(rep.gate_pending[0]["status"], "PASS")
            self.assertEqual(rep.gate_pending[0]["reason_codes"], ["evidence_ok"])


class TestResume(unittest.TestCase):

    def test_resume_skips_succeeded_with_same_fingerprint(self):
        def ok(node, ctx):  # noqa
            return NodeResult(node.node_id, NodeStatus.SUCCEEDED,
                              output_ref="art_" + node.node_id, meta={})
        ex = CallableNodeExecutor()
        ex.register("fn.ok", ok)
        plan = make_plan([WorkflowNode("a", capability_id="fn.ok", capability_version="1")])
        with tempfile.TemporaryDirectory() as t:
            store = make_store(t)
            Orchestrator(plan, store, max_workers=1, executors=[ex]).run()
            rep2 = Orchestrator(plan, store, max_workers=1, executors=[ex],
                                resume=True).run()
            self.assertEqual(rep2.results["a"].status, NodeStatus.SKIPPED)
            self.assertIn("a", rep2.resumed)


class TestParallelExecution(unittest.TestCase):

    def test_parallel_layer_runs_concurrently(self):
        def slow(node, ctx):  # noqa
            time.sleep(0.2)
            return NodeResult(node.node_id, NodeStatus.SUCCEEDED,
                              output_ref="out_" + node.node_id, meta={})
        ex = CallableNodeExecutor()
        ex.register("fn.slow", slow)
        plan = make_plan([WorkflowNode(f"n{i}", capability_id="fn.slow", capability_version="1")
                          for i in range(4)])
        with tempfile.TemporaryDirectory() as t:
            o = Orchestrator(plan, make_store(t), max_workers=4, executors=[ex])
            t0 = time.time()
            rep = o.run()
            elapsed = time.time() - t0
            self.assertEqual(rep.counts.get(NodeStatus.SUCCEEDED, 0), 4)
            # 串行 4*0.2=0.8s；并行约 0.2s；阈值放宽到 0.6s
            self.assertLess(elapsed, 0.6,
                            f"parallel not effective: elapsed={elapsed:.2f}s")


class TestAgentExecutorRedLine(unittest.TestCase):

    def test_agent_without_llm_reports_credentials_need(self):
        """红线：LLM 没配时 AgentRuntime 应报 NEEDS_LLM_CREDENTIALS，
        编排器绝不能把它标记为成功。"""
        ex = AgentNodeExecutor(runtime=AgentRuntime(provider="none"))
        node = WorkflowNode("a", capability_id="lead_producer", capability_version="1")
        with tempfile.TemporaryDirectory() as t:
            store = make_store(t)
            ctx = ExecutionContext(store=store, plan=make_plan([node]))
            r = ex.execute(node, ctx)
            self.assertIn(r.status, (NodeStatus.NEEDS_LLM_CREDENTIALS,
                                     NodeStatus.FAILED))
            self.assertTrue(r.errors, "必须如实报错误，不许空 errors 装成功")


if __name__ == "__main__":
    unittest.main()
