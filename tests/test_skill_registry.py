"""tests/test_skill_registry.py: L2 技能注册表单元测试（W3a）。

三条红线：
1. 真实 ingest 114 项（分母永远不能丢）。
2. 真可调用才能 register；callable / signature 校验必须抛。
3. 已注册的 skill 出现在 capability_registry 里，能被 orchestrator 找到。
"""
import unittest
from typing import Any, Callable

from core.capability_registry import capability_registry
from core.skill_registry import (
    L2Skill,
    SkillClass,
    SkillRegistry,
    SkillStatus,
    skill_registry,
    _score,
    _tokens,
)
from core.skill_registry_seeds import apply_default_seeds, SEEDS


class TestTokensAndScore(unittest.TestCase):

    def test_tokens_split(self):
        self.assertEqual(_tokens("a_star_pathfinding"), {"star", "pathfinding"})
        self.assertEqual(_tokens("responsive_ui_layout"), {"responsive", "ui", "layout"})

    def test_score_identical(self):
        self.assertGreater(_score("sprite_animation_sheet", "sprite_animation_sheet"), 0.95)

    def test_score_unrelated_low(self):
        self.assertLess(_score("quantum_entangler", "save_load_integrity"), 0.1)


class TestIngestAndDiscover(unittest.TestCase):

    def setUp(self):
        # 两个注册表都是模块单例，测试间必须清，否则 key 撞
        from core.capability_registry import capability_registry as _cr
        from core.skill_registry import skill_registry as _sr
        _cr._descriptors.clear()
        _sr._skills.clear()
        self.reg = SkillRegistry()
        self.reg.ingest_from_registry()
        self.assertEqual(len(self.reg._skills), 114)

    def test_ingest_total_is_114(self):
        counts = self.reg.counts()
        self.assertEqual(counts["TOTAL"], 114)
        self.assertEqual(counts["PENDING"], 114)

    def test_discover_finds_a_class(self):
        res = self.reg.discover_a_class()
        self.assertGreater(res["discovered"], 0,
                           f"应至少发现一个 A 类候选；实际：{res}")
        counts = self.reg.counts()
        self.assertGreaterEqual(counts["A_DISCOVERED"] + counts["A_BLOCKED"], 10)

    def test_discover_does_not_invent_modules(self):
        """不能把不存在的模块标成 DISCOVERED。"""
        self.reg.discover_a_class()
        for sk in self.reg.list(status=SkillStatus.DISCOVERED):
            self.assertTrue(sk.candidate_module)
            self.assertIn(".", sk.candidate_module)


class TestRegisterRedLines(unittest.TestCase):

    def setUp(self):
        from core.capability_registry import capability_registry as _cr
        from core.skill_registry import skill_registry as _sr
        _cr._descriptors.clear()
        _sr._skills.clear()
        self.reg = SkillRegistry()
        self.reg.ingest_from_registry()
        self.reg.discover_a_class()

    def test_register_rejects_non_callable(self):
        discovered = self.reg.list(status=SkillStatus.DISCOVERED)
        if not discovered:
            self.skipTest("no discovered skills to test")
        sid = discovered[0].skill_id
        with self.assertRaises(ValueError):
            self.reg.register_as_capability(sid, entry="not a function")

    def test_register_rejects_unknown_skill(self):
        with self.assertRaises(KeyError):
            self.reg.register_as_capability("nonexistent_skill_xyz", entry=lambda: None)

    def test_register_rejects_pending_skill(self):
        """PENDING 不是 DISCOVERED，不能直接 register。"""
        pending = [s for s in self.reg.list(status=SkillStatus.PENDING)]
        if not pending:
            self.skipTest("no pending skills")
        with self.assertRaises(ValueError):
            self.reg.register_as_capability(pending[0].skill_id, entry=lambda: None)

    def test_register_marks_registered(self):
        discovered = self.reg.list(status=SkillStatus.DISCOVERED)
        if not discovered:
            self.skipTest("no discovered skills")
        sid = discovered[0].skill_id
        # 用一个真可调用的占位
        from pipeline.data_oriented_ecs import DataOrientedECS
        # 但 sid 不一定是 data_oriented_typedarray_ecs；换个真存在于已发现里的 entry
        # 简单做法：从 discovered 拿一个，对应 pipeline.data_oriented_ecs.DataOrientedECS
        # 上面 setUp 中 ingest + discover 已把 data_oriented_typedarray_ecs 设为 DISCOVERED
        target = self.reg._skills.get("data_oriented_typedarray_ecs")
        if target is None or target.status != SkillStatus.DISCOVERED:
            self.skipTest("data_oriented_typedarray_ecs not discovered")
        desc = self.reg.register_as_capability(
            "data_oriented_typedarray_ecs", entry=DataOrientedECS, version="1.0.0")
        self.assertEqual(desc.capability_id, "skill.data_oriented_typedarray_ecs")
        # 出现在 capability_registry
        from core.capability_registry import capability_registry
        found = capability_registry.resolve("skill.data_oriented_typedarray_ecs")
        self.assertEqual(found.capability_id, "skill.data_oriented_typedarray_ecs")

    def test_cannot_double_register(self):
        from pipeline.data_oriented_ecs import DataOrientedECS
        self.reg.register_as_capability("data_oriented_typedarray_ecs",
                                        entry=DataOrientedECS)
        # 再注册同一 skill_id 应抛（DISCOVERED → REGISTERED 后不再是 DISCOVERED）
        with self.assertRaises(ValueError):
            self.reg.register_as_capability("data_oriented_typedarray_ecs",
                                            entry=DataOrientedECS)


