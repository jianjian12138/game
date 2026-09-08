"""
Horror Flashlight Effect and Battery Simulation
Provides dynamic cone beam, battery depletion, jitter/flicker state machine, and failure events.
"""

import math
import random
from dataclasses import dataclass
from .light_source import LightSource, LightType


class FlashlightEffect:
    """Simulates realistic handheld flashlight with battery drain and horror flickers."""

    def __init__(self, battery_max: float = 100.0, drain_rate: float = 1.0):
        self.battery_max = battery_max
        self.battery = battery_max
        self.drain_rate = drain_rate  # per second
        self.is_on = True
        self.is_flickering = False
        self.flicker_timer = 0.0

        self.light = LightSource(
            light_id="player_flashlight",
            light_type=LightType.CONE,
            radius=120.0,
            intensity=1.0,
            cone_angle=math.pi / 4.0  # 45 degrees
        )

    def toggle(self) -> bool:
        self.is_on = not self.is_on
        return self.is_on

    def trigger_flicker(self, duration: float = 1.5):
        self.is_flickering = True
        self.flicker_timer = duration

    def update(self, dt: float, player_x: float, player_y: float, player_facing_rad: float):
        self.light.x = player_x
        self.light.y = player_y
        self.light.direction = player_facing_rad

        if not self.is_on or self.battery <= 0:
            self.light.intensity = 0.0
            return

        # Drain battery
        self.battery = max(0.0, self.battery - self.drain_rate * dt)
        base_intensity = max(0.2, self.battery / self.battery_max)

        # Handle flicker
        if self.is_flickering and self.flicker_timer > 0:
            self.flicker_timer -= dt
            if random.random() < 0.4:
                self.light.intensity = 0.0
            else:
                self.light.intensity = base_intensity * random.uniform(0.3, 1.0)
            if self.flicker_timer <= 0:
                self.is_flickering = False
        else:
            # Low battery natural jitter
            if self.battery < 20.0 and random.random() < 0.15:
                self.light.intensity = base_intensity * 0.3
            else:
                self.light.intensity = base_intensity
