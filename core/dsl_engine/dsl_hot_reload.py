"""
DSL Hot Reload — 文件变更监听与热重载
=======================================
在开发模式下监听 DSL 文件变化，自动重新解析并触发回调。
生产环境禁用此模块。
"""

from __future__ import annotations
import time
import threading
from pathlib import Path
from typing import Callable, Optional


class DSLHotReload:
    """
    监听目录下的 DSL 文件变更，自动重载。

    Args:
        watch_dir:  要监听的目录路径
        engine:     DSLEngine 实例（用于重新 load）
        callback:   文件变更时的回调 callback(path, ast)
        poll_interval: 轮询间隔（秒），默认 0.5s
    """

    def __init__(
        self,
        watch_dir: str,
        engine,
        callback: Optional[Callable] = None,
        poll_interval: float = 0.5,
    ):
        self.watch_dir = Path(watch_dir)
        self.engine = engine
        self.callback = callback
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        # 记录每个文件的上次修改时间
        self._mtimes: dict[Path, float] = {}

    def start(self):
        """启动后台监听线程。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print(f"[DSL HotReload] 监听目录: {self.watch_dir}")

    def stop(self):
        """停止监听。"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("[DSL HotReload] 已停止")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _poll_loop(self):
        while self._running:
            self._check_changes()
            time.sleep(self.poll_interval)

    def _check_changes(self):
        for path in self.watch_dir.rglob("*.yaml"):
            mtime = path.stat().st_mtime
            if self._mtimes.get(path) != mtime:
                self._mtimes[path] = mtime
                self._reload(path)
        for path in self.watch_dir.rglob("*.json"):
            mtime = path.stat().st_mtime
            if self._mtimes.get(path) != mtime:
                self._mtimes[path] = mtime
                self._reload(path)

    def _reload(self, path: Path):
        try:
            ast = self.engine.load(str(path))
            print(f"[DSL HotReload] 重载: {path.name}")
            if self.callback:
                self.callback(str(path), ast)
        except Exception as e:
            print(f"[DSL HotReload] 重载失败 [{path.name}]: {e}")
