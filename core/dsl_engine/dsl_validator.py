"""
DSL Validator — 静态类型检查与引用完整性验证
============================================
在执行前捕获 DSL 定义中的错误，提供清晰的错误信息。
"""

from __future__ import annotations
from typing import Any, Optional


class DSLValidator:
    """
    验证 DSL AST 的结构正确性。

    通用验证规则（所有方言共享）:
        - 根节点必须包含 "id" 字段
        - "effect" 必须是列表
        - 每个 effect 必须有 "type" 字段

    方言专属规则通过 dialect.get_schema() 提供。
    """

    REQUIRED_ROOT_FIELDS = ["id"]
    VALID_EFFECT_TARGETS = {
        "self", "enemy_single", "enemy_all", "enemy_adjacent",
        "ally_single", "ally_all", "random_enemy", "random_ally",
    }

    def __init__(self, dialect=None):
        self.dialect = dialect

    def validate(self, ast: dict) -> list[str]:
        """
        验证 AST，返回错误信息列表。列表为空则通过。

        Args:
            ast: 解析后的 AST dict

        Returns:
            错误信息列表（字符串），空列表表示验证通过
        """
        errors = []
        errors.extend(self._check_root_fields(ast))
        errors.extend(self._check_effects(ast))

        # 方言专属验证
        if self.dialect and hasattr(self.dialect, "validate"):
            errors.extend(self.dialect.validate(ast))

        return errors

    # ------------------------------------------------------------------
    # 内部验证方法
    # ------------------------------------------------------------------

    def _check_root_fields(self, ast: dict) -> list[str]:
        errors = []
        for field in self.REQUIRED_ROOT_FIELDS:
            if field not in ast:
                errors.append(f"缺少必要字段: '{field}'")
        if "id" in ast:
            if not isinstance(ast["id"], str) or not ast["id"].strip():
                errors.append("'id' 字段必须是非空字符串")
        return errors

    def _check_effects(self, ast: dict) -> list[str]:
        errors = []
        effects = ast.get("effect", [])
        if effects is None:
            return []  # 无效果卡牌合法（如纯费用牌）

        if not isinstance(effects, list):
            errors.append("'effect' 字段必须是列表")
            return errors

        for i, effect in enumerate(effects):
            prefix = f"effect[{i}]"
            if not isinstance(effect, dict):
                errors.append(f"{prefix}: 必须是 dict，实际类型: {type(effect)}")
                continue
            if "type" not in effect:
                errors.append(f"{prefix}: 缺少 'type' 字段")
            value = effect.get("value")
            if value is not None and not isinstance(value, (int, float, str)):
                errors.append(f"{prefix}.value: 必须是数字或变量引用字符串")

        return errors
