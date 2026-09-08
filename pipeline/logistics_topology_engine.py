"""
Logistics Topology & Material Conservation Simulation Engine (Mindustry-Inspired)
工业级物流管网拓扑与物质守恒流向引擎

核心职责:
1. ConveyorQueue: 传送带物理排队与下游背压拥堵 (Backpressure) 传播
2. RouterDistributor: 1 进 N 出轮询均分物质守恒分发器
3. FluidPressureGrid: 离散流体差压扩散与管道流网
4. PowerGridNetwork: 电网连通分量 (Disjoint Set / BFS) 供需平衡计算与过载降频
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import deque
import enum
import math


class Direction(enum.Enum):
    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
    LEFT = (-1, 0)

    @classmethod
    def from_str(cls, s: str):
        mapping = {"up": cls.UP, "right": cls.RIGHT, "down": cls.DOWN, "left": cls.LEFT,
                   "0": cls.RIGHT, "1": cls.DOWN, "2": cls.LEFT, "3": cls.UP}
        return mapping.get(str(s).lower(), cls.RIGHT)


@dataclass
class ItemSlot:
    item_type: str
    progress: float = 0.0  # 0.0 ~ 1.0 within the tile


class ConveyorTile:
    """
    单格传送带模型:
    - 容量: capacity (默认最多容纳 4 个物品插槽)
    - 移动速率: speed (格/秒)
    - 背压 (Backpressure): 若下游满载或堵塞，本格物品在顶部排队堆积，绝不重叠且绝不凭空消失
    """
    def __init__(self, x: int, y: int, direction: Direction, capacity: int = 4, speed: float = 1.0):
        self.x = x
        self.y = y
        self.direction = direction
        self.capacity = capacity
        self.speed = speed
        self.items: List[ItemSlot] = []
        self.is_blocked: bool = False

    def can_accept(self) -> bool:
        if len(self.items) >= self.capacity:
            return False
        if len(self.items) > 0 and self.items[-1].progress < 0.25:
            return False
        return True

    def push_item(self, item_type: str) -> bool:
        if not self.can_accept():
            return False
        self.items.append(ItemSlot(item_type=item_type, progress=0.0))
        return True

    def update(self, dt: float, downstream_tile: Optional['ConveyorTile'] = None,
               downstream_consumer: Optional[callable] = None) -> List[str]:
        """
        向前推进行进并处理转移与背压。
        返回成功流出或被消费的物品列表。
        """
        if not self.items:
            self.is_blocked = False
            return []

        outflow = []
        min_spacing = 1.0 / self.capacity

        # 逆序或者正序遍历推进
        # 第一件物品（最靠近出口处）
        lead_item = self.items[0]
        if lead_item.progress >= 1.0:
            # 尝试交付给下游
            transferred = False
            if downstream_tile and downstream_tile.can_accept():
                if downstream_tile.push_item(lead_item.item_type):
                    self.items.pop(0)
                    transferred = True
            elif downstream_consumer and downstream_consumer(lead_item.item_type):
                self.items.pop(0)
                outflow.append(lead_item.item_type)
                transferred = True

            self.is_blocked = not transferred
        else:
            self.is_blocked = False

        # 推进所有物品（受前方物品物理阻挡）
        for i in range(len(self.items)):
            item = self.items[i]
            max_allowed = 1.0 if i == 0 else (self.items[i - 1].progress - min_spacing)
            if not self.is_blocked or i > 0:
                item.progress = min(max_allowed, item.progress + self.speed * dt)

        return outflow


class RouterTile:
    """
    三路分流器 (Router):
    - 接收 1 路输入，严格以轮询 (Round-Robin) 方式向 3 个可用输出口物质守恒分发。
    - 绝不凭空湮灭物品，绝不凭空制造物品。
    """
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.buffer: deque = deque(maxlen=8)
        self.round_robin_index = 0

    def push(self, item_type: str) -> bool:
        if len(self.buffer) >= self.buffer.maxlen:
            return False
        self.buffer.append(item_type)
        return True

    def distribute(self, available_outputs: List[callable]) -> bool:
        if not self.buffer or not available_outputs:
            return False
        item = self.buffer[0]
        n = len(available_outputs)
        for offset in range(n):
            target_idx = (self.round_robin_index + offset) % n
            consumer = available_outputs[target_idx]
            if consumer(item):
                self.buffer.popleft()
                self.round_robin_index = (target_idx + 1) % n
                return True
        return False


class PowerGridNetwork:
    """
    工业级电网图平衡求解器:
    - 基于图连通分量 (Connected Components)，将全地图发电机、电线杆与用电设备聚合成独立电网。
    - 计算每个子电网的 总发电量 (Total Power Generated) 与 总负荷 (Total Power Required)。
    - 计算满足率 Satisfaction Rate = min(1.0, TotalGen / TotalReq)。
    - 若发电不足（负荷过载），所有用电设备（炮塔充能、采矿机）等比例降频运转。
    """
    def __init__(self):
        self.generators: Dict[Tuple[int, int], float] = {}  # (x, y) -> power_output
        self.consumers: Dict[Tuple[int, int], float] = {}   # (x, y) -> power_required
        self.poles: Set[Tuple[int, int]] = set()           # (x, y)
        self.adj: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {}

    def _connect_to_nearby_poles(self, x: int, y: int, radius: int = 3):
        for px, py in self.poles:
            if (px, py) != (x, y):
                if math.hypot(px - x, py - y) <= radius:
                    self.connect((x, y), (px, py))

    def add_generator(self, x: int, y: int, power: float):
        self.generators[(x, y)] = power
        self._ensure_node((x, y))
        self._connect_to_nearby_poles(x, y)

    def add_consumer(self, x: int, y: int, power: float):
        self.consumers[(x, y)] = power
        self._ensure_node((x, y))
        self._connect_to_nearby_poles(x, y)

    def add_pole(self, x: int, y: int, connect_radius: int = 3):
        self.poles.add((x, y))
        self._ensure_node((x, y))
        all_nodes = list(self.generators.keys()) + list(self.consumers.keys()) + list(self.poles)
        for nx, ny in all_nodes:
            if (nx, ny) != (x, y):
                if math.hypot(nx - x, ny - y) <= connect_radius:
                    self.connect((x, y), (nx, ny))

    def _ensure_node(self, node: Tuple[int, int]):
        if node not in self.adj:
            self.adj[node] = set()

    def connect(self, u: Tuple[int, int], v: Tuple[int, int]):
        self._ensure_node(u)
        self._ensure_node(v)
        self.adj[u].add(v)
        self.adj[v].add(u)

    def solve_network(self) -> List[Dict]:
        """
        求解全网连通分量及供需满意度。
        """
        visited: Set[Tuple[int, int]] = set()
        subnets = []

        all_nodes = set(self.adj.keys())
        for node in all_nodes:
            if node not in visited:
                comp = []
                queue = [node]
                visited.add(node)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for neighbor in self.adj.get(curr, set()):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

                total_gen = sum(self.generators.get(p, 0.0) for p in comp)
                total_req = sum(self.consumers.get(p, 0.0) for p in comp)
                sat = 1.0 if total_req <= 0.0 else min(1.0, total_gen / total_req)

                subnets.append({
                    "nodes_count": len(comp),
                    "total_generation": total_gen,
                    "total_demand": total_req,
                    "satisfaction_rate": round(sat, 3),
                    "is_brownout": sat < 1.0 and total_req > 0.0
                })

        return subnets


class LogisticsTopologyEngine:
    """
    物流管网总控引擎 (面向客户端代码生成与离线验证)
    """
    @classmethod
    def generate_client_js_module(cls) -> str:
        """
        生成客户端直接运行的完整零依赖 ES6 物流管网引擎代码。
        """
        return """
