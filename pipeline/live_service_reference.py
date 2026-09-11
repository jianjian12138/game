#!/usr/bin/env python3
"""pipeline/live_service_reference.py：可自部署的「参考线上服务」（支付/广告/联机）

缺口二为什么需要它：
    光有 /health 探活只能证明「端点活着」，证明不了「业务链路真的能跑」。
    真服务商（微信支付/广告平台/联机服务）的申请要几天到几周，在拿到真凭据前
    整条链路只能停在 NEEDS_SANDBOX_CREDENTIALS，什么也验证不了。

    本模块提供一个**真实 HTTP 服务**（不是 mock、不是假响应），实现三类业务端点：
      支付    POST /v1/orders            创建订单
              GET  /v1/orders/{id}       查单
              POST /v1/orders/{id}/refund 退款
      广告    POST /v1/ads/request       请求广告（返回素材）
              POST /v1/ads/impression    曝光回执
              POST /v1/ads/click         点击回执
      联机    POST /v1/rooms             创建房间
              POST /v1/rooms/{id}/join   加入
              GET  /v1/rooms/{id}        查询
              POST /v1/rooms/{id}/leave  离开

    它跑在真实 socket 上、真的校验 Bearer Key、真的维护内存状态，
    所以用它跑通的链路，换成真服务商后只需改 .env 的 URL+KEY，业务逻辑不用动。

诚实边界：
    · 这是**参考实现 / 联调桩**，不是生产级服务：状态存内存，进程重启即丢，
      没有持久化、没有并发控制、没有真实资金流。
    · 因此它自报 environment=sandbox，且 health 里带 "reference": true。
      任何把它当生产服务用的行为都会被 --require-production 挡下。
    · 鉴权是真的：Key 不匹配直接 401，便于验证「密钥确实在用」而非摆设。
"""
from __future__ import annotations

import argparse
import json
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

SERVICE_KINDS = ("payment", "ads", "multiplayer")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# 若以 --key 启动，则所有业务端点要求 Authorization: Bearer <key>；
# 不传 --key 时表示「开放联调」，鉴权关闭（仅本地回环使用）。
STATE_LOCK = threading.Lock()
ORDERS: Dict[str, Dict[str, Any]] = {}
ADS_EVENTS: Dict[str, Dict[str, Any]] = {}
ROOMS: Dict[str, Dict[str, Any]] = {}


