"""core/c_skill_verifier.py — 24 项 C 类技能的真实跑通验证（W3c-3）。

C 类技能没有可计算的金标准，"它能用"这件事唯一的证据就是
**一次真实调用 + 通过 schema/acceptance/占位符拦截的完整记录**。
本模块负责把这件事做成可复现、可审计、可回查的动作：

    对每一项 C 类技能 → 真实调用 LLM → 校验 → 落工件（内容寻址 + 哈希）
        → 通过的才允许注册为 CapabilityDescriptor

没跑通的就是没跑通：失败项会连同 status 与错误原因一起写进证据，
不会被筛掉、不会被改写成"通过"。
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.llm_skill_adapter import (LLMSkillAdapter, LLMSkillResult,
                                    LLMSkillStatus, check_acceptance_weighted,
                                    find_placeholders, get_spec, spec_ids,
                                    validate_payload)
from core.run_context import RunContext

# 每一项 C 类技能的默认验证任务。写具体，是为了让产出可被语义判断——
# 泛泛的"请设计一下"只会换来泛泛的产出，那等于没验证。
DEFAULT_TASKS: Dict[str, str] = {
    "core_loop_design":
        "一款移动端竖屏的 Roguelike 弹幕射击游戏，单局目标 ≤30 秒，设计其核心玩法循环。",
    "economy_balance_math":
        "一款建造经营类游戏，主货币为『合金』，请建立其产出/消耗/沉淀三端经济模型。",
    "level_curve_progression":
        "一款平台跳跃游戏，共 10 关，规划难度曲线，每关必须引入一种新的机关。",
    "control_scheme_mapping":
        "一款 PC 端俯视角射击游戏，键盘鼠标方案，需要移动、射击、翻滚、换弹、技能五个动作。",
    "narrative_dialogue_branching":
        "末世废土题材，玩家在关卡前遇到一名受伤的拾荒者，需要决定是否把仅剩的抗生素给他。写分支对白。",
    "quest_tree_builder":
        "一款开放世界采集建造游戏的前 8 个任务（3 主线 + 5 支线），要求给出前驱关系与完成条件。",
    "inventory_slot_matrix":
        "一款生存建造游戏的背包，10x6 网格，道具需要耐久、重量、堆叠上限等属性维度。",
    "drop_rate_rng_table":
        "一款刷宝游戏的 Boss 掉落表，含 5 个稀有度层级，必须给出保底机制。",
    "camera_viewport_rules":
        "一款 2D 横版动作游戏，主角会频繁冲刺与二段跳，设计摄像机跟随规则。",
    "score_combo_multiplier":
        "一款节奏动作游戏，连击窗口与倍率，最高连击 50，设计连击奖励机制。",
    "boss_phase_transition":
        "一款横版动作游戏的最终 Boss，三阶段变身，需要清晰的招式预告。",
    "ui_hud_wireframe":
        "一款手机横屏 MOBA 的战斗 HUD，需要血量、技能、小地图、经济、计时五类信息。",
    "tutorial_stealth_guide":
        "一款三消游戏的前 60 秒新手引导，要求最多 1 次显式文字提示。",
    "accessibility_color_blind":
        "一款策略战棋游戏，需要用颜色区分 4 个阵营与 3 种地形状态，给出色盲友好配色。",
    "hypercasual_ad_monetization":
        "一款超休闲闯关游戏，单局 25 秒，设计广告点位与频控，优先保首日留存。",
    "wechat_social_viral_loop":
        "一款微信小游戏（成语答题），设计分享裂变循环与带参分享卡片。",
    "review_privacy_hardening":
        "一款面向国内的休闲手游，需要微信登录、相册分享与未成年人防沉迷，编写合规弹窗与加固方案。",
    "webgl_shader_pipeline":
        "一个 2D 水面波纹效果，输出 WebGL1 / GLSL ES 1.00 的顶点与片元着色器源码。",
    "tangent_normal_brdf_shader":
        "一个金属材质的 PBR 片元着色器，需处理切线空间法线与微表面 BRDF。",
    "adaptive_music_layering":
        "一款地牢探险游戏，探索/警戒/战斗三种状态，设计三层动态配乐与过渡。",
    "difficulty_kill_ratio_eval":
        "对局数据：共 1200 次关卡尝试，死亡 780 次，击杀 3400。评估难度与挫败感。",
    "telemetry_funnel_analytics":
        "新手漏斗数据：启动 10000 → 创建角色 8200 → 完成教学 5100 → 首胜 3000 → 次日回访 1800。分析瓶颈。",
    "first_principles_structural_audit":
        "审查这个设计主张：『抽卡游戏必须做保底，否则玩家会流失，所以保底是必要的』。",
    "anti_rubber_stamp_veto":
        "以下结论已被标记为通过：『UI 适配已完成』（无截图）、"
        "『性能达标 60fps』（无帧率采样数据）、『音频管线正常』（有 3 段真实导出的 wav 与其 RMS 值）。请审查。",
}


# 精简证据的落盘位置。output/ 被 gitignore（内容寻址的工件体积大、每次跑都变），
# 但这个精简摘要必须进版本库——它是"这一波到底跑通了什么"的可回查凭据。
DIGEST_PATH = "evidence/c_skills_latest.json"

# 复校验报告：历史"通过"在当前契约下是否仍然成立（离线，不烧额度）
AUDIT_PATH = "evidence/c_skills_audit.json"


class CSkillVerifier:
    """批量真实跑通 C 类技能，并把证据落进内容寻址的工件库。"""

    def __init__(self, adapter: Optional[LLMSkillAdapter] = None,
                 registry=None, run_context: Optional[RunContext] = None) -> None:
        self.adapter = adapter or LLMSkillAdapter()
        self.registry = registry
        self.run_context = run_context

    # ── 单跑一项 ────────────────────────────────────────────────────────
    def run_one(self, skill_id: str, task: Optional[str] = None,
                context: Optional[Dict[str, Any]] = None) -> LLMSkillResult:
        return self.adapter.run_skill(
            skill_id, task or DEFAULT_TASKS.get(skill_id, ""), context or {})

    # ── 批量跑 + 落证据 ─────────────────────────────────────────────────
    def run_all(self, skill_ids: Optional[List[str]] = None,
                tasks: Optional[Dict[str, str]] = None,
                verbose: bool = True) -> Dict[str, Any]:
        ids = sorted(skill_ids or spec_ids())
        tasks = tasks or {}
        started = time.time()
        results: List[LLMSkillResult] = []
        registered: List[str] = []
        failed: List[Dict[str, Any]] = []

        pre = self.adapter.preflight()
        if not pre["llm_ready"]:
            # 红线：没有 LLM 就不跑，也不允许继续往下编。
            return {
                "status": LLMSkillStatus.NEEDS_LLM_CREDENTIALS,
                "llm_ready": False,
                "how_to_fix": pre["how_to_fix"],
                "total": len(ids), "ok": 0, "failed": len(ids),
                "results": [], "registered": [], "failed_detail": [],
            }

        for sid in ids:
            t0 = time.time()
            r = self.run_one(sid, tasks.get(sid))
            results.append(r)
            if r.ok:
                if self.registry is not None:
                    try:
                        self.registry.register_c_skill(sid, result=r)
                        registered.append(sid)
                    except (ValueError, KeyError) as exc:
                        failed.append({"skill_id": sid, "status": r.status,
                                       "error": f"注册失败: {exc}"})
                else:
                    registered.append(sid)
                if verbose:
                    print(f"  [OK  ] {sid:38s} {r.provider}/{r.model} "
                          f"{r.latency_ms}ms 尝试{r.attempts}次")
            else:
                failed.append({"skill_id": sid, "status": r.status,
                               "errors": r.errors[:6], "attempts": r.attempts,
                               "provider": r.provider})
                if verbose:
                    first = (r.errors[0] if r.errors else "")[:90]
                    print(f"  [FAIL] {sid:38s} {r.status} "
                          f"{int((time.time() - t0) * 1000)}ms | {first}")

        evidence: Dict[str, Any] = {
            "artifact_type": "c_skill_verification",
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started)),
            "elapsed_seconds": round(time.time() - started, 2),
            "llm_ready": True,
            "available_providers": pre["available_providers"],
            "total": len(ids),
            "ok": len(registered),
            "failed": len(failed),
            "registered": registered,
            "failed_detail": failed,
            "results": [r.to_dict() for r in results],
        }
        if self.registry is not None:
            evidence["counts"] = self.registry.counts()

        evidence["run_dir"] = self._persist(evidence)
        evidence["digest_path"] = self.write_digest(evidence)
        return evidence

    # ── 历次运行的历史工件 ──────────────────────────────────────────────
    @staticmethod
    def collect_history(runs_root: Optional[str] = None) -> List[Dict[str, Any]]:
        """从 output/runs/* 读回历次 c_skill_verification 工件（按目录名时间正序）。

        为什么要跨运行合并：实测同一套契约、不同时段/不同模型，单次全量通过率在
        17/24 ~ 22/24 之间波动。只报某一次的数字会失真——既可能夸大，也可能抹掉
        已经拿到过的真实通过记录。所以证据必须双轨：
        `ever_passed`（历史上至少一次真实通过，工件可回查）+ `last_ok`（最近一次）。

        读不出来的 run（不是验证 run / 工件损坏 / 索引坏）一律跳过，
        不猜、不补、不粉饰成通过。
        """
        import json as _json
        from pathlib import Path

        from core.artifact_store import ArtifactIntegrityError, ArtifactStore

        root = (Path(runs_root) if runs_root
                else Path(__file__).resolve().parent.parent / "output" / "runs")
        if not root.exists():
            return []

        runs: List[Dict[str, Any]] = []
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            try:
                raw = ArtifactStore(d).read_bytes("art_c_skill_verification")
                data = _json.loads(raw.decode("utf-8"))
            except (OSError, KeyError, ValueError,
                    UnicodeDecodeError, ArtifactIntegrityError):
                continue
            runs.append({
                "run_id": data.get("run_id") or d.name,
                "started_at": data.get("started_at"),
                "elapsed_seconds": data.get("elapsed_seconds"),
                "available_providers": data.get("available_providers"),
                "total": data.get("total"),
                "ok": data.get("ok"),
                "failed": data.get("failed"),
                "results": data.get("results", []),
            })
        return runs

    # ── 精简证据（进版本库） ────────────────────────────────────────────
    @staticmethod
    def write_digest(evidence: Dict[str, Any],
                     path: str = DIGEST_PATH,
                     merge_history: bool = True,
                     runs_root: Optional[str] = None) -> str:
        """只留可回查的最小集合：谁、用什么模型、跑没跑通、产出哈希。

        不落 payload 全文（体积大且每次都变），但每一项都留 payload 的 sha256，
        需要时可以拿 output/ 里的完整工件对账。

        merge_history=True 时把 output/runs/ 下历次验证工件一并读回，产出
        schema_version=2 的合并证据。两个口径分开记，不许互相冒充：
          - ever_passed / pass_rate：历史上真实通过的累计情况
          - last_ok / last_status：最近一次运行的真实结果
        通过项额外记录 pass_* （那次通过所用的 run/provider/model/payload 哈希），
        回放注册时用的是通过那次的证据，不是最近一次（可能是失败）的。
        """
        import json as _json
        import os

        from core.contracts import content_hash

        def _sha(r: Dict[str, Any]) -> Optional[str]:
            return content_hash(r["payload"]) if r.get("payload") else None

        current: Dict[str, Any] = {
            "run_id": evidence.get("run_id"),
            "started_at": evidence.get("started_at"),
            "elapsed_seconds": evidence.get("elapsed_seconds"),
            "available_providers": evidence.get("available_providers"),
            "total": evidence.get("total"),
            "ok": evidence.get("ok"),
            "failed": evidence.get("failed"),
            "results": evidence.get("results", []),
        }

        if evidence.get("status") == LLMSkillStatus.NEEDS_LLM_CREDENTIALS:
            # 没跑就是没跑：不合并历史来凑一个好看的数字。
            runs = [current]
        elif merge_history:
            runs = CSkillVerifier.collect_history(runs_root)
            known = {r["run_id"] for r in runs}
            if current["run_id"] in known:
                runs = [current if r["run_id"] == current["run_id"] else r
                        for r in runs]
            else:
                runs.append(current)
        else:
            runs = [current]

        merged: Dict[str, Dict[str, Any]] = {}
        for run in runs:
            for r in run.get("results", []):
                sid = r.get("skill_id")
                if not sid:
                    continue
                ok = bool(r.get("ok"))
                it = merged.setdefault(sid, {
                    "skill_id": sid,
                    "history_runs": 0, "history_passes": 0,
                    "ever_passed": False, "pass_rate": 0.0,
                    "last_ok": None, "last_status": None,
                    "last_provider": None, "last_model": None,
                    "last_attempts": None, "last_latency_ms": None,
                    "last_payload_sha256": None, "last_first_error": None,
                    "last_run_id": None, "last_at": None,
                    "pass_run_id": None, "pass_at": None,
                    "pass_provider": None, "pass_model": None,
                    "pass_attempts": None, "pass_payload_sha256": None,
                })
                it["history_runs"] += 1
                it["history_passes"] += 1 if ok else 0
                it["ever_passed"] = it["ever_passed"] or ok
                it["last_ok"] = ok
                it["last_status"] = r.get("status")
                it["last_provider"] = r.get("provider")
                it["last_model"] = r.get("model")
                it["last_attempts"] = r.get("attempts")
                it["last_latency_ms"] = r.get("latency_ms")
                it["last_payload_sha256"] = _sha(r)
                it["last_first_error"] = (r.get("errors") or [None])[0]
                it["last_run_id"] = run.get("run_id")
                it["last_at"] = run.get("started_at")
                if ok:
                    # 只让"通过那一次"的证据覆盖 pass_*，失败运行不能冲掉它
                    it["pass_run_id"] = run.get("run_id")
                    it["pass_at"] = run.get("started_at")
                    it["pass_provider"] = r.get("provider")
                    it["pass_model"] = r.get("model")
                    it["pass_attempts"] = r.get("attempts")
                    it["pass_payload_sha256"] = _sha(r)

        per_skill = sorted(merged.values(), key=lambda x: x["skill_id"])
        for it in per_skill:
            it["pass_rate"] = (round(it["history_passes"] / it["history_runs"], 3)
                               if it["history_runs"] else 0.0)
        ever = [it["skill_id"] for it in per_skill if it["ever_passed"]]

        digest = {
            "schema_version": 2,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "run_id": current["run_id"],
            "run_dir": evidence.get("run_dir"),
            "available_providers": current["available_providers"],
            "last_run": {"total": current["total"], "ok": current["ok"],
                         "failed": current["failed"]},
            "history_runs": [{
                "run_id": r.get("run_id"),
                "started_at": r.get("started_at"),
                "elapsed_seconds": r.get("elapsed_seconds"),
                "total": r.get("total"), "ok": r.get("ok"),
                "failed": r.get("failed"),
            } for r in runs],
            "ever_passed": ever,
            "ever_passed_count": len(ever),
            "per_skill": per_skill,
            "counts": evidence.get("counts"),
            "note": ("ever_passed = 历史上至少一次真实通过（工件可回查）；"
                     "last_ok = 最近一次运行结果。两个口径不可混用。"),
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(_json.dumps(digest, ensure_ascii=False, indent=2))
        return path

    # ── 复校验：历史"通过"在当前契约下还成不成立 ────────────────────────
    @staticmethod
    def audit_evidence(path: str = DIGEST_PATH,
                       runs_root: Optional[str] = None,
                       write: bool = True,
                       audit_path: str = AUDIT_PATH) -> Dict[str, Any]:
        """把摘要里每项 ever_passed 的 payload 从工件库读回，用**当前**契约重跑一遍。

        为什么必须有这一步：`ever_passed` 记的是"当时跑通了"。如果之后契约被改严
        （阈值上调、字段新增），那次通过可能与现状不符；反之契约被改松，曾经的
        失败也不该突然算通过。拿旧结果冒充现状是另一种失真，所以"历史通过"与
        "当前仍成立"必须分开报——`ever_passed` 是前者，这里是后者。

        全部离线：不调用 LLM，只按哈希读工件 + 跑本地校验。
        读不回 payload（run 目录被清掉）的项记为 `missing`，不猜。
        """
        import json as _json
        import os
        from pathlib import Path

        from core.artifact_store import (ArtifactIntegrityError,
                                         ArtifactStore)

        root = (Path(runs_root) if runs_root
                else Path(__file__).resolve().parent.parent / "output" / "runs")
        if not os.path.exists(path):
            return {"artifact_type": "c_skill_audit", "error": f"摘要不存在: {path}",
                    "checked": 0, "still_valid": 0, "stale": 0, "missing": 0}

        with open(path, "r", encoding="utf-8") as f:
            digest = _json.load(f)

        details: List[Dict[str, Any]] = []
        n_valid = n_stale = n_missing = n_never = 0
        for item in digest.get("per_skill", []):
            sid = item["skill_id"]
            passed = (item.get("ever_passed") if "ever_passed" in item
                      else item.get("ok"))
            rec: Dict[str, Any] = {
                "skill_id": sid,
                "ever_passed": bool(passed),
                "pass_rate": item.get("pass_rate"),
                "pass_run_id": item.get("pass_run_id"),
            }
            if not passed:
                rec["audit"] = "no_pass_record"
                n_never += 1
                details.append(rec)
                continue

            run_id = item.get("pass_run_id")
            spec = get_spec(sid)
            if spec is None:
                rec["audit"] = "no_spec"
                n_stale += 1
                details.append(rec)
                continue
            try:
                raw = ArtifactStore(root / run_id).read_bytes(
                    f"art_payload_{sid}")
                payload = _json.loads(raw.decode("utf-8"))
            except (OSError, KeyError, ValueError,
                    UnicodeDecodeError, ArtifactIntegrityError) as exc:
                rec["audit"] = "missing"
                rec["error"] = str(exc)
                n_missing += 1
                details.append(rec)
                continue

            errors = list(validate_payload(payload, spec.output_schema))
            errors += list(check_acceptance_weighted(payload, spec.acceptance))
            errors += list(find_placeholders(payload))
            if spec.custom:
                errors += list(spec.custom(payload) or [])
            rec["payload_sha256"] = item.get("pass_payload_sha256")
            if errors:
                rec["audit"] = "stale"
                rec["errors"] = errors[:6]
                n_stale += 1
            else:
                rec["audit"] = "still_valid"
                n_valid += 1
            details.append(rec)

        report = {
            "artifact_type": "c_skill_audit",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "digest_path": path,
            "digest_schema_version": digest.get("schema_version"),
            "ever_passed_count": len(digest.get("ever_passed", [])),
            "checked": len(details),
            "still_valid": n_valid,
            "stale": n_stale,
            "missing": n_missing,
            "no_pass_record": n_never,
            "pass_rate_avg": (round(n_valid / max(1, n_valid + n_stale + n_missing), 3)
                              if (n_valid + n_stale + n_missing) else 0.0),
            "details": details,
            "note": ("still_valid = 该技能历史通过的 payload 在**当前**契约下复校验仍通过；"
                     "stale = 契约已变，旧通过不再成立；missing = 工件读不回。"),
        }
        if write:
            os.makedirs(os.path.dirname(audit_path) or ".", exist_ok=True)
            with open(audit_path, "w", encoding="utf-8") as f:
                f.write(_json.dumps(report, ensure_ascii=False, indent=2))
        return report

    # ── 证据落盘 ────────────────────────────────────────────────────────
    def _persist(self, evidence: Dict[str, Any]) -> str:
        ctx = self.run_context or RunContext(title="c_skill_verify")
        self.run_context = ctx
        ref = ctx.artifact_store.put_json(
            "c_skill_verification", evidence,
            artifact_id="art_c_skill_verification",
            relative_name="c_skill_verification.json",
            producer_capability="skill.c_skill_verifier",
        )
        # 逐项落 payload，便于事后回查"当时到底产出了什么"
        for r in evidence["results"]:
            if r.get("payload"):
                ctx.artifact_store.put_json(
                    "c_skill_payload", r["payload"],
                    artifact_id=f"art_payload_{r['skill_id']}",
                    relative_name=f"payload_{r['skill_id']}.json",
                    producer_capability=f"skill.{r['skill_id']}",
                )
        evidence["run_id"] = ctx.run_id
        evidence["evidence_ref"] = ref.sha256
        evidence["artifact_integrity"] = ctx.artifact_store.verify_all()
        ctx.generate_manifest()
        return str(ctx.work_dir)


def restore_registrations(registry, path: str = DIGEST_PATH,
                          verbose: bool = False) -> int:
    """从证据摘要回放 C 类技能的注册状态。

    为什么需要：skill_registry 是内存单例，进程一退出"真跑通过"这件事就没了，
    `skill-list` 会显示 C_REGISTERED=0——看起来像从没跑过，属于另一种失真。
    所以注册状态必须能被证据回放，而不是依赖"当前进程刚好跑过"。

    注意：回放的是**已记录的真实调用**（摘要里有 provider/model/attempts/payload 哈希，
    可回查到 output/ 下的完整工件），不是凭空宣布通过。摘要不存在就一项都不注册。
    """
    import json as _json
    import os

    from core.llm_skill_adapter import LLMSkillResult, LLMSkillStatus

    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            digest = _json.load(f)
    except (OSError, ValueError):
        return 0

    n = 0
    for item in digest.get("per_skill", []):
        # 口径：ever_passed（历史至少一次真实通过）。schema_version 1 的旧摘要
        # 没有这个字段，退回 ok——那是单运行的真实结果，同样有据可查。
        passed = (item.get("ever_passed") if "ever_passed" in item
                  else item.get("ok"))
        if not passed:
            continue
        sk = registry._skills.get(item["skill_id"])
        if sk is None or sk.status == "REGISTERED":
            continue
        # 用"通过那一次"的端点与模型，而不是最近一次（可能失败）运行的
        provider = item.get("pass_provider") or item.get("provider") or ""
        model = item.get("pass_model") or item.get("model") or ""
        if not provider:
            continue  # 没有端点记录 = 没有调用证据，不许注册
        result = LLMSkillResult(
            skill_id=item["skill_id"], status=LLMSkillStatus.OK,
            provider=provider, model=model,
            attempts=item.get("pass_attempts") or item.get("attempts") or 1,
            latency_ms=item.get("last_latency_ms") or 0,
        )
        try:
            registry.register_c_skill(item["skill_id"], result=result)
        except (ValueError, KeyError):
            continue
        sk.notes.append(
            f"由证据摘要回放注册（通过于 run_id={item.get('pass_run_id') or digest.get('run_id')}"
            f" @ {item.get('pass_at') or digest.get('generated_at')}，"
            f"provider={provider}/{model}，"
            f"payload_sha256={item.get('pass_payload_sha256') or item.get('payload_sha256')}）"
            + (f"；历史通过率 {item['pass_rate']}"
               if item.get("pass_rate") is not None else ""))
        n += 1
    if verbose and n:
        print(f"  [RESTORE] 从 {path} 回放 {n} 项 C 类技能的真实通过记录")
    return n


def verify_all(verbose: bool = True, registry=None,
               skill_ids: Optional[List[str]] = None,
               model: Optional[str] = None) -> Dict[str, Any]:
    """便捷入口：分类表 + A 类种子 + 全量真实跑通。

    model 可指定端点池里的具体模型 id。实测不同免费模型在同一套契约下通过率
    差异极大（glm-4-flash 有 5 项填不出内容，gemini-3.6-flash 一次通过），
    所以这个参数必须能被显式指定并记进证据，否则"跑通了"这句话没有意义。
    """
    if registry is None:
        from core.skill_registry import skill_registry
        registry = skill_registry
    if not registry._skills:
        registry.ingest_from_registry()
    from core.skill_registry_seeds import apply_default_seeds
    from core.skill_classification import apply_classification
    apply_default_seeds()
    apply_classification(registry)
    adapter = LLMSkillAdapter(model=model) if model else LLMSkillAdapter()
    return CSkillVerifier(adapter=adapter, registry=registry).run_all(
        skill_ids=skill_ids, verbose=verbose)
