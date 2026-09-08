"""
Save Cloud Sync — 微信云存储同步
===================================
将本地存档同步到微信小游戏云存储，实现跨设备存档。
在非微信环境（开发/测试）中自动降级为本地文件操作。
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional


class SaveCloudSync:
    """
    微信云存储同步器（含降级兼容层）。

    微信 JS API 对应关系：
        wx.setUserCloudStorage()   ← upload()
        wx.getUserCloudStorage()   ← download()
        wx.removeUserCloudStorage()← delete()
    """

    # 微信云存储的 key 前缀
    CLOUD_KEY_PREFIX = "save_slot_"
    # 最大云存档大小（微信限制 128KB/key）
    MAX_CLOUD_SIZE_BYTES = 128 * 1024

    def __init__(self, local_save_dir: Optional[Path] = None):
        self.local_dir = Path(local_save_dir or "saves")
        self._wx_available = self._detect_wx()

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def upload(self, slot: int) -> bool:
        """
        将本地存档上传到云端。

        Returns:
            True=成功, False=失败或不支持
        """
        path = self.local_dir / f"slot_{slot:02d}.json"
        if not path.exists():
            print(f"[CloudSync] ⚠️  本地存档不存在: slot {slot}")
            return False

        data = path.read_text(encoding="utf-8")
        if len(data.encode("utf-8")) > self.MAX_CLOUD_SIZE_BYTES:
            print(f"[CloudSync] ⚠️  存档超过128KB限制，跳过云同步")
            return False

        if self._wx_available:
            return self._wx_upload(slot, data)
        else:
            # 降级：复制到 cloud_backup 目录
            return self._local_backup(slot, data)

    def download(self, slot: int) -> bool:
        """
        从云端下载存档到本地。

        Returns:
            True=成功, False=云端无存档
        """
        if self._wx_available:
            return self._wx_download(slot)
        else:
            return self._local_restore(slot)

    def sync_all(self, max_slots: int = 5) -> dict:
        """同步所有槽位，返回结果摘要。"""
        results = {"uploaded": [], "failed": []}
        for slot in range(1, max_slots + 1):
            if self.upload(slot):
                results["uploaded"].append(slot)
            else:
                results["failed"].append(slot)
        print(f"[CloudSync] 同步完成: 成功{results['uploaded']} 失败{results['failed']}")
        return results

    # ------------------------------------------------------------------
    # 微信 API 封装（需要在 JS 桥接层实现）
    # ------------------------------------------------------------------

    def _wx_upload(self, slot: int, data: str) -> bool:
        """调用微信 setUserCloudStorage。实际由 JS 桥接执行。"""
        key = f"{self.CLOUD_KEY_PREFIX}{slot:02d}"
        print(f"[CloudSync] ⚠️ 微信云存档需通过 JS 桥接调用: key={key} (原生环境未接管)")
        return False

    def _wx_download(self, slot: int) -> bool:
        """调用微信 getUserCloudStorage。实际由 JS 桥接执行。"""
        key = f"{self.CLOUD_KEY_PREFIX}{slot:02d}"
        print(f"[CloudSync] ⚠️ 微信云存档需通过 JS 桥接调用: key={key} (原生环境未接管)")
        return False

    # ------------------------------------------------------------------
    # 降级：本地备份（开发/测试环境）
    # ------------------------------------------------------------------

    def _local_backup(self, slot: int, data: str) -> bool:
        backup_dir = self.local_dir / "cloud_backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"slot_{slot:02d}.json"
        backup_path.write_text(data, encoding="utf-8")
        print(f"[CloudSync] 💾 本地备份: {backup_path}")
        return True

    def _local_restore(self, slot: int) -> bool:
        backup_path = self.local_dir / "cloud_backup" / f"slot_{slot:02d}.json"
        if not backup_path.exists():
            return False
        dest = self.local_dir / f"slot_{slot:02d}.json"
        dest.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[CloudSync] 💾 本地恢复: slot {slot}")
        return True

    @staticmethod
    def _detect_wx() -> bool:
        """检测是否在微信小游戏环境中运行。"""
        # 实际判断通过运行时标志
        import os
        return os.environ.get("WECHAT_MINIGAME_ENV") == "1"
