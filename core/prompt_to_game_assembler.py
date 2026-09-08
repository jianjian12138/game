"""
Universal Prompt-to-Game Assembler (Article 42)
Inspired by Playabl (AI-native TikTok of Games) & YC W26 Archetype.

Translates natural language prompts into a verified, deterministic 5-Pillar Game Specification:
1. Avatar (Character definition, size, shape, physics anchor)
2. Controls (1-tap, touch-drag, wasd, auto-runner)
3. Scoring & Termination (Win/Loss condition, survival time, target score)
4. Aesthetics (Color palette, theme, particles, render styles)
5. Pacing & Micro-session (Session duration 60-120s, difficulty ramp, spawn cadence)
"""

import json
import uuid
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional


@dataclass
class GameAvatar:
    name: str = "Player"
    shape: str = "circle"  # circle, rect, triangle
    size: float = 18.0     # radius or half-width
    speed: float = 240.0
    color: str = "#00F0FF"
    initial_x: float = 200.0
    initial_y: float = 300.0


@dataclass
class GameControls:
    scheme: str = "one_tap"  # one_tap, touch_drag, wasd_keys, auto_runner
    move_speed: float = 220.0
    jump_force: float = 400.0
    gravity: float = 850.0
    allow_diagonal: bool = True
    fire_rate_sec: float = 0.25


@dataclass
class GameTermination:
    win_condition: str = "reach_score"   # reach_score, survive_time, endless
    lose_condition: str = "collide_hazard" # collide_hazard, fall_out, time_out, zero_lives
    target_score: int = 25
    time_limit_sec: float = 60.0
    max_lives: int = 3


@dataclass
class GameAesthetics:
    theme: str = "neon_cyber"  # neon_cyber, synthwave, minimal_pastel, dark_dungeon
    bg_color: str = "#0d1117"
    primary_color: str = "#00F0FF"
    accent_color: str = "#FFE600"
    hazard_color: str = "#FF0055"
    collectible_color: str = "#00FF66"
    particle_burst_count: int = 16
    grid_overlay: bool = True


@dataclass
class GamePacing:
    target_duration_sec: float = 60.0  # TikTok micro-session format (30-90s)
    difficulty_ramp: str = "linear"    # linear, exponential, wave
    spawn_interval_sec: float = 1.2
    speed_multiplier_per_sec: float = 0.005


@dataclass
class StructuredGameSpec:
    spec_id: str = field(default_factory=lambda: f"game_{uuid.uuid4().hex[:8]}")
    title: str = "Neon Odyssey"
    author: str = "PlayablCreator"
    genre: str = "Arcade"
    prompt: str = ""
    avatar: GameAvatar = field(default_factory=GameAvatar)
    controls: GameControls = field(default_factory=GameControls)
    termination: GameTermination = field(default_factory=GameTermination)
    aesthetics: GameAesthetics = field(default_factory=GameAesthetics)
    pacing: GamePacing = field(default_factory=GamePacing)
    parent_id: Optional[str] = None
    remix_lineage: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredGameSpec":
        data = data.copy()
        if "avatar" in data and isinstance(data["avatar"], dict):
            data["avatar"] = GameAvatar(**data["avatar"])
        if "controls" in data and isinstance(data["controls"], dict):
            data["controls"] = GameControls(**data["controls"])
        if "termination" in data and isinstance(data["termination"], dict):
            data["termination"] = GameTermination(**data["termination"])
        if "aesthetics" in data and isinstance(data["aesthetics"], dict):
            data["aesthetics"] = GameAesthetics(**data["aesthetics"])
        if "pacing" in data and isinstance(data["pacing"], dict):
            data["pacing"] = GamePacing(**data["pacing"])
        return cls(**data)


