# 📖 Game-Agent 使用手册 (USAGE.md)

> **版本**：v2.5.0 | **更新**：2026-09-11 | **Python**：3.9+

---

## 目录

1. [快速上手（3 分钟）](#1-快速上手3-分钟)
2. [环境要求与安装](#2-环境要求与安装)
3. [运行模式](#3-运行模式)
4. [LLM 端点配置](#4-llm-端点配置)
5. [核心 CLI 命令](#5-核心-cli-命令)
6. [多端支持矩阵](#6-多端支持矩阵)
7. [多协议接入](#7-多协议接入)
8. [发布与上架链路](#8-发布与上架链路)
9. [本地 Web 控制台](#9-本地-web-控制台)
10. [诚实边界说明](#10-诚实边界说明)
11. [常见问题排查](#11-常见问题排查)

---

## 1. 快速上手（3 分钟）

```bash
# 1. 克隆项目
git clone https://github.com/jianjian12138/game.git
cd game

# 2. 安装依赖（核心零依赖；可选 LLM 客户端）
pip install -r requirements.txt
# 若要接真实 LLM（可选）：pip install -e ".[llm]"

# 3. 自检（退出码 0 = 本地可开工）
python game_agent.py env-check

# 4. 生成第一个游戏
python game_agent.py create "我的第一个游戏" --genre "2D弹幕射击"
# 产出位置：output/我的第一个游戏/index.html（用浏览器打开即可试玩）

# 5. 全自主研发管线（一句话 → 可上架包）
python game_agent.py autonomous --title "太空突围" --genre "roguelike"
```

---

## 2. 环境要求与安装

### 系统要求

| 项目 | 要求 | 说明 |
|:--|:--|:--|
| Python | 3.9+ | 推荐 3.10+；已在 3.14.7 验证 |
| OS | Windows / macOS / Linux | Windows 已完整验证 |
| 磁盘 | ≥ 500MB | output/ 可再生成，按需清理 |

### 安装步骤

```bash
# 基础安装（零外部依赖运行）
pip install -r requirements.txt

# 可选：接真实 LLM（Gemini / OpenAI / Claude / DeepSeek）
pip install -e ".[llm]"

# 可选：真机试玩（接 Playwright 浏览器自动化）
pip install playwright
# 复用本机已有 Edge/Chrome，无需再下载浏览器

# 可选：AIGC 美术生成（需本机 ComfyUI + SDXL）
# 启动 ComfyUI 后在 .env 配置 COMFYUI_URL=http://127.0.0.1:8188
```

### 配置 `.env`

```bash
cp .env.example .env
# 用文本编辑器打开 .env，至少填入一个 LLM API Key（详见第 4 节）
# 填完后自检：
python game_agent.py env-check
```

---

## 3. 运行模式

平台提供两种显式模式，**默认本地模式**，不配任何外部平台也能开发游戏：

| | `local`（本地开发，默认） | `platform`（平台对接） |
|:--|:--|:--|
| **必需** | LLM 端点池 | 本地全部 + 渠道凭据 + 三类沙箱 + Staging + 遥测 |
| **渠道/沙箱** | 完全不检查、不阻塞 | 缺一组即停并逐项列出补齐方式 |
| **缺浏览器驱动** | 降级为「未验证」，退出码 **5** | 不降级，缺工具即停 |
| **产出** | 可上架包、本地试玩、开发迭代 | 走真实上架与线上运营 |

```bash
# 本地模式（默认）
python game_agent.py autonomous --title "游戏名" --run-mode local

# 平台模式（上架时用）
python game_agent.py autonomous --title "游戏名" --run-mode platform
```

**退出码含义**：`0`=完成 | `5`=包已出但试玩未验证 | `4`=平台外部依赖未齐 | `1`=真失败

---

## 4. LLM 端点配置

### 方式 A：直接写入 `.env`

```bash
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...

# 本地 Ollama（无需 API Key，完全离线）
# OLLAMA_BASE_URL=http://localhost:11434
```

### 方式 B：端点池 JSON（推荐，支持多端点轮询）

```bash
# 导入端点池（JSON 含 Key，绝不提交 git）
python game_agent.py llm-import --file <your_endpoints.json>

# 真实连通性探测（必须真拿到模型回复才算可用）
python game_agent.py llm-status
```

端点文件格式：
```json
[{"id":"gemini-flash","vendor":"gemini","url":"...","api_key":"...","model":"gemini-2.0-flash"}]
```

### 无 LLM 时的行为

未配置 LLM 时，平台自动降级为**本地模板模式**（确定性生成，不调用 API），产出品质较低但不报错。

---

## 5. 核心 CLI 命令

### 5.1 游戏创建与研发

```bash
# 生成指定品类游戏
python game_agent.py create "游戏标题" --genre "2D弹幕射击"
# 支持品类：2D弹幕射击 / roguelike / 卡牌 / 节奏 / 赛车 / 工厂 / 地牢 / 叙事

# 全自主研发管线（一句话 → G0-G6 门禁 → 可上架预览包）
python game_agent.py autonomous --title "太空突围" --genre "roguelike" --run-mode local

# 3D 次时代管线（骨骼动画 + PBR + LOD）
python game_agent.py 3d-pipeline

# 模块化装配（从 Ford-T 零件库组装）
python game_agent.py assemble "MyGame" --parts card_deck,card_hand,synergy,loot_table,game_clock

# 蒙特卡洛平衡仿真（500 局对抗）
python game_agent.py balance --type card --games 500
```

### 5.2 平台能力查询

```bash
python game_agent.py agent-cards        # 82 位专家角色卡
python game_agent.py skills             # 114 项技能目录
python game_agent.py list-parts         # 35 项 Ford-T 零件库
python game_agent.py hooks              # 12 个生命周期 Hooks
python game_agent.py route --detect . --prompt "次时代机甲PBR打击感"  # 引擎指纹嗅探
```

### 5.3 环境与门禁

```bash
python game_agent.py env-check                   # 本地视角（退出码 0 = 可开工）
python game_agent.py env-check --run-mode platform  # 含渠道/沙箱/Staging/遥测
python game_agent.py channel-doctor              # 外部渠道体检（差什么/谁来补/怎么补）
python game_agent.py delivery-audit --path .     # 交付卫生审计（退出码 0 = 可交付）
python game_agent.py delivery-pack --out ./dist_package  # 生成脱敏交付副本
```

### 5.4 发布流水线

```bash
python game_agent.py release-drill               # 故障注入演练（验证每条违规都被拦）
python game_agent.py promote --run-id <id> --channel staging --role qa_manager --actor <人>
python game_agent.py promote --run-id <id> --channel production --role release_manager --actor <人>
python game_agent.py rollback --run-id <id> --reason "线上缺陷" --actor <人>
python game_agent.py live-doctor                 # 线上服务探活
python game_agent.py live-flow                   # 业务链路验证（下单/广告/建房）
```

### 5.5 线上服务参考服务端

```bash
# 起自带参考服务端（可本地/部署为 https）
python -m pipeline.live_service_reference --all \
    --payment-key <自定> --ads-key <自定> --multiplayer-key <自定>
# 起在 8801/8802/8803；照抄输出的 URL 到 .env 即可全链路跑通
```

### 5.6 微信小游戏

```bash
python game_agent.py wechat-pack --template survivor_danmaku --out dist/wechat
python game_agent.py distribute --all            # 四端全渠道分发包
python game_agent.py submit --channel wechat --run-id <id>  # 需真实凭据
```

### 5.7 人工审美复核（生产硬门槛）

```bash
python game_agent.py review-create --run-id <id> --kind art --artifact <路径>
python game_agent.py review-approve --ticket-id <工单> --reviewer <署名> --item "检查项=pass"
python game_agent.py review-status --run-id <id>  # 退出码 0=CLEARED / 1=BLOCKED
```

### 5.8 真实玩家验证

```bash
python game_agent.py player-cohort --cohort-id <标识> --source <来源> --size <人数> --window-days <天>
python game_agent.py player-doctor --events ./events.jsonl
```

---

## 6. 多端支持矩阵

| 端 | 状态 | 前置条件 | 验证方式 |
|:--|:--|:--|:--|
| **Web / H5** | ✅ 已验证（默认主线） | 浏览器 | Edge 真实试玩，像素非零 16723 |
| **Godot PC 运行时** | ✅ 已验证 | Godot 4.7.2 | 无头 120 帧，0 错误 |
| **Godot PC .exe 出包** | ⚠️ 需导出模板 | 下载 export_templates.tpz | `3d-pipeline` |
| **微信小游戏** | 🟡 代码就绪 | miniprogram-ci + AppID | `channel-doctor --channel wechat` |
| **桌面 web-shell** | 🟡 壳可生成 | Node.js + Electron/Tauri | `distribute --channel steam` |
| **Android** | 🟡 骨架就绪 | ANDROID_SDK_ROOT + adb | 装 SDK 后启用 |
| **iOS** | 🔴 本机不可达 | macOS + Xcode | 需 macOS 构建机 |

### Godot 环境配置

```bash
# .env 中配置（或 env-check 自动探测 D:\Godot\）
GODOT_PATH=D:/Godot/Godot_v4.7.2-stable_win64.exe

# 出 .exe 独立包还需导出模板：
# 下载 Godot_v4.7.2-stable_export_templates.tpz
# 解压到 D:\Godot\export_templates\4.7.2.stable\
```

---

## 7. 多协议接入

### CLI（直接使用）

```bash
python game_agent.py create "游戏名" --genre "2D射击"
```

### MCP 协议（Claude Code / Cursor / Windsurf）

```bash
# Claude Code
claude mcp add game-dev-agent python ./game_mcp_server.py

# mcp.json（Cursor/Windsurf）
{
  "mcpServers": {
    "game-dev-agent": { "command": "python", "args": ["./game_mcp_server.py"] }
  }
}
```

### OpenAI Function Calling

```bash
python game_mcp_server.py --export-tools > game_tools.json
# 导出的 JSON 数组直接贴入 client.chat.completions.create(tools=...) 即可
```

### Python SDK 直接导入

```python
from pipeline.commercial_game_factory import CommercialGameFactory
from pipeline.adversarial_red_team import RedTeamInquisitor

game = CommercialGameFactory.build_cyber_survivor()
result = RedTeamInquisitor.indict_file("output/cyber_survivor/index.html")
```

### HTTP REST API

```bash
python server.py --port 8090
# GET  http://localhost:8090/api/stats
# GET  http://localhost:8090/api/templates
# POST http://localhost:8090/api/generate   {"title":"太空突围","genre":"2D射击"}
```

---

## 8. 发布与上架链路

### 四个外部缺口

| 缺口 | 体检命令 | 需要提供 |
|:--|:--|:--|
| ① 外部渠道 | `channel-doctor` | 商店账号、上传密钥、版号/备案、隐私政策 |
| ② 线上服务 | `live-doctor` + `live-flow` | 支付/广告/联机沙箱 URL+KEY |
| ③ 人工复核 | `review-create/approve/status` | 具名审美/合规复核签字（硬门槛） |
| ④ 真实玩家 | `player-cohort` + `player-doctor` | 遥测端点、真实玩家、埋点 `source=real_player` |

### 建议推进顺序

```
1. 先本地跑游戏验收质量（不填任何平台配置）
2. 填缺口②（先参考服务端跑通，再换真服务商）
3. 要上架时填缺口①（账号 + 版号 + 隐私政策）
4. 上生产前缺口③具名复核签字（硬门槛，机器门禁全绿也不放行）
5. 上线后缺口④遥测与真实玩家招募
```

### 交付前必做

```bash
python game_agent.py delivery-audit --path .         # 0=可交付 / 1=有阻断项
python game_agent.py delivery-pack  --out ./dist_package  # 生成脱敏副本再分发
```

> ⚠️ `.gitignore` 只能挡 git，挡不住「把工作区打包 zip 发人」。分发前务必用脱敏副本。

---

## 9. 本地 Web 控制台

```bash
python server.py --browser --port 8090
# 浏览器自动打开 http://localhost:8090
# 功能：可视化仪表盘、项目管理、日志查看
```

---

## 10. 诚实边界说明

| 禁止行为 | 平台如何应对 |
|:--|:--|
| 把「文件存在」说成「已验证」 | 试玩 = 真实像素采样 + 输入响应双道验证 |
| 把「降级运行」说成「完整通过」 | 降级退出码 5（COMPLETED_UNVERIFIED），点名未验证项 |
| 伪造绿勾（缺工具却报 PASS） | 缺工具一律 NEEDS_RUNTIME_TOOL，不放宽 |
| 跨端借证据 | 每端独立采证，HostContract 按端实现 |
| 把 web-shell 说成原生引擎 | 分发清单强制标 `web_in_desktop=true` |
| 一键全自动上架 | 商店账号/版号/具名复核属人工输入，代码不能代劳 |

---

## 11. 常见问题排查

### Q1：`env-check` 报 LLM 不可用

```bash
python game_agent.py llm-status   # 查看端点连通情况
```

### Q2：退出码 5（COMPLETED_UNVERIFIED）

包已产出，试玩降级。安装 Playwright 升级为完整验证：
```bash
pip install playwright
```

### Q3：Godot 报 `NEEDS_RUNTIME_TOOL`

```bash
# .env 中配置路径
GODOT_PATH=D:/Godot/Godot_v4.7.2-stable_win64.exe
```

### Q4：Windows 终端乱码

```bash
chcp 65001
# 或设置 PYTHONUTF8=1
```

### Q5：`live-doctor` 探测失败（配置了代理）

```bash
set no_proxy=127.0.0.1,localhost
```

### Q6：微信小游戏上架流程

```bash
npm install -g miniprogram-ci
# .env：WECHAT_APPID=wx...  WECHAT_CI_KEY_PATH=./config/private.key
python game_agent.py channel-doctor --channel wechat
python game_agent.py wechat-pack --template survivor_danmaku --out dist/wechat
```

---

## 附录：目录结构速览

```
game/
├── game_agent.py              # 主 CLI（所有命令入口）
├── game_mcp_server.py         # MCP 协议服务
├── server.py                  # 本地 HTTP 服务
├── .env.example               # 环境配置模板
├── requirements.txt           # 依赖清单
├── core/                      # 引擎底层
│   ├── llm_gateway.py         # 多 LLM 提供商统一网关
│   ├── host_contract.py       # 跨平台宿主契约
│   ├── registry.py            # 82 专家 + 114 技能 + 12 Hooks
│   └── ford_t_game_parts_hub.py  # 35 项 Ford-T 零件库
├── pipeline/                  # 自动化流水线（100+ 模块）
│   ├── autonomous_pipeline.py # W10 全自主研发管线
│   ├── commercial_game_factory.py # 旗舰游戏生成工厂
│   ├── playtest_engine.py     # 真机试玩防伪门禁
│   ├── run_mode.py            # 运行模式分离
│   └── adversarial_red_team.py  # 红队一票否决
├── agents/                    # 专家智能体
├── tests/                     # 单元测试（337 passed，0 failed）
├── evidence/                  # 验收证据（真实采样数据）
├── templates/                 # 原型模版
└── dashboard/                 # 本地可视化控制台
```

---

*本手册随代码库同步维护。运行 `python game_agent.py --help` 可查看所有命令。*
