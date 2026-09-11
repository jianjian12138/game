#!/usr/bin/env python3
"""core/host_contract.py: 宿主契约统一接口 (Host Contract)

把原本绑定浏览器的 window.__GAME_AGENT__ 抽象为与平台无关的 HostContract：
    report_frame()     由主循环每帧上报帧计数（证明画面真在动）
    mark_state()       游戏侧显式上报状态迁移（boot -> playing -> gameover）
    reflect_input()    输入（键鼠 / 触摸 / 手柄）真生效的证据采集入口
    parse_evidence()   把宿主真实运行输出归一化为统一的 ContractEvidence

四条平台实现（红线 13.2：每条宿主必须有自己的真证据口径，绝不跨端借证据）：
    BrowserContract      Web / HTML5（现有 window.__GAME_AGENT__ 逻辑封装于此）
    GodotContract        GDScript 无头探针上报 GAME_AGENT_CONTRACT 行
    MiniProgramContract  微信小游戏 wx.* 运行时映射（代码层）
    NativeContract       原生移动端（Android / iOS）通用契约骨架

所有运行时适配器统一消费 HostContract，门禁逻辑复用，避免每端重写。
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# 浏览器契约常量复用 core/runtime_contract 单一真理源，避免两份定义漂移
from core.runtime_contract import (
    CONTRACT_MARKER,
    inject_runtime_contract,
    empty_contract,
)

CONTRACT_NAME = "__GAME_AGENT__"


def default_evidence(host_type: Optional[str] = None) -> Dict[str, Any]:
    """归一化证据骨架：所有契约 parse_evidence 都必须落回这个形状。"""
    return {
        "host_type": host_type,
        "available": False,   # 是否真的在宿主里采到了运行期证据
        "frames": None,       # 主循环帧计数（画面真在动）
        "state": None,        # 最近一次显式状态迁移
        "errors": 0,          # 宿主侧运行期错误计数
        "input_events": 0,    # 输入真生效计数
        "raw": None,          # 原始证据（调试用，不进断言）
    }


class HostContract(ABC):
    """宿主契约抽象基类。每个目标运行时实现自己的观察协议与证据解析。"""

    host_type: str = "base"
    # 该宿主在本机是否可能真验证；纯粹是文档性提示，裁决仍以 preflight 实测为准。
    local_reachable: bool = True

    # ---------------------------------------------------------- 宿主侧上报协议
    # 以下三个方法描述「宿主运行时应如何向适配器上报」，返回可注入/可对照的代码片段或协议描述。
    # 不要求每个宿主都实现全部：Web/Godot 有真实注入脚本，原生端只给协议描述。

    @abstractmethod
    def report_frame(self) -> str:
        """主循环每帧上报帧计数的协议描述（或注入脚本）。"""

    @abstractmethod
    def mark_state(self) -> str:
        """状态迁移上报协议描述（或注入脚本）。"""

    @abstractmethod
    def reflect_input(self) -> str:
        """输入反射证据采集协议描述（或注入脚本）。"""

    # ---------------------------------------------------------- 适配器侧观测

    @abstractmethod
    def parse_evidence(self, raw: Any) -> Dict[str, Any]:
        """把宿主真实运行输出归一化为 ContractEvidence。

        raw 的形态因宿主而异（网页契约对象 / Godot stdout 文本 / wx 事件计数 / 设备日志）。
        解析不到真证据时必须返回 available=False，绝不能凭空填数字。
        """

    def describe(self) -> Dict[str, str]:
        return {
            "host_type": self.host_type,
            "report_frame": self.report_frame(),
            "mark_state": self.mark_state(),
            "reflect_input": self.reflect_input(),
        }


class BrowserContract(HostContract):
    """Web / HTML5 宿主契约：封装现有 window.__GAME_AGENT__ 注入与解析逻辑。

    frame 由包装 requestAnimationFrame/setInterval 得到，state 由游戏侧显式上报，
    errors 来自 window 级 error/unhandledrejection 监听。详见 core/runtime_contract。
    """

    host_type = "browser"

    # 注入脚本由 core/runtime_contract.inject_runtime_contract 统一维护（单一真理源）
    def report_frame(self) -> str:
        return "window.__GAME_AGENT__.frame += 1 (包装 requestAnimationFrame/setInterval)"

    def mark_state(self) -> str:
        return "window.__GAME_AGENT__.markGameOver()/markRestart() 由游戏侧显式调用"

    def reflect_input(self) -> str:
        return "键鼠/触摸事件由游戏自身监听；契约不代持，只记录 game_over_count/restart_count 等侧面上报"

    @staticmethod
    def inject(html: str) -> str:
        """注入运行时契约；已是 web 主线的单一入口。"""
        return inject_runtime_contract(html)

    def parse_evidence(self, raw: Any) -> Dict[str, Any]:
        ev = default_evidence(self.host_type)
        if raw is None:
            return ev
        data: Optional[Dict[str, Any]] = None
        if isinstance(raw, dict):
            data = raw
        elif isinstance(raw, str):
            s = raw.strip()
            if s.startswith("{"):
                try:
                    data = json.loads(s)
                except ValueError:
                    data = None
            else:
                # 可能是整段 HTML：找注入标记，说明契约存在但未被求值
                if CONTRACT_MARKER in raw:
                    ev["available"] = False
                    ev["raw"] = "html-contains-marker-only"
                    return ev
        if not isinstance(data, dict):
            return ev
        ev["available"] = True
        ev["frames"] = data.get("frame") or data.get("frames") or 0
        ev["state"] = data.get("state")
        ev["errors"] = len(data.get("errors") or [])
        ev["input_events"] = (data.get("game_over_count") or 0) + (data.get("restart_count") or 0)
        ev["raw"] = data
        return ev


class GodotContract(HostContract):
    """Godot 宿主契约：无头探针每推进 N 帧打印 GAME_AGENT_CONTRACT 行。

    probe 脚本由 godot_probe_script() 生成，必须 extends SceneTree 并推进主循环；
    适配器解析 stdout 中的 GAME_AGENT_CONTRACT 行得到帧数，拿 SCRIPT ERROR 等判错误。
    """

    host_type = "godot"
    CONTRACT_PREFIX = "GAME_AGENT_CONTRACT"
    PROBE_FILENAME = "game_agent_runtime_probe.gd"
    _ERROR_MARKERS = ("SCRIPT ERROR", "Parse Error", "ERROR:", "Cannot open file", "modules/gdscript")

    def report_frame(self) -> str:
        return f"GDScript 探针在 _process 中累计帧数，达标后打印 {self.CONTRACT_PREFIX} 行"

    def mark_state(self) -> str:
        return "boot/core_loop 由探针推进帧数隐式证明；gameover/restart 需项目侧显式上报（当前未实现则标 NEEDS_GAME_CONTRACT）"

    def reflect_input(self) -> str:
        return "Godot 输入反射需项目侧接入 InputEvent；无头探针不代持，归为未采集"

    @staticmethod
    def godot_probe_script(frames: int = 120) -> str:
        """生成无头运行时探针脚本（extends SceneTree）。"""
        prefix = GodotContract.CONTRACT_PREFIX
        return (
            "extends SceneTree\n\n"
            "var _frames := 0\n\n"
            "func _initialize() -> void:\n"
            '    print("GAME_AGENT_PROBE_START")\n\n'
            "func _process(_delta: float) -> bool:\n"
            "    _frames += 1\n"
            f"    if _frames >= {frames}:\n"
            '        print("%s {\\"frames\\": %d}")\n' % (prefix, frames)
            + "        return true\n"
            "    return false\n"
        )

    def parse_evidence(self, raw: Any) -> Dict[str, Any]:
        ev = default_evidence(self.host_type)
        if raw is None:
            return ev
        text = raw if isinstance(raw, str) else str(raw)
        # 1) 错误先行：stderr/stdout 命中错误标记即视为运行期错误
        errors = [ln.strip() for ln in text.splitlines() if any(m in ln for m in self._ERROR_MARKERS)]
        ev["errors"] = len(errors)
        # 2) 帧数来自 GAME_AGENT_CONTRACT 行
        contract = self._parse_contract_line(text)
        if contract is None:
            return ev
        ev["available"] = True
        ev["frames"] = int(contract.get("frames", 0))
        ev["raw"] = contract
        return ev

    @staticmethod
    def _parse_contract_line(text: str) -> Optional[Dict[str, Any]]:
        for line in text.splitlines():
            if GodotContract.CONTRACT_PREFIX in line:
                payload = line.split(GodotContract.CONTRACT_PREFIX, 1)[1].strip()
                try:
                    return json.loads(payload)
                except ValueError:
                    return None
        return None


class MiniProgramContract(HostContract):
    """微信小游戏宿主契约（代码层）：把 Web DOM 假设映射到 wx.* 运行时。

    非 web 端不能假设 window/document/canvas/requestAnimationFrame/Audio 存在，
    必须改用 wx.createCanvas / wx.createImage / wx.onTouchStart / wx.createInnerAudioContext。
    本契约只做代码层协议定义与事件计数归一，真验证需微信开发者工具 / 真机（NEEDS_RUNTIME_TOOL）。
    """

    host_type = "miniprogram"
    # 微信运行时必须存在的 API（代码层静态自检用）
    REQUIRED_WX_APIS = (
        "wx.createCanvas", "wx.createImage", "wx.onTouchStart",
        "wx.createInnerAudioContext", "wx.getSystemInfoSync",
    )

    def report_frame(self) -> str:
        return "wx 小游戏以 wx.createCanvas 的 requestAnimationFrame 驱动主循环，每帧自增帧计数"

    def mark_state(self) -> str:
        return "状态迁移由游戏逻辑调用 wx 上报（代码层约定 markState() 上报 boot/playing/gameover）"

    def reflect_input(self) -> str:
        return "wx.onTouchStart/onTouchMove/onTouchEnd 真实触摸事件作为反射证据"

    @staticmethod
    def scan_wx_usage(js_text: str) -> Dict[str, bool]:
        """静态扫描某段 JS 是否真的调用了微信运行时 API（非运行期证据，仅结构自检）。"""
        present = {}
        for api in MiniProgramContract.REQUIRED_WX_APIS:
            member = api.split(".", 1)[1]  # createCanvas ...
            present[api] = bool(re.search(r"wx\s*\.\s*" + re.escape(member), js_text))
        return present

    def parse_evidence(self, raw: Any) -> Dict[str, Any]:
        ev = default_evidence(self.host_type)
        if raw is None:
            return ev
        data = raw if isinstance(raw, dict) else None
        if isinstance(raw, str):
            s = raw.strip()
            if s.startswith("{"):
                try:
                    data = json.loads(s)
                except ValueError:
                    data = None
        if not isinstance(data, dict):
            return ev
        ev["available"] = True
        ev["frames"] = data.get("frames") or data.get("frame") or 0
        ev["state"] = data.get("state")
        ev["input_events"] = data.get("touch_events") or 0
        ev["errors"] = data.get("error_count") or 0
        ev["raw"] = data
        return ev


class NativeContract(HostContract):
    """原生移动端（Android / iOS）通用契约骨架：设备日志归一化。

    真验证需 adb logcat / xcrun 设备日志，本机（Windows）对 iOS 不可达、对 Android 缺 SDK，
    因此 parse_evidence 只做结构归一，never 伪造可用证据。
    """

    host_type = "native"

    def report_frame(self) -> str:
        return "原生端由游戏引擎主循环经 logcat/os_log 上报帧计数（约定 tag: GAME_AGENT_FRAME）"

    def mark_state(self) -> str:
        return "状态迁移经设备日志上报（约定 tag: GAME_AGENT_STATE）"

    def reflect_input(self) -> str:
        return "触摸/手柄事件经设备日志上报（约定 tag: GAME_AGENT_INPUT）"

    def parse_evidence(self, raw: Any) -> Dict[str, Any]:
        ev = default_evidence(self.host_type)
        if raw is None:
            return ev
        data = raw if isinstance(raw, dict) else None
        if isinstance(raw, str):
            s = raw.strip()
            if s.startswith("{"):
                try:
                    data = json.loads(s)
                except ValueError:
                    data = None
        if not isinstance(data, dict):
            return ev
        ev["available"] = True
        ev["frames"] = data.get("frames") or 0
        ev["state"] = data.get("state")
        ev["input_events"] = data.get("input_events") or 0
        ev["errors"] = data.get("errors") or 0
        ev["raw"] = data
        return ev


# 契约注册表：适配器按 host_type 取用，避免散落 if/else
CONTRACTS: Dict[str, type] = {
    "browser": BrowserContract,
    "godot": GodotContract,
    "miniprogram": MiniProgramContract,
    "native": NativeContract,
}


def get_contract(host_type: str) -> HostContract:
    cls = CONTRACTS.get(host_type)
    if cls is None:
        raise KeyError(f"未知宿主契约类型: {host_type}（可选: {', '.join(CONTRACTS)}）")
    return cls()


__all__ = [
    "HostContract", "BrowserContract", "GodotContract", "MiniProgramContract", "NativeContract",
    "CONTRACTS", "get_contract", "default_evidence", "CONTRACT_NAME", "CONTRACT_MARKER",
    "empty_contract",
]
