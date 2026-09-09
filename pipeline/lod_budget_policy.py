"""纯标准库 LOD 三角形预算策略与门禁。"""

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from pipeline.gltf_validator import load_gltf, validate_gltf


_SOURCE = Union[str, Path, Mapping[str, Any]]

DEFAULT_BUDGETS = {
    "hero": {"base": 50000, "lod1": 25000, "lod2": 10000, "lod3": 3000},
    "gameplay": {"base": 20000, "lod1": 10000, "lod2": 4000, "lod3": 1500},
    "mobile": {"base": 8000, "lod1": 4000, "lod2": 1600, "lod3": 600},
}


def _error(report: Dict[str, Any], code: str, message: str, **details: Any) -> None:
    item = {"code": code, "message": message}
    if details:
        item["details"] = details
    report["errors"].append(item)


def _triangle_count(document: Mapping[str, Any]) -> int:
    total = 0
    accessors = document.get("accessors", [])
    for mesh in document.get("meshes", []):
        if not isinstance(mesh, dict):
            continue
        for primitive in mesh.get("primitives", []):
            if not isinstance(primitive, dict):
                continue
            indices = primitive.get("indices")
            if isinstance(indices, int) and 0 <= indices < len(accessors):
                total += int(accessors[indices].get("count", 0)) // 3
    return total


def _lods_from_input(source: _SOURCE, document: Mapping[str, Any]) -> List[int]:
    if isinstance(source, Mapping):
        for key in ("lods", "lod_triangle_counts"):
            if isinstance(source.get(key), list):
                return [int(value) for value in source[key]]
    extras = document.get("extras", {})
    if isinstance(extras, dict):
        for key in ("lods", "lod_triangle_counts"):
            if isinstance(extras.get(key), list):
                return [int(value) for value in extras[key]]
    return []


def validate_lod_budget(
    source: _SOURCE,
    profile: str = "gameplay",
    budgets: Optional[Mapping[str, int]] = None,
    require_explicit_lods: bool = False,
) -> Dict[str, Any]:
    """验证基础网格和可选 LOD 链是否满足三角形预算。"""
    report: Dict[str, Any] = {"status": "FAIL", "valid": False, "errors": [], "warnings": [], "profile": profile}
    selected = dict(budgets or DEFAULT_BUDGETS.get(profile, DEFAULT_BUDGETS["gameplay"]))
    report["budgets"] = selected
    try:
        document = load_gltf(source)
    except (OSError, ValueError, TypeError) as exc:
        _error(report, "LOAD_ERROR", str(exc))
        return report
    structural = validate_gltf(source)
    if not structural["valid"]:
        report["warnings"].append({"code": "GLTF_STRUCTURE", "message": "结构门禁未通过", "details": structural["errors"]})

    if isinstance(source, Mapping) and isinstance(source.get("triangles_count"), int):
        base_triangles = source["triangles_count"]
    else:
        base_triangles = _triangle_count(document)
    lods = _lods_from_input(source, document)
    if lods and lods[0] != base_triangles:
        _error(report, "LOD_BASE_MISMATCH", "LOD 链第一档必须等于基础三角形数", base=base_triangles, lod0=lods[0])
    if not lods:
        if require_explicit_lods:
            _error(report, "LOD_MISSING", "未提供显式 LOD 三角形数据")
        else:
            report["warnings"].append({"code": "LOD_NOT_EXPORTED", "message": "当前桥接输出未携带显式 LOD 链，已仅检查基础预算"})
        lods = [base_triangles]
    if base_triangles < 0:
        _error(report, "LOD_COUNT", "基础三角形数不能为负")
    if base_triangles > selected.get("base", 0):
        _error(report, "LOD_BUDGET", "基础网格超过三角形预算", triangles=base_triangles, budget=selected.get("base"))
    for level, count in enumerate(lods[1:], start=1):
        if count < 0:
            _error(report, "LOD_COUNT", "LOD 三角形数不能为负", level=level)
        if count > lods[level - 1]:
            _error(report, "LOD_ORDER", "LOD 三角形数必须随级别递减", level=level, previous=lods[level - 1], current=count)
        budget = selected.get("lod%d" % level)
        if budget is not None and count > budget:
            _error(report, "LOD_BUDGET", "LOD 超过三角形预算", level=level, triangles=count, budget=budget)
    report["base_triangles"] = base_triangles
    report["lod_triangles"] = lods
    report["valid"] = not report["errors"]
    report["status"] = "SUCCESS" if report["valid"] else "FAIL"
    report["summary"] = {"error_count": len(report["errors"]), "warning_count": len(report["warnings"]), "lod_count": len(lods)}
    return report


class LODBudgetPolicy:
    """可配置的 LOD 预算门面。"""

    def __init__(self, profile: str = "gameplay", budgets: Optional[Mapping[str, int]] = None) -> None:
        self.profile = profile
        self.budgets = dict(budgets) if budgets is not None else None

    def validate(self, source: _SOURCE, require_explicit_lods: bool = False) -> Dict[str, Any]:
        return validate_lod_budget(source, self.profile, self.budgets, require_explicit_lods)


evaluate_lod_budget = validate_lod_budget

__all__ = ["DEFAULT_BUDGETS", "LODBudgetPolicy", "evaluate_lod_budget", "validate_lod_budget"]
