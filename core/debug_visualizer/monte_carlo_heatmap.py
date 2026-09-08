"""
Monte Carlo Simulation Heatmap Visualizer
Formats level difficulty, winrate distributions, and balance risk profiles.
"""

from typing import Dict, List, Any


class MonteCarloHeatmap:
    """Renders tabular win-rate matrices and risk ratings for game balance."""

    @staticmethod
    def render_matrix_table(matchups: List[Dict[str, Any]]) -> str:
        lines = ["=== MONTE CARLO LEVEL & ARCHETYPE BALANCE MATRIX ==="]
        lines.append("| Matchup / Level | Win Rate A | Win Rate B | Avg Duration | Risk Assessment |")
        lines.append("|:---|:---|:---|:---|:---|")
        for m in matchups:
            pair = f"{m.get('deck_a', 'P1')} vs {m.get('deck_b', 'P2')}"
            wra = f"{m.get('winrate_a', 0.0)}%"
            wrb = f"{m.get('winrate_b', 0.0)}%"
            dur = str(m.get("avg_turns", m.get("avg_duration", "N/A")))
            assess = m.get("assessment", "BALANCED")
            lines.append(f"| {pair} | {wra} | {wrb} | {dur} | {assess} |")
        return "\n".join(lines)
