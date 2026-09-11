"""core/llm_skill_adapter.py — C 类技能（绑 LLM）的结构化产出适配器（W3c-2）。

C 类技能（24 项：策划/叙事/合规/评估/Shader 生成）的共同特点是：
产出没有可计算的金标准，必须由 LLM 生成。但"必须由 LLM 生成"不等于
"生成什么都能收"。本模块把 C 类技能变成**有契约的调用**：

    spec(schema + acceptance + 自定义校验) → LLM → JSON 抽取
        → schema 校验 → acceptance 校验 → 占位符拦截 → 自定义语义校验
        → 不过就把错误回喂重改（自修复，最多 max_repairs 次）
        → 仍不过就如实判失败

红线（与计划 13.2 一致，一条都不能破）
────────────────────────────────────
1. 没有可用 LLM 后端 → 返回 NEEDS_LLM_CREDENTIALS，**绝不**返回模板文本冒充产出。
2. 自修复次数用尽仍不过 → 判失败，**绝不**放宽验收规则放行。
3. 占位符（"性能优化" / "排期" / "待定" / "TBD" 这类空话）一律拦截，
   空话清单比空字段更危险，因为它看起来像内容。
4. 是否"真的调用过"由 LLMSkillResult.provider/model/attempts 如实记录，
   可回查到具体端点。
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.agent_runtime import (  # 复用已测试的校验，不另造一套
    check_acceptance, extract_json, validate_schema,
)

NEEDS_LLM_CREDENTIALS = "NEEDS_LLM_CREDENTIALS"


class LLMSkillStatus:
    OK = "OK"
    NEEDS_LLM_CREDENTIALS = NEEDS_LLM_CREDENTIALS
    LLM_ERROR = "LLM_ERROR"
    JSON_INVALID = "JSON_INVALID"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    ACCEPTANCE_FAILED = "ACCEPTANCE_FAILED"
    PLACEHOLDER_REJECTED = "PLACEHOLDER_REJECTED"
    NO_SPEC = "NO_SPEC"
    EXHAUSTED = "EXHAUSTED"


# ── 占位符黑名丹：看起来像内容、实际什么都没说的词 ─────────────────────────────
PLACEHOLDER_HINTS = {
    "性能优化", "排期", "待定", "待补充", "待确认", "后续补充", "略", "同上",
    "无", "暂无", "等等", "等等。", "其他", "相关功能", "若干", "一些",
    "tbd", "todo", "n/a", "na", "xxx", "...", "—", "-", "?", "??",
    "待办", "按需", "视情况", "合理即可", "适当", "若干项",
}

_MIN_LIST_ITEM_CHARS = 6  # 短于此（加权）长度的字符串列表项，视为没说清楚


def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or 0xF900 <= o <= 0xFAFF


def weighted_len(s: str) -> int:
    """按信息量计长：CJK 表意文字计 2，其余字符计 1。

    为什么需要这个：契约里的 minLength 最初按英文习惯写（英文一个词 4~6 字符）。
    中文一个字的信息量约等于英文一个词，直接套用会把『加入顿帧与屏幕震动』
    这类简洁但完全具体的中文产出误杀。折算后同一套阈值在中英文产出上都合理，
    而 GLSL 这类纯 ASCII 源码不受影响（仍是严格的字符数）。
    """
    n = 0
    for ch in s or "":
        n += 2 if _is_cjk(ch) else 1
    return n


# ── 结构化输出契约 ─────────────────────────────────────────────────────────────
@dataclass
class LLMSkillSpec:
    """一项 C 类技能的产出契约。"""

    skill_id: str
    name: str
    system_prompt: str
    task_template: str
    output_schema: Dict[str, Any]
    acceptance: List[Dict[str, Any]] = field(default_factory=list)
    max_repairs: int = 2
    custom: Optional[Callable[[Dict[str, Any]], List[str]]] = None
    notes: str = ""

    @property
    def skeleton(self) -> str:
        """把 output_schema 渲染成可直接抄的 JSON 骨架。

        实测教训：只说"输出 JSON"而不给结构，模型会按自己的理解改名改层级
        （例如把 steps[].step 写成 steps[].decision），三次自修复也拉不回来。
        把骨架直接写进提示词，通过率才有意义。
        """
        return json.dumps(schema_skeleton(self.output_schema), ensure_ascii=False, indent=2)

    def build_prompt(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        ctx = json.dumps(context or {}, ensure_ascii=False, indent=2)
        return (self.task_template.format(task=task or "", context=ctx)
                + "\n\n你必须严格使用下面这个 JSON 结构（字段名、层级、数组长度都不得改动，"
                  "只允许替换其中的值；数组至少给到示例里的条数）：\n```json\n"
                + self.skeleton + "\n```")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "acceptance": list(self.acceptance),
            "max_repairs": self.max_repairs,
            "has_custom": self.custom is not None,
            "schema_required": list((self.output_schema or {}).get("required", [])),
            "notes": self.notes,
        }


@dataclass
class LLMSkillResult:
    skill_id: str
    status: str
    payload: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    attempts: int = 0
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    raw: str = ""

    @property
    def ok(self) -> bool:
        return self.status == LLMSkillStatus.OK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "status": self.status,
            "ok": self.ok,
            "payload": self.payload,
            "errors": list(self.errors),
            "provider": self.provider,
            "model": self.model,
            "attempts": self.attempts,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "raw_chars": len(self.raw),
        }


# ── 校验：在 agent_runtime 的 schema 校验之上补长度/数量/区间 ───────────────────
def validate_payload(value: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    """先跑 agent_runtime.validate_schema（已测过的类型/必填/枚举），再补定量约束。"""
    errors = validate_schema(value, schema, path)
    errors.extend(_schema_extras(value, schema, path))
    return errors


def _schema_extras(value: Any, schema: Dict[str, Any], path: str) -> List[str]:
    if not schema:
        return []
    errors: List[str] = []

    if isinstance(value, str):
        if "minLength" in schema and weighted_len(value.strip()) < schema["minLength"]:
            errors.append(f"{path}: 长度不足（要求加权长度 ≥{schema['minLength']}，"
                          f"实际 {weighted_len(value.strip())}）")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match pattern {schema['pattern']!r}")
        if "containsAny" in schema:
            need = schema["containsAny"]
            if not any(k.lower() in value.lower() for k in need):
                errors.append(f"{path}: must contain one of {need}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: list shorter than minItems {schema['minItems']}")
        items = schema.get("items")
        if isinstance(items, dict):
            for idx, item in enumerate(value):
                errors.extend(_schema_extras(item, items, f"{path}[{idx}]"))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")

    if isinstance(value, dict):
        props = schema.get("properties", {}) or {}
        for key, sub in props.items():
            if key in value and isinstance(sub, dict):
                errors.extend(_schema_extras(value[key], sub, f"{path}.{key}"))

    return errors


_ID_LIKE = re.compile(r"^[A-Za-z0-9_.\-]{1,24}$")


def _is_id_like(s: str) -> bool:
    """ID 类字符串（task1、node_a、weapon.sword）不是空话，不该被长度门槛误伤。

    实测教训：quest_tree_builder 的 prerequisites 里写 "task1" 被判为占位符，
    但那是一个合法的前驱任务 ID。长度门槛只对"要表达意思"的文本有意义。
    """
    return bool(_ID_LIKE.match(s or ""))


def check_acceptance_weighted(payload: Dict[str, Any],
                              rules: List[Dict[str, Any]]) -> List[str]:
    """acceptance 校验：长度门槛按加权长度判定，其余规则委托给 agent_runtime。

    为什么不能直接用 agent_runtime.check_acceptance：
    它用 len() 判 min_len。对英文合理，对中文等于把门槛抬高 2 倍——
    要求"评估结论 ≥40 字"在中文里是整整一段话，模型写不够就被判失败。
    实测 4 项技能因此被误杀，修正量纲后即通过。这不是放宽标准，是修正标尺。
    """
    errors: List[str] = []
    delegated: List[Dict[str, Any]] = []
    for rule in rules or []:
        if "min_len" not in rule:
            delegated.append(rule)
            continue
        field = rule.get("field", "")
        cur: Any = payload
        for part in field.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
            if cur is None:
                break
        if cur is None:
            errors.append(f"acceptance: {field} missing")
        elif not isinstance(cur, str):
            errors.append(f"acceptance: {field} 不是字符串")
        elif weighted_len(cur) < rule["min_len"]:
            errors.append(f"acceptance: {field} 长度不足"
                          f"（要求加权长度 ≥{rule['min_len']}，实际 {weighted_len(cur)}）")
    errors.extend(check_acceptance(payload, delegated))
    return errors


def find_placeholders(payload: Any, path: str = "$") -> List[str]:
    """递归找出"看起来像内容、其实是空话"的产出。

    两类必抓：
    1. 列表里的短/黑名单词 —— 例如 risks=["性能优化","排期"]；
    2. 风险项只写了 risk 没写 impact/mitigation —— 那是标题不是风险。
    """
    errors: List[str] = []

    if isinstance(payload, dict):
        if "risk" in payload and ("impact" not in payload or "mitigation" not in payload):
            errors.append(f"{path}: risk 项必须同时给出 impact 与 mitigation，"
                          f"否则只是标题不是风险")
        for k, v in payload.items():
            # 对象字段值同样要过黑名单：把"待定"写进 item 字段和写进列表里一样是空话。
            # 但这里不套长度门槛——有些字段本来就短（如 key:"C"），长度误伤代价太高。
            if isinstance(v, str) and v.strip().lower() in PLACEHOLDER_HINTS:
                errors.append(f"{path}.{k}: {v!r} 是占位/空话，必须给出具体内容")
            errors.extend(find_placeholders(v, f"{path}.{k}"))
        return errors

    if isinstance(payload, list):
        for idx, item in enumerate(payload):
            if isinstance(item, str):
                s = item.strip().rstrip("。.!！?？")
                if (not s) or s.lower() in PLACEHOLDER_HINTS:
                    errors.append(f"{path}[{idx}]: {item!r} 是黑名单占位/空话")
                elif weighted_len(s) < _MIN_LIST_ITEM_CHARS and not _is_id_like(s):
                    errors.append(f"{path}[{idx}]: {item!r} 疑似占位/空话，"
                                  f"要求 ≥{_MIN_LIST_ITEM_CHARS} 字且为具体表述")
            else:
                errors.extend(find_placeholders(item, f"{path}[{idx}]"))
        return errors

    return errors


def schema_skeleton(schema: Dict[str, Any]) -> Any:
    """把 output_schema 渲染成带占位值的示例结构，供提示词使用。"""
    if not schema:
        return {}
    stype = schema.get("type")

    if stype == "object" or (not stype and "properties" in schema):
        props = schema.get("properties", {}) or {}
        required = list(schema.get("required", []) or [])
        keys = [k for k in required if k in props] + \
               [k for k in props if k not in required]
        out: Dict[str, Any] = {}
        for k in keys:
            out[k] = schema_skeleton(props[k])
        return out

    if stype == "array":
        items = schema.get("items") or {"type": "string"}
        n = int(schema.get("minItems", 1) or 1)
        n = max(1, min(n, 3))  # 骨架不要过长，3 条足够示意
        return [schema_skeleton(items) for _ in range(n)]

    if stype == "number":
        lo, hi = schema.get("minimum"), schema.get("maximum")
        if lo is not None and hi is not None:
            return f"<数字 {lo}~{hi}>"
        return "<数字>"

    if stype == "boolean":
        return "<true 或 false>"

    if stype == "string":
        if "enum" in schema:
            return "|".join(str(e) for e in schema["enum"])
        if "pattern" in schema:
            return schema.get("pattern", "")
        n = int(schema.get("minLength", 8) or 8)
        return f"<中文，至少约 {max(2, n // 2)} 字>"

    return "<值>"


def _build_repair_prompt(previous: str, errors: List[str],
                         skeleton: str = "") -> str:
    return (
        "你上一次的输出没有通过校验，问题如下：\n"
        + "\n".join(f"- {e}" for e in errors[:15])
        + "\n\n要求：\n"
          "1. 逐条修正上述问题，不要删除字段来绕过校验；\n"
          "2. 禁止出现『性能优化』『排期』『待定』『TBD』这类没有信息量的表述；\n"
          "3. 只输出一个 ```json 围栏包裹的 JSON 对象，不要任何解释性散文。\n"
        + ("\n必须严格使用这个结构（字段名与层级不得改动）：\n```json\n"
           + skeleton + "\n```\n" if skeleton else "")
        + "\n上一次的输出：\n" + previous[:3000]
    )


# ── 适配器 ─────────────────────────────────────────────────────────────────────
class LLMSkillAdapter:
    """把 C 类技能契约变成一次可验收的真实 LLM 调用。

    llm_call 可注入（测试用确定性假调用）；不注入时走真实 LLMGateway。
    """

    def __init__(self, provider: str = "auto", model: Optional[str] = None,
                 max_repairs: int = 2, verbose: bool = False,
                 max_tokens: int = 16384, temperature: float = 0.4, timeout: int = 180,
                 llm_call: Optional[Callable[[str, str], Dict[str, Any]]] = None) -> None:
        self.provider = provider
        self.model = model
        self.max_repairs = max_repairs
        self.verbose = verbose
        # 结构化产出默认给足 token：实测 8192 会在多层嵌套 + 长数组时把末尾字段
        # 截断成空串，看起来像"模型漏填"，实际是额度不够。温度压低是为了结构稳定。
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self._llm_call = llm_call

    # ── 环境自检 ──────────────────────────────────────────────────────────
    def llm_ready(self) -> bool:
        if self._llm_call is not None:
            return True
        from core.llm_gateway import LLMGateway
        return bool(LLMGateway.available_providers())

    def preflight(self) -> Dict[str, Any]:
        from core.llm_gateway import LLMGateway
        avail = LLMGateway.available_providers() if self._llm_call is None else ["injected"]
        return {
            "llm_ready": bool(avail),
            "available_providers": avail,
            "status": LLMSkillStatus.OK if avail else NEEDS_LLM_CREDENTIALS,
            "how_to_fix": "" if avail else "配置 config/llm_endpoints.json 或任一 Provider 的 API Key。",
        }

    # ── 执行 ─────────────────────────────────────────────────────────────
    def run(self, spec: LLMSkillSpec, task: str,
            context: Optional[Dict[str, Any]] = None) -> LLMSkillResult:
        started = time.time()

        if not self.llm_ready():
            return LLMSkillResult(
                skill_id=spec.skill_id, status=NEEDS_LLM_CREDENTIALS,
                errors=[f"没有可用的 LLM 后端，{spec.name} 无法产出。"
                        f"未调用模型就不可能有产出，此处如实报 NEEDS_LLM_CREDENTIALS，"
                        f"不返回任何模板文本。"],
                latency_ms=int((time.time() - started) * 1000),
            )

        max_repairs = min(self.max_repairs, spec.max_repairs)
        cur_prompt = spec.build_prompt(task, context)
        last: Optional[LLMSkillResult] = None

        for attempt in range(max_repairs + 1):
            raw_resp = self._call(spec.system_prompt, cur_prompt)
            latency = int((time.time() - started) * 1000)
            if not raw_resp.get("success"):
                last = LLMSkillResult(
                    skill_id=spec.skill_id, status=LLMSkillStatus.LLM_ERROR,
                    errors=[raw_resp.get("error") or "LLM call failed"],
                    provider=raw_resp.get("provider", ""), model=raw_resp.get("model", ""),
                    attempts=attempt + 1, latency_ms=latency, raw=raw_resp.get("text", ""))
                cur_prompt = _build_repair_prompt(raw_resp.get("text", ""), last.errors, spec.skeleton)
                continue

            text = raw_resp.get("text", "") or ""
            parsed = extract_json(text)
            if not isinstance(parsed, dict):
                last = LLMSkillResult(
                    skill_id=spec.skill_id, status=LLMSkillStatus.JSON_INVALID,
                    errors=["输出不是可解析的 JSON 对象"],
                    provider=raw_resp.get("provider", ""), model=raw_resp.get("model", ""),
                    attempts=attempt + 1, latency_ms=latency, raw=text)
                cur_prompt = _build_repair_prompt(text, last.errors, spec.skeleton)
                continue

            errs = validate_payload(parsed, spec.output_schema)
            if errs:
                last = LLMSkillResult(
                    skill_id=spec.skill_id, status=LLMSkillStatus.SCHEMA_INVALID,
                    errors=errs, payload=parsed,
                    provider=raw_resp.get("provider", ""), model=raw_resp.get("model", ""),
                    attempts=attempt + 1, latency_ms=latency,
                    input_tokens=raw_resp.get("input_tokens", 0),
                    output_tokens=raw_resp.get("output_tokens", 0), raw=text)
                cur_prompt = _build_repair_prompt(text, errs, spec.skeleton)
                continue

            errs = check_acceptance_weighted(parsed, spec.acceptance)
            if errs:
                last = LLMSkillResult(
                    skill_id=spec.skill_id, status=LLMSkillStatus.ACCEPTANCE_FAILED,
                    errors=errs, payload=parsed,
                    provider=raw_resp.get("provider", ""), model=raw_resp.get("model", ""),
                    attempts=attempt + 1, latency_ms=latency,
                    input_tokens=raw_resp.get("input_tokens", 0),
                    output_tokens=raw_resp.get("output_tokens", 0), raw=text)
                cur_prompt = _build_repair_prompt(text, errs, spec.skeleton)
                continue

            errs = find_placeholders(parsed)
            if errs:
                last = LLMSkillResult(
                    skill_id=spec.skill_id, status=LLMSkillStatus.PLACEHOLDER_REJECTED,
                    errors=errs, payload=parsed,
                    provider=raw_resp.get("provider", ""), model=raw_resp.get("model", ""),
                    attempts=attempt + 1, latency_ms=latency,
                    input_tokens=raw_resp.get("input_tokens", 0),
                    output_tokens=raw_resp.get("output_tokens", 0), raw=text)
                cur_prompt = _build_repair_prompt(text, errs, spec.skeleton)
                continue

            if spec.custom is not None:
                errs = list(spec.custom(parsed) or [])
                if errs:
                    last = LLMSkillResult(
                        skill_id=spec.skill_id, status=LLMSkillStatus.ACCEPTANCE_FAILED,
                        errors=[f"custom: {e}" for e in errs], payload=parsed,
                        provider=raw_resp.get("provider", ""), model=raw_resp.get("model", ""),
                        attempts=attempt + 1, latency_ms=latency,
                        input_tokens=raw_resp.get("input_tokens", 0),
                        output_tokens=raw_resp.get("output_tokens", 0), raw=text)
                    cur_prompt = _build_repair_prompt(text, [f"custom: {e}" for e in errs], spec.skeleton)
                    continue

            out = LLMSkillResult(
                skill_id=spec.skill_id, status=LLMSkillStatus.OK, payload=parsed,
                provider=raw_resp.get("provider", ""), model=raw_resp.get("model", ""),
                attempts=attempt + 1, latency_ms=latency,
                input_tokens=raw_resp.get("input_tokens", 0),
                output_tokens=raw_resp.get("output_tokens", 0), raw=text)
            if last is not None:
                out.errors = [f"经 {attempt + 1} 次尝试后通过；此前失败原因: {'; '.join(last.errors[:5])}"]
            return out

        assert last is not None
        # 保留具体的失败类型（SCHEMA_INVALID / PLACEHOLDER_REJECTED / ...），
        # 只追加"重试已用尽"。抹成笼统的 EXHAUSTED 会掩盖真正的病因。
        last.errors = last.errors + [f"已重试修复 {max_repairs} 次仍不通过"]
        return last

    # ── 真实调用 ─────────────────────────────────────────────────────────
    def _call(self, system: str, prompt: str) -> Dict[str, Any]:
        if self._llm_call is not None:
            r = self._llm_call(system, prompt)
            return {"success": bool(r.get("success", True)), "text": r.get("text", ""),
                    "provider": r.get("provider", "injected"), "model": r.get("model", ""),
                    "error": r.get("error", ""), "input_tokens": 0, "output_tokens": 0}
        from core.llm_gateway import LLMGateway
        provider = self.provider if self.provider != "auto" else None
        if provider is None:
            avail = LLMGateway.available_providers()
            provider = avail[0] if avail else "openai_compat"
        gw = LLMGateway(provider=provider, model=self.model, verbose=self.verbose,
                        max_tokens=self.max_tokens, temperature=self.temperature,
                        timeout=self.timeout)
        resp = gw.call(prompt, system=system, use_cache=False,
                       max_tokens=self.max_tokens, temperature=self.temperature)
        return {"success": resp.success, "text": resp.text, "provider": str(resp.provider),
                "model": resp.model, "error": resp.error,
                "input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens}

    def run_skill(self, skill_id: str, task: str,
                  context: Optional[Dict[str, Any]] = None) -> LLMSkillResult:
        spec = get_spec(skill_id)
        if spec is None:
            return LLMSkillResult(skill_id=skill_id, status=LLMSkillStatus.NO_SPEC,
                                  errors=[f"{skill_id} 没有 C 类产出契约，无法执行。"
                                          f"先补契约再谈跑通——没有契约的调用等于许愿。"])
        return self.run(spec, task, context)


# ══════════════════════════════════════════════════════════════════════════════
# 24 项 C 类技能的产出契约
# ══════════════════════════════════════════════════════════════════════════════

_JSON_ONLY = (
    "语言要求：所有自然语言的值必须用简体中文（字段名保持英文），不要输出英文句子。\n"
    "类型要求：number 字段必须是裸数字，不要加引号、不要带单位（写 3 不写 \"3秒\"）；"
    "boolean 字段必须写 true / false。\n"
    "输出格式：只输出一个 ```json 围栏包裹的 JSON 对象，不要任何解释性散文、"
    "不要 Markdown 标题、不要前后缀。字段名用英文，值用中文。"
    "禁止出现『性能优化』『排期』『待定』『TBD』『等等』这类没有信息量的表述——"
    "每一条都要具体到能直接拿去做事。"
)


def _v_shader(payload: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    frag = str(payload.get("fragment_shader", "") or payload.get("shader_glsl", ""))
    if not frag.strip():
        errs.append("shader 源码为空")
        return errs
    if "void main" not in frag:
        errs.append("shader 源码缺少 void main 入口")
    if not re.search(r"gl_FragColor|out\s+vec4|pc_fragColor", frag):
        errs.append("shader 源码没有写出片元颜色（gl_FragColor / out vec4）")
    if frag.count("{") != frag.count("}"):
        errs.append("shader 源码大括号不配对")
    return errs


def _v_hex_palette(payload: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    for idx, p in enumerate(payload.get("palette", []) or []):
        hexv = str(p.get("hex", "")).strip()
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", hexv):
            errs.append(f"palette[{idx}].hex={hexv!r} 不是合法的 #RRGGBB")
    return errs


def _v_monotonic_difficulty(payload: Dict[str, Any]) -> List[str]:
    levels = payload.get("levels") or []
    vals = [l.get("difficulty_index") for l in levels if isinstance(l, dict)]
    if any(v is None for v in vals):
        return ["levels[].difficulty_index 存在缺失"]
    if any(vals[i] > vals[i + 1] for i in range(len(vals) - 1)):
        return [f"difficulty_index 非单调不减: {vals}"]
    return []


def _v_pity(payload: Dict[str, Any]) -> List[str]:
    """掉落权重之和必须为正，且保底阈值必须大于 0。"""
    table = payload.get("table") or []
    total = sum(float(t.get("weight", 0) or 0) for t in table if isinstance(t, dict))
    if total <= 0:
        return [f"掉落权重之和={total}，不能为 0"]
    pity = payload.get("pity") or {}
    if not isinstance(pity, dict) or float(pity.get("threshold", 0) or 0) <= 0:
        return ["pity.threshold 必须为正整数（没有保底就不能叫概率表）"]
    return []


def _v_tutorial_stealth(payload: Dict[str, Any]) -> List[str]:
    if int(payload.get("explicit_prompt_count", 99)) > 1:
        return [f"explicit_prompt_count={payload.get('explicit_prompt_count')}，"
                f"隐式引导最多允许 1 次显式提示"]
    return []


def _v_combo_tiers(payload: Dict[str, Any]) -> List[str]:
    tiers = payload.get("tiers") or []
    mults = [t.get("multiplier") for t in tiers if isinstance(t, dict)]
    if any(m is None for m in mults):
        return ["tiers[].multiplier 存在缺失"]
    if any(mults[i] > mults[i + 1] for i in range(len(mults) - 1)):
        return [f"multiplier 必须随 combo 单调不减: {mults}"]
    return []


_SPECS: List[LLMSkillSpec] = [

    # ── GDD 策划族（14）──────────────────────────────────────────────────
    LLMSkillSpec(
        skill_id="core_loop_design", name="核心玩法循环设计",
        system_prompt=(
            "你是核心玩法循环设计师。判断标准只有一条：玩家在 30 秒内能不能完整跑一遍"
            "『决策 → 操作 → 反馈 → 新决策』并愿意再来一次。循环不闭环的设计一律不合格。"
            "每一步必须写清玩家做什么、游戏反馈什么、耗时几秒。"
        ),
        task_template=(
            "为下面这款游戏设计核心玩法循环。要求单局微循环 ≤30 秒。\n\n"
            "任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY
        ),
        output_schema={
            "type": "object",
            "required": ["core_loop", "risks", "confidence"],
            "properties": {
                "core_loop": {"type": "object", "properties": {
                    "steps": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                        "step": {"type": "string", "minLength": 4},
                        "player_action": {"type": "string", "minLength": 4},
                        "feedback": {"type": "string", "minLength": 4},
                        "duration_seconds": {"type": "number", "minimum": 0.5},
                    }, "required": ["step", "player_action", "feedback", "duration_seconds"]}},
                    "loop_duration_seconds": {"type": "number", "minimum": 1, "maximum": 300},
                    "closure_reason": {"type": "string", "minLength": 25},
                }, "required": ["steps", "loop_duration_seconds", "closure_reason"]},
                "risks": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "risk": {"type": "string", "minLength": 6},
                    "impact": {"type": "string", "minLength": 6},
                    "mitigation": {"type": "string", "minLength": 6},
                }, "required": ["risk", "impact", "mitigation"]}},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        acceptance=[{"field": "core_loop.closure_reason", "min_len": 25},
                    {"field": "risks", "min_items": 2}],
    ),

    LLMSkillSpec(
        skill_id="economy_balance_math", name="数值经济平衡建模",
        system_prompt=(
            "你是游戏经济学家。产出必须是三端闭合的模型：产出端（sources）、消耗端（sinks）、"
            "沉淀端（stock）。只给公式不给假设等于没做——assumptions 必须写清你依赖了什么前提。"
        ),
        task_template="为下面的游戏建立数值经济模型。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["sources", "sinks", "stock", "assumptions"],
            "properties": {
                "sources": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "name": {"type": "string", "minLength": 4},
                    "formula": {"type": "string", "minLength": 6},
                    "unit": {"type": "string", "minLength": 2},
                }, "required": ["name", "formula", "unit"]}},
                "sinks": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "name": {"type": "string", "minLength": 4},
                    "formula": {"type": "string", "minLength": 6},
                    "unit": {"type": "string", "minLength": 2},
                }, "required": ["name", "formula", "unit"]}},
                "stock": {"type": "array", "minItems": 1, "items": {"type": "object"}},
                "assumptions": {"type": "array", "minItems": 3, "items": {"type": "string", "minLength": 10}},
            },
        },
        acceptance=[{"field": "sources", "min_items": 2}, {"field": "sinks", "min_items": 2},
                    {"field": "assumptions", "min_items": 3}],
    ),

    LLMSkillSpec(
        skill_id="level_curve_progression", name="关卡难度曲线规划",
        system_prompt=(
            "你是关卡节奏设计师。难度曲线必须单调不减（允许平台期，不允许倒退），"
            "每一关必须引入一样新东西——没有新机制的关卡是填充物。"
        ),
        task_template="规划下面的关卡难度曲线。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["levels", "rationale"],
            "properties": {
                "levels": {"type": "array", "minItems": 5, "items": {"type": "object", "properties": {
                    "level": {"type": "number", "minimum": 1},
                    "new_mechanic": {"type": "string", "minLength": 6},
                    "difficulty_index": {"type": "number", "minimum": 0, "maximum": 100},
                    "expected_deaths": {"type": "number", "minimum": 0},
                }, "required": ["level", "new_mechanic", "difficulty_index", "expected_deaths"]}},
                "rationale": {"type": "string", "minLength": 30},
            },
        },
        acceptance=[{"field": "levels", "min_items": 5}, {"field": "rationale", "min_len": 30}],
        custom=_v_monotonic_difficulty,
    ),

    LLMSkillSpec(
        skill_id="control_scheme_mapping", name="输入控制与键位映射",
        system_prompt=(
            "你是人机工效设计师。键位不是随便分的：高频动作必须落在最省力的位置，"
            "每个映射都要给出理由，冲突必须被显式列出而不是藏起来。"
        ),
        task_template="设计输入控制与键位映射。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["platform", "bindings", "ergonomics_notes"],
            "properties": {
                "platform": {"type": "string",
                             "enum": ["keyboard_mouse", "gamepad", "touch", "all"]},
                "bindings": {"type": "array", "minItems": 4, "items": {"type": "object", "properties": {
                    "action": {"type": "string", "minLength": 4},
                    "input": {"type": "string", "minLength": 1},
                    "rationale": {"type": "string", "minLength": 10},
                }, "required": ["action", "input", "rationale"]}},
                "conflicts": {"type": "array", "items": {"type": "string", "minLength": 8}},
                "ergonomics_notes": {"type": "string", "minLength": 30},
            },
        },
        acceptance=[{"field": "bindings", "min_items": 4},
                    {"field": "ergonomics_notes", "min_len": 30}],
    ),

    LLMSkillSpec(
        skill_id="narrative_dialogue_branching", name="分支剧情与对白设计",
        system_prompt=(
            "你是叙事设计师。对白要能演出人物性格，分支条件要可被程序判定"
            "（写清 condition 的可判定形式，不许写『玩家表现得善良』这种无法求值的条件）。"
        ),
        task_template="写分支剧情与对白。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["entry_node", "branches"],
            "properties": {
                "entry_node": {"type": "string", "minLength": 2},
                "branches": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "id": {"type": "string", "minLength": 2},
                    "condition": {"type": "string", "minLength": 6},
                    "speaker": {"type": "string", "minLength": 2},
                    "text": {"type": "string", "minLength": 12},
                    "leads_to": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 2}},
                }, "required": ["id", "condition", "speaker", "text", "leads_to"]}},
            },
        },
        acceptance=[{"field": "branches", "min_items": 3}],
    ),

    LLMSkillSpec(
        skill_id="quest_tree_builder", name="主支线任务树生成",
        system_prompt=(
            "你是任务设计师。每个任务必须有可判定的完成条件（exit_criteria），"
            "写不出完成条件的任务不许进入任务树。前驱关系不能成环。"
        ),
        task_template="生成主支线任务树。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["quests", "critical_path"],
            "properties": {
                "quests": {"type": "array", "minItems": 4, "items": {"type": "object", "properties": {
                    "id": {"type": "string", "minLength": 2},
                    "title": {"type": "string", "minLength": 6},
                    "type": {"type": "string", "enum": ["main", "side"]},
                    "prerequisites": {"type": "array", "items": {"type": "string"}},
                    "rewards": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 4}},
                    "exit_criteria": {"type": "string", "minLength": 12},
                }, "required": ["id", "title", "type", "exit_criteria"]}},
                "critical_path": {"type": "array", "minItems": 2, "items": {"type": "string", "minLength": 2}},
            },
        },
        acceptance=[{"field": "quests", "min_items": 4}, {"field": "critical_path", "min_items": 2}],
    ),

    LLMSkillSpec(
        skill_id="inventory_slot_matrix", name="背包网格与道具属性表",
        system_prompt=(
            "你是系统设计者。道具属性维度必须具体到能直接落成数据表字段，"
            "每个字段写明类型。示例道具要给出占用格子的形状。"
        ),
        task_template="设计背包网格与道具属性表。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["grid", "item_schema", "sample_items"],
            "properties": {
                "grid": {"type": "object", "properties": {
                    "width": {"type": "number", "minimum": 1},
                    "height": {"type": "number", "minimum": 1},
                }, "required": ["width", "height"]},
                "item_schema": {"type": "array", "minItems": 4, "items": {"type": "object", "properties": {
                    "field": {"type": "string", "minLength": 2},
                    "type": {"type": "string", "minLength": 2},
                    "description": {"type": "string", "minLength": 6},
                }, "required": ["field", "type", "description"]}},
                "sample_items": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "name": {"type": "string", "minLength": 4},
                    "rarity": {"type": "string", "minLength": 2},
                    "shape": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 2}},
                }, "required": ["name", "rarity", "shape"]}},
            },
        },
        acceptance=[{"field": "item_schema", "min_items": 4}, {"field": "sample_items", "min_items": 2}],
    ),

    LLMSkillSpec(
        skill_id="drop_rate_rng_table", name="掉落概率与伪随机发生",
        system_prompt=(
            "你是数值策划。掉落表必须给出权重、保底阈值与保底目标物——"
            "没有保底的纯随机会制造极端负面体验，这是设计缺陷不是概率趣味。"
        ),
        task_template="设计掉落概率表与保底机制。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["table", "pity"],
            "properties": {
                "table": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "item": {"type": "string", "minLength": 4},
                    "weight": {"type": "number", "minimum": 0},
                    "rarity": {"type": "string", "minLength": 2},
                }, "required": ["item", "weight", "rarity"]}},
                "pity": {"type": "object", "properties": {
                    "threshold": {"type": "number", "minimum": 1},
                    "guaranteed": {"type": "string", "minLength": 4},
                }, "required": ["threshold", "guaranteed"]},
            },
        },
        acceptance=[{"field": "table", "min_items": 3}],
        custom=_v_pity,
    ),

    LLMSkillSpec(
        skill_id="camera_viewport_rules", name="摄像机视口跟随规则",
        system_prompt=(
            "你是镜头设计师。死区、阻尼、前瞻量三个参数是手感的全部，"
            "每个值都要说明为什么是这个量级（大了会飘、小了会抖）。"
        ),
        task_template="设计摄像机视口跟随规则。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["mode", "deadzone", "damping", "lookahead", "rules"],
            "properties": {
                "mode": {"type": "string", "enum": ["lock", "follow", "predictive", "dual"]},
                "deadzone": {"type": "object", "properties": {
                    "x": {"type": "number", "minimum": 0}, "y": {"type": "number", "minimum": 0},
                }, "required": ["x", "y"]},
                "damping": {"type": "number", "minimum": 0, "maximum": 1},
                "lookahead": {"type": "number", "minimum": 0},
                "rules": {"type": "array", "minItems": 3, "items": {"type": "string", "minLength": 12}},
            },
        },
        acceptance=[{"field": "rules", "min_items": 3}],
    ),

    LLMSkillSpec(
        skill_id="score_combo_multiplier", name="得分连击与奖励机制",
        system_prompt=(
            "你是手感设计师。倍率必须随连击数单调不减，窗口时长决定连击难度，"
            "衰减规则要写清是归零还是逐级降。"
        ),
        task_template="设计得分连击与倍率机制。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["window_seconds", "tiers", "decay", "rationale"],
            "properties": {
                "window_seconds": {"type": "number", "minimum": 0.2},
                "tiers": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "combo": {"type": "number", "minimum": 1},
                    "multiplier": {"type": "number", "minimum": 1},
                }, "required": ["combo", "multiplier"]}},
                "decay": {"type": "string", "minLength": 8},
                "rationale": {"type": "string", "minLength": 25},
            },
        },
        acceptance=[{"field": "tiers", "min_items": 3}, {"field": "rationale", "min_len": 25}],
        custom=_v_combo_tiers,
    ),

    LLMSkillSpec(
        skill_id="boss_phase_transition", name="Boss 多阶段变身机制",
        system_prompt=(
            "你是 Boss 战设计师。每个阶段必须有清晰的预告（telegraph）——"
            "玩家读不出招就是设计者的问题。阶段切换的戏剧节奏要写清。"
        ),
        task_template="设计 Boss 多阶段变身机制。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["phases", "readability_notes"],
            "properties": {
                "phases": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "phase": {"type": "number", "minimum": 1},
                    "hp_threshold": {"type": "number", "minimum": 0, "maximum": 1},
                    "new_patterns": {"type": "array", "minItems": 1,
                                     "items": {"type": "string", "minLength": 8}},
                    "telegraph": {"type": "string", "minLength": 12},
                }, "required": ["phase", "hp_threshold", "new_patterns", "telegraph"]}},
                "readability_notes": {"type": "string", "minLength": 30},
            },
        },
        acceptance=[{"field": "phases", "min_items": 2}, {"field": "readability_notes", "min_len": 30}],
    ),

    LLMSkillSpec(
        skill_id="ui_hud_wireframe", name="HUD 仪表盘线框布局",
        system_prompt=(
            "你是 HUD 设计师。每个区域要给出锚点、承载内容与优先级（1 最高）。"
            "优先级决定了空间分配：低优先级信息不配占据视觉中心。"
        ),
        task_template="设计 HUD 线框布局。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["regions", "rationale"],
            "properties": {
                "regions": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "id": {"type": "string", "minLength": 3},
                    "anchor": {"type": "string", "minLength": 6},
                    "contents": {"type": "array", "minItems": 1,
                                 "items": {"type": "string", "minLength": 6}},
                    "priority": {"type": "number", "minimum": 1, "maximum": 5},
                }, "required": ["id", "anchor", "contents", "priority"]}},
                "rationale": {"type": "string", "minLength": 30},
            },
        },
        acceptance=[{"field": "regions", "min_items": 3}, {"field": "rationale", "min_len": 30}],
    ),

    LLMSkillSpec(
        skill_id="tutorial_stealth_guide", name="沉浸式新手引导流程",
        system_prompt=(
            "你是新手引导设计师。隐式引导的硬指标：整个流程最多 1 次显式文字提示，"
            "其余必须靠关卡布局、敌人站位、光线引导玩家自己发现。"
        ),
        task_template="设计沉浸式新手引导流程。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["steps", "explicit_prompt_count"],
            "properties": {
                "steps": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "beat": {"type": "string", "minLength": 4},
                    "player_action": {"type": "string", "minLength": 4},
                    "hint_kind": {"type": "string",
                                  "enum": ["environment", "npc", "ui", "none"]},
                    "text": {"type": "string", "minLength": 8},
                }, "required": ["beat", "player_action", "hint_kind", "text"]}},
                "explicit_prompt_count": {"type": "number", "minimum": 0, "maximum": 3},
            },
        },
        acceptance=[{"field": "steps", "min_items": 3}],
        custom=_v_tutorial_stealth,
    ),

    LLMSkillSpec(
        skill_id="accessibility_color_blind", name="色盲色弱无障碍配色",
        system_prompt=(
            "你是无障碍设计专家。配色必须给出十六进制值，并逐一说明在红色盲/绿色盲/蓝色盲"
            "三种模拟下的可辨性。只靠色相区分信息的设计一律不合格，必须叠加明度或形状差异。"
        ),
        task_template="设计色盲友好的配色方案。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["palette", "simulation", "verdict"],
            "properties": {
                "palette": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "name": {"type": "string", "minLength": 3},
                    "hex": {"type": "string", "pattern": r"^#[0-9A-Fa-f]{6}$"},
                    "role": {"type": "string", "minLength": 4},
                }, "required": ["name", "hex", "role"]}},
                "simulation": {"type": "object", "properties": {
                    "protanopia": {"type": "string", "minLength": 12},
                    "deuteranopia": {"type": "string", "minLength": 12},
                    "tritanopia": {"type": "string", "minLength": 12},
                }, "required": ["protanopia", "deuteranopia", "tritanopia"]},
                "verdict": {"type": "string", "minLength": 20},
            },
        },
        acceptance=[{"field": "palette", "min_items": 3}, {"field": "verdict", "min_len": 20}],
        custom=_v_hex_palette,
    ),

    # ── Logic 族（3）────────────────────────────────────────────────────
    LLMSkillSpec(
        skill_id="hypercasual_ad_monetization", name="超轻交互变现与广告契约",
        system_prompt=(
            "你是超休闲商业化设计师。硬约束：单局 ≤30 秒、首日留存优先于首日收入。"
            "每个广告点位都要给出频控，不写频控的广告位等于在赶走玩家。"
        ),
        task_template="设计广告点位与变现契约。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["ad_slots", "first_session", "verdict"],
            "properties": {
                "ad_slots": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "placement": {"type": "string", "minLength": 6},
                    "trigger": {"type": "string", "minLength": 8},
                    "frequency_cap": {"type": "string", "minLength": 8},
                }, "required": ["placement", "trigger", "frequency_cap"]}},
                "first_session": {"type": "object", "properties": {
                    "impression_target": {"type": "number", "minimum": 0},
                    "retention_risk": {"type": "string", "minLength": 15},
                }, "required": ["impression_target", "retention_risk"]},
                "verdict": {"type": "string", "minLength": 25},
            },
        },
        acceptance=[{"field": "ad_slots", "min_items": 2}, {"field": "verdict", "min_len": 25}],
    ),

    LLMSkillSpec(
        skill_id="wechat_social_viral_loop", name="微信社交裂变循环",
        system_prompt=(
            "你是社交裂变设计师，熟悉微信小游戏开放数据域与带参分享卡片的边界。"
            "任何需要获取用户敏感关系链或违反平台规范的机制一律不许提；"
            "privacy_constraints 必须写清踩不得的线。"
        ),
        task_template="设计微信社交裂变循环与分享卡片。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["loop", "share_card", "privacy_constraints"],
            "properties": {
                "loop": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "step": {"type": "string", "minLength": 6},
                    "mechanism": {"type": "string", "minLength": 12},
                    "expected_k_factor_contribution": {"type": "number", "minimum": 0},
                }, "required": ["step", "mechanism", "expected_k_factor_contribution"]}},
                "share_card": {"type": "object", "properties": {
                    "title": {"type": "string", "minLength": 6},
                    "desc": {"type": "string", "minLength": 10},
                    "image_concept": {"type": "string", "minLength": 12},
                }, "required": ["title", "desc", "image_concept"]},
                "privacy_constraints": {"type": "array", "minItems": 2,
                                        "items": {"type": "string", "minLength": 12}},
            },
        },
        acceptance=[{"field": "loop", "min_items": 3}, {"field": "privacy_constraints", "min_items": 2}],
    ),

    LLMSkillSpec(
        skill_id="review_privacy_hardening", name="隐私合规与防沉迷加固",
        system_prompt=(
            "你是合规文案与隐私设计专家。隐私弹窗的文案必须能让普通玩家看懂"
            "（不许用『为提升服务质量我们可能收集』这种含糊表述）；"
            "未成年人防沉迷必须给出具体的时长与时段限制。"
        ),
        task_template="编写隐私授权弹窗与防沉迷合规方案。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["dialogs", "compliance", "minor_protection"],
            "properties": {
                "dialogs": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "scene": {"type": "string", "minLength": 6},
                    "trigger": {"type": "string", "minLength": 8},
                    "title": {"type": "string", "minLength": 6},
                    "body": {"type": "string", "minLength": 20},
                    "buttons": {"type": "array", "minItems": 2,
                                "items": {"type": "string", "minLength": 2}},
                }, "required": ["scene", "trigger", "title", "body", "buttons"]}},
                "compliance": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "requirement": {"type": "string", "minLength": 10},
                    "source": {"type": "string", "minLength": 6},
                    "status": {"type": "string", "enum": ["met", "partial", "missing"]},
                }, "required": ["requirement", "source", "status"]}},
                "minor_protection": {"type": "object", "properties": {
                    "daily_minutes": {"type": "number", "minimum": 0},
                    "curfew": {"type": "string", "minLength": 8},
                }, "required": ["daily_minutes", "curfew"]},
            },
        },
        acceptance=[{"field": "dialogs", "min_items": 2}, {"field": "compliance", "min_items": 3}],
    ),

    # ── Rendering 族（2）────────────────────────────────────────────────
    LLMSkillSpec(
        skill_id="webgl_shader_pipeline", name="WebGL 基础着色器管线",
        system_prompt=(
            "你是 WebGL 着色器工程师，输出 WebGL1 / GLSL ES 1.00 源码。"
            "必须可直接编译：包含 precision 声明、varying、uniform 与 void main。"
            "片元着色器必须写出颜色（gl_FragColor）。"
            "注意：源码生成后仍需经真实编译验证，未验证前不得声称可用。"
        ),
        task_template="编写 WebGL 着色器管线源码。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["vertex_shader", "fragment_shader", "uniforms", "verification"],
            "properties": {
                "vertex_shader": {"type": "string", "minLength": 60},
                "fragment_shader": {"type": "string", "minLength": 60},
                "uniforms": {"type": "array", "minItems": 1, "items": {"type": "object", "properties": {
                    "name": {"type": "string", "minLength": 2},
                    "type": {"type": "string", "minLength": 4},
                    "default": {"type": "string", "minLength": 1},
                }, "required": ["name", "type", "default"]}},
                "verification": {"type": "string", "minLength": 20},
            },
        },
        acceptance=[{"field": "fragment_shader", "min_len": 60},
                    {"field": "verification", "min_len": 20}],
        custom=_v_shader,
    ),

    LLMSkillSpec(
        skill_id="tangent_normal_brdf_shader", name="切线空间法线与微表面 BRDF",
        system_prompt=(
            "你是 PBR 着色器工程师。输出 GLSL 源码，必须显式处理切线空间法线变换，"
            "并采用微表面 BRDF（GGX / Schlick 菲涅尔 / Smith 几何项任一组合）。"
            "源码生成后仍需真机渲染验证，未验证前不得声称可用。"
        ),
        task_template="编写切线空间法线与微表面 BRDF 着色器。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["shader_glsl", "uniforms", "notes"],
            "properties": {
                "shader_glsl": {"type": "string", "minLength": 120,
                                "containsAny": ["GGX", "ggx", "Fresnel", "fresnel", "BRDF"]},
                "uniforms": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "name": {"type": "string", "minLength": 2},
                    "type": {"type": "string", "minLength": 4},
                    "default": {"type": "string", "minLength": 1},
                }, "required": ["name", "type", "default"]}},
                "notes": {"type": "string", "minLength": 25},
            },
        },
        acceptance=[{"field": "shader_glsl", "min_len": 120}, {"field": "notes", "min_len": 25}],
        custom=_v_shader,
    ),

    # ── Audio 族（1）────────────────────────────────────────────────────
    LLMSkillSpec(
        skill_id="adaptive_music_layering", name="自适应多轨音乐动态混音",
        system_prompt=(
            "你是游戏配乐设计师与音频总监。分层配器必须写清每层何时进入、何时退出，"
            "过渡必须对齐小节（beats），不对齐的过渡会听出接缝。"
        ),
        task_template="设计自适应多轨音乐分层方案。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["layers", "transitions", "key", "bpm"],
            "properties": {
                "layers": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "name": {"type": "string", "minLength": 4},
                    "instruments": {"type": "array", "minItems": 1,
                                    "items": {"type": "string", "minLength": 4}},
                    "enters_on": {"type": "string", "minLength": 8},
                    "exits_on": {"type": "string", "minLength": 8},
                }, "required": ["name", "instruments", "enters_on", "exits_on"]}},
                "transitions": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "from": {"type": "string", "minLength": 3},
                    "to": {"type": "string", "minLength": 3},
                    "method": {"type": "string", "minLength": 8},
                    "beats": {"type": "number", "minimum": 1},
                }, "required": ["from", "to", "method", "beats"]}},
                "key": {"type": "string", "minLength": 2},
                "bpm": {"type": "number", "minimum": 40, "maximum": 220},
            },
        },
        acceptance=[{"field": "layers", "min_items": 3}, {"field": "transitions", "min_items": 2}],
    ),

    # ── QA 族（4）───────────────────────────────────────────────────────
    LLMSkillSpec(
        skill_id="difficulty_kill_ratio_eval", name="击杀比与挫败感评估",
        system_prompt=(
            "你是难度评估专家。评估必须基于给出的真实对局数据，不许凭感觉下结论；"
            "每条建议必须绑定一个可观测指标，否则无从验证改善与否。"
        ),
        task_template="评估击杀比与挫败感。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["metrics", "assessment", "recommendations"],
            "properties": {
                "metrics": {"type": "object", "properties": {
                    "attempts": {"type": "number", "minimum": 0},
                    "deaths": {"type": "number", "minimum": 0},
                    "kill_ratio": {"type": "number", "minimum": 0},
                }, "required": ["attempts", "deaths", "kill_ratio"]},
                "assessment": {"type": "string", "minLength": 40},
                "recommendations": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "issue": {"type": "string", "minLength": 10},
                    "suggestion": {"type": "string", "minLength": 15},
                    "observable_metric": {"type": "string", "minLength": 8},
                }, "required": ["issue", "suggestion", "observable_metric"]}},
            },
        },
        acceptance=[{"field": "assessment", "min_len": 40}, {"field": "recommendations", "min_items": 2}],
    ),

    LLMSkillSpec(
        skill_id="telemetry_funnel_analytics", name="新手漏斗与转化分析",
        system_prompt=(
            "你是数据分析师。漏斗数值要算准（drop_off_rate = 1 - 下一步/当前步），"
            "归因结论必须区分『相关』与『因果』，假设必须给出验证方法。"
        ),
        task_template="分析新手引导漏斗与转化。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["funnel", "bottleneck", "hypotheses"],
            "properties": {
                "funnel": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "step": {"type": "string", "minLength": 4},
                    "event": {"type": "string", "minLength": 4},
                    "users": {"type": "number", "minimum": 0},
                    "drop_off_rate": {"type": "number", "minimum": 0, "maximum": 1},
                }, "required": ["step", "event", "users", "drop_off_rate"]}},
                "bottleneck": {"type": "string", "minLength": 20},
                "hypotheses": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "hypothesis": {"type": "string", "minLength": 15},
                    "test": {"type": "string", "minLength": 15},
                }, "required": ["hypothesis", "test"]}},
            },
        },
        acceptance=[{"field": "funnel", "min_items": 3}, {"field": "bottleneck", "min_len": 20},
                    {"field": "hypotheses", "min_items": 2}],
    ),

    LLMSkillSpec(
        skill_id="first_principles_structural_audit", name="第一性原则结构审查",
        system_prompt=(
            "你是第一性原则审查官。做法：把结论拆到不可再拆的前提，逐个问"
            "『这是公理还是推导出来的』。凡是『行业都这么做』『通常如此』"
            "这类来源，一律标记为未证成的前提。"
        ),
        task_template="对下面的设计做第一性原则审查。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["assumptions", "findings", "verdict"],
            "properties": {
                "assumptions": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
                    "assumption": {"type": "string", "minLength": 12},
                    "is_derived_or_axiom": {"type": "string",
                                            "enum": ["axiom", "derived", "unjustified"]},
                    "evidence": {"type": "string", "minLength": 12},
                }, "required": ["assumption", "is_derived_or_axiom", "evidence"]}},
                "findings": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "finding": {"type": "string", "minLength": 15},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "reasoning": {"type": "string", "minLength": 20},
                }, "required": ["finding", "severity", "reasoning"]}},
                "verdict": {"type": "string", "minLength": 30},
            },
        },
        acceptance=[{"field": "assumptions", "min_items": 3}, {"field": "findings", "min_items": 2},
                    {"field": "verdict", "min_len": 30}],
    ),

    LLMSkillSpec(
        skill_id="anti_rubber_stamp_veto", name="反伪通过与否决审查",
        system_prompt=(
            "你是反橡皮图章审查官，职责是对『已通过』这件事本身再审查一次。"
            "规则：每一条被声明为通过的结论，都必须列出你亲眼看到的证据；"
            "看不到证据的一律判 not_verified，并给出否决理由。"
            "你存在的意义就是不让任何东西靠『看起来没问题』过关。"
        ),
        task_template="对下面这批『已通过』的结论做反伪通过审查。\n\n任务：{task}\n上下文：{context}\n\n" + _JSON_ONLY,
        output_schema={
            "type": "object",
            "required": ["claims", "veto"],
            "properties": {
                "claims": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
                    "claim": {"type": "string", "minLength": 10},
                    "evidence_seen": {"type": "string", "minLength": 15},
                    "verdict": {"type": "string",
                                "enum": ["verified", "not_verified", "contradicted"]},
                    "why": {"type": "string", "minLength": 15},
                }, "required": ["claim", "evidence_seen", "verdict", "why"]}},
                "veto": {"type": "boolean"},
                "rationale": {"type": "string", "minLength": 25},
            },
        },
        acceptance=[{"field": "claims", "min_items": 2}],
    ),
]

C_SKILL_SPECS: Dict[str, LLMSkillSpec] = {s.skill_id: s for s in _SPECS}


def get_spec(skill_id: str) -> Optional[LLMSkillSpec]:
    return C_SKILL_SPECS.get(skill_id)


def spec_ids() -> List[str]:
    return sorted(C_SKILL_SPECS)


def specs_cover_classification() -> List[str]:
    """自检：分类表里标 C 的技能，必须每一项都有产出契约（没契约就是空头支票）。"""
    from core.skill_classification import C_SKILLS
    return [sid for sid in C_SKILLS if sid not in C_SKILL_SPECS]
