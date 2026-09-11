---
name: game-dsl-engine
description: |
  通用数据驱动语言（DSL）引擎黄金法则。
  专治卡牌效果硬编码、弹幕模式写死、技能配置分散、谱面无法热更新等问题。
  涵盖 DSL 四大方言（卡牌/弹幕/技能/谱面）、解析→校验→执行管线、
  条件表达式系统和热重载开发工作流。
  当游戏中出现效果/行为需要用数据驱动描述时必须遵循。
---

# DSL引擎黄金法则

## 🔥 核心原则：数据驱动，零硬编码

> **黄金律**：任何游戏中超过3个以上的"效果/行为"，都必须抽象为DSL，不得硬编码。
> 违反此规则将导致：每新增1个卡牌/技能需改动代码 → 策划无法独立调整 → 上线速度崩溃。

```
❌ 错误做法：
def fireball_effect(target):
    target.hp -= 6
    if "burn" in target.tags:
        for adj in target.adjacent:
            adj.hp -= 2

✅ 正确做法：
engine = DSLEngine(dialect=CardEffectDSL())
ast = engine.load("effects/fireball.yaml")
events = engine.execute(ast, context)
```

---

## 📦 模块位置

```
core/dsl_engine/
├── __init__.py          ← DSLEngine 统一入口
├── dsl_parser.py        ← YAML/JSON → AST
├── dsl_runtime.py       ← AST → 效果事件列表
├── dsl_validator.py     ← 静态校验
├── dsl_hot_reload.py    ← 开发模式热重载
└── dialects/
    ├── card_effect_dsl.py     ← 卡牌方言
    ├── bullet_pattern_dsl.py  ← 弹幕方言
    ├── skill_effect_dsl.py    ← 技能方言
    └── chart_note_dsl.py      ← 谱面方言
```

---

## 🃏 卡牌效果DSL（CardEffectDSL）

### 标准 YAML 格式
```yaml
id: fireball           # 必须：唯一ID
name: 火球术
cost: 3                # 法力值消耗 (0-20)
rarity: common         # common/rare/epic/legendary
card_type: spell       # spell/minion/weapon/secret/hero_power
effect:
  - type: damage
    target: enemy_single
    value: 6
  - type: damage
    target: enemy_adjacent
    value: 2
    condition: target_has_tag(burn)   # 条件效果
```

### 随从牌格式
```yaml
id: water_elemental
card_type: minion
cost: 4
stats: {atk: 3, hp: 6}
ability:
  - on_play:
      - type: debuff
        target: enemy_single
        stat: spd
        value: -1
        duration: 2
```

### 支持的效果类型
| type | 说明 | 必要参数 |
|------|------|---------|
| damage | 造成伤害 | target, value |
| heal | 回复生命 | target, value |
| buff | 强化属性 | target, stat, value, duration |
| debuff | 弱化属性 | target, stat, value, duration |
| draw | 抽牌 | count |
| spawn | 召唤单位 | unit_id, position |

### 支持的条件表达式
- `target_has_tag(burn)` — 目标有指定标签
- `hand_size_above(3)` — 手牌超过N张
- `board_count_below(4)` — 我方场面不足N个
- `opponent_hp_below(10)` — 对手血量低于N

---

## 🔫 弹幕模式DSL（BulletPatternDSL）

### 标准 YAML 格式
```yaml
id: spiral_wave
loop: true             # 循环发射
global_speed: 1.0      # 全局速度缩放
pattern:
  - type: fire
    count: 12
    spread: 360         # 全向均匀分布
    speed: 4.0
    aimed: false        # 不瞄准玩家
    bullet:
      sprite: bullet_red
      damage: 1
      lifetime: 5.0
  - type: wait
    frames: 20          # 等待20帧
  - type: fire
    count: 8
    spread: 360
    offset_angle: 15    # 旋转15度偏移
    speed: 3.0
```

### 步骤类型
| type | 说明 |
|------|------|
| fire | 发射一批子弹 |
| wait | 等待 N 帧 |
| aim | 锁定玩家方向 |
| rotate | 旋转发射角度 |
| repeat | 重复整个序列 |

---

## ⚔️ 技能效果DSL（SkillEffectDSL）

### 标准 YAML 格式
```yaml
id: thunder_strike
cooldown: 3.0
cast_range: 8.0
area:
  shape: circle         # circle/cone/rectangle/line
  radius: 2.5
effect:
  - type: damage
    target: area_targets
    value: 40
    tags: [lightning, aoe]
  - type: stun
    target: area_targets
    duration: 0.8
  - type: vfx
    asset: vfx_thunder
  - type: dot           # 持续伤害
    target: hit_target
    damage_per_tick: 5
    tick_interval: 1.0
    duration: 4.0
    tags: [poison]
```

---

## 🎵 谱面DSL（ChartNoteDSL）

### 标准 YAML 格式
```yaml
id: sample_chart
bpm: 138
offset: 0.05           # 音频偏移校正（秒）
lanes: 4               # 轨道数
notes:
  - beat: 1.0          # 拍数（自动转换为时间戳）
    lane: 2            # 轨道 (0-3)
    type: tap
  - beat: 2.0
    lane: 3
    type: hold
    duration: 1.0      # Hold 持续1拍
  - beat: 3.0
    lane: 0
    type: flick
    direction: up
```

---

## 🔧 使用流程

### 标准开发工作流
```python
from core.dsl_engine import DSLEngine
from core.dsl_engine.dialects import CardEffectDSL

# 1. 创建引擎（选择方言）
engine = DSLEngine(dialect=CardEffectDSL())

# 2. 开发时启用热重载
engine.enable_hot_reload(
    watch_dir="game_data/effects/",
    callback=lambda path, ast: game.reload_card(ast["id"], ast)
)

# 3. 加载并执行
ast = engine.load("game_data/effects/fireball.yaml")
events = engine.execute(ast, context={
    "caster": player,
    "target": enemy,
    "board": board_state,
})

# 4. 处理效果事件
for event in events:
    game_world.apply_event(event)
```

### 注册自定义效果处理器
```python
def handle_teleport(effect, context, source_id):
    return [{"type": "teleport", "source_id": source_id,
             "target": effect["target"],
             "destination": effect["destination"]}]

engine.runtime.register_handler("teleport", handle_teleport)
```

---

## ⚠️ 强制约束

1. **所有卡牌/技能/弹幕/谱面** 必须通过 DSL 定义，禁止在 Python 中写效果逻辑
2. **方言校验必须通过**：`engine.load()` 内部自动校验，校验失败时直接抛出异常，不得忽略
3. **条件表达式** 只能使用文档中列出的安全子集，禁止使用 `eval()` 或 `exec()`
4. **效果事件** 是纯数据（dict），不得在事件中包含可执行代码或引用
5. **热重载** 仅限开发/测试环境，生产包必须禁用（防止运行时解析开销）

---

## 🏁 里程碑验收标准（M1）

> Agent 能用 YAML 写出一张可执行的卡牌效果，零 Python 硬编码。
> 测试命令：`python -m pytest tests/test_dsl_engine.py -v`