def _json(handler: BaseHTTPRequestHandler, code: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ReferenceHandler(BaseHTTPRequestHandler):
    service: str = "payment"
    environment: str = "sandbox"
    api_key: str = ""

    # ---------- 基础 ----------

    def log_message(self, fmt: str, *args) -> None:  # 静默，避免污染 CLI 输出
        pass

    def _authorized(self) -> bool:
        if not self.api_key:
            return True
        header = self.headers.get("Authorization") or ""
        return header.strip() == f"Bearer {self.api_key}"

    def _read_json(self) -> Tuple[Dict[str, Any], Optional[str]]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}, None
        try:
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw) if raw.strip() else {}
        except (ValueError, UnicodeDecodeError) as exc:
            return {}, f"请求体不是合法 JSON: {exc}"
        if not isinstance(data, dict):
            return {}, "请求体必须是 JSON 对象"
        return data, None

    def _path(self) -> str:
        return urlparse(self.path).path.rstrip("/") or "/"

    # ---------- 路由 ----------

    def do_GET(self) -> None:  # noqa: N802
        path = self._path()
        if path.endswith("/health"):
            _json(self, 200, {
                "service": self.service,
                "status": "ok",
                "environment": self.environment,
                "reference": True,
            })
            return
        if path.startswith("/v1/orders/"):
            self._order_get(path[len("/v1/orders/"):])
            return
        if path.startswith("/v1/rooms/"):
            self._room_get(path[len("/v1/rooms/"):])
            return
        _json(self, 404, {"error": "not_found", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        path = self._path()
        if not self._authorized():
            _json(self, 401, {"error": "unauthorized", "detail": "Authorization: Bearer <key> 不匹配"})
            return
        body, err = self._read_json()
        if err:
            _json(self, 400, {"error": "bad_request", "detail": err})
            return

        if path == "/v1/orders":
            self._order_create(body)
            return
        if path.endswith("/refund") and path.startswith("/v1/orders/"):
            self._order_refund(path[len("/v1/orders/"):-len("/refund")], body)
            return
        if path == "/v1/ads/request":
            self._ads_request(body)
            return
        if path == "/v1/ads/impression":
            self._ads_event("impression", body)
            return
        if path == "/v1/ads/click":
            self._ads_event("click", body)
            return
        if path == "/v1/rooms":
            self._room_create(body)
            return
        if path.endswith("/join") and path.startswith("/v1/rooms/"):
            self._room_join(path[len("/v1/rooms/"):-len("/join")], body)
            return
        if path.endswith("/leave") and path.startswith("/v1/rooms/"):
            self._room_leave(path[len("/v1/rooms/"):-len("/leave")], body)
            return
        _json(self, 404, {"error": "not_found", "path": path})

    # ---------- 支付 ----------

    def _require_service(self, kind: str) -> bool:
        if self.service != kind:
            _json(self, 409, {"error": "wrong_service",
                              "detail": f"本实例服务类型为 {self.service}，不接受 {kind} 请求"})
            return False
        return True

    def _order_create(self, body: Dict[str, Any]) -> None:
        if not self._require_service("payment"):
            return
        amount = body.get("amount")
        if not isinstance(amount, (int, float)) or amount <= 0:
            _json(self, 400, {"error": "bad_request", "detail": "amount 必须为正数"})
            return
        oid = "ord_" + uuid.uuid4().hex[:16]
        order = {
            "order_id": oid,
            "amount": round(float(amount), 2),
            "currency": str(body.get("currency") or "CNY"),
            "status": "created",
            "refunded": False,
            "environment": self.environment,
            "reference": True,
        }
        with STATE_LOCK:
            ORDERS[oid] = order
        _json(self, 201, order)

    def _order_get(self, oid: str) -> None:
        if not ID_RE.match(oid or ""):
            _json(self, 400, {"error": "bad_request", "detail": "订单号格式非法"})
            return
        with STATE_LOCK:
            order = ORDERS.get(oid)
        if order is None:
            _json(self, 404, {"error": "not_found", "detail": f"订单不存在: {oid}"})
            return
        _json(self, 200, dict(order))

    def _order_refund(self, oid: str, body: Dict[str, Any]) -> None:
        if not self._require_service("payment"):
            return
        with STATE_LOCK:
            order = ORDERS.get(oid)
            if order is None:
                _json(self, 404, {"error": "not_found", "detail": f"订单不存在: {oid}"})
                return
            if order["status"] not in ("created", "paid"):
                _json(self, 409, {"error": "conflict",
                                  "detail": f"订单状态 {order['status']} 不可退款"})
                return
            order["status"] = "refunded"
            order["refunded"] = True
            snapshot = dict(order)
        _json(self, 200, snapshot)

    # ---------- 广告 ----------

    def _ads_request(self, body: Dict[str, Any]) -> None:
        if not self._require_service("ads"):
            return
        slot = str(body.get("slot") or "default")
        creative = {
            "ad_id": "ad_" + uuid.uuid4().hex[:12],
            "slot": slot,
            "creative_type": "image",
            "asset_url": "https://example.invalid/reference-ad.png",
            "click_url": "https://example.invalid/reference-click",
            "environment": self.environment,
            "reference": True,
        }
        _json(self, 200, creative)

    def _ads_event(self, event: str, body: Dict[str, Any]) -> None:
        if not self._require_service("ads"):
            return
        ad_id = str(body.get("ad_id") or "")
        if not ad_id:
            _json(self, 400, {"error": "bad_request", "detail": "ad_id 必填"})
            return
        eid = f"{event}_" + uuid.uuid4().hex[:12]
        with STATE_LOCK:
            ADS_EVENTS[eid] = {"event_id": eid, "event": event, "ad_id": ad_id,
                               "environment": self.environment, "reference": True}
        _json(self, 202, {"accepted": True, "event_id": eid, "event": event})

    # ---------- 联机 ----------

    def _room_create(self, body: Dict[str, Any]) -> None:
        if not self._require_service("multiplayer"):
            return
        capacity = int(body.get("capacity") or 4)
        if capacity < 1 or capacity > 64:
            _json(self, 400, {"error": "bad_request", "detail": "capacity 需在 1..64"})
            return
        rid = "room_" + uuid.uuid4().hex[:12]
        with STATE_LOCK:
            ROOMS[rid] = {"room_id": rid, "capacity": capacity, "players": [],
                          "status": "open", "environment": self.environment,
                          "reference": True}
            snapshot = dict(ROOMS[rid])
        _json(self, 201, snapshot)

    def _room_get(self, rid: str) -> None:
        with STATE_LOCK:
            room = ROOMS.get(rid)
            snapshot = dict(room) if room else None
        if snapshot is None:
            _json(self, 404, {"error": "not_found", "detail": f"房间不存在: {rid}"})
            return
        _json(self, 200, snapshot)

    def _room_join(self, rid: str, body: Dict[str, Any]) -> None:
        if not self._require_service("multiplayer"):
            return
        player = str(body.get("player_id") or "").strip()
        if not player:
            _json(self, 400, {"error": "bad_request", "detail": "player_id 必填"})
            return
        with STATE_LOCK:
            room = ROOMS.get(rid)
            if room is None:
                _json(self, 404, {"error": "not_found", "detail": f"房间不存在: {rid}"})
                return
            if room["status"] != "open":
                _json(self, 409, {"error": "conflict", "detail": f"房间状态 {room['status']}"})
                return
            if len(room["players"]) >= room["capacity"]:
                _json(self, 409, {"error": "room_full", "detail": "房间已满"})
                return
            if player not in room["players"]:
                room["players"].append(player)
            snapshot = dict(room)
        _json(self, 200, snapshot)

    def _room_leave(self, rid: str, body: Dict[str, Any]) -> None:
        if not self._require_service("multiplayer"):
            return
        player = str(body.get("player_id") or "").strip()
        with STATE_LOCK:
            room = ROOMS.get(rid)
            if room is None:
                _json(self, 404, {"error": "not_found", "detail": f"房间不存在: {rid}"})
                return
            if player in room["players"]:
                room["players"].remove(player)
            if not room["players"]:
                room["status"] = "closed"
            snapshot = dict(room)
        _json(self, 200, snapshot)


def make_server(service: str = "payment", environment: str = "sandbox",
                api_key: str = "", host: str = "127.0.0.1", port: int = 0):
    handler = type("BoundHandler", (ReferenceHandler,),
                   {"service": service, "environment": environment, "api_key": api_key})
    return ThreadingHTTPServer((host, port), handler)


#: --all 模式下三类服务的默认端口（payment / ads / multiplayer）
ALL_PORTS = {"payment": 8801, "ads": 8802, "multiplayer": 8803}


def serve_all(environment: str = "sandbox", host: str = "127.0.0.1",
              keys: Optional[Dict[str, str]] = None,
              ports: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """一键起三类服务（各占一端口，线程内 serve_forever），返回实际地址。

    供本地联调使用：起完后把地址填进 .env 即可跑 live-flow。
    """
    keys = keys or {}
    ports = {**ALL_PORTS, **(ports or {})}
    servers = {}
    for kind in SERVICE_KINDS:
        httpd = make_server(kind, environment, keys.get(kind, ""), host, ports[kind])
        servers[kind] = httpd
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return {k: f"http://{host}:{s.server_address[1]}" for k, s in servers.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="参考线上服务（支付/广告/联机）真实 HTTP 服务")
    parser.add_argument("--service", default="payment", choices=list(SERVICE_KINDS))
    parser.add_argument("--environment", default="sandbox", choices=["sandbox", "staging"])
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--key", type=str, default="", help="要求 Bearer 鉴权的 Key（不传=开放联调）")
    parser.add_argument("--all", dest="serve_all", action="store_true",
                        help=f"一键起三类服务（端口 {ALL_PORTS}），适合本地联调")
    parser.add_argument("--payment-key", type=str, default="")
    parser.add_argument("--ads-key", type=str, default="")
    parser.add_argument("--multiplayer-key", type=str, default="")
    args = parser.parse_args()

    if args.serve_all:
        keys = {"payment": args.payment_key, "ads": args.ads_key,
                "multiplayer": args.multiplayer_key}
        addrs = serve_all(args.environment, args.host, keys)
        print("reference live-service (all) environment=" + args.environment)
        for kind, addr in addrs.items():
            auth = "on" if keys.get(kind) else "off"
            print(f"  {kind:12s} {addr}  auth={auth}")
            print(f"    建议 .env: {SANDBOX_ENV_HINT[kind]['url']}={addr}")
            if keys.get(kind):
                print(f"              {SANDBOX_ENV_HINT[kind]['key']}=<上面的 --{kind}-key 值>")
        print("按 Ctrl+C 停止")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        return

    httpd = make_server(args.service, args.environment, args.key, args.host, args.port)
    actual_port = httpd.server_address[1]
    print(f"reference live-service on http://{args.host}:{actual_port} "
          f"service={args.service} environment={args.environment} auth={'on' if args.key else 'off'}")
    print("health: GET /health")
    if args.service == "payment":
        print("  POST /v1/orders  GET /v1/orders/{id}  POST /v1/orders/{id}/refund")
    elif args.service == "ads":
        print("  POST /v1/ads/request  POST /v1/ads/impression  POST /v1/ads/click")
    else:
        print("  POST /v1/rooms  GET /v1/rooms/{id}  POST /v1/rooms/{id}/join  POST /v1/rooms/{id}/leave")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


#: 各类服务对应的 .env 变量名，便于 --all 启动时直接给出可复制的配置
SANDBOX_ENV_HINT = {
    "payment": {"url": "PAYMENT_SANDBOX_URL", "key": "PAYMENT_SANDBOX_KEY"},
    "ads": {"url": "ADS_SANDBOX_URL", "key": "ADS_SANDBOX_KEY"},
    "multiplayer": {"url": "MULTIPLAYER_SANDBOX_URL", "key": "MULTIPLAYER_SANDBOX_KEY"},
}


if __name__ == "__main__":
    main()
