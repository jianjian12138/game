#!/usr/bin/env python3
"""
pipeline/webgl_runtime_probe.py: 3D 资产运行时事实探针 (WebGL Runtime Probe)

诚实边界（红线 13.2）：
    本模块默认只能采集「静态事实」，绝不代表资产已被渲染。
    只有传入真实运行时驱动（runtime）且该驱动在浏览器/WebGL 上下文中完成观测时，
    才允许给出 SUCCESS 与 M3 成熟度；否则一律返回 NEEDS_RUNTIME_TOOL，
    maturity 保持 None，绝不把静态解析包装成运行时验证。
"""
import json
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

ROOT = Path(__file__).resolve().parent.parent

M3_MATURITY = "M3_runtime_verified_3d_assets"
M2_MATURITY = "M2_procedural_asset_baseline"

_RUNTIME_DRIVER = Callable[[Path], Mapping[str, Any]]


class WebGLRuntimeProbe:
    """3D 资产探针：静态事实采集 + 可选真实运行时观测"""

    @classmethod
    def collect_static_facts(cls, asset_path: Path) -> Dict[str, Any]:
        """仅采集静态事实。不推断 WebGL 上下文、不推断渲染结果。"""
        p = Path(asset_path)
        facts: Dict[str, Any] = {
            "asset_name": p.name,
            "extension": p.suffix.lower(),
            "size_bytes": p.stat().st_size if p.exists() else 0,
            "exists": p.exists(),
        }
        if not p.exists():
            facts["errors"] = [f"资产文件不存在: {p}"]
            return facts

        content = p.read_bytes()
        ext = facts["extension"]

        if ext == ".html":
            text = content.decode("utf-8", errors="ignore")
            facts.update({
                "is_html_showcase": True,
                "declares_threejs": ("THREE." in text or "three.module.js" in text or "WebGLRenderer" in text),
                "declares_canvas": "<canvas" in text or "createElement('canvas')" in text,
                "declares_pbr_material": ("MeshStandardMaterial" in text or "MeshPhysicalMaterial" in text),
                "declares_lod": "LOD" in text,
            })
        elif ext == ".gltf":
            try:
                data = json.loads(content.decode("utf-8"))
                facts.update({
                    "is_gltf": True,
                    "mesh_count": len(data.get("meshes", [])),
                    "material_count": len(data.get("materials", [])),
                    "skin_count": len(data.get("skins", [])),
                    "node_count": len(data.get("nodes", [])),
                    "animation_count": len(data.get("animations", [])),
                })
            except Exception as exc:
                facts.update({"is_gltf": True, "parse_error": str(exc)})
        elif ext == ".glb":
            facts.update({
                "is_glb": True,
                "magic_valid": content[:4] == b"glTF",
                "declared_length": int.from_bytes(content[8:12], "little") if len(content) >= 12 else 0,
            })
        return facts

    @classmethod
    def probe_asset(
        cls,
        asset_path: Path,
        runtime: Optional[_RUNTIME_DRIVER] = None,
    ) -> Dict[str, Any]:
        """采集静态事实；有真实运行时驱动时才产出运行时结论。

        runtime: 可调用对象，接收 Path，返回映射，必须包含 status。
                 真实驱动来自 pipeline/browser_runtime_adapter.py 的 WebGL 观测能力。
        """
        static_facts = cls.collect_static_facts(Path(asset_path))
        result: Dict[str, Any] = {
            "asset": str(asset_path),
            "static_facts": static_facts,
            "runtime_facts": None,
            "status": "NEEDS_RUNTIME_TOOL",
            "maturity": None,
            "errors": list(static_facts.get("errors", [])),
        }

        if static_facts.get("errors"):
            result["status"] = "FAIL"
            return result

        if runtime is None:
            result["errors"].append(
                "未提供真实运行时驱动；静态解析通过不等于 WebGL 渲染通过"
            )
            return result

        try:
            observed = dict(runtime(Path(asset_path)))
        except Exception as exc:
            result["status"] = "RUNTIME_ERROR"
            result["errors"].append(f"运行时驱动执行失败: {exc}")
            return result

        result["runtime_facts"] = observed
        status = str(observed.get("status", "")).upper()
        agent = observed.get("agent") or {}
        has_render_stats = agent.get("triangles") is not None or agent.get("draw_calls") is not None

        if status in ("SUCCESS", "PASS") and observed.get("webgl_context") is True:
            if has_render_stats:
                result["status"] = "SUCCESS"
                result["maturity"] = M3_MATURITY
            else:
                # 上下文可用但没有任何渲染统计，无法确认资产真的被画出来
                result["status"] = "RUNTIME_FAILED"
                result["errors"].append("WebGL 上下文可用，但缺少渲染统计契约，无法确认资产已渲染")
        elif status == "NEEDS_RUNTIME_TOOL":
            result["status"] = "NEEDS_RUNTIME_TOOL"
        else:
            result["status"] = "RUNTIME_FAILED"
            result["errors"].append(str(observed.get("error") or "运行时观测未确认 WebGL 上下文"))
        return result

    @classmethod
    def create_probe_callable(cls, runtime: Optional[_RUNTIME_DRIVER] = None) -> _RUNTIME_DRIVER:
        """生成适配 pipeline/runtime_asset_smoke.py 签名的探针回调"""
        def _probe(path: Path) -> Mapping[str, Any]:
            return cls.probe_asset(path, runtime=runtime)
        return _probe


__all__ = ["WebGLRuntimeProbe", "M2_MATURITY", "M3_MATURITY"]