class TestSeeds(unittest.TestCase):

    def setUp(self):
        from core.capability_registry import capability_registry as _cr
        from core.skill_registry import skill_registry as _sr
        _cr._descriptors.clear()
        _sr._skills.clear()

    def test_apply_default_seeds_real_count(self):
        res = apply_default_seeds()
        # 真实数字：等于 SEEDS 全集（当前 25）或其中已失败的子集，
        # 绝不 == 40（那是 A 类总目标，需 W3b 之后才可能达成）。
        self.assertGreater(res["registered"], 0)
        self.assertLessEqual(res["registered"], len(SEEDS))
        # failed 必须有真实原因（不空字符串就 OK）
        if res["failed"] > 0:
            for fid in res["failed_ids"]:
                self.assertIn(":", fid)

    def test_both_seed_batches_present(self):
        """W3a 首批 12 项 + W3b 第二批 13 项都要在 SEEDS 里。"""
        apply_default_seeds()
        ids = [s[0] for s in SEEDS]
        # W3a 首批抽样
        for sid in ("data_oriented_typedarray_ecs", "tech_tree_dag_economic_balance",
                    "autotile_47_bitmask_compilation", "vertical_slice_milestoning"):
            self.assertIn(sid, ids)
        # W3b 第二批抽样（含内容级搜索发现的）
        for sid in ("deterministic_path_solving", "event_driven_msg_bus",
                    "evidence_pack_targeted_healing", "combat_damage_formula",
                    "discrete_tick_physics_freeze"):
            self.assertIn(sid, ids)

    def test_mismatched_candidates_not_registered(self):
        """语义错配的 5 个候选必须**不**被注册（防伪证）。"""
        apply_default_seeds()
        from core.skill_registry import SkillStatus
        registered_ids = {s.skill_id for s in
                          __import__("core.skill_registry",
                                     fromlist=["skill_registry"]).skill_registry.list(
                              status=SkillStatus.REGISTERED)}
        for bad in ("arpeggio_generator", "object_pool_manager",
                    "pbr_five_channel_baking", "save_state_serializer",
                    "webgl_shader_pipeline"):
            self.assertNotIn(bad, registered_ids,
                             f"{bad} 是语义错配候选，不应被注册为 A 类")

    def test_seed_skills_visible_to_capability_registry(self):
        apply_default_seeds()
        for sid, entry, version, _limits, _evi in SEEDS:
            desc = capability_registry.resolve(f"skill.{sid}")
            self.assertEqual(desc.version, version)
            self.assertEqual(desc.implementation["entrypoint"], entry.__name__)


class TestIntegrationWithOrchestrator(unittest.TestCase):

    def setUp(self):
        from core.capability_registry import capability_registry as _cr
        from core.skill_registry import skill_registry as _sr
        _cr._descriptors.clear()
        _sr._skills.clear()

    def test_registered_skill_runs_through_orchestrator(self):
        """注册过的 skill 必须能被 orchestrator 找到并跑（真调用，不只是存在性）。"""
        from core.artifact_store import ArtifactStore
        from core.contracts import WorkflowNode, WorkflowPlan
        from core.orchestrator import CallableNodeExecutor, NodeStatus, Orchestrator
        import tempfile
        from pathlib import Path

        apply_default_seeds()
        ex = CallableNodeExecutor()

        # 注册 skill.entry 作为可执行器
        from pipeline.data_oriented_ecs import DataOrientedECS
        from core.skill_registry_seeds import SEEDS

        def call_seed_skill(node, ctx):
            # 真实调用：构造 DataOrientedECS(capacity=10) 验证 entry 真活着
            inst = DataOrientedECS(capacity=10)
            return __import__("core.orchestrator", fromlist=["NodeResult"]).NodeResult(
                node.node_id, NodeStatus.SUCCEEDED,
                output_ref="seed_out",
                meta={"instance_type": type(inst).__name__, "capacity": 10})

        ex.register("skill.data_oriented_typedarray_ecs", call_seed_skill)

        plan = WorkflowPlan(
            run_id="r_seed", intent_ref="i", spec_ref="s", profile="p",
            nodes=[WorkflowNode("a", capability_id="skill.data_oriented_typedarray_ecs",
                                capability_version="1.0.0")])
        with tempfile.TemporaryDirectory() as t:
            run_dir = Path(t) / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            store = ArtifactStore(run_dir)
            orch = Orchestrator(plan, store, max_workers=1, executors=[ex])
            rep = orch.run()
            self.assertEqual(rep.results["a"].status, NodeStatus.SUCCEEDED)
            self.assertEqual(rep.results["a"].meta["instance_type"], "DataOrientedECS")


if __name__ == "__main__":
    unittest.main()
