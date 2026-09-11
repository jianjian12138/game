"""tests/test_llm_skill_adapter.py — C 类技能适配器与分类表的测试（W3c-4）。

测试策略：
- 所有"跑通/失败"路径用注入的假 LLM 调用，确定性强、不烧真额度；
- 关键红线（无凭据不得产出、不得放宽验收、占位符必拦）逐条断言；
- 与真实端点的连通性不属于本文件职责（由 CLI `skill-verify-c` 真跑并落证据）。
"""
from __future__ import annotations

import json
import unittest
from typing import Any, Dict, List
from unittest import mock

from core.llm_skill_adapter import (
    C_SKILL_SPECS, LLMSkillAdapter, LLMSkillResult, LLMSkillStatus,
    find_placeholders, get_spec, schema_skeleton, spec_ids, validate_payload,
    weighted_len,
)
from core.capability_registry import capability_registry as _cr
from core.skill_registry import SkillClass, SkillStatus, skill_registry as _sr


def _fake(text: Any, provider: str = "fake", model: str = "fake-1",
          success: bool = True, error: str = ""):
    """构造一个注入式 LLM 调用。text 为 dict 时自动序列化成 ```json 围栏。"""
    body = text if isinstance(text, str) else (
        "```json\n" + json.dumps(text, ensure_ascii=False) + "\n```")
    return lambda system, prompt: {"success": success, "text": body,
                                   "provider": provider, "model": model, "error": error}


def _seq(*responses):
    """按调用次序返回不同响应，用于验证自修复确实发生了第二次调用。

    用尽后重复最后一个响应——否则 StopIteration 会掩盖"重试次数"这类真实缺陷。
    """
    it = iter(responses)
    return lambda system, prompt: next(it, responses[-1])


class TestSpecs(unittest.TestCase):
    """24 项契约自身必须完整——没契约的 C 类技能等于空头支票。"""

    def test_24_specs(self):
        self.assertEqual(len(C_SKILL_SPECS), 24)

    def test_specs_cover_all_c_class(self):
        from core.skill_classification import C_SKILLS
        self.assertEqual(set(spec_ids()), set(C_SKILLS))

    def test_every_spec_has_prompt_schema_required(self):
        for sid, spec in C_SKILL_SPECS.items():
            with self.subTest(sid=sid):
                self.assertTrue(spec.system_prompt.strip())
                self.assertTrue(spec.task_template.strip())
                self.assertEqual(spec.output_schema.get("type"), "object")
                self.assertTrue(spec.output_schema.get("required"),
                                f"{sid} 没有 required 字段，等于没有契约")
                self.assertIn("{task}", spec.task_template)

    def test_build_prompt_embeds_schema_skeleton(self):
        """提示词里必须带上结构骨架：实测不带骨架时模型会自行改名改层级。"""
        spec = get_spec("drop_rate_rng_table")
        p = spec.build_prompt("设计一个掉落表", {"k": 1})
        self.assertIn("```json", p)
        for key in spec.output_schema["required"]:
            self.assertIn(key, p)


class TestWeightedLen(unittest.TestCase):

    def test_cjk_counts_double(self):
        self.assertEqual(weighted_len("飘字与顿帧"), 10)
        self.assertEqual(weighted_len("abc"), 3)
        self.assertEqual(weighted_len(""), 0)

    def test_min_length_uses_weighted_len(self):
        schema = {"type": "object", "properties": {"a": {"type": "string", "minLength": 6}}}
        self.assertEqual(validate_payload({"a": "飘字与顿帧"}, schema), [])
        self.assertTrue(validate_payload({"a": "掉帧"}, schema))


