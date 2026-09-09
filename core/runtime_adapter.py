#!/usr/bin/env python3
"""
core/runtime_adapter.py: 目标运行时适配器统一抽象基类 (Runtime Adapter Base)
遵循实施计划第 8.1 节统一接口原则：负责启动目标运行时、执行探针、采集事实、返回结构化结果。
纯 Python 3.9+ 标准库实现，零外部依赖。
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional

class RuntimeStatus:
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_RUNTIME_TOOL = "NEEDS_RUNTIME_TOOL"
    TIMEOUT = "TIMEOUT"
    CRASHED = "CRASHED"
    BLOCKED_BY_STATIC = "BLOCKED_BY_STATIC_VALIDATION"

class RuntimeSession:
    """运行时会话状态容器"""
    def __init__(self, session_id: str, url: str = "", target: str = "web", **kwargs: Any):
        self.session_id = session_id
        self.url = url
        self.target = target
        self.alive = True
        self.data: Dict[str, Any] = kwargs

    def __getitem__(self, item: str) -> Any:
        if hasattr(self, item):
            return getattr(self, item)
        return self.data.get(item)

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            val = getattr(self, key)
            if val is not None:
                return val
        return self.data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.data)
        d.update({
            "session_id": self.session_id,
            "url": self.url,
            "target": self.target,
            "alive": self.alive
        })
        return d

class RuntimeAdapter(ABC):
    """目标运行时适配器抽象基类"""
    name: str = "base_runtime_adapter"
    version: str = "1.0.0"

    @abstractmethod
    def preflight(self, target: str, environment: str = "sandbox") -> Dict[str, Any]:
        """环境自检：验证目标运行时、可执行文件与端口/权限是否就绪"""
        pass

    @abstractmethod
    def launch(self, artifact_path: Path, environment: str = "sandbox") -> Dict[str, Any]:
        """启动目标运行时会话 (Session)"""
        pass

    @abstractmethod
    def run_scenarios(self, session: Dict[str, Any], scenarios: List[str]) -> Dict[str, Any]:
        """执行测试场景 (如 boot, start, core_loop, game_over, restart)"""
        pass

    @abstractmethod
    def collect_evidence(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """采集运行事实、控制台日志、网络请求指标与截图/视频证据"""
        pass

    @abstractmethod
    def close(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """关闭运行时会话，释放端口与资源"""
        pass
