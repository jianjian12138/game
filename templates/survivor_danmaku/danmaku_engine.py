"""
Survivor Danmaku Archetype Engine
Combines BulletPool (500+ zero-GC), SpatialHash (O(1) query), BulletPatternRuntime,
and CombatJuiceBus into a high-throughput bullet-hell game loop.
"""

from typing import Dict, List, Any, Tuple
from core.bullet_system.bullet_pool import BulletPool
from core.bullet_system.spatial_hash import SpatialHash
from core.combat_juice_bus import CombatJuiceBus
from core.frame_data.hitbox_manager import Hitbox, HitboxType


class SurvivorDanmakuGame:
    """Simulates high-density bullet waves, spatial partitioning, and enemy kills."""

    def __init__(self, pool_capacity: int = 500, world_size: float = 800.0):
        self.world_size = world_size
        self.bullet_pool = BulletPool(capacity=pool_capacity)
        self.spatial_hash = SpatialHash(cell_size=32.0)
        self.juice_bus = CombatJuiceBus()

        self.player_x = 400.0
        self.player_y = 300.0
        self.player_hp = 100
        self.score = 0
        self.wave = 1

        self.enemies: List[Dict[str, Any]] = []
        self._spawn_wave(10)

    def _spawn_wave(self, count: int):
        import random
        for i in range(count):
            self.enemies.append({
                "id": f"mob_{len(self.enemies) + 1}",
                "x": random.uniform(50, 750),
                "y": random.uniform(50, 200),
                "hp": 20,
                "speed": random.uniform(30.0, 60.0)
            })

    def fire_radial_burst(self, center_x: float, center_y: float, bullet_count: int = 16, speed: float = 120.0):
        """Fires radial pattern using bullet pool."""
        import math
        step_rad = (math.pi * 2) / bullet_count
        for i in range(bullet_count):
            ang = i * step_rad
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            self.bullet_pool.spawn(center_x, center_y, vx, vy, lifetime=4.0, damage=10, radius=4.0)

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Main game tick: updates bullets, rebuilds spatial hash, checks collisions."""
        # 1. Update active bullets
        self.bullet_pool.update(dt)

        # 2. Re-populate spatial hash with active bullets
        self.spatial_hash.clear()
        active_bullets = self.bullet_pool.get_active_bullets()
        for idx, b in enumerate(active_bullets):
            self.spatial_hash.insert(idx, b.x, b.y, b.radius)

        # 3. Check enemy collisions against bullets
        hits_resolved = 0
        dead_enemies = []

        for e in self.enemies:
            # Query nearby bullets within enemy bounding radius
            nearby = self.spatial_hash.query_radius(e["x"], e["y"], radius=16.0)
            for b_idx in nearby:
                bullet = active_bullets[b_idx]
                if not bullet.active:
                    continue

                # Collision confirmed
                bullet.active = False
                e["hp"] -= bullet.damage

                # Fire juice bus
                att_box = Hitbox(HitboxType.HITBOX, bullet.x, bullet.y, 8.0, 8.0)
                def_box = Hitbox(HitboxType.HURTBOX, e["x"], e["y"], 24.0, 24.0)
                self.juice_bus.resolve_hit(att_box, def_box, override_damage=bullet.damage)
                hits_resolved += 1

                if e["hp"] <= 0:
                    dead_enemies.append(e)
                    self.score += 50
                    break

        # Remove dead
        self.enemies = [e for e in self.enemies if e not in dead_enemies]

        return {
            "active_bullets": len(active_bullets),
            "enemies_count": len(self.enemies),
            "hits_resolved": hits_resolved,
            "score": self.score
        }
