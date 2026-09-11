# 🎮 Universal Game Dev Agent Platform
### 通用型全品类 AI 原生游戏智能研发工业化平台

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-brightgreen.svg" alt="License"></a>
  <a href="./agents/studio_roster.py"><img src="https://img.shields.io/badge/Experts-82_Agents_|_114_Skills-blueviolet.svg" alt="Experts"></a>
  <a href="./core/ford_t_game_parts_hub.py"><img src="https://img.shields.io/badge/Ford--T_Parts-35_Industrial_Parts-purple.svg" alt="Ford-T Parts"></a>
  <a href="./core/host_contract.py"><img src="https://img.shields.io/badge/Platforms-Web_|_Godot_|_MiniProgram_|_Desktop-blue.svg" alt="Platforms"></a>
  <a href="./game_mcp_server.py"><img src="https://img.shields.io/badge/Protocols-CLI_|_MCP_|_REST_|_FunctionCalling-orange.svg" alt="Protocols"></a>
  <a href="./pipeline/test_all_standards.py"><img src="https://img.shields.io/badge/Release_Gate-G0~G7_Audited-success.svg" alt="Release Gate"></a>
</p>

---

## 📖 平台简介 (Overview)

**Universal Game Dev Agent Platform** 是一个面向游戏工业化研发的通用型智能体协同平台。平台摒弃了传统的“单模型黑盒生代码”模式，创新采用 **“6 大部门 82 位专家角色矩阵 + Ford-T 工业化零件组装 + G0~G7 自动化质量门禁”** 的工程体系。

平台不绑定任何特定客户端，既可作为独立命令行（CLI）或本地可视化工作室运行，也可通过 **MCP 协议、OpenAI Function Calling、Python SDK 或 HTTP REST API** 无缝挂载到 Claude Code、Cursor、Windsurf、AutoGen、CrewAI 等外部智能体框架中。

```
                              ┌──────────────────────────────────────────────┐
                              │  用户/外部智能体 (CLI / MCP / REST / WebUI) │
                              └──────────────────────┬───────────────────────┘
                                                     │
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       游戏研发协同中枢 (StudioEngine)                                      │
├────────────────────────────────────────┬───────────────────────────────────┬───────────────────────────────┤
│    👥 82 位专业智能体角色矩阵 (Roster) │   🧩 35 个 Ford-T 工业预制零件    │  🛡️ G0~G7 质量门禁系统 (Gate) │
│    • 制作统筹组 (11 Agents)            │   • 战斗/移动/弹幕/状态机组件     │  • G0: 依赖与环境合规检测     │
│    • 策划数值组 (10 Agents)            │   • 虚拟背包/经济与三选一抽卡     │  • G1: 需求契约与规格收敛     │
│    • 引擎技术组 (25 Agents)            │   • 确定性时钟/输入缓冲/命中箱    │  • G2: 架构规范与防坏味道     │
│    • 美术视效组 (16 Agents)            │   • 动态光照/阴影/战争迷雾系统    │  • G3: 自动化逻辑跑测审计     │
│    • 音频工程组 (7 Agents)             │   • 网络对战 (锁步/状态同步/回放) │  • G4: 运行时防伪试玩采样     │
│    • 质量发版组 (13 Agents)            │   • UGC 关卡/谱面/赛道编辑器      │  • G5-G7: 多端分发与发布就绪  │
└────────────────────────────────────────┴───────────────────────────────────┴───────────────────────────────┘
                                                     │
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    跨平台统一宿主契约 (HostContract)                                       │
├──────────────────────┬──────────────────────┬──────────────────────────────┬───────────────────────────────┤
│  🌐 Web Canvas/WebGL │   🤖 Godot 4.x PC    │      📱 微信小游戏 (WeChat)   │    💻 桌面 Shell (PC Native)  │
│  60fps 确定性主循环  │  GDScript/无头运行时 │   双线程适配与 4MB 分包引擎  │   Electron / Tauri 本地外壳   │
└──────────────────────┴──────────────────────┴──────────────────────────────┴───────────────────────────────┘
```

