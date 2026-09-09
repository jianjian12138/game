#!/usr/bin/env python3
"""
core/security_guard.py: 服务安全白名单与路径穿越防御守卫 (Security Guard)
防御路径穿越攻击 (../)、任意文件读写以及公网高频泛洪调用。
纯 Python 3.9+ 标准库实现，零外部依赖。
"""
import hmac
import ipaddress
import os
import sys
import time
from pathlib import Path
from typing import Union, List, Optional, Dict, Mapping

ROOT = Path(__file__).resolve().parent.parent

class SecurityGuardError(PermissionError):
    """安全拦截异常"""
    pass


def is_loopback_host(host: str) -> bool:
    """判断监听地址是否为回环地址。无法确认的主机名按非回环处理。"""
    normalized = str(host or "").strip().lower().strip("[]")
    if normalized == "localhost":
        return True

    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False

    if address.is_loopback:
        return True
    mapped_address = getattr(address, "ipv4_mapped", None)
    return bool(mapped_address and mapped_address.is_loopback)


def get_configured_token(environ: Optional[Mapping[str, str]] = None) -> str:
    """读取启动配置中的 token，不接收或写入请求数据。"""
    source = os.environ if environ is None else environ
    return str(source.get("GAME_STUDIO_TOKEN", "")).strip()


def has_valid_bearer_token(headers: Mapping[str, str], expected_token: str) -> bool:
    """使用 Bearer 认证校验请求 token，避免普通字符串比较泄露时序信息。"""
    if not expected_token:
        return False

    authorization = str(headers.get("Authorization", ""))
    scheme, separator, credentials = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer":
        return False

    return hmac.compare_digest(credentials.strip(), expected_token)


def safe_resolve_path(raw_path: Union[str, Path], allowed_roots: Optional[List[Path]] = None) -> Path:
    """
    安全路径解析器：严格确保目标路径位于允许的工作区白名单范围内。
    杜绝任何包含路径穿越 (../) 或指向系统敏感目录的非法访问。
    """
    if not raw_path:
        raise SecurityGuardError("路径参数不能为空")

    roots = [r.resolve() for r in (allowed_roots or [ROOT])]
    p_str = str(raw_path).strip()

    # 处理相对路径或绝对路径
    path_obj = Path(p_str)
    if not path_obj.is_absolute():
        resolved = (ROOT / path_obj).resolve()
    else:
        resolved = path_obj.resolve()

    # 检查是否落在任一允许的根目录下
    is_safe = False
    for root in roots:
        try:
            resolved.relative_to(root)
            is_safe = True
            break
        except ValueError:
            continue

    if not is_safe:
        raise SecurityGuardError(f"安全拦截：路径 '{p_str}' 超出允许的工作区安全白名单范围！")

    return resolved

class RateLimiter:
    """轻量级客户端内存滑动窗口限流器"""

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._records: Dict[str, List[float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        timestamps = self._records.setdefault(client_id, [])
        # 清理窗口外的时间戳
        valid_timestamps = [t for t in timestamps if now - t < self.window_seconds]
        self._records[client_id] = valid_timestamps

        if len(valid_timestamps) >= self.max_requests:
            return False

        valid_timestamps.append(now)
        return True

    def clear(self):
        self._records.clear()

global_rate_limiter = RateLimiter(max_requests=120, window_seconds=60.0)
