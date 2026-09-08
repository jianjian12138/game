"""
DSL Runtime — AST 执行器
==========================
将解析后的 AST 字典转换为实际的游戏效果事件列表。
支持条件判断、变量替换、链式效果执行。
"""

from __future__ import annotations
from typing import Any, Callable, Optional
import copy


class DSLRuntime:
    """
    执行 DSL AST，产生效果事件（Effect Events）列表。

    效果事件格式::
        {
            "type": "damage",       # 效果类型
            "target": "enemy",      # 目标
            "value": 6,             # 数值
            "tags": ["burn"],       # 附加标签
            "source_id": "fireball" # 来源 ID
        }
    """

    def __init__(self, dialect=None):
        self.dialect = dialect
        # 内置效果处理器注册表
        self._handlers: dict[str, Callable] = {}
        self._register_builtin_handlers()

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def execute(self, ast: dict, context: dict) -> list[dict]:
        """
        执行完整 AST。

        Args:
            ast:     由 DSLParser 解析的 AST dict
            context: 游戏上下文（caster/target/board/random_seed 等）

        Returns:
            效果事件列表，按执行顺序排列
        """
        events = []
        source_id = ast.get("id", "unknown")

        for effect_def in ast.get("effect", []):
            if not self._check_condition(effect_def, context):
                continue
            resolved = self._resolve_variables(effect_def, context)
            evts = self._execute_single(resolved, context, source_id)
            events.extend(evts)

        # 方言后处理
        if self.dialect and hasattr(self.dialect, "postprocess_events"):
            events = self.dialect.postprocess_events(events, context)

        return events

    def register_handler(self, effect_type: str, handler: Callable):
        """注册自定义效果处理器。handler(effect_def, context) → list[dict]"""
        self._handlers[effect_type] = handler

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _execute_single(self, effect: dict, context: dict, source_id: str) -> list[dict]:
        etype = effect.get("type", "unknown")
        handler = self._handlers.get(etype)
        if handler is None:
            # 未知类型：透传为原始事件
            return [{"type": etype, "source_id": source_id, **effect}]
        return handler(effect, context, source_id)

    def _check_condition(self, effect: dict, context: dict) -> bool:
        """检查 effect.condition 是否满足。"""
        cond = effect.get("condition")
        if cond is None:
            return True
        # 简单条件表达式求值（安全子集，不使用 eval）
        return self._eval_condition(cond, context)

    def _eval_condition(self, cond: str, context: dict) -> bool:
        """
        安全条件表达式求值。
        支持格式: "target_has_tag(burn)", "caster_hp_below(30)", "always"
        """
        if cond == "always":
            return True
        if cond == "never":
            return False

        # target_has_tag(X)
        if cond.startswith("target_has_tag("):
            tag = cond[len("target_has_tag("):-1]
            target = context.get("target", {})
            return tag in target.get("tags", [])

        # caster_hp_below(X)
        if cond.startswith("caster_hp_below("):
            threshold = float(cond[len("caster_hp_below("):-1])
            caster = context.get("caster", {})
            hp_pct = caster.get("hp", 100) / max(caster.get("max_hp", 100), 1) * 100
            return hp_pct < threshold

        # 方言自定义条件
        if self.dialect and hasattr(self.dialect, "eval_condition"):
            return self.dialect.eval_condition(cond, context)

        return True  # 未知条件默认通过

    def _resolve_variables(self, effect: dict, context: dict) -> dict:
        """将 effect 中的变量引用（如 {caster.atk}）替换为实际值。"""
        resolved = copy.deepcopy(effect)
        for key, val in resolved.items():
            if isinstance(val, str) and val.startswith("{") and val.endswith("}"):
                ref = val[1:-1]
                resolved[key] = self._lookup(ref, context)
        return resolved

    def _lookup(self, ref: str, context: dict) -> Any:
        """点路径查找，如 'caster.atk' → context['caster']['atk']"""
        parts = ref.split(".")
        obj = context
        for p in parts:
            if isinstance(obj, dict):
                obj = obj.get(p)
            else:
                return None
        return obj

    def _register_builtin_handlers(self):
        """注册内置效果类型处理器。"""

        def handle_damage(effect, context, source_id):
            return [{
                "type": "damage",
                "source_id": source_id,
                "target": effect.get("target", "enemy_single"),
                "value": effect.get("value", 0),
                "tags": effect.get("tags", []),
            }]

        def handle_heal(effect, context, source_id):
            return [{
                "type": "heal",
                "source_id": source_id,
                "target": effect.get("target", "self"),
                "value": effect.get("value", 0),
            }]

        def handle_buff(effect, context, source_id):
            return [{
                "type": "buff",
                "source_id": source_id,
                "target": effect.get("target", "self"),
                "stat": effect.get("stat", "atk"),
                "value": effect.get("value", 0),
                "duration": effect.get("duration", 1),
            }]

        def handle_draw(effect, context, source_id):
            return [{
                "type": "draw_card",
                "source_id": source_id,
                "count": effect.get("count", 1),
            }]

        def handle_spawn(effect, context, source_id):
            return [{
                "type": "spawn_unit",
                "source_id": source_id,
                "unit_id": effect.get("unit_id", "unknown"),
                "position": effect.get("position", "random"),
            }]

        self._handlers["damage"] = handle_damage
        self._handlers["heal"] = handle_heal
        self._handlers["buff"] = handle_buff
        self._handlers["debuff"] = handle_buff   # 同形状
        self._handlers["draw"] = handle_draw
        self._handlers["spawn"] = handle_spawn
