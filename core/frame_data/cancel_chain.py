"""
Cancel Chain — 取消链系统
===========================
管理格斗游戏中的招式取消优先级：
  普攻 → 特殊技 → 必杀技（单向取消）

规则：
  - 只能从低级别取消到高级别
  - 只能在命中或特定帧窗口内取消
  - 同一级别不能互相取消（防止无限连段）
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from .frame_data_table import FrameDataTable, MoveData, MovePhase


# 取消优先级等级（数字越大越高级）
CANCEL_PRIORITY = {
    "normal":     1,
    "special":    2,
    "super":      3,
    "projectile": 2,  # 投射物与特殊技同级
}


@dataclass
class CancelWindow:
    """当前帧可取消的信息。"""
    can_cancel: bool
    current_move: str
    cancel_targets: list[str]   # 可取消到的招式类别
    reason: str = ""            # 不能取消时的原因说明


class CancelChain:
    """
    取消链管理器：判断当前帧是否可以取消到指定招式。

    用法::
        chain = CancelChain(table)

        # 当前在执行 light_punch 的第 5 帧（活跃帧）
        window = chain.check_cancel(
            current_move="light_punch",
            current_frame=5,
            next_move="hadouken",
            on_hit=True,
        )
        if window.can_cancel:
            execute_move("hadouken")
    """

    def __init__(self, table: FrameDataTable):
        self.table = table
        # 取消类型白名单：{来源类型: [目标类型]}
        self._cancel_rules = {
            "normal":     ["special", "super"],
            "special":    ["super"],
            "super":      [],
            "projectile": ["super"],
        }

    def check_cancel(
        self,
        current_move: str,
        current_frame: int,
        next_move: str,
        on_hit: bool = False,
        on_block: bool = False,
    ) -> CancelWindow:
        """
        检查是否可以从 current_move 取消到 next_move。

        Args:
            current_move:  当前执行中的招式名
            current_frame: 当前执行到的帧数
            next_move:     想要取消到的目标招式名
            on_hit:        是否命中了对手
            on_block:      是否被对手格挡

        Returns:
            CancelWindow 包含是否可取消及原因
        """
        current = self.table.get(current_move)
        target  = self.table.get(next_move)

        if current is None:
            return CancelWindow(False, current_move, [], "当前招式不存在")
        if target is None:
            return CancelWindow(False, current_move, [], "目标招式不存在")

        # 1. 检查帧窗口：必须在活跃帧或命中后的硬直前段
        phase = current.phase_at(current_frame)
        if phase == MovePhase.IDLE:
            return CancelWindow(False, current_move, [], "招式已结束，无法取消")
        if phase == MovePhase.STARTUP:
            return CancelWindow(False, current_move, [], "招式启动中，无法取消")

        # 活跃帧内必须命中或格挡才能取消（防止空挥取消）
        if phase == MovePhase.ACTIVE and not (on_hit or on_block):
            return CancelWindow(False, current_move, current.cancel_into,
                                "活跃帧内须命中/格挡后才能取消")

        # 2. 检查取消权限
        current_priority = CANCEL_PRIORITY.get(current.move_type, 0)
        target_priority  = CANCEL_PRIORITY.get(target.move_type, 0)

        if target_priority <= current_priority:
            return CancelWindow(False, current_move, current.cancel_into,
                                f"不能从 {current.move_type} 取消到 {target.move_type}")

        allowed_targets = self._cancel_rules.get(current.move_type, [])
        if target.move_type not in allowed_targets:
            return CancelWindow(False, current_move, current.cancel_into,
                                f"{current.move_type} 不允许取消到 {target.move_type}")

        # 检查招式自定义的取消列表
        if current.cancel_into and target.move_type not in current.cancel_into:
            return CancelWindow(False, current_move, current.cancel_into,
                                f"{current_move} 不允许取消到 {target.move_type} 类型")

        return CancelWindow(True, current_move, current.cancel_into,
                            f"可以从 {current_move} 取消到 {next_move}")

    def get_cancel_targets(self, move_name: str) -> list[str]:
        """返回该招式可取消到的所有招式名称列表。"""
        move = self.table.get(move_name)
        if move is None:
            return []
        allowed_types = self._cancel_rules.get(move.move_type, [])
        return [name for name, m in self.table._moves.items()
                if m.move_type in allowed_types and name != move_name]