class TestValidatePayload(unittest.TestCase):

    def test_min_items(self):
        s = {"type": "object", "properties": {"x": {"type": "array", "minItems": 3,
                                                    "items": {"type": "object"}}}}
        self.assertEqual(len(validate_payload({"x": [{}, {}, {}]}, s)), 0)
        self.assertTrue(validate_payload({"x": [{}]}, s))

    def test_min_max_numbers(self):
        s = {"type": "object", "properties": {"n": {"type": "number", "minimum": 0, "maximum": 1}}}
        self.assertEqual(validate_payload({"n": 0.5}, s), [])
        self.assertTrue(validate_payload({"n": 5}, s))

    def test_pattern_and_contains_any(self):
        s = {"type": "object", "properties": {
            "hex": {"type": "string", "pattern": r"^#[0-9A-Fa-f]{6}$"},
            "code": {"type": "string", "containsAny": ["GGX", "BRDF"]}}}
        self.assertEqual(validate_payload({"hex": "#1A2B3C", "code": "GGX"}, s), [])
        self.assertTrue(validate_payload({"hex": "1A2B3C", "code": "GGX"}, s))
        self.assertTrue(validate_payload({"hex": "#1A2B3C", "code": "phong"}, s))

    def test_nested_errors_reported_with_path(self):
        s = {"type": "object", "properties": {
            "a": {"type": "array", "items": {"type": "object", "properties": {
                "b": {"type": "string", "minLength": 20}}}}}}
        errs = validate_payload({"a": [{"b": "短"}]}, s)
        self.assertTrue(errs and errs[0].startswith("$.a[0].b"))


class TestPlaceholders(unittest.TestCase):
    """占位符比空字段更危险——它看起来像内容。"""

    def test_blacklist_caught(self):
        errs = find_placeholders({"risks": ["性能优化", "排期"]})
        self.assertEqual(len(errs), 2)

    def test_risk_must_have_impact_and_mitigation(self):
        errs = find_placeholders({"risks": [{"risk": "数值膨胀"}]})
        self.assertTrue(errs and "mitigation" in errs[0])

    def test_too_short_caught(self):
        errs = find_placeholders({"items": ["掉帧"]})
        self.assertTrue(errs)

    def test_real_content_passes(self):
        self.assertEqual(find_placeholders({
            "risks": [{"risk": "后期数值膨胀导致金币失去意义",
                       "impact": "玩家不再有产出动机",
                       "mitigation": "引入金币沉淀池与每周重置的消耗活动"}],
            "steps": ["玩家在开局 10 秒内完成首次建造"]}), [])


    def test_id_like_strings_are_not_placeholders(self):
        """prerequisites:["task1"] 是合法 ID，不是空话——长度门槛必须豁免它。"""
        self.assertEqual(find_placeholders({"prerequisites": ["task1", "quest.main_01"]}), [])

    def test_id_like_still_caught_if_blacklisted(self):
        """但 ID 位上写 "n/a" 仍然是空话，豁免只针对长度不针对黑名单。"""
        self.assertTrue(find_placeholders({"prerequisites": ["n/a"]}))


class TestAcceptanceWeighted(unittest.TestCase):
    """acceptance 的长度门槛必须按加权长度判定——否则中文被要求 2 倍长度。"""

    def test_chinese_verdict_passes_at_half_chars(self):
        from core.llm_skill_adapter import check_acceptance_weighted
        rules = [{"field": "verdict", "min_len": 30}]
        # 20 个汉字 = 加权 40，应当通过；若用原始 len() 判则会被误杀
        ok = {"verdict": "该主张把行业惯例当作公理，未给出任何可验证的因果链条，应判定为未证成。"}
        self.assertEqual(check_acceptance_weighted(ok, rules), [])
        bad = {"verdict": "证据不足。"}
        self.assertTrue(check_acceptance_weighted(bad, rules))

    def test_non_length_rules_still_delegated(self):
        from core.llm_skill_adapter import check_acceptance_weighted
        rules = [{"field": "platform", "enum": ["touch", "gamepad"]},
                 {"field": "bindings", "min_items": 3}]
        self.assertEqual(check_acceptance_weighted(
            {"platform": "touch", "bindings": [{}, {}, {}]}, rules), [])
        self.assertTrue(check_acceptance_weighted(
            {"platform": "mouse", "bindings": [{}]}, rules))


class TestSchemaSkeleton(unittest.TestCase):

    def test_skeleton_has_required_keys_and_array_len(self):
        spec = get_spec("core_loop_design")
        sk = schema_skeleton(spec.output_schema)
        self.assertIn("core_loop", sk)
        self.assertIn("risks", sk)
        self.assertGreaterEqual(len(sk["core_loop"]["steps"]), 3)

    def test_number_placeholder_is_not_quoted(self):
        sk = schema_skeleton({"type": "object", "properties": {
            "n": {"type": "number", "minimum": 0, "maximum": 1}}})
        self.assertIsInstance(sk["n"], str)
        self.assertIn("数字", sk["n"])


