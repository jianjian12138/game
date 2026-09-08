"""
DSL Parser — YAML/JSON → AST 解析器
=====================================
支持从文件或字符串解析，可选方言预处理钩子。
"""

import core.yaml_compat as yaml
import json
from pathlib import Path
from typing import Any, Optional


class DSLParser:
    """将 YAML 或 JSON 文本解析为规范化的 AST 字典。"""

    def __init__(self, dialect=None):
        """
        Args:
            dialect: 方言对象，如果提供则调用 dialect.preprocess(raw_dict)
                     进行方言特定的预处理（展开语法糖、添加默认值等）。
        """
        self.dialect = dialect

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def parse_file(self, path: str) -> dict:
        """从文件路径解析。支持 .yaml/.yml/.json。"""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"DSL 文件不存在: {path}")
        text = p.read_text(encoding="utf-8")
        if p.suffix in (".yaml", ".yml"):
            return self._parse_yaml(text)
        elif p.suffix == ".json":
            return self._parse_json(text)
        else:
            raise ValueError(f"不支持的文件格式: {p.suffix}，请使用 .yaml 或 .json")

    def parse_text(self, text: str, fmt: str = "yaml") -> dict:
        """从字符串解析。fmt 可以是 'yaml' 或 'json'。"""
        if fmt == "yaml":
            return self._parse_yaml(text)
        elif fmt == "json":
            return self._parse_json(text)
        else:
            raise ValueError(f"不支持的格式: {fmt}")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _parse_yaml(self, text: str) -> dict:
        raw = yaml.safe_load(text)
        if not isinstance(raw, dict):
            raise TypeError(f"DSL 根节点必须是 dict，实际得到: {type(raw)}")
        return self._postprocess(raw)

    def _parse_json(self, text: str) -> dict:
        raw = json.loads(text)
        if not isinstance(raw, dict):
            raise TypeError(f"DSL 根节点必须是 dict，实际得到: {type(raw)}")
        return self._postprocess(raw)

    def _postprocess(self, raw: dict) -> dict:
        """规范化 + 方言预处理。"""
        # 规范化：确保必要字段存在
        raw.setdefault("version", "1.0")
        raw.setdefault("metadata", {})

        # 方言预处理（语法糖展开、默认值填充等）
        if self.dialect and hasattr(self.dialect, "preprocess"):
            raw = self.dialect.preprocess(raw)

        return raw
