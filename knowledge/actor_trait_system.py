#!/usr/bin/env python3
"""
actor_trait_system.py: 吸收 OpenRA、Mindustry 与 DevilutionX 源码哲学的工业级 Actor-Trait 体系
彻底废弃单游戏硬编码实体，采用纯组件装配 (Traits) + 数据驱动 (ContentRegistry) + 确定性硬直状态机 (FSM)。
任何品类的游戏实体 (小兵/炮塔/向日葵/Boss/坦克) 均由通用 Actor 与挂载的 Traits 组装而成。
"""
from typing import Dict, List, Any, Optional, Callable

class Trait:
    def __init__(self, name: str):
        self.name = name
        self.actor = None

    def on_attach(self, actor):
        self.actor = actor

    def update(self, delta_time: float):
        pass

class HealthTrait(Trait):
    """生命与受击组件 (带受击顿帧与死亡信号)"""
    def __init__(self, max_hp: float, armor: float = 0.0):
        super().__init__("health")
        self.max_hp = max_hp
        self.hp = max_hp
        self.armor = armor
        self.is_invulnerable = False
        self.hitstop_frames = 0

    def take_damage(self, amount: float, attacker=None) -> float:
        if self.is_invulnerable or self.hp <= 0:
            return 0.0
        
        # 护甲免伤
        actual_damage = max(1.0, amount - self.armor)
        self.hp = max(0.0, self.hp - actual_damage)
        self.hitstop_frames = 3 # 顿帧 3 帧
        
        if self.actor and hasattr(self.actor, "fire_event"):
            self.actor.fire_event("on_damaged", {"damage": actual_damage, "attacker": attacker, "remaining_hp": self.hp})
            if self.hp <= 0:
                self.actor.fire_event("on_killed", {"killer": attacker})
        return actual_damage

    def update(self, delta_time: float):
        if self.hitstop_frames > 0:
            self.hitstop_frames -= 1

class ShooterTrait(Trait):
    """自动寻敌与武器开火组件 (源自 Mindustry / OpenRA Armament)"""
    def __init__(self, weapon_name: str, damage: float, interval_sec: float, range_dist: float):
        super().__init__("shooter")
        self.weapon_name = weapon_name
        self.damage = damage
        self.interval_sec = interval_sec
        self.range_dist = range_dist
        self.cooldown_timer = 0.0

    def update(self, delta_time: float):
        if self.cooldown_timer > 0:
            self.cooldown_timer -= delta_time

    def can_fire(self) -> bool:
        return self.cooldown_timer <= 0

    def fire(self, target) -> Optional[Dict[str, Any]]:
        if not self.can_fire():
            return None
        self.cooldown_timer = self.interval_sec
        payload = {
            "weapon": self.weapon_name,
            "damage": self.damage,
            "origin": (self.actor.x, self.actor.y) if self.actor else (0,0),
            "target": target
        }
        if self.actor and hasattr(self.actor, "fire_event"):
            self.actor.fire_event("on_shoot", payload)
        return payload

class Actor:
    """通用实体容器 (OpenRA 哲学: 世界上的一切皆为 Actor)"""
    def __init__(self, actor_id: str, actor_type: str, x: float = 0.0, y: float = 0.0):
        self.id = actor_id
        self.type = actor_type
        self.x = x
        self.y = y
        self.traits: Dict[str, Trait] = {}
        self.listeners: Dict[str, List[Callable]] = {}

    def add_trait(self, trait: Trait):
        self.traits[trait.name] = trait
        trait.on_attach(self)
        return self

    def get_trait(self, trait_name: str) -> Optional[Trait]:
        return self.traits.get(trait_name)

    def subscribe(self, event_name: str, callback: Callable):
        self.listeners.setdefault(event_name, []).append(callback)

    def fire_event(self, event_name: str, data: Any = None):
        if event_name in self.listeners:
            for cb in self.listeners[event_name]:
                cb(self, data)

    def update(self, delta_time: float):
        for trait in self.traits.values():
            trait.update(delta_time)

class ContentRegistry:
    """声明式数据驱动注册表 (Mindustry 哲学)"""
    def __init__(self):
        self.definitions: Dict[str, Dict[str, Any]] = {}

    def register(self, type_id: str, definition: Dict[str, Any]):
        self.definitions[type_id] = definition

    def spawn(self, type_id: str, actor_id: str, x: float, y: float) -> Actor:
        if type_id not in self.definitions:
            raise ValueError(f"Unknown Actor type: {type_id}")
        
        cfg = self.definitions[type_id]
        actor = Actor(actor_id, type_id, x, y)
        
        # 依据数据声明自动组装 Traits
        if "health" in cfg:
            actor.add_trait(HealthTrait(cfg["health"].get("max_hp", 100), cfg["health"].get("armor", 0)))
        if "shooter" in cfg:
            sc = cfg["shooter"]
            actor.add_trait(ShooterTrait(sc.get("weapon", "bullet"), sc.get("damage", 10), sc.get("interval", 1.0), sc.get("range", 100)))
            
        return actor
