#!/usr/bin/env python3
"""
hook_manager.py: 游戏开发全生命周期钩子引擎 (Lifecycle Hook Manager)
管理 12 个关键研发阶段的事件分发、拦截、上下文传递与自愈回调。
"""
from typing import Dict, List, Callable, Any
import time

class HookManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HookManager, cls).__new__(cls)
            cls._instance._handlers = {}
            cls._instance._history = []
        return cls._instance

    def register(self, hook_id: str, callback: Callable[[dict], dict]):
        if hook_id not in self._handlers:
            self._handlers[hook_id] = []
        self._handlers[hook_id].append(callback)

    def trigger(self, hook_id: str, context: dict) -> dict:
        event = {
            "hook": hook_id,
            "timestamp": time.strftime("%H:%M:%S"),
            "context": context
        }
        self._history.append(event)
        
        current_ctx = dict(context)
        if hook_id in self._handlers:
            for cb in self._handlers[hook_id]:
                try:
                    res = cb(current_ctx)
                    if isinstance(res, dict):
                        current_ctx.update(res)
                except Exception as e:
                    current_ctx.setdefault("errors", []).append(f"Hook [{hook_id}] 异常: {str(e)}")

        return current_ctx

    def get_history(self) -> List[dict]:
        return self._history

hook_manager = HookManager()
