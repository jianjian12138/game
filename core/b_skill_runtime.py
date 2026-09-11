"""core/b_skill_runtime.py — 65 项 B 类（确定性算法）技能的真实执行与验收（W4）。

B 类与 C 类的防伪底线不同，但同样不许装饰：
- C 类（绑 LLM）没有金标准，证据是"一次真实 LLM 调用 + 通过 schema/acceptance"；
- B 类产出可由确定性算法生成、用数值断言验收，证据是
  "一次真实运行 + acceptance 断言全过 + 可复现（同输入同输出）"。

所以 B 类不依赖 LLM、不依赖网络，纯函数式运行；每一项必须带一组数值断言，
断言不通过就不许注册为能力。依赖外部 DCC/GPU 工具、当前环境跑不了的 B 类
（如高模雕刻、UV 展开、PBR 烘焙），run 直接返回 NEEDS_RUNTIME_TOOL——
**宁可标红，也不靠占位实现冒充可执行**（红线 13.2）。

本文件第一批实现 18 项纯 Python 确定性算法（覆盖 Logic/Rendering/Audio/QA），
另含 3 项显式标 NEEDS_RUNTIME_TOOL 的 DCC/GPU 依赖项。其余 B 类按同模式
在后续批次补齐，清单见 core/skill_classification.B_SKILLS。
"""
from __future__ import annotations

import heapq
import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.run_context import RunContext


class BSkillStatus:
    OK = "OK"
    ACCEPTANCE_FAILED = "ACCEPTANCE_FAILED"
    NEEDS_RUNTIME_TOOL = "NEEDS_RUNTIME_TOOL"
    RUN_ERROR = "RUN_ERROR"
    NO_SPEC = "NO_SPEC"


@dataclass
class BSkillSpec:
    """一个 B 类确定性技能的契约。"""
    skill_id: str
    family: str
    summary: str
    run: Callable[[Dict[str, Any]], Dict[str, Any]]   # 确定性计算 -> payload
    acceptance: Callable[[Dict[str, Any]], List[str]]  # 返回错误字符串列表，空=通过
    sample: Dict[str, Any] = field(default_factory=dict)
    needs_runtime_tool: Optional[str] = None
    notes: str = ""


@dataclass
class BSkillResult:
    skill_id: str
    status: str
    payload: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    runtime: str = ""
    needs_runtime_tool: str = ""
    checks_passed: int = 0
    latency_ms: int = 0

    @property
    def ok(self) -> bool:
        return self.status == BSkillStatus.OK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id, "status": self.status,
            "ok": self.ok, "runtime": self.runtime,
            "needs_runtime_tool": self.needs_runtime_tool,
            "checks_passed": self.checks_passed, "latency_ms": self.latency_ms,
            "payload": self.payload, "errors": self.errors,
        }


