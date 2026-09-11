---
name: game-networking
description: |
  多人联机网络层架构（Networking Layer）工程规范。
  专治客户端不同步掉线、状态不同步（Desync）、权威服务器卡顿延迟、高延迟射击空刀等联机痛点。
  涵盖确定性帧同步（LockstepSync）、权威状态同步与预测回滚（StateSync）、
  多人房间/排队撮合（RoomManager）、输入流对局录像回放（ReplayRecorder）及延迟补偿插值（LagCompensator）。
---

# 多人联机网络层架构工程规范

## 1. 核心架构与同步模型

| 同步模型 | 适用品类 | 关键类 | 原理与核心优势 |
|:---|:---|:---|:---|
| **帧同步 (Lockstep)** | RTS、格斗、MOBA、弹幕射击 | `LockstepSync` | 只广播玩家极简输入指令，各端全确定性演算，节省带宽，带状态指纹校验防不同步 |
| **状态同步 (State Sync)** | MMORPG、大逃杀、经营网游 | `StateSync` | 服务端全权威校验，差分快照压缩（Delta Compression），客户端预测+服务器纠偏 |
| **房间与撮合 (Lobby/Rooms)**| 全类型多人联机 | `RoomManager` | 房主权限、座位映射、全员就绪检测与自动化队列撮合 |
| **对局回放 (Replay)** | 竞速幽灵车、排位赛复盘、防作弊仲裁 | `ReplayRecorder`| 初始随机种子 + 逐Tick输入流序列化，极低存储占用 |
| **延迟补偿 (Lag Compensation)**| FPS、动作格斗、赛车对决 | `LagCompensator`| 渲染插值缓冲区消除微抖动，服务端时间回退（Rewind）实现公平命中判定 |

## 2. 帧同步代码范例

```python
from core.networking import LockstepSync, PlayerInput

sync = LockstepSync(expected_players=["p1", "p2"], tick_rate_hz=30)
sync.submit_input(PlayerInput("p1", tick=0, commands={"move": "UP"}))
sync.submit_input(PlayerInput("p2", tick=0, commands={"move": "LEFT"}))

if sync.is_tick_ready(0):
    inputs = sync.advance_tick(state_dict={"p1_pos": (0, 1), "p2_pos": (-1, 0)})
    print(sync.state_checksums[0])
```
