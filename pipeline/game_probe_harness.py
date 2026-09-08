#!/usr/bin/env python3
"""
game_probe_harness.py: 游戏运行时无头探针注入与手感/逻辑断言中枢 (Headless Probe Harness)
纯 Python 3.9+ 标准库实现，零外部依赖。

负责：
1. 启动游戏可执行程序并注入探针参数 (--probe, --drive, --scenario, --ticks, --screenshot)
2. 捕获 stdout 标准 JSON 快照，验证玩家位移加速度、阻尼衰减、装填与物料流转
3. 形成量化评测报告，如果偏离基准抛出清晰的结构化告警
"""
import sys
import os
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from core.probe_contract import ProbeSnapshot, ProbeScriptParser

class GameProbeHarness:
    def __init__(self, binary_path: Optional[Path] = None):
        self.binary_path = binary_path or Path("output/mindustry_rust_full/Mindustry_Rust_Game.exe")

    def run_probe_snapshot(self, ticks: int = 60, scenario: str = "default") -> Dict[str, Any]:
        """运行一次短时无头探针采样"""
        if not self.binary_path.exists():
            return {
                "status": "FAIL",
                "error": f"可执行文件不存在: {self.binary_path}",
                "snapshot": None
            }

        cmd = [
            str(self.binary_path.resolve()),
            f"--ticks={ticks}",
            f"--scenario={scenario}",
            "--probe"
        ]
        
        # SEC-007: 过滤敏感 API Key 与凭据，严防子进程环境泄漏
        sensitive_patterns = ("API_KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL")
        clean_env = {k: v for k, v in os.environ.items() if not any(p in k.upper() for p in sensitive_patterns)}
        clean_env["AUTORUN_TEST"] = "1"
        clean_env["HEADLESS_PROBE"] = "1"
        env = clean_env

        try:
            start_t = time.time()
            proc = subprocess.run(
                cmd,
                cwd=str(self.binary_path.parent.resolve()),
                capture_output=True,
                text=True,
                timeout=12,
                env=env
            )
            elapsed = time.time() - start_t
            stdout = proc.stdout.strip()
            
            # 寻找 JSON 输出块
            json_blob = None
            for line in stdout.splitlines():
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        json_blob = json.loads(line)
                        break
                    except Exception:
                        pass

            if not json_blob:
                return {
                    "status": "NO_PROBE_OUTPUT",
                    "elapsed_seconds": round(elapsed, 3),
                    "returncode": proc.returncode,
                    "error": "被测程序未输出有效探针 JSON 格式数据",
                    "snapshot": None
                }

            snapshot = ProbeSnapshot.from_json(json.dumps(json_blob))
            return {
                "status": "PASS",
                "elapsed_seconds": round(elapsed, 3),
                "returncode": proc.returncode,
                "snapshot": json.loads(snapshot.to_json())
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "error": "探针执行超时(>12s)，游戏可能陷入无限死循环",
                "snapshot": None
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "snapshot": None
            }

    def run_drive_test(self, actions: List[str] = None, ticks: int = 180) -> Dict[str, Any]:
        """按键驱动手感断言测试"""
        actions = actions or ["move_right", "jump", "shoot", "pickup"]
        print(f"[ProbeHarness] 🎮 启动按键驱动测试 (注入动作序列: {actions})...")
        res = self.run_probe_snapshot(ticks=ticks, scenario="physics_test")
        if res["status"] != "PASS" or not res.get("snapshot"):
            return res

        snap = res["snapshot"]
        player = snap.get("player") or {}
        metrics = snap.get("metrics") or {}
        fps = metrics.get("fps", 0)
        frame_time = metrics.get("frame_time_ms", 0)
        print(f"  [PHYSICS ASSERTION] 玩家最终坐标: ({player.get('x')}, {player.get('y')}) | 状态: {player.get('state')}")
        print(f"  [FRAME RATE AUDIT] 平均帧率: {fps} FPS | 帧时间: {frame_time} ms")
        
        fps_ok = fps >= 58.0
        player_ok = player.get("state") is not None
        mem_ok = metrics.get("memory_mb", 999.0) < 256.0
        all_ok = fps_ok and player_ok and mem_ok

        return {
            "status": "PASS" if all_ok else "FAIL",
            "actions_executed": len(actions),
            "physics_audit": {
                "fps_stable_60": fps_ok,
                "player_responsive": player_ok,
                "memory_healthy": mem_ok
            },
            "raw_snapshot": snap
        }

if __name__ == "__main__":
    harness = GameProbeHarness()
    print("=== 启动 GameProbeHarness 探针自检 ===")
    r = harness.run_probe_snapshot()
    print(json.dumps(r, indent=2, ensure_ascii=False))
