# 🎮  AI-Native 全品类游戏研发工业引擎平台
# ( Full-Genre AI-Native Game Development Platform)

> 🚀 **工业级全品类跨端游戏智能开发中枢**：
> 深度融合 **Ford-T 零件流水线装配架构**（35 项预制工业级零件覆盖 8 大主流品类）、**双向 DSL 游戏逻辑热更运行时**、**行为树 AI 决策中枢**、**高精度帧同步/状态同步网络引擎**、**Combat Juice 战斗打击感打击停顿/震屏总线**、**卡牌与肉鸽蒙特卡洛平衡模拟器**、**GDC 赛斯·哈德森叙事教育学与 SLO 闭环审计引擎**，并支持 **一键微信小游戏 4MB 门禁打包与分包审计**。

[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Web_Canvas_|_WeChat_Minigame_|_Python-blue.svg)]()
[![Ford-T Parts](https://img.shields.io/badge/Ford--T_Parts-35_Industrial_Parts-purple.svg)](./core/ford_t_game_parts_hub.py)
[![Release Gate](https://img.shields.io/badge/Release_Gate-APPROVED-brightgreen.svg)](./RELEASE_AUDIT_REPORT.md)
[![Zero-Deps](https://img.shields.io/badge/Zero--Deps-Python_Standard_Library-orange.svg)]()

---

## 🌟 核心子系统与工业矩阵

| 子系统模块 | 核心源码位置 | 功能描述与工业标准 |
| :--- | :--- | :--- |
| **Ford-T 零件装配中枢** | [`core/ford_t_game_parts_hub.py`](file:///d:/jianjian12138/game/core/ford_t_game_parts_hub.py) | **35 项标准化工业零件**，覆盖 Core, Card, Rhythm, Roguelike, Builder/Sim, Racing, 3D 与 Narrative 等全品类 |
| **叙事教育学与 SLO 引擎** | [`core/narrative_pedagogy_engine.py`](file:///d:/jianjian12138/game/core/narrative_pedagogy_engine.py) | GDC 赛斯·哈德森体系：Wordsmith/Sensemaker/Advocate 三角色流水线、死路孤岛审计、机制咬合度、字数预算与遗留交接自愈 |
| **战斗打击感流水线** | [`core/combat_juice_bus.py`](file:///d:/jianjian12138/game/core/combat_juice_bus.py) | 3~12 帧 Hit-Stop 顿帧、非线性 $Trauma^2$ 震屏、体积守恒 Squash-Stretch ($s_x \cdot s_y = 1$)、阻尼浮字与火花粒子 |
| **帧数据与判定盒系统** | [`core/frame_data/`](file:///d:/jianjian12138/game/core/frame_data/) | 6 帧先进制输入缓冲、Startup/Active/Recovery 帧表、Hitbox/Hurtbox/Pushbox 三层 AABB 几何盒 |
| **高并发弹幕与空间索引** | [`core/bullet_system/`](file:///d:/jianjian12138/game/core/bullet_system/) | 500+ 对象池复用、单帧 $O(1)$ 空间哈希网格碰撞加速、Spiral/Radial/Aimed 弹幕模式生成器 |
| **双向 DSL 逻辑解释器** | [`core/dsl_engine/`](file:///d:/jianjian12138/game/core/dsl_engine/) | 零编译极速热重载，内置 Card / Bullet / Skill / Chart 四大领域方言与语义校验 |
| **行为树决策 AI** | [`core/behavior_tree/`](file:///d:/jianjian12138/game/core/behavior_tree/) | Composite/Decorator/Action 节点、黑板机制与格斗/Boss多阶段/恐怖追逐/动态橡皮筋 4 套预设 AI |
| **多通道节拍音频引擎** | [`core/audio/`](file:///d:/jianjian12138/game/core/audio/) | 单调时钟精确音画同步、BGM/SFX/Voice/UI 独立通道衰减与 2D 距离平方立体声 |
| **动态光照与战争迷雾** | [`core/lighting/`](file:///d:/jianjian12138/game/core/lighting/) | 2D 阴影投射、手电筒恐怖闪烁衰减、昼夜循环环境光与已探索/当前可见战争迷雾 |
| **网络多端同步套件** | [`core/networking/`](file:///d:/jianjian12138/game/core/networking/) | 锁步同步 (Lockstep Sync)、状态增量压缩同步 (Delta StateSync)、客户端预测回滚与断线重连 |
| **卡牌与肉鸽数值平衡** | [`pipeline/card_balance_simulator.py`](file:///d:/jianjian12138/game/pipeline/card_balance_simulator.py) | 蒙特卡洛万局对抗模拟、斩杀回合分布、标签协同联动效应溢出 (>2.5x) 自动告警 |
| **A/B 测试与数据埋点** | [`pipeline/player_analytics/`](file:///d:/jianjian12138/game/pipeline/player_analytics/) | 确定性 SHA-256 分流、Z-score 假设检验显著性分析、漏斗转化、D1~D30 留存与空间热力图 |
| **UGC 内容创作套件** | [`core/ugc/`](file:///d:/jianjian12138/game/core/ugc/) | 关卡编辑器 (连通性校验)、音游谱面量化镜像、赛道样条曲线闭环验证与 Base64 紧凑分享口令 |
| **商业化发布门禁** | [`pipeline/release_gate.py`](file:///d:/jianjian12138/game/pipeline/release_gate.py) | 自动化全套回归测试套件运行、微信小游戏 4MB 首包预算审计与发布认证报告 |
| **微信小游戏适配打包** | [`pipeline/wechat_packager.py`](file:///d:/jianjian12138/game/pipeline/wechat_packager.py) | Canvas/DOM/Touch/Audio 抹平适配器，一键输出微信开发者工具工程包 |

---

## 🕹️ 统一开发者命令行 (Master CLI)

平台提供全局统一命令行入口 [`agy_game_cli.py`](file:///d:/jianjian12138/game/agy_game_cli.py)：

### 1. 查询 35 项预制零件库
```bash
python agy_game_cli.py list-parts
```

### 2. 模块化装配游戏架构
```bash
python agy_game_cli.py assemble "MyCyberRogue" --parts card_deck,card_hand,synergy,loot_table,game_clock
```

### 3. 运行蒙特卡洛平衡模拟
```bash
# 模拟 500 局卡牌流派对抗 (快攻 vs 控制 vs 中速)
python agy_game_cli.py balance --type card --games 500

# 模拟 1000 次肉鸽神力遗物羁绊乘数与超标 (OP) 检测
python agy_game_cli.py balance --type roguelike --games 1000
```

### 4. 商业化质量发布门禁 (Release Gate)
```bash
python agy_game_cli.py audit
```

### 5. 专家团队多部门终审验收 (Expert Review)
```bash
python expert_review.py
```

### 6. 查看预制可试玩游戏原型
```bash
python agy_game_cli.py templates
```

### 7. 一键打包输出微信小游戏
```bash
# 打包弹幕幸存者原型为微信小游戏工程
python agy_game_cli.py wechat-pack --template survivor_danmaku --out dist/wechat --orientation portrait

# 打包爬塔卡牌原型为微信小游戏工程
python agy_game_cli.py wechat-pack --template card_roguelike --out dist/wechat_card --orientation landscape
```

---

## 🎮 预制可试玩原型目录 (Playable Archetypes)

1. **弹幕幸存者 (Survivor Danmaku)**:
   - 核心引擎: [`templates/survivor_danmaku/danmaku_engine.py`](file:///d:/jianjian12138/game/templates/survivor_danmaku/danmaku_engine.py)
   - 试玩页面: [`templates/survivor_danmaku/index.html`](file:///d:/jianjian12138/game/templates/survivor_danmaku/index.html)
   - 特色: 500+ 发弹幕空间网格碰撞优化、经验磁力吸附、怪物狂潮、极简触摸/虚拟摇杆控制。
2. **爬塔卡牌肉鸽 (Card Roguelike)**:
   - 核心引擎: [`templates/card_roguelike/card_game_engine.py`](file:///d:/jianjian12138/game/templates/card_roguelike/card_game_engine.py)
   - 试玩页面: [`templates/card_roguelike/index.html`](file:///d:/jianjian12138/game/templates/card_roguelike/index.html)
   - 特色: 动态手牌悬浮透视、法力水晶、意图预警系统、火系标签伤害叠层羁绊、浮字跳字打击感。
3. **战斗打击感格斗沙盒 (Combat Arena Showcase)**:
   - 试玩页面: [`build/playable_showcase.html`](file:///d:/jianjian12138/game/build/playable_showcase.html)
   - 特色: Hit-Stop 顿帧演示、方向火花粒子、体积守恒挤压拉伸、多段连击取消。

---

## 🧪 自动化测试与工业级验收验证矩阵

本源码仓库已配置生产级 .gitignore 彻底排除 output/ 本地编译产物，纯源码仓库体积精简至约 5MB，所有验证逻辑均统一集成入自包含生产发布门禁：

```bash
# 1. 运行自包含商业化发布门禁 (覆盖底层 7 大子系统与微信 4MB 预算硬指标)
python pipeline/release_gate.py
# 或使用全局 CLI
python agy_game_cli.py audit

# 2. 召开 6 大部门联合专家评审团验收并生成终审报告
python expert_review.py
```

执行后将全自动生成并更新：
- 📜 [`RELEASE_AUDIT_REPORT.md`](file:///d:/jianjian12138/game/RELEASE_AUDIT_REPORT.md)：7 大子系统自包含质量门禁报告
- 🏆 [`FINAL_ACCEPTANCE_REPORT.md`](file:///d:/jianjian12138/game/FINAL_ACCEPTANCE_REPORT.md)：6 大核心部门专家联合签署终审合格证书

