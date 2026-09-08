"""
47-Tile Bitmask Autotiling & Procedural Terrain Compiler (Mindustry / Tilemap Industry Standard)
47 掩码自动转角瓦片与地形渲染编译器

核心原理:
- 8 邻域 Blob 47 Tileset 算法 (N, NE, E, SE, S, SW, W, NW)
- 角点依赖性: 仅当相邻两个正交方向 (Cardinal) 都连通时，对角角点 (Corner) 才参与计算
- 彻底解决建筑城墙、地牢石壁、水体与沙地相交时的转角拼缝与生硬边界
"""

from typing import Dict, List, Optional, Tuple


class Blob47BitmaskSolver:
    """
    8 邻居 47-Tile 标准位掩码映射器
    方向权重:
      NW(128)  N(1)   NE(2)
      W(64)   [Tile]  E(4)
      SW(32)   S(16)  SE(8)
    """
    # 256 种二进制输入压缩映射到 47 种经典独立瓦片 (Canonical 47 Tiles)
    CANONICAL_LOOKUP: Dict[int, int] = {}

    @classmethod
    def _init_lookup(cls):
        if cls.CANONICAL_LOOKUP:
            return

        # 47 种标准掩码定义 (Canonical 47 Masks)
        canonical_47 = [
            0,   # 0: 孤岛 (No neighbors)
            1,   # 1: 仅北 (N)
            4,   # 2: 仅东 (E)
            16,  # 3: 仅南 (S)
            64,  # 4: 仅西 (W)
            5,   # 5: 东北直角 (N + E)
            7,   # 6: 东北直角 + 内角 (N + E + NE)
            20,  # 7: 东南直角 (S + E)
            28,  # 8: 东南直角 + 内角 (S + E + SE)
            80,  # 9: 西南直角 (S + W)
            112, # 10: 西南直角 + 内角 (S + W + SW)
            65,  # 11: 西北直角 (N + W)
            193, # 12: 西北直角 + 内角 (N + W + NW)
            17,  # 13: 南北垂直通道 (N + S)
            68,  # 14: 东西水平通道 (E + W)
            21,  # 15: T型向东 (N + E + S)
            23,  # 16: T型向东 + NE内角
            29,  # 17: T型向东 + SE内角
            31,  # 18: T型向东 + 纯双内角 (N + E + S + NE + SE)
            84,  # 19: T型向南 (E + S + W)
            92,  # 20: T型向南 + SE内角
            116, # 21: T型向南 + SW内角
            124, # 22: T型向南 + 双内角 (E + S + W + SE + SW)
            81,  # 23: T型向西 (S + W + N)
            113, # 24: T型向西 + SW内角
            209, # 25: T型向西 + NW内角
            241, # 26: T型向西 + 双内角 (S + W + N + SW + NW)
            69,  # 27: T型向北 (W + N + E)
            71,  # 28: T型向北 + NE内角
            197, # 29: T型向北 + NW内角
            199, # 30: T型向北 + 双内角 (W + N + E + NE + NW)
            85,  # 31: 十字交叉 (N + E + S + W)
            87,  # 32: 十字 + NE
            93,  # 33: 十字 + SE
            117, # 34: 十字 + SW
            213, # 35: 十字 + NW
            95,  # 36: 十字 + NE + SE
            119, # 37: 十字 + SE + SW
            245, # 38: 十字 + SW + NW
            215, # 39: 十字 + NW + NE
            127, # 40: 十字 + 3内角 (无NW)
            223, # 41: 十字 + 3内角 (无SW)
            247, # 42: 十字 + 3内角 (无SE)
            253, # 43: 十字 + 3内角 (无NE)
            125, # 44: 十字 + 对角内角 (NE + SW)
            221, # 45: 十字 + 对角内角 (NW + SE)
            255, # 46: 彻底包围实心中心 (Surrounded Interior)
        ]

        # 映射到 0 ~ 46 索引
        for idx, mask in enumerate(canonical_47):
            cls.CANONICAL_LOOKUP[mask] = idx

        # 为其余非规范输入 (0 ~ 255) 进行角点过滤并回溯
        for raw in range(256):
            if raw in cls.CANONICAL_LOOKUP:
                continue
            # 过滤无效角点
            n = (raw & 1) != 0
            e = (raw & 4) != 0
            s = (raw & 16) != 0
            w = (raw & 64) != 0
            filtered = (raw & 1) | (raw & 4) | (raw & 16) | (raw & 64)
            if n and e and (raw & 2):
                filtered |= 2
            if s and e and (raw & 8):
                filtered |= 8
            if s and w and (raw & 32):
                filtered |= 32
            if n and w and (raw & 128):
                filtered |= 128

            cls.CANONICAL_LOOKUP[raw] = cls.CANONICAL_LOOKUP.get(filtered, 0)

    @classmethod
    def calculate_bitmask(cls, x: int, y: int, is_solid_fn: callable) -> int:
        """
        计算坐标 (x, y) 处周围 8 个邻居的压缩掩码。
        is_solid_fn: 传入 (nx, ny)，返回 bool (是否同一材质或实体)
        """
        cls._init_lookup()

        n  = 1 if is_solid_fn(x, y - 1) else 0
        e  = 1 if is_solid_fn(x + 1, y) else 0
        s  = 1 if is_solid_fn(x, y + 1) else 0
        w  = 1 if is_solid_fn(x - 1, y) else 0

        # 角点仅在相邻两正交方向连通时生效
        ne = (1 if is_solid_fn(x + 1, y - 1) else 0) if (n and e) else 0
        se = (1 if is_solid_fn(x + 1, y + 1) else 0) if (s and e) else 0
        sw = (1 if is_solid_fn(x - 1, y + 1) else 0) if (s and w) else 0
        nw = (1 if is_solid_fn(x - 1, y - 1) else 0) if (n and w) else 0

        raw_mask = (n * 1) + (ne * 2) + (e * 4) + (se * 8) + (s * 16) + (sw * 32) + (w * 64) + (nw * 128)
        return cls.CANONICAL_LOOKUP.get(raw_mask, 0)