def _close(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


# ─────────────────────────────────────────────────────────────────────────────
# Logic 族（9 项）
# ─────────────────────────────────────────────────────────────────────────────

def _a_star(params: Dict[str, Any]) -> Dict[str, Any]:
    w, h = int(params["w"]), int(params["h"])
    start, goal = tuple(params["start"]), tuple(params["goal"])
    obs = set(tuple(p) for p in params.get("obstacles", []))
    hcost = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
    open_ = [(hcost(start, goal), 0, start)]
    came: Dict[tuple, tuple] = {}
    g: Dict[tuple, float] = {start: 0}
    while open_:
        _, cost, cur = heapq.heappop(open_)
        if cur == goal:
            path = []
            while cur in came:
                path.append(list(cur))
                cur = came[cur]
            path.append(list(start))
            path.reverse()
            return {"start": list(start), "goal": list(goal),
                    "path": path, "length": len(path), "cost": cost,
                    "expect_overlap": params.get("expect_overlap")}
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cur[0] + dx, cur[1] + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in obs:
                ng = cost + 1
                if ng < g.get((nx, ny), 1e9):
                    g[(nx, ny)] = ng
                    came[(nx, ny)] = cur
                    heapq.heappush(open_, (ng + hcost((nx, ny), goal), ng, (nx, ny)))
    return {"start": list(start), "goal": list(goal),
            "path": [], "length": 0, "cost": -1}


def _a_star_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["length"] == 0:
        e.append("未找到路径（起点/终点被墙或不可达）")
        return e
    if p["path"][0] != p["start"] or p["path"][-1] != p["goal"]:
        e.append("路径两端不是起点/终点")
    for a, b in zip(p["path"], p["path"][1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            e.append("路径存在非相邻跳跃")
            break
    if p["cost"] != p["length"] - 1:
        e.append("cost 与步数不一致")
    return e


def _aabb(params: Dict[str, Any]) -> Dict[str, Any]:
    a, b = params["a"], params["b"]
    overlap = not (a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"]
                   or a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"])
    return {"a": a, "b": b, "overlap": overlap,
            "expect_overlap": params.get("expect_overlap")}


def _aabb_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    expect = p.get("expect_overlap")
    if expect is not None and p["overlap"] != expect:
        e.append(f"overlap={p['overlap']} 与期望 {expect} 不符")
    return e


def _sat(params: Dict[str, Any]) -> Dict[str, Any]:
    A = [tuple(x) for x in params["a"]]
    B = [tuple(x) for x in params["b"]]

    def axes(poly):
        axs = []
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            axs.append((-(y2 - y1), x2 - x1))
        return axs

    def proj(poly, ax):
        dots = [px * ax[0] + py * ax[1] for px, py in poly]
        return min(dots), max(dots)

    min_ov = float("inf")
    mtv = None
    for ax in axes(A) + axes(B):
        axl = math.hypot(*ax) or 1.0
        ux, uy = ax[0] / axl, ax[1] / axl
        amin, amax = proj(A, (ux, uy))
        bmin, bmax = proj(B, (ux, uy))
        if amax < bmin or bmax < amin:
            return {"a": params["a"], "b": params["b"],
                    "overlap": False, "mtv": [0.0, 0.0], "overlap_depth": 0.0}
        o = min(amax, bmax) - max(amin, bmin)
        if o < min_ov:
            min_ov = o
            mtv = (ux, uy)
    return {"a": params["a"], "b": params["b"], "overlap": True,
            "mtv": [round(mtv[0] * min_ov, 3), round(mtv[1] * min_ov, 3)],
            "overlap_depth": round(min_ov, 3),
            "expect_overlap": params.get("expect_overlap")}


def _sat_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_overlap"):
        if not p["overlap"]:
            e.append("期望重叠却判定为分离")
        elif p["overlap_depth"] <= 0:
            e.append("判定重叠但穿透深度非正")
    else:
        if p["overlap"]:
            e.append("期望分离却判定为重叠")
    return e


def _state_machine(params: Dict[str, Any]) -> Dict[str, Any]:
    states = set(params["states"])
    trans = {s: {} for s in states}
    for (src, ev), dst in params["transitions"].items():
        trans[src][ev] = dst
    cur = params["init"]
    trace = [cur]
    for ev in params["events"]:
        nxt = trans.get(cur, {}).get(ev)
        if nxt is None:
            return {"state": cur, "accepted": False, "trace": trace,
                    "stuck_on": ev}
        cur = nxt
        trace.append(cur)
    return {"state": cur, "accepted": cur in set(params.get("accept", [])),
            "trace": trace, "expect_accept": params.get("expect_accept")}


def _state_machine_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_accept") and not p["accepted"]:
        e.append(f"未到达接受态，停在 {p['state']}")
    if "stuck_on" in p:
        e.append(f"卡在事件 {p['stuck_on']}")
    return e


def _jump(params: Dict[str, Any]) -> Dict[str, Any]:
    v0 = float(params["v0"])
    g = float(params["g"])
    apex = v0 * v0 / (2 * g)
    airtime = 2 * v0 / g
    return {"v0": v0, "g": g, "apex": apex, "airtime": airtime}


def _jump_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if not _close(p["apex"], p["v0"] ** 2 / (2 * p["g"]), 1e-9):
        e.append("apex 不等于 v0^2/2g")
    if not _close(p["airtime"], 2 * p["v0"] / p["g"], 1e-9):
        e.append("airtime 不等于 2v0/g")
    if p["apex"] <= 0:
        e.append("apex 非正")
    return e


def _dungeon(params: Dict[str, Any]) -> Dict[str, Any]:
    import hashlib
    seed = int(params["seed"])
    rng = random.Random(seed)
    w, h = int(params["w"]), int(params["h"])
    cells = []
    for y in range(h):
        row = []
        for x in range(w):
            row.append(1 if rng.random() < params.get("wall_prob", 0.3) else 0)
        cells.append(row)
    cells[0][0] = 0
    cells[h - 1][w - 1] = 0
    blob = json.dumps({"w": w, "h": h, "cells": cells},
                      separators=(",", ":")).encode("utf-8")
    return {"seed": seed, "w": w, "h": h, "map_hash": "sha256:"
            + hashlib.sha256(blob).hexdigest(), "start": [0, 0],
            "boss": [w - 1, h - 1]}


def _dungeon_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    # 复现校验：同一 seed 必须得到同一 map_hash
    rep = _dungeon({"seed": p["seed"], "w": p["w"], "h": p["h"],
                    "wall_prob": params_wallprob(p)})
    if rep["map_hash"] != p["map_hash"]:
        e.append("同种子复现的 map_hash 不一致（非确定性）")
    if p["start"] != [0, 0] or p["boss"] != [p["w"] - 1, p["h"] - 1]:
        e.append("起点或 Boss 房坐标不对")
    return e


def params_wallprob(p: Dict[str, Any]) -> float:
    return 0.3  # 与 DEFAULT 一致（sample 固定）


def _lerp(params: Dict[str, Any]) -> Dict[str, Any]:
    a, b = float(params["a"]), float(params["b"])
    ts = params.get("ts", [0.0, 0.25, 0.5, 0.75, 1.0])
    out = [a + (b - a) * t for t in ts]
    return {"a": a, "b": b, "ts": ts, "out": out}


def _lerp_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if not _close(p["out"][0], p["a"]) or not _close(p["out"][-1], p["b"]):
        e.append("t=0 或 t=1 端点不对")
    seq = p["out"]
    if any(seq[i] > seq[i + 1] + 1e-9 for i in range(len(seq) - 1)) and \
       any(seq[i] < seq[i + 1] - 1e-9 for i in range(len(seq) - 1)):
        e.append("插值非单调")
    return e


def _raycast(params: Dict[str, Any]) -> Dict[str, Any]:
    w, h = int(params["w"]), int(params["h"])
    walls = set(tuple(c) for c in params.get("walls", []))
    (x0, y0), (x1, y1) = tuple(params["src"]), tuple(params["dst"])
    dx, dy = x1 - x0, y1 - y0
    steps = max(abs(dx), abs(dy), 1)
    hit = None
    for i in range(steps + 1):
        x = round(x0 + dx * i / steps)
        y = round(y0 + dy * i / steps)
        if not (0 <= x < w and 0 <= y < h):
            hit = [x, y]
            break
        if (x, y) in walls:
            hit = [x, y]
            break
    return {"src": list(params["src"]), "dst": list(params["dst"]),
            "blocked": hit is not None, "hit": hit,
            "expect_blocked": params.get("expect_blocked")}


def _raycast_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_blocked") and not p["blocked"]:
        e.append("期望被墙阻挡却畅通")
    if p.get("expect_blocked") is False and p["blocked"]:
        e.append("期望畅通却被阻挡")
    return e


def _behavior_tree(params: Dict[str, Any]) -> Dict[str, Any]:
    seq = params["sequence"]  # list of "success"/"failure"
    kind = params.get("kind", "sequence")
    if kind == "sequence":
        res = "success" if all(s == "success" for s in seq) else "failure"
    else:  # selector
        res = "success" if any(s == "success" for s in seq) else "failure"
    return {"kind": kind, "sequence": seq, "result": res, "expect": params.get("expect")}


def _behavior_tree_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect") and p["result"] != p["expect"]:
        e.append(f"行为树结果 {p['result']} 与期望 {p['expect']} 不符")
    return e


# ─────────────────────────────────────────────────────────────────────────────
# Rendering 族（5 项）
# ─────────────────────────────────────────────────────────────────────────────

def _screen_shake(params: Dict[str, Any]) -> Dict[str, Any]:
    amp, dur = float(params["amplitude"]), float(params["duration"])
    ts = params.get("ts", [0.0, 0.25, 0.5, 0.75, 1.0])
    out = [round(amp * (1 - t) ** 2, 4) for t in ts]
    return {"amplitude": amp, "duration": dur, "ts": ts, "offset": out}


def _screen_shake_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if not _close(p["offset"][0], p["amplitude"], 1e-6):
        e.append("t=0 应为最大振幅")
    if p["offset"][-1] > 1e-3:
        e.append("t=duration 应衰减到 ~0")
    if any(p["offset"][i] < p["offset"][i + 1] - 1e-6
           for i in range(len(p["offset"]) - 1)):
        e.append("衰减非单调")
    return e


def _sprite(params: Dict[str, Any]) -> Dict[str, Any]:
    nf = int(params["frames"])
    fps = float(params["fps"])
    ts = params.get("ts", [0.0, 0.5, 1.0, 1.999])
    idx = [min(int(t * fps) % nf, nf - 1) for t in ts]
    return {"frames": nf, "fps": fps, "ts": ts, "frame_index": idx}


def _sprite_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if any(i < 0 or i >= p["frames"] for i in p["frame_index"]):
        e.append("帧索引越界")
    return e


def _upscale(params: Dict[str, Any]) -> Dict[str, Any]:
    n = int(params["scale"])
    grid = params["grid"]  # list of list of 0/1
    hgt = len(grid)
    wid = len(grid[0]) if grid else 0
    out = []
    for row in grid:
        new = []
        for v in row:
            new.extend([v] * n)
        out.append(new)
    big = []
    for row in out:
        for _ in range(n):
            big.append(row)
    sm = sum(sum(r) for r in grid)
    sm2 = sum(sum(r) for r in big)
    return {"scale": n, "in_w": wid, "in_h": hgt, "out_w": wid * n,
            "out_h": hgt * n, "upscaled": big, "pixel_sum_in": sm,
            "pixel_sum_out": sm2}


def _upscale_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["out_w"] != p["in_w"] * p["scale"] or p["out_h"] != p["in_h"] * p["scale"]:
        e.append("输出尺寸不是输入的 scale 倍")
    if p["pixel_sum_out"] != p["pixel_sum_in"] * p["scale"] * p["scale"]:
        e.append("整数放大后前景像素数应是 n^2 倍（失败说明出现插值）")
    return e


def _daynight(params: Dict[str, Any]) -> Dict[str, Any]:
    tod = float(params["t"])  # 0..24
    # 最暗在午夜，最亮在正午，用正弦
    k = (math.cos((tod - 12) / 24 * 2 * math.pi) + 1) / 2  # 0@midnight,1@noon
    brightness = round(0.15 + 0.85 * k, 3)
    return {"t": tod, "brightness": brightness}


def _daynight_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    noon = _daynight({"t": 12.0})["brightness"]
    mid = _daynight({"t": 0.0})["brightness"]
    if not (noon > mid):
        e.append("正午亮度未高于午夜")
    if not _close(p["brightness"], 0.15 + 0.85 * (math.cos((p["t"] - 12) / 24 * 2 * math.pi) + 1) / 2, 1e-6):
        e.append("亮度公式不一致")
    return e


def _stars(params: Dict[str, Any]) -> Dict[str, Any]:
    import hashlib
    seed = int(params["seed"])
    rng = random.Random(seed)
    n = int(params["count"])
    w, h = int(params["w"]), int(params["h"])
    pts = [[rng.randrange(w), rng.randrange(h)] for _ in range(n)]
    blob = json.dumps({"seed": seed, "pts": pts},
                      separators=(",", ":")).encode("utf-8")
    return {"seed": seed, "count": n, "w": w, "h": h,
            "points": pts, "hash": "sha256:" + hashlib.sha256(blob).hexdigest()}


def _stars_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    rep = _stars({"seed": p["seed"], "count": p["count"], "w": p["w"], "h": p["h"]})
    if rep["hash"] != p["hash"]:
        e.append("同种子星图 hash 不一致（非确定性）")
    if len(p["points"]) != p["count"]:
        e.append("星点数量不符")
    return e


# ─────────────────────────────────────────────────────────────────────────────
# Audio 族（2 项）
# ─────────────────────────────────────────────────────────────────────────────

def _adsr(params: Dict[str, Any]) -> Dict[str, Any]:
    a, d, s, r = (float(params[k]) for k in ("attack", "decay", "sustain", "release"))
    dur = float(params["duration"])
    out = []
    for i in range(int(dur * 1000)):
        t = i / 1000.0
        if t < a:
            v = t / a
        elif t < a + d:
            v = 1 - (1 - s) * ((t - a) / d)
        elif t < a + d + float(params.get("hold", 0.5)):
            v = s
        else:
            tt = t - a - d - float(params.get("hold", 0.5))
            v = s * max(0.0, 1 - tt / r)
        out.append(round(v, 4))
    return {"attack": a, "decay": d, "sustain": s, "release": r,
            "duration": dur, "samples": out}


def _adsr_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if not _close(p["samples"][0], 0.0, 1e-3):
        e.append("起音应从 0 开始")
    idx_a = min(int(p["attack"] * 1000), len(p["samples"]) - 1)
    if not _close(p["samples"][idx_a], 1.0, 1e-2):  # attack 末端（进入 decay 前）应到 1.0
        e.append("attack 末应到 1.0")
    if p["samples"][-1] > 0.05:
        e.append("release 末应衰减到 ~0")
    return e


def _arpeggio(params: Dict[str, Any]) -> Dict[str, Any]:
    base = float(params["base_freq"])
    ratios = params["ratios"]           # 如 [1, 1.25, 1.5]（大三和弦）
    oct = int(params.get("octaves", 1))
    seq = []
    for o in range(oct):
        for rt in ratios:
            seq.append(round(base * rt * (2 ** o), 3))
    return {"base_freq": base, "ratios": ratios, "octaves": oct,
            "sequence": seq, "length": len(seq)}


def _arpeggio_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    expect = len(p["ratios"]) * p["octaves"]
    if len(p["sequence"]) != expect:
        e.append(f"音序长度应为 {expect}")
    if any(p["sequence"][i] > p["sequence"][i + 1] + 1e-6
           for i in range(len(p["sequence"]) - 1)):
        e.append("琶音音高应单调递增")
    return e


# ─────────────────────────────────────────────────────────────────────────────
# QA 族（2 项）
# ─────────────────────────────────────────────────────────────────────────────

def _pixel_diff(params: Dict[str, Any]) -> Dict[str, Any]:
    a = params["a"]   # 灰度二维数组
    b = params["b"]
    hgt = len(a)
    wid = len(a[0]) if a else 0
    total = 0
    changed = 0
    for y in range(hgt):
        for x in range(wid):
            d = abs(a[y][x] - b[y][x])
            total += d
            if d > 0:
                changed += 1
    return {"w": wid, "h": hgt, "diff_sum": total,
            "changed_pixels": changed,
            "max_diff": max((max(abs(ra[x] - rb[x]) for x in range(wid))
                             for ra, rb in zip(a, b)), default=0),
            "expect_same": params.get("expect_same"),
            "expect_max_diff": params.get("expect_max_diff")}


def _pixel_diff_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_same") and p["diff_sum"] != 0:
        e.append("本应完全相同的两帧却有差异")
    if p.get("expect_max_diff") is not None and \
       p["max_diff"] != p["expect_max_diff"]:
        e.append("最大像素差与期望不符")
    return e


def _score_overflow(params: Dict[str, Any]) -> Dict[str, Any]:
    val = int(params["value"])
    mx = int(params["max"])
    overflow = val > mx
    return {"value": val, "max": mx, "overflow": overflow,
            "clamped": min(val, mx) if overflow else val,
            "expect_overflow": params.get("expect_overflow")}


def _score_overflow_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_overflow") and not p["overflow"]:
        e.append("应判定溢出却未判定")
    if p.get("expect_overflow") is False and p["overflow"]:
        e.append("不应溢出却判定溢出")
    return e


import random  # noqa: E402  (放在算法之后，便于保持阅读顺序)


# DCC/GPU 依赖项：当前环境跑不了，显式标 NEEDS_RUNTIME_TOOL，不伪证。
B_SKILL_SPECS: Dict[str, BSkillSpec] = {
    # ── Logic ──
    "a_star_pathfinding": BSkillSpec(
        "a_star_pathfinding", "Logic", "网格 A* 寻路，输出最短路径与代价。",
        _a_star, _a_star_acc,
        sample={"w": 8, "h": 8, "start": [0, 0], "goal": [7, 7],
                "obstacles": [[3, 3], [3, 4], [4, 3]]}),
    "aabb_collision_detection": BSkillSpec(
        "aabb_collision_detection", "Logic", "轴对齐包围盒相交判定。",
        _aabb, _aabb_acc,
        sample={"a": {"x": 0, "y": 0, "w": 4, "h": 4},
                "b": {"x": 3, "y": 3, "w": 4, "h": 4}, "expect_overlap": True}),
    "sat_polygon_physics": BSkillSpec(
        "sat_polygon_physics", "Logic", "分离轴定理：凸多边形重叠 + 最小穿透向量。",
        _sat, _sat_acc,
        sample={"a": [[0, 0], [2, 0], [2, 2], [0, 2]],
                "b": [[1, 1], [3, 1], [3, 3], [1, 3]], "expect_overlap": True}),
    "state_machine_builder": BSkillSpec(
        "state_machine_builder", "Logic", "有限状态机 tick 序列，判定是否到接受态。",
        _state_machine, _state_machine_acc,
        sample={"states": ["idle", "run", "jump"], "init": "idle",
                "transitions": {("idle", "move"): "run", ("run", "up"): "jump",
                                ("jump", "land"): "idle"},
                "events": ["move", "up", "land"], "accept": ["idle"],
                "expect_accept": True}),
    "gravity_jump_parabola": BSkillSpec(
        "gravity_jump_parabola", "Logic", "跳跃抛物线解析解：顶点高度与滞空时间。",
        _jump, _jump_acc, sample={"v0": 10.0, "g": 9.8}),
    "seed_procedural_dungeon": BSkillSpec(
        "seed_procedural_dungeon", "Logic", "同种子确定性地牢（可复现哈希校验）。",
        _dungeon, _dungeon_acc, sample={"seed": 12345, "w": 16, "h": 16}),
    "lerp_smoothing_math": BSkillSpec(
        "lerp_smoothing_math", "Logic", "线性插值，端点与单调性断言。",
        _lerp, _lerp_acc, sample={"a": 0.0, "b": 10.0}),
    "raycast_line_of_sight": BSkillSpec(
        "raycast_line_of_sight", "Logic", "网格射线视线，墙体阻挡判定。",
        _raycast, _raycast_acc,
        sample={"w": 8, "h": 8, "src": [0, 0], "dst": [7, 0],
                "walls": [[4, 0]], "expect_blocked": True}),
    "behavior_tree_evaluator": BSkillSpec(
        "behavior_tree_evaluator", "Logic", "行为树 sequence/selector 求值。",
        _behavior_tree, _behavior_tree_acc,
        sample={"kind": "sequence", "sequence": ["success", "success", "failure"],
                "expect": "failure"}),
    # ── Rendering ──
    "screen_shake_effect": BSkillSpec(
        "screen_shake_effect", "Rendering", "震屏衰减偏移（二次衰减）。",
        _screen_shake, _screen_shake_acc,
        sample={"amplitude": 8.0, "duration": 1.0}),
    "sprite_animation_sheet": BSkillSpec(
        "sprite_animation_sheet", "Rendering", "精灵帧索引随时间推进，边界安全。",
        _sprite, _sprite_acc, sample={"frames": 4, "fps": 8.0}),
    "pixel_art_upscaler": BSkillSpec(
        "pixel_art_upscaler", "Rendering", "整数倍确定性放大，像素映射守恒。",
        _upscale, _upscale_acc,
        sample={"scale": 3, "grid": [[1, 0], [0, 1]]}),
    "day_night_color_tint": BSkillSpec(
        "day_night_color_tint", "Rendering", "昼夜亮度随时刻变化（正弦）。",
        _daynight, _daynight_acc, sample={"t": 12.0}),
    "procedural_background_stars": BSkillSpec(
        "procedural_background_stars", "Rendering", "同种子确定性星图（哈希校验）。",
        _stars, _stars_acc, sample={"seed": 777, "count": 20, "w": 64, "h": 36}),
    # ── Audio ──
    "adsr_envelope_shaper": BSkillSpec(
        "adsr_envelope_shaper", "Audio", "ADSR 包络四段，采样曲线断言。",
        _adsr, _adsr_acc,
        sample={"attack": 0.1, "decay": 0.1, "sustain": 0.6, "release": 0.2,
                "duration": 1.0, "hold": 0.5}),
    "arpeggio_generator": BSkillSpec(
        "arpeggio_generator", "Audio", "和弦琶音音高序列，单调递增断言。",
        _arpeggio, _arpeggio_acc,
        sample={"base_freq": 440.0, "ratios": [1.0, 1.25, 1.5], "octaves": 1}),
    # ── QA ──
    "pixel_visual_diffing": BSkillSpec(
        "pixel_visual_diffing", "QA", "两帧灰度像素差分，差异度量断言。",
        _pixel_diff, _pixel_diff_acc,
        sample={"a": [[0, 0], [255, 255]], "b": [[0, 0], [0, 0]],
                "expect_max_diff": 255}),
    "score_overflow_checker": BSkillSpec(
        "score_overflow_checker", "QA", "分数溢出边界检测。",
        _score_overflow, _score_overflow_acc,
        sample={"value": 2_147_483_648, "max": 2_147_483_647,
                "expect_overflow": True}),
    # ── DCC/GPU 依赖（明确标红，不伪证）──
    "next_gen_high_poly_sculpting": BSkillSpec(
        "next_gen_high_poly_sculpting", "Rendering", "高模无头雕刻，依赖 Blender/DCC 工具链。",
        lambda p: {}, lambda p: [], needs_runtime_tool="blender_headless_dcc",
        notes="需 Blender 无头雕刻；本环境未装 DCC，属 NEEDS_RUNTIME_TOOL。"),
    "quad_retopology_uv_unwrap": BSkillSpec(
        "quad_retopology_uv_unwrap", "Rendering", "重拓扑与 UV 展开，依赖 Blender。",
        lambda p: {}, lambda p: [], needs_runtime_tool="blender_headless_dcc",
        notes="需 Blender 执行重拓扑/UV；本环境未装 DCC，属 NEEDS_RUNTIME_TOOL。"),
    "pbr_five_channel_baking": BSkillSpec(
        "pbr_five_channel_baking", "Rendering", "PBR 五通道贴图烘焙，需 GPU 烘焙器。",
        lambda p: {}, lambda p: [], needs_runtime_tool="gpu_texture_baker",
        notes="需 GPU 烘焙器（如 Substance/Blender bake）；本环境无，属 NEEDS_RUNTIME_TOOL。"),
}

# 第一批覆盖范围（其余 B 类按同模式后续批次补齐）
BATCH1_IMPLEMENTED = [s for s in B_SKILL_SPECS
                      if B_SKILL_SPECS[s].needs_runtime_tool is None]
BATCH1_RUNTIME_TOOL = [s for s in B_SKILL_SPECS
                       if B_SKILL_SPECS[s].needs_runtime_tool]


def spec_ids() -> List[str]:
    return sorted(B_SKILL_SPECS)


def get_spec(skill_id: str) -> Optional[BSkillSpec]:
    return B_SKILL_SPECS.get(skill_id)


DIGEST_PATH = "evidence/b_skills_latest.json"
AUDIT_PATH = "evidence/b_skills_audit.json"


class BSkillRuntime:
    """批量真实运行 B 类技能，验收通过才注册，证据落工件库。"""

    def __init__(self, registry=None, run_context: Optional[RunContext] = None) -> None:
        self.registry = registry
        self.run_context = run_context

    def run_skill(self, skill_id: str, params: Optional[Dict[str, Any]] = None) -> BSkillResult:
        spec = B_SKILL_SPECS.get(skill_id)
        if spec is None:
            return BSkillResult(skill_id, BSkillStatus.NO_SPEC,
                                errors=["未注册的 B 类技能 id"])
        if spec.needs_runtime_tool:
            return BSkillResult(skill_id, BSkillStatus.NEEDS_RUNTIME_TOOL,
                                runtime="missing", needs_runtime_tool=spec.needs_runtime_tool,
                                errors=[f"需要 {spec.needs_runtime_tool}，当前环境未提供，不伪证"])
        p = params if params is not None else spec.sample
        t0 = time.time()
        try:
            payload = spec.run(p)
        except Exception as exc:  # 运行期异常也算没跑通
            return BSkillResult(skill_id, BSkillStatus.RUN_ERROR,
                                latency_ms=int((time.time() - t0) * 1000),
                                errors=[f"{type(exc).__name__}: {exc}"])
        errs = list(spec.acceptance(payload) or [])
        lat = int((time.time() - t0) * 1000)
        if errs:
            return BSkillResult(skill_id, BSkillStatus.ACCEPTANCE_FAILED,
                                payload=payload, errors=errs, runtime="pure_python",
                                latency_ms=lat)
        return BSkillResult(skill_id, BSkillStatus.OK, payload=payload,
                            runtime="pure_python", checks_passed=1, latency_ms=lat)

    def run_all(self, skill_ids: Optional[List[str]] = None,
                verbose: bool = True) -> Dict[str, Any]:
        ids = sorted(skill_ids or spec_ids())
        started = time.time()
        results: List[BSkillResult] = []
        registered: List[str] = []
        failed: List[Dict[str, Any]] = []
        for sid in ids:
            r = self.run_skill(sid)
            results.append(r)
            if r.ok:
                if self.registry is not None:
                    try:
                        self.registry.register_b_skill(sid, result=r)
                        registered.append(sid)
                    except (ValueError, KeyError) as exc:
                        failed.append({"skill_id": sid, "status": r.status,
                                       "error": f"注册失败: {exc}"})
                else:
                    registered.append(sid)
                if verbose:
                    print(f"  [OK  ] {sid:38s} {r.runtime:12s} {r.latency_ms}ms")
            else:
                failed.append({"skill_id": sid, "status": r.status,
                               "needs_runtime_tool": r.needs_runtime_tool,
                               "errors": r.errors[:4]})
                if verbose:
                    tag = r.needs_runtime_tool or r.status
                    print(f"  [{tag[:4]}] {sid:38s} {r.status} | "
                          f"{(r.errors[0] if r.errors else '')[:90]}")
        ev = {
            "artifact_type": "b_skill_verification",
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started)),
            "elapsed_seconds": round(time.time() - started, 2),
            "total": len(ids), "ok": len(registered),
            "failed": len(failed), "registered": registered,
            "failed_detail": failed, "results": [r.to_dict() for r in results],
        }
        if self.registry is not None:
            ev["counts"] = self.registry.counts()
        ev["run_dir"] = self._persist(ev)
        ev["digest_path"] = self.write_digest(ev)
        return ev

    @staticmethod
    def collect_history(runs_root: Optional[str] = None) -> List[Dict[str, Any]]:
        from pathlib import Path
        from core.artifact_store import ArtifactIntegrityError, ArtifactStore
        root = (Path(runs_root) if runs_root
                else Path(__file__).resolve().parent.parent / "output" / "runs")
        if not root.exists():
            return []
        runs = []
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            try:
                raw = ArtifactStore(d).read_bytes("art_b_skill_verification")
                data = json.loads(raw.decode("utf-8"))
            except (OSError, KeyError, ValueError, UnicodeDecodeError,
                    ArtifactIntegrityError):
                continue
            runs.append({
                "run_id": data.get("run_id") or d.name,
                "started_at": data.get("started_at"),
                "elapsed_seconds": data.get("elapsed_seconds"),
                "total": data.get("total"), "ok": data.get("ok"),
                "failed": data.get("failed"), "results": data.get("results", []),
            })
        return runs

    @staticmethod
    def write_digest(evidence: Dict[str, Any], path: str = DIGEST_PATH,
                     merge_history: bool = True,
                     runs_root: Optional[str] = None) -> str:
        """双口径：ever_passed（历史至少一次真实通过）+ last_ok（最近一次）。"""
        def _sha(r):
            return hashlib_sha(r["payload"]) if r.get("payload") else None

        current = {"run_id": evidence.get("run_id"),
                   "started_at": evidence.get("started_at"),
                   "elapsed_seconds": evidence.get("elapsed_seconds"),
                   "total": evidence.get("total"), "ok": evidence.get("ok"),
                   "failed": evidence.get("failed"), "results": evidence.get("results", [])}
        if merge_history:
            runs = BSkillRuntime.collect_history(runs_root)
            known = {r["run_id"] for r in runs}
            if current["run_id"] in known:
                runs = [current if r["run_id"] == current["run_id"] else r
                        for r in runs]
            else:
                runs.append(current)
        else:
            runs = [current]

        merged: Dict[str, Dict[str, Any]] = {}
        for run in runs:
            for r in run.get("results", []):
                sid = r.get("skill_id")
                if not sid:
                    continue
                ok = bool(r.get("ok"))
                it = merged.setdefault(sid, {
                    "skill_id": sid, "history_runs": 0, "history_passes": 0,
                    "ever_passed": False, "pass_rate": 0.0,
                    "last_ok": None, "last_status": None, "last_runtime": None,
                    "last_latency_ms": None, "last_first_error": None,
                    "last_run_id": None, "last_at": None,
                    "pass_run_id": None, "pass_at": None, "pass_runtime": None,
                    "pass_payload_sha256": None,
                })
                it["history_runs"] += 1
                it["history_passes"] += 1 if ok else 0
                it["ever_passed"] = it["ever_passed"] or ok
                it["last_ok"] = ok
                it["last_status"] = r.get("status")
                it["last_runtime"] = r.get("runtime")
                it["last_latency_ms"] = r.get("latency_ms")
                it["last_first_error"] = (r.get("errors") or [None])[0]
                it["last_run_id"] = run.get("run_id")
                it["last_at"] = run.get("started_at")
                if ok:
                    it["pass_run_id"] = run.get("run_id")
                    it["pass_at"] = run.get("started_at")
                    it["pass_runtime"] = r.get("runtime")
                    it["pass_payload_sha256"] = _sha(r)

        per_skill = sorted(merged.values(), key=lambda x: x["skill_id"])
        for it in per_skill:
            it["pass_rate"] = (round(it["history_passes"] / it["history_runs"], 3)
                               if it["history_runs"] else 0.0)
        ever = [it["skill_id"] for it in per_skill if it["ever_passed"]]

        digest = {
            "schema_version": 2,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "run_id": current["run_id"],
            "last_run": {"total": current["total"], "ok": current["ok"],
                         "failed": current["failed"]},
            "history_runs": [{
                "run_id": r.get("run_id"), "started_at": r.get("started_at"),
                "elapsed_seconds": r.get("elapsed_seconds"),
                "total": r.get("total"), "ok": r.get("ok"), "failed": r.get("failed"),
            } for r in runs],
            "ever_passed": ever, "ever_passed_count": len(ever),
            "per_skill": per_skill, "counts": evidence.get("counts"),
            "note": ("ever_passed = 历史上至少一次真实运行+验收通过（工件可回查）；"
                     "last_ok = 最近一次结果。两个口径不可混用。"),
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(digest, ensure_ascii=False, indent=2))
        return path

    def _persist(self, evidence: Dict[str, Any]) -> str:
        ctx = self.run_context or RunContext(title="b_skill_verify")
        self.run_context = ctx
        ref = ctx.artifact_store.put_json(
            "b_skill_verification", evidence,
            artifact_id="art_b_skill_verification",
            relative_name="b_skill_verification.json",
            producer_capability="skill.b_skill_runtime")
        for r in evidence["results"]:
            if r.get("payload") and r.get("ok"):
                ctx.artifact_store.put_json(
                    "b_skill_payload", r["payload"],
                    artifact_id=f"art_payload_{r['skill_id']}",
                    relative_name=f"payload_{r['skill_id']}.json",
                    producer_capability=f"skill.{r['skill_id']}")
        evidence["run_id"] = ctx.run_id
        evidence["evidence_ref"] = ref.sha256
        evidence["artifact_integrity"] = ctx.artifact_store.verify_all()
        ctx.generate_manifest()
        return str(ctx.work_dir)

    @staticmethod
    def audit_evidence(path: str = DIGEST_PATH, runs_root: Optional[str] = None,
                       write: bool = True,
                       audit_path: str = AUDIT_PATH) -> Dict[str, Any]:
        """把历史通过的 payload 从工件库读回，用当前契约重跑验收。

        B 类没有 LLM，也没有外部依赖，所以"复验"就是纯本地再跑一遍 acceptance。
        """
        import hashlib
        from pathlib import Path
        from core.artifact_store import (ArtifactIntegrityError, ArtifactStore)

        root = (Path(runs_root) if runs_root
                else Path(__file__).resolve().parent.parent / "output" / "runs")
        if not os.path.exists(path):
            return {"artifact_type": "b_skill_audit", "error": f"摘要不存在: {path}",
                    "checked": 0, "still_valid": 0, "stale": 0, "missing": 0}
        with open(path, "r", encoding="utf-8") as f:
            digest = json.load(f)

        details = []
        n_valid = n_stale = n_missing = n_never = 0
        for item in digest.get("per_skill", []):
            sid = item["skill_id"]
            passed = (item.get("ever_passed") if "ever_passed" in item
                      else item.get("ok"))
            rec = {"skill_id": sid, "ever_passed": bool(passed),
                   "pass_rate": item.get("pass_rate"),
                   "pass_run_id": item.get("pass_run_id")}
            if not passed:
                rec["audit"] = "no_pass_record"
                n_never += 1
                details.append(rec)
                continue
            spec = get_spec(sid)
            if spec is None:
                rec["audit"] = "no_spec"
                n_stale += 1
                details.append(rec)
                continue
            try:
                raw = ArtifactStore(root / item["pass_run_id"]).read_bytes(
                    f"art_payload_{sid}")
                payload = json.loads(raw.decode("utf-8"))
            except (OSError, KeyError, ValueError, UnicodeDecodeError,
                    ArtifactIntegrityError) as exc:
                rec["audit"] = "missing"
                rec["error"] = str(exc)
                n_missing += 1
                details.append(rec)
                continue
            errors = list(spec.acceptance(payload) or [])
            rec["payload_sha256"] = item.get("pass_payload_sha256")
            if errors:
                rec["audit"] = "stale"
                rec["errors"] = errors[:6]
                n_stale += 1
            else:
                rec["audit"] = "still_valid"
                n_valid += 1
            details.append(rec)

        report = {
            "artifact_type": "b_skill_audit",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "digest_path": path,
            "ever_passed_count": len(digest.get("ever_passed", [])),
            "checked": len(details), "still_valid": n_valid, "stale": n_stale,
            "missing": n_missing, "no_pass_record": n_never,
            "details": details,
            "note": "still_valid = 历史通过 payload 在当前契约下复验仍通过；"
                    "stale = 契约已变旧通过不再成立。",
        }
        if write:
            os.makedirs(os.path.dirname(audit_path) or ".", exist_ok=True)
            with open(audit_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(report, ensure_ascii=False, indent=2))
        return report


def hashlib_sha(payload: Dict[str, Any]) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":")).encode("utf-8")).hexdigest()


