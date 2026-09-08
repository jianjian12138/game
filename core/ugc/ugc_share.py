"""
UGC Share Code Encoder & Decoder
Encodes UGC packages into compact Base64/Zlib share tokens for WeChat / social sharing.
"""

import json
import zlib
import base64
from typing import Dict, Any, Optional, Tuple
from .ugc_package import UGCPackage


class UGCShare:
    """Generates and parses shareable clipboard strings for UGC levels, charts, and tracks."""

    PREFIX = "UGC:"

    @classmethod
    def encode_share_token(cls, package_dict: Dict[str, Any]) -> str:
        """Compresses package JSON with zlib and encodes to URL-safe Base64."""
        json_bytes = json.dumps(package_dict, separators=(",", ":")).encode("utf-8")
        compressed = zlib.compress(json_bytes, level=9)
        b64_str = base64.urlsafe_b64encode(compressed).decode("ascii")
        return f"{cls.PREFIX}{b64_str}"

    @classmethod
    def decode_share_token(cls, token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Decodes and decompresses share token, verifies package integrity."""
        if not token.startswith(cls.PREFIX):
            return False, None, "INVALID_TOKEN_PREFIX"

        b64_str = token[len(cls.PREFIX):]
        try:
            compressed = base64.urlsafe_b64decode(b64_str.encode("ascii"))
            json_bytes = zlib.decompress(compressed)
            package_dict = json.loads(json_bytes.decode("utf-8"))
        except Exception as e:
            return False, None, f"DECODING_ERROR: {str(e)}"

        valid, payload, err = UGCPackage.verify_and_unpack(package_dict)
        if not valid:
            return False, None, err

        return True, package_dict, "OK"
