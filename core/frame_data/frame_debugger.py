"""
Frame Debugger — 帧数据可视化调试器
======================================
在终端输出当前招式的帧进度条和判定箱状态。
"""

from __future__ import annotations
from .frame_data_table import FrameDataTable, MoveData, MovePhase
from .hitbox_manager import HitboxManager, HitboxType


_C_RED    = "\033[91m"
_C_GREEN  = "\033[92m"
_C_YELLOW = "\033[93m"
_C_BLUE   = "\033[94m"
_C_RESET  = "\033[0m"
_C_BOLD   = "\033[1m"


class FrameDebugger:
    """帧数据调试器：进度条 + 判定箱状态输出。"""

    def __init__(self, table: FrameDataTable, use_color: bool = True):
        self.table = table
        self.use_color = use_color

    def print_frame_bar(self, move_name: str, current_frame: int):
        """
        打印招式帧进度条。

        示例输出::
            [light_punch] 启动:4 活跃:2 硬直:8 | 第5帧 [ACTIVE]
            SSSSAAARRRRRRRR
                ^
        """
        move = self.table.get(move_name)
        if move is None:
            print(f"[FrameDebugger] 招式不存在: {move_name}")
            return

        bar = self._build_bar(move, current_frame)
        phase = move.phase_at(current_frame)
        phase_str = self._colorize(f"[{phase.value.upper()}]", phase)

        print(f"\n{_C_BOLD}[{move_name}]{_C_RESET} "
              f"启动:{move.startup} 活跃:{move.active} 硬直:{move.recovery} | "
              f"第{current_frame+1}帧 {phase_str}")
        print(bar)
        pointer = " " * min(current_frame, move.total_frames - 1) + "^"
        print(pointer)

    def print_hitbox_summary(self, hm: HitboxManager, char_id: str):
        """打印角色当前判定箱摘要。"""
        print(f"\n[{char_id}] 判定箱:")
        for htype in HitboxType:
            boxes = hm.boxes_for(char_id, htype)
            if not boxes:
                continue
            color = {
                HitboxType.HITBOX:  _C_RED,
                HitboxType.HURTBOX: _C_GREEN,
                HitboxType.PUSHBOX: _C_BLUE,
            }[htype]
            label = f"{color}{htype.value.upper()}{_C_RESET}" if self.use_color else htype.value.upper()
            for b in boxes:
                print(f"  {label}: x={b.x:+.2f} y={b.y:+.2f} "
                      f"w={b.w:.2f} h={b.h:.2f} active={b.active}")

    def print_all_moves(self):
        """打印所有招式帧数据表格。"""
        self.table.print_summary()

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _build_bar(self, move: MoveData, current_frame: int) -> str:
        bar = ""
        for i in range(move.total_frames):
            phase = move.phase_at(i)
            if phase == MovePhase.STARTUP:
                ch = self._colorize("S", MovePhase.STARTUP)
            elif phase == MovePhase.ACTIVE:
                ch = self._colorize("A", MovePhase.ACTIVE)
            else:
                ch = self._colorize("R", MovePhase.RECOVERY)
            bar += ch
        return bar

    def _colorize(self, text: str, phase) -> str:
        if not self.use_color:
            return text
        color = {
            MovePhase.STARTUP:  _C_YELLOW,
            MovePhase.ACTIVE:   _C_RED,
            MovePhase.RECOVERY: _C_GREEN,
            MovePhase.IDLE:     _C_RESET,
        }.get(phase, _C_RESET)
        return f"{color}{text}{_C_RESET}"
