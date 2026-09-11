# 多端游戏开发平台 — 完整实施计划

> 目标：把「Web 主线游戏 Agent」扩展为覆盖 **Web / H5 / 小程序（微信小游戏）/ 电脑（PC 桌面）/ 手机端（Android / iOS）** 的全栈游戏开发平台。
> 原则（红线 13.2）：每端必须有**自己的真实运行时 + 自己的真证据**；绝不跨端借证据、绝不把 web-shell 粉饰成原生、绝不未验证就标 PASS。

---

## 0. 现状核验（现场证据，非记忆）

| 项 | 结论 | 证据 |
|---|---|---|
| Godot 4.7.2 | ✅ **已装本机** | `D:\Godot\Godot_v4.7.2-stable_win64.exe` + `*_console.exe`（在 PATH 外，未被适配器发现） |
| Web / H5 | ✅ 已真验证 | Edge/Chromium + WebGL，G0–G7 全 PASS |
| Android SDK / adb | ❌ 未装 | `ANDROID_HOME`/`ANDROID_SDK_ROOT` 空，`adb` 不在 PATH |
| iOS / Xcode | ❌ **本机物理不可达** | Windows 无法运行 macOS+Xcode，iOS 原生构建需换 macOS 构建机 |

- `GodotRuntimeAdapter` 当前报 `NEEDS_RUNTIME_TOOL` 的根因：**`_resolve_executable()` 只读 `EnvironmentInspector` 清单里的 `tools.godot.executable`，而本机 Godot 没登记、也不在 PATH**——是"找不到二进制"，不是"引擎不能跑"。探针逻辑（`--headless` + SceneTree 探针、`MIN_FRAMES=30`）已就绪。
- `CommercialDistributionHub` 的 `distribute_wechat/steam/pwa/itch` 入参是 `src_html`：当前做的是**把同一份 web 构建包进各端壳**，不是各端原生重做。
- `core/runtime_contract.py` 的 `window.__GAME_AGENT__` 契约**绑定浏览器/DOM**，非 web 端需各自宿主契约。

---

## 1. 总体架构（诚实多端骨架）

```
            GameSpec（目标无关游戏规格，已有 GameIntent/GameSpec）
                          │
            ┌─────────────┴───────────────┐
       HostContract（宿主契约接口）      RuntimeAdapter（每端真实验证）
       report_frame / mark_state /        preflight / launch / run_scenarios
       reflect_input（取代 window.__GAME_AGENT__，按端实现）
            │                                 │
   ┌────────┼────────┬────────┬────────┐     ┌────────┼────────┬────────┬────────┐
 Browser  Godot  MiniProgram  Native   CapContract   Web    GodotPC  WeChat   Android/iOS
```

- **一份规格、每端一份契约、每端一份适配器**：游戏逻辑与平台解耦。
- **门禁按端复制**：G0–G7 升级为 `TargetGate`，每端独立裁决；缺真实运行时→`NEEDS_RUNTIME_TOOL`、缺 SDK→`NEEDS_SDK`、缺凭证→`NEEDS_CREDENTIALS`，永不 PASS。
- **能力登记**：`CapabilityRegistry` 为每个端记 `maturity` + `evidence` 链接，未验证端不进"已支持"清单。

---

## 2. 目标端分级（按本机真实可达性）

### Tier 1 — 本机立即可真验证（最高优先）
- **Web / H5**：已验证，维持。
- **PC 桌面 · Godot 原生**：Godot 已装 → headless 真跑 + 导出 Windows 独立包（`.exe`+`.pck`）。**本计划最快产出"新已验证端"**。
- **PC 桌面 · web-shell（Electron/Tauri）**：把现有 web 构建封进桌面壳，`distribute_steam/itch` 产出可运行桌面包（诚实标注 web-in-desktop）。

### Tier 2 — 代码可写、验证需外部工具/账号（本机出包、真机/云端验证）
- **微信小游戏 / 小程序**：需微信开发者工具 / 真机 + `miniprogram-ci`（渠道/元数据校验已就绪）。
- **Android 原生**：Godot 可导出 Android，但**需 `ANDROID_SDK_ROOT` + `adb` + debug keystore**（当前未装）。

### Tier 3 — 本机物理不可达（需换机/外包，只给 CI 步骤、不在此机验证）
- **iOS 原生**：必须 macOS + Xcode；本机 Windows 不可达。标注"需 macOS 构建机"，提供 GitHub Actions / 自托管 CI 步骤，不标已验证。

---

## 3. 分阶段实施

