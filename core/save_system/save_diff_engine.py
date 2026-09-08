"""
Save Diff Engine — 增量存档引擎
=================================
只存储状态变化（diff），大幅减少 IO 开销和存储空间。
适用于：大地图经营游戏、长时间运营的RPG。

原理：
    新状态 = 旧状态 + Patch
    Patch 只包含变化的键，删除的键用 _DELETED 标记。
"""

from __future__ import annotations
from typing import Any

_DELETED = "__DELETED__"


class SaveDiffEngine:
    """增量存档：计算 diff、应用 patch、合并历史。"""

    @staticmethod
    def diff(old_state: dict, new_state: dict) -> dict:
        """
        计算两个状态之间的差异（浅层 diff，一级 key）。

        Args:
            old_state: 旧状态
            new_state: 新状态

        Returns:
            patch dict：只包含变化的键值对，删除的键值为 _DELETED
        """
        patch = {}

        all_keys = set(old_state.keys()) | set(new_state.keys())
        for key in all_keys:
            old_val = old_state.get(key, _DELETED)
            new_val = new_state.get(key, _DELETED)

            if old_val != new_val:
                if new_val == _DELETED:
                    patch[key] = _DELETED   # 标记为已删除
                else:
                    patch[key] = new_val

        return patch

    @staticmethod
    def apply(base_state: dict, patch: dict) -> dict:
        """
        将 patch 应用到 base_state，返回新状态（不修改原状态）。

        Args:
            base_state: 基础状态
            patch:      由 diff() 生成的 patch

        Returns:
            新状态 dict
        """
        import copy
        new_state = copy.deepcopy(base_state)

        for key, value in patch.items():
            if value == _DELETED:
                new_state.pop(key, None)
            else:
                new_state[key] = value

        return new_state

    @staticmethod
    def deep_diff(old: Any, new: Any, path: str = "") -> dict:
        """
        深层 diff：递归比较嵌套字典，返回点路径格式的 patch。

        示例::
            old = {"player": {"hp": 80, "gold": 100}}
            new = {"player": {"hp": 60, "gold": 100}}
            diff = deep_diff(old, new)
            # → {"player.hp": 60}
        """
        patches = {}

        if isinstance(old, dict) and isinstance(new, dict):
            all_keys = set(old.keys()) | set(new.keys())
            for key in all_keys:
                sub_path = f"{path}.{key}" if path else key
                old_val = old.get(key, _DELETED)
                new_val = new.get(key, _DELETED)
                if old_val != new_val:
                    sub_patches = SaveDiffEngine.deep_diff(old_val, new_val, sub_path)
                    patches.update(sub_patches)
        else:
            if old != new:
                patches[path] = new

        return patches

    @staticmethod
    def compress_patches(patches: list[dict]) -> dict:
        """
        将多个 patch 合并为一个（取最新值）。
        用于：将多个自动存档 patch 合并为一个完整 patch 再写盘。
        """
        merged = {}
        for patch in patches:
            merged.update(patch)
        return merged

    @staticmethod
    def patch_size_bytes(patch: dict) -> int:
        """估算 patch 的序列化大小（字节）。"""
        import json
        return len(json.dumps(patch, ensure_ascii=False).encode("utf-8"))
