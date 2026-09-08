"""
Card Game Archetype & Balance Simulator
Simulates turn-based card battles across archetypes (Aggro, Control, Midrange, Combo)
to detect overpowered cards, mana curve dead-draws, and win-rate imbalances.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple


@dataclass
class CardSpec:
    card_id: str
    name: str
    cost: int
    card_type: str  # "ATTACK", "MINION", "SPELL", "DEFENSE"
    value: int       # damage or shield or minion power
    hp: int = 0      # for minions
    draw_count: int = 0


@dataclass
class DeckArchetype:
    name: str
    description: str
    cards: List[CardSpec]
    max_hp: int = 30


class CardBattleSimulationEngine:
    """Executes a single automated match between two decks using greedy value AI."""

    def __init__(self, deck_a: DeckArchetype, deck_b: DeckArchetype, max_turns: int = 30):
        self.deck_a = deck_a
        self.deck_b = deck_b
        self.max_turns = max_turns

    def run_single_match(self) -> Dict[str, Any]:
        hp_a = self.deck_a.max_hp
        hp_b = self.deck_b.max_hp
        shield_a = 0
        shield_b = 0

        draw_pile_a = list(self.deck_a.cards)
        draw_pile_b = list(self.deck_b.cards)
        random.shuffle(draw_pile_a)
        random.shuffle(draw_pile_b)

        discard_a: List[CardSpec] = []
        discard_b: List[CardSpec] = []
        hand_a: List[CardSpec] = []
        hand_b: List[CardSpec] = []

        # Initial draw 4 cards
        def draw_cards(pile, discard, hand, n):
            for _ in range(n):
                if not pile:
                    if discard:
                        pile.extend(discard)
                        discard.clear()
                        random.shuffle(pile)
                    else:
                        break
                if pile:
                    hand.append(pile.pop())

        draw_cards(draw_pile_a, discard_a, hand_a, 4)
        draw_cards(draw_pile_b, discard_b, hand_b, 4)

        turns = 0
        winner = None

        for t in range(1, self.max_turns + 1):
            turns = t
            mana = min(10, t)

            # ---- TURN PLAYER A ----
            draw_cards(draw_pile_a, discard_a, hand_a, 1)
            # AI plays cards greedy
            rem_mana = mana
            hand_a.sort(key=lambda c: (c.value * 1.5 + c.cost), reverse=True)
            unplayed_a = []
            for c in hand_a:
                if c.cost <= rem_mana:
                    rem_mana -= c.cost
                    if c.card_type in ["ATTACK", "MINION"]:
                        dmg = c.value
                        absorbed = min(shield_b, dmg)
                        shield_b -= absorbed
                        hp_b -= (dmg - absorbed)
                    elif c.card_type == "DEFENSE":
                        shield_a += c.value
                    elif c.card_type == "SPELL":
                        hp_b -= c.value
                        if c.draw_count > 0:
                            draw_cards(draw_pile_a, discard_a, hand_a, c.draw_count)
                    discard_a.append(c)
                else:
                    unplayed_a.append(c)
            hand_a = unplayed_a

            if hp_b <= 0:
                winner = self.deck_a.name
                break

            # ---- TURN PLAYER B ----
            draw_cards(draw_pile_b, discard_b, hand_b, 1)
            rem_mana = mana
            hand_b.sort(key=lambda c: (c.value * 1.5 + c.cost), reverse=True)
            unplayed_b = []
            for c in hand_b:
                if c.cost <= rem_mana:
                    rem_mana -= c.cost
                    if c.card_type in ["ATTACK", "MINION"]:
                        dmg = c.value
                        absorbed = min(shield_a, dmg)
                        shield_a -= absorbed
                        hp_a -= (dmg - absorbed)
                    elif c.card_type == "DEFENSE":
                        shield_b += c.value
                    elif c.card_type == "SPELL":
                        hp_a -= c.value
                        if c.draw_count > 0:
                            draw_cards(draw_pile_b, discard_b, hand_b, c.draw_count)
                    discard_b.append(c)
                else:
                    unplayed_b.append(c)
            hand_b = unplayed_b

            if hp_a <= 0:
                winner = self.deck_b.name
                break

        if winner is None:
            winner = self.deck_a.name if hp_a >= hp_b else self.deck_b.name

        return {
            "winner": winner,
            "turns": turns,
            "hp_a": max(0, hp_a),
            "hp_b": max(0, hp_b)
        }


class CardBalanceSimulator:
    """Batch Monte-Carlo balance evaluator across deck matchups."""

    @staticmethod
    def create_sample_archetypes() -> Dict[str, DeckArchetype]:
        # Aggro deck: cheap minions and direct burn
        aggro_cards = []
        for i in range(8):
            aggro_cards.append(CardSpec(f"agg_1_{i}", "Goblin Raider", 1, "ATTACK", 3))
        for i in range(8):
            aggro_cards.append(CardSpec(f"agg_2_{i}", "Wolf Rider", 2, "ATTACK", 4))
        for i in range(6):
            aggro_cards.append(CardSpec(f"agg_3_{i}", "Fireball", 3, "SPELL", 5))
        for i in range(4):
            aggro_cards.append(CardSpec(f"agg_4_{i}", "Berserker", 4, "ATTACK", 6))
        for i in range(4):
            aggro_cards.append(CardSpec(f"agg_draw_{i}", "Quick Tactics", 2, "SPELL", 1, draw_count=2))

        # Control deck: early defensive shields, mid removal, late game bombs
        control_cards = []
        for i in range(6):
            control_cards.append(CardSpec(f"ctrl_ward_{i}", "Holy Ward", 1, "DEFENSE", 3))
        for i in range(6):
            control_cards.append(CardSpec(f"ctrl_shld_{i}", "Iron Bastion", 2, "DEFENSE", 6))
        for i in range(6):
            control_cards.append(CardSpec(f"ctrl_rmv_{i}", "Smite", 3, "SPELL", 5))
        for i in range(4):
            control_cards.append(CardSpec(f"ctrl_draw_{i}", "Deep Meditation", 3, "SPELL", 1, draw_count=2))
        for i in range(4):
            control_cards.append(CardSpec(f"ctrl_guard_{i}", "Royal Guardian", 5, "MINION", 7, hp=8))
        for i in range(2):
            control_cards.append(CardSpec(f"ctrl_bomb_{i}", "Archmage Cataclysm", 6, "SPELL", 10))
        for i in range(2):
            control_cards.append(CardSpec(f"ctrl_titan_{i}", "Ancient Colossus", 7, "MINION", 12, hp=14))

        # Midrange deck: balanced curve
        midrange_cards = []
        for i in range(6):
            midrange_cards.append(CardSpec(f"mid_1_{i}", "Squire", 1, "ATTACK", 2))
        for i in range(6):
            midrange_cards.append(CardSpec(f"mid_2_{i}", "Swordsman", 2, "ATTACK", 3))
        for i in range(6):
            midrange_cards.append(CardSpec(f"mid_3_{i}", "Knight Commander", 3, "ATTACK", 5))
        for i in range(6):
            midrange_cards.append(CardSpec(f"mid_4_{i}", "Paladin Shield", 4, "DEFENSE", 8))
        for i in range(4):
            midrange_cards.append(CardSpec(f"mid_5_{i}", "Dragon Whelp", 5, "ATTACK", 8))
        for i in range(2):
            midrange_cards.append(CardSpec(f"mid_6_{i}", "War Golem", 6, "ATTACK", 10))

        return {
            "Aggro": DeckArchetype("Aggro", "Fast aggressive rushdown", aggro_cards),
            "Control": DeckArchetype("Control", "Defensive attrition and high cost bombs", control_cards),
            "Midrange": DeckArchetype("Midrange", "Tempered tempo with solid stats", midrange_cards)
        }

    def simulate_matchup(self, deck_a: DeckArchetype, deck_b: DeckArchetype, num_games: int = 200) -> Dict[str, Any]:
        wins_a = 0
        wins_b = 0
        total_turns = 0

        engine_ab = CardBattleSimulationEngine(deck_a, deck_b)
        engine_ba = CardBattleSimulationEngine(deck_b, deck_a)
        for i in range(num_games):
            if i % 2 == 0:
                res = engine_ab.run_single_match()
                if res["winner"] == deck_a.name:
                    wins_a += 1
                else:
                    wins_b += 1
            else:
                res = engine_ba.run_single_match()
                if res["winner"] == deck_a.name:
                    wins_a += 1
                else:
                    wins_b += 1
            total_turns += res["turns"]

        winrate_a = (wins_a / num_games) * 100.0
        winrate_b = (wins_b / num_games) * 100.0
        avg_turns = total_turns / float(num_games)

        # Balance check: healthy winrate range is 40% - 60%
        imbalance_flag = False
        warning = "BALANCED"
        if winrate_a > 65.0:
            imbalance_flag = True
            warning = f"OVERPOWERED: {deck_a.name} dominates with {winrate_a:.1f}% winrate"
        elif winrate_a < 35.0:
            imbalance_flag = True
            warning = f"UNDERPOWERED: {deck_a.name} suffers with only {winrate_a:.1f}% winrate"

        return {
            "deck_a": deck_a.name,
            "deck_b": deck_b.name,
            "games": num_games,
            "wins_a": wins_a,
            "wins_b": wins_b,
            "winrate_a": round(winrate_a, 1),
            "winrate_b": round(winrate_b, 1),
            "avg_turns": round(avg_turns, 1),
            "imbalance": imbalance_flag,
            "assessment": warning
        }

    def run_matrix(self, archetypes: Optional[Dict[str, DeckArchetype]] = None, games_per_pair: int = 100) -> List[Dict[str, Any]]:
        archs = archetypes or self.create_sample_archetypes()
        keys = list(archs.keys())
        results = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                da = archs[keys[i]]
                db = archs[keys[j]]
                res = self.simulate_matchup(da, db, num_games=games_per_pair)
                results.append(res)
        return results


if __name__ == "__main__":
    sim = CardBalanceSimulator()
    matrix = sim.run_matrix(games_per_pair=150)
    print("=== CARD BALANCE SIMULATION MATRIX ===")
    for m in matrix:
        print(f"[{m['deck_a']} vs {m['deck_b']}] {m['winrate_a']}% - {m['winrate_b']}% | Avg Turns: {m['avg_turns']} | {m['assessment']}")
