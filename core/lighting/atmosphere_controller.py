"""
Atmosphere & Weather Lighting Controller
Interpolates ambient colors across diurnal day/night cycles and manages weather light flashes.
"""

import math
import random
from typing import Tuple, Dict, Any


class AtmosphereController:
    """Controls ambient world color, daylight intensity, and weather effects."""

    # Time of day ambient colors (R, G, B)
    PALETTES = {
        "DAWN":     (0.85, 0.65, 0.45),
        "NOON":     (1.00, 1.00, 0.95),
        "DUSK":     (0.70, 0.40, 0.50),
        "MIDNIGHT": (0.08, 0.08, 0.18),
    }

    def __init__(self):
        self.weather = "CLEAR"  # "CLEAR", "FOGGY", "THUNDERSTORM"
        self.lightning_flash = 0.0

    @staticmethod
    def _lerp_color(c1: Tuple[float, float, float], c2: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
        return (
            round(c1[0] + (c2[0] - c1[0]) * t, 3),
            round(c1[1] + (c2[1] - c1[1]) * t, 3),
            round(c1[2] + (c2[2] - c1[2]) * t, 3),
        )

    def get_ambient_lighting(self, hour: float) -> Dict[str, Any]:
        """Hour: 0.0 to 24.0. Returns interpolated ambient color and intensity."""
        if 4.0 <= hour < 8.0:
            t = (hour - 4.0) / 4.0
            color = self._lerp_color(self.PALETTES["MIDNIGHT"], self.PALETTES["DAWN"], t)
            intensity = 0.2 + 0.5 * t
        elif 8.0 <= hour < 17.0:
            t = (hour - 8.0) / 9.0
            color = self._lerp_color(self.PALETTES["DAWN"], self.PALETTES["NOON"], min(1.0, t * 2.0))
            intensity = 0.7 + 0.3 * (1.0 - abs(hour - 12.0) / 5.0)
        elif 17.0 <= hour < 21.0:
            t = (hour - 17.0) / 4.0
            color = self._lerp_color(self.PALETTES["NOON"], self.PALETTES["DUSK"], t)
            intensity = 1.0 - 0.7 * t
        else:
            if hour >= 21.0:
                t = (hour - 21.0) / 3.0
                color = self._lerp_color(self.PALETTES["DUSK"], self.PALETTES["MIDNIGHT"], t)
            else:
                color = self.PALETTES["MIDNIGHT"]
            intensity = 0.15

        # Thunderstorm flash boost
        if self.lightning_flash > 0:
            intensity = min(1.0, intensity + self.lightning_flash)
            color = (1.0, 1.0, 1.0)

        return {
            "hour": hour,
            "ambient_color": color,
            "intensity": round(intensity, 3),
            "weather": self.weather,
            "is_night": hour < 6.0 or hour > 19.0
        }

    def update_weather(self, dt: float):
        if self.lightning_flash > 0:
            self.lightning_flash = max(0.0, self.lightning_flash - dt * 3.0)

        if self.weather == "THUNDERSTORM" and random.random() < 0.02:
            self.lightning_flash = 1.0
