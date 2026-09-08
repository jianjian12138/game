# =================================================================
# 📐 Game-Agent: 工业级场景图与层级变换矩阵引擎 (engine_scene_graph.py)
# 对应 ThisisGame/cpp-game-engine-book 第 4 章(矩阵数学) & 第 8 章(GameObject-Component)
# 严格提供 Transform 父子树、2D仿射矩阵乘法、链式脏标记(Dirty Flag)与惰性求值
# =================================================================

import math
from typing import Dict, List, Optional, Tuple, Any

class Transform2D:
    """
    纯 Python 仿射矩阵与场景图节点数学实现 (用于校验与测试)
    矩阵布局: [a, b, c, d, tx, ty]
    [ x' ]   [ a  c  tx ] [ x ]
    [ y' ] = [ b  d  ty ] [ y ]
    [ 1  ]   [ 0  0  1  ] [ 1 ]
    """
    def __init__(self, name: str = "node"):
        self.name = name
        self.parent: Optional['Transform2D'] = None
        self.children: List['Transform2D'] = []
        
        self.local_x: float = 0.0
        self.local_y: float = 0.0
        self.local_rotation: float = 0.0 # 弧度
        self.local_scale_x: float = 1.0
        self.local_scale_y: float = 1.0
        
        # [a, b, c, d, tx, ty]
        self.local_matrix: List[float] = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        self.world_matrix: List[float] = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        self.is_dirty: bool = True

    def add_child(self, child: 'Transform2D') -> 'Transform2D':
        if child.parent:
            child.parent.remove_child(child)
        child.parent = self
        self.children.append(child)
        child.mark_dirty()
        return child

    def remove_child(self, child: 'Transform2D') -> None:
        if child in self.children:
            self.children.remove(child)
            child.parent = None
            child.mark_dirty()

    def set_position(self, x: float, y: float) -> None:
        if self.local_x != x or self.local_y != y:
            self.local_x = x
            self.local_y = y
            self.mark_dirty()

    def set_rotation(self, rad: float) -> None:
        if self.local_rotation != rad:
            self.local_rotation = rad
            self.mark_dirty()

    def set_scale(self, sx: float, sy: float) -> None:
        if self.local_scale_x != sx or self.local_scale_y != sy:
            self.local_scale_x = sx
            self.local_scale_y = sy
            self.mark_dirty()

    def mark_dirty(self) -> None:
        self.is_dirty = True
        for child in self.children:
            child.mark_dirty()

    def update_local_matrix(self) -> None:
        c = math.cos(self.local_rotation)
        s = math.sin(self.local_rotation)
        self.local_matrix[0] = c * self.local_scale_x
        self.local_matrix[1] = s * self.local_scale_x
        self.local_matrix[2] = -s * self.local_scale_y
        self.local_matrix[3] = c * self.local_scale_y
        self.local_matrix[4] = self.local_x
        self.local_matrix[5] = self.local_y

    def get_world_matrix(self) -> List[float]:
        if self.is_dirty:
            self.update_local_matrix()
            if self.parent is None:
                self.world_matrix = list(self.local_matrix)
            else:
                pw = self.parent.get_world_matrix()
                lw = self.local_matrix
                # pw * lw 矩阵乘法
                # [A.a A.c A.tx] * [B.a B.c B.tx]
                # [A.b A.d A.ty]   [B.b B.d B.ty]
                a = pw[0] * lw[0] + pw[2] * lw[1]
                b = pw[1] * lw[0] + pw[3] * lw[1]
                c = pw[0] * lw[2] + pw[2] * lw[3]
                d = pw[1] * lw[2] + pw[3] * lw[3]
                tx = pw[0] * lw[4] + pw[2] * lw[5] + pw[4]
                ty = pw[1] * lw[4] + pw[3] * lw[5] + pw[5]
                self.world_matrix = [a, b, c, d, tx, ty]
            self.is_dirty = False
        return self.world_matrix

    def transform_point(self, px: float, py: float) -> Tuple[float, float]:
        """将局部坐标变换为世界坐标"""
        m = self.get_world_matrix()
        wx = m[0] * px + m[2] * py + m[4]
        wy = m[1] * px + m[3] * py + m[5]
        return (wx, wy)

    def get_world_position(self) -> Tuple[float, float]:
        m = self.get_world_matrix()
        return (m[4], m[5])

    def get_world_rotation(self) -> float:
        m = self.get_world_matrix()
        return math.atan2(m[1], m[0])