### Phase 0 — 让 Godot 适配器真正跑起来（最小改动、立即见效）
1. **扩展 Godot 发现**：`EnvironmentInspector` / `GodotRuntimeAdapter._resolve_executable()` 增加探测——`GODOT_EXECUTABLE` 环境变量、`config/godot.json`、`D:\Godot\`/`C:\Godot\`/`~/godot/` 下的 `*_console.exe`（headless 优先 console 版），写回工具清单 `tools.godot.executable`。
2. **真跑验证**：对已生成的 Godot 项目（如 `output/cyber_survivor` 或新建 `output/godot_demo`）执行 `preflight`→`launch`→`run_scenarios`，headless 推进 `MIN_FRAMES=30` 帧，采集真实帧数/状态/无 `SCRIPT ERROR`。
3. **导出 PC 包**：新增 Godot export preset（Windows），产出 `.exe`+`.pck`；`distribute_steam/itch` 支持接收 Godot 导出物（不只 web HTML）。
4. **登记**：`CapabilityRegistry` 标 `godot-pc` 为 verified（附 EvidencePack）。

### Phase 1 — HostContract 通用化（所有非 web 端的基础）
1. 把 `window.__GAME_AGENT__` 抽象为 `HostContract` 接口：`report_frame() / mark_state() / reflect_input()`。
2. 实现四个契约：`BrowserContract`（现有 WebGL/DOM）、`GodotContract`（GDScript 探针上报 `GAME_AGENT_CONTRACT`）、`MiniProgramContract`（`wx.*` 映射）、`NativeContract`。
3. 运行时适配器统一消费 `HostContract`，门禁逻辑复用，避免每端重写。

### Phase 2 — 微信小游戏 / 小程序（Tier 2）
1. 新增 `MiniProgramRuntimeAdapter` + `MiniProgramContract`：把 web/Canvas 游戏的 DOM 假设（`window`/`document`/`canvas`/`requestAnimationFrame`/`Audio`）映射到微信运行时（`wx.createCanvas`/`wx.createImage`/`wx.onTouchStart`/`wx.createInnerAudioContext`）。
2. 适配器在微信开发者工具 CLI / 真机验证"画面真在动、触摸真生效"。
3. 复用 `store_submission` 的 `wechat` 渠道（`miniprogram-ci` uploader）；`distribute_wechat` 产出真·小游戏项目（`game.json` + 适配后 js + 资源）。

### Phase 3 — PC 桌面 web-shell（Tier 1，快速覆盖）
1. 新增 `DesktopShellAdapter`（Electron 或 Tauri）：封装现有 web 构建。
2. `distribute_steam/itch` 产出可运行桌面包，诚实标注 `web-in-desktop`，不冒充原生引擎。

### Phase 4 — Android 原生（Tier 2，需装 SDK）
1. Godot export preset 增加 Android；需 `ANDROID_SDK_ROOT` + `adb` + debug keystore。
2. 新增 `AndroidRuntimeAdapter`：真机/模拟器验证（待你装 SDK 后启用）。

### Phase 5 — iOS / 全商店（Tier 3）
1. iOS：本机不可达，提供 macOS CI 步骤（GitHub Actions + `godot --headless --export-release` + Xcode `xcodebuild`），标注"需 macOS 构建机验证"，不标已验证。
2. 商店提交补全：新增 App Store / Google Play 渠道（现有 `wechat/steam/itch/pwa` 之外）。

---

## 4. 每端验证与诚实门禁

每个新端必须产出并写入 `EvidencePack`：
- **真实帧渲染计数**（画面真在动）
- **状态迁移证据**（boot→core_loop→…）
- **输入反射证据**（键鼠/触摸真生效）

缺失对应资源即如实返回：`NEEDS_RUNTIME_TOOL` / `NEEDS_SDK` / `NEEDS_CREDENTIALS`，**绝不 PASS**。

---

## 5. 能力登记与文档

- `CapabilityRegistry` 增加：`godot-pc` / `wechat-mini` / `desktop-shell` / `android-native` / `ios-native`，各自 `maturity` + `evidence`。
- `README.md` 增加「多端支持矩阵」表（已验证 / 待工具 / 本机不可达）。
- 工业级判定更新：从"仅 Web"扩展为"Web + Godot-PC 已验证；小程序/安卓按端诚实标注；iOS 本机不可达"。

---

## 6. 风险与红线

- 不跨端借证据（Web 的像素证据不能证明 Godot/原生端在动）。
- 不把 web-shell 粉饰成原生引擎。
- iOS 不在本机验证就绝不标"支持"；只给 CI 步骤并标注 unverified。
- 所有新端改动纳入 `tests/`，复用 `CODEBUDDY_SAFE_DELETE_ENABLED=0` + 系统 Python 3.14.7 跑回归（整仓连跑 2 次确定性绿）。

---

## 7. 建议执行顺序（最小可行 + 最快见真章）

1. **Phase 0（Godot 跑起来）** → 立刻多出"PC 原生"已验证端，改动最小。
2. **Phase 1（HostContract 通用化）** → 为小程序/原生铺路。
3. **Phase 3（web-shell 桌面）** → 快速多覆盖 PC。
4. **Phase 2（微信小游戏）** → 覆盖小程序/H5 真验证。
5. **Phase 4/5（安卓/iOS）** → 等你装 Android SDK / 给 macOS 构建机。

> 推荐从 **Phase 0** 起步：本机 Godot 已就绪，是最快把"全栈"从口号变成"多一个真验证端"的一步。
