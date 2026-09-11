#!/usr/bin/env python3
"""pipeline/channel_doctor.py: 外部渠道体检与人工配合清单

背景：Agent 已能构建分发包并做提交前门禁（pipeline/store_submission.py），
但「真正上到外部渠道」还差一批只能由人来提供的东西：商店账号、官方上传器、
商店素材、隐私政策、年龄分级问卷、版号/备案材料。这些不可能由代码变出来。

本模块做的不是「假装能上架」，而是把这些缺口逐项体检出来，并明确标注：

    owner="human" —— 必须由人（丁建）提供，Agent 无法代劳
    owner="agent" —— Agent 可自行产出（可用 --dist 产物或 autonomous 出货包补齐）

体检项逐条给出 status / detail / how_to_fix，因此本模块的输出本身就是
「你该怎么配合」的清单，且随配置变化自动更新，不会写死过期。

诚实红线：凭据值一律不打印（只报是否设置、长度、格式是否合法）。
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from pipeline.store_submission import STORE_SPECS, _image_size

OK = "OK"
MISSING = "MISSING"
INVALID = "INVALID"
NEEDS_HUMAN = "NEEDS_HUMAN"

HUMAN = "human"
AGENT = "agent"

# ── 凭据真实性校验：不仅看「有没有」，还看「像不像真的」 ─────────────────────
CREDENTIAL_VALIDATORS: Dict[str, Callable[[str], Tuple[bool, str]]] = {
    "WECHAT_APPID": lambda v: (
        bool(re.fullmatch(r"wx[0-9a-f]{16}", v.strip())),
        "格式应为 wx + 16 位小写十六进制（微信公众平台后台可见）",
    ),
    "WECHAT_CI_KEY_PATH": lambda v: (
        Path(v.strip()).is_file(),
        "必须是真实存在的上传密钥文件（private.key）路径",
    ),
    "STEAM_USER": lambda v: (len(v.strip()) >= 3, "Steamworks 登录用户名"),
    "STEAM_APP_ID": lambda v: (v.strip().isdigit(), "必须是纯数字 AppID（Steamworks 后台分配）"),
    "ITCH_BUTLER_TARGET": lambda v: (
        bool(re.fullmatch(r"[A-Za-z0-9_\-]+/[A-Za-z0-9_\-]+", v.strip())),
        "格式应为 user/game（itch.io 项目页地址的最后两段）",
    ),
    "PWA_DEPLOY_BASE_URL": lambda v: (
        v.strip().startswith("https://"),
        "必须是 https 开头的线上部署地址（PWA 强制 https）",
    ),
}

# ── 官方上传器与获取方式（缺哪个就装哪个） ─────────────────────────────────
UPLOADER_HOWTO: Dict[str, str] = {
    "miniprogram-ci": "npm i -g miniprogram-ci（需 Node.js；微信官方代码上传 CLI）",
    "steamcmd": "https://developer.valvesoftware.com/wiki/SteamCMD 下载解压后加入 PATH",
    "butler": "https://itch.io/docs/butler/ 安装后执行 butler login 完成授权",
}

# ── 纯人工材料：代码变不出来，只能人准备 ───────────────────────────────────
HUMAN_MATERIALS: Dict[str, List[Dict[str, str]]] = {
    "wechat": [
        {"item": "微信小游戏账号与 AppID", "how": "微信公众平台 mp.weixin.qq.com 注册小游戏账号（需主体资质）", "why": "上传与提审的唯一身份"},
        {"item": "小程序代码上传密钥 private.key", "how": "mp 后台 开发管理 -> 开发设置 -> 小程序代码上传密钥 -> 下载", "why": "miniprogram-ci 上传必需"},
        {"item": "游戏类目资质与自审报告", "how": "按微信小游戏类目要求提交（游戏类目需版号或备案材料）", "why": "类目审核硬性要求"},
        {"item": "版号 / 备案材料", "how": "国内发行需国家新闻出版署版号，或按平台要求做备案", "why": "无版号无法商业化与正式上线"},
        {"item": "隐私政策正文与线上 URL", "how": "自行发布到 https 站点后填 privacy_policy_url", "why": "商店审核硬性要求"},
    ],
    "steam": [
        {"item": "Steamworks 开发者账号", "how": "https://partner.steamgames.com 注册并支付上架费", "why": "创建 AppID 与提审的前置"},
        {"item": "AppID 与 app_build.vdf", "how": "Steamworks 后台创建应用获取 AppID；构建脚本按官方 vdf 格式填写", "why": "steamcmd 上传定位应用"},
        {"item": "税务与收款信息", "how": "Steamworks 后台 Tax Information / 银行信息", "why": "无税务信息无法发售"},
        {"item": "IARC 或年龄分级问卷", "how": "Steamworks 后台填写商店问卷与分级", "why": "定价与上架前置"},
        {"item": "隐私政策与第三方 SDK 声明", "how": "发布 https 隐私政策页；在元数据 third_party_sdks 声明", "why": "GDPR/商店合规"},
    ],
    "itch": [
        {"item": "itch.io 账号与 API Key", "how": "https://itch.io/user/settings/api-keys 生成后 butler login", "why": "butler push 授权"},
        {"item": "项目页地址（user/game）", "how": "itch.io 后台新建项目后取地址最后两段", "why": "上传目标定位"},
        {"item": "隐私政策 URL", "how": "发布 https 隐私政策页后填写", "why": "itch 项目页要求"},
    ],
    "pwa": [
        {"item": "https 托管站点与部署凭据", "how": "任意静态托管（如 Vercel/Netlify/自有服务器），配置 PWA_DEPLOY_BASE_URL", "why": "PWA 安装与分享强制 https"},
        {"item": "隐私政策 URL 与年龄分级", "how": "发布 https 隐私政策页并在元数据填写 age_rating", "why": "应用商店 PWA 目录审核要求"},
    ],
}

__all__ = ["ChannelDoctor", "diagnose_all", "OK", "MISSING", "INVALID", "NEEDS_HUMAN"]


def _dir_size_mb(path: Path) -> float:
    try:
        total = sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())
    except OSError:
        return 0.0
    return total / (1024 * 1024)


class ChannelDoctor:
    """对单个或全部渠道做体检，输出可执行的补齐清单。"""

    def __init__(self, dist_root: Path, metadata_path: Optional[Path] = None,
                 assets_dir: Optional[Path] = None):
        self.dist_root = Path(dist_root)
        # 商店元数据属于仓库配置（config/），不随 dist_root 漂移：
        # dist_root 默认为 output/dist，其 parent 是 output 而非仓库根。
        root = Path(__file__).resolve().parent.parent
        self.metadata_path = Path(metadata_path) if metadata_path else root / "config" / "store_metadata.json"
        self.assets_dir = Path(assets_dir) if assets_dir else self.dist_root.parent / "store_assets"

    # ---------- 元数据 ----------

    def load_metadata(self) -> Tuple[Dict[str, Any], Optional[str]]:
        if not self.metadata_path.is_file():
            return {}, f"缺少商店元数据文件: {self.metadata_path}"
        try:
            data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return {}, f"商店元数据解析失败: {exc}"
        if not isinstance(data, dict):
            return {}, "商店元数据必须是 JSON 对象"
        return data, None

    # ---------- 单项体检 ----------

    def check_credentials(self, channel: str) -> List[Dict[str, Any]]:
        spec = STORE_SPECS[channel]
        rows: List[Dict[str, Any]] = []
        for env_name in spec["credential_env"]:
            raw = (os.environ.get(env_name) or "").strip()
            if not raw:
                rows.append({
                    "item": f"凭据 {env_name}", "status": MISSING, "owner": HUMAN,
                    "detail": "环境变量未设置",
                    "how_to_fix": f"在 .env（已被 gitignore）或系统环境变量中设置 {env_name}",
                })
                continue
            validator = CREDENTIAL_VALIDATORS.get(env_name)
            if validator is None:
                rows.append({
                    "item": f"凭据 {env_name}", "status": OK, "owner": HUMAN,
                    "detail": f"已设置（长度 {len(raw)}，值不打印）", "how_to_fix": "",
                })
                continue
            ok, hint = validator(raw)
            rows.append({
                "item": f"凭据 {env_name}",
                "status": OK if ok else INVALID, "owner": HUMAN,
                "detail": f"已设置（长度 {len(raw)}，值不打印）" if ok else f"已设置但格式/路径不合法：{hint}",
                "how_to_fix": "" if ok else hint,
            })
        return rows

    def check_uploader(self, channel: str) -> Dict[str, Any]:
        spec = STORE_SPECS[channel]
        uploader = spec.get("uploader")
        if not uploader:
            return {
                "item": "官方上传器", "status": NEEDS_HUMAN, "owner": HUMAN,
                "detail": f"{spec['label']} 无官方 CLI 上传适配器",
                "how_to_fix": "需人工在商店后台上传，或自行接入该渠道的部署脚本后扩展 STORE_SPECS",
            }
        path = shutil.which(uploader)
        if path is None:
            return {
                "item": f"官方上传器 {uploader}", "status": MISSING, "owner": HUMAN,
                "detail": "PATH 中未找到可执行文件",
                "how_to_fix": UPLOADER_HOWTO.get(uploader, f"安装 {uploader} 并加入 PATH"),
            }
        return {
            "item": f"官方上传器 {uploader}", "status": OK, "owner": HUMAN,
            "detail": f"已找到: {path}", "how_to_fix": "",
        }

    def check_metadata(self, channel: str, metadata: Dict[str, Any],
                       meta_error: Optional[str]) -> List[Dict[str, Any]]:
        spec = STORE_SPECS[channel]
        if meta_error:
            return [{
                "item": "商店元数据文件", "status": MISSING, "owner": HUMAN,
                "detail": meta_error,
                "how_to_fix": "复制 config/store_metadata.example.json 为 config/store_metadata.json 并逐字段填写",
            }]
        channel_meta = metadata.get(channel) or metadata
        rows: List[Dict[str, Any]] = []
        for field in spec["required_metadata"]:
            value = str(channel_meta.get(field, "")).strip()
            if value:
                rows.append({
                    "item": f"元数据 {field}", "status": OK, "owner": HUMAN,
                    "detail": f"已填写（{value[:40]}）", "how_to_fix": "",
                })
            else:
                rows.append({
                    "item": f"元数据 {field}", "status": MISSING, "owner": HUMAN,
                    "detail": "必填字段为空",
                    "how_to_fix": f"在 config/store_metadata.json 的 {channel} 段填写 {field}",
                })

        privacy = str(channel_meta.get("privacy_policy_url", "")).strip()
        rows.append({
            "item": "隐私政策 https 链接",
            "status": OK if privacy.startswith("https://") else INVALID,
            "owner": HUMAN,
            "detail": privacy if privacy.startswith("https://") else "缺失或不是 https 链接",
            "how_to_fix": "" if privacy.startswith("https://") else "发布隐私政策到 https 站点后填入",
        })

        sdks = channel_meta.get("third_party_sdks")
        rows.append({
            "item": "第三方 SDK 声明",
            "status": OK if isinstance(sdks, list) else INVALID,
            "owner": HUMAN,
            "detail": f"已声明 {len(sdks)} 项" if isinstance(sdks, list) else "third_party_sdks 必须是列表（支付/广告/统计 SDK 需如实声明）",
            "how_to_fix": "" if isinstance(sdks, list) else "在元数据中填 third_party_sdks: [] 或列出实际 SDK",
        })
        return rows

    def check_assets(self, channel: str) -> List[Dict[str, Any]]:
        spec = STORE_SPECS[channel]
        rows: List[Dict[str, Any]] = []
        for asset in spec["required_assets"]:
            path = self.assets_dir / asset["filename"]
            if not path.is_file():
                rows.append({
                    "item": f"素材 {asset['key']}", "status": MISSING, "owner": AGENT,
                    "detail": f"缺少文件: {path}",
                    "how_to_fix": f"放入 {path}（要求 ≥{asset['width']}x{asset['height']}）；可由实机截图或 AIGC 出图后人工确认",
                })
                continue
            size = _image_size(path)
            if size is None:
                rows.append({
                    "item": f"素材 {asset['key']}", "status": INVALID, "owner": AGENT,
                    "detail": f"无法解析图片尺寸（需 PNG/JPEG）: {path}",
                    "how_to_fix": "重新导出为标准 PNG/JPEG",
                })
                continue
            width, height = size
            ok = width >= asset["width"] and height >= asset["height"]
            rows.append({
                "item": f"素材 {asset['key']}",
                "status": OK if ok else INVALID, "owner": AGENT,
                "detail": f"{path.name} 实测 {width}x{height}（要求 ≥{asset['width']}x{asset['height']}）",
                "how_to_fix": "" if ok else f"放大到 ≥{asset['width']}x{asset['height']}",
            })
        return rows

    def check_package(self, channel: str) -> Dict[str, Any]:
        spec = STORE_SPECS[channel]
        package_dir = self.dist_root / spec["package_subdir"]
        if not package_dir.is_dir():
            return {
                "item": "渠道分发包", "status": MISSING, "owner": AGENT,
                "detail": f"未找到: {package_dir}",
                "how_to_fix": "先运行 python game_agent.py distribute 生成各渠道包",
            }
        size_mb = _dir_size_mb(package_dir)
        limit = spec.get("max_package_mb")
        if limit is None:
            return {
                "item": "渠道分发包", "status": OK, "owner": AGENT,
                "detail": f"已构建，实测 {size_mb:.2f}MB（该渠道无硬性首包阈值）", "how_to_fix": "",
            }
        ok = size_mb <= limit
        return {
            "item": "渠道分发包",
            "status": OK if ok else INVALID, "owner": AGENT,
            "detail": f"实测 {size_mb:.2f}MB / 上限 {limit}MB",
            "how_to_fix": "" if ok else f"瘦身到 ≤{limit}MB（分包、压缩资源、首包延迟加载）",
        }

    # ---------- 汇总 ----------

    def diagnose(self, channel: str) -> Dict[str, Any]:
        spec = STORE_SPECS.get(channel)
        if spec is None:
            return {"channel": channel, "status": INVALID,
                    "errors": [f"未知渠道: {channel}，可选: {', '.join(STORE_SPECS)}"],
                    "checks": [], "human_materials": []}

        metadata, meta_error = self.load_metadata()
        checks: List[Dict[str, Any]] = []
        checks.extend(self.check_credentials(channel))
        checks.append(self.check_uploader(channel))
        checks.extend(self.check_metadata(channel, metadata, meta_error))
        checks.extend(self.check_assets(channel))
        checks.append(self.check_package(channel))

        blocking = [c for c in checks if c["status"] in (MISSING, INVALID, NEEDS_HUMAN)]
        human_blocking = [c for c in blocking if c["owner"] == HUMAN]
        agent_blocking = [c for c in blocking if c["owner"] == AGENT]

        if not blocking:
            status = OK
        elif human_blocking:
            status = NEEDS_HUMAN
        else:
            status = MISSING

        return {
            "channel": channel,
            "label": spec["label"],
            "status": status,
            "ready": not blocking,
            "total": len(checks),
            "ok": sum(1 for c in checks if c["status"] == OK),
            "blocking": len(blocking),
            "blocking_human": len(human_blocking),
            "blocking_agent": len(agent_blocking),
            "checks": checks,
            "human_materials": HUMAN_MATERIALS.get(channel, []),
        }

    def diagnose_all(self) -> Dict[str, Any]:
        reports = [self.diagnose(ch) for ch in STORE_SPECS]
        return {
            "channels": reports,
            "ready": [r["channel"] for r in reports if r.get("ready")],
            "needs_human": [r["channel"] for r in reports if r.get("status") == NEEDS_HUMAN],
            "dist_root": str(self.dist_root),
            "metadata_path": str(self.metadata_path),
            "assets_dir": str(self.assets_dir),
        }


def diagnose_all(dist_root: Path, metadata_path: Optional[Path] = None,
                 assets_dir: Optional[Path] = None) -> Dict[str, Any]:
    return ChannelDoctor(dist_root, metadata_path, assets_dir).diagnose_all()
