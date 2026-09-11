"""pipeline/png_io.py — 纯 Python PNG 编解码（无 PIL/numpy 依赖）。

支持：8bit、颜色类型 2(RGB)/6(RGBA)、非隔行、全部 5 种滤波还原。
用途：① 程序化占位的真·PNG 生成；② 入库 QA 的像素级真实校验
      （尺寸、透明通道、主色板提取、水印文本块）。
诚实原则：不支持的格式直接抛 ValueError，不静默降级伪装成功。
"""
from __future__ import annotations

import struct
import zlib
from typing import Any, Dict, List, Tuple


def encode_png(width: int, height: int, pixels: bytes, channels: int = 4) -> bytes:
    """编码 RGB/RGBA 像素为合法 PNG。

    pixels: 长度必须为 width*height*channels 的逐像素 bytes（行优先、无滤波字节）。
    """
    if channels not in (3, 4):
        raise ValueError(f"channels 仅支持 3/4，收到 {channels}")
    if len(pixels) != width * height * channels:
        raise ValueError(
            f"pixels 长度 {len(pixels)} != {width}*{height}*{channels}"
            f"={width * height * channels}")
    color_type = 6 if channels == 4 else 2
    raw = bytearray()
    stride = width * channels
    for y in range(height):
        raw.append(0)  # filter type: None
        raw.extend(pixels[y * stride:(y + 1) * stride])
    comp = zlib.compress(bytes(raw), 9)
    out = bytearray()
    out.extend(b"\x89PNG\r\n\x1a\n")
    _chunk(out, b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0))
    _chunk(out, b"IDAT", comp)
    _chunk(out, b"IEND", b"")
    return bytes(out)


def _chunk(out: bytearray, typ: bytes, data: bytes) -> None:
    out += struct.pack(">I", len(data))
    out += typ
    out += data
    crc = zlib.crc32(typ + data) & 0xffffffff
    out += struct.pack(">I", crc)


def decode_png(data: bytes) -> Dict[str, Any]:
    """解码 PNG，返回 {width,height,channels,pixels,bit_depth,text_chunks}。

    pixels: 逐像素 RGB/RGBA bytes。仅支持 8bit、颜色类型 2/6、非隔行。
    """
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("不是合法 PNG 签名")
    pos = 8
    width = height = None
    bit_depth = color_type = 0
    idat = bytearray()
    text_chunks: List[Tuple[str, str]] = []
    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError("PNG 截断：缺少长度/类型字段")
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if len(body) != ln:
            raise ValueError("PNG 截断：块体不足")
        if typ == b"IHDR":
            width, height, bit_depth, color_type, _comp, _filt, ilace = struct.unpack(
                ">IIBBBBB", body)
            if bit_depth != 8:
                raise ValueError(f"仅支持 8bit，收到 {bit_depth}")
            if color_type not in (2, 6):
                raise ValueError(f"仅支持 RGB(2)/RGBA(6)，收到 color_type={color_type}")
            if ilace != 0:
                raise ValueError("不支持隔行 PNG")
        elif typ == b"IDAT":
            idat.extend(body)
        elif typ == b"tEXt":
            if b"\x00" in body:
                k, t = body.split(b"\x00", 1)
                text_chunks.append((k.decode("latin1", "replace"),
                                    t.decode("latin1", "replace")))
        elif typ == b"iTXt":
            if b"\x00" in body:
                k, rest = body.split(b"\x00", 1)
                text_chunks.append((k.decode("latin1", "replace"),
                                    rest.decode("latin1", "replace")))
        elif typ == b"zTXt":
            if b"\x00" in body:
                k, rest = body.split(b"\x00", 1)
                try:
                    text = zlib.decompress(rest[1:]).decode("latin1", "replace")
                    text_chunks.append((k.decode("latin1", "replace"), text))
                except Exception:
                    pass
        elif typ == b"IEND":
            break
        pos += 12 + ln
    if width is None:
        raise ValueError("PNG 缺少 IHDR")
    channels = 3 if color_type == 2 else 4
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    expected = height * (1 + stride)
    if len(raw) != expected:
        raise ValueError(f"IDAT 解压后长度 {len(raw)} != 预期 {expected}")
    pixels = _unfilter(raw, width, height, channels)
    return {"width": width, "height": height, "channels": channels,
            "pixels": pixels, "bit_depth": bit_depth, "text_chunks": text_chunks}


def _unfilter(raw: bytes, width: int, height: int, channels: int) -> bytes:
    stride = width * channels
    out = bytearray(width * height * channels)
    prev = bytearray(stride)
    p = 0
    for y in range(height):
        ft = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if ft == 0:
            pass
        elif ft == 1:  # Sub
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + a) & 0xff
        elif ft == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xff
        elif ft == 3:  # Average
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xff
        elif ft == 4:  # Paeth
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(a, b, c)) & 0xff
        else:
            raise ValueError(f"未知滤波类型 {ft}")
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return bytes(out)


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c
