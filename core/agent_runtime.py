"""core/agent_runtime.py: 专家 Agent 运行时（W1）。

与旧 `agents/base_agent.py` 的根本区别：
  旧实现 `perform_action()` 把入参原样回显并 return status="success" —— 那是花名册，不是 agent。
  本运行时要求：
    1. 每张卡有系统提示词、输入/输出契约、验收规则（见 core/role_cards.py）；
    2. 输出必须是结构化 JSON，且通过输出 schema 校验；
    3. 输出必须通过该卡自带的 acceptance 规则，否则判 ACCEPTANCE_FAILED；
    4. **LLM 不可用时返回 NEEDS_LLM_CREDENTIALS，绝不返回模板文本冒充专家产出。**

最后一条是红线。宁可空着，不可伪造。
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.role_cards import AgentTier, RoleCard, get_card
from core.llm_gateway import LLMGateway


NEEDS_LLM_CREDENTIALS = "NEEDS_LLM_CREDENTIALS"


class AgentStatus:
    OK = "OK"
    NEEDS_LLM_CREDENTIALS = NEEDS_LLM_CREDENTIALS
    LLM_ERROR = "LLM_ERROR"
    JSON_INVALID = "JSON_INVALID"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    ACCEPTANCE_FAILED = "ACCEPTANCE_FAILED"
    UNKNOWN_CARD = "UNKNOWN_CARD"
    INPUT_INVALID = "INPUT_INVALID"


@dataclass
class AgentOutput:
    """一次专家产出的完整记录。payload 为 None 时表示没有真实产出。"""
    card_id: str
    status: str
    payload: Optional[Dict[str, Any]] = None
    raw: str = ""
    errors: List[str] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    created_at: float = field(default_factory=time.time)

    @property
    def ok(self) -> bool:
        return self.status == AgentStatus.OK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "status": self.status,
            "payload": self.payload,
            "raw": self.raw,
            "errors": list(self.errors),
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at,
        }


# ─── 轻量 JSON Schema 校验（只支持本平台用到的子集，不引第三方依赖） ───────────
_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
}


def validate_schema(value: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    """返回错误列表；空列表表示通过。"""
    errors: List[str] = []
    if not schema:
        return errors

    # 本平台 output_schema 里 properties 的值允许是类型名字符串或子 schema
    expected = schema.get("type")
    if expected:
        py_type = _TYPE_MAP.get(expected)
        if py_type is None:
            errors.append(f"{path}: unknown schema type '{expected}'")
            return errors
        if expected == "number" and isinstance(value, bool):
            errors.append(f"{path}: expected number, got bool")
        elif not isinstance(value, py_type):
            errors.append(f"{path}: expected {expected}, got {type(value).__name__}")
            return errors

    if expected == "object" or (isinstance(value, dict) and "properties" in schema):
        props = schema.get("properties", {}) or {}
        for key in schema.get("required", []) or []:
            if key not in value:
                errors.append(f"{path}.{key}: required but missing")
        for key, sub in props.items():
            if key not in value:
                continue
            if isinstance(sub, str):
                sub = {"type": sub}
            errors.extend(validate_schema(value[key], sub, f"{path}.{key}"))

    if expected == "array" and isinstance(value, list):
        items = schema.get("items")
        if isinstance(items, str):
            items = {"type": items}
        if items:
            for idx, item in enumerate(value):
                errors.extend(validate_schema(item, items, f"{path}[{idx}]"))

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {schema['enum']}")

    return errors


# ─── 验收规则校验 ─────────────────────────────────────────────────────────────
def _dig(payload: Dict[str, Any], dotted: str) -> Any:
    cur: Any = payload
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def check_acceptance(payload: Dict[str, Any], rules: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    for rule in rules or []:
        fname = rule.get("field", "")
        val = _dig(payload, fname)
        if val is None:
            errors.append(f"acceptance: {fname} missing")
            continue
        if "enum" in rule and val not in rule["enum"]:
            errors.append(f"acceptance: {fname}={val!r} not in {rule['enum']}")
        if "min_len" in rule:
            if not isinstance(val, str) or len(val) < rule["min_len"]:
                errors.append(f"acceptance: {fname} length < {rule['min_len']}")
        if "min_items" in rule:
            if not isinstance(val, list) or len(val) < rule["min_items"]:
                errors.append(f"acceptance: {fname} items < {rule['min_items']}")
        if "min" in rule and isinstance(val, (int, float)) and val < rule["min"]:
            errors.append(f"acceptance: {fname} < {rule['min']}")
        if "max" in rule and isinstance(val, (int, float)) and val > rule["max"]:
            errors.append(f"acceptance: {fname} > {rule['max']}")
    return errors


# ─── JSON 抽取 ────────────────────────────────────────────────────────────────
_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def extract_json(text: str) -> Optional[Any]:
    """从 LLM 输出中抽取 JSON。优先围栏代码块，其次首个 {...} 平衡块。"""
    if not text:
        return None
    m = _JSON_BLOCK.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:idx + 1])
                except json.JSONDecodeError:
                    return None
    return None


# ─── 会话与运行时 ─────────────────────────────────────────────────────────────
class AgentSession:
    """一个专家的多轮会话。LEAD/SPECIALIST 用 run()，ADVISOR 用 consult()。"""

    def __init__(self, card: RoleCard, runtime: "AgentRuntime"):
        self.card = card
        self.runtime = runtime
        self.messages: List[Dict[str, str]] = []
        self.turns: int = 0

    def _build_prompt(self, task: str, context: Dict[str, Any]) -> str:
        schema_hint = json.dumps(self.card.output_schema, ensure_ascii=False)
        ctx = json.dumps(context or {}, ensure_ascii=False)
        acc_hint = "\n".join(f"  - {r}" for r in self.card.acceptance) or "  - （无）"
        return (
            f"# 任务\n{task}\n\n"
            f"# 上下文\n{ctx}\n\n"
            f"# 你的输出必须满足的 JSON Schema\n{schema_hint}\n\n"
            f"# 硬性要求\n"
            f"1. 只输出一个 JSON 对象，使用 ```json 围栏包裹，不要输出任何额外文字。\n"
            f"2. 所有必填字段必须出现且真实填写，不允许占位符、不允许留空字符串。\n"
            f"3. 枚举字段只能取给定值，**必须原样使用英文枚举值**，不要翻译成中文。\n"
            f"4. 数组字段必须满足最小条目数。\n"
            f"5. 你无法确认或无法执行的事项，写进 unverifiable / blockers / NEEDS_* 字段，不要编造。\n\n"
            f"# 验收规则（违反即判失败）\n{acc_hint}\n"
        )

    def ask(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        return self.runtime._execute(self.card, self._build_prompt(task, context or {}), self)

    def consult(self, question: str, context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        """ADVISOR 档：单次咨询，产出意见。同样强制 JSON，同样过验收。"""
        prompt = (
            f"# 咨询问题\n{question}\n\n# 上下文\n{json.dumps(context or {}, ensure_ascii=False)}\n\n"
            f"# 输出要求\n只输出一个 ```json 围栏包裹的 JSON 对象，字段："
            f"opinion(string)、concerns(array)、suggestions(array)、confidence(number 0-1)。"
        )
        return self.runtime._execute(self.card, prompt, self)


class AgentRuntime:
    """专家运行时的唯一入口。所有 CLI / HTTP / MCP 调用都必须经过它。"""

    def __init__(self, provider: str = "auto", model: Optional[str] = None,
                 verbose: bool = False, max_repairs: int = 2):
        self.provider = provider
        self.model = model
        self.verbose = verbose
        self.max_repairs = max_repairs   # 校验失败后的自愈重试次数，用尽仍不过即判失败
        self._sessions: Dict[str, AgentSession] = {}

    @staticmethod
    def _build_repair_prompt(previous: str, errors: List[str]) -> str:
        """把校验错误回喂给模型重改。修复次数用尽仍不过则判失败，不放宽规则。"""
        return (
            f"你上一次的输出未通过校验，错误如下：\n"
            + "\n".join(f"  - {e}" for e in errors)
            + f"\n\n上一次的输出：\n{previous[:3000]}\n\n"
            f"请修正上述问题，重新只输出一个 ```json 围栏包裹的 JSON 对象。"
            f"枚举值必须使用英文原值，不要翻译。"
        )

    # ── 环境自检 ──────────────────────────────────────────────────────────────
    def available_providers(self) -> List[str]:
        return LLMGateway.available_providers()

    def llm_ready(self) -> bool:
        return bool(self.available_providers())

    def preflight(self) -> Dict[str, Any]:
        """诚实的环境自检：不粉饰，缺什么列什么。"""
        avail = self.available_providers()
        return {
            "llm_ready": bool(avail),
            "available_providers": avail,
            "status": AgentStatus.OK if avail else NEEDS_LLM_CREDENTIALS,
            "how_to_fix": (
                ""
                if avail
                else "在 .env 或环境变量中配置至少一个：GEMINI_API_KEY / DEEPSEEK_API_KEY / "
                     "OPENAI_API_KEY / ANTHROPIC_API_KEY，或本地启动 Ollama。"
            ),
        }

    # ── 激活与执行 ────────────────────────────────────────────────────────────
    def activate(self, card_id: str) -> AgentSession:
        card = get_card(card_id)
        if card is None:
            raise KeyError(f"unknown role card: {card_id}")
        if card_id not in self._sessions:
            self._sessions[card_id] = AgentSession(card, self)
        return self._sessions[card_id]

    def run(self, card_id: str, task: str, context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        card = get_card(card_id)
        if card is None:
            return AgentOutput(card_id=card_id, status=AgentStatus.UNKNOWN_CARD,
                               errors=[f"unknown role card: {card_id}"])
        # 环境缺失优先于输入校验：没 LLM 就是没 LLM，不要把原因说成参数问题
        if not self.llm_ready():
            return AgentOutput(
                card_id=card_id,
                status=NEEDS_LLM_CREDENTIALS,
                payload=None,
                errors=[f"没有可用的 LLM 后端，{card.name} 无法产出。"],
            )
        missing = validate_schema(context or {}, card.input_schema)
        if missing and card.input_schema.get("required"):
            # 输入缺必填项时明确告知，而不是让 LLM 自己脑补
            return AgentOutput(card_id=card_id, status=AgentStatus.INPUT_INVALID, errors=missing)
        return self.activate(card_id).ask(task, context or {})

    def consult(self, card_id: str, question: str,
                context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        if get_card(card_id) is None:
            return AgentOutput(card_id=card_id, status=AgentStatus.UNKNOWN_CARD,
                               errors=[f"unknown role card: {card_id}"])
        return self.activate(card_id).consult(question, context)

    # ── 核心执行（含红线：无 LLM 不得产出） ───────────────────────────────────
    def _execute(self, card: RoleCard, prompt: str, session: AgentSession) -> AgentOutput:
        started = time.time()

        if not self.llm_ready():
            # 红线：不调用 LLM 就没有任何专家产出，返回 NEEDS_LLM_CREDENTIALS 而非模板文本
            return AgentOutput(
                card_id=card.card_id,
                status=NEEDS_LLM_CREDENTIALS,
                payload=None,
                raw="",
                errors=[
                    f"没有可用的 LLM 后端，{card.name} 无法产出。"
                    f"配置 GEMINI_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY "
                    f"或启动本地 Ollama 后重试。"
                ],
                latency_ms=int((time.time() - started) * 1000),
            )

        provider = self.provider if self.provider != "auto" else self.available_providers()[0]
        gw = LLMGateway(provider=provider, model=self.model, verbose=self.verbose)

        # 自愈循环：校验不过时把错误回喂给模型重改，而不是直接判死。
        # 修复次数用尽仍不过，则如实判失败 —— 不允许放宽验收规则放行。
        last: Optional[AgentOutput] = None
        cur_prompt = prompt
        for attempt in range(self.max_repairs + 1):
            resp = gw.call(cur_prompt, system=card.system_prompt, use_cache=False)
            latency = int((time.time() - started) * 1000)

            if not resp.success:
                last = AgentOutput(card_id=card.card_id, status=AgentStatus.LLM_ERROR, raw=resp.text,
                                   errors=[resp.error or "LLM call failed"],
                                   provider=resp.provider, model=resp.model, latency_ms=latency)
                continue

            parsed = extract_json(resp.text)
            if parsed is None or not isinstance(parsed, dict):
                last = AgentOutput(card_id=card.card_id, status=AgentStatus.JSON_INVALID, raw=resp.text,
                                   errors=["输出不是可解析的 JSON 对象"],
                                   provider=resp.provider, model=resp.model, latency_ms=latency)
                cur_prompt = self._build_repair_prompt(resp.text, last.errors)
                continue

            schema_errors = validate_schema(parsed, card.output_schema)
            if schema_errors:
                last = AgentOutput(card_id=card.card_id, status=AgentStatus.SCHEMA_INVALID, raw=resp.text,
                                   errors=schema_errors, provider=resp.provider, model=resp.model,
                                   input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
                                   latency_ms=latency)
                cur_prompt = self._build_repair_prompt(resp.text, schema_errors)
                continue

            acc_errors = check_acceptance(parsed, card.acceptance)
            if acc_errors:
                last = AgentOutput(card_id=card.card_id, status=AgentStatus.ACCEPTANCE_FAILED, raw=resp.text,
                                   payload=parsed, errors=acc_errors, provider=resp.provider, model=resp.model,
                                   input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
                                   latency_ms=latency)
                cur_prompt = self._build_repair_prompt(resp.text, acc_errors)
                continue

            session.turns += 1
            session.messages.append({"role": "user", "content": cur_prompt})
            session.messages.append({"role": "assistant", "content": resp.text})
            out = AgentOutput(card_id=card.card_id, status=AgentStatus.OK, payload=parsed, raw=resp.text,
                              provider=resp.provider, model=resp.model,
                              input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
                              latency_ms=latency)
            if last is not None:
                out.errors = [f"经 {attempt + 1} 次尝试后通过；此前失败原因: {'; '.join(last.errors)}"]
            return out

        assert last is not None
        last.errors = last.errors + [f"已重试修复 {self.max_repairs} 次仍不通过"]
        return last


# ─── 模块级单例 ───────────────────────────────────────────────────────────────
_runtime: Optional[AgentRuntime] = None


def get_runtime(provider: str = "auto", model: Optional[str] = None,
                verbose: bool = False) -> AgentRuntime:
    global _runtime
    if _runtime is None:
        _runtime = AgentRuntime(provider=provider, model=model, verbose=verbose)
    return _runtime
