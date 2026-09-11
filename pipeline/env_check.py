#!/usr/bin/env python3
"""pipeline/env_check.py: 环境与外部信息自检总表

把四个缺口的体检结果聚成一张表，回答一个问题：
「丁建填完之后，还差什么？」

不重复实现检查逻辑，只做聚合：
    本地工具链  -> ComfyUI / Godot 是否可达或存在
    缺口①渠道   -> pipeline.channel_doctor
    缺口②线上   -> pipeline.live_service_doctor
    缺口④遥测   -> pipeline.player_validation
    LLM 端点池  -> config/llm_endpoints.json 是否存在且可解析（不读密钥内容）

两条硬规则：
    1. 只报「是否设置 / 格式是否合法 / 探测是否通过」，绝不打印凭据值。
    2. 默认做真实探测（可 --no-probe 关闭）。探测失败就是失败，不用配置存在冒充可用。
"""
from __future__ import annotations

import json
import os
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline.channel_doctor import ChannelDoctor, HUMAN, MISSING, NEEDS_HUMAN, OK
from pipeline.live_service_doctor import LiveServiceDoctor, PASS
from pipeline.player_validation import PlayerValidation

TOOLCHAIN = "toolchain"
CHANNELS = "channels"
LIVE = "live_services"
TELEMETRY = "telemetry"
LLM = "llm"

UNREACHABLE = "UNREACHABLE"
IDENTITY_UNVERIFIED = "IDENTITY_UNVERIFIED"

DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"
COMPYUI_TIMEOUT_S = 2.5

__all__ = ["EnvCheck", "OK", "MISSING"]


