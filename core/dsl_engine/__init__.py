"""
DSL Engine — 通用数据驱动语言引擎
===================================
将 YAML/JSON 描述文本解析为可执行的运行时行为。
支持多种方言：卡牌效果、弹幕模式、技能效果、节奏谱面。

用法::
    from core.dsl_engine import DSLEngine, dialects

    engine = DSLEngine(dialect=dialects.CardEffectDSL())
    effect = engine.load("effects/fireball.yaml")
    engine.execute(effect, context=battle_context)
"""

from .dsl_parser import DSLParser
from .dsl_runtime import DSLRuntime
from .dsl_validator import DSLValidator
from .dsl_hot_reload import DSLHotReload
from . import dialects

__all__ = [
    "DSLParser",
    "DSLRuntime",
    "DSLValidator",
    "DSLHotReload",
    "dialects",
    "DSLEngine",
]


class DSLEngine:
    """统一入口：解析 → 校验 → 执行 一体化管理器"""

    def __init__(self, dialect=None):
        self.dialect = dialect
        self.parser = DSLParser(dialect=dialect)
        self.validator = DSLValidator(dialect=dialect)
        self.runtime = DSLRuntime(dialect=dialect)
        self._hot_reload = None

    # ------------------------------------------------------------------
    # 核心 API
    # ------------------------------------------------------------------

    def load(self, path: str) -> dict:
        """从文件加载并校验 DSL 定义，返回 AST dict。"""
        ast = self.parser.parse_file(path)
        errors = self.validator.validate(ast)
        if errors:
            raise ValueError(f"DSL 校验失败 [{path}]: {errors}")
        return ast

    def load_text(self, text: str) -> dict:
        """从字符串加载并校验 DSL 定义，返回 AST dict。"""
        ast = self.parser.parse_text(text)
        errors = self.validator.validate(ast)
        if errors:
            raise ValueError(f"DSL 校验失败: {errors}")
        return ast

    def execute(self, ast: dict, context: dict) -> list:
        """执行 AST，返回效果事件列表。"""
        return self.runtime.execute(ast, context)

    def enable_hot_reload(self, watch_dir: str, callback=None):
        """启用热重载（开发模式），文件变更时自动重新解析。"""
        self._hot_reload = DSLHotReload(watch_dir, self, callback=callback)
        self._hot_reload.start()

    def disable_hot_reload(self):
        if self._hot_reload:
            self._hot_reload.stop()
            self._hot_reload = None