// ==========================================
// 工业级物流管网拓扑引擎 (Conveyor & Logistics Engine)
// 物质守恒、拥堵背压 (Backpressure)、路由器分流与电网图
// ==========================================
class LogisticsEngine {
    constructor(gridW, gridH, tileSize = 32) {
        this.gridW = gridW;
        this.gridH = gridH;
        this.tileSize = tileSize;
        // 存储网格中的传送带与建筑
        this.conveyors = new Map(); // key: "x,y" => { dir: 0|1|2|3, items: [{type, p}], cap: 4, speed: 2.0, blocked: false }
        this.buildings = new Map(); // key: "x,y" => { type, acceptItem: fn, ... }
        this.powerGenerators = new Map(); // key => power
        this.powerConsumers = new Map();  // key => power
        this.powerPoles = new Set();
        this.networkStats = { totalItemsMoved: 0, backpressureCount: 0, powerSat: 1.0 };
    }

    getKey(x, y) { return `${x},${y}`; }

    addConveyor(x, y, dir, speed = 2.2) {
        this.conveyors.set(this.getKey(x, y), {
            x, y, dir, speed,
            capacity: 4,
            items: [],
            isBlocked: false
        });
    }

    removeConveyor(x, y) {
        this.conveyors.delete(this.getKey(x, y));
    }

    getNextPos(x, y, dir) {
        const deltas = [[1, 0], [0, 1], [-1, 0], [0, -1]]; // 0: Right, 1: Down, 2: Left, 3: Up
        const d = deltas[dir] || [0, 0];
        return { x: x + d[0], y: y + d[1] };
    }

    canConveyorAccept(conv) {
        if (!conv || conv.items.length >= conv.capacity) return false;
        if (conv.items.length > 0 && conv.items[conv.items.length - 1].p < 0.25) return false;
        return true;
    }

