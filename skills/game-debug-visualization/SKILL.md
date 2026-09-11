---
name: game-debug-visualization
description: |
  多维调试可视化与运行期监控（Debug Visualization Layer）工程规范。
  专治黑盒逻辑无法定位、判定框穿模不知受身还是攻击帧重叠、行为树死循环卡死、
  音画同步延迟毫秒无从测量、Monte Carlo批量平衡无直观报表等调试痛点。
  涵盖判定箱叠加（HitboxOverlay）、行为树状态监视器（BTStateMonitor）、
  存档状态检查器（SaveStateInspector）、DSL轨迹记录器（DSLTraceViewer）与音画同步仪表盘（AudioSyncMeter）。
---

# 多维调试可视化与运行期监控工程规范

## 1. 核心套件矩阵

- **HitboxOverlay (`core/debug_visualizer/hitbox_overlay.py`)**：
  三层判定箱（HITBOX, HURTBOX, PUSHBOX）字符网格叠加与重叠穿透检测。
- **BTStateMonitor (`core/debug_visualizer/bt_state_monitor.py`)**：
  递归树形遍历行为树当前节点状态（`[SUCCESS]`, `[FAILURE]`, `[RUNNING]`），实时呈现决策流。
- **SaveStateInspector (`core/debug_visualizer/save_state_inspector.py`)**：
  存档槽位元数据检验、SHA-256防篡改指纹展示及差异补丁可视化。
- **DSLTraceViewer (`core/debug_visualizer/dsl_trace_viewer.py`)**：
  按步展示DSL技能/卡牌效果事件触发链。
- **AudioSyncMeter (`core/debug_visualizer/audio_sync_meter.py`)**：
  音画单调时钟偏差毫秒游标仪表盘，校准音游与打击判定窗口。
