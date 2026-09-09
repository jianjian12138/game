#!/usr/bin/env python3
"""
core/run_context.py: 任务级沙箱隔离与原子产物提升管理器 (Task Isolation & Run Context)
为每次生成任务分配独立 run_id 工作区，收集阶段执行指纹与 SHA-256 产物哈希，支持原子提升。
纯 Python 3.9+ 标准库实现，零外部依赖。
"""
import os
import sys
import time
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.artifact_store import ArtifactStore, ArtifactIntegrityError

ROOT = Path(__file__).resolve().parent.parent

class RunContext:
    """任务独立沙箱工作区与运行清单管理器"""

    def __init__(self, title: str = "game", base_dir: Optional[Path] = None, run_id: Optional[str] = None):
        self.title = title
        self.start_time = time.time()
        self.created_at = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 生成唯一 run_id: run_YYYYMMDD_HHMMSS_<8位hash>
        entropy = f"{self.start_time}_{title}_{os.getpid()}"
        hash_suffix = hashlib.md5(entropy.encode("utf-8")).hexdigest()[:8]
        self.run_id = run_id or f"run_{time.strftime('%Y%m%d_%H%M%S')}_{hash_suffix}"

        # 确定根工作区: output/runs/<run_id>
        output_root = Path(base_dir) if base_dir else ROOT / "output"
        self.runs_root = output_root / "runs"
        self.work_dir = self.runs_root / self.run_id
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_store = ArtifactStore(self.work_dir)

        self.input_params: Dict[str, Any] = {}
        self.stage_timings: List[Dict[str, Any]] = []
        self.hook_logs: List[Dict[str, Any]] = []
        self.artifacts: Dict[str, Any] = {}
        self.status = "INITIALIZED"

    def set_inputs(self, **kwargs):
        self.input_params = kwargs

    def record_stage(self, stage_name: str, duration_sec: float, details: Optional[Dict[str, Any]] = None):
        self.stage_timings.append({
            "stage": stage_name,
            "duration_sec": round(duration_sec, 4),
            "timestamp": time.strftime("%H:%M:%S"),
            "details": details or {}
        })

    def record_hook(self, hook_id: str, active_agents: List[str], status: str = "SUCCESS"):
        self.hook_logs.append({
            "hook_id": hook_id,
            "timestamp": time.strftime("%H:%M:%S"),
            "active_agents": active_agents,
            "status": status
        })

    def register_artifact(self, name: str, file_path: Path) -> str:
        """注册产物并计算 SHA-256；已密封运行拒绝修改。"""
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return ""
        content = p.read_bytes()
        try:
            ref = self.artifact_store.put_bytes(
                artifact_type=name,
                data=content,
                artifact_id=f"art_{name}",
                relative_name=p.name,
                producer_capability="legacy.studio_engine",
            )
        except ArtifactIntegrityError:
            # 兼容旧流程：同名同内容重复登记可继续；内容变化必须暴露。
            existing = self.artifacts.get(name, {})
            current = "sha256:" + hashlib.sha256(content).hexdigest()
            if existing.get("sha256") == current:
                return current
            raise
        sha256 = ref.sha256
        rel_path = str(p.relative_to(self.work_dir)) if self.work_dir in p.parents else p.name
        self.artifacts[name] = {
            "artifact_id": ref.artifact_id,
            "path": rel_path,
            "size_bytes": len(content),
            "sha256": sha256,
            "immutable_path": ref.relative_path,
        }
        return sha256

    def generate_manifest(self) -> Dict[str, Any]:
        """构建完整的结构化可审计清单"""
        elapsed = time.time() - self.start_time
        manifest = {
            "schema_version": 1,
            "run_id": self.run_id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at,
            "elapsed_seconds": round(elapsed, 3),
            "input_params": self.input_params,
            "stage_timings": self.stage_timings,
            "hooks_dispatched": self.hook_logs,
            "teams_activated": self.input_params.get("teams", []),
            "artifacts_count": len(self.artifacts),
            "artifacts": self.artifacts,
            "artifact_integrity": self.artifact_store.verify_all(),
        }
        manifest_path = self.work_dir / "run_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest

    def promote_to_release(self, target_release_dir: Path, files_to_promote: Optional[List[str]] = None) -> List[Path]:
        """兼容导出：仅允许显式调用，正式候选应由 ReleaseService 创建清单。"""
        if self.status == "SEALED":
            raise ArtifactIntegrityError("Sealed run cannot be promoted through legacy path")
        target = Path(target_release_dir)
        target.mkdir(parents=True, exist_ok=True)
        promoted = []

        files = files_to_promote or ["index.html", "GDD.md", "gdd.json", "Consensus_Record.json", "Peer_Review_Report.json", "run_manifest.json"]
        for fname in files:
            src = self.work_dir / fname
            if src.exists():
                dst = target / fname
                tmp_dst = target / f".tmp_{fname}_{os.getpid()}"
                shutil.copy2(src, tmp_dst)
                if dst.exists():
                    dst.unlink()
                tmp_dst.rename(dst)
                promoted.append(dst)

        self.status = "PROMOTED"
        return promoted
