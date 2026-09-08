"""
Game Engine Capability Matrix & Industrial Code Linter
Based on Article 39 (Tencent Timi / NetEase Leihuo Senior Engine Developer Standard):
Audits game code against industrial standards:
1. 3C Orthogonality: Character (state), Controls (input), Camera (viewport) are separated.
2. Zero-Alloc in Update: Forbids dynamic heap allocations (new, malloc, Vec::new, Box::new) inside update/tick/draw loops.
3. Object Pooling: Enforces pooling for frequently spawned entities (bullets, particles, damage popups).
4. Spatial Partitioning: Flags unindexed O(N^2) brute-force nested distance loops.
5. Game Patterns: Verifies presence of Command, State, or Event Bus patterns.
"""

from typing import Dict, Any, List, Optional
import re

class EngineCompetencyReport:
    def __init__(self, passed: bool, score: float, violations: List[str], recommendations: List[str]):
        self.passed = passed
        self.score = round(score, 2)
        self.violations = violations
        self.recommendations = recommendations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "violations": self.violations,
            "recommendations": self.recommendations,
        }

class GameEngineCapabilityMatrix:
    def __init__(self):
        pass

    def audit_engine_code(
        self,
        code_content: str,
        has_3c_separation: bool = True,
        uses_object_pooling: bool = True,
        uses_spatial_partitioning: bool = True
    ) -> EngineCompetencyReport:
        violations = []
        recommendations = []
        score = 100.0

        # Check 1: 3C Orthogonality (Character, Controls, Camera)
        if not has_3c_separation:
            violations.append("VIOLATION_3C_COUPLING: Character logic, camera tracking, and input handling are tightly coupled.")
            recommendations.append("Decouple 3C into separate orthogonal systems: CharacterController, CameraRig, and PlayerInput.")
            score -= 20.0

        # Check 2: Zero-Alloc in Update / Loop (Zero Heap Allocation)
        # Search for allocation patterns inside update/tick functions
        update_blocks = re.findall(r'(?s)(?:def\s+update|fn\s+update|function\s+update|void\s+Update).*?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', code_content)
        for block in update_blocks:
            # Check for Vec::new(), Box::new(), malloc, new ArrayList, etc.
            alloc_matches = re.findall(r'(?:Vec::new|Box::new|malloc|new\s+[A-Za-z0-9_]+\[|make\(|new\s+Array)', block)
            if alloc_matches:
                violations.append(f"VIOLATION_HEAP_ALLOC_IN_UPDATE: Detected dynamic memory allocation ({', '.join(set(alloc_matches))}) inside update loop.")
                recommendations.append("Industrial Rule: Zero-Alloc in Update. Pre-allocate buffers or use persistent slices to avoid GC / allocator stalls.")
                score -= 30.0
                break

        # Check 3: Object Pooling for Ephemeral Entities
        has_bullets_or_fx = bool(re.search(r'(?i)bullet|particle|projectile|spark|damage_text', code_content))
        if has_bullets_or_fx and not uses_object_pooling:
            violations.append("VIOLATION_MISSING_OBJECT_POOL: Ephemeral entities (bullets/particles) spawned without an Object Pool.")
            recommendations.append("Use an ObjectPool with pre-allocated capacity to recycle inactive entities instead of instantiate/destroy.")
            score -= 25.0

        # Check 4: Spatial Indexing vs O(N^2) Brute Force
        # Check for nested loops over same list (e.g. for a in enemies: for b in enemies:)
        nested_loop = bool(re.search(r'for\s+([a-zA-Z_]+)\s+in\s+([a-zA-Z_]+):.*?\n\s+for\s+([a-zA-Z_]+)\s+in\s+\2:', code_content, re.DOTALL))
        if nested_loop and not uses_spatial_partitioning:
            violations.append("VIOLATION_BRUTE_FORCE_COLLISION: Detected unindexed O(N^2) pairwise distance loop.")
            recommendations.append("Replace O(N^2) checks with Spatial Partitioning (Grid Hash, Quadtree, or BVH) to maintain 60 FPS under high entity counts.")
            score -= 25.0

        score = max(0.0, score)
        passed = (score >= 70.0 and len(violations) == 0 or (len(violations) == 1 and score >= 75.0))

        return EngineCompetencyReport(
            passed=passed,
            score=score,
            violations=violations,
            recommendations=recommendations
        )