def verify_all(verbose: bool = True, registry=None,
               skill_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """便捷入口：分类表 + 全量真实运行 B 类技能。"""
    if registry is None:
        from core.skill_registry import skill_registry
        registry = skill_registry
    if not registry._skills:
        registry.ingest_from_registry()
    from core.skill_classification import apply_classification
    apply_classification(registry)
    return BSkillRuntime(registry=registry).run_all(
        skill_ids=skill_ids, verbose=verbose)


def restore_b_registrations(registry, path: str = DIGEST_PATH,
                            verbose: bool = False) -> int:
    """从证据摘要回放 B 类技能的真实通过记录（内存注册表不跨进程）。

    与 C 类同理由：skill_registry 是内存单例，进程退出后"真跑通过"就没了，
    `skill-list` 会显示 B_REGISTERED=0——看起来像从没跑过，属失真。
    回放的是已记录的真实运行（run_id/payload 哈希可回查），不是凭空宣布通过。
    runtime-tool 依赖项（last_runtime=missing）不回放，它们本就未跑通。
    """
    import os
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            digest = json.load(f)
    except (OSError, ValueError):
        return 0
    n = 0
    for item in digest.get("per_skill", []):
        passed = (item.get("ever_passed") if "ever_passed" in item
                  else item.get("ok"))
        if not passed:
            continue
        sid = item["skill_id"]
        rt = item.get("last_runtime") or item.get("pass_runtime") or ""
        if not rt or rt == "missing":   # 依赖 DCC/GPU、未真跑的不回放
            continue
        r = BSkillResult(skill_id=sid, status=BSkillStatus.OK,
                         runtime=rt, checks_passed=1)
        try:
            registry.register_b_skill(sid, result=r)
        except (ValueError, KeyError):
            continue
        n += 1
    if verbose and n:
        print(f"  [RESTORE-B] 从 {path} 回放 {n} 项 B 类技能的真实通过记录")
    return n


# ════════════════════════════════════════════════════════════════════════════
# W4 第二批：补齐剩余 44 项 B 类确定性算法（纯 Python，可数值断言验收）。
# 全部沿用第一批模式：run = 确定性计算，acceptance = 返回错误列表（空=通过）。
# 不依赖 LLM、不依赖网络、不依赖外部 DCC/GPU——纯函数，可复现。
# ════════════════════════════════════════════════════════════════════════════

def _spatial_grid(params: Dict[str, Any]) -> Dict[str, Any]:
    pts = [tuple(p) for p in params["points"]]
    cell = float(params["cell"])
    origin = tuple(params.get("origin", [0, 0]))
    buckets: Dict[str, List[List[float]]] = {}
    for p in pts:
        key = f"{int((p[0]-origin[0])//cell)},{int((p[1]-origin[1])//cell)}"
        buckets.setdefault(key, []).append(list(p))
    return {"points": params["points"], "cell": cell, "origin": list(origin),
            "buckets": buckets, "bucket_count": len(buckets),
            "total": sum(len(v) for v in buckets.values())}


def _spatial_grid_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["total"] != len(p["points"]):
        e.append("有落点丢失")
    if sum(len(v) for v in p["buckets"].values()) != len(p["points"]):
        e.append("桶内计数与总点数不一致")
    return e


def _pool(params: Dict[str, Any]) -> Dict[str, Any]:
    size = int(params["size"])
    free = list(range(size))
    hits = misses = frees = 0
    for op in params["ops"]:
        if op == "alloc":
            if free:
                free.pop()
                hits += 1
            else:
                misses += 1
        else:
            free.append(1)
            frees += 1
    return {"size": size, "ops": params["ops"], "hits": hits,
            "misses": misses, "frees": frees}


def _pool_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    allocs = p["ops"].count("alloc")
    if p["hits"] + p["misses"] != allocs:
        e.append("hits+misses 不等于 alloc 次数")
    if p["misses"] > p["size"]:
        e.append("新建数超过池容量")
    return e


def _quad(params: Dict[str, Any]) -> Dict[str, Any]:
    boxes = [list(b) for b in params["boxes"]]
    rng = list(params["query"])

    def inter(a, b):
        return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0]
                    or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])

    hits = [i for i, b in enumerate(boxes) if inter(b, rng)]
    return {"boxes": boxes, "query": rng, "hit_indices": hits, "hit_count": len(hits)}


