"""
Card Roguelike (Spire-like) Archetype Engine
Combines CardDeckPart, CardHandPart, CardBattleFieldPart, CardEffectPart,
SynergyPart, RoomGenPart, and CardEffectDSL into a playable card roguelike game loop.
"""

from typing import Dict, List, Any, Optional
from core.ford_t_game_parts_hub import (
    ModularGameAssembler,
    CardDeckPart, CardHandPart, CardBattleFieldPart, CardEffectPart, CardAIPart,
    SynergyPart, RoomGenPart, LootTablePart
)


class CardRoguelikeGame:
    """Manages a complete run of Card Roguelike with floor progression, deck building and combat."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.assembler = ModularGameAssembler()
        self.game_info = self.assembler.assemble(
            title="SpireAscent",
            selected_part_keys=[
                "card_deck", "card_hand", "card_battlefield", "card_effect",
                "card_ai", "synergy", "room_gen", "loot_table"
            ]
        )

        self.deck_part: CardDeckPart = self.assembler.catalog["card_deck"]
        self.hand_part: CardHandPart = self.assembler.catalog["card_hand"]
        self.battle_part: CardBattleFieldPart = self.assembler.catalog["card_battlefield"]
        self.effect_part: CardEffectPart = self.assembler.catalog["card_effect"]
        self.ai_part: CardAIPart = self.assembler.catalog["card_ai"]
        self.synergy_part: SynergyPart = self.assembler.catalog["synergy"]
        self.room_part: RoomGenPart = self.assembler.catalog["room_gen"]
        self.loot_part: LootTablePart = self.assembler.catalog["loot_table"]

        self.player_hp = 60
        self.player_max_hp = 60
        self.player_shield = 0

        self.current_floor = 1
        self.current_room_index = 0
        self.dungeon_map: List[Dict[str, Any]] = []

        self.active_enemy: Dict[str, Any] = {"name": "Slime", "hp": 30, "max_hp": 30, "intent": "ATTACK", "intent_val": 8}
        self.is_combat_active = False

        self._setup_synergy_rules()
        self._init_starter_deck()
        self.generate_dungeon()

    def _setup_synergy_rules(self):
        self.synergy_part.execute("REGISTER_RULE", {
            "tag": "fire",
            "thresholds": [{"count": 2, "effect": "BURN_30_PCT"}, {"count": 4, "effect": "INFERNO_EXPLOSION"}]
        })
        self.synergy_part.execute("REGISTER_RULE", {
            "tag": "block",
            "thresholds": [{"count": 2, "effect": "SHIELD_WALL_10"}]
        })

    def _init_starter_deck(self):
        starter_cards = [
            {"id": "c_strike_1", "name": "Strike", "cost": 1, "value": 6, "type": "DAMAGE", "tags": ["blade"]},
            {"id": "c_strike_2", "name": "Strike", "cost": 1, "value": 6, "type": "DAMAGE", "tags": ["blade"]},
            {"id": "c_strike_3", "name": "Strike", "cost": 1, "value": 6, "type": "DAMAGE", "tags": ["blade"]},
            {"id": "c_defend_1", "name": "Defend", "cost": 1, "value": 5, "type": "SHIELD", "tags": ["block"]},
            {"id": "c_defend_2", "name": "Defend", "cost": 1, "value": 5, "type": "SHIELD", "tags": ["block"]},
            {"id": "c_ignite",   "name": "Ignite", "cost": 2, "value": 14, "type": "DAMAGE", "tags": ["fire"]},
        ]
        self.deck_part.execute("INIT_DECK", {"cards": starter_cards, "shuffle": True})
        for c in starter_cards:
            self.synergy_part.execute("ADD_ITEM", {"item_id": c["id"], "tags": c.get("tags", [])})

    def generate_dungeon(self):
        res = self.room_part.execute("GENERATE_DUNGEON", {"room_count": 6, "seed": self.seed})
        self.dungeon_map = res.data.get("rooms", [])
        self.current_room_index = 0

    def start_combat(self, enemy_name: str = "Goblin Warrior", enemy_hp: int = 35):
        self.is_combat_active = True
        self.active_enemy = {
            "name": enemy_name,
            "hp": enemy_hp,
            "max_hp": enemy_hp,
            "shield": 0,
            "intent": "ATTACK",
            "intent_val": 7
        }
        self.player_shield = 0
        self.start_player_turn()

    def start_player_turn(self):
        # 1. Reset shield
        self.player_shield = 0
        # 2. Advance battlefield mana
        self.battle_part.execute("START_TURN", {"side": "player"})
        # 3. Draw 4 cards into hand
        draw_res = self.deck_part.execute("DRAW", {"count": 4})
        drawn = draw_res.data.get("drawn", [])
        self.hand_part.execute("ADD_CARDS", {"cards": drawn})

    def play_card(self, card_id: str) -> Dict[str, Any]:
        """Player plays a card from hand."""
        if not self.is_combat_active:
            return {"success": False, "error": "NOT_IN_COMBAT"}

        # Find card in hand
        hand_res = self.hand_part.execute("GET_HAND", {})
        hand = hand_res.data.get("hand", [])
        chosen = next((c for c in hand if c["id"] == card_id), None)
        if not chosen:
            return {"success": False, "error": "CARD_NOT_IN_HAND"}

        cost = chosen.get("cost", 1)
        # Check and spend mana
        spend_res = self.battle_part.execute("SPEND_MANA", {"side": "player", "cost": cost})
        if not spend_res.success:
            return {"success": False, "error": "INSUFFICIENT_MANA"}

        # Remove from hand and send to discard
        self.hand_part.execute("PLAY_CARD", {"card_id": card_id})
        self.deck_part.execute("DISCARD", {"cards": [chosen]})

        # Execute effect
        c_type = chosen.get("type", "DAMAGE")
        val = chosen.get("value", 5)

        # Check synergy bonus
        syn_res = self.synergy_part.execute("EVALUATE_SYNERGIES", {})
        bonuses = syn_res.data.get("active_bonuses", [])
        if any(b["tag"] == "fire" for b in bonuses) and "fire" in chosen.get("tags", []):
            val = int(round(val * 1.3))

        result_event = ""
        if c_type == "DAMAGE":
            res_eff = self.effect_part.execute("EXECUTE_EFFECT", {
                "type": "DAMAGE", "value": val,
                "target": {"hp": self.active_enemy["hp"], "shield": self.active_enemy["shield"]}
            })
            self.active_enemy["hp"] = res_eff.data["target_hp"]
            self.active_enemy["shield"] = res_eff.data["target_shield"]
            result_event = f"Dealt {val} damage to {self.active_enemy['name']}"
            if self.active_enemy["hp"] <= 0:
                self.is_combat_active = False
                result_event += f" — {self.active_enemy['name']} defeated!"

        elif c_type == "SHIELD":
            self.player_shield += val
            result_event = f"Gained {val} Shield"

        return {
            "success": True,
            "card_name": chosen["name"],
            "event": result_event,
            "enemy_hp": self.active_enemy["hp"],
            "player_shield": self.player_shield,
            "combat_won": not self.is_combat_active and self.active_enemy["hp"] <= 0
        }

    def end_turn(self) -> Dict[str, Any]:
        """Player ends turn, enemy takes intent action."""
        if not self.is_combat_active:
            return {"success": False, "error": "NOT_IN_COMBAT"}

        # Discard remaining hand
        self.hand_part.execute("DISCARD_HAND", {})

        # Enemy Action
        action_msg = ""
        if self.active_enemy["intent"] == "ATTACK":
            dmg = self.active_enemy["intent_val"]
            absorbed = min(self.player_shield, dmg)
            self.player_shield -= absorbed
            rem_dmg = dmg - absorbed
            self.player_hp = max(0, self.player_hp - rem_dmg)
            action_msg = f"{self.active_enemy['name']} attacked for {dmg} damage (absorbed {absorbed}, took {rem_dmg})"
            if self.player_hp <= 0:
                self.is_combat_active = False
                return {"success": True, "player_dead": True, "message": "PLAYER_DEFEATED"}

        # Start next player turn
        self.start_player_turn()

        return {
            "success": True,
            "enemy_action": action_msg,
            "player_hp": self.player_hp,
            "player_shield": self.player_shield,
            "player_dead": False
        }
