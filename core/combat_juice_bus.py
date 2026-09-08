"""
Combat Juice Bus — 打击感全自动编排总线
============================================
将 FrameData 招式强度、Hitbox 碰撞几何、GameFeelController 创伤震屏/停顿
以及 AudioManager 声音反馈深度熔铸为零样板代码的打击反馈流水线。
遵循 Game Science Principles:
  - 3~6 帧 Hit-Stop 停顿 (无额外开销的钝化爽感)
  - 非线性创伤震屏 (Trauma^2)
  - 体积守恒挤压拉伸 (sx * sy = 1.0)
  - 弹簧阻尼浮动伤害跳字与方向火花粒子
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Any, Tuple, Optional, List
from core.game_feel_juice_system import GameFeelController
from core.frame_data.hitbox_manager import Hitbox, HitboxType
from core.frame_data.frame_data_table import MoveData


@dataclass
class ImpactResolution:
    hit_detected: bool
    impact_tier: str              # "LIGHT", "MEDIUM", "HEAVY", "SUPER"
    damage: int
    is_critical: bool
    hit_stop_frames: int
    trauma_applied: float
    hit_coords: Tuple[float, float]
    impact_angle_deg: float
    spark_particles: List[Dict[str, Any]]
    sfx_channel: str
    sfx_name: str
    camera_shake: Tuple[float, float]
    squash_scale: Tuple[float, float]


class CombatJuiceBus:
    """
    Automated orchestrator that binds combat hitboxes with sensory juice.
    Resolves attacks into tactile, auditory, and visual micro-feedback in a single call.
    """

    IMPACT_PRESETS = {
        "LIGHT": {
            "hit_stop": 3,
            "trauma": 0.20,
            "spark_count": 5,
            "sfx": "sfx_hit_light.wav",
            "base_damage": 15,
        },
        "MEDIUM": {
            "hit_stop": 5,
            "trauma": 0.38,
            "spark_count": 10,
            "sfx": "sfx_hit_medium.wav",
            "base_damage": 35,
        },
        "HEAVY": {
            "hit_stop": 8,
            "trauma": 0.60,
            "spark_count": 18,
            "sfx": "sfx_hit_heavy.wav",
            "base_damage": 75,
        },
        "SUPER": {
            "hit_stop": 12,
            "trauma": 0.85,
            "spark_count": 30,
            "sfx": "sfx_hit_super.wav",
            "base_damage": 150,
        },
    }

    def __init__(self, game_feel: Optional[GameFeelController] = None, audio_manager: Optional[Any] = None):
        self.game_feel = game_feel or GameFeelController()
        self.audio_manager = audio_manager
        self.total_hits_processed = 0

    @staticmethod
    def _compute_overlap_center(b1: Hitbox, b2: Hitbox) -> Tuple[float, float]:
        """Calculates center of AABB intersection for precise particle & text spawning."""
        ix1 = max(b1.left, b2.left)
        ix2 = min(b1.right, b2.right)
        iy1 = max(b1.bottom, b2.bottom)
        iy2 = min(b1.top, b2.top)
        cx = (ix1 + ix2) * 0.5
        cy = (iy1 + iy2) * 0.5
        return round(cx, 1), round(cy, 1)

    @classmethod
    def determine_tier(cls, move_data: Optional[MoveData], damage: int) -> str:
        if move_data:
            mname = move_data.name.lower()
            active_f = getattr(move_data, "active", getattr(move_data, "active_frames", 0))
            if "super" in mname or "ultra" in mname:
                return "SUPER"
            if "heavy" in mname or active_f >= 5:
                return "HEAVY"
            if "medium" in mname:
                return "MEDIUM"
            if "light" in mname or "jab" in mname:
                return "LIGHT"

        # Fallback to damage scale
        if damage >= 120:
            return "SUPER"
        elif damage >= 60:
            return "HEAVY"
        elif damage >= 25:
            return "MEDIUM"
        return "LIGHT"

    def resolve_hit(
        self,
        attacker_box: Hitbox,
        defender_box: Hitbox,
        move_data: Optional[MoveData] = None,
        override_damage: Optional[int] = None,
        is_critical: bool = False
    ) -> ImpactResolution:
        """
        Main arbitration entrypoint:
        1. Checks AABB overlap between attacker HITBOX and defender HURTBOX
        2. Determines impact weight tier
        3. Fires trauma, hit-stop, squash deformation, and floating damage number
        4. Calculates directional spark burst
        5. Dispatches SFX audio event
        """
        # 1. Overlap test
        if not attacker_box.overlaps(defender_box):
            return ImpactResolution(
                hit_detected=False,
                impact_tier="NONE",
                damage=0,
                is_critical=False,
                hit_stop_frames=0,
                trauma_applied=0.0,
                hit_coords=(0.0, 0.0),
                impact_angle_deg=0.0,
                spark_particles=[],
                sfx_channel="SFX",
                sfx_name="",
                camera_shake=(0.0, 0.0),
                squash_scale=(1.0, 1.0)
            )

        self.total_hits_processed += 1
        tier = self.determine_tier(move_data, override_damage or 0)
        preset = self.IMPACT_PRESETS[tier]

        damage = override_damage if override_damage is not None else preset["base_damage"]
        if is_critical:
            damage = int(round(damage * 1.5))
            if tier != "SUPER":
                tier = "HEAVY"
                preset = self.IMPACT_PRESETS[tier]

        hit_coords = self._compute_overlap_center(attacker_box, defender_box)

        # Attacker -> Defender impact vector
        dx = defender_box.x - attacker_box.x
        dy = defender_box.y - attacker_box.y
        impact_angle_rad = math.atan2(dy, dx)
        impact_angle_deg = math.degrees(impact_angle_rad)

        # 2. Trigger Game Feel (Hit-stop + Trauma shake + Squash/Stretch + Floating number)
        hit_stop = preset["hit_stop"] + (2 if is_critical else 0)
        trauma = min(1.0, preset["trauma"] * (1.3 if is_critical else 1.0))

        self.game_feel.trigger_impact(
            intensity=trauma,
            hit_stop=hit_stop,
            direction=(math.cos(impact_angle_rad), math.sin(impact_angle_rad)),
            damage_amount=damage,
            is_critical=is_critical,
            position=hit_coords
        )

        # 3. Generate directional spark particles
        sparks = []
        base_speed = 180.0 if tier in ["HEAVY", "SUPER"] else 100.0
        for i in range(preset["spark_count"]):
            # Cone spread: +/- 35 degrees from impact angle
            spread = math.radians(math.sin(i * 1.7) * 35.0)
            spark_ang = impact_angle_rad + spread
            speed = base_speed * (0.6 + 0.8 * ((i % 5) / 5.0))
            sparks.append({
                "x": hit_coords[0],
                "y": hit_coords[1],
                "vx": round(math.cos(spark_ang) * speed, 1),
                "vy": round(math.sin(spark_ang) * speed, 1),
                "life": round(0.25 + 0.15 * (i % 3), 2),
                "color": "#ffdd44" if is_critical else "#ff6600"
            })

        # 4. Trigger Audio
        sfx_name = preset["sfx"]
        if self.audio_manager and hasattr(self.audio_manager, "play_sfx"):
            self.audio_manager.play_sfx(sfx_name, volume=1.0 if tier != "LIGHT" else 0.7)

        shake = (self.game_feel.camera_offset_x, self.game_feel.camera_offset_y)
        squash = (round(self.game_feel.squash_x, 2), round(self.game_feel.squash_y, 2))

        return ImpactResolution(
            hit_detected=True,
            impact_tier=tier,
            damage=damage,
            is_critical=is_critical,
            hit_stop_frames=hit_stop,
            trauma_applied=trauma,
            hit_coords=hit_coords,
            impact_angle_deg=round(impact_angle_deg, 1),
            spark_particles=sparks,
            sfx_channel="SFX",
            sfx_name=sfx_name,
            camera_shake=shake,
            squash_scale=squash
        )