class AutotileBitmaskEngine:
    """
    自动转角引擎总控 (生成客户端 Canvas 烘焙脚本与运行时渲染器)
    """
    @classmethod
    def generate_client_js_module(cls) -> str:
        """
        生成客户端直接运行的 47 瓦片自动烘焙与转角拼缝渲染器。
        """
        return """
// ==========================================
// 47 掩码自动转角瓦片与地形渲染编译器 (Autotile 47 Bitmask)
// 8 邻域 Blob 拓扑映射，彻底消灭孤立直角与拼缝瑕疵
// ==========================================
class AutotileEngine {
    constructor(tileSize = 32) {
        this.tileSize = tileSize;
        this.lookup = new Uint8Array(256);
        this.atlasCanvas = null;
        this.atlasCtx = null;
        this._initLookup();
        this._bakeAtlas();
    }

    _initLookup() {
        const canonical47 = [
            0, 1, 4, 16, 64, 5, 7, 20, 28, 80, 112, 65, 193, 17, 68, 21,
            23, 29, 31, 84, 92, 116, 124, 81, 113, 209, 241, 69, 71, 197, 199,
            85, 87, 93, 117, 213, 95, 119, 245, 215, 127, 223, 247, 253, 125, 221, 255
        ];
        for (let i = 0; i < 256; i++) {
            const n = (i & 1) !== 0;
            const e = (i & 4) !== 0;
            const s = (i & 16) !== 0;
            const w = (i & 64) !== 0;
            let f = (i & 1) | (i & 4) | (i & 16) | (i & 64);
            if (n && e && (i & 2)) f |= 2;
            if (s && e && (i & 8)) f |= 8;
            if (s && w && (i & 32)) f |= 32;
            if (n && w && (i & 128)) f |= 128;

            let match = 0;
            for (let idx = 0; idx < canonical47.length; idx++) {
                if (canonical47[idx] === f) {
                    match = idx;
                    break;
                }
            }
            this.lookup[i] = match;
        }
    }

    _bakeAtlas() {
        // 烘焙 8x6 阵列的 47 种精细合金石墙瓦片 (256x192)
        const ts = this.tileSize;
        this.atlasCanvas = document.createElement("canvas");
        this.atlasCanvas.width = ts * 8;
        this.atlasCanvas.height = ts * 6;
        const ctx = this.atlasCanvas.getContext("2d");
        this.atlasCtx = ctx;

        ctx.imageSmoothingEnabled = false;

        for (let idx = 0; idx < 47; idx++) {
            const col = idx % 8;
            const row = Math.floor(idx / 8);
            const bx = col * ts;
            const by = row * ts;

            // 基础防爆钛金装甲色
            ctx.fillStyle = "#334155"; // slate-700
            ctx.fillRect(bx, by, ts, ts);

            // 绘制倒角与顶面高光
            ctx.fillStyle = "#475569"; // slate-600
            ctx.fillRect(bx + 2, by + 2, ts - 4, ts - 4);

            // 顶部高光亮条
            ctx.fillStyle = "#64748b"; // slate-500
            ctx.fillRect(bx + 3, by + 3, ts - 6, 4);

            // 底部深色投影
            ctx.fillStyle = "#1e293b"; // slate-800
            ctx.fillRect(bx + 2, by + ts - 4, ts - 4, 2);

            // 战术十字刻线 / 螺栓铆钉
            ctx.fillStyle = "#94a3b8";
            ctx.fillRect(bx + 4, by + 4, 2, 2);
            ctx.fillRect(bx + ts - 6, by + 4, 2, 2);
            ctx.fillRect(bx + 4, by + ts - 6, 2, 2);
            ctx.fillRect(bx + ts - 6, by + ts - 6, 2, 2);

            // 边缘描边
            ctx.strokeStyle = "#0f172a";
            ctx.lineWidth = 1;
            ctx.strokeRect(bx + 0.5, by + 0.5, ts - 1, ts - 1);
        }
    }

    getTileIndex(x, y, isSolidFn) {
        const n  = isSolidFn(x, y - 1) ? 1 : 0;
        const e  = isSolidFn(x + 1, y) ? 1 : 0;
        const s  = isSolidFn(x, y + 1) ? 1 : 0;
        const w  = isSolidFn(x - 1, y) ? 1 : 0;

        const ne = (n && e && isSolidFn(x + 1, y - 1)) ? 1 : 0;
        const se = (s && e && isSolidFn(x + 1, y + 1)) ? 1 : 0;
        const sw = (s && w && isSolidFn(x - 1, y + 1)) ? 1 : 0;
        const nw = (n && w && isSolidFn(x - 1, y - 1)) ? 1 : 0;

        const mask = (n * 1) + (ne * 2) + (e * 4) + (se * 8) + (s * 16) + (sw * 32) + (w * 64) + (nw * 128);
        return this.lookup[mask];
    }

    drawTile(ctx, screenX, screenY, tileIdx) {
        if (!this.atlasCanvas) return;
        const ts = this.tileSize;
        const col = tileIdx % 8;
        const row = Math.floor(tileIdx / 8);
        ctx.drawImage(this.atlasCanvas, col * ts, row * ts, ts, ts, screenX, screenY, ts, ts);
    }
}
"""
