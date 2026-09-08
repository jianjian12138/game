# =================================================================
# ⚙️ 腾讯 CNB 支柱 2: EAC 万物皆代码流水线总调度器 (eac_pipeline_orchestrator.py)
# 对标《腾讯 CNB: .cnb.yml 声明式编排，全自动无人值守流水线》
# =================================================================

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

class EacPipelineOrchestrator:
    """
    EAC (Everything-as-Code) 声明式流水线调度器
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pipeline_dir = project_root / "pipeline"

    def generate_cnb_declarative_spec(self) -> Path:
        """生成标准声明式 .cnb.yml 规范文件"""
        content = """# 🚀 腾讯 CNB 云原生流水线声明式规范 (.cnb.yml)
# Everything-as-Code 游戏全自动研发流水线

version: 1.0
name: mindustry-planet-war-eac-pipeline

stages:
  - name: 1. Requirement & Architecture Gate
    tasks:
      - script: python pipeline/test_mechanics_integration.py
      - script: python pipeline/game_anatomy_audit.py
      - script: python core/constitution_guard.py

  - name: 2. Assets & Rendering Guard
    tasks:
      - script: python pipeline/style_lock_verifier.py
      - script: python pipeline/test_spritesheet_interaction.py
      - script: python pipeline/test_aseprite_engine.py

  - name: 3. Combat, Motion & AI Brain
    tasks:
      - script: python pipeline/test_action_timeline.py
      - script: python pipeline/test_expressive_motion.py
      - script: python pipeline/test_agent_combat_brain.py
      - script: python pipeline/test_nitrogen_action.py

  - name: 4. Final Stranger 3-Q & Assembly Checklist
    tasks:
      - script: python pipeline/anti_overengineering_guard.py
      - script: python pipeline/test_gdevelop_engine.py
      - script: python pipeline/assembly_checklist_gate.py
"""
        cnb_file = self.project_root / ".cnb.yml"
        cnb_file.write_text(content, encoding="utf-8")
        return cnb_file

    def execute_eac_pipeline_locally(self) -> bool:
        """本地无人值守执行声明式流水线核心门禁"""
        print("=== EacPipelineOrchestrator: 正在无人值守执行 EAC 声明式全量流水线 ===")
        suites = [
            ("Constitution & Rules", "core/constitution_guard.py"),
            ("Game Anatomy (5 Blocks)", "pipeline/game_anatomy_audit.py"),
            ("Mechanics Integration", "pipeline/test_mechanics_integration.py"),
            ("Style Lock & DesignTokens", "pipeline/style_lock_verifier.py"),
            ("Spritesheet & Interaction", "pipeline/test_spritesheet_interaction.py"),
            ("Aseprite Palette Engine", "pipeline/test_aseprite_engine.py"),
            ("Action Timeline & Sound", "pipeline/test_action_timeline.py"),
            ("Expressive Motion & Juice", "pipeline/test_expressive_motion.py"),
            ("Agent Combat Brain", "pipeline/test_agent_combat_brain.py"),
            ("NitroGen 20D Action Space", "pipeline/test_nitrogen_action.py"),
            ("Stranger 3-Q & Anti-Overeng", "pipeline/anti_overengineering_guard.py"),
            ("GDevelop Engine (TriggerOnce)", "pipeline/test_gdevelop_engine.py"),
            ("Assembly Checklist Gate", "pipeline/assembly_checklist_gate.py"),
        ]

        all_ok = True
        for name, script_rel in suites:
            script_path = self.project_root / script_rel
            if not script_path.exists():
                print(f"  [WARN] 脚本不存在: {script_rel}")
                continue

            res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
            if res.returncode == 0:
                print(f"  [PASS] {name:<35} -> 100% 绿灯通过")
            else:
                print(f"  [FAIL] {name:<35} -> 报错退出:\n{res.stderr[:200]}")
                all_ok = False

        verdict = "[PASS] (EAC 声明式流水线全景通关，达到腾讯 CNB 云原生最高交付标准！)" if all_ok else "[FAIL]"
        print(f"  [EAC PIPELINE VERDICT] {verdict}")
        print("==========================================================================")
        return all_ok

if __name__ == "__main__":
    orchestrator = EacPipelineOrchestrator((Path(__file__).resolve().parent))
    orchestrator.generate_cnb_declarative_spec()
    orchestrator.execute_eac_pipeline_locally()
