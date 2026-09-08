"""
Universal Ford T-Assembly High-Precision Game Parts Hub (Article 46 - Elseland Architecture)
Decouples game development into pre-validated, high-polish code components ("Parts")
and an automated assembly pipeline.

Parts Library:
1. SlingshotPhysicsPart (Angry Birds / Fruit Frenzy projectile trajectory & bounce)
2. MergeTwoPart (Merge-2 grid crafting & item evolution)
3. RunnerStackPart (Subway Surfers / Capybara companion stacking)
4. ClueInvestigationPart (Detective mystery evidence contradiction arbitration)
5. GachaStorePart (Store inventory, currency economy & pity gacha pull)
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class PartActionResponse:
    success: bool
    event_name: str
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


class GamePartBase:
    def __init__(self, part_id: str, name: str, category: str):
        self.part_id = part_id
        self.name = name
        self.category = category
        self.dependencies: List[str] = []

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        raise NotImplementedError


class SlingshotPhysicsPart(GamePartBase):
    """Handles projectile trajectories, elasticity, and splash damage."""
    def __init__(self):
        super().__init__("part_slingshot", "SlingshotPhysics", "CORE_MECHANIC")
        self.max_pull_dist = 80.0
        self.launch_speed_factor = 7.5
        self.gravity = 9.8

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "FIRE_PROJECTILE":
            pull_x = params.get("pull_x", 0.0)
            pull_y = params.get("pull_y", 0.0)
            dist = math.hypot(pull_x, pull_y)
            clamped_dist = min(dist, self.max_pull_dist)
            angle = math.atan2(-pull_y, -pull_x)
            velocity = clamped_dist * self.launch_speed_factor
            vx = math.cos(angle) * velocity
            vy = math.sin(angle) * velocity
            
            # Predict 5 trajectory points
            trajectory = []
            for t in [0.1, 0.2, 0.3, 0.4, 0.5]:
                px = vx * t
                py = vy * t + 0.5 * self.gravity * 80.0 * (t ** 2)
                trajectory.append((round(px, 1), round(py, 1)))

            return PartActionResponse(
                success=True,
                event_name="PROJECTILE_LAUNCHED",
                data={"vx": round(vx, 2), "vy": round(vy, 2), "trajectory": trajectory},
                message=f"Fired with velocity {velocity:.1f} at angle {math.degrees(angle):.1f}°"
            )
        return PartActionResponse(False, "UNKNOWN_ACTION")


class MergeTwoPart(GamePartBase):
    """Handles 2D grid item merging and level upgrades."""
    def __init__(self, grid_size: int = 4):
        super().__init__("part_merge_two", "MergeTwo", "CORE_MECHANIC")
        self.grid_size = grid_size
        self.grid: Dict[Tuple[int, int], int] = {}  # (r, c) -> item_level
        self._init_grid()

    def _init_grid(self):
        # Spawn two level-1 items
        self.grid[(0, 0)] = 1
        self.grid[(0, 1)] = 1

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "MERGE_ITEMS":
            src = tuple(params.get("src", (0, 0)))
            dst = tuple(params.get("dst", (0, 1)))
            if src not in self.grid or dst not in self.grid:
                return PartActionResponse(False, "MERGE_FAILED", message="Empty source or destination slot")
            if src == dst:
                return PartActionResponse(False, "MERGE_FAILED", message="Cannot merge same slot")

            src_lvl = self.grid[src]
            dst_lvl = self.grid[dst]
            if src_lvl == dst_lvl:
                # Merge into higher level
                new_lvl = dst_lvl + 1
                del self.grid[src]
                self.grid[dst] = new_lvl
                return PartActionResponse(
                    success=True,
                    event_name="ITEMS_MERGED",
                    data={"new_level": new_lvl, "target_slot": dst},
                    message=f"Merged two Lv.{src_lvl} items into Lv.{new_lvl}!"
                )
            else:
                return PartActionResponse(False, "MERGE_MISMATCH", message=f"Cannot merge Lv.{src_lvl} with Lv.{dst_lvl}")
        return PartActionResponse(False, "UNKNOWN_ACTION")


class RunnerStackPart(GamePartBase):
    """Handles running distance, companion pickups, and vertical stack height."""
    def __init__(self):
        super().__init__("part_runner_stack", "RunnerStack", "CORE_MECHANIC")
        self.distance_traveled = 0.0
        self.stack_count = 1  # starts with 1 hero

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "COLLECT_COMPANION":
            count = params.get("count", 1)
            self.stack_count += count
            return PartActionResponse(
                success=True,
                event_name="COMPANION_STACKED",
                data={"current_stack": self.stack_count},
                message=f"Collected companion! Stack height increased to {self.stack_count}"
            )
        elif action == "HIT_HURDLE":
            lost = params.get("penalty", 2)
            self.stack_count = max(0, self.stack_count - lost)
            event = "STACK_COLLAPSED" if self.stack_count == 0 else "COMPANIONS_LOST"
            return PartActionResponse(
                success=True,
                event_name=event,
                data={"remaining_stack": self.stack_count},
                message=f"Hit hurdle! Lost {lost} companions. Remaining: {self.stack_count}"
            )
        return PartActionResponse(False, "UNKNOWN_ACTION")


class ClueInvestigationPart(GamePartBase):
    """Handles detective evidence collection, contradictions, and truth deduction."""
    def __init__(self):
        super().__init__("part_clue_investigation", "ClueInvestigation", "NARRATIVE")
        self.collected_clues: Dict[str, str] = {}
        self.contradictions = {
            ("clue_alibi_inn", "clue_bloody_token"): "Suspect claimed he never left the inn, but his unique token was found at the crime scene!"
        }

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "ADD_CLUE":
            cid = params["clue_id"]
            desc = params["description"]
            self.collected_clues[cid] = desc
            return PartActionResponse(True, "CLUE_FOUND", {"clue_id": cid}, f"Discovered clue: {desc}")
        elif action == "CONFRONT_CONTRADICTION":
            c1 = params.get("clue_1")
            c2 = params.get("clue_2")
            pair = (c1, c2) if (c1, c2) in self.contradictions else (c2, c1)
            if pair in self.contradictions:
                reveal = self.contradictions[pair]
                return PartActionResponse(
                    success=True,
                    event_name="CONTRADICTION_PROVEN",
                    data={"revelation": reveal},
                    message=f"Contradiction exposed! {reveal}"
                )
            else:
                return PartActionResponse(False, "NO_CONTRADICTION", message="These clues do not contradict each other")
        return PartActionResponse(False, "UNKNOWN_ACTION")


class NarrativePedagogyPart(GamePartBase):
    """
    Article 48 - Seth Hudson GDC Narrative Pedagogy Framework:
    Implements 5 Functional Competencies (Fun-Comps), 3-Role dynamic pipeline
    (Wordsmith -> Sensemaker -> Advocate), SLO quality metric audits,
    and legacy handoff healing.
    """
    def __init__(self):
        super().__init__("part_narrative_pedagogy", "NarrativePedagogy", "NARRATIVE")
        from core.narrative_pedagogy_engine import (
            SLOMetricEvaluator,
            ThreeRoleNarrativePipeline,
            LegacyNarrativeHealer
        )
        self.evaluator = SLOMetricEvaluator()
        self.pipeline = ThreeRoleNarrativePipeline(self.evaluator)
        self.healer = LegacyNarrativeHealer(self.evaluator)

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "AUDIT_SLO":
            nodes = params.get("nodes", {})
            start_id = params.get("start_id", "start")
            report = self.evaluator.audit(nodes, start_id)
            return PartActionResponse(
                success=report["compliant"],
                event_name="SLO_AUDITED",
                data=report,
                message=f"SLO Audit completed. Score: {report['overall_score']} (Compliant: {report['compliant']})"
            )
        elif action == "PROCESS_DRAFT":
            draft = params.get("draft", {})
            start_id = params.get("start_id", "start")
            context = params.get("context", {})
            processed, report = self.pipeline.process(draft, start_id, context)
            return PartActionResponse(
                success=True,
                event_name="DRAFT_PROCESSED",
                data={"nodes": processed, "audit": report},
                message=f"Draft processed across Wordsmith, Sensemaker, and Advocate. Compliant: {report['compliant']}"
            )
        elif action == "HEAL_LEGACY":
            broken = params.get("broken_nodes", {})
            start_id = params.get("start_id", "start")
            healed, report = self.healer.heal(broken, start_id)
            return PartActionResponse(
                success=report["final_audit"]["compliant"],
                event_name="LEGACY_HEALED",
                data={"nodes": healed, "report": report},
                message=f"Legacy healed: {report['repaired_dead_ends']} dead ends, {report['stitched_orphans']} orphans stitched."
            )
        return PartActionResponse(False, "UNKNOWN_ACTION")



class GachaStorePart(GamePartBase):
    """Handles inventory store and pity gacha pulls."""
    def __init__(self):
        super().__init__("part_gacha_store", "GachaStore", "SYSTEM")
        self.gold = 500
        self.pity_counter = 0

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "PULL_GACHA":
            cost = 100
            if self.gold < cost:
                return PartActionResponse(False, "INSUFFICIENT_FUNDS", message="Not enough gold for gacha pull")
            self.gold -= cost
            self.pity_counter += 1

            if self.pity_counter >= 10:
                self.pity_counter = 0
                item = "LEGENDARY_PHOENIX_SWORD"
                tier = "SSR"
            else:
                roll = random.random()
                if roll < 0.15:
                    item = "RARE_SILVER_SHIELD"
                    tier = "SR"
                else:
                    item = "COMMON_WOODEN_WAND"
                    tier = "R"

            return PartActionResponse(
                success=True,
                event_name="GACHA_PULLED",
                data={"item": item, "tier": tier, "remaining_gold": self.gold, "pity": self.pity_counter},
                message=f"Pulled [{tier}] {item}! Gold left: {self.gold}"
            )
        return PartActionResponse(False, "UNKNOWN_ACTION")


# =====================================================================
# 1. CARD GAME PARTS (卡牌品类零件)
# =====================================================================

class CardDeckPart(GamePartBase):
    """Manages draw pile, discard pile, exhaust pile, shuffle and card draw."""
    def __init__(self):
        super().__init__("part_card_deck", "CardDeck", "CARD")
        self.draw_pile: List[Dict[str, Any]] = []
        self.discard_pile: List[Dict[str, Any]] = []
        self.exhaust_pile: List[Dict[str, Any]] = []

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "INIT_DECK":
            cards = params.get("cards", [])
            self.draw_pile = [dict(c) for c in cards]
            self.discard_pile.clear()
            self.exhaust_pile.clear()
            if params.get("shuffle", True):
                random.shuffle(self.draw_pile)
            return PartActionResponse(True, "DECK_INITIALIZED", {"total": len(self.draw_pile)})

        elif action == "SHUFFLE":
            random.shuffle(self.draw_pile)
            return PartActionResponse(True, "DECK_SHUFFLED", {"draw_count": len(self.draw_pile)})

        elif action == "DRAW":
            count = params.get("count", 1)
            drawn = []
            for _ in range(count):
                if not self.draw_pile:
                    if self.discard_pile:
                        self.draw_pile = list(self.discard_pile)
                        self.discard_pile.clear()
                        random.shuffle(self.draw_pile)
                    else:
                        break
                if self.draw_pile:
                    drawn.append(self.draw_pile.pop())
            return PartActionResponse(True, "CARDS_DRAWN", {"drawn": drawn, "remaining": len(self.draw_pile)})

        elif action == "DISCARD":
            cards = params.get("cards", [])
            for c in cards:
                self.discard_pile.append(dict(c))
            return PartActionResponse(True, "CARDS_DISCARDED", {"discard_count": len(self.discard_pile)})

        elif action == "EXHAUST":
            cards = params.get("cards", [])
            for c in cards:
                self.exhaust_pile.append(dict(c))
            return PartActionResponse(True, "CARDS_EXHAUSTED", {"exhaust_count": len(self.exhaust_pile)})

        elif action == "PEEK":
            count = min(params.get("count", 1), len(self.draw_pile))
            peeked = self.draw_pile[-count:] if count > 0 else []
            return PartActionResponse(True, "DECK_PEEKED", {"cards": list(reversed(peeked))})

        elif action == "GET_COUNTS":
            return PartActionResponse(True, "COUNTS_RETRIEVED", {
                "draw": len(self.draw_pile),
                "discard": len(self.discard_pile),
                "exhaust": len(self.exhaust_pile)
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class CardHandPart(GamePartBase):
    """Manages player hand, card limits, playing cards and selection."""
    def __init__(self, max_hand_size: int = 10):
        super().__init__("part_card_hand", "CardHand", "CARD")
        self.max_hand_size = max_hand_size
        self.hand: List[Dict[str, Any]] = []

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "ADD_CARDS":
            incoming = params.get("cards", [])
            added = []
            overflow = []
            for c in incoming:
                if len(self.hand) < self.max_hand_size:
                    self.hand.append(dict(c))
                    added.append(c)
                else:
                    overflow.append(c)
            return PartActionResponse(True, "CARDS_ADDED_TO_HAND", {
                "added": added,
                "overflow": overflow,
                "hand_size": len(self.hand)
            })

        elif action == "PLAY_CARD":
            card_id = params.get("card_id")
            for idx, c in enumerate(self.hand):
                if c.get("id") == card_id:
                    played = self.hand.pop(idx)
                    return PartActionResponse(True, "CARD_PLAYED", {"card": played, "hand_size": len(self.hand)})
            return PartActionResponse(False, "CARD_NOT_IN_HAND", message=f"Card {card_id} not found in hand")

        elif action == "DISCARD_HAND":
            discarded = list(self.hand)
            self.hand.clear()
            return PartActionResponse(True, "HAND_DISCARDED", {"discarded": discarded})

        elif action == "GET_HAND":
            return PartActionResponse(True, "HAND_RETRIEVED", {"hand": list(self.hand), "count": len(self.hand)})

        return PartActionResponse(False, "UNKNOWN_ACTION")


class CardBattleFieldPart(GamePartBase):
    """Manages turn phases, mana/energy pools, and minion field slots."""
    def __init__(self, max_slots: int = 5):
        super().__init__("part_card_battlefield", "CardBattleField", "CARD")
        self.turn = 1
        self.phase = "PLAYER_TURN"
        self.max_slots = max_slots
        self.player_mana = 1
        self.player_max_mana = 1
        self.enemy_mana = 1
        self.enemy_max_mana = 1
        self.player_slots: List[Optional[Dict[str, Any]]] = [None] * max_slots
        self.enemy_slots: List[Optional[Dict[str, Any]]] = [None] * max_slots

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "START_TURN":
            side = params.get("side", "player")
            if side == "player":
                self.player_max_mana = min(10, self.player_max_mana + 1)
                self.player_mana = self.player_max_mana
                self.phase = "PLAYER_TURN"
            else:
                self.enemy_max_mana = min(10, self.enemy_max_mana + 1)
                self.enemy_mana = self.enemy_max_mana
                self.phase = "ENEMY_TURN"
            return PartActionResponse(True, "TURN_STARTED", {
                "turn": self.turn, "side": side,
                "mana": self.player_mana if side == "player" else self.enemy_mana
            })

        elif action == "SPEND_MANA":
            side = params.get("side", "player")
            cost = params.get("cost", 0)
            cur = self.player_mana if side == "player" else self.enemy_mana
            if cur < cost:
                return PartActionResponse(False, "INSUFFICIENT_MANA", message=f"Need {cost} mana, have {cur}")
            if side == "player":
                self.player_mana -= cost
            else:
                self.enemy_mana -= cost
            return PartActionResponse(True, "MANA_SPENT", {"remaining": self.player_mana if side == "player" else self.enemy_mana})

        elif action == "SUMMON_MINION":
            side = params.get("side", "player")
            slot = params.get("slot", 0)
            slots = self.player_slots if side == "player" else self.enemy_slots
            if slot < 0 or slot >= self.max_slots:
                return PartActionResponse(False, "INVALID_SLOT")
            if slots[slot] is not None:
                return PartActionResponse(False, "SLOT_OCCUPIED")
            minion = dict(params.get("minion", {}))
            slots[slot] = minion
            return PartActionResponse(True, "MINION_SUMMONED", {"side": side, "slot": slot, "minion": minion})

        elif action == "KILL_MINION":
            side = params.get("side", "player")
            slot = params.get("slot", 0)
            slots = self.player_slots if side == "player" else self.enemy_slots
            if 0 <= slot < self.max_slots and slots[slot] is not None:
                dead = slots[slot]
                slots[slot] = None
                return PartActionResponse(True, "MINION_DIED", {"side": side, "slot": slot, "minion": dead})
            return PartActionResponse(False, "SLOT_EMPTY")

        elif action == "GET_BOARD_STATE":
            return PartActionResponse(True, "BOARD_STATE", {
                "turn": self.turn,
                "phase": self.phase,
                "player_mana": self.player_mana,
                "player_max_mana": self.player_max_mana,
                "player_slots": self.player_slots,
                "enemy_slots": self.enemy_slots
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class CardEffectPart(GamePartBase):
    """Executes card effects: Damage, Shield, Heal, Draw, and Buffs."""
    def __init__(self):
        super().__init__("part_card_effect", "CardEffect", "CARD")

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "EXECUTE_EFFECT":
            eff_type = params.get("type", "DAMAGE")
            val = params.get("value", 0)
            target = dict(params.get("target", {"hp": 30, "shield": 0}))

            if eff_type == "DAMAGE":
                shield = target.get("shield", 0)
                hp = target.get("hp", 0)
                absorbed = min(shield, val)
                rem_dmg = val - absorbed
                target["shield"] = shield - absorbed
                target["hp"] = max(0, hp - rem_dmg)
                return PartActionResponse(True, "DAMAGE_RESOLVED", {
                    "damage_dealt": val,
                    "absorbed": absorbed,
                    "target_hp": target["hp"],
                    "target_shield": target["shield"],
                    "is_dead": target["hp"] <= 0
                })

            elif eff_type == "SHIELD":
                target["shield"] = target.get("shield", 0) + val
                return PartActionResponse(True, "SHIELD_RESOLVED", {"new_shield": target["shield"]})

            elif eff_type == "HEAL":
                max_hp = params.get("max_hp", 30)
                target["hp"] = min(max_hp, target.get("hp", 0) + val)
                return PartActionResponse(True, "HEAL_RESOLVED", {"new_hp": target["hp"]})

            elif eff_type == "BUFF":
                stat = params.get("stat", "attack")
                return PartActionResponse(True, "BUFF_APPLIED", {"stat": stat, "bonus": val})

        return PartActionResponse(False, "UNKNOWN_ACTION")


class CardAIPart(GamePartBase):
    """Heuristic card AI that selects highest-value playable moves given mana constraints."""
    def __init__(self):
        super().__init__("part_card_ai", "CardAI", "CARD")

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "DECIDE_ACTION":
            hand = params.get("hand", [])
            mana = params.get("mana", 0)
            # Find all playable cards
            playable = [c for c in hand if c.get("cost", 0) <= mana]
            if not playable:
                return PartActionResponse(True, "ACTION_DECIDED", {"action": "END_TURN", "card": None})

            # Sort by highest cost/power heuristic
            playable.sort(key=lambda c: (c.get("value", 0) * 1.5 + c.get("cost", 0)), reverse=True)
            chosen = playable[0]
            target_side = "enemy" if chosen.get("type") in ["DAMAGE", "DEBUFF"] else "ally"
            return PartActionResponse(True, "ACTION_DECIDED", {
                "action": "PLAY_CARD",
                "card": chosen,
                "target_side": target_side,
                "mana_remaining": mana - chosen.get("cost", 0)
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


# =====================================================================
# 2. RHYTHM GAME PARTS (音游品类零件)
# =====================================================================

class ChartParserPart(GamePartBase):
    """Loads and indexes rhythm game chart notes, BPM metadata, and timestamps."""
    def __init__(self):
        super().__init__("part_chart_parser", "ChartParser", "RHYTHM")
        self.bpm = 120.0
        self.offset_ms = 0.0
        self.notes: List[Dict[str, Any]] = []

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "LOAD_CHART":
            self.bpm = float(params.get("bpm", 120.0))
            self.offset_ms = float(params.get("offset_ms", 0.0))
            raw_notes = params.get("notes", [])
            self.notes = []
            for idx, n in enumerate(raw_notes):
                note = {
                    "id": n.get("id", f"note_{idx}"),
                    "lane": int(n.get("lane", 0)),
                    "time_ms": float(n.get("time_ms", 0.0)),
                    "type": n.get("type", "TAP"),
                    "duration_ms": float(n.get("duration_ms", 0.0))
                }
                self.notes.append(note)
            self.notes.sort(key=lambda x: x["time_ms"])
            return PartActionResponse(True, "CHART_LOADED", {"bpm": self.bpm, "total_notes": len(self.notes)})

        elif action == "GET_NOTES_IN_WINDOW":
            start_ms = float(params.get("start_ms", 0.0))
            end_ms = float(params.get("end_ms", 1000.0))
            matched = [n for n in self.notes if start_ms <= n["time_ms"] <= end_ms]
            return PartActionResponse(True, "NOTES_WINDOW", {"count": len(matched), "notes": matched})

        return PartActionResponse(False, "UNKNOWN_ACTION")


class NoteRendererPart(GamePartBase):
    """Computes note lane coordinates, speed fall distance, and approach progress."""
    def __init__(self):
        super().__init__("part_note_renderer", "NoteRenderer", "RHYTHM")

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "UPDATE_FRAME":
            current_time = float(params.get("current_time_ms", 0.0))
            approach_window = float(params.get("approach_window_ms", 800.0))
            notes = params.get("notes", [])
            rendered = []
            for n in notes:
                time_diff = n["time_ms"] - current_time
                if -150.0 <= time_diff <= approach_window:
                    # 1.0 = spawn point (top), 0.0 = hit line
                    progress = max(0.0, min(1.0, 1.0 - (time_diff / approach_window)))
                    rendered.append({
                        "id": n["id"],
                        "lane": n["lane"],
                        "type": n["type"],
                        "progress": round(progress, 3),
                        "time_diff_ms": round(time_diff, 1)
                    })
            return PartActionResponse(True, "FRAME_RENDERED", {"active_notes": rendered, "count": len(rendered)})

        return PartActionResponse(False, "UNKNOWN_ACTION")


class JudgmentPart(GamePartBase):
    """Timing arbitration for rhythm games: PERFECT (<=40ms), GREAT (<=80ms), GOOD (<=120ms), MISS (>120ms)."""
    def __init__(self):
        super().__init__("part_judgment", "Judgment", "RHYTHM")
        self.windows = {"PERFECT": 40.0, "GREAT": 80.0, "GOOD": 120.0}

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "JUDGE_HIT":
            note_time = float(params.get("note_time_ms", 0.0))
            hit_time = float(params.get("hit_time_ms", 0.0))
            delta = hit_time - note_time
            abs_delta = abs(delta)

            if abs_delta <= self.windows["PERFECT"]:
                tier = "PERFECT"
            elif abs_delta <= self.windows["GREAT"]:
                tier = "GREAT"
            elif abs_delta <= self.windows["GOOD"]:
                tier = "GOOD"
            else:
                tier = "MISS"

            return PartActionResponse(True, "NOTE_JUDGED", {
                "tier": tier,
                "delta_ms": round(delta, 2),
                "is_early": delta < 0 and tier != "MISS",
                "is_late": delta > 0 and tier != "MISS"
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class ScoreComboPart(GamePartBase):
    """Tracks rhythm game combo, max combo, accuracy %, standard 1M score, and grades."""
    def __init__(self):
        super().__init__("part_score_combo", "ScoreCombo", "RHYTHM")
        self.combo = 0
        self.max_combo = 0
        self.total_notes = 0
        self.judgments = {"PERFECT": 0, "GREAT": 0, "GOOD": 0, "MISS": 0}
        self.score_weights = {"PERFECT": 1.0, "GREAT": 0.7, "GOOD": 0.4, "MISS": 0.0}

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "RECORD_HIT":
            tier = params.get("tier", "MISS")
            if tier not in self.judgments:
                return PartActionResponse(False, "INVALID_TIER")

            self.judgments[tier] += 1
            self.total_notes += 1

            if tier in ["PERFECT", "GREAT", "GOOD"]:
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
            else:
                self.combo = 0

            return PartActionResponse(True, "HIT_RECORDED", {"combo": self.combo, "max_combo": self.max_combo})

        elif action == "CALCULATE_FINAL":
            total_planned = max(1, params.get("total_chart_notes", self.total_notes))
            earned_points = sum(self.judgments[k] * self.score_weights[k] for k in self.judgments)
            accuracy = (earned_points / max(1, self.total_notes)) * 100.0 if self.total_notes > 0 else 0.0
            # Standard 1,000,000 point scale (900k note score + 100k combo score)
            note_score = (earned_points / total_planned) * 900000.0
            combo_ratio = self.max_combo / total_planned
            combo_score = combo_ratio * 100000.0
            final_score = int(round(note_score + combo_score))

            if accuracy == 100.0:
                grade = "AP"  # All Perfect
            elif self.max_combo == total_planned and self.judgments["MISS"] == 0:
                grade = "FC"  # Full Combo
            elif final_score >= 950000:
                grade = "S"
            elif final_score >= 880000:
                grade = "A"
            elif final_score >= 750000:
                grade = "B"
            elif final_score >= 600000:
                grade = "C"
            else:
                grade = "F"

            return PartActionResponse(True, "SCORE_CALCULATED", {
                "final_score": final_score,
                "accuracy": round(accuracy, 2),
                "grade": grade,
                "max_combo": self.max_combo,
                "judgments": dict(self.judgments)
            })

        elif action == "RESET":
            self.combo = 0
            self.max_combo = 0
            self.total_notes = 0
            self.judgments = {k: 0 for k in self.judgments}
            return PartActionResponse(True, "SCORE_RESET")

        return PartActionResponse(False, "UNKNOWN_ACTION")


class ChartEditorPart(GamePartBase):
    """UGC Chart Editor: note creation, beat quantization, removal and JSON export."""
    def __init__(self):
        super().__init__("part_chart_editor", "ChartEditor", "RHYTHM")
        self.notes: List[Dict[str, Any]] = []

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "ADD_NOTE":
            nid = params.get("id", f"ugc_note_{len(self.notes)}")
            note = {
                "id": nid,
                "lane": int(params.get("lane", 0)),
                "time_ms": float(params.get("time_ms", 0.0)),
                "type": params.get("type", "TAP"),
                "duration_ms": float(params.get("duration_ms", 0.0))
            }
            self.notes.append(note)
            self.notes.sort(key=lambda x: x["time_ms"])
            return PartActionResponse(True, "NOTE_ADDED", {"note": note, "total": len(self.notes)})

        elif action == "REMOVE_NOTE":
            nid = params.get("id")
            before = len(self.notes)
            self.notes = [n for n in self.notes if n["id"] != nid]
            removed = len(self.notes) < before
            return PartActionResponse(removed, "NOTE_REMOVED" if removed else "NOTE_NOT_FOUND", {"id": nid})

        elif action == "QUANTIZE":
            bpm = float(params.get("bpm", 120.0))
            division = int(params.get("division", 4))  # 4 = quarter note, 8 = eighth
            beat_ms = 60000.0 / bpm
            interval_ms = beat_ms / (division / 4.0)
            for n in self.notes:
                snapped = round(n["time_ms"] / interval_ms) * interval_ms
                n["time_ms"] = round(snapped, 1)
            self.notes.sort(key=lambda x: x["time_ms"])
            return PartActionResponse(True, "CHART_QUANTIZED", {"interval_ms": interval_ms, "notes_count": len(self.notes)})

        elif action == "EXPORT_CHART":
            return PartActionResponse(True, "CHART_EXPORTED", {"notes": list(self.notes), "count": len(self.notes)})

        return PartActionResponse(False, "UNKNOWN_ACTION")


# =====================================================================
# 3. ROGUELIKE PARTS (Roguelike 品类零件)
# =====================================================================

class RoomGenPart(GamePartBase):
    """Procedural dungeon generator with interconnected rooms (Start, Combat, Shop, Boss)."""
    def __init__(self):
        super().__init__("part_room_gen", "RoomGen", "ROGUELIKE")

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "GENERATE_DUNGEON":
            room_count = max(4, params.get("room_count", 8))
            seed_val = params.get("seed", 12345)
            rng = random.Random(seed_val)

            # Generate linear chain with branches
            rooms = []
            types = ["COMBAT", "COMBAT", "TREASURE", "SHOP", "REST", "ELITE"]
            for i in range(room_count):
                if i == 0:
                    rtype = "START"
                elif i == room_count - 1:
                    rtype = "BOSS"
                else:
                    rtype = rng.choice(types)
                rooms.append({
                    "id": f"room_{i}",
                    "type": rtype,
                    "x": i % 3,
                    "y": i // 3,
                    "doors": []
                })

            # Connect consecutive rooms
            for i in range(room_count - 1):
                rooms[i]["doors"].append(rooms[i + 1]["id"])
                rooms[i + 1]["doors"].append(rooms[i]["id"])

            return PartActionResponse(True, "DUNGEON_GENERATED", {
                "seed": seed_val,
                "room_count": len(rooms),
                "rooms": rooms
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class SynergyPart(GamePartBase):
    """Item synergy matrix: tracks tags and calculates threshold tier bonuses."""
    def __init__(self):
        super().__init__("part_synergy", "Synergy", "ROGUELIKE")
        self.inventory_tags: Dict[str, List[str]] = {}
        self.rules: Dict[str, List[Dict[str, Any]]] = {}

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "REGISTER_RULE":
            tag = params.get("tag")
            thresholds = params.get("thresholds", [])  # [{"count": 2, "effect": "BURN_20"}, {"count": 4, "effect": "EXPLODE"}]
            self.rules[tag] = thresholds
            return PartActionResponse(True, "RULE_REGISTERED", {"tag": tag})

        elif action == "ADD_ITEM":
            item_id = params.get("item_id")
            tags = params.get("tags", [])
            self.inventory_tags[item_id] = tags
            return PartActionResponse(True, "ITEM_ADDED", {"item_id": item_id, "tags": tags})

        elif action == "REMOVE_ITEM":
            item_id = params.get("item_id")
            if item_id in self.inventory_tags:
                del self.inventory_tags[item_id]
                return PartActionResponse(True, "ITEM_REMOVED", {"item_id": item_id})
            return PartActionResponse(False, "ITEM_NOT_FOUND")

        elif action == "EVALUATE_SYNERGIES":
            tag_counts: Dict[str, int] = {}
            for tags in self.inventory_tags.values():
                for t in tags:
                    tag_counts[t] = tag_counts.get(t, 0) + 1

            active_bonuses = []
            for tag, thresholds in self.rules.items():
                cur = tag_counts.get(tag, 0)
                for th in thresholds:
                    if cur >= th["count"]:
                        active_bonuses.append({
                            "tag": tag,
                            "required": th["count"],
                            "current": cur,
                            "effect": th["effect"]
                        })

            return PartActionResponse(True, "SYNERGIES_EVALUATED", {
                "tag_counts": tag_counts,
                "active_bonuses": active_bonuses
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class LootTablePart(GamePartBase):
    """Dynamic weighted loot drop with rarity tiers and bad-luck pity counter."""
    def __init__(self):
        super().__init__("part_loot_table", "LootTable", "ROGUELIKE")
        self.pity_count = 0
        self.pity_limit = 10

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "ROLL_LOOT":
            luck = float(params.get("luck", 1.0))
            weights = params.get("weights", {"COMMON": 60, "RARE": 30, "EPIC": 9, "LEGENDARY": 1})
            self.pity_count += 1

            # Pity check
            if self.pity_count >= self.pity_limit:
                tier = "LEGENDARY"
                self.pity_count = 0
            else:
                # Modulate weights with luck
                adj_weights = {}
                adj_weights["COMMON"] = max(10, weights["COMMON"] - luck * 5)
                adj_weights["RARE"] = weights["RARE"] + luck * 2
                adj_weights["EPIC"] = weights["EPIC"] + luck * 2
                adj_weights["LEGENDARY"] = weights["LEGENDARY"] + luck * 1

                total = sum(adj_weights.values())
                pick = random.uniform(0, total)
                accum = 0.0
                tier = "COMMON"
                for t, w in adj_weights.items():
                    accum += w
                    if pick <= accum:
                        tier = t
                        break

                if tier in ["EPIC", "LEGENDARY"]:
                    self.pity_count = 0

            return PartActionResponse(True, "LOOT_ROLLED", {
                "tier": tier,
                "pity_count": self.pity_count,
                "pity_limit": self.pity_limit
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class MetaProgressPart(GamePartBase):
    """Meta-progression talent tree and permanent stat upgrades."""
    def __init__(self):
        super().__init__("part_meta_progress", "MetaProgress", "ROGUELIKE")
        self.souls = 0
        self.unlocked_talents: Dict[str, int] = {}

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "ADD_SOULS":
            amount = params.get("amount", 0)
            self.souls += amount
            return PartActionResponse(True, "SOULS_ADDED", {"souls": self.souls})

        elif action == "UPGRADE_TALENT":
            talent_id = params.get("talent_id")
            cost = params.get("cost", 100)
            max_lvl = params.get("max_level", 5)
            cur_lvl = self.unlocked_talents.get(talent_id, 0)

            if cur_lvl >= max_lvl:
                return PartActionResponse(False, "MAX_LEVEL_REACHED")
            if self.souls < cost:
                return PartActionResponse(False, "INSUFFICIENT_SOULS", message=f"Need {cost}, have {self.souls}")

            self.souls -= cost
            self.unlocked_talents[talent_id] = cur_lvl + 1
            return PartActionResponse(True, "TALENT_UPGRADED", {
                "talent_id": talent_id,
                "level": self.unlocked_talents[talent_id],
                "remaining_souls": self.souls
            })

        elif action == "GET_PROGRESS":
            return PartActionResponse(True, "PROGRESS_RETRIEVED", {
                "souls": self.souls,
                "talents": dict(self.unlocked_talents)
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class SeedManagerPart(GamePartBase):
    """PRNG seed management, deterministic run generation and reproducible replay codes."""
    def __init__(self):
        super().__init__("part_seed_manager", "SeedManager", "ROGUELIKE")
        self.seed = 0
        self.rng = random.Random()

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "SET_SEED":
            s = params.get("seed", 42)
            if isinstance(s, str):
                self.seed = sum(ord(c) for c in s)
            else:
                self.seed = int(s)
            self.rng = random.Random(self.seed)
            return PartActionResponse(True, "SEED_SET", {"seed": self.seed})

        elif action == "NEXT_INT":
            low = params.get("min", 0)
            high = params.get("max", 100)
            val = self.rng.randint(low, high)
            return PartActionResponse(True, "INT_GENERATED", {"value": val})

        elif action == "NEXT_FLOAT":
            val = round(self.rng.random(), 4)
            return PartActionResponse(True, "FLOAT_GENERATED", {"value": val})

        elif action == "DERIVE_SEED":
            salt = params.get("salt", "branch")
            derived = (self.seed * 31 + sum(ord(c) for c in salt)) % 2147483647
            return PartActionResponse(True, "SEED_DERIVED", {"salt": salt, "derived_seed": derived})

        return PartActionResponse(False, "UNKNOWN_ACTION")


# =====================================================================
# 4. BUILDER / SIM PARTS (模拟建造品类零件)
# =====================================================================

class GridBuildPart(GamePartBase):
    """2D tile-based construction: placement validation, occupancy check, and demolition."""
    def __init__(self, width: int = 32, height: int = 32):
        super().__init__("part_grid_build", "GridBuild", "SIM")
        self.width = width
        self.height = height
        self.grid: Dict[Tuple[int, int], str] = {}  # (x, y) -> building_id
        self.buildings: Dict[str, Dict[str, Any]] = {}

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "PLACE_BUILDING":
            bid = params.get("id", f"b_{len(self.buildings)}")
            btype = params.get("type", "house")
            x = params.get("x", 0)
            y = params.get("y", 0)
            w = params.get("width", 1)
            h = params.get("height", 1)

            # Check bounds and collision
            for r in range(y, y + h):
                for c in range(x, x + w):
                    if c < 0 or c >= self.width or r < 0 or r >= self.height:
                        return PartActionResponse(False, "OUT_OF_BOUNDS")
                    if (c, r) in self.grid:
                        return PartActionResponse(False, "SPACE_OCCUPIED", message=f"Occupied at ({c}, {r})")

            # Occupy
            for r in range(y, y + h):
                for c in range(x, x + w):
                    self.grid[(c, r)] = bid

            self.buildings[bid] = {"id": bid, "type": btype, "x": x, "y": y, "width": w, "height": h}
            return PartActionResponse(True, "BUILDING_PLACED", {"building": self.buildings[bid]})

        elif action == "DEMOLISH":
            bid = params.get("id")
            if bid not in self.buildings:
                return PartActionResponse(False, "BUILDING_NOT_FOUND")

            # Free cells
            to_del = [k for k, v in self.grid.items() if v == bid]
            for k in to_del:
                del self.grid[k]

            del self.buildings[bid]
            return PartActionResponse(True, "BUILDING_DEMOLISHED", {"id": bid, "freed_cells": len(to_del)})

        elif action == "QUERY_TILE":
            x = params.get("x", 0)
            y = params.get("y", 0)
            bid = self.grid.get((x, y))
            return PartActionResponse(True, "TILE_QUERIED", {
                "x": x, "y": y,
                "building_id": bid,
                "building": self.buildings.get(bid) if bid else None
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class ResourceFlowPart(GamePartBase):
    """Resource supply-demand networks, transport pipelines and bottleneck detection."""
    def __init__(self):
        super().__init__("part_resource_flow", "ResourceFlow", "SIM")
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.connections: List[Dict[str, Any]] = []

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "ADD_NODE":
            nid = params.get("id")
            ntype = params.get("type", "producer")  # producer / consumer / storage
            res = params.get("resource", "water")
            rate = float(params.get("rate", 10.0))
            capacity = float(params.get("capacity", 100.0))
            self.nodes[nid] = {
                "id": nid, "type": ntype, "resource": res,
                "rate": rate, "capacity": capacity, "current": 0.0
            }
            return PartActionResponse(True, "NODE_ADDED", {"node": self.nodes[nid]})

        elif action == "CONNECT":
            src = params.get("from_id")
            dst = params.get("to_id")
            bandwidth = float(params.get("bandwidth", 10.0))
            self.connections.append({"from": src, "to": dst, "bandwidth": bandwidth})
            return PartActionResponse(True, "CONNECTED", {"from": src, "to": dst, "bandwidth": bandwidth})

        elif action == "TICK_FLOW":
            dt = float(params.get("dt", 1.0))
            # 1. Produce
            for n in self.nodes.values():
                if n["type"] == "producer":
                    n["current"] = min(n["capacity"], n["current"] + n["rate"] * dt)

            # 2. Transport along connections
            flowed = 0.0
            for conn in self.connections:
                src = self.nodes.get(conn["from"])
                dst = self.nodes.get(conn["to"])
                if src and dst and src["resource"] == dst["resource"]:
                    avail = min(src["current"], conn["bandwidth"] * dt)
                    space = dst["capacity"] - dst["current"]
                    amount = min(avail, space)
                    src["current"] -= amount
                    dst["current"] += amount
                    flowed += amount

            # 3. Consume
            shortages = []
            for n in self.nodes.values():
                if n["type"] == "consumer":
                    needed = n["rate"] * dt
                    if n["current"] < needed:
                        shortages.append(n["id"])
                    n["current"] = max(0.0, n["current"] - needed)

            return PartActionResponse(True, "FLOW_TICKED", {
                "flowed": flowed,
                "shortages": shortages,
                "node_status": {k: v["current"] for k, v in self.nodes.items()}
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class GameClockPart(GamePartBase):
    """Simulation time clock, day/night cycles, seasonal progression and speed control."""
    def __init__(self):
        super().__init__("part_game_clock", "GameClock", "SIM")
        self.speed = 1.0
        self.game_seconds = 0.0
        self.day_length_sec = 600.0  # 10 real minutes = 1 game day

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "SET_SPEED":
            self.speed = max(0.0, min(5.0, float(params.get("speed", 1.0))))
            return PartActionResponse(True, "SPEED_SET", {"speed": self.speed})

        elif action == "TICK":
            dt = float(params.get("dt", 1.0))
            self.game_seconds += dt * self.speed

            total_days = int(self.game_seconds // self.day_length_sec)
            day_progress = (self.game_seconds % self.day_length_sec) / self.day_length_sec
            # Hour 0..23
            hour = int(day_progress * 24)
            # Daylight factor: 0.0 (midnight) to 1.0 (noon)
            daylight = math.sin(day_progress * math.pi)

            seasons = ["SPRING", "SUMMER", "AUTUMN", "WINTER"]
            season = seasons[(total_days // 30) % 4]

            return PartActionResponse(True, "CLOCK_TICKED", {
                "hour": hour,
                "day": total_days + 1,
                "season": season,
                "daylight": round(max(0.0, daylight), 3),
                "speed": self.speed
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class EconomyPart(GamePartBase):
    """City/Sim economy: treasury cashflow, dynamic supply-demand commodity pricing."""
    def __init__(self):
        super().__init__("part_economy", "Economy", "SIM")
        self.treasury = 5000.0
        self.commodities: Dict[str, Dict[str, float]] = {
            "grain": {"base": 10.0, "supply": 100.0, "demand": 100.0},
            "iron": {"base": 50.0, "supply": 50.0, "demand": 50.0}
        }

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "TRANSACTION":
            amt = float(params.get("amount", 0.0))
            if self.treasury + amt < 0:
                return PartActionResponse(False, "BANKRUPTCY_PREVENTED", message="Not enough treasury funds")
            self.treasury += amt
            return PartActionResponse(True, "TRANSACTION_COMPLETED", {"treasury": round(self.treasury, 2)})

        elif action == "GET_COMMODITY_PRICE":
            c = params.get("commodity", "grain")
            if c not in self.commodities:
                return PartActionResponse(False, "UNKNOWN_COMMODITY")
            item = self.commodities[c]
            # Price = base * (demand / max(1, supply))
            ratio = item["demand"] / max(1.0, item["supply"])
            price = round(item["base"] * ratio, 2)
            return PartActionResponse(True, "PRICE_CALCULATED", {"commodity": c, "price": price, "ratio": round(ratio, 2)})

        elif action == "UPDATE_MARKET":
            c = params.get("commodity")
            if c in self.commodities:
                self.commodities[c]["supply"] += float(params.get("delta_supply", 0.0))
                self.commodities[c]["demand"] += float(params.get("delta_demand", 0.0))
                return PartActionResponse(True, "MARKET_UPDATED", {"data": self.commodities[c]})
            return PartActionResponse(False, "UNKNOWN_COMMODITY")

        return PartActionResponse(False, "UNKNOWN_ACTION")


# =====================================================================
# 5. RACING GAME PARTS (竞速品类零件)
# =====================================================================

class SplineTrackPart(GamePartBase):
    """Track waypoints, spline interpolation, progress tracking, and off-track detection."""
    def __init__(self):
        super().__init__("part_spline_track", "SplineTrack", "RACING")
        self.waypoints: List[Tuple[float, float]] = []
        self.track_width = 15.0
        self.total_length = 0.0

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "SET_WAYPOINTS":
            pts = params.get("waypoints", [])
            self.waypoints = [(float(p[0]), float(p[1])) for p in pts]
            self.track_width = float(params.get("track_width", 15.0))
            # Calculate total length
            length = 0.0
            for i in range(len(self.waypoints)):
                p1 = self.waypoints[i]
                p2 = self.waypoints[(i + 1) % len(self.waypoints)]
                length += math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            self.total_length = length
            return PartActionResponse(True, "TRACK_INITIALIZED", {"waypoints_count": len(self.waypoints), "length": round(length, 1)})

        elif action == "GET_PROGRESS":
            if not self.waypoints:
                return PartActionResponse(False, "NO_WAYPOINTS")
            x = float(params.get("x", 0.0))
            y = float(params.get("y", 0.0))
            # Find distance to closest line segment
            min_dist = float("inf")
            best_progress = 0.0
            accum_dist = 0.0

            n = len(self.waypoints)
            for i in range(n):
                p1 = self.waypoints[i]
                p2 = self.waypoints[(i + 1) % n]
                vx, vy = p2[0] - p1[0], p2[1] - p1[1]
                seg_len = math.hypot(vx, vy)
                if seg_len > 0:
                    wx, wy = x - p1[0], y - p1[1]
                    c1 = wx * vx + wy * vy
                    c2 = vx * vx + vy * vy
                    t = max(0.0, min(1.0, c1 / c2))
                    proj_x = p1[0] + t * vx
                    proj_y = p1[1] + t * vy
                    d = math.hypot(x - proj_x, y - proj_y)
                    if d < min_dist:
                        min_dist = d
                        best_progress = (accum_dist + t * seg_len) / max(1.0, self.total_length)
                    accum_dist += seg_len

            is_off = min_dist > self.track_width
            return PartActionResponse(True, "PROGRESS_CALCULATED", {
                "progress": round(best_progress, 3),
                "distance_to_center": round(min_dist, 2),
                "is_off_track": is_off
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class VehiclePhysPart(GamePartBase):
    """Vehicle kinematics: throttle, braking, drift friction, nitro boost, and steering."""
    def __init__(self):
        super().__init__("part_vehicle_phys", "VehiclePhys", "RACING")
        self.x = 0.0
        self.y = 0.0
        self.speed = 0.0
        self.max_speed = 60.0
        self.heading = 0.0  # radians
        self.accel = 20.0
        self.brake = 40.0
        self.friction = 5.0
        self.nitro_timer = 0.0

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "APPLY_INPUT":
            throttle = float(params.get("throttle", 0.0))
            steer = float(params.get("steer", 0.0))
            brake = float(params.get("brake", 0.0))
            nitro = bool(params.get("nitro", False))
            dt = float(params.get("dt", 0.016))

            if nitro and self.nitro_timer <= 0:
                self.nitro_timer = 2.0

            top_speed = self.max_speed * (1.5 if self.nitro_timer > 0 else 1.0)

            # Acceleration / Braking
            if throttle > 0:
                self.speed = min(top_speed, self.speed + self.accel * throttle * dt)
            elif brake > 0:
                self.speed = max(0.0, self.speed - self.brake * brake * dt)
            else:
                self.speed = max(0.0, self.speed - self.friction * dt)

            # Steering
            if self.speed > 0.5:
                self.heading += steer * 2.5 * dt

            # Position
            self.x += math.cos(self.heading) * self.speed * dt
            self.y += math.sin(self.heading) * self.speed * dt

            if self.nitro_timer > 0:
                self.nitro_timer = max(0.0, self.nitro_timer - dt)

            return PartActionResponse(True, "PHYSICS_STEPPED", {
                "x": round(self.x, 2),
                "y": round(self.y, 2),
                "speed": round(self.speed, 2),
                "heading": round(self.heading, 2),
                "nitro_active": self.nitro_timer > 0
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class RubberBandPart(GamePartBase):
    """Dynamic difficulty rubber-band: adjusts opponent speed based on player distance."""
    def __init__(self):
        super().__init__("part_rubber_band", "RubberBand", "RACING")

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "CALCULATE_HANDICAP":
            player_prog = float(params.get("player_progress", 0.0))
            ai_prog = float(params.get("ai_progress", 0.0))
            diff = player_prog - ai_prog  # positive if player is ahead

            # If player is far ahead (>0.05 track length), boost AI
            if diff > 0.05:
                factor = 1.0 + min(0.35, diff * 2.5)  # up to +35% speed
            # If AI is far ahead, penalize AI slightly so player can catch up
            elif diff < -0.05:
                factor = max(0.85, 1.0 + diff * 1.5)  # down to -15% speed
            else:
                factor = 1.0

            return PartActionResponse(True, "HANDICAP_CALCULATED", {
                "speed_multiplier": round(factor, 3),
                "progress_diff": round(diff, 3)
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class GhostReplayPart(GamePartBase):
    """Records and samples ghost trajectory frames for asynchronous racing ghosts."""
    def __init__(self):
        super().__init__("part_ghost_replay", "GhostReplay", "RACING")
        self.frames: List[Dict[str, Any]] = []
        self.is_recording = False

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "START_RECORD":
            self.frames.clear()
            self.is_recording = True
            return PartActionResponse(True, "RECORDING_STARTED")

        elif action == "RECORD_FRAME":
            if self.is_recording:
                f = {
                    "t": float(params.get("time", 0.0)),
                    "x": float(params.get("x", 0.0)),
                    "y": float(params.get("y", 0.0)),
                    "speed": float(params.get("speed", 0.0))
                }
                self.frames.append(f)
                return PartActionResponse(True, "FRAME_RECORDED", {"count": len(self.frames)})
            return PartActionResponse(False, "NOT_RECORDING")

        elif action == "STOP_RECORD":
            self.is_recording = False
            return PartActionResponse(True, "RECORDING_STOPPED", {"total_frames": len(self.frames)})

        elif action == "SAMPLE_GHOST":
            t = float(params.get("time", 0.0))
            if not self.frames:
                return PartActionResponse(False, "EMPTY_GHOST")
            # Binary search or closest frame
            closest = min(self.frames, key=lambda f: abs(f["t"] - t))
            return PartActionResponse(True, "GHOST_SAMPLED", {"frame": closest})

        return PartActionResponse(False, "UNKNOWN_ACTION")


class LapTimerPart(GamePartBase):
    """Lap tracking, split times, current/best lap time records."""
    def __init__(self, total_laps: int = 3):
        super().__init__("part_lap_timer", "LapTimer", "RACING")
        self.total_laps = total_laps
        self.current_lap = 1
        self.lap_times: List[float] = []
        self.lap_start_time = 0.0
        self.best_lap = float("inf")
        self.finished = False

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "START_RACE":
            self.current_lap = 1
            self.lap_times.clear()
            self.lap_start_time = float(params.get("start_time", 0.0))
            self.best_lap = float("inf")
            self.finished = False
            return PartActionResponse(True, "RACE_STARTED", {"total_laps": self.total_laps})

        elif action == "CROSS_FINISH":
            now = float(params.get("current_time", 0.0))
            lap_duration = now - self.lap_start_time
            self.lap_times.append(round(lap_duration, 3))
            if lap_duration < self.best_lap:
                self.best_lap = round(lap_duration, 3)

            if self.current_lap >= self.total_laps:
                self.finished = True
                return PartActionResponse(True, "RACE_FINISHED", {
                    "total_time": round(sum(self.lap_times), 3),
                    "best_lap": self.best_lap,
                    "lap_times": list(self.lap_times)
                })
            else:
                self.current_lap += 1
                self.lap_start_time = now
                return PartActionResponse(True, "LAP_COMPLETED", {
                    "lap": self.current_lap - 1,
                    "duration": round(lap_duration, 3),
                    "best_lap": self.best_lap
                })

        return PartActionResponse(False, "UNKNOWN_ACTION")


# =====================================================================
# =====================================================================
# 6. 3D GAME PARTS (3D 品类零件扩展)
# =====================================================================

class SceneGraph3DPart(GamePartBase):
    """Hierarchical 3D transform tree: position, Euler rotation, scale, and world transforms."""
    def __init__(self):
        super().__init__("part_scene_graph_3d", "SceneGraph3D", "3D")
        self.nodes: Dict[str, Dict[str, Any]] = {}

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "ADD_NODE":
            nid = params.get("id")
            parent = params.get("parent_id")
            pos = list(params.get("position", [0.0, 0.0, 0.0]))
            rot = list(params.get("rotation", [0.0, 0.0, 0.0]))
            scale = list(params.get("scale", [1.0, 1.0, 1.0]))

            self.nodes[nid] = {
                "id": nid, "parent_id": parent,
                "position": pos, "rotation": rot, "scale": scale,
                "children": []
            }
            if parent and parent in self.nodes:
                self.nodes[parent]["children"].append(nid)
            return PartActionResponse(True, "NODE_ADDED", {"node_id": nid})

        elif action == "SET_TRANSFORM":
            nid = params.get("id")
            if nid in self.nodes:
                if "position" in params:
                    self.nodes[nid]["position"] = list(params["position"])
                if "rotation" in params:
                    self.nodes[nid]["rotation"] = list(params["rotation"])
                if "scale" in params:
                    self.nodes[nid]["scale"] = list(params["scale"])
                return PartActionResponse(True, "TRANSFORM_UPDATED", {"node_id": nid})
            return PartActionResponse(False, "NODE_NOT_FOUND")

        elif action == "GET_WORLD_TRANSFORM":
            nid = params.get("id")
            if nid not in self.nodes:
                return PartActionResponse(False, "NODE_NOT_FOUND")

            # Traverse to root accumulating translations
            curr = nid
            wx, wy, wz = 0.0, 0.0, 0.0
            chain = []
            while curr and curr in self.nodes:
                n = self.nodes[curr]
                chain.append(curr)
                wx += n["position"][0]
                wy += n["position"][1]
                wz += n["position"][2]
                curr = n["parent_id"]

            return PartActionResponse(True, "WORLD_TRANSFORM_COMPUTED", {
                "node_id": nid,
                "world_position": [round(wx, 2), round(wy, 2), round(wz, 2)],
                "hierarchy_depth": len(chain)
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class MeshRendererPart(GamePartBase):
    """3D Mesh geometry descriptors, PBR materials, and drawcall statistics."""
    def __init__(self):
        super().__init__("part_mesh_renderer", "MeshRenderer", "3D")
        self.meshes: Dict[str, Dict[str, Any]] = {}

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "REGISTER_MESH":
            mid = params.get("id")
            vcount = int(params.get("vertex_count", 0))
            tcount = int(params.get("triangle_count", 0))
            self.meshes[mid] = {
                "id": mid,
                "vertex_count": vcount,
                "triangle_count": tcount,
                "material": {"albedo": (1.0, 1.0, 1.0), "roughness": 0.5, "metallic": 0.0}
            }
            return PartActionResponse(True, "MESH_REGISTERED", {"mesh_id": mid, "triangles": tcount})

        elif action == "SET_MATERIAL":
            mid = params.get("id")
            if mid in self.meshes:
                self.meshes[mid]["material"].update(params.get("material", {}))
                return PartActionResponse(True, "MATERIAL_UPDATED", {"mesh_id": mid})
            return PartActionResponse(False, "MESH_NOT_FOUND")

        elif action == "GET_RENDER_STATS":
            total_v = sum(m["vertex_count"] for m in self.meshes.values())
            total_t = sum(m["triangle_count"] for m in self.meshes.values())
            return PartActionResponse(True, "STATS_RETRIEVED", {
                "total_meshes": len(self.meshes),
                "total_vertices": total_v,
                "total_triangles": total_t,
                "estimated_draw_calls": len(self.meshes)
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class SkeletalAnimPart(GamePartBase):
    """Skeletal animation: bone hierarchy, clip playback, crossfading, and pose blending."""
    def __init__(self):
        super().__init__("part_skeletal_anim", "SkeletalAnim", "3D")
        self.bones: List[str] = []
        self.current_clip = "idle"
        self.blend_clip: Optional[str] = None
        self.blend_weight = 0.0

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "INIT_SKELETON":
            self.bones = list(params.get("bones", ["root", "spine", "head", "arm_l", "arm_r", "leg_l", "leg_r"]))
            return PartActionResponse(True, "SKELETON_INITIALIZED", {"bone_count": len(self.bones)})

        elif action == "PLAY_ANIM":
            clip = params.get("clip", "idle")
            self.current_clip = clip
            self.blend_clip = None
            self.blend_weight = 0.0
            return PartActionResponse(True, "ANIM_PLAYING", {"clip": clip})

        elif action == "CROSSFADE":
            to_clip = params.get("to_clip", "walk")
            weight = float(params.get("weight", 0.5))
            self.blend_clip = to_clip
            self.blend_weight = max(0.0, min(1.0, weight))
            return PartActionResponse(True, "CROSSFADE_APPLIED", {
                "from_clip": self.current_clip,
                "to_clip": to_clip,
                "blend_weight": self.blend_weight
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class TPSCameraPart(GamePartBase):
    """Third-Person Orbit Camera: spring arm, pitch/yaw rotation clamping, and collision avoidance."""
    def __init__(self):
        super().__init__("part_tps_camera", "TPSCamera", "3D")
        self.target_pos = (0.0, 0.0, 0.0)
        self.arm_length = 5.0
        self.pitch = 15.0  # degrees
        self.yaw = 0.0     # degrees

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "SET_TARGET":
            t = params.get("target", (0.0, 0.0, 0.0))
            self.target_pos = (float(t[0]), float(t[1]), float(t[2]))
            return PartActionResponse(True, "TARGET_UPDATED", {"target": self.target_pos})

        elif action == "ROTATE":
            dpitch = float(params.get("delta_pitch", 0.0))
            dyaw = float(params.get("delta_yaw", 0.0))
            self.pitch = max(-60.0, min(80.0, self.pitch + dpitch))
            self.yaw = (self.yaw + dyaw) % 360.0
            return PartActionResponse(True, "CAMERA_ROTATED", {"pitch": self.pitch, "yaw": self.yaw})

        elif action == "COMPUTE_EYE_POSITION":
            # Orbit spherical coordinate offset
            col_hit_dist = params.get("collision_dist")
            effective_arm = min(self.arm_length, col_hit_dist) if col_hit_dist else self.arm_length

            pitch_rad = math.radians(self.pitch)
            yaw_rad = math.radians(self.yaw)

            eye_x = self.target_pos[0] - effective_arm * math.cos(pitch_rad) * math.sin(yaw_rad)
            eye_y = self.target_pos[1] + effective_arm * math.sin(pitch_rad)
            eye_z = self.target_pos[2] - effective_arm * math.cos(pitch_rad) * math.cos(yaw_rad)

            return PartActionResponse(True, "EYE_COMPUTED", {
                "eye": (round(eye_x, 2), round(eye_y, 2), round(eye_z, 2)),
                "arm_length": effective_arm
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


class NavMeshPart(GamePartBase):
    """Navigation mesh: graph topology, cost evaluation, and A* pathfinding."""
    def __init__(self):
        super().__init__("part_navmesh", "NavMesh", "3D")
        self.nodes: Dict[str, Tuple[float, float, float]] = {}
        self.adj: Dict[str, List[Tuple[str, float]]] = {}

    def execute(self, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if action == "BUILD_GRAPH":
            # nodes: { "A": (0,0,0), "B": (5,0,0), ... }
            self.nodes = {k: tuple(v) for k, v in params.get("nodes", {}).items()}
            # edges: [ ("A", "B", cost), ... ]
            self.adj = {k: [] for k in self.nodes}
            for u, v, cost in params.get("edges", []):
                if u in self.adj and v in self.adj:
                    self.adj[u].append((v, float(cost)))
                    self.adj[v].append((u, float(cost)))
            return PartActionResponse(True, "NAVMESH_BUILT", {"node_count": len(self.nodes)})

        elif action == "FIND_PATH":
            start = params.get("start")
            goal = params.get("goal")
            if start not in self.nodes or goal not in self.nodes:
                return PartActionResponse(False, "INVALID_ENDPOINT")

            # Dijkstra / A* Search
            import heapq
            distances = {n: float("inf") for n in self.nodes}
            distances[start] = 0.0
            prev = {n: None for n in self.nodes}
            pq = [(0.0, start)]

            while pq:
                d, u = heapq.heappop(pq)
                if u == goal:
                    break
                if d > distances[u]:
                    continue

                for v, weight in self.adj.get(u, []):
                    if distances[u] + weight < distances[v]:
                        distances[v] = distances[u] + weight
                        prev[v] = u
                        heapq.heappush(pq, (distances[v], v))

            if distances[goal] == float("inf"):
                return PartActionResponse(False, "NO_PATH_FOUND")

            # Reconstruct
            path = []
            curr = goal
            while curr:
                path.append(curr)
                curr = prev[curr]
            path.reverse()

            return PartActionResponse(True, "PATH_FOUND", {
                "path": path,
                "total_cost": round(distances[goal], 2),
                "waypoint_coords": [self.nodes[p] for p in path]
            })

        return PartActionResponse(False, "UNKNOWN_ACTION")


# =====================================================================
# MODULAR GAME ASSEMBLER (ASSEMBLY LINE)
# =====================================================================

class ModularGameAssembler:
    """
    Ford-T Assembly Line: Mounts, coordinates, and wires pre-fabricated high-precision parts
    into a cohesive, robust game architecture across all genres.
    """

    def __init__(self):
        self.catalog: Dict[str, GamePartBase] = {
            # Core Minigame Parts
            "slingshot": SlingshotPhysicsPart(),
            "merge_two": MergeTwoPart(),
            "runner_stack": RunnerStackPart(),
            "clue_investigation": ClueInvestigationPart(),
            "narrative_pedagogy": NarrativePedagogyPart(),
            "gacha_store": GachaStorePart(),
            # Card Game Parts
            "card_deck": CardDeckPart(),
            "card_hand": CardHandPart(),
            "card_battlefield": CardBattleFieldPart(),
            "card_effect": CardEffectPart(),
            "card_ai": CardAIPart(),
            # Rhythm Game Parts
            "chart_parser": ChartParserPart(),
            "note_renderer": NoteRendererPart(),
            "judgment": JudgmentPart(),
            "score_combo": ScoreComboPart(),
            "chart_editor": ChartEditorPart(),
            # Roguelike Parts
            "room_gen": RoomGenPart(),
            "synergy": SynergyPart(),
            "loot_table": LootTablePart(),
            "meta_progress": MetaProgressPart(),
            "seed_manager": SeedManagerPart(),
            # Builder / Sim Parts
            "grid_build": GridBuildPart(),
            "resource_flow": ResourceFlowPart(),
            "game_clock": GameClockPart(),
            "economy": EconomyPart(),
            # Racing Parts
            "spline_track": SplineTrackPart(),
            "vehicle_phys": VehiclePhysPart(),
            "rubber_band": RubberBandPart(),
            "ghost_replay": GhostReplayPart(),
            "lap_timer": LapTimerPart(),
            # 3D Parts
            "scene_graph_3d": SceneGraph3DPart(),
            "mesh_renderer": MeshRendererPart(),
            "skeletal_anim": SkeletalAnimPart(),
            "tps_camera": TPSCameraPart(),
            "navmesh": NavMeshPart(),
        }

    def assemble(self, title: str, selected_part_keys: List[str]) -> Dict[str, Any]:
        mounted_parts = {}
        for key in selected_part_keys:
            if key not in self.catalog:
                raise KeyError(f"Part '{key}' not in catalog. Available: {list(self.catalog.keys())}")
            mounted_parts[key] = self.catalog[key]

        return {
            "title": title,
            "parts_count": len(mounted_parts),
            "active_parts": list(mounted_parts.keys()),
            "status": "ASSEMBLED_AND_WIRED"
        }

    def dispatch(self, part_key: str, action: str, params: Dict[str, Any]) -> PartActionResponse:
        if part_key not in self.catalog:
            return PartActionResponse(False, "PART_NOT_MOUNTED", message=f"Part {part_key} is not registered")
        return self.catalog[part_key].execute(action, params)


