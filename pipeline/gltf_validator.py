"""纯标准库 glTF 2.0 结构与几何引用验证器。"""

import base64
import binascii
import json
import math
import struct
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


_SOURCE = Union[str, Path, Mapping[str, Any]]
_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
_COMPONENT_BYTES = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
_COMPONENT_FORMAT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}


class GLTFValidationError(ValueError):
    """输入不是可验证的 glTF 文档。"""


def _load_document(source: _SOURCE) -> Tuple[Dict[str, Any], Optional[Path]]:
    if isinstance(source, Mapping):
        return dict(source), None
    path = Path(source)
    text = path.read_text(encoding="utf-8")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GLTFValidationError("glTF JSON 无法解析: %s" % exc) from exc
    if not isinstance(document, dict):
        raise GLTFValidationError("glTF 根节点必须是 JSON object")
    return document, path.parent


def load_gltf(source: _SOURCE) -> Dict[str, Any]:
    """加载 glTF 文件或直接返回文档副本。"""
    return _load_document(source)[0]


def _issue(report: Dict[str, Any], level: str, code: str, message: str, **details: Any) -> None:
    item = {"code": code, "message": message}
    if details:
        item["details"] = details
    report[level].append(item)


def _ref(array: Sequence[Any], index: Any) -> Optional[Any]:
    return array[index] if isinstance(index, int) and 0 <= index < len(array) else None


def _decode_uri(uri: str, base_dir: Optional[Path]) -> bytes:
    if uri.startswith("data:"):
        try:
            header, payload = uri.split(",", 1)
        except ValueError as exc:
            raise GLTFValidationError("data URI 缺少 payload") from exc
        if ";base64" not in header:
            raise GLTFValidationError("仅支持 base64 data URI")
        try:
            return base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise GLTFValidationError("data URI base64 无效") from exc
    if base_dir is None:
        raise GLTFValidationError("外部 buffer 需要文件路径上下文")
    return (base_dir / uri).read_bytes()


def _buffers(document: Mapping[str, Any], base_dir: Optional[Path]) -> List[bytes]:
    result = []
    for item in document.get("buffers", []):
        if not isinstance(item, dict) or not isinstance(item.get("byteLength"), int):
            raise GLTFValidationError("buffer 缺少合法 byteLength")
        if "uri" not in item:
            raise GLTFValidationError("不支持未内嵌的 GLB buffer")
        data = _decode_uri(item["uri"], base_dir)
        if len(data) < item["byteLength"]:
            raise GLTFValidationError("buffer 实际长度小于 byteLength")
        result.append(data)
    return result


def _accessor_layout(accessor: Mapping[str, Any]) -> Tuple[int, int, int]:
    component_type = accessor.get("componentType")
    kind = accessor.get("type")
    if component_type not in _COMPONENT_BYTES:
        raise GLTFValidationError("accessor componentType 无效")
    if kind not in _COMPONENTS:
        raise GLTFValidationError("accessor type 无效")
    if not isinstance(accessor.get("count"), int) or accessor["count"] < 0:
        raise GLTFValidationError("accessor count 无效")
    return component_type, _COMPONENTS[kind], _COMPONENT_BYTES[component_type] * _COMPONENTS[kind]


def _read_accessor_values(
    document: Mapping[str, Any],
    accessor_index: int,
    buffers: Optional[List[bytes]] = None,
    base_dir: Optional[Path] = None,
) -> List[Union[int, float, Tuple[Union[int, float], ...]]]:
    accessors = document.get("accessors", [])
    accessor = _ref(accessors, accessor_index)
    if not isinstance(accessor, dict):
        raise GLTFValidationError("accessor 引用越界")
    component_type, component_count, element_size = _accessor_layout(accessor)
    if buffers is None:
        buffers = _buffers(document, base_dir)
    view_index = accessor.get("bufferView")
    if view_index is None:
        raise GLTFValidationError("不支持没有 bufferView 的 sparse accessor")
    views = document.get("bufferViews", [])
    view = _ref(views, view_index)
    if not isinstance(view, dict):
        raise GLTFValidationError("accessor bufferView 引用越界")
    buffer_index = view.get("buffer", 0)
    if not isinstance(buffer_index, int) or buffer_index < 0 or buffer_index >= len(buffers):
        raise GLTFValidationError("bufferView buffer 引用越界")
    raw = buffers[buffer_index]
    view_offset = view.get("byteOffset", 0)
    accessor_offset = accessor.get("byteOffset", 0)
    stride = view.get("byteStride", element_size)
    if not all(isinstance(value, int) and value >= 0 for value in (view_offset, accessor_offset, stride)):
        raise GLTFValidationError("bufferView/accessor 偏移或 stride 无效")
    if stride < element_size:
        raise GLTFValidationError("byteStride 小于 accessor 元素长度")
    start = view_offset + accessor_offset
    end = start if accessor["count"] == 0 else start + stride * (accessor["count"] - 1) + element_size
    if end > view_offset + view.get("byteLength", 0) or end > len(raw):
        raise GLTFValidationError("accessor 数据超出 bufferView 或 buffer")
    fmt = "<" + _COMPONENT_FORMAT[component_type] * component_count
    values: List[Union[int, float, Tuple[Union[int, float], ...]]] = []
    for index in range(accessor["count"]):
        offset = start + index * stride
        unpacked = struct.unpack_from(fmt, raw, offset)
        value: Union[int, float, Tuple[Union[int, float], ...]] = unpacked[0] if component_count == 1 else unpacked
        values.append(value)
    return values


