#!/usr/bin/env python3
"""
qa_and_antiglitch.py: 工业级 QA 质量防护、反穿模与防卡死算法知识库
为测试总监与质量部提供 CCD 连续碰撞检测、固定物理步长循环与对象池泄漏探针。
"""
from typing import Dict, List, Tuple, Any

class QAAndAntiGlitchKnowledge:

    # 1. CCD 连续碰撞检测算法 (Continuous Collision Detection - 杜绝高速子弹穿墙)
    @staticmethod
    def check_ray_segment_intersection(p1: Tuple[float, float], p2: Tuple[float, float],
                                        wall_p1: Tuple[float, float], wall_p2: Tuple[float, float]) -> bool:
        """检测高速移动物体上一帧位置 p1 到当前帧位置 p2 的线段，是否与障碍物线段发生交叉穿透"""
        def ccw(a, b, c):
            return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

        return (ccw(p1, wall_p1, wall_p2) != ccw(p2, wall_p1, wall_p2)) and \
               (ccw(p1, p2, wall_p1) != ccw(p1, p2, wall_p2))

    # 2. 物理固定步长循环守卫 (Fixed Timestep Physics Guard)
    FIXED_DELTA_SEC = 1.0 / 60.0 # 0.0166667s

    @staticmethod
    def simulate_fixed_physics_loop(accumulator: float, delta_time: float, max_sub_steps: int = 5) -> Tuple[float, int]:
        """防止低帧率设备上物理爆炸 (Spiral of Death) 的累加器算法
        返回: (剩余累加器时间, 本次应执行的物理步数)
        """
        # 限制单帧最大时间，防止长时间卡顿后瞬间爆发成千上万次物理计算
        clamped_delta = min(delta_time, 0.25)
        accumulator += clamped_delta

        sub_steps = 0
        while accumulator >= QAAndAntiGlitchKnowledge.FIXED_DELTA_SEC and sub_steps < max_sub_steps:
            accumulator -= QAAndAntiGlitchKnowledge.FIXED_DELTA_SEC
            sub_steps += 1

        return accumulator, sub_steps

    # 3. 对象池卫生与状态彻底 Reset 规范
    @staticmethod
    def sanitize_recycled_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
        """将从对象池拿出的实体进行全量初始化擦除，防止上一次被杀死的残留状态污染新实体"""
        entity["is_active"] = True
        entity["velocity_x"] = 0.0
        entity["velocity_y"] = 0.0
        entity["hp"] = entity.get("max_hp", 100)
        entity["active_buffs"] = []
        entity["lifetime_ticks"] = 0
        return entity
