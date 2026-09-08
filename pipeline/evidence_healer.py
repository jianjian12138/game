#!/usr/bin/env python3
"""
evidence_healer.py: 四维运行证据链精准自愈引擎 v5.0 (Evidence-Based Healing Engine)

v5.0 升级：调用 LLMGateway + HealPrompt 直接生成可执行的 Patch diff
向后兼容：未配置 LLM 时自动降级到原有规则引擎。

基于《godogen》与《妙点小匠》第四阶段核心经验：
当验收门禁未通过时，绝不向模型发送泛泛的“请再试一次”，而是构造一份高密度的四维 Evidence Pack：
1. 真实运行/编译报错 (Compiler/Runtime stderr)
2. 无头探针数据快照 (Probe Snapshot JSON)
3. 视觉真理差分诊断 (Visual Diff Layer Violations)
4. 确定性求解器数学证据 (Solver Topology/Path Failures)

驱动 Agent 针对具体失效的代码行与函数执行最小侵入式定向修补 (Targeted Healing)。
"""
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

class EvidenceHealer:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path(".")

    def assemble_evidence_pack(
        self,
        stderr_text: str = "",
        probe_snapshot: Optional[Dict[str, Any]] = None,
        visual_findings: Optional[List[Dict[str, Any]]] = None,
        solver_failures: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """打包四维结构化证据链"""
        pack = {
            "evidence_version": "1.0.0",
            "has_critical_blockers": bool(stderr_text or solver_failures or (visual_findings and len(visual_findings) > 0)),
            "dimension_1_runtime_stderr": stderr_text.strip() if stderr_text else "None (Clean Run)",
            "dimension_2_probe_state": probe_snapshot or {},
            "dimension_3_visual_diff_violations": visual_findings or [],
            "dimension_4_solver_failures": solver_failures or []
        }
        
        out_path = Path("knowledge/latest_evidence_pack.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
        return pack

    def diagnose_and_suggest_patch(
        self,
        evidence_pack: Dict[str, Any],
        source_code: str = "",
        use_llm: bool = True,
        llm_provider: str = "gemini",
        llm_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """根据四维证据自动生成靶向修补策略建议 v5.0

        Args:
            evidence_pack:  assemble_evidence_pack() 输出的证据包
            source_code:    待修复的源代码（可选，提供时 LLM 能生成更精确的 Patch）
            use_llm:        是否调用 LLM 生成可执行 Patch
            llm_provider:   LLM Provider
            llm_model:      指定模型
        """
        print("=== EvidenceHealer v5.0: 启动四维运行证据链诊断自愈 ===")

        # 形成视觉成果列表（兼容两种证据格式）
        raw_visual = evidence_pack.get("dimension_3_visual_diff_violations", [])
        visual_findings = []
        for v in raw_visual:
            if isinstance(v, dict):
                visual_findings.append(v.get("description", str(v)))
            else:
                visual_findings.append(str(v))

        runtime_errors = []
        stderr = evidence_pack.get("dimension_1_runtime_stderr", "")
        if stderr and stderr != "None (Clean Run)":
            runtime_errors = [line.strip() for line in stderr.splitlines() if line.strip()]

        # 尝试 LLM 生成可执行 Patch
        llm_result = None
        if use_llm:
            llm_result = self._llm_heal(
                evidence_pack, visual_findings, runtime_errors,
                source_code, llm_provider, llm_model
            )

        if llm_result:
            print(f"  [LLM HEAL] 生成 Patch 成功 — 根因: {llm_result.get('root_cause', 'N/A')[:80]}")
            patch_suggestions = llm_result.get("patch", "")
            result = {
                "status": "NEEDS_PATCH" if evidence_pack.get("has_critical_blockers") else "PASS",
                "mode": "llm",
                "root_cause": llm_result.get("root_cause", ""),
                "patch": patch_suggestions,
                "fix_rationale": llm_result.get("fix_rationale", ""),
                "side_effects": llm_result.get("side_effects", ""),
                "verification_steps": llm_result.get("verification_steps", []),
                "targeted_suggestions": [{"layer": "LLM", "action": patch_suggestions[:200]}]
            }
        else:
            # 降级到原有规则引擎
            result = self._rule_based_suggestions(evidence_pack)
            result["mode"] = "rule"

        print(f"  [EVIDENCE ASSEMBLED] 模式: {result['mode']}, 状态: {result['status']}")
        print("==============================================================")
        return result

    def _llm_heal(
        self,
        evidence_pack: Dict[str, Any],
        visual_findings: List[str],
        runtime_errors: List[str],
        source_code: str,
        provider: str,
        model: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """调用 LLM + HealPrompt 生成可执行的 Patch"""
        try:
            from core.llm_gateway import LLMGateway
            from core.prompt_template_engine import HealPrompt

            effective_provider = os.environ.get("LLM_DEFAULT_PROVIDER", "gemini") if provider == "gemini" else provider
            pack_for_prompt = {
                "visual_findings": visual_findings,
                "runtime_errors": runtime_errors,
                "log_anomalies": evidence_pack.get("dimension_4_solver_failures", []),
                "player_feedback": [],
            }
            prompt = HealPrompt.from_evidence_pack(pack_for_prompt, source_code)
            gw = LLMGateway(provider=effective_provider, model=model)
            resp = gw.call(prompt.user, system=prompt.system)
            if not resp.success:
                return None
            # 解析 JSON 输出
            text = resp.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            print(f"  [LLM HEAL] 调用失败，降级到规则引擎: {e}")
            return None

    def _rule_based_suggestions(self, evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
        """原有规则引擎建议（降级备用）"""
        targeted_suggestions = []
        stderr = evidence_pack.get("dimension_1_runtime_stderr", "")
        if stderr and stderr != "None (Clean Run)":
            targeted_suggestions.append({
                "layer": "Runtime",
                "action": f"修复运行时错误: 检查异常栈并添加空值/边界检查: {stderr[:150]}"
            })

        probe_state = evidence_pack.get("dimension_2_probe_state", {})
        if probe_state:
            for k, v in probe_state.items():
                if v is False or v == "failed" or v == 0:
                    targeted_suggestions.append({
                        "layer": "Probe",
                        "action": f"探针状态异常 [{k} = {v}]: 请核验游戏初始化与循环状态"
                    })

        visual_findings = evidence_pack.get("dimension_3_visual_diff_violations", [])
        for vf in visual_findings:
            desc = vf.get("description", str(vf)) if isinstance(vf, dict) else str(vf)
            targeted_suggestions.append({
                "layer": "VisualDiff",
                "action": f"修复渲染层差异: {desc}"
            })

        solver_failures = evidence_pack.get("dimension_4_solver_failures", [])
        for sf in solver_failures:
            targeted_suggestions.append({
                "layer": "Solver",
                "action": f"修复数学求解器约束失败: {sf}"
            })

        has_blockers = evidence_pack.get("has_critical_blockers", False) or len(targeted_suggestions) > 0
        patch_text = "\n".join([f"- [{s['layer']}] {s['action']}" for s in targeted_suggestions])

        return {
            "status": "NEEDS_PATCH" if has_blockers else "PASS",
            "mode": "rule",
            "root_cause": targeted_suggestions[0]["action"] if targeted_suggestions else "无显著异常",
            "patch": patch_text,
            "fix_rationale": "基于规则引擎从四维运行证据链匹配的修复建议",
            "side_effects": "规则建议需开发者人工审查",
            "verification_steps": ["重新运行门禁测试", "核验探针快照与视觉渲染"],
            "targeted_suggestions": targeted_suggestions
        }


if __name__ == "__main__":
    healer = EvidenceHealer()
    pack = healer.assemble_evidence_pack(
        visual_findings=["Turret missing drop shadow layer"]
    )
    healer.diagnose_and_suggest_patch(pack, use_llm=False)