def read_accessor_values(source: _SOURCE, accessor_index: int) -> List[Any]:
    """读取一个 accessor，供 PBR/骨骼门禁复用。"""
    document, base_dir = _load_document(source)
    return _read_accessor_values(document, accessor_index, base_dir=base_dir)


def _validate_ref(report: Dict[str, Any], document: Mapping[str, Any], field: str, index: Any, length: int) -> None:
    if not isinstance(index, int) or not 0 <= index < length:
        _issue(report, "errors", "REF_OUT_OF_RANGE", "%s 引用越界" % field, index=index, length=length)


def validate_gltf(source: _SOURCE) -> Dict[str, Any]:
    """验证当前 Asset3DBridge/SkeletalAnimationEngine 生成的 glTF 结构。"""
    report: Dict[str, Any] = {
        "status": "FAIL",
        "valid": False,
        "errors": [],
        "warnings": [],
        "checks": {"version": False, "indices": False, "buffers": False, "accessors": False},
    }
    try:
        document, base_dir = _load_document(source)
    except (OSError, ValueError, TypeError) as exc:
        _issue(report, "errors", "LOAD_ERROR", str(exc))
        return report

    asset = document.get("asset")
    if not isinstance(asset, dict) or asset.get("version") != "2.0":
        _issue(report, "errors", "GLTF_VERSION", "asset.version 必须为 2.0")
    else:
        report["checks"]["version"] = True

    buffers: List[bytes] = []
    try:
        buffers = _buffers(document, base_dir)
        report["checks"]["buffers"] = True
    except (OSError, ValueError, GLTFValidationError) as exc:
        _issue(report, "errors", "BUFFER_INVALID", str(exc))

    buffer_views = document.get("bufferViews", [])
    accessors = document.get("accessors", [])
    if not isinstance(buffer_views, list) or not isinstance(accessors, list):
        _issue(report, "errors", "TABLE_INVALID", "bufferViews/accessors 必须为数组")
        buffer_views, accessors = [], []
    else:
        for index, view in enumerate(buffer_views):
            if not isinstance(view, dict):
                _issue(report, "errors", "BUFFERVIEW_INVALID", "bufferView 必须为 object", index=index)
                continue
            _validate_ref(report, document, "bufferView.buffer", view.get("buffer", 0), len(buffers))
            if not isinstance(view.get("byteLength"), int) or view["byteLength"] < 0:
                _issue(report, "errors", "BUFFERVIEW_LENGTH", "bufferView.byteLength 无效", index=index)
            if view.get("byteOffset", 0) % 4 != 0:
                _issue(report, "errors", "BUFFERVIEW_ALIGNMENT", "bufferView.byteOffset 必须 4 字节对齐", index=index)
        for index, accessor in enumerate(accessors):
            if not isinstance(accessor, dict):
                _issue(report, "errors", "ACCESSOR_INVALID", "accessor 必须为 object", index=index)
                continue
            try:
                _accessor_layout(accessor)
            except GLTFValidationError as exc:
                _issue(report, "errors", "ACCESSOR_LAYOUT", str(exc), index=index)
                continue
            if "bufferView" in accessor:
                _validate_ref(report, document, "accessor.bufferView", accessor["bufferView"], len(buffer_views))
            else:
                _issue(report, "errors", "SPARSE_UNSUPPORTED", "accessor 缺少 bufferView，当前门禁不接受 sparse accessor", index=index)
            if isinstance(accessor.get("bufferView"), int) and 0 <= accessor["bufferView"] < len(buffer_views) and buffers:
                try:
                    _read_accessor_values(document, index, buffers=buffers, base_dir=base_dir)
                except GLTFValidationError as exc:
                    _issue(report, "errors", "ACCESSOR_DATA", str(exc), index=index)
        report["checks"]["accessors"] = not any(item["code"].startswith("ACCESSOR") or item["code"] == "SPARSE_UNSUPPORTED" for item in report["errors"])

    meshes = document.get("meshes", [])
    index_check_ok = True
    for mesh_index, mesh in enumerate(meshes if isinstance(meshes, list) else []):
        if not isinstance(mesh, dict) or not isinstance(mesh.get("primitives"), list):
            _issue(report, "errors", "MESH_INVALID", "mesh/primitives 无效", index=mesh_index)
            index_check_ok = False
            continue
        for primitive_index, primitive in enumerate(mesh["primitives"]):
            if not isinstance(primitive, dict):
                _issue(report, "errors", "PRIMITIVE_INVALID", "primitive 无效", mesh=mesh_index, primitive=primitive_index)
                index_check_ok = False
                continue
            attributes = primitive.get("attributes", {})
            if not isinstance(attributes, dict):
                _issue(report, "errors", "ATTRIBUTES_INVALID", "primitive.attributes 无效", mesh=mesh_index)
                index_check_ok = False
                continue
            for semantic, accessor_index in attributes.items():
                if not isinstance(accessor_index, int) or not 0 <= accessor_index < len(accessors):
                    _issue(report, "errors", "ATTRIBUTE_REF", "顶点属性 accessor 引用越界", semantic=semantic)
                    index_check_ok = False
            if "indices" not in primitive:
                _issue(report, "errors", "INDICES_MISSING", "primitive 缺少 indices")
                index_check_ok = False
                continue
            indices_index = primitive["indices"]
            if not isinstance(indices_index, int) or not 0 <= indices_index < len(accessors):
                _issue(report, "errors", "INDICES_REF", "indices accessor 引用越界")
                index_check_ok = False
                continue
            index_accessor = accessors[indices_index]
            if index_accessor.get("type") != "SCALAR" or index_accessor.get("componentType") not in (5121, 5123, 5125):
                _issue(report, "errors", "INDICES_LAYOUT", "indices 必须是 SCALAR 且使用无符号整数")
                index_check_ok = False
                continue
            position_index = attributes.get("POSITION")
            if not isinstance(position_index, int) or not 0 <= position_index < len(accessors):
                _issue(report, "errors", "POSITION_MISSING", "primitive 缺少有效 POSITION")
                index_check_ok = False
                continue
            position_count = accessors[position_index].get("count", 0)
            try:
                index_values = _read_accessor_values(document, indices_index, buffers=buffers, base_dir=base_dir)
            except GLTFValidationError as exc:
                _issue(report, "errors", "INDICES_DATA", str(exc))
                index_check_ok = False
                continue
            if len(index_values) % 3 != 0:
                _issue(report, "errors", "INDICES_TRIANGLES", "三角形 primitive 的 indices 数量必须为 3 的倍数")
                index_check_ok = False
            for value in index_values:
                if not isinstance(value, int) or value < 0 or value >= position_count:
                    _issue(report, "errors", "INDEX_OUT_OF_RANGE", "indices 超出 POSITION 范围", value=value, position_count=position_count)
                    index_check_ok = False
    report["checks"]["indices"] = index_check_ok and isinstance(meshes, list) and bool(meshes)
    if not isinstance(meshes, list) or not meshes:
        _issue(report, "errors", "MESHES_MISSING", "glTF 必须包含至少一个 mesh")

    report["valid"] = not report["errors"]
    report["status"] = "SUCCESS" if report["valid"] else "FAIL"
    report["summary"] = {"error_count": len(report["errors"]), "warning_count": len(report["warnings"])}
    return report


class GLTFValidator:
    """面向对象入口，便于管线门禁复用。"""

    @staticmethod
    def validate(source: _SOURCE) -> Dict[str, Any]:
        return validate_gltf(source)

    @staticmethod
    def validate_file(path: Union[str, Path]) -> Dict[str, Any]:
        return validate_gltf(path)


validate_gltf_file = validate_gltf

__all__ = ["GLTFValidator", "GLTFValidationError", "load_gltf", "read_accessor_values", "validate_gltf", "validate_gltf_file"]