---

## 🌟 核心工程特性 (Key Features)

### 1. 👥 82 位专家角色矩阵与 12 阶段生命周期流转
基于工业化分工，研发任务不依赖单一大模型漫无目的地瞎猜，而是由 `StudioEngine` 严格按冲刺周期派发：
- **阶段 1-2（立项与拆解）**：`project_lead` 确立研发基线，`agile_scrum_master` 拆解 12 个生命周期任务泳道；
- **阶段 3（共识研讨会）**：`lead_game_designer`、`lead_architect`、`combat_balancer`、`qa_director` 开展多轮红蓝交叉质询，形成 `Consensus_Record.json`；
- **阶段 4-6（策划定案与代码装配）**：生成 8 章节标准 GDD，架构师确立 Actor-Trait 组件化架构，主程通过 `VerbAssembler` 装配 60fps 确定性状态机；
- **阶段 7-9（代码审查与视听总线）**：`code_critic` 执行 AST 静态审计，美术总监挂载 Shader/PBR，音效师通过纯 Python 算法合成无依赖的 WebAudio 动态音效；
- **阶段 10-12（自动化验收与多端打包）**：`qa_director` 组织无头试玩测试，G0~G7 门禁逐级裁决，输出各端分发包。

### 2. 🧩 35 个 Ford-T 工业机制零件库 (Ford-T Parts)
系统内置 35 项开箱即用的预制游戏机制零件，杜绝硬编码与重复造轮子：
- **核心控制**：`game_clock` (确定性时钟)、`input_buffer` (6 帧缓冲)、`hitbox_manager` (碰撞判定箱)；
- **策略与数值**：`card_deck` (洗发牌堆)、`loot_table` (加权掉落)、`synergy_matrix` (羁绊系统)；
- **图形与视效**：`dynamic_light` (2D/3D 光照)、`fog_of_war` (战争迷雾)、`screen_shake` (创伤震屏)；
- **高级系统**：`lockstep_sync` (锁步网络同步)、`save_serializer` (安全存档)、`level_editor` (UGC 编辑器)。

### 3. 🛠️ 12 项自研核心落地技能库 (Skills)
在 `skills/` 目录下真实沉淀了 12 套独立工业规范与可执行技能模块：
`game-analytics-loop` (埋点分析) · `game-audio-engine` (音频合成) · `game-behavior-tree` (行为树) · `game-debug-visualization` (调试视效) · `game-dsl-engine` (领域DSL) · `game-genre-parts` (机制组装) · `game-narrative-pedagogy` (叙事教学) · `game-narrative-triggers` (剧情触发) · `game-networking` (网络对战) · `game-save-system` (安全存读档) · `game-science-principles` (游科十原则) · `game-ugc-toolchain` (UGC工具链)。

