---
name: game-analytics-loop
description: |
  玩家数据闭环与运营决策（Game Analytics & Data Loop）工程规范。
  专治上线后两眼一抹黑、新手关卡卡死流失严重、次留不达标不知从何调优、
  死亡热点无从定位等运营痛点。涵盖埋点跟踪（EventTracker）、漏斗分析（FunnelAnalyzer）、
  空间死亡热图（HeatmapGenerator）、用户留存群组（CohortAnalyzer）与自动化运营日报。
---

# 玩家数据闭环与运营决策工程规范

## 1. 核心管线

- **EventTracker (`pipeline/player_analytics/event_tracker.py`)**：
  统一埋点SDK，规范标准事件命名 (`session_start`, `level_complete`, `player_death` 等)，支持批量与异步冲刷。
- **FunnelAnalyzer (`pipeline/player_analytics/funnel_analyzer.py`)**：
  新手引导与关卡漏斗，自动计算单步流失率与最大流失瓶颈。
- **HeatmapGenerator (`pipeline/player_analytics/heatmap_generator.py`)**：
  空间坐标聚类与归一化热度矩阵，支持终端 ASCII 字符画可视化输出。
- **CohortAnalyzer (`pipeline/player_analytics/cohort_analyzer.py`)**：
  按注册日期划分子群组，精准追踪 D1/D3/D7/D14/D30 留存衰减率。
- **InsightReporter (`pipeline/player_analytics/insight_reporter.py`)**：
  将多维指标自动组装为 Markdown 格式的运维调优报告。
