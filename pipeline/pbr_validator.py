"""纯标准库 glTF PBR 材质门禁。"""

import math
from pathlib import Path
from typing import Any, Dict, Mapping, Union

from pipeline.gltf_validator import load_gltf, validate_gltf


_SOURCE = Union[str, Path, Mapping[str, Any]]


def _result() -> Dict[str, Any]:
    return {"status": "FAIL", "valid": False, "errors": [], "warnings": [], "materials": []}


def _error(report: Dict[str, Any], code: str, message: str, **details: Any) -> None:
    item = {"code": code, "message": message}
    if details:
        item["details"] = details
    report["errors"].append(item)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _color(report: Dict[str, Any], value: Any, length: int, field: str, material_index: int) -> None:
    if not isinstance(value, list) or len(value) != length or not all(_number(item) for item in value):
        _error(report, "PBR_FIELD", "%s 必须是 %d 个有限数字" % (field, length), material=material_index)
        return
    if any(float(item) < 0.0 or float(item) > 1.0 for item in value):
        _error(report, "PBR_RANGE", "%s 必须位于 [0, 1]" % field, material=material_index)


def validate_pbr(source: _SOURCE, validate_structure: bool = True) -> Dict[str, Any]:
    """检查 BaseColor、Metallic、Roughness、Emissive 等实际材质字段。"""
    report = _result()
    try:
        document = load_gltf(source)
    except (OSError, ValueError, TypeError) as exc:
        _error(report, "LOAD_ERROR", str(exc))
        return report

    if validate_structure:
        structural = validate_gltf(source)
        if not structural["valid"]:
            report["warnings"].append({"code": "GLTF_STRUCTURE", "message": "结构门禁未通过", "details": structural["errors"]})

    materials = document.get("materials")
    if not isinstance(materials, list) or not materials:
        _error(report, "MATERIALS_MISSING", "glTF 必须包含至少一个材质")
        report["summary"] = {"error_count": len(report["errors"]), "warning_count": len(report["warnings"])}
        return report

    for material_index, material in enumerate(materials):
        if not isinstance(material, dict):
            _error(report, "MATERIAL_INVALID", "材质必须是 object", material=material_index)
            continue
        pbr = material.get("pbrMetallicRoughness")
        if not isinstance(pbr, dict):
            _error(report, "PBR_MISSING", "材质缺少 pbrMetallicRoughness", material=material_index)
            continue
        _color(report, pbr.get("baseColorFactor"), 4, "baseColorFactor", material_index)
        for field in ("metallicFactor", "roughnessFactor"):
            value = pbr.get(field)
            if not _number(value):
                _error(report, "PBR_FIELD", "%s 必须是有限数字" % field, material=material_index)
            elif not 0.0 <= float(value) <= 1.0:
                _error(report, "PBR_RANGE", "%s 必须位于 [0, 1]" % field, material=material_index)
        _color(report, material.get("emissiveFactor"), 3, "emissiveFactor", material_index)
        if "doubleSided" in material and not isinstance(material["doubleSided"], bool):
            _error(report, "PBR_FIELD", "doubleSided 必须是 boolean", material=material_index)
        report["materials"].append({
            "index": material_index,
            "name": material.get("name", ""),
            "base_color": pbr.get("baseColorFactor"),
            "metallic": pbr.get("metallicFactor"),
            "roughness": pbr.get("roughnessFactor"),
            "emissive": material.get("emissiveFactor"),
        })

    report["valid"] = not report["errors"]
    report["status"] = "SUCCESS" if report["valid"] else "FAIL"
    report["summary"] = {"error_count": len(report["errors"]), "warning_count": len(report["warnings"]), "material_count": len(materials)}
    return report


class PBRValidator:
    @staticmethod
    def validate(source: _SOURCE) -> Dict[str, Any]:
        return validate_pbr(source)


validate_pbr_materials = validate_pbr

__all__ = ["PBRValidator", "validate_pbr", "validate_pbr_materials"]