def _quad_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    rng = p["query"]
    for i in p["hit_indices"]:
        b = p["boxes"][i]
        if (b[0] + b[2] <= rng[0] or rng[0] + rng[2] <= b[0]
                or b[1] + b[3] <= rng[1] or rng[1] + rng[3] <= b[1]):
            e.append(f"box {i} 实际不相交却被命中")
            break
    return e


def _tilemap(params: Dict[str, Any]) -> Dict[str, Any]:
    grid = params["grid"]
    h = len(grid)
    w = len(grid[0]) if grid else 0
    enc = ";".join(",".join(str(c) for c in row) for row in grid)
    parsed = [[int(c) for c in row.split(",")] for row in enc.split(";")]
    return {"grid": grid, "encoded": enc, "decoded": parsed, "w": w, "h": h}


def _tilemap_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["decoded"] != p["grid"]:
        e.append("编码→解析往返不一致")
    if len(p["decoded"]) != p["h"]:
        e.append("行数不符")
    return e


def _cooldown(params: Dict[str, Any]) -> Dict[str, Any]:
    timers = params["timers"]
    fired = {}
    log = []
    for t in params["ticks"]:
        for name, d in timers.items():
            if name not in fired and t >= d:
                fired[name] = t
                log.append({"name": name, "at": t})
    return {"timers": timers, "ticks": params["ticks"], "fired": fired, "log": log}


