"""
Antigravity Narrative Pedagogy & SLO Quality Audit Engine
=========================================================
Based on Seth Hudson's GDC framework ("Pedagogy of Game Writing"):
  - 5 Functional Competencies (Fun-Comps): Writing Craft, Collaboration,
    Mechanics Hook, Tool Fluency, Player Mindset.
  - 3 Dynamic Roles: Wordsmith (craft), Sensemaker (linkage), Advocate (arbitration).
  - Industrial SLO Quality Closed-Loop: Dead-End Audit, Mechanic Density,
    Word Budget Compliance, and Emotional Tension Curve Variance.
"""

import math
import re
from typing import Dict, List, Any, Optional, Tuple


class SLOMetricEvaluator:
    """Evaluates narrative DAGs against industrial Service Level Objectives."""

    def __init__(self, max_chars_per_node: int = 75, min_mechanic_density: float = 0.30):
        self.max_chars = max_chars_per_node
        self.min_density = min_mechanic_density

    def audit(self, narrative_nodes: Dict[str, Dict[str, Any]], start_node_id: str) -> Dict[str, Any]:
        """Runs full 4-point SLO audit on dialogue nodes."""
        reachability_res = self._check_reachability(narrative_nodes, start_node_id)
        mechanic_res = self._check_mechanic_density(narrative_nodes)
        budget_res = self._check_word_budget(narrative_nodes)
        tension_res = self._check_tension_variance(narrative_nodes, start_node_id)

        all_passed = (
            reachability_res["passed"]
            and mechanic_res["passed"]
            and budget_res["passed"]
            and tension_res["passed"]
        )

        return {
            "compliant": all_passed,
            "overall_score": round(
                (reachability_res["score"] + mechanic_res["score"] + budget_res["score"] + tension_res["score"]) / 4.0,
                2
            ),
            "reachability": reachability_res,
            "mechanic_density": mechanic_res,
            "word_budget": budget_res,
            "tension_curve": tension_res,
            "recommendations": self._generate_recommendations(
                reachability_res, mechanic_res, budget_res, tension_res
            )
        }

    def _check_reachability(self, nodes: Dict[str, Dict[str, Any]], start_id: str) -> Dict[str, Any]:
        if start_id not in nodes:
            return {"passed": False, "score": 0.0, "dead_ends": [start_id], "orphans": []}

        visited = set()
        queue = [start_id]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            data = nodes.get(curr, {})
            # Next nodes can be from "next", "choices"
            next_ids = []
            if "next" in data and data["next"]:
                next_ids.append(data["next"])
            for ch in data.get("choices", []):
                if "next" in ch:
                    next_ids.append(ch["next"])
            for nid in next_ids:
                if nid != "END" and nid in nodes and nid not in visited:
                    queue.append(nid)

        orphans = [nid for nid in nodes if nid not in visited]
        dead_ends = []
        for nid in visited:
            data = nodes[nid]
            is_end = data.get("is_end", False) or data.get("next") == "END"
            has_choices = len(data.get("choices", [])) > 0
            has_next = bool(data.get("next"))
            if not is_end and not has_choices and not has_next:
                dead_ends.append(nid)

        passed = (len(dead_ends) == 0 and len(orphans) == 0)
        score = 1.0 if passed else max(0.0, 1.0 - (len(dead_ends) + len(orphans)) * 0.2)
        return {
            "passed": passed,
            "score": round(score, 2),
            "dead_ends": dead_ends,
            "orphans": orphans
        }

    def _check_mechanic_density(self, nodes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        if not nodes:
            return {"passed": False, "score": 0.0, "density": 0.0}

        hooked_count = 0
        for nid, data in nodes.items():
            text = data.get("text", "")
            has_var = bool(re.search(r"\{[a-zA-Z0-9_]+\}", text))
            has_actions = bool(data.get("actions"))
            has_prereqs = bool(data.get("prerequisites"))
            has_conditions = any("condition" in ch for ch in data.get("choices", []))
            if has_var or has_actions or has_prereqs or has_conditions:
                hooked_count += 1

        density = hooked_count / len(nodes)
        passed = density >= self.min_density
        score = min(1.0, density / self.min_density) if self.min_density > 0 else 1.0
        return {
            "passed": passed,
            "score": round(score, 2),
            "density": round(density, 3),
            "required_density": self.min_density,
            "hooked_nodes": hooked_count,
            "total_nodes": len(nodes)
        }

    def _check_word_budget(self, nodes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        violations = []
        for nid, data in nodes.items():
            tlen = len(data.get("text", ""))
            if tlen > self.max_chars:
                violations.append({"node_id": nid, "length": tlen, "limit": self.max_chars})

        passed = len(violations) == 0
        score = 1.0 if passed else max(0.0, 1.0 - (len(violations) / max(1, len(nodes))))
        return {
            "passed": passed,
            "score": round(score, 2),
            "violations_count": len(violations),
            "violations": violations
        }

    def _check_tension_variance(self, nodes: Dict[str, Dict[str, Any]], start_id: str) -> Dict[str, Any]:
        tensions = [data.get("tension", 0.5) for data in nodes.values()]
        if not tensions:
            return {"passed": False, "score": 0.0, "variance": 0.0}

        mean = sum(tensions) / len(tensions)
        variance = sum((x - mean) ** 2 for x in tensions) / len(tensions)
        passed = variance >= 0.02  # Expect some dynamic fluctuation
        score = min(1.0, variance / 0.04)
        return {
            "passed": passed,
            "score": round(score, 2),
            "mean_tension": round(mean, 2),
            "variance": round(variance, 4)
        }

    def _generate_recommendations(self, reach, mech, budget, tension) -> List[str]:
        recs = []
        if not reach["passed"]:
            if reach["dead_ends"]:
                recs.append(f"Fix dead-end nodes missing next/choices: {reach['dead_ends']}")
            if reach["orphans"]:
                recs.append(f"Connect unreachable orphan nodes to main graph: {reach['orphans']}")
        if not mech["passed"]:
            recs.append(f"Increase game mechanic linkage (density {mech['density']*100:.1f}% < {mech['required_density']*100:.1f}%). Add state checks or variable tags.")
        if not budget["passed"]:
            recs.append(f"Trim {budget['violations_count']} word-budget violations (> {self.max_chars} chars) for mobile/wechat viewport.")
        if not tension["passed"]:
            recs.append("Narrative tension curve is too flat. Introduce moments of conflict or relief.")
        return recs


class ThreeRoleNarrativePipeline:
    """Orchestrates narrative generation through Wordsmith, Sensemaker, and Advocate."""

    def __init__(self, evaluator: Optional[SLOMetricEvaluator] = None):
        self.evaluator = evaluator or SLOMetricEvaluator()

    def process(
        self,
        raw_draft: Dict[str, Dict[str, Any]],
        start_id: str,
        game_context: Dict[str, Any]
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """Executes full 3-role pipeline and evaluates SLO compliance."""

        # Stage 1: Wordsmith (Polish language, enforce character voice)
        wordsmith_nodes = self._wordsmith_pass(raw_draft)

        # Stage 2: Sensemaker (Bind mechanics, triggers, inventory variables)
        sensemaker_nodes = self._sensemaker_pass(wordsmith_nodes, game_context)

        # Stage 3: Advocate (Trim length, balance pacing, enforce budget)
        advocate_nodes = self._advocate_pass(sensemaker_nodes)

        # Stage 4: SLO Quality Audit
        audit_report = self.evaluator.audit(advocate_nodes, start_id)

        return advocate_nodes, audit_report

    def _wordsmith_pass(self, nodes: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        out = {}
        for nid, data in nodes.items():
            d = dict(data)
            text = d.get("text", "").strip()
            # Wordsmith removes redundant exclamation marks and adds speaker punctuation
            text = re.sub(r"!{2,}", "!", text)
            d["text"] = text
            out[nid] = d
        return out

    def _sensemaker_pass(self, nodes: Dict[str, Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        out = {}
        known_vars = context.get("variables", {})
        for nid, data in nodes.items():
            d = dict(data)
            # If node mentions context keywords, link action or variable
            text = d.get("text", "")
            for var_key, var_val in known_vars.items():
                if f"${var_key}" in text:
                    text = text.replace(f"${var_key}", f"{{{var_key}}}")
            d["text"] = text
            out[nid] = d
        return out

    def _advocate_pass(self, nodes: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        out = {}
        for nid, data in nodes.items():
            d = dict(data)
            text = d.get("text", "")
            # Advocate trims overly verbose exposition (> 75 chars)
            if len(text) > 75:
                # Truncate to first clean clause or punchy sentence
                puncts = [m.start() for m in re.finditer(r"[，。！？,\.!?]", text) if m.start() < 72]
                if puncts:
                    best_cut = puncts[-1] + 1
                    text = text[:best_cut].strip()
                else:
                    text = text[:72] + "..."
            d["text"] = text
            out[nid] = d
        return out


class LegacyNarrativeHealer:
    """
    Implements Seth Hudson's 'Handoff Shock Exercise' for AI Agents:
    Transforms chaotic, broken, or legacy narrative graphs into compliant,
    production-ready DAGs by repairing dead-ends, stitching orphans, and
    enforcing mechanics hookage.
    """

    def __init__(self, evaluator: Optional[SLOMetricEvaluator] = None):
        self.evaluator = evaluator or SLOMetricEvaluator()

    def heal(
        self,
        broken_nodes: Dict[str, Dict[str, Any]],
        start_id: str,
        default_exit_id: str = "END"
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """Repairs dead-ends, binds orphan nodes, and cleans up broken paths."""
        healed = {}
        for k, v in broken_nodes.items():
            healed[k] = dict(v)

        # 1. Audit before healing
        initial_audit = self.evaluator.audit(healed, start_id)

        # 2. Repair dead-ends (nodes with no next, choices, or is_end)
        for dead_id in initial_audit["reachability"]["dead_ends"]:
            if dead_id in healed:
                # Advocate decision: route dead end to safe exit or mark as end
                healed[dead_id]["next"] = default_exit_id
                healed[dead_id]["is_end"] = True

        # 3. Stitch unreachable orphan nodes to the start or a fallback branch
        for orphan_id in initial_audit["reachability"]["orphans"]:
            if orphan_id in healed:
                # Connect orphan into fallback choices at start node
                start_node = healed.get(start_id)
                if start_node:
                    choices = start_node.get("choices", [])
                    choices.append({
                        "text": f"调查遗留线索 [{orphan_id}]",
                        "next": orphan_id
                    })
                    start_node["choices"] = choices

        # 4. Repair mechanic hooks if density is too low
        mech_res = self.evaluator._check_mechanic_density(healed)
        if not mech_res["passed"]:
            for nid, node in healed.items():
                if not node.get("actions") and "{" not in node.get("text", ""):
                    node["actions"] = [{"type": "gain_clue", "clue_id": f"clue_{nid}"}]
                    break

        # 5. Final audit after healing
        final_audit = self.evaluator.audit(healed, start_id)
        return healed, {
            "healed": True,
            "repaired_dead_ends": len(initial_audit["reachability"]["dead_ends"]),
            "stitched_orphans": len(initial_audit["reachability"]["orphans"]),
            "initial_score": initial_audit["overall_score"],
            "final_score": final_audit["overall_score"],
            "final_audit": final_audit
        }

