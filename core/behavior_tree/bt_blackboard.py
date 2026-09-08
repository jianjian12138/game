"""
BT Blackboard — 行为树黑板（共享状态）
========================================
黑板是行为树中各节点间共享数据的中央仓库。
支持分层命名空间、变更监听和快照/回滚。
"""

from __future__ import annotations
from typing import Any, Callable, Optional


class Blackboard:
    """
    行为树黑板：键值存储 + 变更监听。

    用法::
        bb = Blackboard({"hp": 80, "target": player_obj})
        bb.set("phase", 2)
        hp = bb.get("hp", default=100)
        bb.on_change("phase", lambda old, new: print(f"阶段: {old}→{new}"))
    """

    def __init__(self, initial: Optional[dict] = None):
        self._data: dict[str, Any] = dict(initial or {})
        self._listeners: dict[str, list[Callable]] = {}

    # ------------------------------------------------------------------
    # 核心读写
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """读取值，不存在时返回 default。支持点路径: 'entity.hp'"""
        if "." in key:
            return self._get_nested(key, default)
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """写入值，并触发变更监听器。支持点路径: 'entity.hp'"""
        if "." in key:
            self._set_nested(key, value)
            return
        old = self._data.get(key)
        self._data[key] = value
        if old != value and key in self._listeners:
            for cb in self._listeners[key]:
                try:
                    cb(old, value)
                except Exception as e:
                    print(f"[Blackboard] 监听器异常 [{key}]: {e}")

    def has(self, key: str) -> bool:
        return key in self._data

    def delete(self, key: str):
        self._data.pop(key, None)

    def update(self, mapping: dict):
        """批量更新。"""
        for k, v in mapping.items():
            self.set(k, v)

    # ------------------------------------------------------------------
    # 变更监听
    # ------------------------------------------------------------------

    def on_change(self, key: str, callback: Callable):
        """注册键变更监听器。callback(old_value, new_value)"""
        self._listeners.setdefault(key, []).append(callback)

    def off_change(self, key: str, callback: Callable = None):
        """取消监听。callback=None 则取消该键的所有监听器。"""
        if callback is None:
            self._listeners.pop(key, None)
        else:
            listeners = self._listeners.get(key, [])
            if callback in listeners:
                listeners.remove(callback)

    # ------------------------------------------------------------------
    # 快照 / 回滚
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """导出当前状态快照（浅拷贝）。"""
        import copy
        return copy.copy(self._data)

    def restore(self, snapshot: dict):
        """恢复到快照状态。"""
        self._data = dict(snapshot)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _get_nested(self, key: str, default: Any) -> Any:
        parts = key.split(".")
        obj = self._data
        for p in parts:
            if isinstance(obj, dict):
                obj = obj.get(p)
            else:
                return default
            if obj is None:
                return default
        return obj

    def _set_nested(self, key: str, value: Any):
        parts = key.split(".")
        obj = self._data
        for p in parts[:-1]:
            obj = obj.setdefault(p, {})
        obj[parts[-1]] = value

    def __repr__(self):
        keys = list(self._data.keys())
        return f"Blackboard({keys})"
