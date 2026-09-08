#!/usr/bin/env python3
"""
probe_contract.py: 游戏运行时无头探针与按键驱动标准契约规范 (CLI Probe & Drive Protocol Specification)
纯 Python 3.9+ 标准库实现，零外部依赖。

定义全引擎适用的统一探针协议：
1. --probe: 游戏向 stdout 输出标准化 JSON 运行时状态快照 (含 tick, player, logistics, entities, metrics)
2. --drive="<script>": 逐帧或按时间戳注入按键序列 (如 tick:action:arg)
3. --pose="<x,y>": 瞬移实体至指定世界坐标
4. --scenario="<id>": 拉起内置基准测试沙盒
5. --screenshot="<path>": 渲染指定帧后保存实机截图并安全退出
"""
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional

@dataclass
class ProbePlayerState:
    x: float
    y: float
    vx: float
    vy: float
    on_ground: bool
    state: str
    inventory: Dict[str, int]

@dataclass
class ProbeMetricsState:
    fps: float
    frame_time_ms: float
    draw_calls: int
    active_entities: int
    memory_mb: float

@dataclass
class ProbeSnapshot:
    tick: int
    time_seconds: float
    state: str
    player: Optional[ProbePlayerState]
    logistics: Dict[str, Any]
    combat: Dict[str, Any]
    metrics: ProbeMetricsState

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "ProbeSnapshot":
        data = json.loads(text)
        player_data = data.get("player")
        player = ProbePlayerState(**player_data) if player_data else None
        metrics_data = data.get("metrics", {})
        metrics = ProbeMetricsState(**metrics_data) if metrics_data else ProbeMetricsState(
            fps=60.0, frame_time_ms=16.6, draw_calls=1, active_entities=0, memory_mb=0.0
        )
        return cls(
            tick=data.get("tick", 0),
            time_seconds=data.get("time_seconds", 0.0),
            state=data.get("state", "RUNNING"),
            player=player,
            logistics=data.get("logistics", {}),
            combat=data.get("combat", {}),
            metrics=metrics
        )

class ProbeScriptParser:
    """解析 --drive 脚本，格式如:
    0:press:right; 30:release:right; 31:press:jump; 45:release:jump
    """
    @staticmethod
    def parse_drive_script(script_str: str) -> List[Dict[str, Any]]:
        actions = []
        chunks = [c.strip() for c in script_str.split(";") if c.strip()]
        for c in chunks:
            parts = [p.strip() for p in c.split(":")]
            if len(parts) >= 2:
                tick = int(parts[0])
                cmd = parts[1]
                arg = parts[2] if len(parts) > 2 else ""
                actions.append({"tick": tick, "command": cmd, "arg": arg})
        return sorted(actions, key=lambda x: x["tick"])

    @staticmethod
    def serialize_actions(actions: List[Dict[str, Any]]) -> str:
        return "; ".join(f"{a['tick']}:{a['command']}:{a.get('arg', '')}".rstrip(":") for a in actions)
