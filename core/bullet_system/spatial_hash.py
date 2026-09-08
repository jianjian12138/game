"""
Spatial Hash — 空间哈希碰撞检测
==================================
将2D空间划分为网格单元，只对同一单元或相邻单元的对象进行碰撞检测，
将O(N²)暴力检测降低为接近O(1)的查询速度。

适用场景：同屏100+子弹的碰撞检测。
"""

from __future__ import annotations
import math
from typing import Any


class SpatialHash:
    """
    空间哈希表：将圆形/矩形对象插入对应的网格单元，
    快速查询给定区域内的所有对象。

    用法::
        sh = SpatialHash(cell_size=64)  # 每个格子64像素

        # 每帧重建（子弹位置变化）
        sh.clear()
        for bullet in active_bullets:
            sh.insert(bullet, bullet.x, bullet.y, radius=4)

        # 查询玩家附近的子弹
        nearby = sh.query_radius(player.x, player.y, radius=24)
    """

    def __init__(self, cell_size: float = 64.0):
        self.cell_size = cell_size
        self._table: dict[tuple[int, int], list] = {}

    def clear(self):
        """清空所有单元（每帧调用一次）。"""
        self._table.clear()

    def insert(self, obj: Any, x: float, y: float, radius: float = 0.0):
        """将对象插入覆盖其边界框的所有格子。"""
        min_cx = self._cell(x - radius)
        max_cx = self._cell(x + radius)
        min_cy = self._cell(y - radius)
        max_cy = self._cell(y + radius)

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                key = (cx, cy)
                if key not in self._table:
                    self._table[key] = []
                self._table[key].append(obj)

    def query_point(self, x: float, y: float) -> list:
        """返回包含给定点的格子中的所有对象。"""
        key = (self._cell(x), self._cell(y))
        return list(self._table.get(key, []))

    def query_radius(self, x: float, y: float, radius: float) -> list:
        """返回给定圆形范围内的所有对象（含去重）。"""
        min_cx = self._cell(x - radius)
        max_cx = self._cell(x + radius)
        min_cy = self._cell(y - radius)
        max_cy = self._cell(y + radius)

        seen = set()
        results = []
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                for obj in self._table.get((cx, cy), []):
                    obj_id = id(obj)
                    if obj_id not in seen:
                        seen.add(obj_id)
                        results.append(obj)
        return results

    def query_rect(self, left: float, top: float,
                   right: float, bottom: float) -> list:
        """返回给定矩形范围内的所有对象（含去重）。"""
        min_cx = self._cell(left)
        max_cx = self._cell(right)
        min_cy = self._cell(top)
        max_cy = self._cell(bottom)

        seen = set()
        results = []
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                for obj in self._table.get((cx, cy), []):
                    obj_id = id(obj)
                    if obj_id not in seen:
                        seen.add(obj_id)
                        results.append(obj)
        return results

    def stats(self) -> dict:
        """返回空间哈希统计信息（性能调优用）。"""
        if not self._table:
            return {"cells": 0, "avg_per_cell": 0, "max_per_cell": 0}
        counts = [len(v) for v in self._table.values()]
        return {
            "cells": len(self._table),
            "avg_per_cell": sum(counts) / len(counts),
            "max_per_cell": max(counts),
        }

    def _cell(self, coord: float) -> int:
        return math.floor(coord / self.cell_size)
