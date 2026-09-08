# 🎮 Universal Game Dev Agent Platform — 通用型全品类游戏智能研发平台
# (Universal Full-Genre AI-Native Game Development Platform)

> 🚀 **通用型全品类游戏智能研发中枢 (生产级正式版 v4.3.0)**：
> 本系统为**开放通用型 AI 游戏研发智能体中枢**，不绑定任何特定客户端。**既可完全独立作为命令行开发工具或 Web 工作室运行，也可被 Claude Code (cc)、OpenAI Codex、Hermes-Agent、Cursor/Windsurf 等各类通用 Agent 通过工业标准协议 (MCP / Function Calling / REST / Python SDK) 无缝调用**。
>
> 平台深度融合 **75 位专家级游戏智能体矩阵**、**108 项专业研发技能库**、**35 项预制 Ford-T 工业零件**、**双向 DSL 游戏逻辑热更运行时**、**行为树 AI 决策中枢**、**高精度定频帧同步网络引擎**、**Combat Juice 战斗打击感总线（创伤震屏/顿帧/体积守恒挤压）**、**3D Khronos glTF 2.0 骨骼蒙皮动画系统**、**蒙特卡洛经济平衡仿真器**、**GDC 赛斯·哈德森叙事教育学审计闭环**，并严密集成 **红队一票否决门禁 (Veto Gate)** 与 **微信小游戏 4MB 极速交付打包器**。

