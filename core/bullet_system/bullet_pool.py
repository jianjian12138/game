"""
Bullet Pool — 子弹对象池
==========================
预分配固定数量子弹对象，重用而非频繁创建/销毁，
确保同屏500+子弹零GC压力。
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Bullet:
    """子弹运行时状态。"""
    active: bool = False
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0     # X速度（像素/帧）
    vy: float = 0.0     # Y速度
    speed: float = 0.0  # 初始速度大小
    angle: float = 0.0  # 初始角度（度，0=右）
    damage: int = 1
    lifetime: float = 4.0   # 最大存活时间（秒）
    elapsed: float = 0.0
    sprite: str = "bullet_default"
    tags: list = field(default_factory=list)
    # 追踪弹参数
    homing: bool = False
    target_x: float = 0.0
    target_y: float = 0.0
    turn_speed: float = 3.0   # 追踪转向速度（度/帧）

    def reset(self):
        """回收子弹，重置所有状态。"""
        self.active = False
        self.x = self.y = 0.0
        self.vx = self.vy = 0.0
        self.elapsed = 0.0
        self.homing = False
        self.tags = []

    def update(self, delta: float):
        """物理更新：移动 + 生命周期。"""
        if not self.active:
            return

        if self.homing:
            self._update_homing()

        self.x += self.vx * delta * 60   # 转换为帧速度
        self.y += self.vy * delta * 60
        self.elapsed += delta

        if self.elapsed >= self.lifetime:
            self.active = False

    def _update_homing(self):
        """追踪弹：逐步转向目标方向。"""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        target_angle = math.degrees(math.atan2(dy, dx))
        current_angle = math.degrees(math.atan2(self.vy, self.vx))

        # 计算最短旋转方向
        diff = (target_angle - current_angle + 180) % 360 - 180
        turn = max(-self.turn_speed, min(self.turn_speed, diff))
        new_angle = math.radians(current_angle + turn)

        self.vx = math.cos(new_angle) * self.speed
        self.vy = math.sin(new_angle) * self.speed


class BulletPool:
    """
    子弹对象池：预分配 max_bullets 个 Bullet，循环复用。

    用法::
        pool = BulletPool(max_bullets=500)
        bullet = pool.acquire()
        if bullet:
            bullet.x, bullet.y = 100, 200
            bullet.vx, bullet.vy = 3.0, 0.0
            bullet.damage = 1
            bullet.active = True

        # 每帧更新
        pool.update_all(delta_time)

        # 回收（超时自动回收，也可手动）
        pool.release(bullet)
    """

    def __init__(self, max_bullets: int = 500):
        self.max_bullets = max_bullets
        self._pool = [Bullet() for _ in range(max_bullets)]
        self._next_index = 0

    def acquire(self) -> Optional[Bullet]:
        """从池中取一个非活跃子弹。"""
        # 从 next_index 开始循环查找
        for _ in range(self.max_bullets):
            b = self._pool[self._next_index]
            self._next_index = (self._next_index + 1) % self.max_bullets
            if not b.active:
                b.reset()
                return b
        return None  # 池已满

    def release(self, bullet: Bullet):
        """手动回收子弹。"""
        bullet.reset()

    def update_all(self, delta: float):
        """更新所有活跃子弹。"""
        for b in self._pool:
            if b.active:
                b.update(delta)

    def active_bullets(self) -> list[Bullet]:
        """返回所有活跃子弹列表（只读，不分配新内存）。"""
        return [b for b in self._pool if b.active]

    def active_count(self) -> int:
        return sum(1 for b in self._pool if b.active)

    def fill_ratio(self) -> float:
        """池占用率（0.0–1.0），超过 0.9 时应警告。"""
        return self.active_count() / self.max_bullets
