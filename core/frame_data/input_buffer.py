"""
Input Buffer — 格斗游戏输入缓冲系统
======================================
在 N 帧内缓存玩家输入，容错提前按键并识别指令序列（如 ↓↘→P）。

格斗游戏玩家平均提前 3–6 帧按下按键，
不做缓冲会导致"明明按了但没出招"的挫败感。

支持的指令格式：
  数字小键盘记法：5=中立，6=前，4=后，8=上，2=下
  组合：236=↓↘→（波动拳），623=→↓↘（升龙拳），214=↓↙←
"""

from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Direction(Enum):
    NEUTRAL    = 5
    FORWARD    = 6
    BACK       = 4
    UP         = 8
    DOWN       = 2
    UP_FORWARD = 9
    UP_BACK    = 7
    DOWN_FORWARD = 3
    DOWN_BACK  = 1


@dataclass
class InputCommand:
    """一个已识别的指令。"""
    name: str               # 指令名称（如 "hadouken", "shoryuken"）
    button: str             # 触发按键（"P"=拳，"K"=腿，"S"=斩）
    timestamp: float        # 识别时间戳
    move_id: str = ""       # 对应的招式 ID


class InputBuffer:
    """
    输入缓冲器：存储最近 N 帧的输入，识别指令序列。

    用法::
        buf = InputBuffer(buffer_frames=6)

        # 每帧调用：推入当前输入
        buf.push(direction=Direction.DOWN, buttons=set())
        buf.push(direction=Direction.DOWN_FORWARD, buttons=set())
        buf.push(direction=Direction.FORWARD, buttons={"P"})

        # 检查是否有已识别指令
        cmd = buf.consume_command("hadouken")
        if cmd:
            execute_hadouken()
    """

    # 内置指令定义：{名称: (方向序列, 触发按键)}
    BUILTIN_MOTIONS = {
        "hadouken":   ([2, 3, 6], "P"),      # ↓↘→P
        "shoryuken":  ([6, 2, 3], "P"),      # →↓↘P
        "tatsumaki":  ([2, 1, 4], "K"),      # ↓↙←K
        "super":      ([2, 3, 6, 2, 3], "P"),# ↓↘→↓↘→P
        "dp_kick":    ([6, 2, 3], "K"),      # →↓↘K
        "charge_back_forward": (None, "P"),   # ←チャージ→P (特殊处理)
    }

    def __init__(self, buffer_frames: int = 6):
        self.buffer_frames = buffer_frames
        self._dir_history: deque = deque(maxlen=20)   # 方向历史
        self._btn_history: deque = deque(maxlen=20)   # 按键历史
        self._pending_commands: list[InputCommand] = []
        self._custom_motions: dict = {}
        self._frame_count = 0

    def push(self, direction: Direction, buttons: set[str]):
        """
        推入当前帧的输入状态。每帧调用一次。

        Args:
            direction: 当前方向
            buttons:   当前按下的按键集合（"P"/"K"/"S"/"HS"）
        """
        self._dir_history.append(direction.value)
        self._btn_history.append((set(buttons), self._frame_count))
        self._frame_count += 1
        self._detect_commands()

    def consume_command(self, command_name: str) -> Optional[InputCommand]:
        """
        消耗（取出）一个已识别的指令。
        如果指令存在则返回并从队列中移除，否则返回 None。
        """
        for i, cmd in enumerate(self._pending_commands):
            if cmd.name == command_name:
                # 检查是否还在缓冲窗口内
                if self._frame_count - (cmd.timestamp) <= self.buffer_frames:
                    self._pending_commands.pop(i)
                    return cmd
        return None

    def has_pending(self, command_name: str) -> bool:
        """检查是否有待执行的指令（不消耗）。"""
        return any(c.name == command_name for c in self._pending_commands)

    def register_motion(self, name: str, directions: list[int], button: str):
        """注册自定义指令。"""
        self._custom_motions[name] = (directions, button)

    def flush(self):
        """清空所有缓冲（角色被击飞/眩晕时调用）。"""
        self._dir_history.clear()
        self._btn_history.clear()
        self._pending_commands.clear()

    # ------------------------------------------------------------------
    # 内部指令识别
    # ------------------------------------------------------------------

    def _detect_commands(self):
        """检测历史输入中是否完成了已知指令。"""
        all_motions = {**self.BUILTIN_MOTIONS, **self._custom_motions}

        for cmd_name, (motion, btn) in all_motions.items():
            if motion is None:
                continue
            button_pressed = self._last_button_pressed(btn)
            if button_pressed and self._match_motion(motion):
                cmd = InputCommand(
                    name=cmd_name,
                    button=btn,
                    timestamp=self._frame_count,
                )
                # 避免重复添加
                if not self.has_pending(cmd_name):
                    self._pending_commands.append(cmd)

        # 清理过期指令
        self._pending_commands = [
            c for c in self._pending_commands
            if self._frame_count - c.timestamp <= self.buffer_frames * 3
        ]

    def _match_motion(self, motion: list[int]) -> bool:
        """在最近历史中匹配方向序列（允许中间帧的冗余输入）。"""
        history = list(self._dir_history)
        if len(history) < len(motion):
            return False

        # 在最近 16 帧内查找序列（从后往前匹配）
        search_window = history[-16:]
        j = len(motion) - 1
        for i in range(len(search_window) - 1, -1, -1):
            if search_window[i] == motion[j]:
                j -= 1
                if j < 0:
                    return True
        return False

    def _last_button_pressed(self, button: str) -> bool:
        """检查最近 N 帧内是否按下了指定按键。"""
        for buttons, frame in reversed(list(self._btn_history)):
            if self._frame_count - frame > self.buffer_frames:
                break
            if button in buttons:
                return True
        return False
