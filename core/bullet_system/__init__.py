"""
Bullet System — 弹幕系统
=========================
提供对象池化子弹、空间哈希碰撞检测和模式运行时。

用法::
    from core.bullet_system import BulletPatternRuntime, BulletPool

    pool    = BulletPool(max_bullets=500)
    runtime = BulletPatternRuntime(pool)
    runtime.load_pattern("core/bullet_system/patterns/spiral_wave.yaml")
    runtime.start()

    # 每帧调用
    events = runtime.tick(delta_time=0.016, context={"boss_phase": 1})
"""

from .bullet_pool import BulletPool, Bullet
from .spatial_hash import SpatialHash
from .bullet_pattern_runtime import BulletPatternRuntime

__all__ = [
    "BulletPool", "Bullet",
    "SpatialHash",
    "BulletPatternRuntime",
]
