#!/usr/bin/env python3
"""
server.py: 游戏开发多智能体工作室 Web 服务
纯 Python 3.10+ 标准库 http.server 实现，零外部依赖，安全加固版。
"""
import sys
import os
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

from core.registry import get_all_agents, GAME_SKILLS, get_stats
from core.studio_engine import studio_engine
from core.security_guard import safe_resolve_path, global_rate_limiter, SecurityGuardError
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

        expected_token = os.environ.get("GAME_STUDIO_TOKEN", "").strip()
        if expected_token:
            auth_header = self.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "").strip()
            if token != expected_token:
                self.send_json(401, {"error": "Unauthorized: Invalid or missing GAME_STUDIO_TOKEN"})
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

        if path in ("/api/create", "/api/generate"):
            title = str(data.get("title", "中国象棋"))[:100]
            genre = str(data.get("genre", ""))[:50]
            custom_rules = str(data.get("custom_rules", ""))[:1000]
            
            res = studio_engine.create_game_pipeline(title=title, genre=genre, custom_rules=custom_rules)
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
    server = HTTPServer((host, port), StudioHTTPHandler)
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