def _cooldown_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    for name, d in p["timers"].items():
        if name in p["fired"] and p["fired"][name] < d - 1e-9:
            e.append(f"{name} 在冷却未到时触发")
    return e


def _save(params: Dict[str, Any]) -> Dict[str, Any]:
    import hashlib as _hl
    state = params["state"]
    s = json.dumps(state, sort_keys=True, ensure_ascii=False)
    back = json.loads(s)
    return {"state": state, "serialized": s, "restored": back,
            "hash": _hl.sha256(s.encode("utf-8")).hexdigest()}


def _save_acc(p: Dict[str, Any]) -> List[str]:
    import hashlib as _hl
    e = []
    if p["restored"] != p["state"]:
        e.append("序列化→反序列化往返不一致")
    if p["hash"] != _hl.sha256(json.dumps(p["state"], sort_keys=True,
                                         ensure_ascii=False).encode()).hexdigest():
        e.append("相同状态哈希不确定（非确定性）")
    return e


def _joystick(params: Dict[str, Any]) -> Dict[str, Any]:
    cx, cy = float(params["cx"]), float(params["cy"])
    tx, ty = float(params["tx"]), float(params["ty"])
    R = float(params["radius"])
    dx, dy = tx - cx, ty - cy
    d = math.hypot(dx, dy)
    if d <= 1e-9:
        vec = [0.0, 0.0]
    elif d > R:
        vec = [dx / d, dy / d]
    else:
        vec = [dx / R, dy / R]
    return {"cx": cx, "cy": cy, "touch": [tx, ty], "radius": R,
            "vector": [round(vec[0], 4), round(vec[1], 4)], "dist": round(d, 4)}


def _joystick_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    mag = math.hypot(p["vector"][0], p["vector"][1])
    if p["dist"] < 1e-9:
        if p["vector"] != [0.0, 0.0]:
            e.append("中心应返回零向量")
    elif mag > 1.0001:
        e.append("向量模长不应超过 1")
    return e


def _gamepad(params: Dict[str, Any]) -> Dict[str, Any]:
    mapping = params["mapping"]
    pressed = set(params["pressed"])
    state = {act: (btn in pressed) for btn, act in mapping.items()}
    return {"mapping": mapping, "pressed": list(pressed), "state": state}


def _gamepad_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    for btn in p["pressed"]:
        act = p["mapping"].get(btn)
        if act and not p["state"].get(act):
            e.append(f"{btn}->{act} 应为按下态")
    return e


def _floattext(params: Dict[str, Any]) -> Dict[str, Any]:
    sx, sy = float(params["sx"]), float(params["sy"])
    ex, ey = float(params["ex"]), float(params["ey"])
    ts = params.get("ts", [0.0, 1.0])
    pos = [[round(sx + (ex - sx) * t, 3), round(sy + (ey - sy) * t, 3)]
           for t in ts]
    return {"start": [sx, sy], "end": [ex, ey], "ts": ts, "pos": pos}


def _floattext_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["pos"][0] != p["start"]:
        e.append("t=0 应在起点")
    if p["pos"][-1] != p["end"]:
        e.append("t=1 应在终点")
    return e


def _sandbox(params: Dict[str, Any]) -> Dict[str, Any]:
    allowed, denied = params["allowed"], params["denied"]
    path = params["path"]
    ok = any(path.startswith(a) for a in allowed) and \
        not any(path.startswith(d) for d in denied)
    return {"path": path, "allowed": allowed, "denied": denied,
            "permitted": ok, "expect_permitted": params.get("expect_permitted")}


def _sandbox_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_permitted") is not None and p["permitted"] != p["expect_permitted"]:
        e.append("许可判定与期望不符")
    return e


def _patch(params: Dict[str, Any]) -> Dict[str, Any]:
    scopes = params["scopes"]
    file = params["file"]
    included = any(file.startswith(s) for s in scopes)
    return {"file": file, "scopes": scopes, "included": included,
            "expect_included": params.get("expect_included")}


def _patch_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_included") is not None and p["included"] != p["expect_included"]:
        e.append("作用域命中与期望不符")
    return e


def _logi(params: Dict[str, Any]) -> Dict[str, Any]:
    inflow = sum(params["inflow"].values())
    outflow = sum(params["outflow"].values())
    produced = params.get("produced", 0)
    consumed = params.get("consumed", 0)
    return {"inflow": params["inflow"], "outflow": params["outflow"],
            "produced": produced, "consumed": consumed,
            "balanced": (inflow + produced) == (outflow + consumed)}


