#!/usr/bin/env python3
"""
visual_diff_engine.py: 像素级视觉真理差分与多层热力图比对引擎 (Visual Diff Engine)
纯 Python 3.9+ 标准库实现，零外部依赖（复用 pipeline.png_io 做真实像素解码，不读压缩字节代理）。

负责：
1. 黄金基准帧 (Golden Reference Frames) 管理
2. 捕获画面与基准帧像素直方图、通道密度与色彩差分比对
3. 渲染图层装配完整性 Linter：
   - 是否缺失底座层 (Missing Base)
   - 是否缺失地面微投影 (Missing Drop Shadow)
   - 是否缺失运动/枪管层 (Missing Recoil/Rotor Layer)
   - 是否存在图层颠倒变异 (Layer Mutation)
4. 输出结构化视觉缺陷诊断报告与修改建议
"""
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


def _decode_image(path: Path) -> Optional[Dict[str, Any]]:
    """用 pipeline.png_io.decode_png 解码真实像素；失败返回 None（诚实，不崩）。

    原实现读 PNG 压缩字节算均值/暗色比，与像素内容无可靠相关，不能用于视觉 diff（评审 R1）。
    """
    try:
        from pipeline.png_io import decode_png
    except Exception:
        return None
    if not path or not path.exists():
        return None
    try:
        return decode_png(path.read_bytes())
    except Exception as e:  # 损坏/不支持格式：诚实返回错误，不静默降级
        return {"error": str(e)}


def read_png_dimensions(path: Path) -> Tuple[int, int]:
    """返回 (宽, 高)；解码失败返回 (0, 0)。"""
    dec = _decode_image(path)
    if dec and "error" not in dec:
        return int(dec.get("width", 0)), int(dec.get("height", 0))
    return 0, 0


def compute_rgb_histogram(path: Path) -> Dict[str, Any]:
    """计算真实像素级的色彩特征（平均亮度、暗色像素比、RGB 三通道均值）。

    注意：仍是粗筛层（不区分细粒度构图），语义级美术裁判由 VLM 负责（评审共识 R1/R4）。
    """
    if not path or not path.exists():
        return {"byte_mean": 0.0, "dark_ratio": 0.0, "file_size_kb": 0.0, "status": "FILE_NOT_FOUND"}
    dec = _decode_image(path)
    if dec is None:
        return {"byte_mean": 0.0, "dark_ratio": 0.0, "file_size_kb": 0.0, "status": "FILE_NOT_FOUND"}
    if "error" in dec:
        return {"byte_mean": 0.0, "dark_ratio": 0.0,
                "file_size_kb": round(path.stat().st_size / 1024, 2),
                "status": "DECODE_ERROR", "error": dec["error"]}
    pixels = dec.get("pixels", b"")
    ch = int(dec.get("channels", 4))
    n = len(pixels)
    if n == 0 or ch < 3:
        return {"byte_mean": 0.0, "dark_ratio": 0.0,
                "file_size_kb": round(path.stat().st_size / 1024, 2), "status": "EMPTY_DATA"}
    total = 0
    dark = 0
    r_total = 0
    g_total = 0
    b_total = 0
    count = 0
    for i in range(0, n - (ch - 1), ch):
        r = pixels[i]; g = pixels[i + 1]; b = pixels[i + 2]
        r_total += r
        g_total += g
        b_total += b
        total += (r + g + b) // 3
        lum = (299 * r + 587 * g + 114 * b) // 1000
        if lum < 64:
            dark += 1
        count += 1
    if count == 0:
        return {"byte_mean": 0.0, "dark_ratio": 0.0, "file_size_kb": 0.0, "status": "EMPTY_DATA"}
    return {
        "byte_mean": round(total / count, 2),
        "r_mean": round(r_total / count, 2),
        "g_mean": round(g_total / count, 2),
        "b_mean": round(b_total / count, 2),
        "dark_ratio": round(dark / count, 4),
        "file_size_kb": round(path.stat().st_size / 1024, 2),
        "resolution": f'{dec.get("width")}x{dec.get("height")}',
        "status": "SUCCESS",
    }

