# =================================================================
# 🛑 CCGS 支柱 2: 程序员速查表与红线控制清单 (control_manifest_generator.py)
# 对标《CCGS: create-control-manifest 提取【必须做】与【禁止做】硬约束》
# =================================================================

from pathlib import Path
from typing import Dict, List, Any

class ControlManifestGenerator:
    """
    程序员控制清单生成器 (Control Manifest Generator)
    """

    MUST_DO_RULES = [
        "所有世界网格与实体坐标计算必须通过 WorldBasis 进行 48px 轴心对齐 (Center-Centered)",
        "所有跨系统状态变更必须通过 EventBus 广播信号，UI 层按需重绘，杜绝每帧轮询",
        "所有 Sprite 贴图与音频必须在 Loading 阶段前置 Pre-Cook 到显存，实现 O(1) 零分配极速渲染",
        "单帧物理与渲染耗时必须严格控制在 16.6ms 以内 (稳 60 FPS 垂直同步)",
        "所有实体运动计算必须严格执行 Input ➔ MovementIntent ➔ Resolver ➔ Commit 权威管线"
    ]

    MUST_NOT_DO_RULES = [
        "【严禁】在 Render 绘制函数中反向写修改业务状态或工具状态机",
        "【严禁】在每帧 update/draw 中动态 load_texture 或动态分配堆内存导致 GC 停顿",
        "【严禁】使用特殊 Emoji 代替矢量字体导致 Windows 豆腐块方块乱码",
        "【严禁】跨系统私自直接读写对方私有字段，必须通过消息总线或公开只读接口",
        "【严禁】未通过 Asset QA 与 5 步可玩门禁前私自标记发布"
    ]

    def generate_manifest_document(self, output_file: Path) -> Path:
        """生成标准程序员控制清单大典"""
        lines = [
            "# 🛑 程序员速查表与架构控制红线大典 (control_manifest.md)",
            "> **遵循 CCGS 工业架构铁律：红线不可逾越，确保系统级工业稳定性**\n",
            "---\n",
            "## 🟢 【必须做】(MUST DO) 架构原则\n"
        ]
        for idx, r in enumerate(self.MUST_DO_RULES, 1):
            lines.append(f"{idx}. ✅ `{r}`")

        lines.append("\n---\n## 🔴 【严禁做】(MUST NOT DO) 架构红线\n")
        for idx, r in enumerate(self.MUST_NOT_DO_RULES, 1):
            lines.append(f"{idx}. ❌ `{r}`")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(lines), encoding="utf-8")
        return output_file

if __name__ == "__main__":
    generator = ControlManifestGenerator()
    out = generator.generate_manifest_document(Path(r"D:\jianjian12138\game\docs\architecture\control_manifest.md"))
    print(f"=== ControlManifestGenerator: 程序员控制红线大典已生成 -> {out.name} ===")