class TestAdapterRedLines(unittest.TestCase):

    def setUp(self):
        self.spec = get_spec("drop_rate_rng_table")

    def test_no_credentials_returns_needs_and_never_payload(self):
        """红线 1：没有 LLM 就不许有产出，更不许返回模板文本。"""
        adapter = LLMSkillAdapter()
        with mock.patch("core.llm_gateway.LLMGateway.available_providers",
                        staticmethod(lambda: [])):
            r = adapter.run(self.spec, "x")
        self.assertEqual(r.status, LLMSkillStatus.NEEDS_LLM_CREDENTIALS)
        self.assertIsNone(r.payload)
        self.assertFalse(r.ok)

    def test_llm_error_recorded(self):
        a = LLMSkillAdapter(llm_call=_seq({"success": False, "error": "HTTP 429"}))
        r = a.run(self.spec, "x")
        self.assertEqual(r.status, LLMSkillStatus.LLM_ERROR)
        self.assertIn("429", r.errors[0])

    def test_non_json_rejected(self):
        a = LLMSkillAdapter(llm_call=_fake("这不是 JSON，只是一段散文。"))
        r = a.run(self.spec, "x")
        self.assertEqual(r.status, LLMSkillStatus.JSON_INVALID)
        self.assertIsNone(r.payload)

    def test_schema_invalid_exhausts_repairs(self):
        bad = {"table": [{"item": "剑", "weight": "很多", "rarity": "sr"}]}
        a = LLMSkillAdapter(llm_call=_fake(bad))
        r = a.run(self.spec, "x")
        self.assertIn(r.status, (LLMSkillStatus.SCHEMA_INVALID, LLMSkillStatus.LLM_ERROR))
        self.assertEqual(r.attempts, 3)          # max_repairs=2 → 共 3 次
        self.assertTrue(any("已重试修复" in e for e in r.errors))

    def test_placeholder_rejected(self):
        good = {"table": [{"item": "生锈的铁剑", "weight": 40, "rarity": "普通"},
                          {"item": "精钢长剑", "weight": 12, "rarity": "精良"},
                          {"item": "龙牙巨剑", "weight": 1, "rarity": "传说"}],
                "pity": {"threshold": 60, "guaranteed": "龙牙巨剑"}}
        bad = dict(good, table=[dict(good["table"][0], item="待定")] * 3)
        # 让 item="待定" 躲过长度与类型校验，只能靠黑名单拦截
        a = LLMSkillAdapter(llm_call=_fake(bad))
        r = a.run(self.spec, "x")
        self.assertEqual(r.status, LLMSkillStatus.PLACEHOLDER_REJECTED)
        self.assertTrue(any("占位" in e for e in r.errors))

    def test_custom_validator_runs(self):
        """权重全为 0 时 schema 仍成立（minimum=0），只能靠自定义校验抓住。"""
        payload = {"table": [{"item": "生锈的铁剑", "weight": 0, "rarity": "普通"},
                             {"item": "精钢长剑", "weight": 0, "rarity": "精良"},
                             {"item": "龙牙巨剑", "weight": 0, "rarity": "传说"}],
                   "pity": {"threshold": 60, "guaranteed": "龙牙巨剑"}}
        a = LLMSkillAdapter(llm_call=_fake(payload))
        r = a.run(self.spec, "x")
        self.assertFalse(r.ok)
        self.assertTrue(any("custom" in e for e in r.errors))

    def test_ok_on_first_try(self):
        payload = {"table": [{"item": "生锈的铁剑", "weight": 40, "rarity": "普通"},
                             {"item": "精钢长剑", "weight": 12, "rarity": "精良"},
                             {"item": "龙牙巨剑", "weight": 1, "rarity": "传说"}],
                   "pity": {"threshold": 60, "guaranteed": "龙牙巨剑"}}
        a = LLMSkillAdapter(llm_call=_fake(payload))
        r = a.run(self.spec, "x")
        self.assertTrue(r.ok, r.errors)
        self.assertEqual(r.attempts, 1)
        self.assertEqual(r.provider, "fake")

    def test_self_repair_actually_retries(self):
        """第一次不合格、第二次合格 → 必须通过，且如实记录重试过。"""
        good = {"table": [{"item": "生锈的铁剑", "weight": 40, "rarity": "普通"},
                          {"item": "精钢长剑", "weight": 12, "rarity": "精良"},
                          {"item": "龙牙巨剑", "weight": 1, "rarity": "传说"}],
                "pity": {"threshold": 60, "guaranteed": "龙牙巨剑"}}
        a = LLMSkillAdapter(llm_call=_seq({"success": True, "text": "一段散文"},
                                          {"success": True, "text": json.dumps(good, ensure_ascii=False)}))
        r = a.run(self.spec, "x")
        self.assertTrue(r.ok, r.errors)
        self.assertEqual(r.attempts, 2)
        self.assertTrue(any("此前失败原因" in e for e in r.errors))

    def test_unknown_skill_is_no_spec(self):
        a = LLMSkillAdapter(llm_call=_fake("{}"))
        r = a.run_skill("no_such_skill", "x")
        self.assertEqual(r.status, LLMSkillStatus.NO_SPEC)


