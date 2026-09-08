"""
Bullet Pattern DSL — 弹幕模式方言（BulletML风格）
===================================================
用数据驱动方式描述弹幕发射模式，无需硬编码。

YAML 示例::

    id: spiral_wave
    name: 螺旋波
    pattern:
      - type: fire
        count: 12
        spread: 360       # 全向均匀分布
        speed: 4.0
        bullet:
          sprite: bullet_red
          damage: 1
          lifetime: 5.0
      - type: wait
        frames: 20
      - type: fire
        count: 8
        spread: 360
        offset_angle: 15  # 旋转偏移
        speed: 3.0
        bullet:
          sprite: bullet_blue
          damage: 2
          lifetime: 4.0
      - type: repeat
        times: 6
        target: spiral_wave   # 递归模式（引用自身）
"""

import math


class BulletPatternDSL:
    """弹幕模式方言：展开发射指令序列为帧事件流。"""

    VALID_STEP_TYPES = {
        "fire",      # 发射一批子弹
        "wait",      # 等待若干帧
        "aim",       # 瞄准目标方向
        "rotate",    # 旋转发射方向
        "repeat",    # 重复整个序列
        "branch",    # 条件分支
    }

    def preprocess(self, raw: dict) -> dict:
        """展开弹幕模式为规范化步骤列表。"""
        raw.setdefault("loop", False)       # 是否循环发射
        raw.setdefault("start_delay", 0)    # 首发延迟帧数
        raw.setdefault("global_speed", 1.0) # 全局速度缩放

        for step in raw.get("pattern", []):
            step.setdefault("type", "fire")
            if step["type"] == "fire":
                self._preprocess_fire_step(step)
            elif step["type"] == "wait":
                step.setdefault("frames", 10)

        return raw

    def _preprocess_fire_step(self, step: dict):
        """为 fire 步骤填充默认值并展开角度分布。"""
        step.setdefault("count", 1)
        step.setdefault("spread", 0)          # 0=单发，360=全向
        step.setdefault("speed", 3.0)
        step.setdefault("offset_angle", 0)
        step.setdefault("aimed", False)       # 是否瞄准玩家
        bullet = step.setdefault("bullet", {})
        bullet.setdefault("sprite", "bullet_default")
        bullet.setdefault("damage", 1)
        bullet.setdefault("lifetime", 4.0)
        bullet.setdefault("tags", [])

        # 预计算每颗子弹的角度偏移（均匀分布）
        count = step["count"]
        spread = step["spread"]
        offset = step["offset_angle"]
        if count == 1:
            step["_angles"] = [offset]
        elif spread == 0:
            step["_angles"] = [offset] * count
        else:
            step["_angles"] = [
                offset + spread * i / count for i in range(count)
            ]

    def validate(self, ast: dict) -> list[str]:
        errors = []
        pattern = ast.get("pattern", [])
        if not isinstance(pattern, list):
            errors.append("'pattern' 必须是列表")
            return errors
        for i, step in enumerate(pattern):
            stype = step.get("type", "fire")
            if stype not in self.VALID_STEP_TYPES:
                errors.append(f"pattern[{i}].type 无效: '{stype}'")
            if stype == "fire":
                count = step.get("count", 1)
                if not isinstance(count, int) or count < 1 or count > 360:
                    errors.append(f"pattern[{i}].count 必须是 1–360 整数")
        return errors

    def eval_condition(self, cond: str, context: dict) -> bool:
        """弹幕条件：boss_phase_above(N) / player_distance_below(N)"""
        if cond.startswith("boss_phase_above("):
            n = int(cond[len("boss_phase_above("):-1])
            return context.get("boss_phase", 1) > n
        if cond.startswith("player_distance_below("):
            n = float(cond[len("player_distance_below("):-1])
            return context.get("player_distance", 999) < n
        return True