### 4. 📱 跨端统一宿主抽象矩阵 (HostContract Matrix)
由 [`core/host_contract.py`](file:///d:/jianjian12138/game/core/host_contract.py) 统一抽象四类宿主交互标准（`report_frame`、`mark_state`、`reflect_input`、`parse_evidence`）：
| 目标平台 | 适配器 (Adapter) | 成熟度 | 核心技术支持 |
| :--- | :--- | :---: | :--- |
| **Web (Canvas/WebGL)** | `BrowserRuntimeAdapter` | **M2 已验证** | 60fps 渲染、零GC批处理、Edge 真实像素防伪试玩取证 |
| **Godot 4.x PC** | `GodotRuntimeAdapter` | **M2 已验证** | GDScript 逻辑生成、无头进程运行测试、全功能 3D/2D 渲染 |
| **微信小游戏 (WeChat)** | `MiniProgramRuntimeAdapter` | **M1 壳就绪** | 双线程隔离适配、4MB 首包分包机制、广告与虚拟支付契约 |
| **桌面 PC Shell** | `DesktopShellAdapter` | **M1 壳就绪** | Electron / Tauri 本地跨端桌面工程封装与分发打包 |
| **移动端 (Android/iOS)** | `AndroidRuntime` / `ios_packaging` | **M0 骨架就绪** | Gradle/Capacitor 导出打包封装，诚实标明缺口与 macOS CI 规范 |

---

## 🚀 快速上手 (Quick Start)

### 1. 环境准备
平台基于 Python 3.10+ 标准库构建，核心链路零重型第三方依赖：
```bash
# 克隆仓库
git clone https://github.com/jianjian12138/game.git
cd game

# 安装测试与扩展依赖（可选）
pip install -r requirements.txt
```

### 2. 核心 CLI 命令一览

```bash
# 1. 启动全生命周期游戏研发流水线（创建游戏）
python game_agent.py create "赛博地牢" --genre "Roguelike"

# 2. 查看 82 位专家角色卡与 114 项技能字典
python game_agent.py agent-cards
python game_agent.py skills

# 3. 查看并装配 35 项 Ford-T 机制零件
python game_agent.py list-parts
python game_agent.py assemble "MyGame" --parts card_deck,card_hand,synergy,loot_table,game_clock

# 4. 执行 500 局蒙特卡洛数值平衡对抗模拟
python game_agent.py balance --type card --games 500

# 5. 打包微信小游戏合规工程（带 4MB 分包预检）
python game_agent.py wechat-pack --template survivor_danmaku --out dist/wechat

# 6. 执行全链路工业标准自动化测试与 G0~G7 门禁裁决
python pipeline/test_all_standards.py

# 7. 启动本地可视化工作室控制台
python server.py --browser --port 8090
```

---

## 🌐 多协议智能体接入 (Interoperability)

平台支持 5 种平行的接入协议，可自由嵌入任何外部 Agent 体系：

### 1. Claude Code / Cursor / Windsurf 接入 (标准 MCP 协议)
- **Claude Code 一键挂载**：
  ```bash
  claude mcp add game-dev-agent python ./game_mcp_server.py
  ```
- **Cursor / Windsurf (`mcp.json`) 配置**：
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

### 2. OpenAI Function Calling 接入
导出符合 OpenAI 标准的工具描述 JSON 数组：
```bash
python game_mcp_server.py --export-tools > game_tools.json
```
直接贴入 `client.chat.completions.create(tools=...)` 即可使用。

### 3. Python SDK 原生导入 (AutoGen / CrewAI / 独立脚本)
```python
from core.ford_t_game_parts_hub import ModularGameAssembler
from pipeline.card_balance_simulator import CardBalanceSimulator

# 在任意 Python 工作流中组装零件与测试平衡
assembler = ModularGameAssembler()
game_code = assembler.assemble_blueprint(parts=["card_deck", "synergy", "game_clock"])
sim_result = CardBalanceSimulator.run_simulation(games=200)
```

### 4. HTTP REST API 接入 (LangChain / 前端 / 跨语言调用)
启动后端服务后，即可通过标准 HTTP 访问：
```bash
python server.py --port 8090
# 常用端点：
# GET  http://localhost:8090/api/stats
# GET  http://localhost:8090/api/templates
# POST http://localhost:8090/api/generate
```

---

## 📂 仓库工程结构 (Repository Layout)

项目严格遵循**零冗余、高内聚、无死代码**的工程规范，目录职责划分如下：

```text
game/
├── agents/                     # 👥 智能体花名册与心智驱动
│   ├── base_agent.py           # BaseStudioAgent 抽象基类
│   ├── agent_mind.py           # AgentMind 认知决策与专业思维链推理核
│   └── studio_roster.py        # 82 位专家智能体实例单例池
├── config/                     # ⚙️ 配置模板与规则（含上架元数据模板）
├── core/                       # 🧠 核心架构与引擎工业抽象
│   ├── contracts.py            # 全局数据契约定义 (Intent, Spec, Workflow, Gate)
│   ├── host_contract.py        # 跨端统一宿主契约 (Browser, Godot, WeChat, Native)
│   ├── studio_engine.py        # 12 阶段生命周期流水线总调度器
│   ├── registry.py             # 82 位专家花名册与 114 项技能元数据注册真理源
│   ├── ford_t_game_parts_hub.py# 35 个工业级预制机制零件库
│   ├── gate_engine.py          # G0-G7 门禁裁决器
│   ├── run_service.py          # CLI / HTTP / MCP 统一运行门面
│   ├── dsl_engine/             # 领域特定语言解析器与运行时 (卡牌/技能/谱面)
│   ├── frame_data/             # 60Hz 帧数据、输入缓冲队列、取消链、判定框
│   ├── lighting/               # 2D/3D 光照、迷雾遮罩、视锥、阴影投射
│   ├── narrative/              # 剧情对话分支树、事件状态图、触发区域
│   ├── networking/             # 网络对战 (锁步、状态同步、房间调度、回放)
│   ├── save_system/            # 安全存档、版本迁移、快照对比、云同步
│   └── ugc/                    # UGC 关卡、赛道、谱面编辑器与资源包分发
├── dashboard/                  # 📊 本地可视化研发展台与监控面板前端
├── design/                     # 🎨 策划规范、视觉品牌色彩锁定、GDD 模板
├── docs/                       # 📚 深度架构研报与开源游戏逆向分析报告
├── evidence/                   # 🔍 自动化试玩真实像素防伪证据与审计证据链
├── hooks/                      # 🪝 12 阶段生命周期钩子管理器
├── knowledge/                  # 📖 游戏研发各子系统知识库 (ECS/PCG/数值/音频/Godot)
├── pipeline/                   # 🏭 多端运行时适配器与流水线子系统
│   ├── browser_runtime_adapter.py    # Web Canvas / WebGL 浏览器运行时
│   ├── miniprogram_runtime_adapter.py# 微信小游戏运行时与双线程适配
│   ├── godot_runtime_adapter.py      # Godot PC 运行时与无头仿真
│   ├── desktop_shell_adapter.py      # 桌面 PC Shell (Electron/Tauri) 打包
│   ├── android_runtime_adapter.py    # Android 原生封装适配
│   ├── ios_packaging.py              # iOS 打包规范与 macOS CI 编排
│   ├── gdd_generator.py              # 8 章节策划案生成器
│   ├── verb_assembler.py             # 核心动词与确定性状态机代码装配器
│   └── test_all_standards.py         # 全套研发标准集成自检器
├── skills/                     # 🛠️ 12 个自研核心落地技能模块 (含 SKILL.md)
├── templates/                  # 🎮 开箱即用的参考游戏骨架 (卡牌肉鸽 / 割草弹幕)
├── tests/                      # 🧪 全套单元测试与集成测试集
├── game_agent.py               # 🚀 主命令行总入口 (Master CLI)
├── game_mcp_server.py          # 🔌 标准 MCP 协议服务端入口
├── server.py                   # 🌐 Web 可视化控制台与 REST API 服务端
├── USAGE.md                    # 📘 全生命周期详细使用与交付手册
└── README.md                   # 📄 项目主说明文档
```

---

## 🛡️ 研发铁律与诚实交付准则 (Honesty & Compliance)

1. **绝对真实的运行取证**：
   - 试玩防伪门禁（`playtest`）必须真实启动无头浏览器，采样真实画布像素（非全黑/非空白）并断言用户输入触发哈希变化，严禁使用空转伪造测试通过。
2. **多端成熟度诚实分级**：
   - 只有在本机具备真实运行证据的平台才标记为 `M2 (已验证)`（如 Web 与 Godot 运行时）；缺少外部 SDK、编译链或开发者凭据的端如实返回 `NEEDS_RUNTIME_TOOL` 或 `NEEDS_CREDENTIALS`，绝不跨端借用证据。
3. **零死代码与安全分发**：
   - 代码中严禁硬编码敏感 API Key 与私有凭据；所有运行时产物通过 `.gitignore` 阻断，保证版本库始终处于纯净、轻量的工业级交付状态。

---

## 📄 开源许可证 (License)

本项目基于 [MIT License](./LICENSE) 协议开源。
