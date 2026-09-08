#!/usr/bin/env python3
"""
open_source_masters_encyclopedia.py: 世界级开源经典神作架构与算法总库
沉淀 6 大世界级巅峰开源游戏的底层工业逻辑：
1. 《Warzone 2100》: 模块化载具拼装 (底盘/推进/炮塔) 与曲射火炮雷达弹道
2. 《OpenRCT2》: 等轴测 2.5D 坐标转换与微观游客 6 维个体心智模型
3. 《OpenTTD》: 铁路 Block/Path 信号机网络与工业链供需有向图
4. 《OpenArena》: Quake 3 原生向量物理 (Strafe Jumping & Rocket Jump)
5. 《SuperTuxKart》: 漂移蓄力动力学、四轮悬挂阻力与航点 Rubberbanding
6. 《Battle for Wesnoth》: 轴向六角格 (Axial Hex)、ZOC 控制区与昼夜伤害加成矩阵
"""
import math
from typing import Dict, List, Tuple, Any

class OpenSourceMastersEncyclopedia:
    """世界级开源经典神作架构与算法总库"""

    # =================================================================
    # 1. 《Warzone 2100》: 模块化车体拼装与火炮雷达算法
    # =================================================================
    class Warzone2100:
        CHASSIS_SPECS = {
            "viper": {"name": "猎豹轻型底盘", "weight": 120, "hp": 150, "slots": 1},
            "cobra": {"name": "眼镜蛇中型底盘", "weight": 280, "hp": 380, "slots": 1},
            "python": {"name": "巨蟒重型底盘", "weight": 550, "hp": 850, "slots": 2}
        }
        PROPULSION_SPECS = {
            "wheels": {"name": "六轮轮式", "speed": 6.5, "road_bonus": 1.4, "offroad_penalty": 0.7},
            "half_tracks": {"name": "半履带式", "speed": 4.8, "road_bonus": 1.1, "offroad_penalty": 0.95},
            "hover": {"name": "气垫悬浮", "speed": 5.5, "water_capable": True, "offroad_penalty": 1.0}
        }
        TURRET_SPECS = {
            "heavy_cannon": {"name": "重型穿甲加农炮", "dmg": 180, "reload_sec": 3.2, "range": 350, "type": "kinetic"},
            "inferno_mortar": {"name": "地狱曲射迫击炮", "dmg": 260, "reload_sec": 5.5, "range": 750, "type": "artillery"},
            "radar_sensor": {"name": "超视距火控雷达", "dmg": 0, "reload_sec": 0.0, "range": 1200, "type": "sensor"}
        }

        @classmethod
        def assemble_vehicle(cls, chassis_id: str, propulsion_id: str, turret_id: str) -> Dict[str, Any]:
            """Warzone 2100 模块化拼装核心算法"""
            c = cls.CHASSIS_SPECS[chassis_id]
            p = cls.PROPULSION_SPECS[propulsion_id]
            t = cls.TURRET_SPECS[turret_id]
            total_hp = c["hp"] + (50 if "heavy" in turret_id else 20)
            total_weight = c["weight"] + 80
            final_speed = p["speed"] * (300.0 / total_weight)
            return {
                "unit_name": f"{c['name']}-{p['name']}-{t['name']}",
                "total_hp": total_hp,
                "top_speed": round(final_speed, 2),
                "weapon": t,
                "propulsion": p
            }

    # =================================================================
    # 2. 《OpenRCT2》: 等轴测 2.5D 空间与微观游客 6 维个体心智状态机
    # =================================================================
    class OpenRCT2:
        @staticmethod
        def world_to_isometric(x: float, y: float, z: float) -> Tuple[float, float]:
            """等轴测 2.5D 投影算法"""
            iso_x = (x - y) * math.cos(math.radians(30))
            iso_y = (x + y) * math.sin(math.radians(30)) - z
            return (round(iso_x, 2), round(iso_y, 2))

        @staticmethod
        def update_guest_mindset(guest: Dict[str, float], delta_sec: float) -> Dict[str, float]:
            """微观游客个体 6 维需求仿真状态机 (过山车大亨核心心流)"""
            guest["hunger"] = min(100.0, guest.get("hunger", 0) + 0.35 * delta_sec)
            guest["thirst"] = min(100.0, guest.get("thirst", 0) + 0.55 * delta_sec)
            guest["energy"] = max(0.0, guest.get("energy", 100) - 0.20 * delta_sec)
            guest["nausea"] = max(0.0, guest.get("nausea", 0) - 0.40 * delta_sec) # 恶心晕眩消退

            # 综合满意度加权公式
            dissatisfaction = (guest["hunger"] * 0.3 + guest["thirst"] * 0.4 + guest["nausea"] * 0.8)
            guest["happiness"] = max(0.0, min(100.0, 100.0 - dissatisfaction))
            return guest

    # =================================================================
    # 3. 《OpenTTD》: 铁路信号机网络与产业链供需拓扑
    # =================================================================
    class OpenTTD:
        INDUSTRY_GRAPH = {
            "CoalMine": {"produces": "Coal", "requires": None, "rate_per_month": 120},
            "PowerStation": {"produces": "Electricity", "requires": "Coal", "conversion_ratio": 1.0},
            "IronOreMine": {"produces": "IronOre", "requires": None, "rate_per_month": 90},
            "SteelMill": {"produces": "Steel", "requires": "IronOre", "conversion_ratio": 0.8},
            "Factory": {"produces": "Goods", "requires": "Steel", "conversion_ratio": 1.2}
        }

        @staticmethod
        def evaluate_path_signal(train_route: List[int], occupied_blocks: List[int]) -> bool:
            """OpenTTD 经典路径信号机 (Path Signal) 避障判定"""
            for block in train_route:
                if block in occupied_blocks:
                    return False # 闭塞区间被占用，亮红灯停车
            return True # 路径完全畅通，亮绿灯放行

    # =================================================================
    # 4. 《OpenArena》: Quake 3 扫射跳与火箭跳向量物理模型
    # =================================================================
    class OpenArena:
        @staticmethod
        def quake3_accelerate(vel: Tuple[float, float, float], wish_dir: Tuple[float, float, float],
                              wish_speed: float, accel: float, delta_time: float) -> Tuple[float, float, float]:
            """Quake 3 原生 strafe acceleration 扫射跳加速度矢量物理模型"""
            current_speed = vel[0] * wish_dir[0] + vel[1] * wish_dir[1] + vel[2] * wish_dir[2]
            add_speed = wish_speed - current_speed
            if add_speed <= 0:
                return vel
            accel_speed = min(add_speed, accel * delta_time * wish_speed)
            return (
                vel[0] + accel_speed * wish_dir[0],
                vel[1] + accel_speed * wish_dir[1],
                vel[2] + accel_speed * wish_dir[2]
            )

    # =================================================================
    # 5. 《SuperTuxKart》: 漂移阻力动力学与航点 Rubberbanding
    # =================================================================
    class SuperTuxKart:
        @staticmethod
        def compute_drift_boost(drift_duration_sec: float, drift_angle_deg: float) -> Dict[str, Any]:
            """超级企鹅卡丁车漂移蓄力与火花释放动力学"""
            if drift_duration_sec < 0.6 or abs(drift_angle_deg) < 25.0:
                return {"boost_level": 0, "impulse": 0.0, "spark_color": None}
            elif drift_duration_sec < 1.4:
                return {"boost_level": 1, "impulse": 4.5, "spark_color": "#ffaa00"} # 黄火花
            elif drift_duration_sec < 2.5:
                return {"boost_level": 2, "impulse": 8.0, "spark_color": "#00eeff"} # 蓝火花
            else:
                return {"boost_level": 3, "impulse": 13.5, "spark_color": "#ff00ff"} # 紫火花极限冲刺

    # =================================================================
    # 6. 《Battle for Wesnoth》: 六角格 ZOC 与昼夜阵营伤害加成矩阵
    # =================================================================
    class BattleForWesnoth:
        # 六角格 6 方向邻居单位向量 (Axial Coordinates)
        HEX_DIRECTIONS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]

        # 昼夜节拍与阵营伤害修正矩阵 (Lawful 守序, Chaotic 混乱, Neutral 中立)
        TIME_OF_DAY_MODIFIERS = {
            "Dawn": {"Lawful": 0.0, "Chaotic": 0.0, "Neutral": 0.0},
            "Morning": {"Lawful": 0.25, "Chaotic": -0.25, "Neutral": 0.0},
            "Afternoon": {"Lawful": 0.25, "Chaotic": -0.25, "Neutral": 0.0},
            "Dusk": {"Lawful": 0.0, "Chaotic": 0.0, "Neutral": 0.0},
            "FirstWatch": {"Lawful": -0.25, "Chaotic": 0.25, "Neutral": 0.0},
            "SecondWatch": {"Lawful": -0.25, "Chaotic": 0.25, "Neutral": 0.0},
        }

        @classmethod
        def calculate_zoc_block(cls, unit_q: int, unit_r: int, target_q: int, target_r: int) -> bool:
            """韦诺之战 ZOC (Zone of Control) 控制区截停阻断判定"""
            dq = target_q - unit_q
            dr = target_r - unit_r
            return (dq, dr) in cls.HEX_DIRECTIONS