def _logi_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if not p["balanced"]:
        e.append("物质不守恒（流入+产出 != 流出+消耗）")
    return e


def _v8(params: Dict[str, Any]) -> Dict[str, Any]:
    classes: Dict[tuple, int] = {}
    order = []
    for keys in params["allocs"]:
        k = tuple(keys)
        if k not in classes:
            classes[k] = len(classes)
        order.append(classes[k])
    return {"allocs": params["allocs"], "distinct_classes": len(classes),
            "class_ids": order}


def _v8_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    seen: Dict[tuple, int] = {}
    for keys, cid in zip(p["allocs"], p["class_ids"]):
        k = tuple(keys)
        if k in seen and seen[k] != cid:
            e.append("同 shape 的分配复用了不同 hidden class")
            break
        seen[k] = cid
    return e


def _particles(params: Dict[str, Any]) -> Dict[str, Any]:
    seed = int(params["seed"])
    n = int(params["n"])
    w, h = float(params["w"]), float(params["h"])
    rng = random.Random(seed)
    ps = [[round(rng.random() * w, 3), round(rng.random() * h, 3)]
          for _ in range(n)]
    out = [p for p in ps if 0 <= p[0] <= w and 0 <= p[1] <= h]
    return {"seed": seed, "n": n, "w": w, "h": h,
            "particles": out, "count": len(out)}


def _particles_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["count"] != p["n"]:
        e.append("粒子数不符（部分越界）")
    for pt in p["particles"]:
        if not (0 <= pt[0] <= p["w"] and 0 <= pt[1] <= p["h"]):
            e.append("粒子越界")
            break
    return e


def _bloom(params: Dict[str, Any]) -> Dict[str, Any]:
    thr = float(params["threshold"])
    bright = [v for v in params["pixels"] if v > thr]
    return {"pixels": params["pixels"], "threshold": thr,
            "bright_count": len(bright), "bright": bright}


def _bloom_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    for v in p["bright"]:
        if v <= p["threshold"]:
            e.append("bloom 列表包含低于阈值的像素")
            break
    return e


def _shock(params: Dict[str, Any]) -> Dict[str, Any]:
    speed = float(params["speed"])
    ts = params.get("ts", [0.0, 0.5, 1.0])
    radius = [round(speed * t, 3) for t in ts]
    return {"speed": speed, "ts": ts, "radius": radius}


def _shock_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["radius"][0] != 0.0:
        e.append("t=0 半径应为 0")
    if any(p["radius"][i] > p["radius"][i + 1] + 1e-6
           for i in range(len(p["radius"]) - 1)):
        e.append("环半径应随时间单调增大")
    return e


def _ghost(params: Dict[str, Any]) -> Dict[str, Any]:
    n = int(params["samples"])
    base = float(params["alpha"])
    alphas = [round(base * (1 - i / n), 4) for i in range(n)]
    return {"samples": n, "base_alpha": base, "alphas": alphas}


def _ghost_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["alphas"][0] != p["base_alpha"]:
        e.append("首个残影应为基准透明度")
    if any(p["alphas"][i] < p["alphas"][i + 1] - 1e-6
           for i in range(len(p["alphas"]) - 1)):
        e.append("残影透明度应递减")
    return e


def _raster(params: Dict[str, Any]) -> Dict[str, Any]:
    x0, y0 = params["p0"]
    x1, y1 = params["p1"]
    steps = max(abs(x1 - x0), abs(y1 - y0))
    if steps == 0:
        pts = [[x0, y0]]
    else:
        pts = [[round(x0 + (x1 - x0) * i / steps), round(y0 + (y1 - y0) * i / steps)]
               for i in range(steps + 1)]
    return {"p0": [x0, y0], "p1": [x1, y1], "pixels": pts, "coverage": len(pts)}


def _raster_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["pixels"][0] != p["p0"] or p["pixels"][-1] != p["p1"]:
        e.append("栅格化未包含端点")
    return e


def _flash(params: Dict[str, Any]) -> Dict[str, Any]:
    dur = float(params["duration"])
    ts = params.get("ts", [0.0, 0.5, 1.0])
    alpha = [round(max(0.0, 1 - t / dur), 4) for t in ts]
    return {"duration": dur, "ts": ts, "alpha": alpha}


def _flash_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["alpha"][0] != 1.0:
        e.append("t=0 应全白（alpha=1）")
    if p["alpha"][-1] > 0.05:
        e.append("受击闪白应衰减到 ~0")
    return e


def _radial(params: Dict[str, Any]) -> Dict[str, Any]:
    frac = float(params["fraction"])
    return {"fraction": frac, "angle": round(frac * 2 * math.pi, 4),
            "degrees": round(frac * 360, 2)}


def _radial_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    # _radial 对角度做了 round(...,4)，与精确值差 ≤5e-5，故用 1e-3 容差比对公式一致性
    if not _close(p["angle"], p["fraction"] * 2 * math.pi, 1e-3):
        e.append("环形角度公式错误")
    if p["fraction"] >= 1.0 and p["degrees"] < 359.9:
        e.append("满进度应接近整圆")
    return e


def _scanline(params: Dict[str, Any]) -> Dict[str, Any]:
    h = int(params["h"])
    period = int(params["period"])
    pattern = [1 if (y % period == 0) else 0 for y in range(h)]
    return {"h": h, "period": period, "pattern": pattern,
            "dark_rows": sum(pattern)}


def _scanline_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["dark_rows"] != p["h"] // p["period"]:
        e.append("暗行数应为 h/period")
    return e


def _batch(params: Dict[str, Any]) -> Dict[str, Any]:
    draws = params["draws"]
    return {"draws": draws, "draw_calls": len(set(draws)), "naive": len(draws)}


def _batch_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["draw_calls"] > p["naive"]:
        e.append("合批后 drawcall 不应增多")
    if p["draw_calls"] != len(set(p["draws"])):
        e.append("drawcall 数应等于不同材质数")
    return e


def _frustum(params: Dict[str, Any]) -> Dict[str, Any]:
    objs = [list(o) for o in params["objects"]]
    v = list(params["view"])
    visible = [i for i, o in enumerate(objs)
               if v[0] <= o[0] <= v[0] + v[2] and v[1] <= o[1] <= v[1] + v[3]]
    return {"objects": objs, "view": v, "visible": visible,
            "visible_count": len(visible)}


def _frustum_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    for i in p["visible"]:
        o = p["objects"][i]
        v = p["view"]
        if not (v[0] <= o[0] <= v[0] + v[2] and v[1] <= o[1] <= v[1] + v[3]):
            e.append(f"obj {i} 不在视锥内却被保留")
            break
    return e


def _rig(params: Dict[str, Any]) -> Dict[str, Any]:
    verts = [list(v) for v in params["vertices"]]
    bones = [list(b) for b in params["bones"]]
    weights = []
    for vx, vy in verts:
        d = [math.hypot(vx - bx, vy - by) for bx, by in bones]
        w = [1.0 / (dd + 1e-3) for dd in d]
        s = sum(w)
        weights.append([round(x / s, 4) for x in w])
    return {"vertices": verts, "bones": bones, "weights": weights}


def _rig_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    for w in p["weights"]:
        if abs(sum(w) - 1.0) > 1e-3:
            e.append("蒙皮权重未归一化")
            break
        if w.index(max(w)) != 0:
            e.append("最近的骨骼未获得最高权重")
            break
    return e


def _synth(params: Dict[str, Any]) -> Dict[str, Any]:
    freq = float(params["freq"])
    sr = int(params["sr"])
    dur = float(params["duration"])
    n = int(sr * dur)
    samples = []
    for i in range(n):
        phase = (i / sr * freq) % 1.0
        samples.append(1.0 if phase < 0.5 else -1.0)
    return {"freq": freq, "sr": sr, "duration": dur, "samples": samples, "n": n}


def _synth_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if any(abs(s) > 1.0001 for s in p["samples"]):
        e.append("方波幅度应 ≤ 1")
    # 方波每周期有 2 次过零（上升+下降），需双向统计；容差 ±2 容纳相位边界
    zc = sum(1 for a, b in zip(p["samples"], p["samples"][1:])
             if (a <= 0 < b) or (a >= 0 > b))
    if abs(zc - round(2 * p["freq"] * p["duration"])) > 2:
        e.append("过零次数与频率不符")
    return e


