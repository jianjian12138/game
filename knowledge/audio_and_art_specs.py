#!/usr/bin/env python3
"""
audio_and_art_specs.py: 视听资产、程序化音效包络 (ADSR) 与色彩无障碍规范知识库
为技术美术与音频总监提供纯原生 WebAudio 合成参数、调色板与无障碍矩阵。
"""
from typing import Dict, List, Any

class AudioAndArtSpecsKnowledge:

    # 1. 经典程序化游戏音效 ADSR 包络参数大典
    PROCEDURAL_SFX_PRESETS = {
        "laser_shoot": {
            "type": "sawtooth",
            "start_freq": 650,
            "end_freq": 90,
            "attack_sec": 0.005,
            "decay_sec": 0.12,
            "sustain_vol": 0.01,
            "release_sec": 0.05,
            "description": "街机激光射击下潜音效"
        },
        "explosion_boom": {
            "type": "noise", # 白噪声
            "filter_type": "lowpass",
            "start_filter_freq": 1200,
            "end_filter_freq": 40,
            "attack_sec": 0.01,
            "decay_sec": 0.45,
            "sustain_vol": 0.0,
            "release_sec": 0.1,
            "description": "重度爆炸与破裂音效"
        },
        "coin_pickup": {
            "type": "sine",
            "notes": [1046.5, 1318.5], # C6 ➔ E6 双音阶琶音
            "duration_per_note_sec": 0.06,
            "description": "清脆金币与宝石拾取双音阶"
        },
        "jump_bounce": {
            "type": "triangle",
            "start_freq": 160,
            "end_freq": 380,
            "attack_sec": 0.01,
            "decay_sec": 0.15,
            "description": "轻盈跳跃向上滑动音调"
        },
        "player_hit_damage": {
            "type": "square",
            "start_freq": 180,
            "end_freq": 60,
            "attack_sec": 0.005,
            "decay_sec": 0.18,
            "description": "受击低沉顿挫音效"
        },
        "victory_fanfare": {
            "type": "triangle",
            "notes": [523.25, 659.25, 783.99, 1046.50], # C5-E5-G5-C6 大三和弦琶音
            "duration_per_note_sec": 0.12,
            "description": "胜利与大获全胜激昂号角"
        }
    }

    # 2. 经典工业级配色方案体系 (Color Palettes)
    PALETTES = {
        "cyberpunk_neon": {
            "bg": "#0b0d19",
            "panel": "#161b22",
            "primary": "#00eeff",   # 青色高光
            "secondary": "#ff3366", # 荧光粉
            "accent": "#ffe600",    # 霓虹黄
            "text": "#c9d1d9"
        },
        "oriental_ink": {
            "bg": "#1e1b18",        # 宣纸墨褐
            "panel": "#2b2621",
            "primary": "#dfbc7a",   # 古朴雅金
            "secondary": "#d9383a", # 丹砂红
            "accent": "#2e7a5c",    # 翡翠竹青
            "text": "#f0e6d2"
        },
        "retro_arcade": {
            "bg": "#000000",
            "panel": "#111111",
            "primary": "#58a6ff",
            "secondary": "#3fb950",
            "accent": "#ffd700",
            "text": "#ffffff"
        }
    }

    # 3. 无障碍色盲色弱滤镜矩阵 (Accessibility Matrices)
    COLOR_BLIND_MATRICES = {
        "protanopia": [ # 红色盲矫正矩阵
            0.567, 0.433, 0.000,
            0.558, 0.442, 0.000,
            0.000, 0.242, 0.758
        ],
        "deuteranopia": [ # 绿色盲矫正矩阵
            0.625, 0.375, 0.000,
            0.700, 0.300, 0.000,
            0.000, 0.300, 0.700
        ]
    }

    # 4. 自适应多轨动态混音与低通滤波矩阵 (Adaptive Dynamic Mix Matrix)
    DYNAMIC_ADAPTIVE_MIX_MATRIX = {
        "calm_exploration": {
            "bpm": 95,
            "lowpass_cutoff_hz": 800, # 柔和低通氛围
            "sub_bass_boost_db": 0,
            "description": "探索与宁静待机阶段"
        },
        "combat_engagement": {
            "bpm": 128,
            "lowpass_cutoff_hz": 3500, # 敞开全频高音与打击通透感
            "sub_bass_boost_db": 3.5,
            "description": "白刃战与激烈交火阶段"
        },
        "boss_frenzy": {
            "bpm": 150,
            "lowpass_cutoff_hz": 12000, # 极度高亢与警报张力
            "sub_bass_boost_db": 6.0,
            "description": "Boss狂暴与残血决战阶段"
        }
    }
