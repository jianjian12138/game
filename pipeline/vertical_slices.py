"""pipeline/vertical_slices.py — W9 八垂直切片规格目录（真实盘点，非虚构）。

每个切片都锚定到本仓库真实存在的机制零件（core/ford_t_game_parts_hub.py 的 35 个
GamePartBase 子类），以及真实资产画像（W7 程序化音频主题 / W5 2D 资产 / W6 3D 资产）。
这是「数清楚再声称」（Count before claiming）的落地：8 个切片 = 9 大机制品类里挑出的
8 个可装配原型，零件 id 全部可在 ford_t_game_parts_hub.py 中找到。

诚实口径：
  - 本文件只定义「规格」与「真实零件映射」，不替切片生成任何运行证据。
  - 切片运行产物由 pipeline/slice_prototyper.py 生成（确定性的 contract-bearing 可玩骨架），
    再由 pipeline/vertical_slice_validator.py 跑 W8 PlaytestEngine 采集真实证据。
  - 这些切片是「垂直可玩骨架（Slice 2 成熟度）」：真实可运行、真实可玩、真实可达 gameover，
    但不是已上架的完整商业游戏；verdict 如实标注成熟度，不粉饰为 shipped。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# 真实零件品类（来自 ford_t_game_parts_hub.py 的 35 个 part 的 category 字段）
PART_CATEGORIES = [
    "CORE_MECHANIC", "NARRATIVE", "SYSTEM", "CARD", "RHYTHM",
    "ROGUELIKE", "SIM", "RACING", "3D",
]


@dataclass
class SliceSpec:
    id: str
    name: str
    genre: str
    # 锚定的真实零件 id（必须能在 ford_t_game_parts_hub.py 找到；仅作设计溯源，不运行时加载）
    parts: List[str]
    # 真实资产画像
    sfx_theme: str = "cyberpunk"          # 映射 W7 BGM 调式名
    sfx_kinds: List[str] = field(default_factory=lambda: ["laser", "hit", "coin"])
    sprite_refs: List[str] = field(default_factory=list)   # 可挂 W5 2D 资产（缺省程序化绘制）
    model_refs: List[str] = field(default_factory=list)     # 可挂 W6 3D 资产（缺省程序化几何）
    # 切片成熟度目标（垂直切片阶梯：1=契约骨架 2=核心可玩 3=物流战斗 4=打磨保真）
    maturity_target: int = 2
    # 浏览器内机制简述（真实可玩循环，驱动输入→状态→可达 gameover）
    mechanic: str = ""
    # 该切片是否有可运行的现存模板（templates/ 下）
    existing_template: str = ""


# 8 个垂直切片：从 9 大品类里挑 8 个可装配原型，零件 id 全部真实存在
VERTICAL_SLICES: List[SliceSpec] = [
    SliceSpec(
        id="vs_card_roguelike", name="卡牌 Roguelike", genre="card_roguelike",
        parts=["part_card_deck", "part_card_hand", "part_card_battlefield",
               "part_card_effect", "part_card_ai", "part_loot_table",
               "part_synergy", "part_meta_progress"],
        sfx_theme="dorian", sfx_kinds=["ui_click", "hit", "coin"],
        existing_template="templates/card_roguelike",
        maturity_target=2,
        mechanic="抽牌→出牌（Space 打出手中牌）→战斗结算→资源增长；生命耗尽触发 gameover。",
    ),
    SliceSpec(
        id="vs_survivor_danmaku", name="弹幕生存", genre="survivor_danmaku",
        parts=["part_slingshot", "part_runner_stack", "part_game_clock"],
        sfx_theme="cyberpunk", sfx_kinds=["laser", "hit", "powerup"],
        existing_template="templates/survivor_danmaku",
        maturity_target=2,
        mechanic="玩家移动（方向键/WASD）→敌弹下坠→碰撞扣血→耗尽触发 gameover；吃 powerup 回血。",
    ),
    SliceSpec(
        id="vs_rhythm", name="音游", genre="rhythm",
        parts=["part_chart_parser", "part_note_renderer", "part_judgment",
               "part_score_combo", "part_chart_editor"],
        sfx_theme="harmonic_minor", sfx_kinds=["ui_click", "coin", "step"],
        maturity_target=2,
        mechanic="音符下落到判定线→按对应键判定（Perfect/Good/Miss）→连击与分数；Miss 过多扣血触发 gameover。",
    ),
    SliceSpec(
        id="vs_racing", name="竞速", genre="racing",
        parts=["part_spline_track", "part_vehicle_phys", "part_rubber_band",
               "part_ghost_replay", "part_lap_timer"],
        sfx_theme="pentatonic", sfx_kinds=["laser", "powerup", "ui_click"],
        maturity_target=2,
        mechanic="油门（↑）加速→圈速计时（LapTimer）→AI 橡皮筋（RubberBand）追赶→完成圈数判胜/撞墙扣血触发 gameover。",
    ),
    SliceSpec(
        id="vs_factory_sim", name="工厂模拟", genre="factory_sim",
        parts=["part_grid_build", "part_resource_flow", "part_game_clock", "part_economy"],
        sfx_theme="dorian", sfx_kinds=["step", "coin", "ui_click"],
        maturity_target=2,
        mechanic="网格放置（方向键移动光标+Space 放置）→资源流动（ResourceFlow）→经济结算；产能崩溃扣血触发 gameover。",
    ),
    SliceSpec(
        id="vs_roguelike_dungeon", name="Roguelike 地牢", genre="roguelike",
        parts=["part_room_gen", "part_loot_table", "part_synergy",
               "part_meta_progress", "part_seed_manager"],
        sfx_theme="harmonic_minor", sfx_kinds=["hit", "coin", "powerup"],
        maturity_target=2,
        mechanic="种子生成房间（SeedManager）→移动探索→拾取战利品（LootTable）→陷阱扣血触发 gameover。",
    ),
    SliceSpec(
        id="vs_3d_action", name="3D 动作", genre="3d_action",
        parts=["part_scene_graph_3d", "part_mesh_renderer", "part_skeletal_anim",
               "part_tps_camera", "part_navmesh"],
        sfx_theme="cyberpunk", sfx_kinds=["laser", "hit", "explosion"],
        maturity_target=2,
        mechanic="TPS 相机（TPSCamera）环绕→骨骼动画（SkeletalAnim）角色→导航网格（NavMesh）寻路敌人→被击中扣血触发 gameover。",
    ),
    SliceSpec(
        id="vs_narrative_mystery", name="叙事解谜", genre="narrative_mystery",
        parts=["part_clue_investigation", "part_narrative_pedagogy", "part_gacha_store"],
        sfx_theme="pentatonic", sfx_kinds=["ui_click", "coin", "powerup"],
        maturity_target=2,
        mechanic="线索调查（ClueInvestigation）→收集全部线索判胜；错误推理扣血触发 gameover；GachaStore 提供提示道具。",
    ),
]


def get_slice(slice_id: str) -> SliceSpec:
    for s in VERTICAL_SLICES:
        if s.id == slice_id:
            return s
    raise KeyError(f"未知垂直切片: {slice_id}（可用: {[s.id for s in VERTICAL_SLICES]}）")


def all_slice_ids() -> List[str]:
    return [s.id for s in VERTICAL_SLICES]


__all__ = ["SliceSpec", "VERTICAL_SLICES", "PART_CATEGORIES",
           "get_slice", "all_slice_ids"]
