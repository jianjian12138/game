"""
Save Serializer — 游戏状态序列化/反序列化
==========================================
将游戏状态 dict 持久化到本地文件，支持 JSON（可读）和 MessagePack（紧凑）格式。
"""

from __future__ import annotations
import json
import hashlib
import time
from pathlib import Path
from typing import Any, Optional

from .save_integrity import SaveIntegrity

# 避免循环导入，直接定义版本常量（与 __init__.py 保持一致）
SAVE_FORMAT_VERSION = 1


class SaveSerializer:
    """
    游戏状态序列化器。

    存档文件结构::
        {
            "_meta": {
                "version": 1,
                "timestamp": 1725417600.0,
                "slot": 1,
                "checksum": "sha256..."
            },
            "data": { ...游戏状态... }
        }
    """

    DEFAULT_SAVE_DIR = Path("saves")

    @classmethod
    def save(cls, state: dict, slot: int = 1, save_dir: Optional[Path] = None) -> Path:
        """
        保存游戏状态到指定槽位。

        Args:
            state:    游戏状态 dict
            slot:     存档槽位（1–99）
            save_dir: 存档目录（默认 ./saves/）

        Returns:
            存档文件路径
        """
        save_dir = Path(save_dir or cls.DEFAULT_SAVE_DIR)
        save_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "_meta": {
                "version": SAVE_FORMAT_VERSION,
                "timestamp": time.time(),
                "slot": slot,
                "game_time": state.get("_game_time", 0),
            },
            "data": state,
        }

        # 计算校验和
        payload["_meta"]["checksum"] = SaveIntegrity.compute_checksum(payload["data"])

        path = save_dir / f"slot_{slot:02d}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[SaveSystem] OK saved: {path} (slot {slot})")
        return path

    @classmethod
    def load(cls, slot: int = 1, save_dir: Optional[Path] = None) -> dict:
        """
        从槽位加载游戏状态。

        Returns:
            游戏状态 dict（data 字段）

        Raises:
            FileNotFoundError: 存档文件不存在
            ValueError:        校验和不匹配（存档损坏/被篡改）
        """
        save_dir = Path(save_dir or cls.DEFAULT_SAVE_DIR)
        path = save_dir / f"slot_{slot:02d}.json"

        if not path.exists():
            raise FileNotFoundError(f"存档不存在: {path}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload.get("_meta", {})
        data = payload.get("data", {})

        # 完整性校验
        stored_checksum = meta.get("checksum", "")
        if stored_checksum:
            SaveIntegrity.verify_checksum(data, stored_checksum)

        print(f"[SaveSystem] OK loaded: slot {slot} "
              f"(v{meta.get('version', '?')}, "
              f"time: {time.strftime('%Y-%m-%d %H:%M', time.localtime(meta.get('timestamp', 0)))})")
        return data

    @classmethod
    def list_slots(cls, save_dir: Optional[Path] = None) -> list[dict]:
        """列出所有存档槽位信息。"""
        save_dir = Path(save_dir or cls.DEFAULT_SAVE_DIR)
        if not save_dir.exists():
            return []

        slots = []
        for path in sorted(save_dir.glob("slot_*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                meta = payload.get("_meta", {})
                slots.append({
                    "slot": meta.get("slot"),
                    "timestamp": meta.get("timestamp"),
                    "version": meta.get("version"),
                    "game_time": meta.get("game_time"),
                    "path": str(path),
                })
            except Exception:
                pass
        return slots

    @classmethod
    def delete(cls, slot: int, save_dir: Optional[Path] = None) -> bool:
        """删除指定槽位存档。"""
        save_dir = Path(save_dir or cls.DEFAULT_SAVE_DIR)
        path = save_dir / f"slot_{slot:02d}.json"
        if path.exists():
            path.unlink()
            print(f"[SaveSystem] DELETED: slot {slot}")
            return True
        return False