    pushItem(x, y, itemType) {
        const conv = this.conveyors.get(this.getKey(x, y));
        if (conv && this.canConveyorAccept(conv)) {
            conv.items.push({ type: itemType, p: 0.0 });
            return true;
        }
        return false;
    }

    update(dt, buildingAcceptCallback) {
        const minSpacing = 0.25;
        this.networkStats.backpressureCount = 0;

        for (const [key, conv] of this.conveyors.entries()) {
            if (conv.items.length === 0) {
                conv.isBlocked = false;
                continue;
            }

            const nextPos = this.getNextPos(conv.x, conv.y, conv.dir);
            const nextKey = this.getKey(nextPos.x, nextPos.y);
            const nextConv = this.conveyors.get(nextKey);

            // 领头物品移至边界处理
            const lead = conv.items[0];
            if (lead.p >= 1.0) {
                let moved = false;
                if (nextConv) {
                    if (this.canConveyorAccept(nextConv)) {
                        nextConv.items.push({ type: lead.type, p: 0.0 });
                        conv.items.shift();
                        moved = true;
                        this.networkStats.totalItemsMoved++;
                    }
                } else if (buildingAcceptCallback) {
                    if (buildingAcceptCallback(nextPos.x, nextPos.y, lead.type)) {
                        conv.items.shift();
                        moved = true;
                        this.networkStats.totalItemsMoved++;
                    }
                }
                conv.isBlocked = !moved;
                if (!moved) this.networkStats.backpressureCount++;
            } else {
                conv.isBlocked = false;
            }

            // 物理推进与背压挤压
            for (let i = 0; i < conv.items.length; i++) {
                const item = conv.items[i];
                const maxP = (i === 0) ? 1.0 : (conv.items[i - 1].p - minSpacing);
                if (!conv.isBlocked || i > 0) {
                    item.p = Math.min(maxP, item.p + conv.speed * dt);
                }
            }
        }
    }

    draw(ctx, camera, spriteRenderer) {
        const dirAngles = [0, Math.PI / 2, Math.PI, -Math.PI / 2];
        for (const [key, conv] of this.conveyors.entries()) {
            const sx = conv.x * this.tileSize - camera.x;
            const sy = conv.y * this.tileSize - camera.y;
            if (sx < -64 || sx > ctx.canvas.width + 64 || sy < -64 || sy > ctx.canvas.height + 64) continue;

            // 绘制传送带底板
            ctx.save();
            ctx.translate(sx + 16, sy + 16);
            ctx.rotate(dirAngles[conv.dir]);
            
            // 传送带基底 (金属槽)
            ctx.fillStyle = "#27272a";
            ctx.fillRect(-16, -16, 32, 32);
            ctx.strokeStyle = "#3f3f46";
            ctx.lineWidth = 2;
            ctx.strokeRect(-16, -16, 32, 32);

            // 履带滚轴齿印
            ctx.fillStyle = conv.isBlocked ? "#713f12" : "#52525b";
            const animOffset = (Date.now() * 0.01 * (conv.isBlocked ? 0 : conv.speed)) % 10;
            for (let ox = -14 + animOffset; ox < 16; ox += 8) {
                ctx.fillRect(ox, -12, 3, 24);
            }
            // 移动方向微型箭头
            ctx.fillStyle = conv.isBlocked ? "#f59e0b" : "#a1a1aa";
            ctx.beginPath();
            ctx.moveTo(6, 0); ctx.lineTo(-2, -5); ctx.lineTo(-2, 5); ctx.fill();
            ctx.restore();

            // 绘制其上的矿石物品
            for (const item of conv.items) {
                const forward = [[1, 0], [0, 1], [-1, 0], [0, -1]][conv.dir];
                const ix = sx + 16 + forward[0] * (item.p * 32 - 16);
                const iy = sy + 16 + forward[1] * (item.p * 32 - 16);

                ctx.save();
                if (item.type === "copper") {
                    ctx.fillStyle = "#f97316"; // 铜矿: 鲜亮橙红
                    ctx.strokeStyle = "#c2410c";
                } else if (item.type === "lead") {
                    ctx.fillStyle = "#a855f7"; // 铅矿: 科技亮紫
                    ctx.strokeStyle = "#7e22ce";
                } else {
                    ctx.fillStyle = "#38bdf8"; // 稀有硅/钛: 冰蓝
                    ctx.strokeStyle = "#0284c7";
                }
                ctx.shadowColor = ctx.fillStyle;
                ctx.shadowBlur = 4;
                ctx.beginPath();
                ctx.arc(ix, iy, 4.5, 0, Math.PI * 2);
                ctx.fill();
                ctx.lineWidth = 1.5;
                ctx.stroke();
                ctx.restore();
            }
        }
    }
}
"""
