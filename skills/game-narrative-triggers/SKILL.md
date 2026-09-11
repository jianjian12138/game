---
name: game-narrative-triggers
description: |
  空间叙事与事件图谱触发器（Spatial Narrative & Event Graph）工程规范。
  专治解谜条件网状依赖死锁、剧情触发器穿模漏发、NPC对白状态与任务进度脱节等问题。
  涵盖圆形/矩形/多边形触发区（TriggerZone）、事件前置依赖DAG图（EventGraph）、
  分支对话机（DialogueEngine）及序列化剧情持久化状态（StoryState）。
---

# 空间叙事与事件图谱触发器工程规范

## 1. 核心架构

- **TriggerZone (`core/narrative/trigger_zone.py`)**：
  提供圆形、AABB矩形与多边形触发区，管理进入/离开事件与一次性/可重复激活。
- **EventGraph (`core/narrative/event_graph.py`)**：
  DAG有向无环图驱动，依赖所有前置事件完成后自动触发下游事件链。
- **DialogueEngine (`core/narrative/dialogue_engine.py`)**：
  状态机分支对话节点，支持变量插值 `{player_name}`、条件选择支与事件回调。
- **StoryState (`core/narrative/story_state.py`)**：
  全局剧情标志位、任务字典、好感度与事件历史的统一序列化存储。

## 2. 范例用法

```python
from core.narrative import DialogueEngine, StoryState, TriggerZone, EventGraph

state = StoryState()
state.set_flag("has_key", True)

engine = DialogueEngine()
# 执行分支对话，根据 state 进行选项解锁
```
