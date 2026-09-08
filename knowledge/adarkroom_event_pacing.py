#!/usr/bin/env python3
"""
adarkroom_event_pacing.py: 吸收《A Dark Room》(小黑屋) 极简深邃神作心流架构大典
核心思想：
1. 渐进式功能展开 (Progressive Disclosure)：绝不一开始给全部功能，根据状态阈值逐步解锁 (生火 ➔ 建造 ➔ 招募 ➔ 大地图罗盘 ➔ 星舰跃迁)
2. 事件驱动池 (Event-Driven State Pool)：随机游商、野兽突袭、流浪工匠与资源消耗严密闭环
"""
from typing import Dict, List, Any

class ADarkRoomPacingKnowledge:
    """A Dark Room 渐进式心流与事件状态机规范"""

    # 1. 六阶段渐进式心流状态树
    PACING_STAGES = [
        {
            "stage_id": 1,
            "name": "微光与冷意 (The Fire is Dead)",
            "unlock_condition": "游戏开始",
            "active_buttons": ["light_fire", "stoke_fire"],
            "core_tension": "在严寒黑暗中维持微光，建立对温暖的本能渴望"
        },
        {
            "stage_id": 2,
            "name": "陌生人来访 (A Silent Stranger)",
            "unlock_condition": "火堆温度达到「温暖」且持续 30 秒",
            "active_buttons": ["check_traps", "build_cart"],
            "core_tension": "引入工匠建造，木材经济开始流转"
        },
        {
            "stage_id": 3,
            "name": "村落与猎人 (The Quiet Village)",
            "unlock_condition": "木材累计达到 100",
            "active_buttons": ["gather_wood", "assign_gatherers", "assign_trappers"],
            "core_tension": "肉、毛皮、牙齿资源闭环，人口自动化生产"
        },
        {
            "stage_id": 4,
            "name": "尘土之路大地图 (A Dusty Path)",
            "unlock_condition": "制造出罗盘与皮水壶",
            "active_buttons": ["embark_map", "explore_ruins"],
            "core_tension": "玩法突变为末日大地图 Roguelike 探索与水源补给管理"
        },
        {
            "stage_id": 5,
            "name": "废土星舰飞升 (An Old Starship)",
            "unlock_condition": "在大地图探索中寻获坠毁飞船并修复引擎",
            "active_buttons": ["launch_ship", "hyperdrive_evac"],
            "core_tension": "最终跃迁逃逸，叙事终局闭环"
        }
    ]

    # 2. 状态机事件驱动模板
    EVENT_DISPATCH_SCHEMA = """
    class EventBus {
      constructor() { this.listeners = {}; }
      on(event, cb) { (this.listeners[event] = this.listeners[event] || []).push(cb); }
      emit(event, data) { (this.listeners[event] || []).forEach(cb => cb(data)); }
    }
    """
