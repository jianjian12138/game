"""Executable capability descriptors built from the existing registry."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from core.contracts import CapabilityDescriptor
from core.registry import STUDIO_TEAMS


class CapabilityRegistry:
    def __init__(self) -> None:
        self._descriptors: Dict[str, CapabilityDescriptor] = {}
        self._register_builtin()

    def _register_builtin(self) -> None:
        builtins = [
            CapabilityDescriptor(
                capability_id="intent.normalize", version="1.0.0", kind="normalizer",
                accepts=[{"type": "GameIntent", "schema_version": "1.0"}],
                produces=[{"type": "GameSpec", "schema_version": "1.0"}],
                implementation={"module": "core.contracts", "entrypoint": "GameSpec"},
                permissions={"filesystem": "none", "network": "disabled", "process": "none"},
                resource_limits={"timeout_seconds": 10, "max_memory_mb": 128},
                evidence_requirements=["input_hash", "output_hash"], maturity="M1",
            ),
            CapabilityDescriptor(
                capability_id="team.next_gen_3d_art", version="1.0.0", kind="team",
                accepts=[{"type": "GameSpec", "schema_version": "1.0"}],
                produces=[{"type": "asset_manifest", "schema_version": "1.0"}],
                implementation={"module": "core.registry", "entrypoint": "next_gen_3d_art_team"},
                permissions={"filesystem": "run_workspace", "network": "disabled", "process": "allowlist"},
                resource_limits={"timeout_seconds": 300, "max_memory_mb": 1024},
                evidence_requirements=["team_plan", "asset_hashes", "runtime_asset_smoke"], maturity="M2",
            ),
            CapabilityDescriptor(
                capability_id="gate.release", version="1.0.0", kind="gate",
                accepts=[{"type": "EvidencePack", "schema_version": "1.0"}],
                produces=[{"type": "GateDecision", "schema_version": "1.0"}],
                implementation={"module": "core.gate_engine", "entrypoint": "GateEngine.evaluate"},
                permissions={"filesystem": "run_read_only", "network": "disabled", "process": "none"},
                resource_limits={"timeout_seconds": 30, "max_memory_mb": 256},
                evidence_requirements=["evidence_hash", "policy_version"], maturity="M1",
            ),
            CapabilityDescriptor(
                capability_id="godot.pc_desktop", version="1.0.0", kind="runtime",
                accepts=[{"type": "GameSpec", "schema_version": "1.0"}],
                produces=[{"type": "RuntimeEvidence", "schema_version": "1.0"}],
                implementation={"module": "pipeline.godot_runtime_adapter", "entrypoint": "GodotRuntimeAdapter.run_scenarios"},
                permissions={"filesystem": "run_workspace", "network": "disabled", "process": "allowlist"},
                resource_limits={"timeout_seconds": 60, "max_memory_mb": 1024},
                evidence_requirements=[
                    "headless_boot_exit0", "core_loop_frames>=30", "godot_error_count==0",
                ],
                preconditions=[
                    "godot_executable_present (D:\\Godot\\Godot_v4.7.2-stable_win64.exe)",
                    # 独立 .exe 出包还需导出模板；本地已装编辑器但无模板，打包侧标 NEEDS_RUNTIME_TOOL。
                    "standalone_packaging_requires_export_templates (NEEDS_RUNTIME_TOOL on this host)",
                ],
                failure_policy="block",
                # M2 = 运行时验证已在本机真实通过（output/godot_demo 无头跑通 120 帧 / 0 错误）。
                # 仅「独立 .exe 分发」受限于缺导出模板，不改此能力运行时已验证的事实。
                maturity="M2",
            ),
            CapabilityDescriptor(
                capability_id="wechat.mini", version="1.0.0", kind="runtime",
                accepts=[{"type": "GameSpec", "schema_version": "1.0"}],
                produces=[{"type": "RuntimeEvidence", "schema_version": "1.0"}],
                implementation={"module": "pipeline.miniprogram_runtime_adapter",
                                "entrypoint": "MiniProgramRuntimeAdapter.run_scenarios"},
                permissions={"filesystem": "run_workspace", "network": "disabled", "process": "allowlist"},
                resource_limits={"timeout_seconds": 120, "max_memory_mb": 1024},
                evidence_requirements=["wx_frame_count", "boot_state", "touch_input_reflected"],
                preconditions=[
                    "wechat_devtools_cli_present (微信开发者工具 cli 或 miniprogram-ci；本机未装)",
                    "Tier2: 真验证需外部工具/账号，本机返回 NEEDS_RUNTIME_TOOL",
                ],
                failure_policy="block",
                # M0 = 代码骨架已就绪（适配器 + MiniProgramContract），但本机无微信开发者工具，
                # 运行期未真验证；绝不在未验证时标已支持。
                maturity="M0",
            ),
            CapabilityDescriptor(
                capability_id="desktop.shell", version="1.0.0", kind="runtime",
                accepts=[{"type": "GameSpec", "schema_version": "1.0"}],
                produces=[{"type": "RuntimeEvidence", "schema_version": "1.0"}],
                implementation={"module": "pipeline.desktop_shell_adapter",
                                "entrypoint": "DesktopShellAdapter.package_desktop_shell"},
                permissions={"filesystem": "run_workspace", "network": "disabled", "process": "allowlist"},
                resource_limits={"timeout_seconds": 120, "max_memory_mb": 1024},
                evidence_requirements=["shell_project_generated", "web_in_desktop_label"],
                preconditions=[
                    "web_build_verified_first (桌面壳只是把已验证 Web 构建封进 Electron/Tauri)",
                    "build_to_native_exe_requires_framework (NEEDS_RUNTIME_TOOL on this host)",
                ],
                failure_policy="block",
                # M1 = 壳工程生成（真实文件产物）已可用；但「游戏真在桌面壳里跑起来」的验证需框架构建链，
                # 本机未启用，故运行期仍 NEEDS_RUNTIME_TOOL，绝不粉饰成原生引擎。
                maturity="M1",
            ),
            CapabilityDescriptor(
                capability_id="android.native", version="1.0.0", kind="runtime",
                accepts=[{"type": "GameSpec", "schema_version": "1.0"}],
                produces=[{"type": "RuntimeEvidence", "schema_version": "1.0"}],
                implementation={"module": "pipeline.android_runtime_adapter",
                                "entrypoint": "AndroidRuntimeAdapter.run_scenarios"},
                permissions={"filesystem": "run_workspace", "network": "disabled", "process": "allowlist"},
                resource_limits={"timeout_seconds": 300, "max_memory_mb": 1536},
                evidence_requirements=["adb_boot", "core_loop_frames>=30", "touch_input_reflected"],
                preconditions=[
                    "ANDROID_SDK_ROOT_present (本机未装)",
                    "adb_present (本机未装)",
                    "debug_keystore_present (本机未生成)",
                    "Tier2: 真验证需装 SDK，本机返回 NEEDS_RUNTIME_TOOL",
                ],
                failure_policy="block",
                # M0 = 代码骨架已就绪（适配器 + Godot Android 导出封装），但本机无 Android SDK/adb。
                maturity="M0",
            ),
            CapabilityDescriptor(
                capability_id="ios.native", version="1.0.0", kind="runtime",
                accepts=[{"type": "GameSpec", "schema_version": "1.0"}],
                produces=[{"type": "RuntimeEvidence", "schema_version": "1.0"}],
                implementation={"module": "pipeline.ios_packaging", "entrypoint": "ios_export"},
                permissions={"filesystem": "run_workspace", "network": "disabled", "process": "allowlist"},
                resource_limits={"timeout_seconds": 300, "max_memory_mb": 1536},
                evidence_requirements=["xcode_archive", "core_loop_frames>=30", "touch_input_reflected"],
                preconditions=[
                    "macos_builder_required (本机 Windows 物理不可达)",
                    "Tier3: 需换 macOS 构建机/CI 验证，本机返回 NEEDS_MACOS_BUILDER",
                ],
                failure_policy="block",
                # M0 = 仅提供 macOS CI 步骤清单（unverified）；iOS 本机不可达，绝不标已验证。
                maturity="M0",
            ),
        ]
        for descriptor in builtins:
            self.register(descriptor)

    def register(self, descriptor: CapabilityDescriptor) -> None:
        key = f"{descriptor.capability_id}@{descriptor.version}"
        if key in self._descriptors:
            raise ValueError(f"Capability already registered: {key}")
        self._descriptors[key] = descriptor

    def resolve(self, capability_id: str, version: str | None = None) -> CapabilityDescriptor:
        if version:
            return self._descriptors[f"{capability_id}@{version}"]
        candidates = [d for d in self._descriptors.values() if d.capability_id == capability_id]
        if not candidates:
            raise KeyError(capability_id)
        return sorted(candidates, key=lambda d: d.version)[-1]

    def list(self) -> List[CapabilityDescriptor]:
        return list(self._descriptors.values())

    def as_dict(self) -> List[Dict[str, Any]]:
        return [descriptor.to_dict() for descriptor in self.list()]


capability_registry = CapabilityRegistry()
