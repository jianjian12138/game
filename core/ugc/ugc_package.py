"""
UGC Package Packaging and Checksum Verification
Encapsulates user-created levels, charts, and tracks with metadata and SHA-256 integrity hashes.
"""

import json
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple


@dataclass
class UGCMetadata:
    package_id: str
    content_type: str  # "LEVEL", "CHART", "TRACK"
    title: str
    author_id: str
    author_name: str
    version: int = 1
    checksum: str = ""


class UGCPackage:
    """Handles serialization and cryptographic integrity checking of UGC packages."""

    @staticmethod
    def create_package(content_type: str, title: str, author_id: str,
                       author_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload_str = json.dumps(payload, sort_keys=True)
        chk = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        pkg_id = f"ugc_{content_type.lower()}_{chk[:10]}"
        return {
            "_ugc_meta": {
                "package_id": pkg_id,
                "content_type": content_type,
                "title": title,
                "author_id": author_id,
                "author_name": author_name,
                "version": 1,
                "checksum": chk
            },
            "data": payload
        }

    @staticmethod
    def verify_and_unpack(package_dict: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        meta = package_dict.get("_ugc_meta")
        data = package_dict.get("data")
        if not meta or not data:
            return False, None, "INVALID_PACKAGE_FORMAT"

        expected_chk = meta.get("checksum", "")
        payload_str = json.dumps(data, sort_keys=True)
        actual_chk = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        if expected_chk != actual_chk:
            return False, None, "CHECKSUM_INTEGRITY_MISMATCH"

        return True, data, "OK"
