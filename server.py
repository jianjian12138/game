#!/usr/bin/env python3
"""
server.py: 游戏开发多智能体工作室 Web 服务
纯 Python 3.9+ 标准库 http.server 实现，零外部依赖，极速开箱即用。
"""
import sys
import os
import json
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from core.registry import get_all_agents, GAME_SKILLS, get_stats
from core.studio_engine import studio_engine
from pipeline.rules_researcher import RulesResearcher

class StudioHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # 静默常规访问日志

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/agents":
            agents = get_all_agents()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(agents, ensure_ascii=False).encode("utf-8"))

        elif path == "/api/skills":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(GAME_SKILLS, ensure_ascii=False).encode("utf-8"))

        elif path == "/api/stats":
            stats = get_stats()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(stats, ensure_ascii=False).encode("utf-8"))

        else:
            # 静态文件
            if path in ("", "/"):
                target = ROOT / "dashboard" / "index.html"
            elif path.startswith("/output/"):
                target = ROOT / "output" / path[8:]
            else:
                target = ROOT / "dashboard" / path.lstrip("/")

            if target.exists() and target.is_file():
                ctype = "text/html; charset=utf-8"
                if target.suffix == ".css": ctype = "text/css; charset=utf-8"
                elif target.suffix == ".js": ctype = "application/javascript; charset=utf-8"
                elif target.suffix == ".json": ctype = "application/json; charset=utf-8"
                
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.end_headers()
                self.wfile.write(target.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/create":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            data = json.loads(body)
            title = data.get("title", "中国象棋")
            genre = data.get("genre", "")
            custom_rules = data.get("custom_rules", "")
            
            res = studio_engine.create_game_pipeline(title=title, genre=genre, custom_rules=custom_rules)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))

        elif path == "/api/research_rules":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            data = json.loads(body)
            q = data.get("query", "")
            res = RulesResearcher.research_game_rules(q)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

def run_server(port: int = 8090, open_browser: bool = False):
    server = HTTPServer(("0.0.0.0", port), StudioHTTPHandler)
    url = f"http://localhost:{port}"
    print("=" * 65)
    print("  🎮 Game Dev Agent Studios 工作室控制台已启动")
    print(f"  🌐 浏览器访问: {url}")
    print("=" * 65)
    if open_browser:
        try: webbrowser.open(url)
        except Exception: pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Game Dev Agent Studios 中控台服务")
    parser.add_argument("port", nargs="?", type=int, default=8090, help="监听端口 (默认 8090)")
    parser.add_argument("--port", "-p", dest="opt_port", type=int, default=None, help="监听端口")
    parser.add_argument("--browser", "-b", action="store_true", help="自动打开浏览器")
    args = parser.parse_args()
    port = args.opt_port or args.port
    run_server(port=port, open_browser=args.browser)
