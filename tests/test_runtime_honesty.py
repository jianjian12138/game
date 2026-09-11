"""运行时诚实性与门禁强度回归。

红线：任何环节都不得把「静态事实」或「工具存在」包装成「运行时通过」。
本文件全部用例不依赖浏览器，可在任意沙盒中快速执行。
"""
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

_MINIMAL_HTML = (
    "<!doctype html><html><body><canvas id='c' width='800' height='600'></canvas>"
    "<script>requestAnimationFrame(function(){});</script></body></html>"
)


def _playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except Exception:
        return False


class TestBrowserAdapterHonesty(unittest.TestCase):
    """浏览器适配器在无真实驱动时必须 fail-closed"""

    def test_no_driver_yields_needs_runtime_tool(self):
        from core.runtime_adapter import RuntimeStatus
        from pipeline.browser_runtime_adapter import BrowserRuntimeAdapter

        adapter = BrowserRuntimeAdapter()
        original = BrowserRuntimeAdapter._load_driver
        BrowserRuntimeAdapter._load_driver = staticmethod(lambda: (None, "测试注入：无驱动"))
        try:
            with tempfile.TemporaryDirectory() as tmp:
                page = Path(tmp) / "index.html"
                page.write_text(_MINIMAL_HTML, encoding="utf-8")
                session = adapter.launch(page)
                result = adapter.run_scenarios(session)
                self.assertEqual(result["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)
                for scenario in ("boot", "start", "core_loop", "game_over", "restart"):
                    self.assertEqual(session["scenarios"][scenario]["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)
                self.assertFalse(session["metrics"].get("collected"))
                evidence = adapter.collect_evidence(session)
                self.assertFalse(evidence["metrics"].get("collected"))
                adapter.close(session)
        finally:
            # 取出的是底层函数，恢复时必须重新包成 staticmethod，否则后续用例会收到多余的 self
            BrowserRuntimeAdapter._load_driver = staticmethod(original)

    def test_preflight_reports_missing_driver(self):
        from core.runtime_adapter import RuntimeStatus
        from pipeline.browser_runtime_adapter import BrowserRuntimeAdapter

        adapter = BrowserRuntimeAdapter()
        original = BrowserRuntimeAdapter._load_driver
        BrowserRuntimeAdapter._load_driver = staticmethod(lambda: (None, "测试注入：无驱动"))
        try:
            pre = adapter.preflight("web")
            self.assertFalse(pre.get("can_launch"))
            self.assertEqual(pre["status"], RuntimeStatus.NEEDS_RUNTIME_TOOL)
        finally:
            # 取出的是底层函数，恢复时必须重新包成 staticmethod，否则后续用例会收到多余的 self
            BrowserRuntimeAdapter._load_driver = staticmethod(original)


class TestWebGLProbeHonesty(unittest.TestCase):
    """3D 探针不得在无渲染证据时给出 M3"""

    def test_static_facts_never_claim_webgl(self):
        from pipeline.webgl_runtime_probe import WebGLRuntimeProbe

        with tempfile.TemporaryDirectory() as tmp:
            asset = Path(tmp) / "crate.gltf"
            asset.write_text(
                '{"asset":{"version":"2.0"},"meshes":[{"primitives":[{"attributes":{"POSITION":0}}]}],'
                '"materials":[{"pbrMetallicRoughness":{}}],"nodes":[{"mesh":0}]}',
                encoding="utf-8",
            )
            result = WebGLRuntimeProbe.probe_asset(asset)
            self.assertEqual(result["status"], "NEEDS_RUNTIME_TOOL")
            self.assertIsNone(result["maturity"])
            self.assertNotIn("webgl_context_supported", result["static_facts"])
            self.assertEqual(result["static_facts"]["mesh_count"], 1)

    def test_m3_requires_confirmed_webgl_context_and_render_stats(self):
        from pipeline.webgl_runtime_probe import WebGLRuntimeProbe, M3_MATURITY

        with tempfile.TemporaryDirectory() as tmp:
            asset = Path(tmp) / "showcase.html"
            asset.write_text(_MINIMAL_HTML, encoding="utf-8")

            confirmed = lambda _p: {"status": "SUCCESS", "webgl_context": True,
                                    "agent": {"triangles": 512, "draw_calls": 2}}
            self.assertEqual(WebGLRuntimeProbe.probe_asset(asset, runtime=confirmed)["maturity"], M3_MATURITY)

            no_context = lambda _p: {"status": "SUCCESS", "webgl_context": False}
            self.assertIsNone(WebGLRuntimeProbe.probe_asset(asset, runtime=no_context)["maturity"])

            no_stats = lambda _p: {"status": "SUCCESS", "webgl_context": True, "agent": {}}
            self.assertIsNone(WebGLRuntimeProbe.probe_asset(asset, runtime=no_stats)["maturity"])


class TestAssetSmokeHasNoSideEffects(unittest.TestCase):
    """无运行时时不得偷偷拉起浏览器进程"""

    def test_does_not_launch_browser_process(self):
        from pipeline import runtime_asset_smoke as smoke
        from pipeline.asset_3d_bridge import Asset3DBridge

        with tempfile.TemporaryDirectory() as tmp:
            built = Asset3DBridge.build_procedural_asset("crate", output_dir=Path(tmp))
            launched = []
            original_popen = smoke.subprocess.Popen

            def _spy(*args, **kwargs):
                launched.append(args)
                return original_popen(*args, **kwargs)

            smoke.subprocess.Popen = _spy
            try:
                report = smoke.run_runtime_asset_smoke(built["gltf_path"])
            finally:
                smoke.subprocess.Popen = original_popen

            self.assertEqual(report["status"], "NEEDS_RUNTIME_TOOL")
            self.assertEqual(launched, [])


class TestRuntimeContractInjection(unittest.TestCase):
    """契约必须注入到 head 最前，否则包装不到游戏已经注册好的主循环"""

    def test_injected_into_head_and_idempotent(self):
        from core.runtime_contract import CONTRACT_NAME, inject_runtime_contract

        html = "<!doctype html><html><head><title>t</title></head><body><p>hi</p></body></html>"
        injected = inject_runtime_contract(html)
        self.assertIn(CONTRACT_NAME, injected)
        self.assertLess(injected.index(CONTRACT_NAME), injected.index("</head>"))
        self.assertEqual(injected, inject_runtime_contract(injected))

    def test_falls_back_to_body_without_head(self):
        from core.runtime_contract import CONTRACT_NAME, inject_runtime_contract

        html = "<canvas id='c'></canvas>"
        injected = inject_runtime_contract(html)
        self.assertIn(CONTRACT_NAME, injected)

    def test_empty_html_is_untouched(self):
        from core.runtime_contract import inject_runtime_contract
        self.assertEqual(inject_runtime_contract(""), "")

    def test_page_merely_mentioning_contract_is_still_injected(self):
        """页面自己写了 __GAME_AGENT__（比如上报渲染统计）不等于契约已注入。

        曾经用契约名做幂等判断，导致展台的上报代码让注入被整体跳过，
        浏览器里 window.__GAME_AGENT__ 始终是 undefined。
        """
        from core.runtime_contract import CONTRACT_MARKER, inject_runtime_contract

        html = ("<!doctype html><html><head><title>t</title></head><body>"
                "<script>if (window.__GAME_AGENT__) { window.__GAME_AGENT__.triangles = 1; }</script>"
                "</body></html>")
        injected = inject_runtime_contract(html)
        self.assertIn(CONTRACT_MARKER, injected)


@unittest.skipUnless(_playwright_available(), "需要 playwright 与本地 Chromium 内核浏览器")
class TestContractDoesNotFakeRunningState(unittest.TestCase):
    """没有主循环就是没有主循环，注入按键也不许把 state 说成 playing"""

    def test_idle_page_reports_boot_not_playing(self):
        from core.runtime_contract import inject_runtime_contract
        from pipeline.browser_runtime_adapter import BrowserRuntimeAdapter

        idle_page = ("<!doctype html><html><head></head><body>"
                     "<canvas id='c' width='800' height='600'></canvas></body></html>")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.html"
            path.write_text(inject_runtime_contract(idle_page), encoding="utf-8")
            adapter = BrowserRuntimeAdapter()
            session = adapter.launch(path)
            adapter.run_scenarios(session)
            start = session["scenarios"]["start"]
            self.assertEqual(start["status"], "FAIL")
            self.assertNotEqual(start.get("state"), "playing")
            adapter.close(session)


@unittest.skipUnless(_playwright_available(), "需要 playwright 与本地 Chromium 内核浏览器")
class Test3DShowcaseRuntimeEvidence(unittest.TestCase):
    """3D 团队 M3：必须是真实 WebGL 渲染统计，不是静态解析"""

    def test_showcase_reports_real_render_stats_in_browser(self):
        from pipeline.next_gen_3d_pipeline import NextGen3AShowcaseGenerator
        from pipeline.webgl_runtime_probe import WebGLRuntimeProbe, M3_MATURITY
        from pipeline.browser_runtime_adapter import BrowserRuntimeAdapter

        with tempfile.TemporaryDirectory() as tmp:
            showcase = NextGen3AShowcaseGenerator.generate_showcase_html(
                target_path=Path(tmp) / "index.html"
            )
            adapter = BrowserRuntimeAdapter()
            if adapter._load_driver()[0] is None:
                self.skipTest("无可用浏览器驱动")
            result = WebGLRuntimeProbe.probe_asset(showcase, runtime=adapter.probe_webgl)
            self.assertEqual(result["status"], "SUCCESS")
            self.assertEqual(result["maturity"], M3_MATURITY)
            agent = result["runtime_facts"]["agent"]
            self.assertGreater(agent["triangles"], 0)
            self.assertGreater(agent["draw_calls"], 0)


class TestLiveServiceSandboxHonesty(unittest.TestCase):
    """支付/广告/联机沙箱：无凭据必须报缺失，有响应才允许 PASS"""

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in
                       ("PAYMENT_SANDBOX_URL", "PAYMENT_SANDBOX_KEY",
                        "ADS_SANDBOX_URL", "ADS_SANDBOX_KEY",
                        "MULTIPLAYER_SANDBOX_URL", "MULTIPLAYER_SANDBOX_KEY")}
        for key in self._saved:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_missing_credentials_is_not_pass(self):
        from pipeline.live_service_sandbox import LiveServiceSandbox, NEEDS_SANDBOX_CREDENTIALS

        for kind in ("payment", "ads", "multiplayer"):
            result = LiveServiceSandbox.smoke(kind)
            self.assertEqual(result["status"], NEEDS_SANDBOX_CREDENTIALS)
            self.assertIsNone(result["observed"])

    def test_plaintext_remote_endpoint_is_rejected(self):
        from pipeline.live_service_sandbox import LiveServiceSandbox, NEEDS_SANDBOX_CREDENTIALS

        os.environ["PAYMENT_SANDBOX_URL"] = "http://sandbox.example.com"
        os.environ["PAYMENT_SANDBOX_KEY"] = "k"
        result = LiveServiceSandbox.smoke("payment")
        self.assertEqual(result["status"], NEEDS_SANDBOX_CREDENTIALS)
        self.assertIn("https", result["errors"][0])

    def test_real_local_sandbox_passes_and_bad_service_fails(self):
        from pipeline import live_service_sandbox as ls

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.endswith("/health"):
                    body = json.dumps({"service": "payment-sandbox", "status": "ok"}).encode()
                    self.send_response(200)
                else:
                    body = b'{"service":"ads-sandbox"}'
                    self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            os.environ["PAYMENT_SANDBOX_URL"] = base
            os.environ["PAYMENT_SANDBOX_KEY"] = "sandbox-key"
            ok = ls.LiveServiceSandbox.smoke("payment")
            self.assertEqual(ok["status"], "PASS")
            self.assertEqual(ok["observed"]["status_code"], 200)

            # 对端返回 200 但不自证支付身份，不能算沙箱通过
            os.environ["ADS_SANDBOX_URL"] = base
            os.environ["ADS_SANDBOX_KEY"] = "sandbox-key"
            wrong = ls.LiveServiceSandbox.smoke("ads")
            self.assertEqual(wrong["status"], "FAIL")
        finally:
            server.shutdown()
            server.server_close()


class TestGodotAdapterHonesty(unittest.TestCase):
    """Godot 适配器：没有引擎就 NEEDS_RUNTIME_TOOL，有引擎才按真实输出裁决"""

    def _project(self, tmp: str) -> Path:
        project = Path(tmp) / "godot_project"
        project.mkdir(parents=True, exist_ok=True)
        (project / "project.godot").write_text('config_version=5\n[application]\n', encoding="utf-8")
        return project

    def test_without_engine_is_needs_runtime_tool(self):
        from pipeline.godot_runtime_adapter import GodotRuntimeAdapter

        adapter = GodotRuntimeAdapter(godot_executable="")
        self.assertFalse(adapter.preflight("godot")["can_launch"])
        with tempfile.TemporaryDirectory() as tmp:
            session = adapter.launch(self._project(tmp))
            self.assertEqual(session["status"], "NEEDS_RUNTIME_TOOL")
            result = adapter.run_scenarios(session)
            self.assertEqual(result["status"], "NEEDS_RUNTIME_TOOL")

    def test_missing_project_is_blocked_by_static_validation(self):
        from pipeline.godot_runtime_adapter import GodotRuntimeAdapter

        adapter = GodotRuntimeAdapter(godot_executable="fake-godot")
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "not_a_project"
            empty.mkdir()
            session = adapter.launch(empty)
            self.assertEqual(session["status"], "BLOCKED_BY_STATIC_VALIDATION")

    @staticmethod
    def _fake_engine(stdout: str = "", stderr: str = "", returncode: int = 0):
        class _Completed:
            def __init__(self):
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = returncode
        return lambda *a, **k: _Completed()

    def test_real_frames_yield_pass(self):
        from pipeline import godot_runtime_adapter as gda
        from pipeline.godot_runtime_adapter import GodotRuntimeAdapter

        adapter = GodotRuntimeAdapter(godot_executable="fake-godot")
        original = gda.subprocess.run
        gda.subprocess.run = self._fake_engine(stdout="GAME_AGENT_PROBE_START\nGAME_AGENT_CONTRACT {\"frames\": 120}\n")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                project = self._project(tmp)
                session = adapter.launch(project)
                result = adapter.run_scenarios(session)
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(session["scenarios"]["core_loop"]["status"], "PASS")
                self.assertEqual(session["metrics"]["frames"], 120)
                self.assertTrue((project / gda.PROBE_FILENAME).exists())
                adapter.close(session)
                self.assertFalse((project / gda.PROBE_FILENAME).exists())
        finally:
            gda.subprocess.run = original

    def test_script_errors_yield_fail(self):
        from pipeline import godot_runtime_adapter as gda
        from pipeline.godot_runtime_adapter import GodotRuntimeAdapter

        adapter = GodotRuntimeAdapter(godot_executable="fake-godot")
        original = gda.subprocess.run
        gda.subprocess.run = self._fake_engine(stderr="SCRIPT ERROR: Parse Error: bad indent\n", returncode=1)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                session = adapter.launch(self._project(tmp))
                result = adapter.run_scenarios(session)
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(session["metrics"]["godot_error_count"], 1)
        finally:
            gda.subprocess.run = original


class TestReleaseGatesAreEvaluated(unittest.TestCase):
    """G6/G7 必须真实裁决；生产提升不得用 Preview 资格顶替审批"""

    def _run_dir(self, tmp: str) -> Path:
        return Path(tmp) / "run_x"

    def _decide(self, gate_engine, gate_id: str, passed: bool) -> Any:
        return gate_engine.evaluate(gate_id, passed=passed).to_dict()

    def test_g6_passes_only_when_g0_to_g5_pass(self):
        from core.artifact_store import ArtifactStore
        from core.gate_engine import GateEngine

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._run_dir(tmp)
            engine = GateEngine(ArtifactStore(run_dir))
            decisions = [self._decide(engine, g, True) for g in ("G0", "G1", "G2", "G3", "G4", "G5")]
            g6 = engine.evaluate_release_gate("G6", decisions)
            self.assertEqual(g6.result, "PASS")

            broken = decisions[:-1] + [self._decide(engine, "G5", False)]
            g6_fail = engine.evaluate_release_gate("G6", broken)
            self.assertEqual(g6_fail.result, "FAIL")
            self.assertIn("gate_not_passed:G5", g6_fail.reason_codes)

    def test_g7_requires_g6_and_release_manager_approval(self):
        from core.artifact_store import ArtifactStore
        from core.gate_engine import GateEngine

        with tempfile.TemporaryDirectory() as tmp:
            engine = GateEngine(ArtifactStore(self._run_dir(tmp)))
            decisions = [self._decide(engine, g, True) for g in ("G0", "G1", "G2", "G3", "G4", "G5")]
            decisions.append(engine.evaluate_release_gate("G6", decisions).to_dict())

            approved = {"role": "release_manager", "approved": True, "identity": "alice"}
            self.assertEqual(engine.evaluate_release_gate("G7", decisions, approval=approved).result, "PASS")

            no_approval = engine.evaluate_release_gate("G7", decisions)
            self.assertEqual(no_approval.result, "FAIL")
            self.assertIn("approval_required:release_manager", no_approval.reason_codes)

            wrong_role = {"role": "developer", "approved": True}
            self.assertEqual(engine.evaluate_release_gate("G7", decisions, approval=wrong_role).result, "FAIL")

            without_g6 = [d for d in decisions if d["gate_id"] != "G6"]
            self.assertIn("gate_not_passed:G6",
                          engine.evaluate_release_gate("G7", without_g6, approval=approved).reason_codes)

    def test_production_candidate_blocked_without_g7(self):
        from core.artifact_store import ArtifactStore
        from core.gate_engine import GateEngine
        from core.release_service import ReleaseService, ReleaseBlockedError
        from core.contracts import ArtifactRef

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._run_dir(tmp)
            store = ArtifactStore(run_dir)
            engine = GateEngine(store)
            decisions = [self._decide(engine, g, True) for g in ("G0", "G1", "G2", "G3", "G4", "G5")]
            decisions.append(engine.evaluate_release_gate("G6", decisions).to_dict())
            ref = store.put_bytes("GameBuild", b"<html></html>", artifact_id="build-1")
            kwargs = dict(
                candidate_artifact=ref,
                intent_ref="i", spec_ref="s", workflow_ref="w", evidence_ref="e",
                decisions=decisions,
                approval={"role": "release_manager", "approved": True, "identity": "alice"},
            )
            svc = ReleaseService(store)
            self.assertEqual(svc.create_candidate(channel="preview", **kwargs).release_status, "candidate")
            with self.assertRaises(ReleaseBlockedError):
                svc.create_candidate(channel="production", **kwargs)


class TestRunServiceGateStrength(unittest.TestCase):
    """门禁强度：G3 不得只看文件存在，run 目录不得被穿越"""

    def test_build_artifact_validation(self):
        from core.run_service import RunService

        ok, reasons = RunService._validate_build_artifact(None)
        self.assertFalse(ok)
        self.assertIn("build_artifact_missing", reasons)

        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.html"
            empty.write_text("", encoding="utf-8")
            ok, reasons = RunService._validate_build_artifact(str(empty))
            self.assertFalse(ok)
            self.assertIn("build_artifact_empty", reasons)

            plain = Path(tmp) / "readme.txt"
            plain.write_text("not a game", encoding="utf-8")
            ok, reasons = RunService._validate_build_artifact(str(plain))
            self.assertFalse(ok)
            self.assertIn("build_artifact_not_html_document", reasons)

            game = Path(tmp) / "game.html"
            game.write_text(_MINIMAL_HTML, encoding="utf-8")
            ok, reasons = RunService._validate_build_artifact(str(game))
            self.assertTrue(ok)
            self.assertEqual(reasons, [])

    def test_release_gate_is_shared_by_every_entrypoint(self):
        from core.run_service import RunService

        service = RunService()
        self.assertTrue(service.check_release_gate("distribute", ""))
        self.assertTrue(service.check_release_gate("distribute", "run_not_exist"))
        self.assertTrue(service.check_release_gate("submit", "../../.."))
        # 有 ReleaseManifest 的 run 才放行：用真实 run 目录验证
        released = [d for d in service.output_dir.iterdir()
                    if d.is_dir() and RunService.classify_run(d) == "released"]
        if released:
            self.assertEqual(service.check_release_gate("distribute", released[0].name), "")

    def test_run_status_rejects_path_traversal(self):
        from core.run_service import RunService
        from core.security_guard import SecurityGuardError

        service = RunService()
        for hostile in ("../../..", "../", "/etc/passwd"):
            with self.assertRaises(SecurityGuardError):
                service.get_run_status(hostile)


class TestStagingPromotionAndRollback(unittest.TestCase):
    """Staging 晋升必须有真实部署证据；回滚必须留审计"""

    def _build_preview_run(self, tmp: str) -> Any:
        from core.artifact_store import ArtifactStore
        from core.gate_engine import GateEngine
        from core.release_service import ReleaseService

        run_dir = Path(tmp) / "output" / "runs" / "run_x"
        store = ArtifactStore(run_dir)
        engine = GateEngine(store)
        decisions = [engine.evaluate(g, passed=True).to_dict()
                     for g in ("G0", "G1", "G2", "G3", "G4", "G5")]
        decisions.append(engine.evaluate_release_gate("G6", decisions).to_dict())
        ref = store.put_bytes("GameBuild", _MINIMAL_HTML.encode("utf-8"), artifact_id="build-1")
        ReleaseService(store).create_candidate(
            channel="preview", candidate_artifact=ref, intent_ref="i", spec_ref="s",
            workflow_ref="w", evidence_ref="e", decisions=decisions)
        return run_dir

    @staticmethod
    def _staging_server():
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - stdlib callback name
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"staging ok")

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server

    def test_staging_promotion_requires_real_deployment_and_qa_role(self):
        from core.run_service import RunService
        from core.release_service import ReleaseBlockedError

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._build_preview_run(tmp)
            service = RunService(workspace=Path(tmp))

            saved = os.environ.get("STAGING_BASE_URL")
            os.environ.pop("STAGING_BASE_URL", None)
            try:
                with self.assertRaises(ReleaseBlockedError):
                    service.promote_to_staging("run_x", {"role": "qa_manager", "approved": True, "identity": "qa1"})
                with self.assertRaises(ReleaseBlockedError):
                    service.promote_to_staging("run_x", {"role": "developer", "approved": True, "identity": "dev1"})

                server = self._staging_server()
                os.environ["STAGING_BASE_URL"] = f"http://127.0.0.1:{server.server_port}/"
                try:
                    result = service.promote_to_staging(
                        "run_x", {"role": "qa_manager", "approved": True, "identity": "qa1"})
                    self.assertEqual(result["channel"], "staging")
                    self.assertEqual(result["staging_smoke"]["status"], "PASS")
                    self.assertEqual(result["staging_smoke"]["observed"]["status_code"], 200)

                    # 生产候选必须先有具名人工复核（美术/音频/出货包），否则机器门禁全绿也不放行
                    from pipeline.human_review import HumanReviewBoard
                    reviews_dir = Path(tmp) / "reviews"
                    saved_review_root = os.environ.get("GAME_REVIEW_ROOT")
                    os.environ["GAME_REVIEW_ROOT"] = str(reviews_dir)
                    try:
                        with self.assertRaises(ReleaseBlockedError):
                            service.promote_to_production(
                                "run_x", {"role": "release_manager", "approved": True, "identity": "alice"})

                        board = HumanReviewBoard()
                        for kind in ("art", "audio", "release"):
                            artifact = Path(tmp) / f"{kind}_artifact.bin"
                            artifact.write_bytes(f"{kind}-bytes".encode("utf-8"))
                            ticket = board.create_ticket("run_x", kind, artifact)
                            board.submit(ticket["ticket_id"], "human_reviewer_qa", "APPROVED",
                                         notes="离线验收：具名复核通过")

                        production = service.promote_to_production(
                            "run_x", {"role": "release_manager", "approved": True, "identity": "alice"})
                    finally:
                        if saved_review_root is not None:
                            os.environ["GAME_REVIEW_ROOT"] = saved_review_root
                        else:
                            os.environ.pop("GAME_REVIEW_ROOT", None)
                    self.assertEqual(production["channel"], "production")
                    self.assertEqual(production["release_status"], "approved")

                    rolled = service.rollback("run_x", "回归缺陷", {"role": "release_manager", "identity": "alice"})
                    self.assertEqual(rolled["status"], "rolled_back")
                    self.assertEqual(sorted(rolled["channels"]), ["production", "staging"])
                    self.assertEqual(len(rolled["rolled_back"]), 2)

                    from core.audit_log import AuditLog
                    self.assertTrue(AuditLog(run_dir).verify()["passed"])
                finally:
                    server.shutdown()
                    server.server_close()
            finally:
                if saved is not None:
                    os.environ["STAGING_BASE_URL"] = saved

    def test_release_drill_blocks_every_violation(self):
        from pipeline.release_drill import ReleaseDrill

        report = ReleaseDrill.run()
        self.assertEqual(report["status"], "PASS", report["cases"])
        self.assertEqual(report["total"], 6)
        self.assertTrue(all(c["actual"].startswith("blocked") for c in report["cases"]))


class TestStoreSubmissionHonesty(unittest.TestCase):
    """渠道上架：包打好了 ≠ 已上架；缺素材/缺凭据/缺上传器都必须如实报"""

    def _png(self, path: Path, width: int, height: int) -> Path:
        import struct
        import zlib

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        raw = b"".join(b"\x00" + b"\xff\xff\xff" * width for _ in range(height))
        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
        path.write_bytes(png)
        return path

    def _full_metadata(self) -> dict:
        return {
            "title": "星际防线", "short_desc": "一款竖版割草生存游戏", "long_desc": "长描述" * 10,
            "keywords": "割草,生存,roguelike", "category": "动作", "age_rating": "12+",
            "privacy_policy_url": "https://example.com/privacy", "publisher": "某工作室",
            "version": "1.0.0", "supported_languages": "简体中文", "price_tier": "free",
            "start_url": "/", "third_party_sdks": ["payment", "ads"],
        }

    def _prepare(self, tmp: str):
        dist_root = Path(tmp) / "dist"
        (dist_root / "wechat").mkdir(parents=True)
        (dist_root / "wechat" / "game.js").write_text("console.log(1)", encoding="utf-8")
        assets = Path(tmp) / "store_assets"
        assets.mkdir()
        for name, w, h in (("icon.png", 256, 256), ("screenshot_1.png", 1280, 720),
                           ("screenshot_2.png", 1280, 720)):
            self._png(assets / name, w, h)
        return dist_root, assets

    def test_missing_metadata_and_assets_are_blocked(self):
        from pipeline.store_submission import StoreSubmission, BLOCKED

        with tempfile.TemporaryDirectory() as tmp:
            dist_root, assets = self._prepare(tmp)
            service = StoreSubmission(dist_root, Path(tmp) / "submission")

            empty = service.check_readiness("wechat", {}, assets)
            self.assertEqual(empty["status"], BLOCKED)
            self.assertTrue(any("元数据字段" in e for e in empty["errors"]))

            partial = dict(self._full_metadata(), privacy_policy_url="http://insecure.example.com")
            partial_report = service.check_readiness("wechat", partial, assets)
            self.assertTrue(any("隐私政策" in f["rule"] and f["status"] == "FAIL"
                                for f in partial_report["findings"]))

            undersized = Path(tmp) / "small_assets"
            undersized.mkdir()
            self._png(undersized / "icon.png", 64, 64)
            self._png(undersized / "screenshot_1.png", 1280, 720)
            self._png(undersized / "screenshot_2.png", 1280, 720)
            size_report = service.check_readiness("wechat", self._full_metadata(), undersized)
            self.assertTrue(any("素材 icon" in f["rule"] and f["status"] == "FAIL"
                                for f in size_report["findings"]))

    def test_ready_bundle_still_refuses_to_claim_submission(self):
        from pipeline.store_submission import (StoreSubmission, READY,
                                               NEEDS_SANDBOX_CREDENTIALS, NEEDS_RUNTIME_TOOL)

        with tempfile.TemporaryDirectory() as tmp:
            dist_root, assets = self._prepare(tmp)
            service = StoreSubmission(dist_root, Path(tmp) / "submission")

            ready = service.build_bundle("wechat", self._full_metadata(), assets)
            self.assertEqual(ready["status"], READY)
            self.assertEqual(len(ready["copied_assets"]), 3)
            self.assertTrue(Path(ready["bundle_path"], "store_metadata.json").is_file())

            saved = {k: os.environ.get(k) for k in ("WECHAT_APPID", "WECHAT_CI_KEY_PATH")}
            for key in saved:
                os.environ.pop(key, None)
            try:
                no_cred = service.submit("wechat", self._full_metadata(), dry_run=True, assets_dir=assets)
                self.assertEqual(no_cred["status"], NEEDS_SANDBOX_CREDENTIALS)

                os.environ["WECHAT_APPID"] = "wx_test"
                os.environ["WECHAT_CI_KEY_PATH"] = str(Path(tmp) / "private.key")
                (Path(tmp) / "private.key").write_text("key", encoding="utf-8")
                no_tool = service.submit("wechat", self._full_metadata(), dry_run=True, assets_dir=assets)
                self.assertIn(no_tool["status"], (NEEDS_RUNTIME_TOOL, READY))
                self.assertNotEqual(no_tool["status"], "SUBMITTED")
            finally:
                for key, value in saved.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
