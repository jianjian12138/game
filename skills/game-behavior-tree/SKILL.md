---
name: game-behavior-tree
description: |
  行为树（Behavior Tree）黄金法则。专治游戏AI硬编码if-else地狱、
  Boss行为写死难维护、NPC逻辑复杂度爆炸等问题。
  涵盖标准节点库（Sequence/Selector/Parallel/Decorator）、黑板共享状态、
  YAML构建器和4套现成AI预设（格斗/Boss/恐怖/竞速）。
  当任何游戏对象需要"智能决策"时必须遵循。
---

# 行为树黄金法则

## 🔥 核心原则：用树取代 if-else

> **黄金律**：游戏AI超过3层条件判断，就必须改用行为树。
> if-else地狱的后果：Boss新增一个阶段 = 修改10处代码 = 引入3个Bug。

```
❌ 错误做法（if-else地狱）：
def boss_update(self):
    if self.hp < 0.3:
        if not self.phase3_triggered:
            self.trigger_phase3()
        if self.cooldown_timer <= 0:
            if self.distance < 3:
                self.charge()
            else:
                self.barrage()
    elif self.hp < 0.6:
        ...

✅ 正确做法（行为树）：
tree = BTBuilder.from_yaml("presets/bt_boss_phases.yaml", registry)
status = tree.tick(blackboard)
```

---

## 📦 模块位置

```
core/behavior_tree/
├── __init__.py          ← 公开API
├── bt_nodes.py          ← 全节点库
├── bt_blackboard.py     ← 共享黑板
├── bt_builder.py        ← YAML→树实例
├── bt_debugger.py       ← 终端可视化调试
└── presets/
    ├── bt_fighting_ai.yaml    ← 格斗AI
    ├── bt_boss_phases.yaml    ← Boss分阶段
    ├── bt_horror_npc.yaml     ← 恐怖NPC
    └── bt_rubber_band_ai.yaml ← 竞速橡皮筋
```

---

## 🧩 节点类型速查

### 组合节点（Composite）
| 节点 | 逻辑 | 适用场景 |
|------|------|---------|
| `Sequence` | AND — 全成功才成功 | 执行步骤序列（先检查→再行动） |
| `Selector` | OR — 一个成功即成功 | 按优先级选择行为 |
| `Parallel` | 同时执行所有子节点 | 移动+攻击+播放动画同步进行 |

### 修饰节点（Decorator）
| 节点 | 功能 |
|------|------|
| `Inverter` | 翻转结果（SUCCESS↔FAILURE） |
| `Repeater(times=N)` | 重复N次（-1=无限） |
| `Timeout(seconds)` | 超时强制FAILURE |
| `Cooldown(seconds)` | 成功后进入冷却期 |

### 叶子节点（Leaf）
| 节点 | 功能 |
|------|------|
| `Condition(fn)` | 检查条件，fn(bb)→bool |
| `Action(fn)` | 执行动作，fn(bb)→NodeStatus |

---

## 🔧 标准使用流程

### 完整集成示例
```python
from core.behavior_tree import BTBuilder, Blackboard, BTDebugger, NodeStatus

# 1. 定义动作注册表（将动作名映射到Python函数）
def perform_basic_attack(bb: Blackboard) -> NodeStatus:
    target = bb.get("target")
    if target is None:
        return NodeStatus.FAILURE
    target.take_damage(10)
    return NodeStatus.SUCCESS

def perform_charge(bb: Blackboard) -> NodeStatus:
    # 冲锋需要多帧，返回 RUNNING 表示进行中
    charge_progress = bb.get("charge_progress", 0)
    if charge_progress < 1.0:
        bb.set("charge_progress", charge_progress + 0.1)
        return NodeStatus.RUNNING
    bb.set("charge_progress", 0)
    bb.get("target").take_damage(30)
    return NodeStatus.SUCCESS

registry = {
    "basic_attack":    perform_basic_attack,
    "charge_attack":   perform_charge,
    "skill_attack":    lambda bb: NodeStatus.SUCCESS,  # 占位
    # ... 其他动作
}

# 2. 从 YAML 构建树
tree = BTBuilder.from_yaml(
    "core/behavior_tree/presets/bt_boss_phases.yaml",
    action_registry=registry,
)

# 3. 初始化黑板
bb = Blackboard({
    "hp_percent": 100,
    "target": player,
    "distance_to_player": 5.0,
    "phase2_triggered": False,
    "phase3_triggered": False,
})

# 4. 绑定黑板监听（可选）
bb.on_change("hp_percent", lambda old, new:
    print(f"Boss HP: {old:.0f}% → {new:.0f}%"))

# 5. 开发时使用调试器包裹
debugger = BTDebugger(tree, print_every=60)  # 每60帧打印一次

# 6. 游戏循环中 tick
def boss_update(delta_time: float):
    bb.set("hp_percent", boss.hp / boss.max_hp * 100)
    bb.set("distance_to_player", boss.distance_to(player))
    debugger.tick(bb)   # 开发时用 debugger，发布时用 tree
```

---

## 📋 YAML 语法参考

### 完整节点字典
```yaml
# Sequence
- type: Sequence
  name: 攻击序列
  children: [...]

# Selector  
- type: Selector
  name: 行为选择
  children: [...]

# Cooldown 修饰
- type: Cooldown
  cooldown: 5.0
  child:
    type: Action
    action: special_attack

# Timeout 修饰
- type: Timeout
  time_limit: 10.0
  child:
    type: Action
    action: chase_player

# Inverter 修饰
- type: Inverter
  child:
    type: Condition
    key: phase2_triggered
    op: has

# Condition（黑板键比较）
- type: Condition
  name: HP低于30%
  key: hp_percent
  op: below      # below/above/equal/has
  threshold: 30

# Action
- type: Action
  name: 执行攻击
  action: basic_attack   # 对应注册表中的键名
```

---

## 🎯 四套AI预设速查

### Boss分阶段（bt_boss_phases.yaml）
- Phase 3（HP<30%）：全屏弹幕 + 狂暴冲锋
- Phase 2（HP<60%）：范围爆炸 + 冲锋
- Phase 1（HP≥60%）：技能循环 + 普攻
- **关键特性**：入场演出仅触发一次（Inverter+Condition保证）

### 格斗AI（bt_fighting_ai.yaml）
- 优先级：反击 > 近战爆发 > 中距离 > 远距离
- 距离阈值：<2近战，2-5中距，>5远程
- **关键特性**：必杀技8s冷却，特攻3s冷却

### 恐怖NPC（bt_horror_npc.yaml）
- 状态顺序：攻击 > 追逐(30s超时) > 调查(8s超时) > 感知 > 巡逻
- **关键特性**：追逐超时自动重置，听觉/视觉双感知

### 竞速橡皮筋（bt_rubber_band_ai.yaml）
- 落后>2名：强力加速+走捷径
- 落后：轻微加速
- 领先>3名：模拟失误减速
- **关键特性**：动态平衡竞争感，防止玩家感到无聊

---

## ⚠️ 强制约束

1. **所有游戏AI** 超过3层决策必须使用行为树，禁止嵌套 if-else
2. **动作函数** 必须是纯函数（只通过黑板读写状态），禁止直接修改游戏对象
3. **Condition节点** 必须是幂等的（多次调用结果相同），不得有副作用
4. **RUNNING状态** 只用于真正需要多帧执行的动作（移动/动画），不要滥用
5. **黑板键名** 使用 snake_case，必须在 YAML 和注册表中保持一致

---

## 🏁 里程碑验收标准（M2）

> Boss行为可用 BT YAML 描述，三阶段切换自动触发，不改一行 Python 代码。
