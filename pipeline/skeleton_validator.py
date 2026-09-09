"""纯标准库 glTF 骨骼、权重与动画验证器。"""

import math
from pathlib import Path
from typing import Any, Dict, Mapping, Union

from pipeline.gltf_validator import GLTFValidationError, _load_document, _read_accessor_values, load_gltf, validate_gltf


_SOURCE = Union[str, Path, Mapping[str, Any]]


def _report() -> Dict[str, Any]:
    return {"status": "FAIL", "valid": False, "errors": [], "warnings": [], "checks": {"skins": False, "weights": False, "animations": False}}


def _error(report: Dict[str, Any], code: str, message: str, **details: Any) -> None:
    item = {"code": code, "message": message}
    if details:
        item["details"] = details
    report["errors"].append(item)


def _accessor(document: Mapping[str, Any], index: Any) -> Any:
    accessors = document.get("accessors", [])
    return accessors[index] if isinstance(index, int) and 0 <= index < len(accessors) else None


def validate_skeleton(source: _SOURCE, validate_structure: bool = True) -> Dict[str, Any]:
    """验证 SkeletalAnimationEngine 的 skins、JOINTS_0/WEIGHTS_0 和动画采样器。"""
    report = _report()
    try:
        document, base_dir = _load_document(source)
    except (OSError, ValueError, TypeError) as exc:
        _error(report, "LOAD_ERROR", str(exc))
        return report
    if validate_structure:
        structural = validate_gltf(source)
        if not structural["valid"]:
            report["warnings"].append({"code": "GLTF_STRUCTURE", "message": "结构门禁未通过", "details": structural["errors"]})

    skins = document.get("skins")
    nodes = document.get("nodes", [])
    if not isinstance(skins, list) or not skins:
        _error(report, "SKINS_MISSING", "glTF 必须包含至少一个 skin")
        report["summary"] = {"error_count": len(report["errors"]), "warning_count": len(report["warnings"])}
        return report
    if not isinstance(nodes, list):
        _error(report, "NODES_INVALID", "nodes 必须是数组")
        nodes = []

    buffers = None
    try:
        from pipeline.gltf_validator import _buffers
        buffers = _buffers(document, base_dir)
    except (OSError, ValueError, GLTFValidationError) as exc:
        _error(report, "BUFFER_INVALID", str(exc))

    for skin_index, skin in enumerate(skins):
        if not isinstance(skin, dict) or not isinstance(skin.get("joints"), list) or not skin["joints"]:
            _error(report, "SKIN_INVALID", "skin.joints 必须是非空数组", skin=skin_index)
            continue
        for joint_index in skin["joints"]:
            if not isinstance(joint_index, int) or not 0 <= joint_index < len(nodes):
                _error(report, "JOINT_REF", "skin.joints 引用越界", skin=skin_index, joint=joint_index)
        if "skeleton" in skin and (not isinstance(skin["skeleton"], int) or not 0 <= skin["skeleton"] < len(nodes)):
            _error(report, "SKELETON_REF", "skin.skeleton 引用越界", skin=skin_index)
        ibm = _accessor(document, skin.get("inverseBindMatrices"))
        if ibm is None or ibm.get("type") != "MAT4" or ibm.get("count") != len(skin["joints"]):
            _error(report, "IBM_INVALID", "inverseBindMatrices 必须与 joints 数量匹配", skin=skin_index)
    report["checks"]["skins"] = not any(item["code"] in {"SKIN_INVALID", "JOINT_REF", "SKELETON_REF", "IBM_INVALID"} for item in report["errors"])

    mesh_count = 0
    for mesh_index, mesh in enumerate(document.get("meshes", [])):
        if not isinstance(mesh, dict):
            continue
        for primitive_index, primitive in enumerate(mesh.get("primitives", [])):
            attributes = primitive.get("attributes", {}) if isinstance(primitive, dict) else {}
            joints_accessor = _accessor(document, attributes.get("JOINTS_0"))
            weights_accessor = _accessor(document, attributes.get("WEIGHTS_0"))
            position_accessor = _accessor(document, attributes.get("POSITION"))
            if joints_accessor is None or weights_accessor is None:
                _error(report, "SKIN_ATTRIBUTES", "蒙皮 primitive 必须包含 JOINTS_0 与 WEIGHTS_0", mesh=mesh_index, primitive=primitive_index)
                continue
            mesh_count += 1
            if joints_accessor.get("type") != "VEC4" or joints_accessor.get("componentType") not in (5121, 5123):
                _error(report, "JOINTS_LAYOUT", "JOINTS_0 必须是 VEC4 无符号整数", mesh=mesh_index, primitive=primitive_index)
            if weights_accessor.get("type") != "VEC4" or weights_accessor.get("componentType") not in (5121, 5123, 5126):
                _error(report, "WEIGHTS_LAYOUT", "WEIGHTS_0 必须是 VEC4 数值 accessor", mesh=mesh_index, primitive=primitive_index)
            if position_accessor is not None and weights_accessor.get("count") != position_accessor.get("count"):
                _error(report, "WEIGHTS_COUNT", "权重数量必须等于顶点数量", mesh=mesh_index, primitive=primitive_index)
            if buffers is None:
                continue
            try:
                joint_values = _read_accessor_values(document, attributes["JOINTS_0"], buffers=buffers, base_dir=base_dir)
                weight_values = _read_accessor_values(document, attributes["WEIGHTS_0"], buffers=buffers, base_dir=base_dir)
            except (KeyError, GLTFValidationError) as exc:
                _error(report, "WEIGHTS_DATA", str(exc), mesh=mesh_index, primitive=primitive_index)
                continue
            joint_limit = len(skins[0].get("joints", []))
            for vertex_index, (joint_tuple, weight_tuple) in enumerate(zip(joint_values, weight_values)):
                joints = joint_tuple if isinstance(joint_tuple, tuple) else (joint_tuple,)
                weights = weight_tuple if isinstance(weight_tuple, tuple) else (weight_tuple,)
                if any(not isinstance(value, int) or value < 0 or value >= joint_limit for value in joints):
                    _error(report, "JOINT_INDEX", "顶点骨骼索引超出 skin.joints 范围", vertex=vertex_index)
                if any(not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) < 0.0 or float(value) > 1.0 for value in weights):
                    _error(report, "WEIGHT_RANGE", "顶点权重必须是 [0, 1] 内有限数字", vertex=vertex_index)
                total = sum(float(value) for value in weights)
                if total <= 0.0 or abs(total - 1.0) > 0.002:
                    _error(report, "WEIGHT_SUM", "每个顶点的四权重之和必须约等于 1", vertex=vertex_index, total=total)
    report["checks"]["weights"] = mesh_count > 0 and not any(item["code"].startswith(("SKIN_ATTRIBUTES", "JOINTS_", "WEIGHTS_", "JOINT_INDEX", "WEIGHT_")) for item in report["errors"])

    animations = document.get("animations")
    if not isinstance(animations, list) or not animations:
        _error(report, "ANIMATIONS_MISSING", "glTF 必须包含至少一个 animation")
    else:
        for animation_index, animation in enumerate(animations):
            if not isinstance(animation, dict) or not isinstance(animation.get("samplers"), list) or not isinstance(animation.get("channels"), list):
                _error(report, "ANIMATION_INVALID", "animation.samplers/channels 无效", animation=animation_index)
                continue
            for sampler_index, sampler in enumerate(animation["samplers"]):
                input_accessor = _accessor(document, sampler.get("input"))
                output_accessor = _accessor(document, sampler.get("output"))
                if input_accessor is None or output_accessor is None:
                    _error(report, "ANIMATION_ACCESSOR", "动画 sampler accessor 引用越界", animation=animation_index, sampler=sampler_index)
                    continue
                if input_accessor.get("type") != "SCALAR" or input_accessor.get("componentType") != 5126:
                    _error(report, "ANIMATION_INPUT", "动画 input 必须是 float SCALAR", animation=animation_index, sampler=sampler_index)
                if output_accessor.get("type") not in ("VEC3", "VEC4") or output_accessor.get("componentType") != 5126:
                    _error(report, "ANIMATION_OUTPUT", "动画 output 必须是 float VEC3/VEC4", animation=animation_index, sampler=sampler_index)
                if buffers is not None:
                    try:
                        times = _read_accessor_values(document, sampler["input"], buffers=buffers, base_dir=base_dir)
                        if any(float(times[i]) > float(times[i + 1]) for i in range(len(times) - 1)):
                            _error(report, "ANIMATION_TIME", "动画时间必须单调不减", animation=animation_index, sampler=sampler_index)
                    except (KeyError, GLTFValidationError) as exc:
                        _error(report, "ANIMATION_DATA", str(exc), animation=animation_index, sampler=sampler_index)
            for channel_index, channel in enumerate(animation["channels"]):
                target = channel.get("target", {}) if isinstance(channel, dict) else {}
                if not isinstance(target, dict) or not isinstance(target.get("node"), int) or not 0 <= target["node"] < len(nodes):
                    _error(report, "ANIMATION_NODE", "动画 target.node 引用越界", animation=animation_index, channel=channel_index)
                if target.get("path") not in ("translation", "rotation", "scale", "weights"):
                    _error(report, "ANIMATION_PATH", "动画 target.path 无效", animation=animation_index, channel=channel_index)
        report["checks"]["animations"] = not any(item["code"].startswith("ANIMATION_") for item in report["errors"])

    report["valid"] = not report["errors"]
    report["status"] = "SUCCESS" if report["valid"] else "FAIL"
    report["summary"] = {"error_count": len(report["errors"]), "warning_count": len(report["warnings"]), "skin_count": len(skins), "animation_count": len(animations) if isinstance(animations, list) else 0}
    return report


class SkeletonValidator:
    @staticmethod
    def validate(source: _SOURCE) -> Dict[str, Any]:
        return validate_skeleton(source)


validate_skeleton_asset = validate_skeleton

__all__ = ["SkeletonValidator", "validate_skeleton", "validate_skeleton_asset"]
