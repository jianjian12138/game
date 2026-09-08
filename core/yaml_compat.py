"""
core/yaml_compat.py: 零依赖 PyYAML 安全兼容层
若运行环境安装了 PyYAML 则优先调用，未安装时自动降级到纯 Python 标准库解析器，杜绝因缺少外部依赖而崩溃。
"""
import json
import re
from typing import Any, Dict

try:
    import yaml as _yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    _yaml = None
    HAS_YAML = False

def safe_load(stream_or_text: Any) -> Any:
    """安全解析 YAML 格式内容，自动支持 YAML/JSON 与键值对"""
    if stream_or_text is None:
        return {}

    if hasattr(stream_or_text, "read"):
        text = stream_or_text.read()
    else:
        text = str(stream_or_text)

    if HAS_YAML and _yaml is not None:
        return _yaml.safe_load(text)

    # 纯标准库降级解析器 (YAML 1.2 是 JSON 的超集)
    text_clean = text.strip()
    if not text_clean:
        return {}

    try:
        return json.loads(text_clean)
    except json.JSONDecodeError:
        pass

    # 简单 YAML 键值对解析降级
    result: Dict[str, Any] = {}
    current_key = None
    for line in text_clean.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip().strip("'\"")
            v = v.strip().strip("'\"")
            if v.lower() == "true":
                val = True
            elif v.lower() == "false":
                val = False
            elif v.isdigit():
                val = int(v)
            else:
                try:
                    val = float(v)
                except ValueError:
                    val = v
            result[k] = val
    return result

def safe_dump(data: Any, **kwargs) -> str:
    """序列化为 YAML/JSON 字符串"""
    if HAS_YAML and _yaml is not None:
        return _yaml.safe_dump(data, **kwargs)
    return json.dumps(data, ensure_ascii=False, indent=2)