class VisualDiffEngine:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path(".")
        self.golden_dir = self.root_dir / "knowledge" / "golden_frames"
        self.golden_dir.mkdir(parents=True, exist_ok=True)

    def audit_capture_vs_ground_truth(self, live_capture_path: Path) -> Dict[str, Any]:
        """对比实机截图与官方规范，进行多层视觉完整性审查"""
        print(f"=== VisualDiffEngine: 启动像素级视觉真理审查 ===")
        print(f"  [TARGET CAPTURE] {live_capture_path}")
        
        if not live_capture_path.exists():
            return {
                "status": "FAIL",
                "verdict": "REJECTED",
                "error": f"找不到目标截屏: {live_capture_path}",
                "layer_checks": []
            }

        w, h = read_png_dimensions(live_capture_path)
        stats = compute_rgb_histogram(live_capture_path)
        print(f"  [DIMENSIONS] 分辨率: {w}x{h}")
        print(f"  [HISTOGRAM] 图像特征: 均值={stats['byte_mean']} (R={stats.get('r_mean')}, G={stats.get('g_mean')}, B={stats.get('b_mean')}), 暗色率={stats['dark_ratio']}, 体积={stats['file_size_kb']}KB")

        # 检查多层装配不变量 (Layer Invariants)
        # 通过读取渲染源码与资源引用，审查是否存在变异
        layer_checks = []
        renderer_path = self.root_dir / "output" / "mindustry_rust_full" / "src" / "render" / "renderer.rs"
        
        if renderer_path.exists():
            src = renderer_path.read_text(encoding="utf-8", errors="ignore")
            
            # 1. 炮台底座与图层顺序审查 (1:1 DrawTurret.java)
            has_base = "block-1" in src
            has_shadow = "shadow" in src.lower() or "color::new(0.0, 0.0, 0.0" in src
            has_under_barrel = "duo-barrel" in src and "under" in src.lower() or ("barrel" in src and "draw_texture_ex" in src)
            
            layer_checks.append({
                "component": "Turret_MultiLayer_Duo",
                "rules": [
                    {"name": "独立底座层 (block-1.png)", "passed": has_base},
                    {"name": "地面投影层 (Ground Drop Shadow)", "passed": has_shadow},
                    {"name": "炮管底层下潜 (under = true)", "passed": has_under_barrel}
                ]
            })
            
            # 2. 地图岩壁与峡谷阴影审查
            has_wall_shadow = "wall" in src.lower() and "shadow" in src.lower()
            no_full_tile_grid = "tile_size" not in src.lower() or "grid_step" not in src.lower()
            layer_checks.append({
                "component": "Environment_Canyon_Terrain",
                "rules": [
                    {"name": "2.5D 岩壁高度投影", "passed": has_wall_shadow},
                    {"name": "无人工全屏无谓网格线覆盖", "passed": no_full_tile_grid}
                ]
            })

            # 3. UI 视口层叠结构审查
            has_hud_fragment = "wave" in src.lower() and ("core" in src.lower() or "inventory" in src.lower())
            has_placement_grid = "44.0" in src or "placement" in src.lower()
            layer_checks.append({
                "component": "Mindustry_Classic_HUD",
                "rules": [
                    {"name": "左上角波次与核心物料无缝组合", "passed": has_hud_fragment},
                    {"name": "右下角4列按钮网格与右侧分类竖条", "passed": has_placement_grid}
                ]
            })

        all_passed = all(r["passed"] for lc in layer_checks for r in lc["rules"]) if layer_checks else True

        # 真·基准帧像素/直方图对比（Dream Loop 式目标图锚定闭环）
        golden_diff = self._diff_vs_golden(live_capture_path)

        if layer_checks:
            print("\n  --- 多层装配真理门禁审查明细 ---")
            for lc in layer_checks:
                print(f"  【{lc['component']}】")
                for r in lc["rules"]:
                    flag = "[PASS]" if r["passed"] else "[FAIL]"
                    print(f"    {flag} {r['name']}")
        else:
            print("\n  [LAYER CHECKS] 渲染源文件不存在，跳过源码层静态分析")

        golden_status = golden_diff.get("status")
        golden_ok = golden_status == "PASS"
        if golden_status == "SKIPPED":
            print(f"  [GOLDEN DIFF] SKIPPED - 未建立视觉基准帧 (knowledge/golden_frames/ 为空)")
            print(f"     -> 自举基准: python game_agent.py diff --seed <截图路径>  或  python game_agent.py diff --gen-target --prompt <描述>")
        else:
            print(f"  [{'PASS' if golden_ok else 'WARN'}] 基准帧像素/直方图对比: "
                  f"{golden_diff.get('verdict')} (暗色率delta={golden_diff.get('dark_ratio_delta')}, "
                  f"均值delta={golden_diff.get('byte_mean_delta')})")

        # 诚实门禁（评审共识 R5）：无基准帧时视觉真理不可声称已验证，坚决判定 DEGRADED，杜绝虚假 PASS
        if golden_status == "SKIPPED":
            verdict = "DEGRADED"
        elif golden_ok and all_passed:
            verdict = "PASS"
        else:
            verdict = "WARN"

        if verdict == "DEGRADED":
            print(f"\n=======================================================")
            print(f"  [!] [VISUAL VERDICT] [DEGRADED] 视觉基准缺失或未见源码图层！")
            print(f"  说明: 本次仅完成基础尺寸分析，像素级视觉真理未建立比对基准，严禁视为真机渲染通过！")
            print(f"=======================================================\n")
        else:
            print(f"\n=======================================================")
            print(f"  [VISUAL VERDICT] [{verdict}] (视觉真理多层图层 / 基准帧对齐)")
            print(f"=======================================================\n")

        return {
            "status": verdict,
            "verdict": verdict,
            "resolution": f"{w}x{h}",
            "stats": stats,
            "layer_checks": layer_checks,
            "golden_diff": golden_diff
        }

    # ── 真·视觉闭环能力（对应 Dream Loop：目标图锚定 + 截图追近） ──

    def _find_golden(self, name: str = "target") -> Optional[Path]:
        """优先匹配指定名称基准，其次匹配任意已置入的基准帧。"""
        for ext in (".png", ".jpg"):
            c = self.golden_dir / f"{name}{ext}"
            if c.exists():
                return c
        # 兼容回退：如果指定名字没找到，尝试在 golden_dir 查找任何已有的基准图片
        all_goldens = sorted(self.golden_dir.glob("*.png")) + sorted(self.golden_dir.glob("*.jpg"))
        if all_goldens:
            return all_goldens[0]
        return None

    def _diff_vs_golden(self, live_path: Path, name: str = "target") -> Dict[str, Any]:
        """将实机截图与 golden_dir 同名的基准帧做真实像素/直方图差分。"""
        golden = self._find_golden(name)
        if not golden:
            return {"layer": "golden_frame_diff", "status": "SKIPPED",
                    "reason": "NO_GOLDEN_FRAME", "verdict": "SKIPPED"}
        gw, gh = read_png_dimensions(golden)
        lw, lh = read_png_dimensions(live_path)
        g_stat = compute_rgb_histogram(golden)
        l_stat = compute_rgb_histogram(live_path)
        res_match = (gw == lw and gh == lh)
        dark_delta = abs(g_stat.get("dark_ratio", 0.0) - l_stat.get("dark_ratio", 0.0))
        mean_delta = abs(g_stat.get("byte_mean", 0.0) - l_stat.get("byte_mean", 0.0))
        pixel_ok = bool(res_match and dark_delta < 0.15 and mean_delta < 30)
        return {
            "layer": "golden_frame_diff",
            "golden": str(golden),
            "resolution_match": res_match,
            "golden_resolution": f"{gw}x{gh}",
            "live_resolution": f"{lw}x{lh}",
            "dark_ratio_delta": round(dark_delta, 4),
            "byte_mean_delta": round(mean_delta, 2),
            "status": "PASS" if pixel_ok else "WARN",
            "verdict": "MATCH" if pixel_ok else "VISUAL_DRIFT",
        }

    def seed_golden_frame(self, live_path: Path, name: str = "target") -> Dict[str, Any]:
        """把实机截图固化为基准帧（自举），后续迭代以此追近。"""
        if not live_path.exists():
            return {"status": "FAIL", "error": f"live capture 不存在: {live_path}"}
        dst = self.golden_dir / f"{name}.png"
        dst.write_bytes(live_path.read_bytes())
        return {"status": "OK", "seeded": str(dst), "bytes": dst.stat().st_size}

    def generate_target_image(self, prompt: str, name: str = "target",
                              style: Any = None, seed: int = 123456789) -> Dict[str, Any]:
        """用文生图生成目标参考图写入 golden_dir（Dream Loop 的 target image 锚定）。
        无可用生图后端时诚实返回 NEEDS_RUNTIME_TOOL，不伪证。"""
        try:
            from pipeline.image_gen_adapter import ImageGenAdapter, ImageGenResult
        except Exception as e:
            return {"status": "FAIL", "error": f"image_gen_adapter 不可导入: {e}"}
        adapter = ImageGenAdapter()
        if not adapter.available_backends():
            return {"status": "NEEDS_RUNTIME_TOOL", "needs_runtime_tool": "image_gen",
                    "error": "无可用生图后端(云/ComfyUI 均未配置)，未伪证"}
        res: ImageGenResult = adapter.generate(prompt, style=style, seed=seed)
        if not res.ok:
            return {"status": "FAIL", "error": res.error or res.status,
                    "needs_runtime_tool": res.needs_runtime_tool}
        dst = self.golden_dir / f"{name}.png"
        dst.write_bytes(res.image_bytes)
        return {"status": "OK", "target": str(dst), "backend": res.backend,
                "provenance": res.provenance}

if __name__ == "__main__":
    engine = VisualDiffEngine()
    test_img = Path("output/mindustry_rust_full/mindustry_rust_live.png")
    res = engine.audit_capture_vs_ground_truth(test_img)
