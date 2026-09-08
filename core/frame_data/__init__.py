"""
Frame Data System — 格斗游戏帧数据系统
========================================
管理每个招式的启动帧/活跃帧/硬直帧，
提供取消链、输入缓冲和判定箱三层系统。

用法::
    from core.frame_data import FrameDataTable, CancelChain, InputBuffer

    table = FrameDataTable.from_yaml("data/frame_data.yaml")
    chain = CancelChain(table)
    buf   = InputBuffer(buffer_frames=6)
"""

from .frame_data_table import FrameDataTable, MoveData, MovePhase
from .cancel_chain import CancelChain, CancelWindow
from .input_buffer import InputBuffer, InputCommand
from .hitbox_manager import HitboxManager, Hitbox, HitboxType
from .frame_debugger import FrameDebugger

__all__ = [
    "FrameDataTable", "MoveData", "MovePhase",
    "CancelChain", "CancelWindow",
    "InputBuffer", "InputCommand",
    "HitboxManager", "Hitbox", "HitboxType",
    "FrameDebugger",
]
