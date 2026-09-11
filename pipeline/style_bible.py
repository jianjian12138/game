"""pipeline/style_bible.py — 风格圣经 StyleBible（L3 内容工厂一致性锚点）。

设计要点（来自升级计划 4.1）：
  - 立项阶段一次性生成并【锁定】，后续所有资产 prompt 必须引用 style_ref，
    这是风格一致性的唯一保证。
  - 锁死后禁止改色板/线条/光影，避免"中途换皮"导致资产风格漂移。
  - 纯数据 + 工具方法，不依赖 LLM、不依赖网络；可落工件库做不可变存档。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


def _hex_to_rgb(hexv: str) -> Tuple[int, int, int]:
    h = hexv.lstrip("#").strip()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"非法 hex 色值: {hexv}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % (rgb[0] & 0xff, rgb[1] & 0xff, rgb[2] & 0xff)


@dataclass
class StyleBible:
    name: str = "default"
    palette: List[str] = field(default_factory=list)        # 主色板 hex
    accent: List[str] = field(default_factory=list)          # 强调色 hex
    line: str = ""                                           # 线条语言
    lighting: str = ""                                       # 光影
    composition: str = ""                                    # 构图
    references: List[str] = field(default_factory=list)      # 参考图（外部路径/URL，可空）
    negative_prompts: List[str] = field(default_factory=list)
    created_at: str = ""
    locked: bool = False

    # ── 构造与锁定 ──────────────────────────────────────────────────────────
    @classmethod
    def build(cls, name: str = "default", palette: Optional[List[str]] = None,
              accent: Optional[List[str]] = None, seed: int = 0,
              line: str = "", lighting: str = "", composition: str = "",
              references: Optional[List[str]] = None,
              negative_prompts: Optional[List[str]] = None) -> "StyleBible":
        """构建一份风格圣经。缺省色板用确定性派生（不是随机），保证可复现。"""
        if palette is None:
            palette = cls._derive_palette(seed)
        if accent is None:
            accent = palette[-2:] or ["#ffd166"]
        return cls(
            name=name,
            palette=list(palette),
            accent=list(accent),
            line=line or "clean vector-like edges, confident uniform strokes",
            lighting=lighting or "soft top-down key light, gentle ambient fill",
            composition=composition or "centered, symmetrical, clear silhouette",
            references=list(references or []),
            negative_prompts=list(negative_prompts or [
                "watermark", "text", "letters", "words", "signature",
                "photograph", "blurry", "low quality", "cluttered"]),
            created_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            locked=False,
        )

    @staticmethod
    def _derive_palette(seed: int) -> List[str]:
        # 确定性派生 6 色，避免依赖随机源（可复现）。
        base = [
            (34, 40, 58), (58, 74, 110), (96, 130, 182),
            (223, 193, 122), (214, 222, 235), (18, 22, 32),
        ]
        out = []
        for i, (r, g, b) in enumerate(base):
            sh = (seed * 37 + i * 13) % 32 - 16
            out.append(_rgb_to_hex((max(0, min(255, r + sh)),
                                     max(0, min(255, g + sh)),
                                     max(0, min(255, b + sh)))))
        return out

    def lock(self) -> None:
        self.locked = True

    _LOCKED_FIELDS = ("name", "palette", "accent", "line", "lighting",
                     "composition", "references", "negative_prompts")

    def __setattr__(self, name: str, value: Any) -> None:
        # 锁死后禁止改风格字段（直接赋值也会拦，不止方法内）
        if getattr(self, "locked", False) and name in self._LOCKED_FIELDS:
            raise RuntimeError("StyleBible 已锁定，禁止修改（一致性保证）；"
                               "如需新风格请 build 新实例")
        super().__setattr__(name, value)

    def _guard(self) -> None:
        if self.locked:
            raise RuntimeError("StyleBible 已锁定，禁止修改（一致性保证）；"
                               "如需新风格请 build 新实例")

    # ── 查询工具 ────────────────────────────────────────────────────────────
    def palette_rgb(self) -> List[Tuple[int, int, int]]:
        return [_hex_to_rgb(c) for c in self.palette]

    def accent_rgb(self) -> List[Tuple[int, int, int]]:
        return [_hex_to_rgb(c) for c in self.accent]

    def all_colors_rgb(self) -> List[Tuple[int, int, int]]:
        seen = {}
        for c in self.palette + self.accent:
            rgb = _hex_to_rgb(c)
            seen[rgb] = True
        return list(seen.keys())

    def enrich_prompt(self, prompt: str) -> str:
        """把资产 prompt 锚定到本风格圣经（style_ref）。

        返回合并后的正向 prompt + 负向 prompt，供 ImageGenAdapter 使用。
        这是一致性的唯一保证：任何资产都必须经过本方法。
        """
        parts = [prompt.strip(), f"style: {self.name}"]
        if self.line:
            parts.append(f"linework: {self.line}")
        if self.lighting:
            parts.append(f"lighting: {self.lighting}")
        if self.composition:
            parts.append(f"composition: {self.composition}")
        if self.palette:
            parts.append("color palette: " + ", ".join(self.palette))
        positive = ", ".join(p for p in parts if p)
        negative = ", ".join(self.negative_prompts) if self.negative_prompts else ""
        return positive + (" | negative: " + negative if negative else "")

    # ── 序列化 ──────────────────────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StyleBible":
        sb = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
        sb.locked = bool(d.get("locked", False))
        return sb
