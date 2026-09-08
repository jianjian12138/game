"""
Save Migrator — 存档版本迁移
==============================
处理新版本游戏读取旧版本存档的兼容性问题。
每次升级存档格式时，在此注册迁移函数。
"""

from __future__ import annotations
from typing import Callable, Dict

# 避免循环导入
SAVE_FORMAT_VERSION = 1


class SaveMigrator:
    """
    存档版本迁移器。

    用法::
        # 注册 v1→v2 的迁移函数
        @SaveMigrator.register(from_version=1, to_version=2)
        def migrate_v1_to_v2(data: dict) -> dict:
            data["new_field"] = data.pop("old_field", None)
            return data

        # 迁移存档
        migrated = SaveMigrator.migrate(old_data, current_version=2)
    """

    # {from_version: (to_version, migration_fn)}
    _migrations: Dict[int, tuple] = {}

    @classmethod
    def register(cls, from_version: int, to_version: int):
        """装饰器：注册版本迁移函数。"""
        def decorator(fn: Callable):
            cls._migrations[from_version] = (to_version, fn)
            return fn
        return decorator

    @classmethod
    def migrate(cls, data: dict, stored_version: int = 0,
                target_version: int = None) -> dict:
        """
        将 data 从 stored_version 迁移到 target_version（默认当前版本）。

        Args:
            data:           原始存档数据
            stored_version: 存档中记录的版本号
            target_version: 目标版本号（默认 SAVE_FORMAT_VERSION）

        Returns:
            迁移后的数据 dict
        """
        target = target_version or SAVE_FORMAT_VERSION
        current = stored_version
        import copy
        result = copy.deepcopy(data)

        while current < target:
            migration = cls._migrations.get(current)
            if migration is None:
                print(f"[SaveMigrator] ⚠️  没有从 v{current} 到更新版本的迁移路径，跳过")
                break
            to_ver, fn = migration
            print(f"[SaveMigrator] 🔄 迁移存档: v{current} → v{to_ver}")
            result = fn(result)
            current = to_ver

        return result

    @classmethod
    def needs_migration(cls, stored_version: int) -> bool:
        """检查是否需要迁移。"""
        return stored_version < SAVE_FORMAT_VERSION


# ======================================================================
# 内置迁移：当前只有 v1，无需迁移，预留扩展
# ======================================================================
# 示例：未来 v1→v2 时取消注释并添加迁移逻辑
#
# @SaveMigrator.register(from_version=1, to_version=2)
# def migrate_v1_to_v2(data: dict) -> dict:
#     # 示例：将旧的 "exp" 字段重命名为 "experience"
#     data["experience"] = data.pop("exp", 0)
#     return data