class PromptToGameAssembler:
    """
    Compiler that maps natural language gameplay prompts into 
    verified 5-Pillar StructuredGameSpecs.
    """

    THEMES = {
        "neon_cyber": {
            "bg_color": "#0a0e17",
            "primary_color": "#00f0ff",
            "accent_color": "#ffe600",
            "hazard_color": "#ff0055",
            "collectible_color": "#00ff88",
        },
        "synthwave": {
            "bg_color": "#1a0826",
            "primary_color": "#ff007f",
            "accent_color": "#00f0ff",
            "hazard_color": "#ff3b00",
            "collectible_color": "#f9ff00",
        },
        "minimal_pastel": {
            "bg_color": "#f7f9fa",
            "primary_color": "#4a90e2",
            "accent_color": "#f5a623",
            "hazard_color": "#d0021b",
            "collectible_color": "#7ed321",
        },
        "dark_dungeon": {
            "bg_color": "#121212",
            "primary_color": "#e0a96d",
            "accent_color": "#ebc999",
            "hazard_color": "#8b0000",
            "collectible_color": "#ffd700",
        },
    }

    @staticmethod
    def compile_prompt(prompt: str, title: Optional[str] = None) -> StructuredGameSpec:
        p_lower = prompt.lower()
        spec = StructuredGameSpec(prompt=prompt)
        spec.title = title or PromptToGameAssembler._extract_title(prompt)

        # 1. Avatar Pillar
        if any(w in p_lower for w in ["plane", "jet", "spaceship", "ship", "飞机", "战机"]):
            spec.avatar.name = "Starfighter"
            spec.avatar.shape = "triangle"
            spec.avatar.size = 16.0
            spec.genre = "Space Shooter"
        elif any(w in p_lower for w in ["bird", "climber", "flappy", "小鸟", "跳跃"]):
            spec.avatar.name = "Chirper"
            spec.avatar.shape = "circle"
            spec.avatar.size = 14.0
            spec.genre = "One-Tap Jumper"
        elif any(w in p_lower for w in ["ninja", "runner", "跑酷"]):
            spec.avatar.name = "Runner"
            spec.avatar.shape = "rect"
            spec.avatar.size = 18.0
            spec.genre = "Endless Runner"
        else:
            spec.avatar.name = "Orb"
            spec.avatar.shape = "circle"
            spec.avatar.size = 16.0
            spec.genre = "Arcade Dodger"

        # 2. Controls Pillar
        if any(w in p_lower for w in ["one-tap", "one tap", "tap", "click", "点击", "一键", "长按", "hold"]):
            spec.controls.scheme = "one_tap"
            spec.controls.jump_force = 380.0
            spec.controls.gravity = 820.0
        elif any(w in p_lower for w in ["drag", "touch", "follow", "拖动", "跟随", "滑动"]):
            spec.controls.scheme = "touch_drag"
            spec.controls.move_speed = 320.0
            spec.controls.gravity = 0.0
        elif any(w in p_lower for w in ["wasd", "arrow", "keys", "方向键", "键盘"]):
            spec.controls.scheme = "wasd_keys"
            spec.controls.move_speed = 260.0
            spec.controls.gravity = 0.0
        else:
            # Default to mobile-friendly touch drag / one-tap
            spec.controls.scheme = "touch_drag"
            spec.controls.gravity = 0.0

        # 3. Termination & Scoring Pillar
        if any(w in p_lower for w in ["survive", "survival", "存活", "生存"]):
            spec.termination.win_condition = "survive_time"
            spec.termination.time_limit_sec = 60.0
        elif any(w in p_lower for w in ["endless", "无尽", "刷分"]):
            spec.termination.win_condition = "endless"
        else:
            spec.termination.win_condition = "reach_score"
            spec.termination.target_score = 30

        # Parse lives if specified
        lives_match = re.search(r"(\d+)\s*(?:条命|次机会|lives|hp)", p_lower)
        if lives_match:
            spec.termination.max_lives = max(1, min(10, int(lives_match.group(1))))
        else:
            spec.termination.max_lives = 3

        # 4. Aesthetics Pillar
        selected_theme = "neon_cyber"
        if any(w in p_lower for w in ["synthwave", "retro", "80s", "霓虹复古"]):
            selected_theme = "synthwave"
        elif any(w in p_lower for w in ["pastel", "clean", "minimal", "清新", "简约", "极简"]):
            selected_theme = "minimal_pastel"
        elif any(w in p_lower for w in ["dark", "dungeon", "horror", "暗黑", "地牢"]):
            selected_theme = "dark_dungeon"

        palette = PromptToGameAssembler.THEMES[selected_theme]
        spec.aesthetics.theme = selected_theme
        spec.aesthetics.bg_color = palette["bg_color"]
        spec.aesthetics.primary_color = palette["primary_color"]
        spec.aesthetics.accent_color = palette["accent_color"]
        spec.aesthetics.hazard_color = palette["hazard_color"]
        spec.aesthetics.collectible_color = palette["collectible_color"]
        spec.avatar.color = palette["primary_color"]

        # 5. Pacing Pillar (TikTok session target)
        duration_match = re.search(r"(\d+)\s*(?:秒|分钟|s|sec|seconds|min)", p_lower)
        if duration_match:
            val = int(duration_match.group(1))
            if "分" in duration_match.group(0) or "min" in duration_match.group(0):
                spec.pacing.target_duration_sec = float(min(180, val * 60))
            else:
                spec.pacing.target_duration_sec = float(min(180, max(15, val)))
        else:
            spec.pacing.target_duration_sec = 60.0

        if spec.termination.win_condition == "survive_time":
            spec.termination.time_limit_sec = spec.pacing.target_duration_sec

        # Spawn interval calculation
        spec.pacing.spawn_interval_sec = 1.0
        spec.pacing.speed_multiplier_per_sec = 0.008

        return spec

    @staticmethod
    def _extract_title(prompt: str) -> str:
        words = prompt.strip().split()
        if len(words) > 0 and len(prompt) <= 24:
            return prompt.strip()
        # Extract meaningful first clause
        clauses = re.split(r"[,;，。！!？?\n]", prompt)
        first = clauses[0].strip()
        if len(first) > 0 and len(first) <= 20:
            return first
        return "Mini " + (words[0].capitalize() if words else "Game")