[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Universal Agent](https://img.shields.io/badge/Agent-Claude_Code_|_Codex_|_Hermes_|_MCP_|_REST-blueviolet.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Standalone_CLI_|_Web_Canvas_|_WeChat_Minigame-blue.svg)]()
[![Agents & Skills](https://img.shields.io/badge/Experts-75_Agents_|_108_Skills-blue.svg)](./agents/studio_roster.py)
[![Ford-T Parts](https://img.shields.io/badge/Ford--T_Parts-35_Industrial_Parts-purple.svg)](./core/ford_t_game_parts_hub.py)
[![Release Gate](https://img.shields.io/badge/Release_Gate-APPROVED_(100/100)-brightgreen.svg)](./pipeline/test_all_standards.py)
[![Zero-Deps](https://img.shields.io/badge/Zero--Deps-Python_Standard_Library-orange.svg)]()

---

## 📦 平台商业级成品交付矩阵 (Production Deliverables)

平台自带三款完全开箱即用、无跨域限制（直接以 `file://` 双击即可运行）、零残存占位符的工业级标杆交付物：

| 交付项目 | 运行物路径 | 核心技术标准与工业指标 |
| :--- | :--- | :--- |
| **🏆 赛博幸存者 (商业旗舰正式版)** | [`output/cyber_survivor/index.html`](./output/cyber_survivor/index.html)<br>微信包: `output/cyber_survivor/wechat_package/` | **全闭环商业系统**: 局外军火库/永久养成/抽卡/签到、局内三选一技能肉鸽升级、Boss 三阶段 AI。<br>**性能手感**: 零 `Math.hypot`（平方和距离碰撞）、创伤震屏、伤害浮字、单包 140KB（微信首包仅 0.05MB 远低于 4MB 限制）。 |
| **⚙️ 泰坦机甲 (C++ 工业引擎场景架构)** | [`output/industrial_engine_showcase/index.html`](./output/industrial_engine_showcase/index.html) | **工业渲染标准**: DAG 场景图三级级联变换、零-GC `sortKey` 渲染队列、400 条指令折叠为 2 次合批 DrawCall（合批率 99.5%）、预烘焙 80×80 网格贴图、体积守恒挤压拉伸 (`sx*sy=1.0`)。 |
| **🧍 3D 骨骼动画演示系统** | [`output/skeletal_showcase/index.html`](./output/skeletal_showcase/index.html)<br>模型: `output/assets/3d/HeroRigged.gltf` | **Khronos glTF 2.0 标准**: 15 关节全功能人形骨架、网格骨骼权重绑定、Idle/Walk/Attack 三段动画 0.25s 交叉平滑过渡 (CrossFade)、THREE.SkeletonHelper 骨骼调试透视、数据完全内嵌无本地 CORS 报错。 |

---

## 🌐 通用 Agent 跨平台调用与多协议支持 (Multi-Agent Interoperability)

本平台设计原则为 **“协议解耦、无宿主锁死”**，提供 5 种平行的调用方式：

### 1. 独立单独使用 (Standalone CLI & Web Studio)
无需任何外部 AI Agent 客户端，开发者或 CI/CD 流程可直接调用：
```bash
# 全局统一开发命令行 (生产流水线)
python game_agent.py create "赛博幸存者" --genre "2D弹幕射击"

# 启动本地可视化工作室控制台与仪表盘
python server.py --browser --port 8090
```

### 2. Claude Code (`cc`) / Cursor / Windsurf 接入 (标准 MCP 协议)
支持 Anthropic 主导的 **Model Context Protocol (MCP)** 标准，作为外部工具挂载：
- **Claude Code 挂载命令**：
  ```bash
  claude mcp add game-dev-agent python ./game_mcp_server.py
  ```
- **Cursor / Windsurf 配置 (`mcp.json`)**：
  ```json
  {
    "mcpServers": {
      "game-dev-agent": {
        "command": "python",
        "args": ["./game_mcp_server.py"]
      }
    }
  }
  ```
Claude Code 或 Cursor 可自动发现并调用包括装配、平衡模拟、红军对抗、微信打包等 **30+ 个原子研发工具**。

### 3. OpenAI Codex / ChatGPT / Function Calling 智能体接入
支持一键导出 OpenAI 格式的标准 Function Calling Tools 契约：
```bash
python game_mcp_server.py --export-tools > game_tools.json
```
导出的 JSON 数组可直接贴入 OpenAI `client.chat.completions.create(tools=...)` 或 Codex Agent 中。

### 4. Hermes-Agent / AutoGen / CrewAI 原生 Python SDK 导入
基于标准 `pyproject.toml` 规范，任何 Python 智能体框架均可直接引入：
```python
from core.behavior_tree import BTBuilder, Blackboard
from pipeline.commercial_game_factory import CommercialGameFactory
from pipeline.adversarial_red_team import RedTeamInquisitor

# 在任何通用智能体工作流内调用
game = CommercialGameFactory.build_cyber_survivor()
veto_result = RedTeamInquisitor.indict_file("output/cyber_survivor/index.html")
assert veto_result["passed"] is True
```

### 5. 通用 HTTP REST API 接入 (LangChain, Flowise, 跨语言微服务)
启动后台服务后，任何语言 (Node.js, Go, Rust, Java) 均可通过 HTTP 访问：
```bash
python server.py --port 8090
# 接口：
# GET  http://localhost:8090/api/stats
# GET  http://localhost:8090/api/templates
# POST http://localhost:8090/api/generate  (Body: {"title": "太空突围", "genre": "2D射击"})
```

---

## 🕹️ 统一开发者命令行 (Master CLI)

平台提供全局通用命令行入口 [`game_agent.py`](./game_agent.py)（或兼容入口 [`agy_game_cli.py`](./agy_game_cli.py)）：

```bash
# 1. 启动端到端全自动游戏研发生产流水线
python game_agent.py create "游戏标题" --genre "2D弹幕射击"

# 2. 查询 35 项预制零件库与 75 专家名录
python game_agent.py list-parts
python game_agent.py roster

# 3. 模块化装配新游戏架构 (Ford-T 流水线)
python game_agent.py assemble "MyGame" --parts card_deck,card_hand,synergy,loot_table,game_clock

# 4. 运行蒙特卡洛平衡模拟 (500 局对抗仿真与 OP 判定)
python game_agent.py balance --type card --games 500

# 5. 一键打包输出合规微信小游戏 (支持 4MB 分包预检)
python game_agent.py wechat-pack --template survivor_danmaku --out dist/wechat
```

---

## 🧪 工业级回归总测与多维度终审门禁

项目建立了“拒绝形式主义自证循环”的严格无头对抗测试标准体系：

### 1. 13 项全工业级标准全量回归总测 (Master Regression Suite)
覆盖引擎核心底层、网络、音效、美学与全交付物合规性：
```bash
python pipeline/test_all_standards.py
```
- ✅ **Test 1**: 2D C++ 场景图脏标记级联变换与整数合批渲染队列
- ✅ **Test 2**: 3D 人形骨骼蒙皮动画 glTF 2.0 生成器
- ✅ **Test 3**: Web Audio API 自适应动态背景音乐与合成音效系统
- ✅ **Test 4**: AST 跨文件符号图谱完整性扫描 (防 AttributeError)
- ✅ **Test 5**: 定频锁步帧同步网络仿真 (120 帧定点数抗抖动校验)
- ✅ **Test 6**: 移动端硬件功耗与帧预算探针 (16.6ms 预算超标拦截)
- ✅ **Test 7**: VLM 多模态美学评估器 (对比度、排版、主色调工业评分)
- ✅ **Test 8**: 《赛博幸存者》28 项商业化全要素与 0 缺陷审计
- ✅ **Test 9**: 泰坦机甲展示原型 6 大专家缺陷清零实测
- ✅ **Test 10**: 3D 骨骼演示原型 Khronos 标准与离线可运行验证
- ✅ **Test 11**: 对抗式红军一票否决门禁 (严查 `alert()`、`Math.hypot`、半成品 Mock)
- ✅ **Test 12-13**: 架构单元测试与全生命周期断言全绿

### 2. 8 大领域专家联合验收评审团 (Independent Expert Acceptance Panel)
```bash
python expert_review.py
```
涵盖：
1. **架构与系统基础设施**: 35 项预制零件库与增量 DSL Patch 正确性
2. **动作与手感工程**: 6 帧输入缓冲波动拳、Hit-Stop 顿帧与体积守恒挤压拉伸
3. **叙事工程与教学关卡**: GDC 赛斯·哈德森体系、叙事 SLO 达标、自愈无死路
4. **数值平衡与经济系统**: 蒙特卡洛 500 局卡牌仿真、肉鸽膨胀率 0.0%
5. **网络同步与高吞吐性能**: 500 实体对象池与 O(1) 空间哈希、定频锁步闭环
6. **商业化与跨端分发交付**: 微信首包 0.05MB (<4MB)、HTML5 原生装配
7. **C++ 工业引擎场景架构**: 级联变换正确、渲染合批率 99.5%
8. **底层数据导向与红军对抗**: SoA 连续内存、DAG 无环、红军评分 100/100 (0 票否决)

---

## 📁 核心架构目录排版

```text
d:/jianjian12138/game/
├── agents/                     # 75 位专家智能体思维模型与工作流名录
│   ├── agent_mind.py           # 智能体心智中枢与反思循环
│   └── studio_roster.py        # 75 专家智能体能力矩阵定义
├── core/                       # 工业级通用游戏研发引擎底层
│   ├── behavior_tree/          # 行为树 AI 决策中枢
│   ├── dsl_engine/             # 双向 AST 与 DSL 游戏状态热更解析器
│   ├── frame_data/             # 格斗与打击动作帧数据判定表
│   ├── narrative/              # GDC 赛斯·哈德森叙事教学图谱
│   ├── networking/             # 定频锁步帧同步与状态同步网络协议
│   ├── ford_t_game_parts_hub.py# 35 项预制 Ford-T 零件库中枢
│   └── llm_gateway.py          # 智能网关路由 (DeepSeek / Claude / Qwen / Gemini)
├── pipeline/                   # 自动化工程化流水线
│   ├── adversarial_red_team.py # 对抗式红队一票否决门禁 (Veto Gate)
│   ├── commercial_game_factory.py # 商业级游戏工业生成工厂
│   ├── data_driven_compiler.py # 数据驱动小游戏实时编译器
│   ├── release_gate.py         # 商业化发布门禁
│   └── test_all_standards.py   # 13 项工业级标准全量自动化回归总测
├── output/                     # 正式商业级交付物矩阵
│   ├── cyber_survivor/         # 《赛博幸存者》旗舰交付物 (Web + 微信小游戏)
│   ├── industrial_engine_showcase/ # 泰坦机甲 C++ 引擎场景图与合批展示
│   └── skeletal_showcase/      # 3D Khronos glTF 2.0 骨骼蒙皮动画展示
├── dashboard/                  # 本地可视化游戏研发控制台 (HTML5/Canvas)
├── templates/                  # 原型模版工程 (弹幕幸存者、爬塔肉鸽)
├── tests/                      # 标准单元测试套件
├── game_agent.py               # 平台统一生产流水线开发入口 (Master CLI)
├── game_mcp_server.py          # 标准 MCP 协议服务 (供 Claude Code / Cursor 挂载)
├── server.py                   # 本地轻量化 HTTP / WebSocket 服务中枢
└── README.md                   # 平台技术架构总说明文档
```

---

## 📜 开源协议

本项目采用 **MIT 许可证**，详见 [LICENSE](./LICENSE) 文件。
