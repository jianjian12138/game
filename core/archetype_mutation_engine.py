"""
Archetype Mutation Engine (Deep-Well Archetype Cross-Breeding)
Inspired by Article 36 (Mihuan Workshop vs Sokpop):
Combines stable core game archetypes with targeted mechanic mutations
to reliably create breakthrough games without starting from scratch.
"""

from typing import Dict, Any, List, Optional
import json

class CoreArchetype:
    TOWER_DEFENSE = "TOWER_DEFENSE"
    ROGUELIKE = "ROGUELIKE"
    FACTORY_AUTOMATION = "FACTORY_AUTOMATION"
    PLATFORMER = "PLATFORMER"
    DECKBUILDER = "DECKBUILDER"

class MutationGene:
    ASYMMETRIC_INVERSION = "ASYMMETRIC_INVERSION"     # e.g. Haunted Dorm: player becomes the ghost/boss
    ROGUELIKE_DRAFT = "ROGUELIKE_DRAFT"               # e.g. Zhao Yun & A Dou: 3-choice synergies in TD
    CARD_STACKING = "CARD_STACKING"                   # e.g. Stacklands: card drag-and-drop crafting
    FACTORY_DEFENSE = "FACTORY_DEFENSE"               # e.g. Mindustry: production + wave defense
    TIME_DILATION_MOVE = "TIME_DILATION_MOVE"         # e.g. Superhot: time moves only when moving

class GameMutationSpec:
    def __init__(
        self,
        game_name: str,
        base_archetype: str,
        mutation_gene: str,
        core_hook: str,
        primary_loop: str,
        win_condition: str,
        loss_condition: str,
        target_ge_stage: str,
        expected_synergy: str
    ):
        self.game_name = game_name
        self.base_archetype = base_archetype
        self.mutation_gene = mutation_gene
        self.core_hook = core_hook
        self.primary_loop = primary_loop
        self.win_condition = win_condition
        self.loss_condition = loss_condition
        self.target_ge_stage = target_ge_stage
        self.expected_synergy = expected_synergy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_name": self.game_name,
            "base_archetype": self.base_archetype,
            "mutation_gene": self.mutation_gene,
            "core_hook": self.core_hook,
            "primary_loop": self.primary_loop,
            "win_condition": self.win_condition,
            "loss_condition": self.loss_condition,
            "target_ge_stage": self.target_ge_stage,
            "expected_synergy": self.expected_synergy,
        }

class ArchetypeMutationEngine:
    def __init__(self):
        self.archetypes = {
            CoreArchetype.TOWER_DEFENSE: {
                "base_verbs": ["place_turret", "upgrade_wall", "collect_gold"],
                "base_win": "survive_all_waves",
                "base_loss": "core_crystal_destroyed"
            },
            CoreArchetype.ROGUELIKE: {
                "base_verbs": ["explore_room", "attack_monster", "loot_chest"],
                "base_win": "defeat_floor_boss",
                "base_loss": "hero_hp_zero"
            },
            CoreArchetype.FACTORY_AUTOMATION: {
                "base_verbs": ["mine_ore", "place_conveyor", "craft_item"],
                "base_win": "launch_core_cargo",
                "base_loss": "production_deadlock"
            },
            CoreArchetype.PLATFORMER: {
                "base_verbs": ["run", "jump", "dash"],
                "base_win": "reach_level_flag",
                "base_loss": "fall_into_pit_or_hazard"
            },
            CoreArchetype.DECKBUILDER: {
                "base_verbs": ["draw_cards", "spend_energy", "end_turn"],
                "base_win": "clear_encounter",
                "base_loss": "deck_exhaust_or_hp_zero"
            }
        }

    def cross_breed(self, base: str, mutation: str, theme_name: str) -> GameMutationSpec:
        """Cross-breeds a base archetype with a mutation operator to generate a game spec."""
        if base not in self.archetypes:
            raise ValueError(f"Unknown archetype: {base}")

        if base == CoreArchetype.TOWER_DEFENSE and mutation == MutationGene.ASYMMETRIC_INVERSION:
            return GameMutationSpec(
                game_name=f"{theme_name} Asymmetric Inversion (Haunted Dorm style)",
                base_archetype=base,
                mutation_gene=mutation,
                core_hook="Player can astral-project into the nightmare monster to invade AI defenders.",
                primary_loop="Defend your bed chamber -> Earn dream coins -> Transform into nightmare monster to breach other dorms.",
                win_condition="Breach the final guardian dorm before dawn.",
                loss_condition="Bed chamber door breaks while player is in human form.",
                target_ge_stage="GE5",
                expected_synergy="Inverts the passive waiting of tower defense into proactive predator thrills."
            )

        elif base == CoreArchetype.TOWER_DEFENSE and mutation == MutationGene.ROGUELIKE_DRAFT:
            return GameMutationSpec(
                game_name=f"{theme_name} Roguelike TD (Zhao Yun style)",
                base_archetype=base,
                mutation_gene=mutation,
                core_hook="Each wave clear offers a 3-choice synergy card that mutates all deployed turrets.",
                primary_loop="Place historical general turrets -> Survive wave -> Draft synergistic blessing card (e.g. Thunder Chain).",
                win_condition="Escort convoy across 20 escalating battle waves.",
                loss_condition="Convoy carriage destroyed.",
                target_ge_stage="GE30",
                expected_synergy="Injects Roguelike build variance into rigid TD calculations, making each run unique."
            )

        elif base == CoreArchetype.FACTORY_AUTOMATION and mutation == MutationGene.FACTORY_DEFENSE:
            return GameMutationSpec(
                game_name=f"{theme_name} Factory Defense (Mindustry style)",
                base_archetype=base,
                mutation_gene=mutation,
                core_hook="Conveyor belts transport ammunition directly into defense turrets under wave assault.",
                primary_loop="Mine copper & lead -> Route ammo lines to turrets -> Repel incoming air & ground swarms -> Expand factory.",
                win_condition="Secure sector core and launch expedition rocket.",
                loss_condition="Core base structure destroyed by enemy wave.",
                target_ge_stage="GE180",
                expected_synergy="Adds high-stakes survival urgency to traditional peaceful logistics automation."
            )

        elif base == CoreArchetype.DECKBUILDER and mutation == MutationGene.CARD_STACKING:
            return GameMutationSpec(
                game_name=f"{theme_name} Card Stacking Sandbox (Stacklands style)",
                base_archetype=base,
                mutation_gene=mutation,
                core_hook="Cards are physical objects on a table; stacking card A on card B crafts card C over time.",
                primary_loop="Drag villager onto berry bush -> Harvest food -> Stack wood + stone to craft hut -> Feed villagers.",
                win_condition="Defeat the summoned dark portal demon.",
                loss_condition="All villagers starve at month end.",
                target_ge_stage="GE_T60",
                expected_synergy="Turns abstract turn-based deck manipulation into intuitive tactile toy play."
            )

        else:
            # Universal fallback combination
            base_info = self.archetypes[base]
            return GameMutationSpec(
                game_name=f"{theme_name} Hybrid",
                base_archetype=base,
                mutation_gene=mutation,
                core_hook=f"Infuses {mutation} mechanics into core {base} loop.",
                primary_loop=f"Execute {', '.join(base_info['base_verbs'])} with mutated parameters.",
                win_condition=base_info["base_win"],
                loss_condition=base_info["base_loss"],
                target_ge_stage="GE30",
                expected_synergy=f"Combines {base} stability with {mutation} surprise."
            )
