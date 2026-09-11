"""core/skill_registry.py: L2 技能注册表（W3a）。

L2 技能（114 项）分三类处置：
- A 类（约 40）：已有现成 core/pipeline 模块，封装即用。
- B 类（约 50）：需新写确定性实现，留 W3b。
- C 类（约 24）：需 LLM 介入，留 W3c。

本模块只做"找到 A 类 + 报告 + 注册"三件事。
B/C 类只挂"NEEDS_IMPLEMENTATION"占位，**不可装饰成已实现**。
未实现模块不会自动注册——不为了凑数装成功。

诚实红线（与计划 13.2 一致）：
- 候选模块若 import 失败 → 标 BLOCKED_BY_IMPORT，**绝不**继续注册。
- register_as_capability 强制要求 entry 可调用、签名可读，否则抛错。
- 实际注册数与 discovered/pending 全部如实显示在 CLI，分母永远是 114。
"""
from __future__ import annotations

import importlib
import inspect
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.contracts import CapabilityDescriptor


class SkillClass:
    A = "A"
    B = "B"
    C = "C"
    UNIMPLEMENTED = "U"


class SkillStatus:
    PENDING = "PENDING"
    DISCOVERED = "DISCOVERED"
    REGISTERED = "REGISTERED"
    BLOCKED_BY_IMPORT = "BLOCKED_BY_IMPORT"
    NEEDS_IMPLEMENTATION = "NEEDS_IMPLEMENTATION"


# 命名相似度去噪 stopwords
_STOPWORDS = {"a", "an", "the", "of", "to", "in", "on", "for", "with",
              "and", "or", "not", "no", "be", "by", "as", "at", "from",
              "but", "is", "are", "engine", "manager", "system", "core",
              "pipeline", "module", "skill", "skills", "tool"}


def _tokens(name: str) -> set:
    parts = re.split(r"[_\W]+", (name or "").lower())
    return {p for p in parts if len(p) > 1 and p not in _STOPWORDS}


def _score(a: str, b: str) -> float:
    A, B = _tokens(a), _tokens(b)
    if not A or not B:
        return 0.0
    return len(A & B) / max(len(A), len(B))


@dataclass
class L2Skill:
    skill_id: str
    category: str
    name: str
    cls: str = SkillClass.UNIMPLEMENTED
    status: str = SkillStatus.PENDING
    candidate_module: Optional[str] = None
    candidate_score: float = 0.0
    capability: Optional[CapabilityDescriptor] = None
    import_error: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "category": self.category,
            "name": self.name,
            "cls": self.cls,
            "status": self.status,
            "candidate_module": self.candidate_module,
            "candidate_score": round(self.candidate_score, 2),
            "capability_id": self.capability.capability_id if self.capability else None,
            "import_error": self.import_error,
            "notes": list(self.notes),
        }


