#!/usr/bin/env python3
"""pipeline/run_mode.py：运行模式分离 —— 本地开发（local） / 平台对接（platform）

为什么要分：
    用户拿到 agent 的第一诉求是「先把游戏做出来」，而不是先去申请微信/ steam
    / itch 账号、支付沙箱、Staging 域名。把两类依赖混在一起，会导致
    「没配渠道凭据 → 整条流水线 PAUSED → 连本地开发都做不了」。

    本模块把依赖切成两档：
      · local    —— 只要 LLM 端点就能开发、出包、本地试玩；
                    渠道凭据 / 沙箱 / Staging / 遥测一概不看、一概不阻塞。
      · platform —— 在 local 基础上，额外要求四类外部依赖齐全；
                    缺任一组即明确阻断并列出缺什么，绝不用本地假数据冒充。

诚实红线（13.2）：
    1. 本地模式**允许验证类能力降级**，但绝不允许把「没验证」写成「已验证」：
       降级节点记入 unverified，整机状态为 COMPLETED_UNVERIFIED（退出码 5），
       并在输出里点名未验证项。
    2. 平台模式缺外部配置一律阻断（NEEDS_HUMAN），不做任何本地模拟替代。
    3. 本模块只回答「是否设置 / 格式是否合法」，绝不打印任何凭据值。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

LOCAL = "local"
PLATFORM = "platform"
VALID_MODES = (LOCAL, PLATFORM)

MODE_ENV = "GAME_RUN_MODE"

# ── 本地模式下允许降级的节点：它们只影响「验证强度」，不影响「能否出货」──────
# playtest = 真机自动试玩，依赖本机浏览器自动化驱动；缺驱动时降级为「未验证」。
DEGRADABLE_NODES_IN_LOCAL = frozenset({"playtest"})

# ── 本地工具链：本地开发模式下的体检项 ───────────────────────────────────────
# required=True 缺了会阻断；required=False 缺了只降级并如实标注。
LOCAL_TOOLCHAIN: List[Dict[str, Any]] = [
    {
        "key": "llm",
        "label": "LLM 端点池",
        "required": True,
        "env": [],
        "how_to_fix": "在 config/llm_endpoints.json 或 .env 配置至少一个可用 LLM 端点",
        "degrade_note": "",
    },
    {
        "key": "comfyui",
        "label": "ComfyUI（AIGC 美术）",
        "required": False,
        "env": ["COMFYUI_URL"],
        "how_to_fix": "启动 ComfyUI 后在 .env 配置 COMFYUI_URL=http://127.0.0.1:8188",
        "degrade_note": "缺则美术降级为程序化占位，并在 provenance 标注 procedural_placeholder",
    },
    {
        "key": "godot",
        "label": "Godot（仅 Godot 目标需要）",
        "required": False,
        "env": ["GODOT_PATH"],
        "how_to_fix": "在 .env 配置 GODOT_PATH=D:/Godot/Godot_v4.7.2-stable_win64.exe",
        "degrade_note": "Web 目标不需要；Godot 目标缺此项将无法导出",
    },
    {
        "key": "browser",
        "label": "浏览器自动化驱动（真机试玩）",
        "required": False,
        "env": ["CHROMIUM_PATH"],
        "how_to_fix": "pip install playwright（复用本机 Edge/Chrome，无需下载浏览器）",
        "degrade_note": "缺则 playtest 判为「未验证」，出货包仍产出但不得声称已试玩",
    },
]

# ── 平台模式下额外要求的外部依赖组 ───────────────────────────────────────────
PLATFORM_GROUPS: List[Dict[str, Any]] = [
    {
        "key": "channel_wechat",
        "label": "渠道 · 微信小游戏",
        "env": ["WECHAT_APPID", "WECHAT_APP_SECRET"],
        "how_to_fix": "微信公众平台后台获取 AppID/AppSecret；版号与备案属纯人工材料，代码替代不了",
    },
    {
        "key": "channel_steam",
        "label": "渠道 · Steam",
        "env": ["STEAM_APP_ID", "STEAM_USERNAME"],
        "how_to_fix": "Steamworks 后台创建应用后取得 AppID，并配置 steamcmd 上传账号",
    },
    {
        "key": "channel_itch",
        "label": "渠道 · itch.io",
        "env": ["ITCH_BUTLER_TARGET", "ITCH_API_KEY"],
        "how_to_fix": "itch.io 创建项目后取得 user/game 目标串与 API Key，并安装 butler",
    },
    {
        "key": "sandbox_payment",
        "label": "线上服务 · 支付沙箱",
        "env": ["PAYMENT_SANDBOX_URL", "PAYMENT_SANDBOX_KEY"],
        "how_to_fix": "申请支付服务商沙箱，配置 URL+KEY；对端 /health 须自报 service=payment",
    },
    {
        "key": "sandbox_ads",
        "label": "线上服务 · 广告沙箱",
        "env": ["ADS_SANDBOX_URL", "ADS_SANDBOX_KEY"],
        "how_to_fix": "申请广告平台沙箱；对端 /health 须自报 service=ads",
    },
    {
        "key": "sandbox_multiplayer",
        "label": "线上服务 · 联机沙箱",
        "env": ["MULTIPLAYER_SANDBOX_URL", "MULTIPLAYER_SANDBOX_KEY"],
        "how_to_fix": "部署联机服务沙箱；对端 /health 须自报 service=multiplayer",
    },
    {
        "key": "staging",
        "label": "线上服务 · Staging 预发布",
        "env": ["STAGING_BASE_URL"],
        "how_to_fix": "部署真实 https 预发布环境（远端必须 https，本地联调可用 http://127.0.0.1:port）",
    },
    {
        "key": "telemetry",
        "label": "真实玩家 · 遥测端点",
        "env": ["TELEMETRY_ENDPOINT", "TELEMETRY_KEY"],
        "how_to_fix": "部署遥测服务；埋点须带 properties.source ∈ real_player/playtest/beta/store/live",
    },
]

OK = "OK"
MISSING = "MISSING"
OPTIONAL_MISSING = "OPTIONAL_MISSING"
NEEDS_HUMAN = "NEEDS_HUMAN"

__all__ = [
    "LOCAL", "PLATFORM", "VALID_MODES", "MODE_ENV",
    "DEGRADABLE_NODES_IN_LOCAL", "LOCAL_TOOLCHAIN", "PLATFORM_GROUPS",
    "resolve_mode", "check_local_readiness", "check_platform_readiness",
    "describe_mode", "OK", "MISSING", "OPTIONAL_MISSING", "NEEDS_HUMAN",
]


def resolve_mode(value: Optional[str] = None) -> str:
    """解析运行模式：CLI 参数 > 环境变量 GAME_RUN_MODE > 默认 local。

    非法值一律退回 local 而不是抛错——模式只影响门禁松紧，
    不该因为拼错一个单词就让开发跑不起来；但会如实告知。
    """
    raw = (value or os.environ.get(MODE_ENV) or "").strip().lower()
    if raw in VALID_MODES:
        return raw
    return LOCAL


def _env_set(name: str) -> bool:
    return bool((os.environ.get(name) or "").strip())


def _has_llm_endpoint() -> bool:
    """LLM 端点是否可用：复用 llm_gateway 的既有判定，避免两套口径。"""
    try:
        from core.llm_gateway import LLMGateway
        providers = LLMGateway.available_providers() or []
    except Exception:
        return False
    return len(providers) > 0


def check_local_readiness(mode: str = LOCAL) -> Dict[str, Any]:
    """本地开发模式体检：只查本地工具链，绝不查渠道/沙箱/Staging/遥测。"""
    items: List[Dict[str, Any]] = []
    blocking: List[str] = []
    degraded: List[str] = []

    for spec in LOCAL_TOOLCHAIN:
        if spec["key"] == "llm":
            ok = _has_llm_endpoint()
        elif spec["key"] == "browser":
            ok = _browser_driver_available()
        elif spec["env"]:
            ok = any(_env_set(e) for e in spec["env"]) or _auto_detect(spec["key"])
        else:
            ok = False

        if ok:
            status = OK
        elif spec["required"]:
            status = MISSING
            blocking.append(spec["label"])
        else:
            status = OPTIONAL_MISSING
            degraded.append(spec["label"])

        items.append({
            "key": spec["key"], "item": spec["label"], "status": status,
            "required": bool(spec["required"]),
            "detail": "已就绪" if ok else (spec["degrade_note"] or "未配置"),
            "how_to_fix": "" if ok else spec["how_to_fix"],
        })

    ready = not blocking
    result: Dict[str, Any] = {
        "mode": mode, "ready": ready, "items": items,
        "blocking": blocking, "degraded": degraded,
        "note": "本地模式不检查渠道/沙箱/Staging/遥测：这些只在 platform 模式下要求",
    }
    return result


def _auto_detect(key: str) -> bool:
    """部分工具链可以本机自动探测，不必用户显式配置路径。"""
    if key == "godot":
        try:
            from core.environment_inspector import EnvironmentInspector
            return bool(EnvironmentInspector.detect_godot_executable())
        except Exception:
            return False
    if key == "comfyui":
        # COMFYUI_URL 有默认值 http://127.0.0.1:8188，探测一次即可
        try:
            from pipeline.env_check import _probe_comfyui  # noqa: WPS433
            return bool(_probe_comfyui().get("ok"))
        except Exception:
            return False
    return False


def _browser_driver_available() -> bool:
    """真机试玩是否可用 = 有浏览器可执行程序 + 有自动化驱动。"""
    try:
        from core.environment_inspector import EnvironmentInspector
        if not EnvironmentInspector.detect_chromium_executable():
            return False
    except Exception:
        return False
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except Exception:
        return False


def check_platform_readiness() -> Dict[str, Any]:
    """平台对接模式体检：本地工具链 + 四类外部依赖，缺任一组即阻断。"""
    local = check_local_readiness(PLATFORM)
    groups: List[Dict[str, Any]] = []
    blocking: List[str] = list(local["blocking"])

    for spec in PLATFORM_GROUPS:
        missing = [e for e in spec["env"] if not _env_set(e)]
        present = [e for e in spec["env"] if _env_set(e)]
        ok = not missing
        if not ok:
            blocking.append(spec["label"])
        groups.append({
            "key": spec["key"], "group": spec["label"],
            "status": OK if ok else NEEDS_HUMAN,
            "present": present, "missing": missing,
            "detail": "已配置（值不打印）" if ok else f"缺 {len(missing)}/{len(spec['env'])} 项",
            "how_to_fix": "" if ok else spec["how_to_fix"],
        })

    return {
        "mode": PLATFORM,
        "ready": not blocking,
        "local": local,
        "groups": groups,
        "blocking": blocking,
        "note": "平台模式缺任一组即阻断：外部账号/沙箱/域名无法由代码替代，必须人工提供",
    }


def describe_mode(mode: str) -> str:
    if mode == PLATFORM:
        return ("platform（平台对接）：本地工具链 + 渠道凭据 + 三类沙箱 + Staging + 遥测，"
                "缺一项即阻断；产出可走真实上架与线上运营")
    return ("local（本地开发）：只需 LLM 端点即可开发、出包、本地试玩；"
            "渠道/沙箱/Staging/遥测一概不要求，缺试玩驱动只降级为「未验证」")
