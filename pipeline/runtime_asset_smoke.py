"""资产运行时冒烟门禁。

该模块不伪造浏览器结果：没有可用运行时工具时明确返回 NEEDS_RUNTIME_TOOL。
"""

import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Union

from pipeline.gltf_validator import validate_gltf
from pipeline.lod_budget_policy import validate_lod_budget
from pipeline.pbr_validator import validate_pbr
from pipeline.skeleton_validator import validate_skeleton


_RUNTIME_PROBE = Callable[[Path], Mapping[str, Any]]


def _entry(code: str, message: str, **details: Any) -> Dict[str, Any]:
    item = {"code": code, "message": message}
    if details:
        item["details"] = details
    return item


def _runtime_executable(runtime_command: Optional[Union[str, Sequence[str]]]) -> Optional[str]:
    """只在调用方显式给出运行时命令时解析可执行文件。

    绝不自动探测并拉起浏览器：那样既观测不到渲染结果、产生不了任何证据，
    又会在每次冒烟时留下一个必须靠超时杀掉的孤儿进程。没有显式运行时，
    就没有运行时结论（fail-closed）。
    """
    if isinstance(runtime_command, (list, tuple)):
        return runtime_command[0] if runtime_command else None
    if isinstance(runtime_command, str):
        try:
            return shlex.split(runtime_command)[0]
        except ValueError:
            return None
    return None


def run_runtime_asset_smoke(
    asset_path: Union[str, Path],
    runtime_command: Optional[Union[str, Sequence[str]]] = None,
    runtime_probe: Optional[_RUNTIME_PROBE] = None,
    timeout: float = 8.0,
) -> Dict[str, Any]:
    """执行静态门禁并尝试运行时探测。

    ``runtime_probe`` 是外部浏览器/引擎适配器；没有它时，浏览器进程启动本身也不会被当作渲染成功。
    """
    path = Path(asset_path)
    report: Dict[str, Any] = {
        "status": "FAIL",
        "valid": False,
        "asset": str(path),
        "checks": {},
        "errors": [],
        "warnings": [],
        "runtime": {"status": "NOT_STARTED", "tool": None},
    }
    if not path.is_file():
        report["errors"].append(_entry("ASSET_MISSING", "资产文件不存在"))
        return report

    gltf = validate_gltf(path)
    pbr = validate_pbr(path, validate_structure=False)
    skeleton = validate_skeleton(path, validate_structure=False)
    lod = validate_lod_budget(path)
    report["checks"] = {"gltf": gltf, "pbr": pbr, "skeleton": skeleton, "lod": lod}
    report["maturity"] = {
        "static": "M2_procedural_asset_baseline" if not report["errors"] else "M1_static_validation_failed",
        "runtime": "PENDING",
        "production_eligible": False,
    }
    report["errors"].extend(gltf["errors"])
    report["errors"].extend(pbr["errors"])
    if path.name.lower().find("rig") >= 0 or skeleton["checks"].get("skins") or "skins" in gltf:
        report["errors"].extend(skeleton["errors"])
    report["warnings"].extend(lod["warnings"])
    if lod["errors"]:
        report["errors"].extend(lod["errors"])

    if report["errors"]:
        report["runtime"] = {"status": "BLOCKED_BY_STATIC_VALIDATION", "tool": None}
        report["summary"] = {"error_count": len(report["errors"]), "warning_count": len(report["warnings"])}
        return report

    executable = _runtime_executable(runtime_command)
    report["runtime"]["tool"] = executable
    if runtime_probe is not None:
        try:
            probe_result = dict(runtime_probe(path))
        except Exception as exc:
            report["runtime"] = {"status": "RUNTIME_ERROR", "tool": executable, "error": str(exc)}
            report["errors"].append(_entry("RUNTIME_ERROR", "运行时探测器执行失败"))
        else:
            probe_status = str(probe_result.get("status", "")).upper()
            report["runtime"] = {"tool": executable, "probe": probe_result}
            if probe_status in ("SUCCESS", "PASS"):
                report["runtime"]["status"] = "SUCCESS"
            elif probe_status == "NEEDS_RUNTIME_TOOL":
                # 「无法验证」必须区别于「验证不通过」，不能降级成 FAIL 也不能升级成 SUCCESS
                report["runtime"]["status"] = "NEEDS_RUNTIME_TOOL"
            else:
                report["runtime"]["status"] = "RUNTIME_FAILED"
                report["errors"].append(_entry("RUNTIME_FAILED", "运行时探测器未确认资产可加载"))
    elif executable is None:
        report["runtime"] = {
            "status": "NEEDS_RUNTIME_TOOL",
            "tool": None,
            "reason": "未检测到浏览器或引擎运行时；静态门禁通过不等于运行时通过",
        }
    else:
        try:
            if isinstance(runtime_command, (list, tuple)):
                command = list(runtime_command)
            elif isinstance(runtime_command, str):
                command = shlex.split(runtime_command)
            else:
                command = [executable]
            with tempfile.TemporaryDirectory(prefix="asset_runtime_smoke_") as temp_dir:
                probe_file = Path(temp_dir) / "asset_probe.html"
                probe_file.write_text(
                    "<!doctype html><meta charset='utf-8'><title>Asset runtime probe</title>"
                    "<p>需要外部运行时适配器确认 glTF 加载与渲染。</p>",
                    encoding="utf-8",
                )
                process = subprocess.Popen(command + [str(probe_file)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                report["runtime"] = {
                    "status": "NEEDS_RUNTIME_TOOL",
                    "tool": executable,
                    "reason": "浏览器已启动，但标准库无法观测 WebGL/glTF 渲染结果；需要运行时适配器",
                }
        except (OSError, ValueError) as exc:
            report["runtime"] = {"status": "NEEDS_RUNTIME_TOOL", "tool": executable, "reason": "无法启动运行时: %s" % exc}

    if report["runtime"]["status"] == "NEEDS_RUNTIME_TOOL":
        report["status"] = "NEEDS_RUNTIME_TOOL"
        report["valid"] = False
        report["maturity"]["runtime"] = "NEEDS_RUNTIME_TOOL"
    else:
        report["valid"] = not report["errors"] and report["runtime"]["status"] == "SUCCESS"
        report["status"] = "SUCCESS" if report["valid"] else "FAIL"
        report["maturity"]["runtime"] = "M3_runtime_verified_3d_assets" if report["valid"] else "M2_procedural_asset_baseline"
        report["maturity"]["production_eligible"] = False
    report["summary"] = {"error_count": len(report["errors"]), "warning_count": len(report["warnings"])}
    return report


class RuntimeAssetSmoke:
    @staticmethod
    def run(asset_path: Union[str, Path], **kwargs: Any) -> Dict[str, Any]:
        return run_runtime_asset_smoke(asset_path, **kwargs)


runtime_asset_smoke = run_runtime_asset_smoke

__all__ = ["RuntimeAssetSmoke", "run_runtime_asset_smoke", "runtime_asset_smoke"]
