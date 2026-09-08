"""
Save Integrity — 存档完整性校验
=================================
使用 SHA-256 校验和防止存档损坏和篡改。
"""

from __future__ import annotations
import json
import hashlib


class SaveIntegrity:
    """存档完整性工具：计算和验证校验和。"""

    @staticmethod
    def compute_checksum(data: dict) -> str:
        """
        计算数据的 SHA-256 校验和。

        Args:
            data: 要校验的数据 dict

        Returns:
            十六进制字符串格式的 SHA-256 校验和
        """
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_checksum(data: dict, stored_checksum: str):
        """
        验证数据校验和。

        Raises:
            ValueError: 校验和不匹配时抛出
        """
        computed = SaveIntegrity.compute_checksum(data)
        if computed != stored_checksum:
            raise ValueError(
                f"存档校验失败！存档可能已损坏或被篡改。\n"
                f"  期望: {stored_checksum[:16]}...\n"
                f"  实际: {computed[:16]}..."
            )

    @staticmethod
    def is_valid(data: dict, stored_checksum: str) -> bool:
        """静默版校验，返回 True/False 而非抛出异常。"""
        try:
            SaveIntegrity.verify_checksum(data, stored_checksum)
            return True
        except ValueError:
            return False
