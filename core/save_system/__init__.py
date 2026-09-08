"""
Save System Framework — 游戏存档序列化框架
==========================================
提供游戏状态的序列化、增量diff、版本迁移、云同步和完整性校验。

用法::
    from core.save_system import SaveSerializer, SaveDiffEngine, SaveCloudSync

    # 保存
    state = {"level": 5, "gold": 1200, "inventory": [...]}
    slot = SaveSerializer.save(state, slot=1)

    # 加载
    state = SaveSerializer.load(slot=1)

    # 增量存档（只存变化，节省 IO）
    diff = SaveDiffEngine.diff(old_state, new_state)
    SaveDiffEngine.apply_patch(slot=1, diff=diff)
"""

from .save_serializer import SaveSerializer
from .save_diff_engine import SaveDiffEngine
from .save_migrator import SaveMigrator
from .save_cloud_sync import SaveCloudSync
from .save_integrity import SaveIntegrity

__all__ = [
    "SaveSerializer",
    "SaveDiffEngine",
    "SaveMigrator",
    "SaveCloudSync",
    "SaveIntegrity",
]

# 当前存档格式版本，升级时递增并在 SaveMigrator 注册迁移函数
SAVE_FORMAT_VERSION = 1
