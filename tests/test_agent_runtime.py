"""W1 专家 Agent 运行时测试。

核心验证两件事：
  1. 无 LLM 时必须报 NEEDS_LLM_CREDENTIALS 且 payload 为 None —— 绝不用模板文本冒充专家产出；
  2. 有 LLM 时输出必须过 schema + acceptance，不过就判失败，不得放行。
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.agent_runtime import (  # noqa: E402
    AgentRuntime, AgentStatus, NEEDS_LLM_CREDENTIALS,
    extract_json, validate_schema, check_acceptance,
)
from core.role_cards import AgentTier, all_cards, card_counts, get_card  # noqa: E402


def _resp(text, success=True, provider="fake", model="fake-1", error=""):
    from core.llm_gateway import LLMResponse
    return LLMResponse(text, provider, model, 10, 20, success, error)


class TestRoleCards(unittest.TestCase):
    def test_lead_cards_registered(self):
        leads = [c for c in all_cards() if c.tier == AgentTier.LEAD]
        self.assertEqual(len(leads), 8)

    def test_every_card_has_full_definition(self):
        for card in all_cards():
            self.assertTrue(card.system_prompt.strip(), card.card_id)
            self.assertTrue(card.output_schema.get("required"), card.card_id)
            self.assertTrue(card.tools, card.card_id)
            self.assertTrue(card.phases, card.card_id)

    def test_counts_are_honest_about_the_82_target(self):
        """计数必须如实暴露缺口，不得把已注册数当成 82 位可用。"""
        counts = card_counts()
        self.assertEqual(counts["TARGET"], 82)
        self.assertEqual(counts["TOTAL"], len(all_cards()))
        self.assertEqual(counts["MISSING"], 82 - len(all_cards()))
        self.assertGreater(counts["MISSING"], 0)  # W2 补齐前必须大于 0


class TestSchemaAndAcceptance(unittest.TestCase):
    def test_validate_schema_catches_missing_required(self):
        errors = validate_schema({"a": 1}, {"type": "object", "properties": {"a": "number", "b": "string"},
                                            "required": ["a", "b"]})
        self.assertTrue(any("b" in e for e in errors))

    def test_validate_schema_catches_wrong_type(self):
        errors = validate_schema({"a": "x"}, {"type": "object", "properties": {"a": "number"}})
        self.assertTrue(errors)

    def test_validate_schema_accepts_valid(self):
        errors = validate_schema({"a": [1, 2]},
                                 {"type": "object", "properties": {"a": {"type": "array", "items": "number"}}})
        self.assertEqual(errors, [])

    def test_acceptance_min_items_and_enum(self):
        errors = check_acceptance({"v": "maybe", "l": [1]},
                                  [{"field": "v", "enum": ["go", "no-go"]},
                                   {"field": "l", "type": "list", "min_items": 3}])
        self.assertEqual(len(errors), 2)

    def test_extract_json_from_fence_and_balanced_block(self):
        self.assertEqual(extract_json("```json\n{\"a\": 1}\n```"), {"a": 1})
        self.assertEqual(extract_json('noise {"b": {"c": 2}} trailing'), {"b": {"c": 2}})
        self.assertIsNone(extract_json("no json here"))


class TestRuntimeHonesty(unittest.TestCase):
    def test_no_llm_returns_needs_credentials_not_template_text(self):
        """红线：没有 LLM 后端时不得产出任何专家结论。"""
        rt = AgentRuntime()
        with mock.patch.object(AgentRuntime, "available_providers", return_value=[]):
            out = rt.run("lead_producer", "评估这个需求", {"intent": "做一个割草游戏"})
        self.assertEqual(out.status, NEEDS_LLM_CREDENTIALS)
        self.assertIsNone(out.payload)
        self.assertEqual(out.raw, "")          # 没有任何冒充产出的文本
        self.assertTrue(out.errors)

    def test_preflight_reports_missing_credentials(self):
        rt = AgentRuntime()
        with mock.patch.object(AgentRuntime, "available_providers", return_value=[]):
            pre = rt.preflight()
        self.assertFalse(pre["llm_ready"])
        self.assertEqual(pre["status"], NEEDS_LLM_CREDENTIALS)
        self.assertTrue(pre["how_to_fix"])

    def test_unknown_card_is_rejected(self):
        rt = AgentRuntime()
        out = rt.run("not_a_real_card", "x", {})
        self.assertEqual(out.status, AgentStatus.UNKNOWN_CARD)

    def test_missing_required_input_is_rejected_before_calling_llm(self):
        rt = AgentRuntime()
        with mock.patch.object(AgentRuntime, "available_providers", return_value=["gemini"]):
            out = rt.run("lead_producer", "x", {})   # 缺 intent
        self.assertEqual(out.status, AgentStatus.INPUT_INVALID)


class TestRuntimeWithStubbedLLM(unittest.TestCase):
    """用假 LLM 验证 schema / acceptance 真的会拦。"""

    def _runtime(self, text, success=True):
        rt = AgentRuntime()
        patchers = [
            mock.patch.object(AgentRuntime, "available_providers", return_value=["gemini"]),
            mock.patch("core.agent_runtime.LLMGateway.call", return_value=_resp(text, success=success)),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)
        return rt

    def test_valid_output_passes(self):
        payload = {
            "verdict": "go",
            "scope_in": ["核心战斗"],
            "scope_out": ["多人联机"],
            "top_risks": [{"risk": "r", "impact": "i", "mitigation": "m"} for _ in range(3)],
            "milestones": [{"name": "垂直切片", "exit_criteria": "可玩且帧率达标"}],
            "budget_note": "两周内完成，需要 1 个 LLM key。",
        }
        text = "```json\n" + __import__("json").dumps(payload, ensure_ascii=False) + "\n```"
        out = self._runtime(text).run("lead_producer", "评估", {"intent": "割草", "constraints": "web", "budget": "小"})
        self.assertEqual(out.status, AgentStatus.OK, out.errors)
        self.assertEqual(out.payload["verdict"], "go")

    def test_non_json_output_is_rejected(self):
        out = self._runtime("我认为这个需求不错，可以做。").run(
            "lead_producer", "评估", {"intent": "割草", "constraints": "web", "budget": "小"})
        self.assertEqual(out.status, AgentStatus.JSON_INVALID)
        self.assertIsNone(out.payload)

    def test_schema_violation_is_rejected(self):
        text = '```json\n{"verdict": "go"}\n```'   # 缺 scope_in 等必填
        out = self._runtime(text).run("lead_producer", "评估",
                                      {"intent": "割草", "constraints": "web", "budget": "小"})
        self.assertEqual(out.status, AgentStatus.SCHEMA_INVALID)

    def test_acceptance_violation_is_rejected(self):
        # 结构合规但质量不达标：top_risks 只有 1 条、budget_note 过短
        text = ('```json\n{"verdict":"go","scope_in":["a"],"scope_out":[],'
                '"top_risks":[{"risk":"r","impact":"i","mitigation":"m"}],'
                '"milestones":[{"name":"x","exit_criteria":"y"}],"budget_note":"短"}\n```')
        out = self._runtime(text).run("lead_producer", "评估",
                                      {"intent": "割草", "constraints": "web", "budget": "小"})
        self.assertEqual(out.status, AgentStatus.ACCEPTANCE_FAILED)
        self.assertIsNotNone(out.payload)   # 保留原始产出以便排查

    def test_shallow_placeholder_entries_are_rejected(self):
        """「性能优化」这种单词占位不能算风险条目，必须带 risk/impact/mitigation。"""
        text = ('```json\n{"verdict":"go","scope_in":["a"],"scope_out":[],'
                '"top_risks":["性能优化","排期","美术"],'
                '"milestones":["原型","上线"],"budget_note":"预算够用预算够用预算够用"}\n```')
        out = self._runtime(text).run("lead_producer", "评估",
                                      {"intent": "割草", "constraints": "web", "budget": "小"})
        self.assertEqual(out.status, AgentStatus.SCHEMA_INVALID, out.errors)
        self.assertTrue(any("top_risks" in e for e in out.errors))

    def test_repair_loop_recovers_from_bad_enum(self):
        """第一次给错枚举值、第二次改对 —— 自愈循环应让它通过，而不是直接判死。"""
        bad = '```json\n{"verdict":"不可行","scope_in":["a"],"scope_out":[],"top_risks":[{"risk":"r","impact":"i","mitigation":"m"},{"risk":"r","impact":"i","mitigation":"m"},{"risk":"r","impact":"i","mitigation":"m"}],"milestones":[{"name":"x","exit_criteria":"y"}],"budget_note":"这是足够长的预算说明"}\n```'
        good = bad.replace('"不可行"', '"no-go"')
        import core.agent_runtime as ar
        responses = [_resp(bad), _resp(good)]
        rt = AgentRuntime(max_repairs=2)
        p1 = mock.patch.object(AgentRuntime, "available_providers", return_value=["gemini"])
        p2 = mock.patch.object(ar.LLMGateway, "call", side_effect=responses)
        with p1, p2:
            out = rt.run("lead_producer", "评估", {"intent": "割草", "constraints": "web", "budget": "小"})
        self.assertEqual(out.status, AgentStatus.OK, out.errors)
        self.assertEqual(out.payload["verdict"], "no-go")

    def test_repair_exhausted_still_fails(self):
        """自愈次数用尽仍不过，必须判失败 —— 不允许放宽验收规则放行。"""
        bad = '```json\n{"verdict":"不可行"}\n```'
        rt = AgentRuntime(max_repairs=1)
        p1 = mock.patch.object(AgentRuntime, "available_providers", return_value=["gemini"])
        p2 = mock.patch("core.agent_runtime.LLMGateway.call", return_value=_resp(bad))
        with p1, p2:
            out = rt.run("lead_producer", "评估", {"intent": "割草", "constraints": "web", "budget": "小"})
        self.assertNotEqual(out.status, AgentStatus.OK)
        self.assertTrue(any("重试修复" in e for e in out.errors))

    def test_llm_failure_is_not_reported_as_success(self):
        out = self._runtime("", success=False).run(
            "lead_producer", "评估", {"intent": "割草", "constraints": "web", "budget": "小"})
        self.assertEqual(out.status, AgentStatus.LLM_ERROR)


if __name__ == "__main__":
    unittest.main(verbosity=2)