class TestClassification(unittest.TestCase):
    """分类表必须自洽：114 = A + B + C，零漏项。"""

    def setUp(self):
        _sr._skills.clear()
        _cr._descriptors.clear()

    def tearDown(self):
        _sr._skills.clear()
        _cr._descriptors.clear()

    def test_table_is_self_consistent(self):
        from core.skill_classification import verify_table
        ok, problems = verify_table()
        self.assertTrue(ok, problems)

    def test_apply_classification_covers_everything(self):
        from core.skill_classification import apply_classification, unclassified
        from core.skill_registry_seeds import apply_default_seeds
        _sr.ingest_from_registry()
        apply_default_seeds()          # 25 项 A 类先就位，否则它们会被算成"未分类"
        apply_classification(_sr)
        self.assertEqual(unclassified(_sr), [])
        c = _sr.counts()
        self.assertEqual(c["TOTAL"], 114)
        self.assertEqual(c["B"], 65)
        self.assertEqual(c["C"], 24)
        self.assertEqual(c["C_REGISTERED"] + c["C_SPECD"], 24)

    def test_demoted_candidates_leave_a_class(self):
        """5 个语义错配的候选必须被撤出 A 类，不许靠它们凑 A 的数量。"""
        from core.skill_classification import apply_classification
        _sr.ingest_from_registry()
        apply_classification(_sr)
        for sid in ("arpeggio_generator", "object_pool_manager",
                    "pbr_five_channel_baking", "save_state_serializer"):
            self.assertNotEqual(_sr._skills[sid].cls, SkillClass.A, sid)
        self.assertEqual(_sr._skills["webgl_shader_pipeline"].cls, SkillClass.C)


class TestRegisterCSkill(unittest.TestCase):
    """C 类只有真跑通才允许注册——这是本平台对绑 LLM 技能的防伪底线。"""

    def setUp(self):
        _sr._skills.clear()
        _cr._descriptors.clear()
        _sr.ingest_from_registry()
        from core.skill_classification import apply_classification
        apply_classification(_sr)

    def tearDown(self):
        _sr._skills.clear()
        _cr._descriptors.clear()

    def _ok_result(self, skill_id: str) -> LLMSkillResult:
        return LLMSkillResult(skill_id=skill_id, status=LLMSkillStatus.OK,
                              payload={"x": 1}, provider="openai_compat",
                              model="glm-4-flash", attempts=1)

    def test_cannot_register_without_passing(self):
        bad = LLMSkillResult(skill_id="anti_rubber_stamp_veto",
                             status=LLMSkillStatus.SCHEMA_INVALID,
                             provider="openai_compat", errors=["bad"])
        with self.assertRaises(ValueError):
            _sr.register_c_skill("anti_rubber_stamp_veto", result=bad)

    def test_cannot_register_without_provider(self):
        r = LLMSkillResult(skill_id="anti_rubber_stamp_veto",
                           status=LLMSkillStatus.OK, payload={}, provider="")
        with self.assertRaises(ValueError):
            _sr.register_c_skill("anti_rubber_stamp_veto", result=r)

    def test_cannot_register_non_c_skill(self):
        with self.assertRaises(ValueError):
            _sr.register_c_skill("aabb_collision_detection",
                                 result=self._ok_result("aabb_collision_detection"))

    def test_register_after_real_pass(self):
        sid = "anti_rubber_stamp_veto"
        desc = _sr.register_c_skill(sid, result=self._ok_result(sid))
        self.assertEqual(desc.capability_id, f"skill.{sid}")
        self.assertEqual(desc.kind, "llm_skill")
        self.assertIn(f"skill.{sid}", [d.capability_id for d in _cr.list()])
        self.assertEqual(_sr.counts()["C_REGISTERED"], 1)
        self.assertEqual(_sr._skills[sid].status, SkillStatus.REGISTERED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
