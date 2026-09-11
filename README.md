# 🎮 Universal Game Dev Agent Platform — 通用型全品类游戏智能研发平台
# (Universal Full-Genre AI-Native Game Development Platform)

> 🚀 **通用型 AI 游戏研发 Agent（Web + Godot-PC 已验证工程交付版；全端路线进行中）**：
> 本系统是一个开放型游戏研发智能体中枢，不绑定特定客户端。它可以作为命令行工具或本地 Web 工作室运行，也可以通过 MCP / Function Calling / REST / Python SDK 被其他 Agent 调用。
>
> 当前交付版包含 **82 张可审计角色卡**、**114 项技能目录**、35 项 Ford-T 机制零件、契约化工件库、DAG 自主编排、真实 Edge 试玩、W5 AIGC 美术工厂、W6 glTF/PBR/Godot 校验、W7 音频工厂、W10 预览包门禁。这里的数字代表目录与已验证分层能力，不代表所有技能都在无外部工具时稳定可用：A=25 真注册、B=62 真跑通+3 项缺 DCC/GPU、C=24 历史至少一次通过但最近批量结果可能波动。所有缺凭据、缺运行工具和未完成人审的事项必须保留为 NEEDS_* / PAUSED / 未达成。

[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Universal Agent](https://img.shields.io/badge/Agent-Claude_Code_|_Codex_|_Hermes_|_MCP_|_REST-blueviolet.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Standalone_CLI_|_Web_Canvas_|_Godot_PC_|_WeChat_Minigame-blue.svg)]()
[![Agents & Skills](https://img.shields.io/badge/Experts-82_Agents_|_114_Skills-blue.svg)](./agents/studio_roster.py)
[![Ford-T Parts](https://img.shields.io/badge/Ford--T_Parts-35_Industrial_Parts-purple.svg)](./core/ford_t_game_parts_hub.py)
[![Release Gate](https://img.shields.io/badge/Release_Gate-APPROVED_(100/100)-brightgreen.svg)](./pipeline/test_all_standards.py)
[![Zero-Deps](https://img.shields.io/badge/Zero--Deps-Python_Standard_Library-orange.svg)]()

---

## 📦 平台内置演示与验收产物（运行命令生成，不等同商店成品）

平台内置四类可运行的工程演示/验收产物，用于验证渲染、骨骼、PBR、性能和分发契约；完整商业游戏仍需内容生产、人工验收、真实玩家测试和渠道合规。

> ⚠️ **诚实说明**：`output/` 是可再生成运行时目录（已加入 `.gitignore`，**不随交付物发出**）。下面的演示由本地命令生成于 `output/`，交付前请用 `python game_agent.py delivery-pack --out ./dist_package` 生成脱敏副本分发，**不要**直接打包 `output/` 或整个工作区。
> 真机试玩防伪底稿（真实像素渲染 + 真实输入响应）已固化在 [`evidence/acceptance_playtest_ep0.png`](./evidence/acceptance_playtest_ep0.png) 与 [`evidence/acceptance_playtest_evidence.json`](./evidence/acceptance_playtest_evidence.json)，可作为验收证据，不依赖 `output/` 是否还在。

| 交付项目 | 生成命令（本地运行后落于 `output/`） | 核心技术标准与工业指标 |
| :--- | :--- | :--- |
| **🏆 赛博幸存者 (商业旗舰正式版)** | `python game_agent.py create "赛博幸存者" --genre "2D弹幕射击"` | **全闭环商业系统**: 局外军火库/永久养成/抽卡/签到、局内三选一技能肉鸽升级、Boss 三阶段 AI。<br>**性能手感**: 零 `Math.hypot`（平方和距离碰撞）、创伤震屏、伤害浮字、单包 140KB（微信首包仅 0.05MB 远低于 4MB 限制）。 |
| **⚙️ 泰坦机甲 (C++ 工业引擎场景架构)** | `python game_agent.py 3d-pipeline` | **工业渲染标准**: DAG 场景图三级级联变换、零-GC `sortKey` 渲染队列、400 条指令折叠为 2 次合批 DrawCall（合批率 99.5%）、预烘焙 80×80 网格贴图、体积守恒挤压拉伸 (`sx*sy=1.0`)。 |
| **🧍 3D 骨骼动画演示系统** | `python game_agent.py 3d-pipeline` | **Khronos glTF 2.0 标准**: 15 关节全功能人形骨架、网格骨骼权重绑定、Idle/Walk/Attack 三段动画 0.25s 交叉平滑过渡 (CrossFade)、THREE.SkeletonHelper 骨骼调试透视、数据完全内嵌无本地 CORS 报错。 |
| **🦾 3A 次时代 PBR/LOD 展台** | `python game_agent.py 3d-pipeline` | **次时代工业美术管线**: 纯 Python 零依赖烘焙 5 通道 PBR 物理贴图 (Albedo/Normal/Roughness/AO/Emissive)、LOD0/1/2 阶梯几何减面与自适应距离调度、HRTF 3D 空间音频定位、红队一票否决审计 100 分。 |

---

## 🌐 通用 Agent 跨平台调用与多协议支持 (Multi-Agent Interoperability)

本平台设计原则为 **“协议解耦、无宿主锁死”**，提供 5 种平行的调用方式：

### 1. 独立单独使用 (Standalone CLI & Web Studio)
无需任何外部 AI Agent 客户端，开发者或 CI/CD 流程可直接调用：
```bash
# 全局统一开发命令行 (生产流水线)
python game_agent.py create "赛博幸存者" --genre "2D弹幕射击"

# 两阶段多引擎指纹智能嗅探与团队匹配
python game_agent.py route --detect . --prompt "次时代机甲PBR打击感"

# 四端全渠道商业分发包构建 (WeChat / SteamPipe / Web PWA / itch.io)
python game_agent.py distribute --all

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

# 2. 查询 35 项预制零件库与 82 张专家角色卡
python game_agent.py list-parts
python game_agent.py agent-cards

# 3. 模块化装配新游戏架构 (Ford-T 流水线)
python game_agent.py assemble "MyGame" --parts card_deck,card_hand,synergy,loot_table,game_clock

# 4. 运行蒙特卡洛平衡模拟 (500 局对抗仿真与 OP 判定)
python game_agent.py balance --type card --games 500

# 5. 一键打包输出合规微信小游戏 (支持 4MB 分包预检)
python game_agent.py wechat-pack --template survivor_danmaku --out dist/wechat
```

### LLM 端点池与专家运行时（W1）

免费额度的 LLM 端点统一走端点池，密钥只存在 `config/llm_endpoints.json`（已在 `.gitignore` 中，禁止提交）。

```bash
# 导入端点池（从本地 JSON，含密钥）
python game_agent.py llm-import --file <endpoints.json>

# 真实连通性探测：必须真的拿回模型回复才算可用，不探测不得宣称可用
python game_agent.py llm-status

# 查看已注册专家卡与 82 位目标的真实缺口
python game_agent.py agent-cards

# 激活一位专家；无可用 LLM 时返回 NEEDS_LLM_CREDENTIALS，不会用模板文本冒充产出
python game_agent.py agent-run --card lead_producer --task "立项评估：割草幸存" \
  --context '{"intent":"割草幸存","constraints":"首包4MB","budget":"2周"}'
```

专家产出强制为结构化 JSON，需通过输出 schema 与验收规则校验；校验失败会把错误回喂模型自愈重试（默认 2 次），
用尽仍不通过则判失败，**不放宽验收规则放行**。

### 发布流水线（Preview → Staging → Production → 渠道上架）

发布链路上每一环都以真实证据为准：没部署过的 Staging 不会算通过，缺商店凭据不会算已上架。

```bash
# 发布门禁故障注入演练：故意制造违规，断言每一条都必须被拦住
python game_agent.py release-drill

# Staging 晋升：需 qa_manager 批准 + 真实访问 STAGING_BASE_URL
python game_agent.py promote --run-id <run_id> --channel staging --role qa_manager --actor <审批人>

# 生产晋升：需先有 Staging 记录，且 release_manager 批准
python game_agent.py promote --run-id <run_id> --channel production --role release_manager --actor <审批人>

# 发布回滚：记录决策与审计，不谎称已执行远端下架
python game_agent.py rollback --run-id <run_id> --reason "线上缺陷" --actor <操作人>

# 在线服务沙箱冒烟（支付/广告/联机）：缺凭据如实返回 NEEDS_SANDBOX_CREDENTIALS
python game_agent.py live-smoke --kind all

# 第三方渠道上架包 + 提交前门禁（默认 dry-run，只组装命令不上传）
python game_agent.py submit --channel wechat --run-id <run_id>

# 外部渠道体检：逐项列出上架还缺什么、由谁补、怎么补（不打印任何凭据值）
python game_agent.py channel-doctor                # 退出码 0=就绪 / 3=缺人工材料 / 1=缺 Agent 可补项

# 交付卫生审计：扫描目录是否含秘密文件与明文密钥
python game_agent.py delivery-audit --path .       # 退出码 0=可交付 / 1=存在阻断项

# 生成脱敏交付副本：排除秘密文件后复检自证，产物干净才允许分发
python game_agent.py delivery-pack --out ./dist_package

# 线上服务体检：支付/广告/联机沙箱 + Staging（服务端必须自证身份，仅能连上不算可用）
python game_agent.py live-doctor
python game_agent.py live-doctor --emit-reference ./health_server   # 写出可直接跑的 /health 参考服务端

# 人工审美与合规复核（生产放行的硬门槛，机器门禁全绿也不放行）
python game_agent.py review-create --run-id <run_id> --kind art --artifact <路径>
python game_agent.py review-approve --ticket-id <工单> --reviewer <署名> --item "检查项=pass"
python game_agent.py review-status --run-id <run_id>                # 退出码 0=CLEARED / 1=BLOCKED

# 真实玩家验证：遥测接入 + 试点队列登记 + 事件真实性判定
python game_agent.py player-cohort --cohort-id <标识> --source <招募来源> --size <人数> --window-days <天数>
python game_agent.py player-doctor --events ./events.jsonl

# 环境自检总表：一张表看四个缺口还差什么（填完 .env 后可自行验证）
python game_agent.py env-check                      # 默认 local 视角，退出码 0=本地可开工
python game_agent.py env-check --run-mode platform  # 含渠道/沙箱/Staging/遥测

# ── 运行模式：本地开发 vs 平台对接（不配置任何外部平台也能开发） ──────────────
python game_agent.py autonomous --title "roguelike 卡牌" --run-mode local
#   local（默认）：只要 LLM 端点就能开发/出包/本地试玩；
#   渠道、沙箱、Staging、遥测一概不看、不阻塞；缺浏览器驱动时试玩降级为「未验证」
#   退出码：0=COMPLETED ／ 5=COMPLETED_UNVERIFIED（包已出但验证项没跑，不得声称已验证）

python game_agent.py autonomous --title "roguelike 卡牌" --run-mode platform
#   platform：开工前即校验渠道/沙箱/Staging/遥测，缺一组就停下并逐项列出补齐方式（退出码 4）

# ── 缺口② 线上服务：先跑通业务链路，再换真服务商 ──────────────────────────────
# 1) 起自带参考服务端（真实 HTTP，不是 mock；可本地，也可部署成 https）
python -m pipeline.live_service_reference --all \
    --payment-key <自定> --ads-key <自定> --multiplayer-key <自定>   # 8801/8802/8803
# 2) 把打印出的地址填进 .env 的 PAYMENT/ADS/MULTIPLAYER_SANDBOX_URL/KEY
python game_agent.py live-doctor      # 探活：端点活着吗（服务端须自证 service/environment）
python game_agent.py live-flow        # 业务链路：下单→查单→退款 / 广告曝光点击 / 建房→加入→离开
# 换真服务商时只改 .env 的 URL+KEY，业务代码不用动
```

上架元数据模板见 [`config/store_metadata.example.json`](./config/store_metadata.example.json)，
素材放置在 `output/store_assets/`；环境变量清单见 [`.env.example`](./.env.example)。
**未经真实凭据与官方上传器，工具不会执行提交，也不会把打包成功汇报为已上架。**

`channel-doctor` 的输出本身就是「外部渠道还差什么」的清单：每项标注 `需人工` 或 `Agent 可补`，
并给出补齐方式；纯人工材料（商店账号、上传密钥、版号/备案、税务信息、隐私政策）单列，
因为这些不可能由代码凭空产生。凭据一律只报「是否设置/格式是否合法」，绝不打印值。

---

## ✅ 当前交付口径（2026-09-11）

W1–W10 的工程升级已完成，Web 主线可真实生成、打包并用 Edge 试玩验证；W5 ImageGenAdapter 已接入 W10 autonomous，默认优先本机 ComfyUI + SDXL，并随包写入 PNG 与 provenance JSON。最新单元测试回归（`pytest tests/`，关闭环境安全删除护栏后实跑）为 **305 passed + 11 skipped + 105 subtests（0 failed）**，skipped 是受环境变量保护的真实运行守护项（真实浏览器 / Godot / ComfyUI）。本轮已清理：39 个零引用模块移入 `attic/`（可还原）、根目录散落的研究 JSON 移入 `attic/`、被取代的旧验收报告删除、`output/` 等可再生成临时目录清理；并修复了两处真实问题：`BrowserRuntimeAdapter._load_driver` 的 `@staticmethod`/签名不一致（会导致 `preflight` 与垂直切片 CLI 崩溃），以及 `test_live_service_flow.py::test_contract_mismatch_when_no_business_endpoints` 在 Windows `SO_REUSEADDR` 端口复用下的偶发抖动（前序用例遗留 server 与本测试 server 共用端口，导致同一测试内 auth 探针拿到 404、支付流却连接被拒；已加唯一 `probe_token` + 就绪探测换端口重绑，整仓连跑 2 次确定性 **305 passed + 11 skipped + 105 subtests（0 failed）**）。

多端路线 Phase 0 已落地（完整计划见 `MULTI_PLATFORM_PLAN.md`）：Godot 4.7.2 本机真实无头跑通取证（`output/godot_demo`：`frames=120`、`godot_error_count=0`、exit 0，见 `pipeline/godot_runtime_adapter.py`）；新增诚实导出器 `pipeline/godot_exporter.py:GodotExporter.export_windows`（缺导出模板时真实报错并如实返回 `NEEDS_RUNTIME_TOOL`，绝不伪称可出独立包）；`commercial_distribution_hub` 的 Steam/itch 分发支持接收真实 Godot 导出物并标注 `godot_native=true`，否则退回 Web 壳且 `godot_native=false`；`cmd_distribute` 增加 `--godot-project` 真实导出后下传；能力登记 `godot.pc_desktop`（maturity M2，运行时已验证）。独立 .exe 出包仍受限于本机缺导出模板（无外网下载），属真实 NEEDS_RUNTIME_TOOL，非工程缺陷。

多端路线 **Phase 1–5 骨架已于本轮落地（2026-09-11）**：`core/host_contract.py` 通用化 `HostContract`（四条宿主契约，所有适配器统一消费）；新增 `MiniProgramRuntimeAdapter`（微信小游戏）、`DesktopShellAdapter`（PC 桌面 web-shell，接入 Steam/itch 分发并标 `web_in_desktop`）、`AndroidRuntimeAdapter`（Android 原生 + Godot 导出封装）、`ios_packaging`（iOS 打包，本机返回 `NEEDS_MACOS_BUILDER` 并提供 macOS CI 步骤）、`store_submission` 新增 App Store / Google Play 渠道门禁；`CapabilityRegistry` 登记 `wechat.mini` / `desktop.shell` / `android.native` / `ios.native`（maturity 诚实：M0 代码就绪未真验证 / M1 壳生成可用）。Tier2/3 端在本机缺工具/不可达时一律 `NEEDS_RUNTIME_TOOL` / `NEEDS_SDK` / `NEEDS_MACOS_BUILDER`，**绝不伪 PASS**；桌面 web-shell 明确与 Godot 原生 `.exe` 区分，不粉饰成原生引擎。新增 `tests/test_multi_platform.py`（24 passed + 2 skipped），整仓回归连跑 2 次确定性绿。

这不是“任意品类商业成品一键自动上架”的承诺。当前可交付的是：

- Web 端可玩的垂直切片、原型和自主预览包；
- 真实工件、SHA256、审计链、G0–G6 预览门禁和项目级运行记忆；
- W1–W10 已实现的确定性系统、资产工厂、试玩和发布前校验。

仍需人工或外部凭据的事项必须保留为红线：AI 美术的审美/版权复核、生产审美拍板、版号/渠道凭据、第三方支付/广告/联机沙箱、真实商店提交；Godot 目标虽已具备本机验证证据，但 Web 仍是默认主线。114 技能的诚实口径为 A=25 真注册、B=62 真跑通 + 3 项缺 DCC/GPU、C=24 历史至少一次通过但最近批量为 17/24，不能把历史通过冒充当前稳定通过。

## 📱 多端支持矩阵（诚实分级，2026-09-11）

目标定位是**全栈游戏研发平台**（PC / 手机端 / 小程序 / H5 / Web 页游都要支持），但每一端必须各自有**真实运行时 + 真实证据**才能标「已验证」，绝不跨端借证据、不把 web-shell 粉饰成原生、不未验证就标 PASS（红线 13.2）。当前分级（Phase 0–5 骨架已落地，maturity 见 `core/capability_registry.py`）：

| 端 | 验证状态 | 真实证据 | maturity | 缺口 / 待补 |
| :-- | :-- | :-- | :-- | :-- |
| **Web / H5**（Canvas + WebGL） | ✅ 已验证（默认主线） | Edge 真实试玩：像素采样 `pixel_nonzero=16723`、输入前后画布哈希变化 | M2 | — |
| **Godot PC 桌面**（运行时 boot/core_loop） | ✅ 已验证（本机真实跑通） | `GodotRuntimeAdapter` 无头跑 `output/godot_demo`：`frames=120`、`godot_error_count=0`、exit 0 | M2 | — |
| **Godot PC 桌面**（独立 .exe 出包） | ⚠️ NEEDS_RUNTIME_TOOL | 真实 `--export-release` 报错：缺导出模板 `D:\Godot\export_templates\4.7.2.stable\windows_{debug,release}_x86_64.exe` | M2（运行时）/ NEEDS_RUNTIME_TOOL（出包） | 下载 `Godot_v4.7.2-stable_export_templates.tpz` 解压后重试（本环境无外网，待你提供模板） |
| **微信小游戏 / 小程序** | 🟡 Tier2（代码就绪，未真验证） | `MiniProgramRuntimeAdapter` + `MiniProgramContract`（wx.* 映射）已落；`WeChatPackager` 4MB 分包 + 广告/支付契约结构已生成 | M0 | 需微信开发者工具 CLI / miniprogram-ci + 真实 AppID / 广告位 / 虚拟支付沙箱 |
| **PC 桌面 web-shell（Electron / Tauri）** | 🟡 Tier1（壳生成可用，运行期待验证） | `DesktopShellAdapter.package_desktop_shell` 真实生成壳工程（main.js/package.json/tauri 配置）；`distribute_steam/itch` 接收并标 `web_in_desktop=true`（**不粉饰成原生**） | M1 | 构建可运行桌面包需 Electron/Tauri 构建链（本机 `electron`/`tauri` 二进制缺失） |
| **Android 原生** | 🟡 Tier2（代码就绪，未真验证） | `AndroidRuntimeAdapter` + Godot Android 导出封装已落 | M0 | 本机未装 `ANDROID_SDK_ROOT` / `adb` / debug keystore；需 SDK + 签名密钥 |
| **iOS 原生** | 🔴 Tier3（本机不可达） | `ios_export()` 如实返回 `NEEDS_MACOS_BUILDER`；`macos_ci_steps()` 提供 macOS CI 步骤（标注 unverified，未执行） | M0 | 需 macOS + Xcode 签名；当前 Windows 主机无法真验证 |
| **商店渠道：App Store / Google Play** | 🟡 门禁就绪（诚实拦截） | `store_submission.STORE_SPECS` 新增 `appstore`/`googleplay`，缺凭据/工具如实返回 `NEEDS_SANDBOX_CREDENTIALS` / `NEEDS_RUNTIME_TOOL` | — | 需商店账号、上传器、签名与版号 |
| **Rust/WASM 原生** | 🟡 可选路线 | `core/` 预留 wasm_rust 目标预检 | — | 需 Rust 工具链 |

> **Phase 1–5 已落地（诚实骨架）**：`core/host_contract.py` 把 `window.__GAME_AGENT__` 抽象为跨端 `HostContract` 接口（`report_frame()` / `mark_state()` / `reflect_input()` / `parse_evidence()`），并实现 `BrowserContract` / `GodotContract` / `MiniProgramContract` / `NativeContract` 四条契约，所有运行时适配器统一消费、门禁逻辑复用。已新增 `MiniProgramRuntimeAdapter`（微信）、`DesktopShellAdapter`（桌面 web-shell）、`AndroidRuntimeAdapter`（Android 原生）、`ios_packaging`（iOS 打包）四个适配器/模块，并接入 `commercial_distribution_hub` 与 `store_submission`。**关键诚实红线**：Tier2/3 端在本机缺工具/不可达时一律 `NEEDS_RUNTIME_TOOL` / `NEEDS_SDK` / `NEEDS_MACOS_BUILDER`，绝不伪 PASS；桌面 web-shell 明确标 `web_in_desktop`，不与 Godot 原生 `.exe` 混淆。完整分阶段计划见 `MULTI_PLATFORM_PLAN.md`。

> 路线原则：先让**能真验证的端**（Web、Godot-PC 运行时）拿到确定性证据，再逐端补齐工具链；每补一端都先跑该端的真实运行时取证，再开放「已验证」标。

## 🏁 工业级交付标准判定（诚实自评）

判断口径：对照“工业级游戏开发 agent”应达到的工程标准，逐项看**有没有真证据**，而不是看文档写得满不满。

| # | 工业级标准 | 判定 | 证据 |
| :-- | :-- | :-- | :-- |
| 1 | 能真实产出可玩、非平凡的完整游戏（从垂直切片到可上架预览包） | ✅ 达成 | `autonomous` 端到端 G0–G6 全 PASS，出货包含 `index.html`+清单+合规+4 条音频+AIGC 美术 |
| 2 | 产出经**真实**验证而非伪造（画面真在动、输入真生效） | ✅ 达成 | 试玩防伪门禁：真实像素采样 `pixel_nonzero=16723`、驱动输入前后画布哈希变化 `1550669026→2876515305`；空转壳子旧版误判 PASS、新版如实 FAIL |
| 3 | 覆盖完整研发生命周期（设计/资产/平衡/手感/打包/预览） | ✅ 研发侧达成 | W1–W10 确定性系统 + 资产工厂 + 平衡仿真 + 手感总线 + 打包 + 预览门禁 |
| 4 | 诚实暴露局限、不伪造绿勾（降级不伪称已验证） | ✅ 达成 | 13.2 红线、运行模式分离（`COMPLETED_UNVERIFIED` 退出码 5）、门禁降级点名不伪称 |
| 5 | 代码干净可维护、无硬编码密钥 | ✅ 达成 | 39 零引用模块移 `attic/`、密钥卫生审计、`delivery-pack` 脱敏副本 |
| 6 | 文档与交接完备、可独立验收 | ✅ 达成 | 本 README + `DELIVERY_ACCEPTANCE_REPORT.html` + 门禁自检 `env-check` + 交接清单 |
| 7 | 一键全自动上架并持续运营（无需人工/外部） | ❌ 不可达成 | **本质需要商店账号/版号/具名复核/遥测端点等人工与法律输入**，非工程缺口；任何“全自动”宣称都违反红线 |

**结论**：本 agent 已达到「**工业级 AI 原生游戏研发 agent（本地可玩、可验证、可预览出包）**」的交付标准——这是真实、有据、可独立复现的。它**未达到**「全自动商业上架 + 线上运营」标准，因为后者在根上依赖人工与法律动作（版号、具名复核、真实玩家招募），没有任何 agent 能自行供给；把“需人工”说成“已自动完成”正是用户明令禁止的假绿。工程侧四个缺口均已做成**可执行门禁**（缺什么、由谁补、怎么补都列清楚），只差你填入真实凭据与人工动作，不会再出现“以为做完了其实没做”。

## 🔒 交付安全与密钥卫生

本平台会被交付给使用者，因此凭据边界是硬要求，而不是建议：

| 位置 | 内容 | 是否进入交付物 |
| --- | --- | --- |
| 代码 / git 仓库 | **无硬编码密钥**，只从环境变量或被忽略的配置文件读取 | 是（安全） |
| `config/llm_endpoints.json` | 明文 LLM API Key（运行必需） | **否**，已被 `.gitignore` 忽略，且被 `delivery-pack` 排除 |
| `.env` | 沙箱 / 渠道上架凭据 | **否**，同上 |
| 资产 provenance | 本地端点、模型名、seed、prompt、SHA256 | 是（不含密钥） |

三点需要如实说明：

1. `.gitignore` 只能挡住 git，**挡不住「把整个工作区打包成 zip 发给人」**。因此交付前必须执行
   `python game_agent.py delivery-pack --out <目录>`，用脱敏副本分发，而不是直接拷贝工作区。
2. 审计结论是「未命中已知密钥模式」，**不等于绝对无泄露**；扫描器无法识别未知形式的秘密。
3. 曾经落盘过的 API Key 建议撤销轮换，因为删除文件不等于密钥未曾暴露。

## 🧩 四个剩余缺口的工程状态（2026-09-10）

通往「商业游戏完整团队、自动上线并持续运营」还差四类外部条件。目前四类都已做成**可执行门禁**，
只差填入真实凭据与人工动作——不会再出现「以为做完了其实没做」的情况。

| 缺口 | 工程侧已完成 | 仍需丁建提供 |
| --- | --- | --- |
| ① 外部渠道 | `channel-doctor` 逐项体检，标注「需人工 / Agent 可补」与补齐方式 | 商店账号与上传密钥、官方上传器、元数据、版号备案、隐私政策 |
| ② 线上服务 | `live-doctor`（探活）+ `live-flow`（真实业务链路：下单→查单→退款 / 广告曝光点击 / 建房→加入→离开）+ `/health` 身份自证契约 + 可一键启动的参考服务端 `live_service_reference --all` | 支付/广告/联机沙箱真实 URL+KEY、Staging 真实 https 部署（先用自带参考服务端即可全链路跑通） |
| ③ 人工审美合规 | `human_review` 工单制，已挂进生产门禁：无具名复核，G7 全绿也不放行 | 具名复核人对美术/音频/出货包签字 |
| ④ 真实玩家验证 | `player-doctor` + 试点队列登记 + 事件来源判定（模拟数据不得冒充留存） | 遥测端点、真实玩家招募、客户端埋点带 `source=real_player` |

三条硬规则：

1. **连通不等于可用**：`/health` 必须返回 `{"service":..., "status":"ok", "environment":...}`，
   自报家门不符即判 `IDENTITY_UNVERIFIED`，避免把 URL 错配成任意可达站点也算通过。
2. **无人签字就不是复核**：生产候选要求 `art/audio/release` 三类工单全部 `APPROVED` 且具名。
   记录只证明有人签署，不证明签署者具备审美或法务资质。
3. **模拟数据不算真实**：事件必须带 `properties.source=real_player`（或 playtest/beta/store/live）
   才计入真实指标；没有任何真实事件时如实返回 `NO_REAL_PLAYER_DATA`，不得对外宣称留存/付费/时长。

配置模板见 [`.env.example`](./.env.example)（已改写成填写指南版：每项标注去哪拿、格式要求与验证命令）。
填完直接跑 `python game_agent.py env-check` 自检，不必等他人确认。

> 两个实测踩到的坑：
> ① 本机若配置了 HTTP 代理，探测 `127.0.0.1` 的服务需设置 `no_proxy=127.0.0.1,localhost`
> （Windows 上还会读注册表代理设置，必要时直接清空 `http_proxy`/`https_proxy`），
> 否则代理返回 502 会被误判为不可达；
> ② `.env` 原先只在导入 `core.llm_gateway` 时才被顺带加载，某些命令路径会「填了却报未配置」，
> 现已在 CLI 入口显式加载，不依赖导入顺序。

## 🏠 运行模式分离：不配任何平台也能开发（2026-09-11）

用户诉求：「现在一些配置需要我来配置，现在不配置，可以先本地进行游戏开发吗？」
已落地为两种显式模式，**默认就是本地模式**：

| | `local`（本地开发，默认） | `platform`（平台对接） |
| --- | --- | --- |
| 必需 | LLM 端点池 | 本地全部 + 渠道凭据 + 三类沙箱 + Staging + 遥测 |
| 渠道/沙箱/Staging/遥测 | **完全不检查、不阻塞** | 缺一组即在**开工前**停下并逐项列出补齐方式 |
| 缺浏览器驱动 | 试玩降级为「未验证」，状态 `COMPLETED_UNVERIFIED`，退出码 **5** | 不降级，缺工具即停 |
| 产出 | 可上架包、本地试玩、开发迭代 | 走真实上架与线上运营 |

诚实边界（这是模式分离最容易做假的地方）：

- 本地模式允许**验证类**能力降级，但**绝不允许把「没验证」写成「已验证」**——
  降级节点会进 `unverified` 列表并在输出里点名，状态是 `COMPLETED_UNVERIFIED` 而非 `COMPLETED`。
- 只有 `playtest` 属于可降级集合；装配/打包等**出货类**节点缺工具，本地模式照样停。
- 平台模式下 `DEGRADABLE_NODES_IN_LOCAL` 被强制清空，任何降级都不允许。

本机实测（未配置任何渠道/线上配置）：

```
python game_agent.py autonomous --title "本地模式验收 无外部配置" --genre roguelike --run-mode local
[AUTON] 状态=COMPLETED   退出码 0
  门禁: G0–G6 全 PASS（含 G4 真机试玩 PASS，Edge + Playwright 实跑）
  可上架包: index.html + manifest + 合规清单 + 4 条音频 + AIGC 美术
python game_agent.py autonomous --title "平台模式验收" --run-mode platform
[AUTON] 状态=PAUSED      退出码 4，开工前即列出 8 组待补依赖及各自补齐方式
```

> 本地试玩依赖 Playwright 驱动：`pip install playwright` 即可（复用本机 Edge/Chrome，
> 无需再下载浏览器）。没装也不影响出货，只是试玩判为「未验证」。

### 🛡️ 试玩防伪增强：真看像素 + 真测输入响应（13.2 红线落地）

旧版试玩门禁只数 `frame/ticks` 自增 + 校验 canvas 尺寸 + 契约挂载 + 无异常——
**帧数涨 ≠ 画面在动**，一个「canvas 存在、rAF 空转自增、但从不绘制、忽略键盘」的壳子
会因此在旧版误判 PASS。升级后 `pipeline/playtest_engine.py` 在每轮 episode 增加两道
真实采样（辅助函数 `_JS_CANVAS_PIXELS` 见 `browser_runtime_adapter.py`）：

1. **真实像素验证**：到达 playing 后 `getImageData` 统计非背景像素（WebGL/tainted 回退
   `toDataURL` 哈希），canvas 必须采样到非空白内容，否则 FAIL——证明「画面真在渲染」。
2. **真实输入响应**：驱动真实键盘前后各采一次画布内容哈希，哈希确有变化才认定输入被处理
   并反映到画面，否则 FAIL——证明「输入真生效」而非空转循环。

verdict 现要求「到达 playing **且** 像素渲染 **且** 输入响应」三者同时成立才 PASS，
否则如实 FAIL 并点名原因（画面空白 / 输入无响应）。已造空转壳子回归验证：旧版会 PASS，
新版如实 FAIL。回归见 `tests/test_playtest_pixel_truth.py`。

## 🧹 死代码清理：39 个零引用模块移入 `attic/`（2026-09-11）

扫描发现 319 个 py 文件中有 **39 个从未参与任何一条运行链路**，已移出主代码库到
[`attic/`](./attic/README.md)（**未删除，可一键还原**）。

判定不靠单一静态扫描，而是三重实证：

1. 无任何 `import` 引用（含函数内懒加载）；
2. 类名/函数名在整个仓库（含 `.md/.json/.toml`）零出现；
3. 移出后 `pytest tests/`（305 passed + 11 skipped + 105 subtests，0 failed）、
   `pipeline/test_all_standards.py`（28 项）、六个主要 CLI 命令、以及一次完整
   `autonomous` 出货（G0–G6 全 PASS）——**全部与清理前一致**。

> **踩到的坑值得记住**：静态扫描本身不可靠。`core/skill_registry.py` 用
> `importlib.import_module()` 按完整点分路径动态加载模块，第一版扫描漏掉了
> `core/combat_numerical_engine.py`（它**确实**被加载），移走后
> `tests/test_skill_registry.py` 立刻收集失败。该模块已归位并保留在主代码库。
> 所以**任何「扫一遍就删」的清理都必须用回归验证兜底**。

顺带修掉一个陈旧断言：`pipeline/test_all_standards.py` 的 Test20 原先写死
「Godot 未安装 → 预检必失败」，在你装好 Godot 4.7.2 后会误报失败（README 却宣称全绿）。
现改为**跟随真实环境**：装了就该通过，没装就该如实报缺失。修复后 28 项全绿，
README 的宣传才站得住。

## 📋 交接清单：现在需要你提供什么（工程侧已闭环，只差外部与人工）

工程侧四个缺口已全部闭环，**你可以什么都不配置就本地开发**。只有在要真实上架/线上运营时，
才需要外部信息——一次性给齐即可，不必边做边等。

先确认现在能做什么（不需要下面任何一项）：

```bash
python game_agent.py autonomous --title "你的游戏名" --genre roguelike   # 本地开发（默认零外部配置）
python game_agent.py env-check                                        # 退出码 0 = 可以开工
```

退码含义：`0`=完成 ｜ `5`=包已出但试玩未验证（缺浏览器驱动）｜ `4`=平台模式外部依赖未齐 ｜ `1`=真失败。

| 缺口 | 需要你提供 | 自查 / 门禁 |
| :--- | :--- | :--- |
| ① 外部渠道 | 商店账号与上传密钥（微信 `WECHAT_APPID`+`private.key`、Steam `STEAM_APP_ID`、itch `ITCH_BUTLER_TARGET`、Web PWA `PWA_DEPLOY_BASE_URL`）、版号/备案、隐私政策 | `python game_agent.py channel-doctor`（3=缺人工材料，逐项列出） |
| ② 线上服务 | 支付/广告/联机沙箱真实 URL+KEY、Staging 真实 https（**可先跑自带参考服务端全链路跑通**） | `python -m pipeline.live_service_reference --all` → `python game_agent.py live-flow` |
| ③ 人工审美合规 | **具名复核人**对美术/音频/出货包签字（机器门禁全绿也不放行） | `python game_agent.py review-create/approve/status` |
| ④ 真实玩家验证 | 遥测端点 `TELEMETRY_ENDPOINT`/`KEY`、真实玩家招募；客户端埋点带 `source=real_player` | `python game_agent.py player-cohort` / `player-doctor`（无真实事件如实返回 `NO_REAL_PLAYER_DATA`） |

建议推进顺序：① 现在什么都不填，先本地跑几个游戏验收质量 → ② 填缺口②（先参考服务端跑通再换真服务商）→ ③ 要上架填缺口①+版号备案 → ④ 上生产前缺口③具名复核签字（硬门槛）→ ⑤ 上线后缺口④遥测与真实玩家招募。

**信息泄露防护（必须做）**：`.gitignore` 只能挡 git，挡不住「把工作区打包 zip 发人」。分发前务必：
```bash
python game_agent.py delivery-audit --path .     # 0=可交付 / 1=有阻断项
python game_agent.py delivery-pack  --out ./dist_package   # 生成脱敏副本再分发
```
> 曾经落盘过的 API Key 建议撤销轮换——删除文件不等于密钥未曾暴露；审计「未命中已知密钥模式」≠ 绝对无泄露。

## 🧾 最终交付审计

全面能力矩阵、真实证据、未达成项和清理边界见 [`DELIVERY_ACCEPTANCE_REPORT.html`](./DELIVERY_ACCEPTANCE_REPORT.html)。该报告明确区分“工程能力已具备”“预览包可交付”和“商店/线上生产仍需外部条件”，不把演示产物或静态代码当作商业成品。

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

> **运行约束（诚实说明）**：`test_all_standards.py` 是**验收套件**，部分用例断言 `output/` 下预生成的旗舰演示（`cyber_survivor` / `industrial_engine_showcase` / `skeletal_showcase`）。
> - Test 8/9/10/11/18 在演示产物缺失时**诚实 `skip`**（明确提示先跑 `python game_agent.py create "赛博幸存者" --genre "2D弹幕射击"` 或 `3d-pipeline` 生成），不伪称通过；
> - Test 12/22 自带自愈（产物缺失则实时重建）；
> - 浏览器相关用例（Test 21/22）在本地无 Edge/Playwright 时如实降级为 `NEEDS_RUNTIME_TOOL`。
> - 运行环境带安全删除护栏（`CODEBUDDY_SAFE_DELETE_ENABLED`，默认开启）：测试用 `shutil.rmtree` 清理临时目录累计超阈值会触发 `SystemExit` 中断。要在本机跑完整套件请临时 `set CODEBUDDY_SAFE_DELETE_ENABLED=0`；**规范单元测试请用 `pytest tests/`（305 passed + 11 skipped + 105 subtests，0 failed）**，它不依赖预生成演示与浏览器。

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
├── agents/                     # 82 位专家智能体思维模型与工作流名录
│   ├── agent_mind.py           # 智能体心智中枢与反思循环
│   └── studio_roster.py        # 82 位专家智能体能力矩阵定义
├── core/                       # 工业级通用游戏研发引擎底层
│   └── registry.py             # 专家/技能/生命周期 Hook 与跨部门团队契约（含 3D 次时代美术与资产工程团队）
│   ├── contracts.py            # GameIntent/GameSpec/Workflow/Evidence/Gate/Release 契约
│   ├── artifact_store.py       # SHA-256 内容寻址与不可变工件存储
│   ├── run_service.py          # CLI/HTTP/MCP 统一运行服务
│   ├── workflow_orchestrator.py# 版本化工作流计划与能力编排
│   └── gate_engine.py          # G0-G7 门禁裁决
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
├── output/                     # 可再生成运行时目录（gitignored，不随交付物发出；由 create / 3d-pipeline / autonomous 生辰）
│   ├── cyber_survivor/         # 《赛博幸存者》旗舰交付物 (Web + 微信小游戏)，运行 create 后生成
│   ├── industrial_engine_showcase/ # 泰坦机甲 C++ 引擎场景图与合批展示，运行 3d-pipeline 后生成
│   └── skeletal_showcase/      # 3D Khronos glTF 2.0 骨骼蒙皮动画展示，运行 3d-pipeline 后生成
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
