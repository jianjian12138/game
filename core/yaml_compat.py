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

    # 纯标准库降级解析器：支持常用的嵌套 mapping/list 结构。
    # 不能只按行拆键值，否则 effect:\n  - type: damage 会被错误解析为字符串。
    raw_lines = []
    for raw_line in text_clean.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        raw_lines.append((indent, raw_line.strip()))

    def parse_scalar(value: str) -> Any:
        value = value.strip()
        if not value:
            return None
        if (value.startswith("\"") and value.endswith("\"")) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        if value.lower() in ("null", "none", "~"):
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            try:
                return float(value) if "." in value else int(value)
            except ValueError:
                return value

    def parse_block(index: int, indent: int):
        if index >= len(raw_lines):
            return {}, index
        is_list = raw_lines[index][0] == indent and raw_lines[index][1].startswith("-")
        result = [] if is_list else {}
        while index < len(raw_lines):
            current_indent, text = raw_lines[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                break
            if is_list:
                if not text.startswith("-"):
                    break
                item_text = text[1:].strip()
                if not item_text:
                    if index + 1 < len(raw_lines) and raw_lines[index + 1][0] > indent:
                        item, index = parse_block(index + 1, raw_lines[index + 1][0])
                    else:
                        item, index = None, index + 1
                    result.append(item)
                    continue
                if ":" in item_text:
                    key, value = item_text.split(":", 1)
                    item = {key.strip(): parse_scalar(value)} if value.strip() else {key.strip(): None}
                    index += 1
                    while index < len(raw_lines) and raw_lines[index][0] > indent:
                        child_indent, child_text = raw_lines[index]
                        if child_text.startswith("-"):
                            child, index = parse_block(index, child_indent)
                            if item.get(key.strip()) is None:
                                item[key.strip()] = child
                            else:
                                item.setdefault("items", child)
                            continue
                        if ":" not in child_text:
                            index += 1
                            continue
                        child_key, child_value = child_text.split(":", 1)
                        index += 1
                        if child_value.strip():
                            item[child_key.strip()] = parse_scalar(child_value)
                        elif index < len(raw_lines) and raw_lines[index][0] > child_indent:
                            nested, index = parse_block(index, raw_lines[index][0])
                            item[child_key.strip()] = nested
                        else:
                            item[child_key.strip()] = None
                    result.append(item)
                else:
                    result.append(parse_scalar(item_text))
                    index += 1
                continue

            if ":" not in text:
                index += 1
                continue
            key, value = text.split(":", 1)
            key = key.strip()
            index += 1
            if value.strip():
                result[key] = parse_scalar(value)
            elif index < len(raw_lines) and raw_lines[index][0] > indent:
                nested, index = parse_block(index, raw_lines[index][0])
                result[key] = nested
            else:
                result[key] = None
        return result, index

    parsed, _ = parse_block(0, raw_lines[0][0] if raw_lines else 0)
    return parsed

def safe_dump(data: Any, **kwargs) -> str:
    """序列化为 YAML/JSON 字符串"""
    if HAS_YAML and _yaml is not None:
        return _yaml.safe_dump(data, **kwargs)
    return json.dumps(data, ensure_ascii=False, indent=2)
