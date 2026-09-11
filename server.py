#!/usr/bin/env python3
"""
server.py: 游戏开发多智能体工作室 Web 服务
纯 Python 3.10+ 标准库 http.server 实现，零外部依赖，安全加固版。
"""
import sys
import json
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from core.registry import get_all_agents, get_all_teams, GAME_SKILLS, get_stats
from core.studio_engine import studio_engine
from core.security_guard import (
    get_configured_token,
    global_rate_limiter,
    has_valid_bearer_token,
    is_loopback_host,
    safe_resolve_path,
    SecurityGuardError,
)
from pipeline.rules_researcher import RulesResearcher

MAX_PAYLOAD_BYTES = 5 * 1024 * 1024  # 5MB 限制

class StudioHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 记录关键访问日志供安全审计
        sys.stderr.write(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}\n")

    def _check_auth_and_rate_limit(self) -> bool:
        client_ip = self.client_address[0] if self.client_address else "127.0.0.1"
        if not global_rate_limiter.is_allowed(client_ip):
            self.send_json(429, {"error": "Too Many Requests: Rate limit exceeded"})
            return False

        require_auth = bool(getattr(self.server, "require_auth", False))
        expected_token = getattr(self.server, "expected_token", "")
        if require_auth and not has_valid_bearer_token(self.headers, expected_token):
            self.send_json(401, {"error": "Unauthorized: valid Bearer GAME_STUDIO_TOKEN required"})
            return False
        return True

    def send_json(self, status_code: int, data: any):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if not self._check_auth_and_rate_limit():
            return
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/agents":
            self.send_json(200, get_all_agents())

        elif path == "/api/skills":
            self.send_json(200, GAME_SKILLS)

        elif path == "/api/teams":
            self.send_json(200, get_all_teams())

        elif path == "/api/stats":
            self.send_json(200, get_stats())

        elif path == "/api/departments":
            stats = get_stats()
            self.send_json(200, stats.get("departments", {}))

        elif path == "/api/templates":
            templates = [
                {"id": "survivor_danmaku", "name": "赛博弹幕幸存者 (Roguelike Survivor)", "genre": "2D弹幕射击"},
                {"id": "card_deck_builder", "name": "深渊爬塔卡牌构筑 (Deck Builder)", "genre": "策略卡牌"},
                {"id": "titan_mech_2d", "name": "泰坦机甲工业引擎演示 (Industrial 2D)", "genre": "动作射击"},
                {"id": "humanoid_3d", "name": "3D 人形骨骼蒙皮动画 (Skeletal 3D)", "genre": "3D动作"},
                {"id": "next_gen_3a_pbr", "name": "3A 次时代物理材质与 LOD 展台 (Next-Gen 3D PBR/LOD)", "genre": "3D次时代"}
            ]
            self.send_json(200, templates)

        elif path == "/api/toolchain":
            from core.environment_inspector import EnvironmentInspector
            manifest = EnvironmentInspector.get_toolchain_manifest()
            self.send_json(200, manifest)

        elif path == "/api/preflight":
            from core.environment_inspector import EnvironmentInspector
            # 支持 query 参数 ?target=web 或 target=godot
            query_params = dict(qp.split("=", 1) for qp in parsed.query.split("&") if "=" in qp) if parsed.query else {}
            target = query_params.get("target", "web")
            pf = EnvironmentInspector.preflight_check(target)
            self.send_json(200, pf)

        else:
            # 静态文件路由（SEC-001 深度防御路径穿越）
            dashboard_root = (ROOT / "dashboard").resolve()
            output_root = (ROOT / "output").resolve()
            target: Path = None

            try:
                if path in ("", "/"):
                    target = (dashboard_root / "index.html").resolve()
                elif path.startswith("/output/"):
                    sub_path = path[8:].lstrip("/\\")
                    candidate = (output_root / sub_path).resolve()
                    if candidate.is_relative_to(output_root):
                        target = candidate
                else:
                    sub_path = path.lstrip("/\\")
                    candidate = (dashboard_root / sub_path).resolve()
                    if candidate.is_relative_to(dashboard_root):
                        target = candidate
            except (ValueError, RuntimeError):
                target = None

            if not target:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"403 Forbidden: Path Traversal Denied")
                return

            if target.exists() and target.is_file():
                ctype = "text/html; charset=utf-8"
                if target.suffix == ".css": ctype = "text/css; charset=utf-8"
                elif target.suffix == ".js": ctype = "application/javascript; charset=utf-8"
                elif target.suffix == ".json": ctype = "application/json; charset=utf-8"
                elif target.suffix in (".png", ".jpg", ".jpeg", ".webp"): ctype = f"image/{target.suffix.lstrip('.')}"
                
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(target.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        if not self._check_auth_and_rate_limit():
            return
        parsed = urlparse(self.path)
        path = parsed.path

        # SEC-004 Content-Type 与 Body 大小检查
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            self.send_json(415, {"error": "Unsupported Media Type: expected application/json"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            length = 0

        if length > MAX_PAYLOAD_BYTES:
            self.send_json(413, {"error": "Payload Too Large: max 5MB allowed"})
            return

        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_json(400, {"error": "Malformed JSON in request body"})
            return

        if path == "/api/v1/runs":
            from core.run_service import run_service
            intent = run_service.create_intent(
                title=str(data.get("title", "未命名游戏"))[:100],
                genre=str(data.get("genre", "2D 独立游戏"))[:50],
                custom_rules=str(data.get("custom_rules", ""))[:1000],
                source="http_v1",
                subject_id=str(data.get("subject_id", "local"))[:100],
                profile=str(data.get("profile", "web_survivor_vertical_v1"))[:80],
            )

            # 仅受理不执行：调用方显式传 "execute": false 时使用。
            # 此时 run 停在 G0-G2，必须重新 POST（默认 execute）才会真正构建与验证。
            if data.get("execute") is False:
                prepared = run_service.prepare(intent)
                self.send_json(202, {
                    "status": "accepted_not_executed",
                    "run_id": intent.run_id,
                    "intent_id": intent.intent_id,
                    "spec_id": prepared["spec"].spec_id,
                    "plan_id": prepared["plan"].plan_id,
                    "next": "/api/v1/runs",
                    "note": "当前 run 仅完成契约准备，未执行构建与运行时验证",
                })
                return

            res = run_service.execute_run(
                intent,
                mode=str(data.get("mode", "fast"))[:20],
                llm_provider=str(data.get("llm_provider", "gemini"))[:30],
            )
            self.send_json(200, {
                "status": res.get("status"),
                "run_id": res.get("run_id"),
                "intent_id": res.get("intent_id"),
                "spec_id": res.get("spec_id"),
                "plan_id": res.get("plan_id"),
                "game_file": res.get("game_file"),
                "gate_decisions": res.get("gate_decisions"),
                "verification_coverage": res.get("verification_coverage"),
                "release_eligible": res.get("release_eligible"),
            })

        elif path.startswith("/api/v1/runs/") and path.endswith("/status"):
            from core.run_service import run_service
            run_id = path[len("/api/v1/runs/"):-len("/status")].strip("/")
            try:
                self.send_json(200, run_service.get_run_status(run_id))
            except FileNotFoundError:
                self.send_json(404, {"error": "Run not found"})
            except SecurityGuardError as exc:
                self.send_json(400, {"error": f"Invalid run id: {exc}"})

        elif path.startswith("/api/v1/runs/") and path.endswith("/promote"):
            from core.run_service import run_service
            from core.release_service import ReleaseBlockedError
            run_id = path[len("/api/v1/runs/"):-len("/promote")].strip("/")
            approval = data.get("approval")
            if not isinstance(approval, dict) or not approval.get("identity"):
                self.send_json(400, {"error": "approval must be an object with role, approved and identity"})
                return
            approval = {
                "role": str(approval.get("role", ""))[:50],
                "approved": bool(approval.get("approved")),
                "identity": str(approval.get("identity"))[:100],
                "reason": str(approval.get("reason", ""))[:200],
            }
            channel = str(data.get("channel", "production"))
            if channel not in ("staging", "production"):
                self.send_json(400, {"error": "channel must be 'staging' or 'production'"})
                return
            try:
                manifest = (run_service.promote_to_staging(run_id, approval) if channel == "staging"
                            else run_service.promote_to_production(run_id, approval))
            except FileNotFoundError:
                self.send_json(404, {"error": "Run not found"})
            except SecurityGuardError as exc:
                self.send_json(400, {"error": f"Invalid run id: {exc}"})
            except ReleaseBlockedError as exc:
                self.send_json(409, {"error": str(exc), "run_id": run_id})
            else:
                self.send_json(200, {
                    "status": f"{channel}_promoted",
                    "run_id": run_id,
                    "release_channel": manifest.get("release_channel"),
                    "release_status": manifest.get("release_status"),
                    "release_id": manifest.get("release_id"),
                    "staging_smoke": manifest.get("staging_smoke"),
                })

        elif path.startswith("/api/v1/runs/") and path.endswith("/rollback"):
            from core.run_service import run_service
            from core.release_service import ReleaseBlockedError
            run_id = path[len("/api/v1/runs/"):-len("/rollback")].strip("/")
            reason = str(data.get("reason", ""))[:500]
            if not reason:
                self.send_json(400, {"error": "reason is required"})
                return
            actor = data.get("actor")
            if not isinstance(actor, dict) or not actor.get("identity"):
                self.send_json(400, {"error": "actor must be an object with role and identity"})
                return
            actor = {"role": str(actor.get("role", "release_manager"))[:50],
                     "identity": str(actor.get("identity"))[:100]}
            try:
                result = run_service.rollback(run_id, reason, actor)
            except FileNotFoundError:
                self.send_json(404, {"error": "Run not found"})
            except SecurityGuardError as exc:
                self.send_json(400, {"error": f"Invalid run id: {exc}"})
            except ReleaseBlockedError as exc:
                self.send_json(409, {"error": str(exc), "run_id": run_id})
            else:
                self.send_json(200, {"status": "rolled_back", "run_id": run_id, **result})

        elif path == "/api/v1/release-drill":
            from pipeline.release_drill import ReleaseDrill
            report = ReleaseDrill.run()
            self.send_json(200 if report["status"] == "PASS" else 500, report)

        elif path == "/api/create" or path == "/api/generate":
            title = str(data.get("title", "中国象棋"))[:100]
            genre = str(data.get("genre", ""))[:50]
            custom_rules = str(data.get("custom_rules", ""))[:1000]
            
            from core.run_service import run_service
            res = run_service.create_game(
                title=title,
                genre=genre,
                custom_rules=custom_rules,
                source="http_legacy",
            )
            res["deprecated_endpoint"] = True
            res["replacement"] = "/api/v1/runs"
            self.send_json(200, res)

        elif path == "/api/research_rules":
            q = str(data.get("query", ""))[:100]
            res = RulesResearcher.research_game_rules(q)
            self.send_json(200, res)

        elif path == "/api/audit":
            from pipeline.adversarial_red_team import RedTeamInquisitor
            target_html = data.get("html", "")
            if not target_html:
                target_path = ROOT / "pipeline" / "templates" / "cyber_survivor_master.html"
                target_html = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
            veto_res = RedTeamInquisitor.indict_game_code(target_html)
            self.send_json(200, veto_res)

        else:
            self.send_json(404, {"error": "Endpoint not found"})

def run_server(host: str = "127.0.0.1", port: int = 8090, open_browser: bool = False):
    is_loopback = is_loopback_host(host)
    expected_token = get_configured_token()
    if not is_loopback and not expected_token:
        raise RuntimeError(
            f"拒绝启动：监听地址 '{host}' 不是回环地址，必须先配置 GAME_STUDIO_TOKEN。"
        )

    server = HTTPServer((host, port), StudioHTTPHandler)
    server.require_auth = not is_loopback
    server.expected_token = expected_token
    url = f"http://{host}:{port}"
    print("=" * 65)
    print("  🎮 Universal Game Dev Agent Studio 工作室控制台已启动")
    print(f"  🌐 访问地址: {url} (绑定: {host})")
    print("  🔒 安全模式: 本地回环保护、静态路径穿越防御、JSON Payload 校验已就绪")
    print("=" * 65)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception as e:
            sys.stderr.write(f"浏览器打开提示: {e}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已安全停止。")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Universal Game Dev Agent Studio 中控台服务")
    parser.add_argument("port", nargs="?", type=int, default=8090, help="监听端口 (默认 8090)")
    parser.add_argument("--host", default="127.0.0.1", help="监听主机IP (默认 127.0.0.1 本地回环安全防护)")
    parser.add_argument("--port", "-p", dest="opt_port", type=int, default=None, help="监听端口")
    parser.add_argument("--browser", "-b", action="store_true", help="自动打开浏览器")
    args = parser.parse_args()
    port = args.opt_port or args.port
    run_server(host=args.host, port=port, open_browser=args.browser)
