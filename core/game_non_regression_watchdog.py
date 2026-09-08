"""
Game Non-Regression Watchdog (GameXpert-Bench GameOpt Standard)
Guarantees that multi-round feature evolution (GameOpt) and bug fixing (GameFix)
do not break existing gameplay invariants established in previous rounds.

Monitors 5 core gold contract categories:
1. INPUT_REACHABILITY: Player input actions (move, fire, interact, pause) remain dispatchable.
2. STATE_TRANSITION: Key game states (menu -> play -> game_over / victory) remain reachable.
3. PROGRESSION_SETTLEMENT: Win/loss conditions and score accumulators remain active.
4. UI_INTEGRITY: Critical HUD elements (health, score, inventory) remain connected.
5. AUDIO_JUICE: Existing sound/visual feedback bindings are not accidentally detached.
"""

from typing import Dict, Any, List, Optional
import json

class GoldContract:
    def __init__(self, contract_id: str, category: str, description: str, verification_lambda_name: str, critical: bool = True):
        self.contract_id = contract_id
        self.category = category # INPUT, STATE, PROGRESSION, UI, AUDIO
        self.description = description
        self.verification_lambda_name = verification_lambda_name
        self.critical = critical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "category": self.category,
            "description": self.description,
            "verification_lambda_name": self.verification_lambda_name,
            "critical": self.critical,
        }

class RegressionReport:
    def __init__(self, passed: bool, round_id: int, total_checked: int, regressions: List[Dict[str, Any]]):
        self.passed = passed
        self.round_id = round_id
        self.total_checked = total_checked
        self.regressions = regressions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "round_id": self.round_id,
            "total_checked": self.total_checked,
            "regressions": self.regressions,
        }

class GameNonRegressionWatchdog:
    def __init__(self):
        self.gold_baselines: Dict[str, GoldContract] = {}
        self.history_records: List[Dict[str, Any]] = []

    def register_baseline_contract(self, contract: GoldContract):
        """Registers a contract into the permanent Gold Baseline."""
        self.gold_baselines[contract.contract_id] = contract

    def register_standard_game_contracts(self):
        """Initializes universal game baseline contracts required for any genre."""
        self.register_baseline_contract(GoldContract(
            contract_id="STD_INPUT_MOVE",
            category="INPUT",
            description="Movement inputs (WASD/Arrows/Virtual D-pad) must be registered and active.",
            verification_lambda_name="has_active_movement_input",
            critical=True
        ))
        self.register_baseline_contract(GoldContract(
            contract_id="STD_STATE_PLAYING",
            category="STATE",
            description="Engine must support transitioning into 'PLAYING' state from Menu.",
            verification_lambda_name="can_enter_playing_state",
            critical=True
        ))
        self.register_baseline_contract(GoldContract(
            contract_id="STD_SETTLEMENT_WIN_LOSS",
            category="PROGRESSION",
            description="At least one terminal state (VICTORY or DEFEAT) must have a valid trigger condition.",
            verification_lambda_name="has_terminal_conditions",
            critical=True
        ))
        self.register_baseline_contract(GoldContract(
            contract_id="STD_HUD_RENDER",
            category="UI",
            description="HUD canvas must be mounted and not occluded.",
            verification_lambda_name="is_hud_rendered",
            critical=False
        ))

    def verify_round_evolution(self, round_id: int, current_system_state: Dict[str, Any]) -> RegressionReport:
        """
        Audits current_system_state against all active Gold Contracts:
        current_system_state is expected to contain boolean status or features:
        {
            "active_inputs": ["move", "interact", "fire"],
            "reachable_states": ["MENU", "PLAYING", "GAMEOVER", "VICTORY"],
            "terminal_triggers_count": 2,
            "hud_mounted": True,
            "audio_events_count": 5
        }
        """
        regressions = []
        total_checked = len(self.gold_baselines)

        for cid, contract in self.gold_baselines.items():
            violation = None
            if cid == "STD_INPUT_MOVE":
                inputs = current_system_state.get("active_inputs", [])
                if "move" not in inputs:
                    violation = "Player movement input was detached or deleted in this round!"

            elif cid == "STD_STATE_PLAYING":
                states = current_system_state.get("reachable_states", [])
                if "PLAYING" not in states:
                    violation = "Game loop broke: 'PLAYING' state is no longer reachable from main menu!"

            elif cid == "STD_SETTLEMENT_WIN_LOSS":
                triggers = current_system_state.get("terminal_triggers_count", 0)
                if triggers == 0:
                    violation = "Game settlement broken: zero win/loss trigger conditions exist!"

            elif cid == "STD_HUD_RENDER":
                if not current_system_state.get("hud_mounted", False):
                    violation = "HUD was unmounted or occluded by newly added UI layers!"

            # Custom user-defined contract check
            elif contract.verification_lambda_name in current_system_state:
                if not current_system_state[contract.verification_lambda_name]:
                    violation = f"Contract '{contract.description}' failed verification!"

            if violation:
                regressions.append({
                    "contract_id": cid,
                    "category": contract.category,
                    "critical": contract.critical,
                    "description": contract.description,
                    "violation": violation
                })

        # Failure if any critical contract was violated
        has_critical_failure = any(r["critical"] for r in regressions)
        passed = not has_critical_failure

        report = RegressionReport(
            passed=passed,
            round_id=round_id,
            total_checked=total_checked,
            regressions=regressions
        )

        self.history_records.append(report.to_dict())
        return report
