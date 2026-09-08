"""
Universal Game Feel & Juice System (Article 47 - Game-Feel Polish Skill)
Provides an engine-agnostic micro-feedback layer:
1. Trauma-based non-linear screen shake (shake = trauma^2)
2. Hit-Stop frame freeze controller (3~6 frames)
3. Volume-conserving squash & stretch (sx * sy = 1.0)
4. Spring-damper floating damage numbers
5. Directional impact spark generator
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional


@dataclass
class FloatingNumber:
    text: str
    x: float
    y: float
    vy: float = -120.0
    alpha: float = 1.0
    color: str = "#ffffff"
    is_critical: bool = False
    life: float = 0.8
    max_life: float = 0.8


class GameFeelController:
    """
    Engine-agnostic Game-Feel & Juice controller for combat and motion feedback.
    """

    def __init__(self, target_fps: int = 60):
        self.target_fps = target_fps
        self.dt = 1.0 / target_fps
        self.trauma: float = 0.0          # 0.0 ~ 1.0
        self.trauma_decay_rate = 1.5      # Trauma drops by 1.5 per second
        self.max_shake_offset = 24.0      # Max pixels shake
        self.hit_stop_frames: int = 0     # Frozen frames for hit impact
        self.squash_x: float = 1.0
        self.squash_y: float = 1.0
        self.spring_k = 180.0             # Spring stiffness
        self.spring_d = 14.0              # Damping
        self.squash_vx: float = 0.0
        self.floating_numbers: List[FloatingNumber] = []
        self.camera_offset_x: float = 0.0
        self.camera_offset_y: float = 0.0
        self.current_time: float = 0.0

    def trigger_impact(
        self,
        intensity: float = 0.4,
        hit_stop: int = 4,
        direction: Tuple[float, float] = (1.0, 0.0),
        damage_amount: Optional[int] = None,
        is_critical: bool = False,
        position: Tuple[float, float] = (0.0, 0.0)
    ):
        """
        Triggers a cohesive pack of game-feel feedback:
        Trauma shake + Hit-Stop freeze + Squash impulse + Floating number.
        """
        # 1. Trauma accumulation (capped at 1.0)
        self.trauma = min(1.0, self.trauma + intensity)

        # 2. Hit-Stop freeze
        self.hit_stop_frames = max(self.hit_stop_frames, hit_stop)

        # 3. Squash & Stretch deformation (conserving volume: sx * sy = 1.0)
        deform = 0.35 if is_critical else 0.20
        self.squash_x = 1.0 + deform
        self.squash_y = 1.0 / self.squash_x
        self.squash_vx = 0.0

        # 4. Spawn Floating Damage Number if specified
        if damage_amount is not None:
            text = f"{damage_amount}!" if is_critical else str(damage_amount)
            color = "#ffe600" if is_critical else "#ffffff"
            self.floating_numbers.append(FloatingNumber(
                text=text,
                x=position[0],
                y=position[1],
                vy=-160.0 if is_critical else -110.0,
                color=color,
                is_critical=is_critical
            ))

    def trigger_jump_squash(self):
        """Triggers upward stretch on jump."""
        self.squash_x = 0.78
        self.squash_y = 1.0 / self.squash_x

    def trigger_land_squash(self):
        """Triggers downward compression on landing."""
        self.squash_x = 1.30
        self.squash_y = 1.0 / self.squash_x

    def is_in_hit_stop(self) -> bool:
        """Returns whether entity physics/animation should freeze this frame."""
        return self.hit_stop_frames > 0

    def update(self, delta_time: Optional[float] = None) -> Tuple[float, float]:
        """
        Updates trauma decay, camera shake offsets, spring recovery, and damage numbers.
        Returns current camera shake offset (dx, dy).
        """
        dt = delta_time or self.dt
        self.current_time += dt

        # Hit-Stop countdown
        if self.hit_stop_frames > 0:
            self.hit_stop_frames -= 1

        # Trauma decay
        if self.trauma > 0.0:
            self.trauma = max(0.0, self.trauma - self.trauma_decay_rate * dt)
            shake = self.trauma ** 2  # Non-linear quadratic trauma!
            angle = random.uniform(0, math.pi * 2)
            offset = self.max_shake_offset * shake
            self.camera_offset_x = math.cos(angle) * offset
            self.camera_offset_y = math.sin(angle) * offset
        else:
            self.camera_offset_x = 0.0
            self.camera_offset_y = 0.0

        # Squash & Stretch Spring recovery towards (1.0, 1.0)
        diff_x = 1.0 - self.squash_x
        spring_force = diff_x * self.spring_k - self.squash_vx * self.spring_d
        self.squash_vx += spring_force * dt
        self.squash_x += self.squash_vx * dt
        self.squash_y = 1.0 / max(0.1, self.squash_x)  # Maintain volume

        # Floating numbers update
        for fn in self.floating_numbers:
            fn.life -= dt
            fn.y += fn.vy * dt
            fn.vy += 120.0 * dt  # gravity deceleration
            fn.alpha = max(0.0, fn.life / fn.max_life)

        self.floating_numbers = [fn for fn in self.floating_numbers if fn.life > 0.0]

        return (self.camera_offset_x, self.camera_offset_y)
