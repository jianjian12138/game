"""
Worker Task Offloader — 多线程与异步 Worker 计算卸载器
======================================================
将 500+ 发弹幕空间哈希检测、3D NavMesh A* 寻路和蒙特卡洛大规模推演
剥离至后台 Worker 线程池，确保主游戏循环恒定 60FPS 零掉帧。
"""

import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Callable, Any, Dict, Optional, List


@dataclass
class OffloadedTask:
    task_id: str
    future: Future
    created_at: float
    name: str


class WorkerOffloader:
    """Non-blocking background computation worker pool."""

    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="GameWorker")
        self.active_tasks: Dict[str, OffloadedTask] = {}
        self._seq = 0

    def submit_task(self, name: str, task_fn: Callable[..., Any], *args, **kwargs) -> str:
        self._seq += 1
        tid = f"task_{self._seq}_{int(time.time() * 1000)}"
        future = self.executor.submit(task_fn, *args, **kwargs)
        self.active_tasks[tid] = OffloadedTask(task_id=tid, future=future, created_at=time.time(), name=name)
        return tid

    def poll_result(self, task_id: str) -> Optional[Any]:
        """Non-blocking check if task has completed. Returns result or None."""
        task = self.active_tasks.get(task_id)
        if not task:
            return None
        if task.future.done():
            del self.active_tasks[task_id]
            return task.future.result()
        return None

    def cancel_task(self, task_id: str) -> bool:
        task = self.active_tasks.get(task_id)
        if task:
            cancelled = task.future.cancel()
            del self.active_tasks[task_id]
            return cancelled
        return False

    def shutdown(self, wait: bool = False):
        self.executor.shutdown(wait=wait)
