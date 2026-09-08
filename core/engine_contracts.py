#!/usr/bin/env python3
"""
engine_contracts.py: 8 大前置工程刚性防线规范库 (Pre-emptive Invariants Library)
治未病大于治已病！在游戏生成前就将边界跌落、掩体穿模、窗口失焦狂奔、内存泄漏等萌芽问题彻底封死。
"""

class EngineContracts:

    @staticmethod
    def get_kinematics_and_boundary_js(boundary_size: float = 50.0) -> str:
        """防线一与防线三：世界封闭空气墙、AABB 掩体推挤阻挡与窗口失焦按键复位守卫"""
        return f"""
// =================================================================
// 🛡️ 防线一与三: 刚性空间边界、掩体碰撞与失焦防狂奔守卫 (Engine Contract)
// =================================================================
const BoundaryKinematics = (function() {{
  const HALF_SIZE = {boundary_size}; // 地图刚性边界半长: [-{boundary_size}, {boundary_size}]
  const obstacles = [];

  return {{
    addObstacle: function(x, z, width, depth) {{
      obstacles.push({{
        minX: x - width / 2 - 0.6, // 附加玩家胶囊体半径余量
        maxX: x + width / 2 + 0.6,
        minZ: z - depth / 2 - 0.6,
        maxZ: z + depth / 2 + 0.6
      }});
    }},
    // 刚性位置约束 (Clamp + 掩体滑移推挤，绝对防跌落虚空与防穿模)
    resolvePosition: function(currPos, newX, newZ) {{
      // 1. 刚性世界边界夹紧 (World Clamping)
      let clampedX = Math.max(-HALF_SIZE, Math.min(HALF_SIZE, newX));
      let clampedZ = Math.max(-HALF_SIZE, Math.min(HALF_SIZE, newZ));

      // 2. AABB 掩体静态阻挡与法线滑动 (Obstacle Slide)
      for (const obs of obstacles) {{
        if (clampedX > obs.minX && clampedX < obs.maxX && clampedZ > obs.minZ && clampedZ < obs.maxZ) {{
          // 产生碰撞，优先沿单轴滑动阻挡
          if (currPos.x <= obs.minX || currPos.x >= obs.maxX) clampedX = currPos.x;
          if (currPos.z <= obs.minZ || currPos.z >= obs.maxZ) clampedZ = currPos.z;
        }}
      }}
      return {{ x: clampedX, z: clampedZ }};
    }},
    getBoundaries: function() {{
      return {{ min: -HALF_SIZE, max: HALF_SIZE }};
    }}
  }};
}})();

// 窗口失焦按键清空守卫 (防止切换标签页或最小化时角色一直狂奔)
window.addEventListener('blur', function() {{
  if (typeof keyState !== 'undefined') {{
    for (const k in keyState) keyState[k] = false;
  }}
  if (typeof moveFwd !== 'undefined') {{
    moveFwd = false; moveBwd = false; moveLeft = false; moveRight = false;
  }}
}});
"""

    @staticmethod
    def get_lifecycle_cleaner_js() -> str:
        """防线六：弹道与粒子生命周期自动销毁器 (防内存泄漏与掉帧卡死)"""
        return """
// =================================================================
// 🛡️ 防线六: 实体生命周期超时与越界自动回收器 (Lifecycle GC Guard)
// =================================================================
function pruneDeadEntities(entityList, scene, maxLifetimeSec = 5.0) {
  const now = Date.now();
  for (let i = entityList.length - 1; i >= 0; i--) {
    const e = entityList[i];
    const isExpired = e.birthTime && (now - e.birthTime > maxLifetimeSec * 1000);
    const isOutOfBounds = e.mesh && (Math.abs(e.mesh.position.x) > 80 || Math.abs(e.mesh.position.z) > 80);
    
    if (isExpired || isOutOfBounds || e.isDead) {
      if (scene && e.mesh) scene.remove(e.mesh);
      entityList.splice(i, 1);
    }
  }
}
"""