class SkillRegistry:
    """L2 技能注册表。"""

    SCAN_TOPDIRS = ("core", "pipeline")
    MATCH_THRESHOLD = 0.30  # 名称相似度门槛；过低会乱匹配

    def __init__(self, project_root: Optional[str] = None) -> None:
        self._skills: Dict[str, L2Skill] = {}
        self._project_root = os.path.abspath(project_root or ".")

    # ── 同步元数据 ──────────────────────────────────────────────────────
    def ingest_from_registry(self) -> int:
        from core.registry import GAME_SKILLS
        n = 0
        for s in GAME_SKILLS:
            if s["id"] in self._skills:
                continue
            self._skills[s["id"]] = L2Skill(
                skill_id=s["id"], category=s["category"], name=s["name"],
                cls=SkillClass.UNIMPLEMENTED, status=SkillStatus.PENDING,
            )
            n += 1
        return n

    # ── 候选扫描 ────────────────────────────────────────────────────────
    def _iter_modules(self) -> List[Tuple[str, str]]:
        """产出 (dotted_module_name, base_name) 对。"""
        out: List[Tuple[str, str]] = []
        for d in self.SCAN_TOPDIRS:
            full = os.path.join(self._project_root, d)
            if not os.path.isdir(full):
                continue
            for f in sorted(os.listdir(full)):
                fp = os.path.join(full, f)
                if f == "__init__.py" or f.startswith("__"):
                    continue
                if os.path.isfile(fp) and f.endswith(".py"):
                    base = f[:-3]
                    out.append((f"{d}.{base}", base))
                elif os.path.isdir(fp) and os.path.exists(os.path.join(fp, "__init__.py")):
                    pkg = f
                    for sub in sorted(os.listdir(fp)):
                        sp = os.path.join(fp, sub)
                        if sub == "__init__.py" or sub.startswith("__"):
                            continue
                        if os.path.isfile(sp) and sub.endswith(".py"):
                            base = sub[:-3]
                            out.append((f"{d}.{pkg}.{base}", base))
        return out

    def _candidates_for(self, skill_id: str, name: str) -> List[Tuple[str, float]]:
        """返回 (module_dotted, score) 列表，按 score 降序。"""
        scored: List[Tuple[str, float]] = []
        for mod_dotted, base in self._iter_modules():
            s_id = _score(skill_id, base)
            s_name = _score(name, base)
            sc = s_id * 0.7 + s_name * 0.3
            if sc >= self.MATCH_THRESHOLD:
                scored.append((mod_dotted, sc))
        scored.sort(key=lambda x: -x[1])
        return scored[:5]

    def discover_a_class(self) -> Dict[str, int]:
        """对每个 PENDING / BLOCKED_BY_IMPORT 的技能找候选 + 试 import。

        返回计数：{"discovered": N, "blocked_by_import": M, "still_pending": K}
        """
        discovered = 0
        blocked = 0
        still_pending = 0
        for sid, sk in self._skills.items():
            if sk.cls not in (SkillClass.UNIMPLEMENTED, SkillClass.A):
                continue
            if sk.status not in (SkillStatus.PENDING, SkillStatus.BLOCKED_BY_IMPORT):
                continue
            cands = self._candidates_for(sid, sk.name)
            if not cands:
                still_pending += 1
                continue
            best_mod, best_sc = cands[0]
            sk.candidate_module = best_mod
            sk.candidate_score = best_sc
            sk.cls = SkillClass.A
            sk.notes.append(f"discovered: {best_mod} (score={best_sc:.2f})")
            # 真探测 import：失败就标 BLOCKED_BY_IMPORT，不许装成功
            try:
                importlib.import_module(best_mod)
            except Exception as exc:
                sk.status = SkillStatus.BLOCKED_BY_IMPORT
                sk.import_error = f"{type(exc).__name__}: {exc}"
                sk.notes.append(f"import failed: {sk.import_error}")
                blocked += 1
                continue
            sk.status = SkillStatus.DISCOVERED
            discovered += 1
        return {"discovered": discovered, "blocked_by_import": blocked,
                "still_pending": still_pending}

    # ── 显式注册（人工/代码确认真实可调） ──────────────────────────────
    def register_as_capability(
        self,
        skill_id: str,
        *,
        entry: Callable[..., Any],
        version: str = "1.0.0",
        accepts: Optional[List[Dict]] = None,
        produces: Optional[List[Dict]] = None,
        resource_limits: Optional[Dict[str, Any]] = None,
        permissions: Optional[Dict[str, Any]] = None,
        evidence_requirements: Optional[List[str]] = None,
        maturity: str = "M2",
    ) -> CapabilityDescriptor:
        """把一个 A 类技能的真实现注册成 CapabilityDescriptor。

        强制要求：
        - entry 必须是真正可调用的对象
        - 签名可读（inspect.signature 不抛 TypeError/ValueError）
        - 目标 skill 必须是已 discover 且 import 通的 A 类
        """
        sk = self._skills.get(skill_id)
        if sk is None:
            raise KeyError(f"unknown skill_id: {skill_id}")
        if sk.cls != SkillClass.A:
            raise ValueError(f"skill {skill_id} is cls={sk.cls}; only A can be registered")
        if sk.status != SkillStatus.DISCOVERED:
            raise ValueError(f"skill {skill_id} status={sk.status}; must be DISCOVERED before register")
        if not callable(entry):
            raise ValueError(f"entry must be callable, got {type(entry).__name__}")
        try:
            inspect.signature(entry)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"entry has no inspectable signature: {exc}") from exc

        module = getattr(entry, "__module__", None) or sk.candidate_module or ""
        desc = CapabilityDescriptor(
            capability_id=f"skill.{skill_id}",
            version=version, kind="skill",
            accepts=accepts or [],
            produces=produces or [],
            implementation={"module": module, "entrypoint": getattr(entry, "__name__", str(entry))},
            permissions=permissions or {"filesystem": "run_workspace",
                                        "network": "disabled", "process": "none"},
            resource_limits=resource_limits or {"timeout_seconds": 60, "max_memory_mb": 256},
            evidence_requirements=evidence_requirements or ["input_hash", "output_hash"],
            maturity=maturity,
        )
        from core.capability_registry import capability_registry
        capability_registry.register(desc)
        sk.capability = desc
        sk.status = SkillStatus.REGISTERED
        sk.notes.append(f"registered as {desc.capability_id}@{version}")
        return desc

    # ── C 类：真跑通才允许注册 ──────────────────────────────────────────
    def register_c_skill(self, skill_id: str, *, result: Any,
                         version: str = "1.0.0") -> CapabilityDescriptor:
        """把一项 C 类技能注册为能力。**前置条件是它真的跑通过一次。**

        这是本平台对"绑 LLM 技能"的防伪底线：C 类技能的产出没有可计算金标准，
        唯一能证明它存在的证据就是一次真实调用 + 通过 schema/acceptance 的记录。
        因此这里强制：
        - result.ok 必须为 True（没跑通不许注册）；
        - result.provider 必须非空（没记录调用端点，等于没有证据）；
        - skill.cls 必须是 C。
        三条任一不满足就抛错——宁可少注册，也不把"有契约"伪装成"能用"。
        """
        sk = self._skills.get(skill_id)
        if sk is None:
            raise KeyError(f"unknown skill_id: {skill_id}")
        if sk.cls != SkillClass.C:
            raise ValueError(f"skill {skill_id} is cls={sk.cls}; only C can be registered here")
        if not bool(getattr(result, "ok", False)):
            raise ValueError(
                f"skill {skill_id} 未真实跑通（status={getattr(result, 'status', '?')}），"
                f"不允许注册为能力")
        provider = str(getattr(result, "provider", "") or "")
        if not provider:
            raise ValueError("result 没有记录 provider —— 无法证明这次产出真的来自一次 LLM 调用")

        from core.capability_registry import capability_registry
        desc = CapabilityDescriptor(
            capability_id=f"skill.{skill_id}",
            version=version, kind="llm_skill",
            accepts=[{"name": "task", "type": "string"},
                     {"name": "context", "type": "object"}],
            produces=[{"name": "payload", "schema_ref": f"c_skill_spec.{skill_id}"}],
            implementation={"module": "core.llm_skill_adapter",
                            "entrypoint": "LLMSkillAdapter.run_skill",
                            "spec": skill_id},
            permissions={"filesystem": "run_workspace",
                         "network": "llm_endpoint_only", "process": "none"},
            resource_limits={"timeout_seconds": 180, "max_memory_mb": 256,
                             "max_repairs": int(getattr(result, "attempts", 1)) - 1},
            evidence_requirements=["llm_call_trace", "provider", "model",
                                   "schema_validated", "acceptance_passed"],
            maturity="M2",
        )
        capability_registry.register(desc)
        sk.capability = desc
        sk.status = SkillStatus.REGISTERED
        sk.notes.append(
            f"真实调用 {provider}/{getattr(result, 'model', '')} "
            f"{getattr(result, 'attempts', 1)} 次后通过校验，注册为 {desc.capability_id}")
        return desc

    def register_b_skill(self, skill_id: str, *, result: Any,
                         version: str = "1.0.0") -> CapabilityDescriptor:
        """把一项 B 类（确定性算法）技能注册为能力。**前置条件是它真的跑过且验收通过。**

        B 类与 C 类的防伪底线不同，但同样不可装饰：
        - C 类没有金标准，唯一证据是"一次真实 LLM 调用 + 通过校验"；
        - B 类产出可由确定性算法生成、用数值断言验收，所以证据是
          "一次真实运行 + acceptance 断言全过 + 可复现"。
        因此这里强制：
        - result.ok 必须为 True（没跑通/验收没过不许注册）；
        - result.runtime 必须非空（没记录运行环境，等于没有证据）；
        - skill.cls 必须是 B。
        依赖外部 DCC/GPU 工具、当前跑不了的 B 类，result.ok 应为 False 并带
        needs_runtime_tool 说明——**不许靠占位实现冒充可执行**。
        """
        sk = self._skills.get(skill_id)
        if sk is None:
            raise KeyError(f"unknown skill_id: {skill_id}")
        if sk.cls != SkillClass.B:
            raise ValueError(f"skill {skill_id} is cls={sk.cls}; only B can be registered here")
        if not bool(getattr(result, "ok", False)):
            raise ValueError(
                f"skill {skill_id} 未真实跑通/验收未过（status={getattr(result, 'status', '?')}），"
                f"不允许注册为能力")
        runtime = str(getattr(result, "runtime", "") or "")
        if not runtime:
            raise ValueError("result 没有记录 runtime —— 无法证明这次产出真的来自一次确定性运行")

        from core.capability_registry import capability_registry
        needs_tool = str(getattr(result, "needs_runtime_tool", "") or "")
        desc = CapabilityDescriptor(
            capability_id=f"skill.{skill_id}",
            version=version, kind="deterministic_algorithm",
            accepts=[{"name": "params", "type": "object"}],
            produces=[{"name": "payload", "schema_ref": f"b_skill_spec.{skill_id}"}],
            implementation={"module": "core.b_skill_runtime",
                            "entrypoint": "BSkillRuntime.run_skill",
                            "spec": skill_id},
            permissions={"filesystem": "run_workspace",
                         "network": "none", "process": "none"},
            resource_limits={"timeout_seconds": 30, "max_memory_mb": 128},
            evidence_requirements=["deterministic_run", "acceptance_passed",
                                   "reproducible"],
            maturity="M3",
        )
        desc.runtime_constraint = needs_tool or "pure_python"
        capability_registry.register(desc)
        sk.capability = desc
        sk.status = SkillStatus.REGISTERED
        sk.notes.append(
            f"真实运行({runtime})且 {getattr(result, 'checks_passed', '?')} 项验收断言全过，"
            f"注册为 {desc.capability_id}"
            + (f"；运行约束: {needs_tool}" if needs_tool else ""))
        return desc

    # ── 分类（B/C 留 W3b/c） ────────────────────────────────────────────
    def mark_needs_implementation(self, skill_id: str, cls: str, *, note: str = "") -> None:
        if cls not in (SkillClass.B, SkillClass.C):
            raise ValueError(f"cls must be B or C, got {cls!r}")
        sk = self._skills.get(skill_id)
        if sk is None:
            raise KeyError(skill_id)
        sk.cls = cls
        sk.status = SkillStatus.NEEDS_IMPLEMENTATION
        if note:
            sk.notes.append(note)

    # ── 报告 ────────────────────────────────────────────────────────────
    def counts(self) -> Dict[str, int]:
        out = {
            "A_REGISTERED": 0, "A_DISCOVERED": 0, "A_BLOCKED": 0,
            "B": 0, "B_REGISTERED": 0, "C": 0, "C_REGISTERED": 0, "C_SPECD": 0,
            "PENDING": 0, "TOTAL": len(self._skills),
        }
        for sk in self._skills.values():
            if sk.cls == SkillClass.A:
                if sk.status == SkillStatus.REGISTERED:
                    out["A_REGISTERED"] += 1
                elif sk.status == SkillStatus.DISCOVERED:
                    out["A_DISCOVERED"] += 1
                elif sk.status == SkillStatus.BLOCKED_BY_IMPORT:
                    out["A_BLOCKED"] += 1
            elif sk.cls == SkillClass.B:
                out["B"] += 1
                if sk.status == SkillStatus.REGISTERED:
                    out["B_REGISTERED"] += 1
            elif sk.cls == SkillClass.C:
                out["C"] += 1
                if sk.status == SkillStatus.REGISTERED:
                    out["C_REGISTERED"] += 1
                else:
                    out["C_SPECD"] += 1
            else:
                out["PENDING"] += 1
        return out

    def list(self, *, status: Optional[str] = None,
             cls: Optional[str] = None) -> List[L2Skill]:
        out = list(self._skills.values())
        if status:
            out = [s for s in out if s.status == status]
        if cls:
            out = [s for s in out if s.cls == cls]
        return sorted(out, key=lambda s: s.skill_id)

    def as_dict(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.list()]


# 全局单例（与 capability_registry 一致）
skill_registry = SkillRegistry()
