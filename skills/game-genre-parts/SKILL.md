---
name: game-genre-parts
description: |
  福特T型全品类零件库（Ford-T Game Parts Hub）工业化规范。
  专治品类开发重造轮子、卡牌抽弃牌规则冗余、音游判定/连击算分混乱、
  Roguelike房间与羁绊耦合死锁、模拟经营资源管网倒灌、竞速车辆物理漂移手感脱节等问题。
  涵盖卡牌、音游、Roguelike、模拟建造、竞速五大品类预制高精零件与组装流水线。
---

# 福特T型全品类零件库工业化规范

## 核心哲学：搭积木式装配，零从零编写

> **福特制装配线原则**：任何特定游戏品类的底层机械系统（牌堆/手牌/战场、谱面/判定/连击、地下城/羁绊/掉落表、网格/管网/经济、赛道/车辆/橡皮筋/幽灵），都应当作为高精预制零件（GamePartBase）即插即用，通过 `ModularGameAssembler.assemble()` 组装与 `dispatch()` 驱动。

---

## 1. 五大品类零件速查矩阵

| 品类 | 零件 Key | 核心类 | 关键 Action | 职责边界 |
|:---|:---|:---|:---|:---|
| **卡牌 (Card)** | `card_deck` | `CardDeckPart` | `INIT_DECK`, `DRAW`, `DISCARD`, `EXHAUST`, `PEEK` | 抽牌堆/弃牌堆/消耗堆轮转、洗牌与防疲劳 |
| | `card_hand` | `CardHandPart` | `ADD_CARDS`, `PLAY_CARD`, `DISCARD_HAND` | 手牌上限限制、手牌打出、溢出处理 |
| | `card_battlefield` | `CardBattleFieldPart` | `START_TURN`, `SPEND_MANA`, `SUMMON_MINION` | 回合生命周期、费用水晶增长、战线卡槽管理 |
| | `card_effect` | `CardEffectPart` | `EXECUTE_EFFECT` | 伤害吸收、护盾叠算、治疗与Buff结算 |
| | `card_ai` | `CardAIPart` | `DECIDE_ACTION` | 贪心法/收益比出牌启发式决策 |
| **音游 (Rhythm)** | `chart_parser` | `ChartParserPart` | `LOAD_CHART`, `GET_NOTES_IN_WINDOW` | BPM时钟基准、Tap/Hold/Flick/Slide谱面加载 |
| | `note_renderer` | `NoteRendererPart` | `UPDATE_FRAME` | 轨道下落坐标投影、视距进场进度归一化 |
| | `judgment` | `JudgmentPart` | `JUDGE_HIT` | PERFECT(<=40ms) / GREAT(<=80ms) / GOOD(<=120ms) |
| | `score_combo` | `ScoreComboPart` | `RECORD_HIT`, `CALCULATE_FINAL` | 百万分制（90万音符+10万连击）、全连/全P评级 |
| | `chart_editor` | `ChartEditorPart` | `ADD_NOTE`, `QUANTIZE`, `EXPORT_CHART` | UGC谱面创作、1/4、1/8、1/16拍节拍吸附 |
| **肉鸽 (Roguelike)**| `room_gen` | `RoomGenPart` | `GENERATE_DUNGEON` | 确定性种子、网格房间分支布局、门禁拓扑 |
| | `synergy` | `SynergyPart` | `ADD_ITEM`, `REGISTER_RULE`, `EVALUATE_SYNERGIES`| 词条矩阵累积、跨装备阶梯阈值增伤/特效触发 |
| | `loot_table` | `LootTablePart` | `ROLL_LOOT` | 动态幸运值修正、防非保底（Pity Counter） |
| | `meta_progress` | `MetaProgressPart` | `ADD_SOULS`, `UPGRADE_TALENT` | 局外代币积累、局外天赋树与永久被动属性 |
| | `seed_manager` | `SeedManagerPart` | `SET_SEED`, `NEXT_INT`, `DERIVE_SEED` | 随机种子分流（主干/战役/掉落子种子），支持复盘重放 |
| **模拟 (Sim/Build)**| `grid_build` | `GridBuildPart` | `PLACE_BUILDING`, `DEMOLISH`, `QUERY_TILE` | 2D网格占位、多格碰撞体积、建筑拆除与退款 |
| | `resource_flow`| `ResourceFlowPart` | `ADD_NODE`, `CONNECT`, `TICK_FLOW` | 产出者-管道-消费者网络、管网吞吐与断供告警 |
| | `game_clock` | `GameClockPart` | `SET_SPEED`, `TICK` | 游戏日夜循环、四季更迭、0x/1x/2x/5x倍速 |
| | `economy` | `EconomyPart` | `TRANSACTION`, `GET_COMMODITY_PRICE` | 国库收支、供需比动态商品物价定价公式 |
| **竞速 (Racing)** | `spline_track` | `SplineTrackPart` | `SET_WAYPOINTS`, `GET_PROGRESS` | 路径点拟合、完赛百分比、脱轨偏离度检测 |
| | `vehicle_phys` | `VehiclePhysPart` | `APPLY_INPUT` | 油门/刹车/转向/漂移摩擦力/氮气加速动力学 |
| | `rubber_band` | `RubberBandPart` | `CALCULATE_HANDICAP` | 距离差距手感补偿、动态AI追车削弱算法 |
| | `ghost_replay` | `GhostReplayPart` | `START_RECORD`, `RECORD_FRAME`, `SAMPLE_GHOST`| 异步影子车帧采样、回放插值对比 |
| | `lap_timer` | `LapTimerPart` | `START_RACE`, `CROSS_FINISH` | 单圈计时、最快圈速纪录、分段计时点追踪 |

---

## 2. 组装流水线代码范例

```python
from core.ford_t_game_parts_hub import ModularGameAssembler

assembler = ModularGameAssembler()

# 组装一款卡牌肉鸽游戏 (Slay-the-Spire Like)
game = assembler.assemble(
    title="SpireAscent",
    selected_part_keys=["card_deck", "card_hand", "card_battlefield", "card_effect", "synergy", "loot_table"]
)

# 调度零件动作
res = assembler.dispatch("card_deck", "INIT_DECK", {"cards": [{"id": "strike", "cost": 1, "value": 6}]})
print(res.event_name)  # DECK_INITIALIZED
```

## 3. 数值平衡测试要求

1. **卡牌平衡仿真 (`pipeline/card_balance_simulator.py`)**：
   - 必须运行 Monte Carlo 模拟对局，胜率超过 65% 或低于 35% 必须触发警告。
2. **Roguelike 羁绊仿真 (`pipeline/roguelike_synergy_balancer.py`)**：
   - 必须评估词条累积 DPS 膨胀倍数，极端破模比（>2.5x）严禁超过总对局数的 10%。
