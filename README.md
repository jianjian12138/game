# 🎮 Universal Game Dev Agent Platform — 通用型全品类游戏智能研发平台
# (Universal Full-Genre AI-Native Game Development Platform)

> 🚀 **通用型全品类游戏智能研发中枢**：
> 本系统为**开放通用型 AI 智能体架构**，不绑定任何特定客户端。**既可完全独立作为命令行工具或 Web 工作室运行，也可被 Claude Code (cc)、OpenAI Codex、Hermes-Agent、Cursor/Windsurf 等各类通用 Agent 通过标准协议 (MCP / Function Calling / REST / Python SDK) 无缝调用**。
>
> 深度融合 **Ford-T 零件流水线装配架构**（35 项预制工业级零件覆盖 9 大主流品类）、**双向 DSL 游戏逻辑热更运行时**、**行为树 AI 决策中枢**、**高精度帧同步/状态同步网络引擎**、**Combat Juice 战斗打击感打击停顿/震屏总线**、**卡牌与肉鸽蒙特卡洛平衡模拟器**、**GDC 赛斯·哈德森叙事教育学与 SLO 闭环审计引擎**，并支持 **一键微信小游戏 4MB 门禁打包与分包审计**。

[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Universal Agent](https://img.shields.io/badge/Agent-Claude_Code_|_Codex_|_Hermes_|_MCP_|_REST-blueviolet.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Standalone_CLI_|_Web_Canvas_|_WeChat_Minigame-blue.svg)]()
[![Ford-T Parts](https://img.shields.io/badge/Ford--T_Parts-35_Industrial_Parts-purple.svg)](./core/ford_t_game_parts_hub.py)
[![Release Gate](https://img.shields.io/badge/Release_Gate-APPROVED-brightgreen.svg)](./pipeline/release_gate.py)
[![Zero-Deps](https://img.shields.io/badge/Zero--Deps-Python_Standard_Library-orange.svg)]()

---

## 🌐 通用 Agent 跨平台调用与多协议支持 (Multi-Agent Interoperability)

本平台设计原则为 **“协议解耦、无宿主锁死”**，提供 5 种平行的调用方式：

### 1. 独立单独使用 (Standalone CLI & Web Studio)
无需任何 AI Agent 客户端，开发者或 CI/CD 流程可直接调用：
```bash
# 全局命令行快速执行
python game_cli.py list-parts
python game_agent.py create "赛博幸存者" --genre "2D弹幕射击"

# 启动本地可视化工作室控制台
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
Claude Code 或 Cursor 可自动发现并调用包括装配、平衡模拟、红军对抗、微信打包等 **30 个原子研发工具**。

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

# 在 Hermes-Agent 工具函数内执行
game = CommercialGameFactory.build_cyber_survivor()
veto_result = RedTeamInquisitor.indict_file("output/cyber_survivor/index.html")
```

### 5. 通用 HTTP REST API 接入 (LangChain, Flowise, 跨语言服务)
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

平台提供全局通用命令行入口 [`game_cli.py`](./game_cli.py)（或 [`game_agent.py`](./game_agent.py)）：

### 1. 查询 35 项预制零件库
```bash
python game_cli.py list-parts
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
   - 核心引擎: [`templates/survivor_danmaku/danmaku_engine.py`](./templates/survivor_danmaku/danmaku_engine.py)
   - 试玩页面: [`templates/survivor_danmaku/index.html`](./templates/survivor_danmaku/index.html)
   - 特色: 500+ 发弹幕空间网格碰撞优化、经验磁力吸附、怪物狂潮、极简触摸/虚拟摇杆控制。
2. **爬塔卡牌肉鸽 (Card Roguelike)**:
   - 核心引擎: [`templates/card_roguelike/card_game_engine.py`](./templates/card_roguelike/card_game_engine.py)
   - 试玩页面: [`templates/card_roguelike/index.html`](./templates/card_roguelike/index.html)
   - 特色: 动态手牌悬浮透视、法力水晶、意图预警系统、火系标签伤害叠层羁绊、浮字跳字打击感。
3. **战斗打击感工业沙盒 (Industrial Combat Showcase)**:
   - 试玩页面: [`output/industrial_engine_showcase/index.html`](./output/industrial_engine_showcase/index.html)
   - 特色: Hit-Stop 顿帧演示、非线性创伤震屏、体积守恒挤压拉伸、多段连击取消。

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
- 📜 [`RELEASE_AUDIT_REPORT.md`](./RELEASE_AUDIT_REPORT.md)：7 大子系统自包含质量门禁报告
- 🏆 [`FINAL_ACCEPTANCE_REPORT.md`](./FINAL_ACCEPTANCE_REPORT.md)：6 大核心部门专家联合签署终审合格证书