def generate_scene_graph_js() -> str:
    """生成工业级 V8 零GC高性能 JavaScript 场景图运行时代码"""
    return """
// =================================================================
// 📐 工业级场景图运行时 (Scene Graph & Transform Hierarchy)
// 遵循 ThisisGame/cpp-game-engine-book 第 4 & 8 章架构
// Float32Array 仿射矩阵 + 链式脏标记 (isDirty) 惰性求值
// =================================================================
class TransformNode {
    constructor(name = 'node') {
        this.name = name;
        this.parent = null;
        this.children = [];

        this.x = 0;
        this.y = 0;
        this.rotation = 0; // 弧度
        this.scaleX = 1;
        this.scaleY = 1;

        // [a, b, c, d, tx, ty] 2D 仿射变换连续内存
        this.localMatrix = new Float32Array([1, 0, 0, 1, 0, 0]);
        this.worldMatrix = new Float32Array([1, 0, 0, 1, 0, 0]);
        this.isDirty = true;
    }

    addChild(child) {
        if (child.parent) child.parent.removeChild(child);
        child.parent = this;
        this.children.push(child);
        child.markDirty();
        return child;
    }

    removeChild(child) {
        const idx = this.children.indexOf(child);
        if (idx !== -1) {
            this.children.splice(idx, 1);
            child.parent = null;
            child.markDirty();
        }
    }

    setPosition(x, y) {
        if (this.x !== x || this.y !== y) {
            this.x = x;
            this.y = y;
            this.markDirty();
        }
    }

    setRotation(rad) {
        if (this.rotation !== rad) {
            this.rotation = rad;
            this.markDirty();
        }
    }

    setScale(sx, sy) {
        if (this.scaleX !== sx || this.scaleY !== sy) {
            this.scaleX = sx;
            this.scaleY = sy;
            this.markDirty();
        }
    }

    markDirty() {
        if (!this.isDirty) {
            this.isDirty = true;
            for (let i = 0; i < this.children.length; i++) {
                this.children[i].markDirty();
            }
        }
    }

    updateLocalMatrix() {
        const c = Math.cos(this.rotation);
        const s = Math.sin(this.rotation);
        const lm = this.localMatrix;
        lm[0] = c * this.scaleX;
        lm[1] = s * this.scaleX;
        lm[2] = -s * this.scaleY;
        lm[3] = c * this.scaleY;
        lm[4] = this.x;
        lm[5] = this.y;
    }

    getWorldMatrix() {
        if (this.isDirty) {
            this.updateLocalMatrix();
            const lm = this.localMatrix;
            const wm = this.worldMatrix;

            if (!this.parent) {
                wm[0] = lm[0]; wm[1] = lm[1];
                wm[2] = lm[2]; wm[3] = lm[3];
                wm[4] = lm[4]; wm[5] = lm[5];
            } else {
                const pw = this.parent.getWorldMatrix();
                const pa = pw[0], pb = pw[1], pc = pw[2], pd = pw[3], ptx = pw[4], pty = pw[5];
                const la = lm[0], lb = lm[1], lc = lm[2], ld = lm[3], ltx = lm[4], lty = lm[5];

                wm[0] = pa * la + pc * lb;
                wm[1] = pb * la + pd * lb;
                wm[2] = pa * lc + pc * ld;
                wm[3] = pb * lc + pd * ld;
                wm[4] = pa * ltx + pc * lty + ptx;
                wm[5] = pb * ltx + pd * lty + pty;
            }
            this.isDirty = false;
        }
        return this.worldMatrix;
    }

    transformPoint(px, py, out = { x: 0, y: 0 }) {
        const m = this.getWorldMatrix();
        out.x = m[0] * px + m[2] * py + m[4];
        out.y = m[1] * px + m[3] * py + m[5];
        return out;
    }

    getWorldPosition(out = { x: 0, y: 0 }) {
        const m = this.getWorldMatrix();
        out.x = m[4];
        out.y = m[5];
        return out;
    }

    getWorldRotation() {
        const m = this.getWorldMatrix();
        return Math.atan2(m[1], m[0]);
    }
}
"""