class EnvCheck:
    """聚合四类体检，输出一张「还差什么」的总表。"""

    def __init__(self, dist_root: Optional[Path] = None, probe: bool = True):
        root = Path(__file__).resolve().parent.parent
        self.root = root
        self.dist_root = Path(dist_root) if dist_root else root / "output" / "dist"
        self.probe = probe

    # ---------- 本地工具链 ----------

    def check_toolchain(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        comfy_url = (os.environ.get("COMFYUI_URL") or "").strip() or DEFAULT_COMFYUI_URL
        if not self.probe:
            rows.append({"item": "ComfyUI 出图服务", "status": OK if comfy_url else MISSING,
                         "owner": "human",
                         "detail": f"配置为 {comfy_url}（--no-probe 未做真实探测）",
                         "how_to_fix": ""})
        else:
            rows.append(self._probe_comfyui(comfy_url))

        godot = (os.environ.get("GODOT_PATH") or "").strip() or shutil.which("godot") or ""
        if not godot:
            default = Path(r"D:\Godot\Godot_v4.7.2-stable_win64.exe")
            godot = str(default) if default.is_file() else ""
        rows.append({
            "item": "Godot 引擎",
            "status": OK if godot and Path(godot).is_file() else MISSING,
            "owner": "agent",
            "detail": f"已找到 {godot}" if godot else "未找到 Godot（Web 主线不强依赖，Godot 目标需要）",
            "how_to_fix": "" if godot else "安装 Godot 4.x 后设置 GODOT_PATH 指向可执行文件",
        })
        return rows

    def _probe_comfyui(self, url: str) -> Dict[str, Any]:
        request = urllib.request.Request(url.rstrip("/") + "/system_stats", method="GET",
                                         headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=COMPYUI_TIMEOUT_S) as response:
                code = response.getcode()
                raw = response.read(8192).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return {"item": "ComfyUI 出图服务", "status": UNREACHABLE, "owner": "human",
                    "detail": f"/system_stats 返回 HTTP {exc.code}",
                    "how_to_fix": "启动 ComfyUI（默认 http://127.0.0.1:8188），或用 COMFYUI_URL 指向实际地址"}
        except (urllib.error.URLError, TimeoutError, OSError):
            return {"item": "ComfyUI 出图服务", "status": UNREACHABLE, "owner": "human",
                    "detail": f"无法连接 {url}",
                    "how_to_fix": "启动 ComfyUI（默认 http://127.0.0.1:8188），或用 COMFYUI_URL 指向实际地址"}
        if code >= 400:
            return {"item": "ComfyUI 出图服务", "status": UNREACHABLE, "owner": "human",
                    "detail": f"/system_stats 返回 HTTP {code}",
                    "how_to_fix": "确认 ComfyUI 已就绪"}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"item": "ComfyUI 出图服务", "status": IDENTITY_UNVERIFIED, "owner": "human",
                    "detail": "响应不是 JSON，可能不是 ComfyUI",
                    "how_to_fix": "确认 COMFYUI_URL 指向的是 ComfyUI 服务"}
        if not isinstance(payload, dict) or not ("system" in payload or "devices" in payload):
            return {"item": "ComfyUI 出图服务", "status": IDENTITY_UNVERIFIED, "owner": "human",
                    "detail": "响应缺少 system/devices 字段，可能不是 ComfyUI",
                    "how_to_fix": "确认 COMFYUI_URL 指向的是 ComfyUI 服务"}
        return {"item": "ComfyUI 出图服务", "status": OK, "owner": "human",
                "detail": f"已连通 {url}（识别为 ComfyUI）", "how_to_fix": ""}

    # ---------- 缺口①渠道 ----------

    def check_channels(self) -> List[Dict[str, Any]]:
        doctor = ChannelDoctor(self.dist_root)
        rows: List[Dict[str, Any]] = []
        for channel in ("wechat", "steam", "itch", "pwa"):
            report = doctor.diagnose(channel)
            blocking_human = sum(1 for c in report.get("checks", [])
                                 if c["status"] != OK and c["owner"] == HUMAN)
            rows.append({
                "item": f"渠道 {channel}（{report.get('label', channel)}）",
                "status": OK if report.get("ready") else (NEEDS_HUMAN if blocking_human else MISSING),
                "owner": HUMAN,
                "detail": f"通过 {report.get('ok', 0)}/{report.get('total', 0)}，"
                          f"待人工 {report.get('blocking_human', 0)} 项",
                "how_to_fix": "" if report.get("ready") else f"运行 python game_agent.py channel-doctor --channel {channel} 查看明细",
            })
        return rows

    # ---------- 缺口②线上服务 ----------

    def check_live_services(self) -> List[Dict[str, Any]]:
        doctor = LiveServiceDoctor()
        rows: List[Dict[str, Any]] = []
        payload = doctor.diagnose_all() if self.probe else None
        if payload is None:
            for kind, label in (("payment", "支付沙箱"), ("ads", "广告沙箱"),
                                ("multiplayer", "联机沙箱"), ("staging", "Staging 部署")):
                rows.append({"item": label, "status": MISSING, "owner": HUMAN,
                             "detail": "--no-probe 未做真实探测",
                             "how_to_fix": "运行 python game_agent.py live-doctor 查看明细"})
            return rows
        for report in payload["services"]:
            rows.append({
                "item": f"{report.get('label', report['kind'])}",
                "status": OK if report.get("ready") else report.get("status", MISSING),
                "owner": HUMAN,
                "detail": "；".join(f"{c['item']}={c['status']}" for c in report["checks"]
                                   if c["status"] != PASS) or "全部通过",
                "how_to_fix": "" if report.get("ready") else f"运行 python game_agent.py live-doctor --kind {report['kind']}",
            })
        return rows

    # ---------- 缺口④遥测 ----------

    def check_telemetry(self) -> List[Dict[str, Any]]:
        validator = PlayerValidation()
        rows = validator.check_telemetry_endpoint()
        for row in rows:
            row.setdefault("owner", HUMAN)
        return rows

    # ---------- LLM ----------

    def check_llm(self) -> List[Dict[str, Any]]:
        path = self.root / "config" / "llm_endpoints.json"
        if not path.is_file():
            return [{"item": "LLM 端点池 config/llm_endpoints.json", "status": MISSING,
                     "owner": HUMAN,
                     "detail": "文件不存在；无 LLM 时自动降级为模板模式（不会伪造 LLM 产出）",
                     "how_to_fix": "复制模板后填入端点与密钥；该文件已被 gitignore，不会进交付物"}]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            count = len(data) if isinstance(data, list) else len(data.get("endpoints", []))
        except (json.JSONDecodeError, OSError):
            return [{"item": "LLM 端点池", "status": "INVALID", "owner": HUMAN,
                     "detail": "文件存在但无法解析为 JSON", "how_to_fix": "检查文件内容格式"}]
        return [{"item": "LLM 端点池", "status": OK if count else MISSING, "owner": HUMAN,
                 "detail": f"已配置 {count} 个端点（密钥内容不读取、不打印）",
                 "how_to_fix": "" if count else "填入至少一个可用端点"}]

    # ---------- 汇总 ----------

    def run(self, mode: str = "") -> Dict[str, Any]:
        from pipeline.run_mode import PLATFORM, LOCAL, resolve_mode
        mode = resolve_mode(mode)
        # 渠道 / 沙箱 / Staging / 遥测只在平台模式下要求；本地开发不看这几组。
        platform_only = {CHANNELS, LIVE, TELEMETRY}
        groups = [
            {"group": TOOLCHAIN, "label": "本地工具链", "checks": self.check_toolchain(),
             "scope": LOCAL},
            {"group": LLM, "label": "LLM 端点池", "checks": self.check_llm(),
             "scope": LOCAL},
            {"group": CHANNELS, "label": "缺口① 外部渠道", "checks": self.check_channels(),
             "scope": PLATFORM},
            {"group": LIVE, "label": "缺口② 线上服务", "checks": self.check_live_services(),
             "scope": PLATFORM},
            {"group": TELEMETRY, "label": "缺口④ 真实玩家遥测", "checks": self.check_telemetry(),
             "scope": PLATFORM},
        ]
        total = sum(len(g["checks"]) for g in groups)
        ready = sum(1 for g in groups for c in g["checks"] if c["status"] == OK)
        pending = [f"{g['label']} / {c['item']}" for g in groups for c in g["checks"] if c["status"] != OK]

        local_groups = [g for g in groups if g["scope"] == LOCAL]
        local_pending = [f"{g['label']} / {c['item']}" for g in local_groups
                         for c in g["checks"] if c["status"] != OK]
        platform_pending = [f"{g['label']} / {c['item']}" for g in groups
                            if g["scope"] == PLATFORM
                            for c in g["checks"] if c["status"] != OK]

        return {
            "status": OK if not pending else MISSING,
            "ready": not pending,
            "total": total,
            "ok": ready,
            "pending_count": len(pending),
            "pending": pending,
            "groups": groups,
            # ── 模式视角：本地开发只关心 local_*，platform_* 属上线阶段 ──
            "mode": mode,
            "local_ready": not local_pending,
            "local_pending": local_pending,
            "local_pending_count": len(local_pending),
            "platform_pending": platform_pending,
            "platform_pending_count": len(platform_pending),
            "platform_only_groups": sorted(platform_only),
        }
