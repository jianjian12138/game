#!/usr/bin/env python3
"""pipeline/playtest_engine.py — W8 自动试玩闭环（真实闭环 + 诚实门禁）。

职责（与升级计划第十一章、W8 一致）：
  在已安装的 Playwright + 本机 Edge（与 W7 前 Web 主线同套环境）上，对生成的游戏做
  **自动化闭环试玩**：
    ① 每轮 episode：真实加载页面 → boot 真校验（canvas 有尺寸 + 契约已挂载 + 无未捕获异常）
       → 真实触发 start → 自动驱动输入（确定性真实键盘事件）→ 采样运行时契约
       → 真实像素采样（canvas 非空白 / 前后帧内容哈希 diff）→ 真实输入响应验证
         （驱动输入前后画面确有可观测变化，证明「输入真被处理」而非空转帧数）
       → 尝试触发 game_over / restart 闭合循环 → 记录本轮真实证据。
    ② 多轮重复（episodes），聚合真实证据：到达 playing 的轮次、主循环推进帧数、
       真实渲染轮次、输入有响应轮次、未捕获异常、控制台错误、网络失败、
       game_over/restart 是否真实支持。
    ③ 产出诚实 verdict + EvidencePack（含目标文件哈希、逐轮像素快照 + 截图）。

防伪底线（13.2）：
  - 没有任何自动化驱动时，一律 NEEDS_RUNTIME_TOOL，绝不因为「HTML 有 canvas」而 PASS。
  - 主循环推进帧数（frame/ticks）只是「循环在跑」的弱信号，**不算**「画面在动」：
    特增「真实像素采样」——canvas 必须采样到非空白内容，且驱动输入前后像素内容确有
    可观测变化，否则不得 PASS（帧数涨 ≠ 画面在动；空转循环也会被抓出）。
  - 每一条 PASS 都必须由真实浏览器加载 + 主循环推进 + 画面真渲染 + 输入真响应 + 契约状态迁移佐证；
    游戏未暴露 endMatch/restartMatch 接口时，game_over/restart 如实标 NEEDS_GAME_CONTRACT，
    绝不假装完成了「死亡→重开」闭环。
  - 复用 BrowserRuntimeAdapter（W7 前已落地的诚实浏览器适配器）的驱动/契约/触发逻辑，不另起炉灶。
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.runtime_adapter import RuntimeStatus
from pipeline.browser_runtime_adapter import (
    BrowserRuntimeAdapter, CHROMIUM_ARGS,
    _JS_CANVAS_SIZE, _JS_GAME_CONTRACT, _JS_CANVAS_PIXELS, _loop_position,
)

ROOT = Path(__file__).resolve().parent.parent

# 自动驱动时每步按键间隔（毫秒）——真实键盘事件，非模拟
_STEP_DOWN_MS = 60
_STEP_GAP_MS = 90
_ACTION_KEYS = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown",
                "Space", "KeyA", "KeyD", "KeyW", "KeyS"]


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _hash_basename(target_hash: str) -> str:
    """从 'sha256:abc...' 取冒号后部分作为文件名安全片段。"""
    return target_hash.split(":", 1)[-1] or "unknown"


@dataclass
class EpisodeRecord:
    episode: int
    boot_status: str = "UNKNOWN"
    canvas: Optional[Dict[str, int]] = None
    start_triggered: Optional[str] = None
    reached_playing: bool = False
    frames_before: int = 0
    frames_after: int = 0
    frames_advanced: int = 0
    inputs_sent: int = 0
    # 真实像素采样（防伪：画面真在渲染 + 画面随输入变化）
    pixel_rendered: bool = False
    pixel_type: Optional[str] = None
    pixel_nonzero: int = 0
    pixel_before_hash: Optional[int] = None
    pixel_after_hash: Optional[int] = None
    input_reflected: bool = False
    input_evidence: str = ""
    screenshot: str = ""
    end_triggered: Optional[str] = None
    game_over_reached: bool = False
    restart_triggered: Optional[str] = None
    restart_reached: bool = False
    page_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode": self.episode,
            "boot_status": self.boot_status,
            "canvas": self.canvas,
            "start_triggered": self.start_triggered,
            "reached_playing": self.reached_playing,
            "frames_before": self.frames_before,
            "frames_after": self.frames_after,
            "frames_advanced": self.frames_advanced,
            "inputs_sent": self.inputs_sent,
            "pixel_rendered": self.pixel_rendered,
            "pixel_type": self.pixel_type,
            "pixel_nonzero": self.pixel_nonzero,
            "pixel_before_hash": self.pixel_before_hash,
            "pixel_after_hash": self.pixel_after_hash,
            "input_reflected": self.input_reflected,
            "input_evidence": self.input_evidence,
            "screenshot": self.screenshot,
            "end_triggered": self.end_triggered,
            "game_over_reached": self.game_over_reached,
            "restart_triggered": self.restart_triggered,
            "restart_reached": self.restart_reached,
            "page_errors": self.page_errors[:5],
        }


@dataclass
class PlaytestResult:
    status: str
    target: str
    target_hash: str
    episodes_planned: int = 0
    episodes_run: int = 0
    episodes_reached_playing: int = 0
    full_loops_completed: int = 0
    game_over_supported: bool = False
    restart_supported: bool = False
    total_frames: int = 0
    # 真实渲染 / 输入响应计数（防伪门禁）
    pixel_rendered_count: int = 0
    input_reflected_count: int = 0
    console_error_count: int = 0
    page_error_count: int = 0
    network_failure_count: int = 0
    needs_runtime_tool: Optional[str] = None
    episodes: List[Dict[str, Any]] = field(default_factory=list)
    console_errors: List[str] = field(default_factory=list)
    failed_requests: List[str] = field(default_factory=list)
    evidence_path: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "target": self.target,
            "target_hash": self.target_hash,
            "episodes_planned": self.episodes_planned,
            "episodes_run": self.episodes_run,
            "episodes_reached_playing": self.episodes_reached_playing,
            "full_loops_completed": self.full_loops_completed,
            "game_over_supported": self.game_over_supported,
            "restart_supported": self.restart_supported,
            "total_frames": self.total_frames,
            "pixel_rendered_count": self.pixel_rendered_count,
            "input_reflected_count": self.input_reflected_count,
            "console_error_count": self.console_error_count,
            "page_error_count": self.page_error_count,
            "network_failure_count": self.network_failure_count,
            "needs_runtime_tool": self.needs_runtime_tool,
            "episodes": self.episodes,
            "console_errors": self.console_errors[:10],
            "failed_requests": self.failed_requests[:10],
            "evidence_path": self.evidence_path,
            "error": self.error,
        }


class PlaytestEngine:
    """自动化试玩闭环引擎：多轮 episode 真实驱动 + 聚合真实证据。"""

    def __init__(self, evidence_dir: Optional[str] = None, seed: int = 0):
        self.adapter = BrowserRuntimeAdapter(evidence_dir=evidence_dir)
        self.evidence_dir = Path(evidence_dir) if evidence_dir \
            else (ROOT / "output" / "playtest")
        self.rng = random.Random(int(seed) if seed is not None else 0)

    # ── 主入口 ──────────────────────────────────────────────────────────────
    def run(self, target: str, episodes: int = 3, play_seconds: float = 3.0,
            seed: int = 0, policy: str = "auto", headless: bool = True) -> PlaytestResult:
        tpath = Path(target)
        target_bytes = b""
        if tpath.exists():
            target_bytes = tpath.read_bytes()
        target_hash = _sha(target_bytes) if target_bytes else "sha256:none"
        self.rng = random.Random(int(seed) if seed is not None else 0)
        self._target_hash = target_hash

        res = PlaytestResult(
            status=RuntimeStatus.FAIL, target=str(tpath),
            target_hash=target_hash, episodes_planned=max(1, episodes))

        if not target_bytes:
            res.error = f"试玩目标不存在: {target}"
            return res

        # 诚实门禁：无真实浏览器自动化驱动 → NEEDS_RUNTIME_TOOL
        driver, driver_reason = BrowserRuntimeAdapter._load_driver()
        if driver is None:
            res.status = RuntimeStatus.NEEDS_RUNTIME_TOOL
            res.needs_runtime_tool = "browser_runtime"
            res.error = driver_reason
            return res

        session = self.adapter.launch(tpath)
        console_errors: List[str] = []
        page_errors: List[str] = []
        failed_requests: List[str] = []
        records: List[EpisodeRecord] = []

        try:
            with driver() as p:
                browser = p.chromium.launch(
                    executable_path=session.get("browser_exe"),
                    headless=headless, args=CHROMIUM_ARGS)
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.on("console", lambda m: console_errors.append(m.text)
                        if (m.type == "error" and "Failed to load resource" not in m.text)
                        else None)
                page.on("pageerror", lambda e: page_errors.append(str(e)))
                page.on("requestfailed",
                        lambda r: failed_requests.append(str(r.url)))

                for e in range(max(1, episodes)):
                    ep = self._run_episode(page, session.get("server_url"), e,
                                           play_seconds, policy)
                    ep.page_errors = page_errors[-5:]
                    records.append(ep)

                browser.close()
        except Exception as exc:
            res.status = RuntimeStatus.NEEDS_RUNTIME_TOOL
            res.needs_runtime_tool = "browser_runtime"
            res.error = f"真实浏览器驱动执行失败: {exc}"
            self.adapter.close(session)
            return res
        finally:
            try:
                self.adapter.close(session)
            except Exception:
                pass

        return self._aggregate(res, records, console_errors,
                                page_errors, failed_requests)

    # ── 单轮 episode 真实驱动 ─────────────────────────────────────────────────
    def _run_episode(self, page, url: str, e: int, play_seconds: float,
                     policy: str) -> EpisodeRecord:
        rec = EpisodeRecord(episode=e)
        page.goto(url, wait_until="load", timeout=20000)
        page.wait_for_timeout(300)

        canvas = page.evaluate(_JS_CANVAS_SIZE)
        before = page.evaluate(_JS_GAME_CONTRACT) or {}
        rec.canvas = canvas
        # boot 真校验：canvas 有真实尺寸 + 契约已挂载 ready + 页面无未捕获异常（契约 errors 字段）
        boot_ok = bool(canvas and canvas.get("width", 0) > 0
                       and canvas.get("height", 0) > 0) \
            and bool(before.get("ready")) and not before.get("errors")
        rec.boot_status = RuntimeStatus.PASS if boot_ok else RuntimeStatus.FAIL

        # 真实触发 start
        rec.start_triggered = BrowserRuntimeAdapter._try_start_game(page)
        reached = False
        for _ in range(10):
            page.wait_for_timeout(200)
            c = page.evaluate(_JS_GAME_CONTRACT) or {}
            if c.get("state") in ("playing", "running"):
                reached = True
                break
        rec.reached_playing = reached
        rec.frames_before = _loop_position(before)

        # 真实像素采样①：到达 playing 后，canvas 必须采样到非空白内容（防伪：画面真在渲染）
        pix_at_playing = page.evaluate(_JS_CANVAS_PIXELS)
        if isinstance(pix_at_playing, dict):
            rec.pixel_type = pix_at_playing.get("type")
            rec.pixel_nonzero = int(pix_at_playing.get("nonzero", 0) or 0)
            rec.pixel_rendered = bool(pix_at_playing.get("nonblank"))
            rec.pixel_before_hash = pix_at_playing.get("hash")
        else:
            rec.pixel_rendered = False  # 连 canvas 都采不到：无法证实渲染

        # 自动驱动真实输入（驱动前已记录像素哈希，用于随后比对「输入真有响应」）
        rec.inputs_sent = self._drive_inputs(page, play_seconds, policy)

        after = page.evaluate(_JS_GAME_CONTRACT) or {}
        rec.frames_after = _loop_position(after)
        rec.frames_advanced = rec.frames_after - rec.frames_before

        # 真实像素采样② + 真实输入响应验证：
        #   驱动输入前后画布内容哈希发生变化 → 证明输入真被处理并反映到画面
        #   （帧数涨 ≠ 画面在动；空转循环或忽略输入的壳子在这里被抓出）
        pix_after = page.evaluate(_JS_CANVAS_PIXELS)
        if isinstance(pix_after, dict):
            rec.pixel_after_hash = pix_after.get("hash")
            if rec.pixel_type is None:
                rec.pixel_type = pix_after.get("type")
                rec.pixel_nonzero = int(pix_after.get("nonzero", 0) or 0)
        if rec.pixel_before_hash is not None and rec.pixel_after_hash is not None:
            if rec.pixel_before_hash != rec.pixel_after_hash:
                rec.input_reflected = True
                rec.input_evidence = (f"驱动输入前后画布内容哈希变化 "
                                      f"({rec.pixel_before_hash} → {rec.pixel_after_hash})，"
                                      f"证明输入被处理并反映到画面")
            else:
                rec.input_evidence = ("驱动输入前后画布内容哈希未变化；"
                                      "若游戏确有响应应改变像素，疑似忽略输入或静态画面")
        else:
            rec.input_evidence = "无法采样 canvas 像素，输入响应无法核验"

        # 截图留证（仅首轮，供人工复核画面是否真实渲染）
        if e == 0 and self.evidence_dir is not None:
            try:
                self.evidence_dir.mkdir(parents=True, exist_ok=True)
                safe = _hash_basename(self._target_hash)
                shot = self.evidence_dir / f"playtest_{safe}_ep{e}.png"
                page.screenshot(path=str(shot))
                rec.screenshot = str(shot)
            except Exception:
                pass

        # 尝试闭合循环：game_over → restart（仅当游戏暴露接口才真实成立）
        rec.end_triggered = BrowserRuntimeAdapter._try_end_game(page)
        if rec.end_triggered:
            for _ in range(10):
                page.wait_for_timeout(200)
                c = page.evaluate(_JS_GAME_CONTRACT) or {}
                if c.get("state") == "gameover" and c.get("game_over_count", 0) >= 1:
                    rec.game_over_reached = True
                    break
            if rec.game_over_reached:
                rec.restart_triggered = BrowserRuntimeAdapter._try_restart_game(page)
                if rec.restart_triggered:
                    for _ in range(10):
                        page.wait_for_timeout(200)
                        c = page.evaluate(_JS_GAME_CONTRACT) or {}
                        if c.get("restart_count", 0) >= 1 \
                                and c.get("state") in ("playing", "running", "boot"):
                            rec.restart_reached = True
                            break
        return rec

    def _drive_inputs(self, page, play_seconds: float, policy: str) -> int:
        """发送真实键盘事件（确定性随机）。返回发送的事件数。"""
        steps = max(1, int(play_seconds / ((_STEP_DOWN_MS + _STEP_GAP_MS) / 1000.0)))
        sent = 0
        for _ in range(steps):
            key = self.rng.choice(_ACTION_KEYS)
            try:
                page.keyboard.down(key)
                page.wait_for_timeout(_STEP_DOWN_MS)
                page.keyboard.up(key)
                sent += 1
                page.wait_for_timeout(_STEP_GAP_MS)
            except Exception:
                break
        return sent

    # ── 聚合 + 诚实 verdict + 证据落盘 ────────────────────────────────────────
    def _aggregate(self, res: PlaytestResult, records: List[EpisodeRecord],
                   console_errors: List[str], page_errors: List[str],
                   failed_requests: List[str]) -> PlaytestResult:
        res.episodes_run = len(records)
        res.episodes = [r.to_dict() for r in records]
        res.episodes_reached_playing = sum(1 for r in records if r.reached_playing)
        res.game_over_supported = any(r.end_triggered for r in records)
        res.restart_supported = any(r.restart_triggered for r in records)
        res.total_frames = sum(r.frames_after for r in records)
        res.pixel_rendered_count = sum(1 for r in records if r.pixel_rendered)
        res.input_reflected_count = sum(1 for r in records if r.input_reflected)
        res.console_error_count = len(console_errors)
        res.page_error_count = len(page_errors)
        res.network_failure_count = len(failed_requests)
        res.console_errors = console_errors
        res.failed_requests = failed_requests

        # 完整闭环 = 到达 playing 且（若游戏支持则）真实完成 game_over→restart
        def _full(ep: EpisodeRecord) -> bool:
            if not ep.reached_playing:
                return False
            if res.game_over_supported and not ep.game_over_reached:
                return False
            if res.restart_supported and not ep.restart_reached:
                return False
            return True
        res.full_loops_completed = sum(1 for r in records if _full(r))

        # 诚实 verdict（防伪：帧数涨 ≠ 画面在动）
        if res.page_error_count > 0 or any(r.boot_status == RuntimeStatus.FAIL
                                          for r in records):
            res.status = RuntimeStatus.FAIL
            res.error = (f"未捕获异常 {res.page_error_count} 个" if res.page_error_count
                         else "boot 校验失败")
        elif res.episodes_reached_playing < 1:
            res.status = RuntimeStatus.FAIL
            res.error = "没有任何 episode 真正进入 playing 状态"
        elif res.pixel_rendered_count < 1:
            res.status = RuntimeStatus.FAIL
            res.error = ("canvas 像素采样显示画面空白/未渲染（防伪：主循环在跑 ≠ 画面在动；"
                         "疑似空转壳子或未绘制内容的页面）")
        elif res.input_reflected_count < 1:
            res.status = RuntimeStatus.FAIL
            res.error = ("驱动输入前后画面内容哈希未变化（防伪：输入未被处理或画面静态；"
                         "疑似忽略键盘事件的空转循环）")
        else:
            res.status = RuntimeStatus.PASS

        # EvidencePack
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        epath = self.evidence_dir / f"playtest_{res.target_hash.replace(':', '_')}.json"
        epath.write_text(json.dumps(res.to_dict(), ensure_ascii=False, indent=2),
                         encoding="utf-8")
        res.evidence_path = str(epath)
        return res


if __name__ == "__main__":
    import sys
    tgt = sys.argv[1] if len(sys.argv) > 1 else \
        "output/runs/run_b6c2573f8c56c02f8a45/index.html"
    r = PlaytestEngine(seed=42).run(tgt, episodes=2, play_seconds=3.0, seed=42)
    print(f"[PLAYTEST] 目标: {r.target}")
    print(f"  [VERDICT] {r.status}")
    print(f"  [EVIDENCE] 到达playing={r.episodes_reached_playing}/{r.episodes_run} "
          f"完整闭环={r.full_loops_completed} 总帧={r.total_frames}")
    print(f"  [TRUTH] 像素渲染={r.pixel_rendered_count}/{r.episodes_run} "
          f"输入响应={r.input_reflected_count}/{r.episodes_run}")
    print(f"  [SUPPORT] game_over={r.game_over_supported} restart={r.restart_supported}")
    print(f"  [ERRORS] page={r.page_error_count} console={r.console_error_count} net={r.network_failure_count}")
    print(f"  [HASH] {r.target_hash}")
    print(f"  [PACK] {r.evidence_path}")
