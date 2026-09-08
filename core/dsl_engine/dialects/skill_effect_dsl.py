"""
Skill Effect DSL — 技能效果方言（RPG/动作游戏通用）
====================================================
描述技能的施放条件、范围、效果序列和冷却。

YAML 示例::

    id: thunder_strike
    name: 雷击
    cooldown: 3.0
    cast_range: 8.0
    area:
      shape: circle
      radius: 2.5
    effect:
      - type: damage
        target: area_targets
        value: 40
        tags: [lightning, aoe]
      - type: stun
        target: area_targets
        duration: 0.8
      - type: vfx
        asset: vfx_thunder
        position: cast_position
      - type: sfx
        asset: sfx_thunder_crack

    id: poison_dart
    name: 毒镖
    cooldown: 1.5
    cast_range: 12.0
    projectile:
      speed: 18.0
      homing: false
    effect:
      - type: damage
        target: hit_target
        value: 10
      - type: dot              # 持续伤害
        target: hit_target
        damage_per_tick: 5
        tick_interval: 1.0
        duration: 4.0
        tags: [poison]
"""


class SkillEffectDSL:
    """RPG技能效果方言，支持AOE/投射物/持续效果。"""

    VALID_SHAPES = {"circle", "cone", "rectangle", "line", "point"}

    def preprocess(self, raw: dict) -> dict:
        raw.setdefault("cooldown", 1.0)
        raw.setdefault("cast_range", 6.0)
        raw.setdefault("cast_time", 0.0)   # 吟唱时间
        raw.setdefault("mana_cost", 0)
        raw.setdefault("interrupt_on_move", False)

        # 区域技能默认值
        if "area" in raw:
            area = raw["area"]
            area.setdefault("shape", "circle")
            area.setdefault("radius", 2.0)

        # 投射物默认值
        if "projectile" in raw:
            proj = raw["projectile"]
            proj.setdefault("speed", 12.0)
            proj.setdefault("homing", False)
            proj.setdefault("pierce", False)   # 穿透
            proj.setdefault("max_bounces", 0)  # 弹射次数

        # effect 填充
        for effect in raw.get("effect", []) or []:
            effect.setdefault("type", "damage")
            if effect.get("type") == "dot":
                effect.setdefault("tick_interval", 1.0)
                effect.setdefault("duration", 3.0)
                effect.setdefault("damage_per_tick", 5)

        return raw

    def validate(self, ast: dict) -> list[str]:
        errors = []
        if "area" in ast:
            shape = ast["area"].get("shape", "circle")
            if shape not in self.VALID_SHAPES:
                errors.append(f"area.shape 无效: '{shape}'，合法值: {self.VALID_SHAPES}")
        cd = ast.get("cooldown", 1.0)
        if not isinstance(cd, (int, float)) or cd < 0:
            errors.append(f"cooldown 必须是非负数: {cd}")
        return errors

    def eval_condition(self, cond: str, context: dict) -> bool:
        if cond.startswith("mana_above("):
            n = float(cond[len("mana_above("):-1])
            return context.get("caster", {}).get("mana", 0) >= n
        if cond.startswith("target_count_above("):
            n = int(cond[len("target_count_above("):-1])
            return len(context.get("area_targets", [])) > n
        return True
