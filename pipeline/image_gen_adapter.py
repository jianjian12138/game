"""pipeline/image_gen_adapter.py — ImageGenAdapter：可插拔图像生成后端（L3）。

后端优先级（来自升级计划 4.1 / 第十一章）：
  ① cloud_api       —— 云生图 API（魔搭 Z-Image-Turbo / 硅基流动 FLUX），
                        需配置 endpoint+key；未配置即不可用（诚实）。
  ② comfyui_local   —— 本地 ComfyUI（SDXL 已实测可用），POST /prompt 真出图。
  ③ procedural_placeholder —— 纯 Python 真生成 PNG，确定性、可复现；
                        仅在 AIGC 后端都不可用时兜底，并【明确标注程序化占位】。

防伪底线（与 B/C 类一致）：
  - 没真出到图绝不报 is_ai_generated=True；程序化兜底 is_ai_generated=False、
    is_procedural_placeholder=True，且 needs_runtime_tool="aigc_backend" 如实标注。
  - 真出图则把模型/端点/seed/prompt/负向词/取回路径写进 provenance，可回查。
  - 不依赖 requests/PIL：HTTP 用 stdlib urllib，图像用本库 png_io。
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pipeline import png_io
from pipeline.style_bible import StyleBible

# 本机 ComfyUI 默认端口 8188；换端口/换机时用环境变量 COMFYUI_URL 覆盖，
# 不写死地址，避免部署到别的机器后无法指向真实服务。
COMFYUI_URL = (os.environ.get("COMFYUI_URL") or "").strip() or "http://127.0.0.1:8188"
CLOUD_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "image_gen.json"


@dataclass
class ImageGenResult:
    backend: str
    is_ai_generated: bool
    is_procedural_placeholder: bool
    status: str                       # OK / PROCEDURAL_PLACEHOLDER / NEEDS_RUNTIME_TOOL / ERROR
    image_bytes: bytes = b""
    width: int = 0
    height: int = 0
    has_alpha: bool = False
    content_hash: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    needs_runtime_tool: Optional[str] = None
    latency_ms: float = 0.0
    error: str = ""

    def ok(self) -> bool:
        return bool(self.image_bytes) and self.status in ("OK", "PROCEDURAL_PLACEHOLDER")


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _http_json(url: str, data: Optional[bytes] = None, timeout: float = 30.0) -> Any:
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _http_get_bytes(url: str, timeout: float = 30.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


class ImageGenAdapter:
    def __init__(self, comfyui_url: str = COMFYUI_URL,
                 cloud_config_path: Optional[str] = None):
        self.comfyui_url = comfyui_url.rstrip("/")
        self.cloud_config_path = Path(cloud_config_path) if cloud_config_path \
            else CLOUD_CONFIG_PATH

    # ── 后端可用性探测（诚实，不假设） ──────────────────────────────────────
    def comfyui_available(self) -> bool:
        try:
            _http_json(f"{self.comfyui_url}/system_stats", timeout=4.0)
            return True
        except Exception:
            return False

    def cloud_available(self) -> bool:
        cfg = self._load_cloud_config()
        if not cfg:
            return False
        return bool(cfg.get("endpoint")) and bool(cfg.get("api_key"))

    def available_backends(self) -> List[str]:
        out = []
        if self.cloud_available():
            out.append("cloud_api")
        if self.comfyui_available():
            out.append("comfyui_local")
        return out  # 注意：procedural 永远可用，不在此列（它是兜底）

    def _load_cloud_config(self) -> Dict[str, Any]:
        if not self.cloud_config_path.exists():
            return {}
        try:
            return json.loads(self.cloud_config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    # ── 主入口 ────────────────────────────────────────────────────────────
    def generate(self, prompt: str, style: Optional[StyleBible] = None,
                 seed: Optional[int] = None, width: int = 512, height: int = 512,
                 backend: Optional[str] = None,
                 negative_prompt: Optional[str] = None,
                 transparent: bool = False) -> ImageGenResult:
        """生成一张图。backend=None 时按优先级自动选可用后端，全不可用则程序化兜底。"""
        seed = int(seed) if seed is not None else 123456789
        width = max(8, (width // 8) * 8)
        height = max(8, (height // 8) * 8)
        pos = style.enrich_prompt(prompt) if style else prompt
        neg = negative_prompt or (", ".join(style.negative_prompts) if style else "")

        if backend == "procedural_placeholder":
            return self.generate_procedural(prompt, style, seed, width, height, transparent)
        if backend == "comfyui_local":
            if not self.comfyui_available():
                return ImageGenResult("comfyui_local", False, False,
                                      "NEEDS_RUNTIME_TOOL",
                                      error="ComfyUI 不可达，未伪证",
                                      needs_runtime_tool="comfyui_local")
            return self.generate_comfyui(pos, neg, seed, width, height)
        if backend == "cloud_api":
            if not self.cloud_available():
                return ImageGenResult("cloud_api", False, False,
                                      "NEEDS_RUNTIME_TOOL",
                                      error="云生图 API 未配置 endpoint/key，未伪证",
                                      needs_runtime_tool="cloud_api")
            return self.generate_cloud(pos, neg, seed, width, height)
        if backend is not None:
            return ImageGenResult(backend, False, False, "ERROR",
                                  error=f"未知后端: {backend}")

        # 自动模式：真实 AIGC 优先，全不可用才程序化兜底
        if self.cloud_available():
            return self.generate_cloud(pos, neg, seed, width, height)
        if self.comfyui_available():
            return self.generate_comfyui(pos, neg, seed, width, height)
        return self.generate_procedural(prompt, style, seed, width, height, transparent)

    # ── ① 云端 API（实现即真调，未配置即不可用） ───────────────────────────
    def generate_cloud(self, prompt: str, negative_prompt: str, seed: int,
                        width: int, height: int) -> ImageGenResult:
        cfg = self._load_cloud_config()
        endpoint = cfg.get("endpoint")
        api_key = cfg.get("api_key")
        if not endpoint or not api_key:
            return ImageGenResult("cloud_api", False, False, "NEEDS_RUNTIME_TOOL",
                                  error="云生图 API 未配置 endpoint/key",
                                  needs_runtime_tool="cloud_api")
        payload = {
            "model": cfg.get("model", "Z-Image-Turbo"),
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "seed": seed,
            "width": width, "height": height,
            "n": 1,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=cfg.get("timeout", 60.0)) as r:
                resp = json.loads(r.read().decode("utf-8"))
            img_b64 = resp.get("data", [{}])[0].get("b64_json") or resp.get("image")
            if not img_b64:
                return ImageGenResult("cloud_api", False, False, "ERROR",
                                      error="云 API 未返回图像字段")
            import base64
            img = base64.b64decode(img_b64)
            return self._wrap_ai("cloud_api", img, prompt, negative_prompt, seed,
                                 width, height, time.time() - t0,
                                 endpoint=cfg.get("model", endpoint))
        except Exception as e:
            return ImageGenResult("cloud_api", False, False, "ERROR",
                                  error=f"云 API 调用失败: {e}")

    # ── ② 本地 ComfyUI（真出图） ──────────────────────────────────────────
    TXT2IMG_WORKFLOW = {
        "3": {"class_type": "KSampler", "inputs": {
            "seed": 0, "steps": 20, "cfg": 7.0, "sampler_name": "euler",
            "scheduler": "normal", "denoise": 1.0,
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0]}},
        "4": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"filename_prefix": "gameagent", "images": ["8", 0]}},
    }

    def generate_comfyui(self, prompt: str, negative_prompt: str, seed: int,
                         width: int, height: int) -> ImageGenResult:
        wf = json.loads(json.dumps(self.TXT2IMG_WORKFLOW))
        wf["3"]["inputs"]["seed"] = seed
        wf["5"]["inputs"]["width"] = width
        wf["5"]["inputs"]["height"] = height
        wf["6"]["inputs"]["text"] = prompt
        wf["7"]["inputs"]["text"] = negative_prompt
        t0 = time.time()
        try:
            import uuid
            resp = _http_json(f"{self.comfyui_url}/prompt",
                              json.dumps({"prompt": wf,
                                          "client_id": str(uuid.uuid4())}).encode("utf-8"),
                              timeout=30.0)
            prompt_id = resp.get("prompt_id")
            if not prompt_id:
                return ImageGenResult("comfyui_local", False, False, "ERROR",
                                      error="ComfyUI 未返回 prompt_id")
            # 轮询历史
            img = None
            for _ in range(60):  # 最多 ~120s
                try:
                    hist = _http_json(f"{self.comfyui_url}/history/{prompt_id}",
                                      timeout=10.0)
                except Exception:
                    hist = None
                if hist and prompt_id in hist:
                    outputs = hist[prompt_id].get("outputs", {})
                    node = outputs.get("9") or next(iter(outputs.values()), {})
                    imgs = node.get("images") or []
                    if imgs:
                        im = imgs[0]
                        url = (f"{self.comfyui_url}/view?filename="
                               f"{urllib.parse.quote(im['filename'])}"
                               f"&subfolder={urllib.parse.quote(im.get('subfolder',''))}"
                               f"&type={urllib.parse.quote(im.get('type',''))}")
                        img = _http_get_bytes(url, timeout=30.0)
                        break
                time.sleep(2.0)
            if not img:
                return ImageGenResult("comfyui_local", False, False, "ERROR",
                                      error="ComfyUI 超时未取到图（诚实：未伪证）",
                                      needs_runtime_tool="comfyui_local")
            return self._wrap_ai("comfyui_local", img, prompt, negative_prompt, seed,
                                 width, height, time.time() - t0,
                                 endpoint=self.comfyui_url,
                                 model="sd_xl_base_1.0.safetensors")
        except Exception as e:
            return ImageGenResult("comfyui_local", False, False, "ERROR",
                                  error=f"ComfyUI 调用失败: {e}")

    def _wrap_ai(self, backend: str, img: bytes, prompt: str, neg: str, seed: int,
                 w: int, h: int, lat: float, **prov_extra) -> ImageGenResult:
        try:
            d = png_io.decode_png(img)
            aw, ah, ch = d["width"], d["height"], d["channels"]
        except Exception as e:
            return ImageGenResult(backend, False, False, "ERROR",
                                  error=f"生成图解码失败: {e}")
        prov = {"generator": backend, "is_ai_generated": True,
                "prompt": prompt, "negative_prompt": neg, "seed": seed,
                "retrieved_from": "comfyui_local" if backend == "comfyui_local"
                else "cloud_api",
                **prov_extra}
        # 从 tEXt 块尝试提取已嵌入的工作流（ComfyUI 会回写 prompt 元信息）
        return ImageGenResult(
            backend=backend, is_ai_generated=True, is_procedural_placeholder=False,
            status="OK", image_bytes=img, width=aw, height=ah,
            has_alpha=(ch == 4), content_hash=_sha(img),
            provenance=prov, latency_ms=round(lat * 1000, 1))

    # ── ③ 程序化占位（真生成 PNG，诚实标注） ───────────────────────────────
    def generate_procedural(self, prompt: str, style: Optional[StyleBible],
                            seed: int, width: int, height: int,
                            transparent: bool = False) -> ImageGenResult:
        t0 = time.time()
        rgba = self._draw_placeholder(width, height, style, seed, transparent)
        if transparent:
            img = png_io.encode_png(width, height, rgba, channels=4)
            has_alpha = True
        else:
            # 非透明模式输出 RGB（不伪造透明通道），QA 才能如实判定
            rgb = b"".join(rgba[i * 4:i * 4 + 3] for i in range(width * height))
            img = png_io.encode_png(width, height, rgb, channels=3)
            has_alpha = False
        colors = style.all_colors_rgb() if style else [
            (34, 40, 58), (223, 193, 122), (214, 222, 235)]
        prov = {"generator": "procedural_placeholder", "is_ai_generated": False,
                "style_ref": style.name if style else "none", "seed": seed,
                "prompt": prompt,
                "note": "程序化占位，非 AI 生成；接入真实 AIGC 后端后将替换",
                "palette_used": [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in colors]}
        warns = []
        if not self.available_backends():
            warns.append("无可用 AIGC 后端（cloud/comfyui），已回退程序化占位；"
                         "此资产非 AI 生成，不得宣称为 AI 美术")
        return ImageGenResult(
            backend="procedural_placeholder", is_ai_generated=False,
            is_procedural_placeholder=True, status="PROCEDURAL_PLACEHOLDER",
            image_bytes=img, width=width, height=height, has_alpha=has_alpha,
            content_hash=_sha(img), provenance=prov, warnings=warns,
            needs_runtime_tool="aigc_backend" if not self.available_backends() else None,
            latency_ms=round((time.time() - t0) * 1000, 1))

    @staticmethod
    def _draw_placeholder(w: int, h: int, style: Optional[StyleBible], seed: int,
                          transparent: bool) -> bytes:
        """确定性绘制一个'占位图标'：暗底 + 强调色边框 + 中心徽记。
        透明模式：边框外区域 alpha=0（演示真实透明通道）。不依赖随机源。"""
        colors = style.all_colors_rgb() if style else [
            (34, 40, 58), (223, 193, 122), (214, 222, 235), (96, 130, 182)]
        bg = colors[0]
        frame = colors[1 % len(colors)]
        inner = colors[2 % len(colors)]
        mark = colors[3 % len(colors)]
        # 用 seed 决定中心徽记形状（菱形/方块/圆环），确定性
        shape = seed % 3
        cx, cy = w // 2, h // 2
        fw = max(2, w // 24)  # 边框宽
        out = bytearray(w * h * 4)

        def set_px(x, y, rgb, a=255):
            if 0 <= x < w and 0 <= y < h:
                i = (y * w + x) * 4
                out[i:i + 4] = bytes((rgb[0], rgb[1], rgb[2], a))

        for y in range(h):
            for x in range(w):
                # 边框带
                edge = (x < fw or y < fw or x >= w - fw or y >= h - fw)
                if edge:
                    set_px(x, y, frame)
                    continue
                if transparent:
                    set_px(x, y, bg, 0)  # 透明留白
                    continue
                set_px(x, y, bg)
        # 中心徽记
        r = min(w, h) // 5
        for y in range(cy - r, cy + r):
            for x in range(cx - r, cx + r):
                dx, dy = x - cx, y - cy
                inside = False
                if shape == 0:      # 菱形
                    inside = (abs(dx) + abs(dy)) <= r
                elif shape == 1:    # 方块
                    inside = (abs(dx) <= r and abs(dy) <= r)
                else:               # 圆环
                    d2 = dx * dx + dy * dy
                    inside = (r * r * 0.45) <= d2 <= (r * r)
                if inside:
                    set_px(x, y, mark)
                elif (abs(dx) + abs(dy)) <= r + fw:  # 内面板底
                    set_px(x, y, inner)
        return bytes(out)
