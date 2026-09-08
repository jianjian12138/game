#!/usr/bin/env python3
"""
core/exceptions.py: 游戏开发智能体平台统一异常体系与结构化错误码
规范所有子系统、网络分发、资产编译、安全门禁与 LLM 网关的错误抛出与处理。
"""
from typing import Optional, Dict, Any

class GameDevError(Exception):
    """平台所有异常的顶层基类"""
    def __init__(self, message: str, code: str = "ERR_INTERNAL", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

# ─── 安全违规异常 ─────────────────────────────────────────────────────────────
class SecurityViolationError(GameDevError):
    """安全违规：路径穿越、越权访问、环境泄露等"""
    def __init__(self, message: str, code: str = "ERR_SECURITY_VIOLATION", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)

class PathTraversalError(SecurityViolationError):
    """静态文件路径穿越违规"""
    def __init__(self, path: str):
        super().__init__(f"检测到非法路径穿越尝试: {path}", code="ERR_PATH_TRAVERSAL", details={"attempted_path": path})

# ─── 核心引擎异常 ─────────────────────────────────────────────────────────────
class EngineError(GameDevError):
    """核心引擎调度与装配失败"""
    def __init__(self, message: str, code: str = "ERR_ENGINE_FAILURE", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)

class PartNotFoundError(EngineError):
    """Ford-T 零件未找到"""
    def __init__(self, part_key: str):
        super().__init__(f"Ford-T 零件库中未找到构件: {part_key}", code="ERR_PART_NOT_FOUND", details={"part_key": part_key})

class CompilationError(EngineError):
    """多平台目标代码编译/装配失败"""
    def __init__(self, message: str, target_platform: str = "unknown"):
        super().__init__(message, code="ERR_COMPILATION_FAILED", details={"platform": target_platform})

# ─── 门禁与验证异常 ───────────────────────────────────────────────────────────
class ValidationError(GameDevError):
    """门禁断言或合规性校验失败"""
    def __init__(self, message: str, code: str = "ERR_VALIDATION_FAILED", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)

class RedTeamVetoError(ValidationError):
    """红军对抗性审查一票否决"""
    def __init__(self, veto_reasons: list):
        super().__init__(f"触发红军对抗一票否决 ({len(veto_reasons)} 项未通过)", code="ERR_RED_TEAM_VETO", details={"vetoes": veto_reasons})

class ComplianceBudgetExceededError(ValidationError):
    """微信 4MB 等跨端合规包体超标"""
    def __init__(self, actual_size_mb: float, limit_mb: float = 4.0):
        super().__init__(
            f"首包分包预算超标: 实测 {actual_size_mb:.2f}MB, 限制 {limit_mb:.2f}MB",
            code="ERR_BUDGET_EXCEEDED",
            details={"actual_mb": actual_size_mb, "limit_mb": limit_mb}
        )

# ─── LLM 网关异常 ─────────────────────────────────────────────────────────────
class LLMGatewayError(GameDevError):
    """大模型提供商调用与通信异常"""
    def __init__(self, message: str, provider: str = "", code: str = "ERR_LLM_GATEWAY"):
        super().__init__(message, code, details={"provider": provider})

class LLMAuthError(LLMGatewayError):
    """API Key 缺失或鉴权失败"""
    def __init__(self, provider: str):
        super().__init__(f"{provider.upper()} API Key 缺失或无效", provider=provider, code="ERR_LLM_AUTH")