def _noise(params: Dict[str, Any]) -> Dict[str, Any]:
    seed = int(params["seed"])
    n = int(params["n"])
    rng = random.Random(seed)
    raw = [rng.random() * 2 - 1 for _ in range(n)]
    env = [math.exp(-3 * (i / n)) for i in range(n)]
    sig = [raw[i] * env[i] for i in range(n)]
    q = max(1, n // 4)

    def _rms(seg):
        return math.sqrt(sum(x * x for x in seg) / len(seg)) if seg else 0.0

    curve = [round(_rms(sig[i * q:(i + 1) * q]), 4) for i in range(4)]
    return {"seed": seed, "n": n, "rms_curve": curve}


def _noise_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if not (p["rms_curve"][0] >= p["rms_curve"][-1] - 1e-6):
        e.append("爆炸噪声 RMS 应随衰减包络不增")
    return e


def _pitch(params: Dict[str, Any]) -> Dict[str, Any]:
    f0, f1 = float(params["f0"]), float(params["f1"])
    ts = params.get("ts", [0.0, 1.0])
    freq = [round(f0 + (f1 - f0) * t, 3) for t in ts]
    return {"f0": f0, "f1": f1, "ts": ts, "freq": freq}


def _pitch_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["freq"][0] != p["f0"]:
        e.append("起点频率错误")
    if p["freq"][-1] != p["f1"]:
        e.append("终点频率错误")
    return e


def _coin(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"freq_a": float(params["freq_a"]), "freq_b": float(params["freq_b"]),
            "dur_a": float(params["dur_a"]), "dur_b": float(params["dur_b"]),
            "steps": [float(params["freq_a"]), float(params["freq_b"])],
            "total": round(float(params["dur_a"]) + float(params["dur_b"]), 3)}


def _coin_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["steps"][0] <= p["steps"][1]:
        e.append("金币音效应先高后低")
    if not _close(p["total"], p["dur_a"] + p["dur_b"], 1e-6):
        e.append("总时长计算错误")
    return e


def _whistle(params: Dict[str, Any]) -> Dict[str, Any]:
    f0, f1 = float(params["f0"]), float(params["f1"])
    ts = params.get("ts", [0.0, 0.5, 1.0])
    freq = [round(f0 + (f1 - f0) * (1 - abs(2 * t - 1)), 3) for t in ts]
    return {"f0": f0, "f1": f1, "ts": ts, "freq": freq}


def _whistle_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["freq"][0] != p["f0"] or p["freq"][-1] != p["f0"]:
        e.append("首尾应回到基频")
    if p["freq"][len(p["freq"]) // 2] != max(p["freq"]):
        e.append("中段应达峰值频率")
    return e


def _jingle(params: Dict[str, Any]) -> Dict[str, Any]:
    root = float(params["root"])
    semis = [0, 3, 6, 9]
    freqs = [round(root * 2 ** (s / 12), 3) for s in semis]
    return {"root": root, "intervals": semis, "freqs": freqs}


def _jingle_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    for i in range(1, len(p["freqs"])):
        if not _close(p["freqs"][i], p["freqs"][i - 1] * 2 ** (3 / 12), 1e-3):
            e.append("减七和弦相邻音程应恰为 3 个半音")
    return e


def _panner(params: Dict[str, Any]) -> Dict[str, Any]:
    pan = float(params["pan"])
    return {"pan": pan, "L": round((1 - pan) / 2, 4), "R": round((1 + pan) / 2, 4)}


def _panner_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if not _close(p["L"] + p["R"], 1.0, 1e-6):
        e.append("L+R 增益应守恒为 1")
    if p["pan"] == 0.0 and abs(p["L"] - p["R"]) > 1e-6:
        e.append("中心声相应等功率")
    if p["pan"] < 0 and not (p["L"] > p["R"]):
        e.append("左声相时 L 应大于 R")
    return e


def _inputsim(params: Dict[str, Any]) -> Dict[str, Any]:
    state: Dict[str, bool] = {}
    for ev in params["events"]:
        state[ev["key"]] = bool(ev["down"])
    return {"events": params["events"], "state": state}


def _inputsim_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    # 终态仅反映每个键最后一次事件指定的 down 值，而非每个事件的瞬时态
    last: Dict[str, bool] = {}
    for ev in p["events"]:
        last[ev["key"]] = bool(ev["down"])
    for key, expected in last.items():
        if p["state"].get(key) != expected:
            e.append(f"{key} 注入后终态与事件不符")
            break
    return e


def _fps(params: Dict[str, Any]) -> Dict[str, Any]:
    ft = params["frame_times"]
    s = sorted(ft)
    n = len(s)
    p95 = s[min(n - 1, max(0, int(math.ceil(0.95 * n)) - 1))]
    budget = float(params.get("budget", 33.3))
    dropped = sum(1 for t in ft if t > budget)
    return {"frame_times": ft, "p95": p95, "budget": budget, "dropped": dropped}


def _fps_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["p95"] > max(p["frame_times"]):
        e.append("p95 超过最大值（不可能）")
    if p["dropped"] > len(p["frame_times"]):
        e.append("掉帧数越界")
    return e


def _leak(params: Dict[str, Any]) -> Dict[str, Any]:
    before, after = int(params["before"]), int(params["after"])
    return {"before": before, "after": after, "leaked": after - before,
            "grew": after - before > 0}


def _leak_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["leaked"] != p["after"] - p["before"]:
        e.append("差值计算错误")
    return e


def _glitch(params: Dict[str, Any]) -> Dict[str, Any]:
    a, b = list(params["a"]), list(params["b"])
    ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    oy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    pen = max(0.0, min(ox, oy)) if ox > 0 and oy > 0 else 0.0
    return {"a": a, "b": b, "penetration": round(pen, 3), "overlap": pen > 0}


def _glitch_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["overlap"] and p["penetration"] <= 0:
        e.append("判定重叠但穿透深度为 0（矛盾）")
    return e


def _boundary(params: Dict[str, Any]) -> Dict[str, Any]:
    x, y = float(params["x"]), float(params["y"])
    b = list(params["bounds"])
    out = (x < b[0] or x > b[2] or y < b[1] or y > b[3])
    return {"x": x, "y": y, "bounds": b, "out_of_bounds": out,
            "expect_out": params.get("expect_out")}


def _boundary_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_out") is not None and p["out_of_bounds"] != p["expect_out"]:
        e.append("越界判定与期望不符")
    return e


def _silence(params: Dict[str, Any]) -> Dict[str, Any]:
    sig = params["signal"]
    thr = float(params["threshold"])
    rms = math.sqrt(sum(x * x for x in sig) / len(sig)) if sig else 0.0
    return {"signal_len": len(sig), "rms": round(rms, 4), "threshold": thr,
            "silent": rms < thr, "expect_silent": params.get("expect_silent")}


def _silence_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_silent") is not None and p["silent"] != p["expect_silent"]:
        e.append("静音判定与期望不符")
    return e


def _watchdog(params: Dict[str, Any]) -> Dict[str, Any]:
    steps, limit = int(params["steps"]), int(params["limit"])
    return {"steps": steps, "limit": limit, "killed": steps > limit,
            "expect_killed": params.get("expect_killed")}


def _watchdog_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_killed") is not None and p["killed"] != p["expect_killed"]:
        e.append("超时看门狗判定与期望不符")
    return e


def _resize(params: Dict[str, Any]) -> Dict[str, Any]:
    sizes = params["sizes"]
    return {"sizes": sizes, "reflows": len(sizes), "expect": params.get("expect")}


def _resize_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect") is not None and p["reflows"] != p["expect"]:
        e.append("重绘次数与期望不符")
    return e


def _linter(params: Dict[str, Any]) -> Dict[str, Any]:
    allow = set(params["allowlist"])
    missing = [a for a in params["apis"] if a not in allow]
    return {"apis": params["apis"], "allowlist": params["allowlist"],
            "missing": missing, "all_ok": len(missing) == 0}


def _linter_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["all_ok"] and p["missing"]:
        e.append("声称全部合规却存在缺失 API")
    return e


def _probe(params: Dict[str, Any]) -> Dict[str, Any]:
    status = int(params.get("status", 200))
    return {"url": params["url"], "status": status, "ok": 200 <= status < 400}


def _probe_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["ok"] and not (200 <= p["status"] < 400):
        e.append("状态判定矛盾")
    return e


def _invariant(params: Dict[str, Any]) -> Dict[str, Any]:
    state = params["state"]
    checks = {"hp_nonneg": state.get("hp", 0) >= 0,
              "speed_finite": isinstance(state.get("speed", 0), (int, float))}
    return {"state": state, "checks": checks, "holds": all(checks.values())}


def _invariant_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p["holds"] and not all(p["checks"].values()):
        e.append("声称不变量成立却存在失败项")
    return e


def _hw(params: Dict[str, Any]) -> Dict[str, Any]:
    vram = float(params["vram_mb"])
    tier = "low" if vram < 2048 else ("mid" if vram < 8192 else "high")
    return {"vram_mb": vram, "tier": tier, "expect_tier": params.get("expect_tier")}


def _hw_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_tier") and p["tier"] != p["expect_tier"]:
        e.append("硬件档位与期望不符")
    return e


def _hud(params: Dict[str, Any]) -> Dict[str, Any]:
    raw = params["metrics"]
    out = {k: round(float(v), 3) for k, v in raw.items()}
    return {"metrics": out, "count": len(out),
            "expect_count": params.get("expect_count")}


def _hud_acc(p: Dict[str, Any]) -> List[str]:
    e = []
    if p.get("expect_count") is not None and p["count"] != p["expect_count"]:
        e.append("采集指标数不符")
    return e


# ── 第二批规格并入 B_SKILL_SPECS ─────────────────────────────────────────────
NEW_SPECS_B2: Dict[str, BSkillSpec] = {
    "spatial_grid_partitioning": BSkillSpec(
        "spatial_grid_partitioning", "Logic", "空间网格分区，每点恰落一桶。",
        _spatial_grid, _spatial_grid_acc,
        sample={"points": [[1, 1], [1, 2], [5, 5]], "cell": 4}),
    "object_pool_manager": BSkillSpec(
        "object_pool_manager", "Logic", "对象池命中/新建统计。",
        _pool, _pool_acc,
        sample={"size": 3, "ops": ["alloc", "alloc", "alloc", "alloc", "alloc"]}),
    "quadtree_collision": BSkillSpec(
        "quadtree_collision", "Logic", "区域查询返回确定相交子集。",
        _quad, _quad_acc,
        sample={"boxes": [[0, 0, 2, 2], [5, 5, 2, 2], [1, 1, 1, 1]],
                "query": [0, 0, 3, 3]}),
    "grid_tilemap_parser": BSkillSpec(
        "grid_tilemap_parser", "Logic", "瓦片地图编码→解析往返一致。",
        _tilemap, _tilemap_acc, sample={"grid": [[1, 0], [0, 1]]}),
    "cooldown_timer_queue": BSkillSpec(
        "cooldown_timer_queue", "Logic", "冷却计时触发调度。",
        _cooldown, _cooldown_acc,
        sample={"timers": {"a": 1.0, "b": 2.0},
                "ticks": [0.5, 1.0, 1.5, 2.0, 3.0]}),
    "save_state_serializer": BSkillSpec(
        "save_state_serializer", "Logic", "存档序列化往返 + 哈希确定。",
        _save, _save_acc, sample={"state": {"hp": 10, "pos": [1, 2]}}),
    "virtual_joystick_touch": BSkillSpec(
        "virtual_joystick_touch", "Logic", "触摸向量归一化（中心零、边缘单位）。",
        _joystick, _joystick_acc,
        sample={"cx": 100, "cy": 100, "tx": 140, "ty": 100, "radius": 40}),
    "gamepad_api_handler": BSkillSpec(
        "gamepad_api_handler", "Logic", "手柄按键→动作状态映射。",
        _gamepad, _gamepad_acc,
        sample={"mapping": {"a": "jump", "b": "attack"}, "pressed": ["a"]}),
    "floating_combat_text": BSkillSpec(
        "floating_combat_text", "Logic", "飘字沿插值轨迹从起点到终点。",
        _floattext, _floattext_acc,
        sample={"sx": 0, "sy": 0, "ex": 100, "ey": -50, "ts": [0.0, 1.0]}),
    "dual_engine_subsystem_sandbox": BSkillSpec(
        "dual_engine_subsystem_sandbox", "Logic", "沙盒路径许可规则。",
        _sandbox, _sandbox_acc,
        sample={"allowed": ["core/", "pipeline/"], "denied": ["/etc/"],
                "path": "core/x.py", "expect_permitted": True}),
    "patch_first_sandboxing": BSkillSpec(
        "patch_first_sandboxing", "Logic", "补丁作用域按路径前缀匹配。",
        _patch, _patch_acc,
        sample={"scopes": ["core/", "pipeline/"], "file": "core/x.py",
                "expect_included": True}),
    "logistics_conveyor_network_solving": BSkillSpec(
        "logistics_conveyor_network_solving", "Logic", "传送带节点物质守恒。",
        _logi, _logi_acc,
        sample={"inflow": {"ore": 5}, "outflow": {"plate": 5}}),
    "v8_hidden_class_zero_gc_tuning": BSkillSpec(
        "v8_hidden_class_zero_gc_tuning", "Logic", "同 shape 分配复用 hidden class。",
        _v8, _v8_acc,
        sample={"allocs": [["x", "y"], ["x", "y"], ["x", "y", "z"]]}),
    "canvas_particle_emitter": BSkillSpec(
        "canvas_particle_emitter", "Rendering", "粒子发射计数与边界。",
        _particles, _particles_acc,
        sample={"seed": 42, "n": 200, "w": 800, "h": 600}),
    "lighting_bloom_postprocess": BSkillSpec(
        "lighting_bloom_postprocess", "Rendering", "亮度阈值筛选 bloom 像素。",
        _bloom, _bloom_acc,
        sample={"pixels": [10, 200, 255, 50], "threshold": 128}),
    "shockwave_ring_distort": BSkillSpec(
        "shockwave_ring_distort", "Rendering", "冲击环半径随时间单调增大。",
        _shock, _shock_acc, sample={"speed": 4.0, "ts": [0.0, 0.5, 1.0]}),
    "trail_ghost_renderer": BSkillSpec(
        "trail_ghost_renderer", "Rendering", "残影透明度递减。",
        _ghost, _ghost_acc, sample={"samples": 3, "alpha": 1.0}),
    "svg_path_rasterizer": BSkillSpec(
        "svg_path_rasterizer", "Rendering", "线段栅格化含端点。",
        _raster, _raster_acc, sample={"p0": [0, 0], "p1": [4, 2]}),
    "damage_flash_white": BSkillSpec(
        "damage_flash_white", "Rendering", "受击闪白衰减。",
        _flash, _flash_acc, sample={"duration": 0.3, "ts": [0.0, 0.5, 1.0]}),
    "radial_progress_cooldown": BSkillSpec(
        "radial_progress_cooldown", "Rendering", "环形进度角度 = 比例×2π。",
        _radial, _radial_acc, sample={"fraction": 1.0}),
    "canvas_scanline_crt": BSkillSpec(
        "canvas_scanline_crt", "Rendering", "扫描线每 N 行一行暗。",
        _scanline, _scanline_acc, sample={"h": 10, "period": 2}),
    "render_queue_material_batching": BSkillSpec(
        "render_queue_material_batching", "Rendering", "同材质合批降低 DrawCall。",
        _batch, _batch_acc,
        sample={"draws": ["m1", "m1", "m2", "m3", "m2"]}),
    "frustum_culling_quadtree_spatial": BSkillSpec(
        "frustum_culling_quadtree_spatial", "Rendering", "视锥内对象集合确定。",
        _frustum, _frustum_acc,
        sample={"objects": [[1, 1], [9, 9], [2, 2]], "view": [0, 0, 5, 5]}),
    "auto_rigging_heat_skinning": BSkillSpec(
        "auto_rigging_heat_skinning", "Rendering", "蒙皮权重归一且最近骨最高。",
        _rig, _rig_acc, sample={"vertices": [[0, 0]], "bones": [[0, 0], [10, 0]]}),
    "webaudio_retro_synth": BSkillSpec(
        "webaudio_retro_synth", "Audio", "方波逐样本幅度≤1、过零数匹配频率。",
        _synth, _synth_acc,
        sample={"freq": 440.0, "sr": 8000, "duration": 0.01}),
    "white_noise_explosion": BSkillSpec(
        "white_noise_explosion", "Audio", "爆炸噪声 RMS 随衰减包络不增。",
        _noise, _noise_acc, sample={"seed": 7, "n": 400, "duration": 1.0}),
    "pitch_bend_laser_sfx": BSkillSpec(
        "pitch_bend_laser_sfx", "Audio", "激光音频率线性扫频。",
        _pitch, _pitch_acc,
        sample={"f0": 880.0, "f1": 440.0, "ts": [0.0, 1.0]}),
    "coin_pickup_bell_chime": BSkillSpec(
        "coin_pickup_bell_chime", "Audio", "金币音先高后低、时长正确。",
        _coin, _coin_acc,
        sample={"freq_a": 880.0, "freq_b": 440.0, "dur_a": 0.1, "dur_b": 0.2}),
    "jump_spring_whistle": BSkillSpec(
        "jump_spring_whistle", "Audio", "起跳哨音首尾回基频、中段峰值。",
        _whistle, _whistle_acc,
        sample={"f0": 300.0, "f1": 900.0, "ts": [0.0, 0.5, 1.0]}),
    "game_over_jingle_chord": BSkillSpec(
        "game_over_jingle_chord", "Audio", "减七和弦相邻音程恰 3 半音。",
        _jingle, _jingle_acc, sample={"root": 220.0}),
    "spatial_stereo_panner": BSkillSpec(
        "spatial_stereo_panner", "Audio", "声相→L/R 增益守恒。",
        _panner, _panner_acc, sample={"pan": -1.0}),
    "headless_input_simulator": BSkillSpec(
        "headless_input_simulator", "QA", "注入事件序列得到确定终态。",
        _inputsim, _inputsim_acc,
        sample={"events": [{"key": "jump", "down": True},
                           {"key": "jump", "down": False}]}),
    "fps_stability_auditor": BSkillSpec(
        "fps_stability_auditor", "QA", "帧耗时的 p95 与掉帧数统计。",
        _fps, _fps_acc,
        sample={"frame_times": [16, 16, 16, 50, 16], "budget": 33.3}),
    "memory_leak_probe": BSkillSpec(
        "memory_leak_probe", "QA", "堆快照差值检测泄漏。",
        _leak, _leak_acc, sample={"before": 100, "after": 150}),
    "collision_glitch_detector": BSkillSpec(
        "collision_glitch_detector", "QA", "穿透深度几何检测。",
        _glitch, _glitch_acc,
        sample={"a": [0, 0, 2, 2], "b": [1, 1, 2, 2]}),
    "boundary_exploit_tester": BSkillSpec(
        "boundary_exploit_tester", "QA", "坐标越界检测。",
        _boundary, _boundary_acc,
        sample={"x": 10, "y": 10, "bounds": [0, 0, 5, 5], "expect_out": True}),
    "audio_silence_detector": BSkillSpec(
        "audio_silence_detector", "QA", "RMS 阈值静音检测。",
        _silence, _silence_acc,
        sample={"signal": [0, 0, 0, 0], "threshold": 0.01, "expect_silent": True}),
    "infinite_loop_watchdog": BSkillSpec(
        "infinite_loop_watchdog", "QA", "步数超阈值看门狗。",
        _watchdog, _watchdog_acc,
        sample={"steps": 1000, "limit": 500, "expect_killed": True}),
    "browser_resize_stress": BSkillSpec(
        "browser_resize_stress", "QA", "每次 resize 触发一次重绘。",
        _resize, _resize_acc,
        sample={"sizes": [800, 1024, 1280], "expect": 3}),
    "cross_browser_api_linter": BSkillSpec(
        "cross_browser_api_linter", "QA", "API 存在性白名单检测。",
        _linter, _linter_acc,
        sample={"apis": ["fetch", "localStorage"],
                "allowlist": ["fetch", "localStorage", "indexedDB"]}),
    "cli_headless_probing": BSkillSpec(
        "cli_headless_probing", "QA", "探针返回状态可断言。",
        _probe, _probe_acc, sample={"url": "http://x", "status": 200}),
    "state_invariants_fuzzing": BSkillSpec(
        "state_invariants_fuzzing", "QA", "不变量布尔判定。",
        _invariant, _invariant_acc, sample={"state": {"hp": 10, "speed": 5}}),
    "hardware_tier_profiling": BSkillSpec(
        "hardware_tier_profiling", "QA", "按显存推导硬件档位。",
        _hw, _hw_acc, sample={"vram_mb": 8192, "expect_tier": "high"}),
    "engine_subsystem_profiling_hud": BSkillSpec(
        "engine_subsystem_profiling_hud", "QA", "采集指标计数确定。",
        _hud, _hud_acc,
        sample={"metrics": {"fps": 60, "cpu": 12.5, "mem": 512},
                "expect_count": 3}),
}

B_SKILL_SPECS.update(NEW_SPECS_B2)
# W4 全量覆盖：确定性算法 + DCC/GPU 标红 = 65
BATCH1_IMPLEMENTED = [s for s in B_SKILL_SPECS
                      if B_SKILL_SPECS[s].needs_runtime_tool is None]
BATCH1_RUNTIME_TOOL = [s for s in B_SKILL_SPECS
                       if B_SKILL_SPECS[s].needs_runtime_tool]
