---
name: game-save-system
description: |
  游戏存档系统黄金法则。专治：游戏无法保存进度、存档损坏无法恢复、
  版本更新存档不兼容、跨设备无法同步等问题。
  涵盖序列化/反序列化、增量diff存档、版本迁移、微信云同步和三套模板
  （Meta进度/世界状态/Roguelike单局）。
  当任何游戏需要持久化状态时必须遵循。
---

# 游戏存档系统黄金法则

## 🔥 核心原则：存档是生命线，不是可选功能

> **黄金律**：玩家不能接受进度丢失。存档系统必须在第一天就设计好，
> 不能是"上线前再加"——那时已来不及做好版本迁移。

```
❌ 错误做法：
import json
json.dump(game_state, open("save.json", "w"))  # 无校验、无版本、无迁移

✅ 正确做法：
from core.save_system import SaveSerializer
SaveSerializer.save(state, slot=1)  # 自动添加校验和、版本号
state = SaveSerializer.load(slot=1) # 自动版本迁移 + 完整性校验
```

---

## 📦 模块位置

```
core/save_system/
├── __init__.py            ← 公开API + SAVE_FORMAT_VERSION
├── save_serializer.py     ← 主序列化器（save/load/list/delete）
├── save_diff_engine.py    ← 增量diff（节省IO）
├── save_migrator.py       ← 版本迁移注册
├── save_cloud_sync.py     ← 微信云同步
├── save_integrity.py      ← SHA-256 校验
└── templates/
    ├── meta_progress.py   ← Roguelike元进度模板
    ├── world_state.py     ← 经营/RPG世界模板
    └── run_state.py       ← Roguelike单局模板
```

---

## 🔧 核心 API 速查

### 基础存档
```python
from core.save_system import SaveSerializer

# 保存（自动添加版本、时间戳、校验和）
SaveSerializer.save(game_state, slot=1)

# 加载（自动校验 + 版本迁移）
state = SaveSerializer.load(slot=1)

# 列出所有存档
slots = SaveSerializer.list_slots()
# → [{"slot": 1, "timestamp": ..., "game_time": 5.2}, ...]

# 删除
SaveSerializer.delete(slot=2)
```

### 增量存档（大地图/高频自动保存）
```python
from core.save_system import SaveDiffEngine

# 计算差异
patch = SaveDiffEngine.diff(old_state, new_state)
print(f"Patch大小: {SaveDiffEngine.patch_size_bytes(patch)} bytes")

# 应用差异（不修改原状态）
new_state = SaveDiffEngine.apply(base_state, patch)

# 深层diff（递归比较嵌套字典）
patch = SaveDiffEngine.deep_diff(old, new)
# → {"player.hp": 60, "resources.gold": 250}

# 合并多个patch
merged = SaveDiffEngine.compress_patches([patch1, patch2, patch3])
```

### 版本迁移（新版本兼容旧存档）
```python
from core.save_system import SaveMigrator

# 在 save_migrator.py 中注册迁移函数
@SaveMigrator.register(from_version=1, to_version=2)
def migrate_v1_to_v2(data: dict) -> dict:
    # 将旧字段 "exp" 重命名为 "experience"
    data["experience"] = data.pop("exp", 0)
    # 添加新字段的默认值
    data.setdefault("achievement_count", 0)
    return data

# 加载时自动迁移（SaveSerializer内部调用）
state = SaveSerializer.load(slot=1)  # 自动迁移到最新版本
```

### 云同步（微信跨设备）
```python
from core.save_system import SaveCloudSync

sync = SaveCloudSync()

# 保存后立即同步
SaveSerializer.save(state, slot=1)
sync.upload(slot=1)

# 登录时从云端恢复
sync.download(slot=1)
state = SaveSerializer.load(slot=1)

# 批量同步所有槽位
results = sync.sync_all(max_slots=3)
```

---

## 📋 模板使用指南

### Meta进度（Roguelike永久解锁）
```python
from core.save_system.templates.meta_progress import MetaProgressTemplate
from core.save_system import SaveSerializer

# 加载
data = SaveSerializer.load(slot=0)  # slot 0 = meta存档
meta = MetaProgressTemplate.from_dict(data.get("meta", {}))

# 解锁内容
is_new = meta.unlock("characters", "char_rogue")   # True=新解锁
is_new = meta.unlock("relics", "relic_hourglass")

# 局结束后更新
meta.record_run_end(won=True, score=8800, playtime=1245.0)
meta.add_gold(150)

# 保存
SaveSerializer.save({"meta": meta.to_dict()}, slot=0)
```

### 世界状态（经营/RPG大地图）
```python
from core.save_system.templates.world_state import WorldStateTemplate

world = WorldStateTemplate()

# 资源管理
world.add_resource("wood", 50)
success = world.spend_resource("gold", 100)  # False=不足

# 建造
world.place_building(3, 5, "farm", level=1)

# 推进时间
world.advance_day()
print(f"Day {world.day_count}, Season: {world.season}")

# 任务
world.quest_states["main_quest_1"] = "active"
```

### 单局状态（Roguelike局内）
```python
from core.save_system.templates.run_state import RunStateTemplate
import random

run = RunStateTemplate(
    seed=random.randint(0, 2**32),
    character_id="warrior",
    hp=100, max_hp=100,
)

run.take_damage(15)
run.heal(10)
run.add_gold(30)
run.deck.extend(["strike", "defend", "bash"])

# 局内自动存档（任意时刻可续玩）
SaveSerializer.save(run.to_dict(), slot=99)  # slot 99 = 局内存档
```

---

## 🗂️ 存档槽位规范

| 槽位 | 用途 |
|------|------|
| 0 | Meta进度（永久数据，谨慎覆写） |
| 1–5 | 玩家手动存档槽 |
| 10–19 | 自动存档（循环覆写） |
| 99 | Roguelike局内断点存档 |

---

## ⚠️ 强制约束

1. **SAVE_FORMAT_VERSION** 每次修改存档结构必须递增，并在 `SaveMigrator` 注册迁移
2. **校验和** 不得跳过，`save_integrity.verify_checksum()` 失败必须提示用户存档可能损坏
3. **存档数据** 只能包含基本类型（int/float/str/list/dict），禁止存储 Python 对象引用
4. **云同步** 必须先本地写盘成功，再异步上传，禁止只存云端
5. **增量存档** 适用于频繁自动保存（每30秒），全量存档适用于玩家手动保存

---

## 🏁 里程碑验收标准（M3）

> 100个对象的世界状态 <100ms 完成序列化+反序列化。
> 测试命令：`python -m pytest tests/test_save_system.py -v`
