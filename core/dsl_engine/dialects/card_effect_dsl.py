"""
Card Effect DSL — 卡牌效果方言
================================
扩展通用 DSL 引擎，支持卡牌专属语法糖：
  - cost: 法力消耗
  - rarity: 稀有度
  - card_type: 法术/随从/武器
  - 自动填充 target 默认值

YAML 示例::

    id: fireball
    name: 火球术
    cost: 3
    rarity: common
    card_type: spell
    effect:
      - type: damage
        target: enemy_single
        value: 6
      - type: damage
        target: enemy_adjacent
        value: 2
        condition: target_has_tag(burn)

    id: water_elemental
    name: 水元素
    cost: 4
    card_type: minion
    stats: {atk: 3, hp: 6}
    ability:
      - on_play:
          - type: debuff
            target: enemy_single
            stat: spd
            value: -1
            duration: 2
"""


class CardEffectDSL:
    """卡牌效果方言：预处理、校验、条件扩展。"""

    VALID_CARD_TYPES = {"spell", "minion", "weapon", "secret", "hero_power"}
    VALID_RARITIES = {"common", "rare", "epic", "legendary"}

    # ------------------------------------------------------------------
    # 预处理：语法糖展开
    # ------------------------------------------------------------------

    def preprocess(self, raw: dict) -> dict:
        """展开卡牌专属语法糖，填充默认值。"""
        # 默认值
        raw.setdefault("cost", 0)
        raw.setdefault("rarity", "common")
        raw.setdefault("card_type", "spell")
        raw.setdefault("tags", [])

        # 随从牌：展开 ability → effect
        if raw.get("card_type") == "minion":
            raw = self._expand_minion_ability(raw)

        # effect 列表中每个 damage/heal 填充默认 target
        for effect in raw.get("effect", []) or []:
            if effect.get("type") in ("damage", "debuff"):
                effect.setdefault("target", "enemy_single")
            elif effect.get("type") in ("heal", "buff"):
                effect.setdefault("target", "self")

        return raw

    def _expand_minion_ability(self, raw: dict) -> dict:
        """将 ability.on_play 展开为 effect 列表。"""
        ability = raw.pop("ability", None)
        if not ability:
            return raw
        effects = raw.setdefault("effect", [])
        for trigger_block in ability:
            if "on_play" in trigger_block:
                for e in trigger_block["on_play"]:
                    e["_trigger"] = "on_play"
                    effects.append(e)
        return raw

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------

    def validate(self, ast: dict) -> list[str]:
        errors = []
        ct = ast.get("card_type", "spell")
        if ct not in self.VALID_CARD_TYPES:
            errors.append(f"无效的 card_type: '{ct}'，合法值: {self.VALID_CARD_TYPES}")
        rarity = ast.get("rarity", "common")
        if rarity not in self.VALID_RARITIES:
            errors.append(f"无效的 rarity: '{rarity}'，合法值: {self.VALID_RARITIES}")
        cost = ast.get("cost", 0)
        if not isinstance(cost, int) or cost < 0 or cost > 20:
            errors.append(f"cost 必须是 0–20 的整数，实际: {cost}")
        return errors

    # ------------------------------------------------------------------
    # 条件扩展
    # ------------------------------------------------------------------

    def eval_condition(self, cond: str, context: dict) -> bool:
        """卡牌专属条件。"""
        # hand_size_above(N)
        if cond.startswith("hand_size_above("):
            n = int(cond[len("hand_size_above("):-1])
            return len(context.get("hand", [])) > n
        # board_count_below(N)
        if cond.startswith("board_count_below("):
            n = int(cond[len("board_count_below("):-1])
            return len(context.get("board", [])) < n
        # opponent_hp_below(N)
        if cond.startswith("opponent_hp_below("):
            n = int(cond[len("opponent_hp_below("):-1])
            return context.get("opponent", {}).get("hp", 30) < n
        return True
