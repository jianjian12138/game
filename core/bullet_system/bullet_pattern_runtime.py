"""
Bullet Pattern Runtime — 弹幕模式运行时
=========================================
读取弹幕DSL（BulletPatternDSL）生成的AST，
按帧执行发射序列，管理子弹生命周期和碰撞事件。
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Optional

from .bullet_pool import BulletPool, Bullet
from .spatial_hash import SpatialHash
from ..dsl_engine import DSLEngine
from ..dsl_engine.dialects import BulletPatternDSL


class BulletPatternRuntime:
    """
    弹幕运行时引擎。

    工作流：
        1. load_pattern(yaml_path)  — 加载弹幕模式
        2. start(origin_x, origin_y)— 开始发射（传入发射源位置）
        3. 每帧 tick(delta, context) — 更新子弹 + 处理发射序列
        4. 通过 collision_events()  — 获取命中事件
    """

    def __init__(self, pool: Optional[BulletPool] = None, cell_size: float = 64.0):
        self.pool = pool or BulletPool(max_bullets=500)
        self.spatial_hash = SpatialHash(cell_size=cell_size)
        self._engine = DSLEngine(dialect=BulletPatternDSL())
        self._pattern_ast: Optional[dict] = None
        self._pattern_steps: list = []
        self._step_index: int = 0
        self._frame_timer: int = 0    # 等待帧计数
        self._wait_frames: int = 0    # 当前 wait 步骤剩余帧数
        self._origin_x: float = 0.0
        self._origin_y: float = 0.0
        self._running: bool = False
        self._loop: bool = False
        self._collision_events: list[dict] = []

    # ------------------------------------------------------------------
    # 控制 API
    # ------------------------------------------------------------------

    def load_pattern(self, path: str):
        """加载弹幕模式 YAML 文件。"""
        self._pattern_ast = self._engine.load(path)
        self._pattern_steps = self._pattern_ast.get("pattern", [])
        self._loop = self._pattern_ast.get("loop", False)
        self._step_index = 0

    def load_pattern_text(self, text: str):
        """从字符串加载弹幕模式（测试用）。"""
        self._pattern_ast = self._engine.load_text(text)
        self._pattern_steps = self._pattern_ast.get("pattern", [])
        self._loop = self._pattern_ast.get("loop", False)
        self._step_index = 0

    def start(self, origin_x: float = 0.0, origin_y: float = 0.0):
        """开始发射。"""
        self._origin_x = origin_x
        self._origin_y = origin_y
        self._running = True
        self._step_index = 0
        self._wait_frames = 0

    def stop(self):
        """停止发射（子弹继续飞行直到消失）。"""
        self._running = False

    # ------------------------------------------------------------------
    # 每帧更新
    # ------------------------------------------------------------------

    def tick(self, delta: float, context: Optional[dict] = None) -> list[dict]:
        """
        每帧调用：更新子弹物理 + 执行发射序列。

        Args:
            delta:   帧间隔时间（秒）
            context: 游戏上下文（player_x/y, boss_phase 等）

        Returns:
            本帧新发射的子弹信息列表
        """
        context = context or {}
        self._collision_events.clear()

        # 1. 更新所有子弹
        self.pool.update_all(delta)

        # 2. 重建空间哈希
        self.spatial_hash.clear()
        for b in self.pool.active_bullets():
            self.spatial_hash.insert(b, b.x, b.y, radius=8)

        # 3. 执行发射序列
        new_bullets = []
        if self._running and self._pattern_steps:
            new_bullets = self._execute_steps(delta)

        return new_bullets

    def check_hits(self, target_x: float, target_y: float,
                   target_radius: float = 16.0) -> list[Bullet]:
        """检查目标是否被子弹命中（用于玩家/敌人碰撞检测）。"""
        return self.spatial_hash.query_radius(target_x, target_y, target_radius)

    def active_count(self) -> int:
        return self.pool.active_count()

    # ------------------------------------------------------------------
    # 内部发射序列执行
    # ------------------------------------------------------------------

    def _execute_steps(self, delta: float) -> list[dict]:
        """按帧执行模式步骤序列。"""
        emitted = []

        if self._wait_frames > 0:
            self._wait_frames -= 1
            return emitted

        while self._step_index < len(self._pattern_steps):
            step = self._pattern_steps[self._step_index]
            stype = step.get("type", "fire")

            if stype == "wait":
                self._wait_frames = step.get("frames", 10)
                self._step_index += 1
                break

            if stype == "fire":
                emitted.extend(self._fire_step(step))
                self._step_index += 1

            else:
                self._step_index += 1  # 跳过未知步骤

        # 循环
        if self._step_index >= len(self._pattern_steps):
            if self._loop:
                self._step_index = 0
            else:
                self._running = False

        return emitted

    def _fire_step(self, step: dict) -> list[dict]:
        """执行一个 fire 步骤，发射一批子弹。"""
        angles = step.get("_angles", [0.0])
        speed = step.get("speed", 3.0)
        bullet_def = step.get("bullet", {})
        aimed = step.get("aimed", False)
        emitted = []

        for angle_deg in angles:
            actual_angle = angle_deg
            if aimed and "player_x" in self._get_context():
                # 瞄准玩家方向
                ctx = self._get_context()
                dx = ctx.get("player_x", 0) - self._origin_x
                dy = ctx.get("player_y", 0) - self._origin_y
                actual_angle += math.degrees(math.atan2(dy, dx))

            bullet = self.pool.acquire()
            if bullet is None:
                break  # 池已满

            rad = math.radians(actual_angle)
            bullet.x = self._origin_x
            bullet.y = self._origin_y
            bullet.speed = speed
            bullet.vx = math.cos(rad) * speed
            bullet.vy = math.sin(rad) * speed
            bullet.angle = actual_angle
            bullet.damage = bullet_def.get("damage", 1)
            bullet.lifetime = bullet_def.get("lifetime", 4.0)
            bullet.sprite = bullet_def.get("sprite", "bullet_default")
            bullet.tags = list(bullet_def.get("tags", []))
            bullet.active = True

            emitted.append({
                "type": "bullet_fired",
                "bullet": bullet,
                "angle": actual_angle,
            })

        return emitted

    def _get_context(self) -> dict:
        return {}   # 由子类或外部注入
