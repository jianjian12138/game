#!/usr/bin/env python3
"""
deterministic_solvers.py: 确定性算法求解器套件 (Deterministic Solvers Suite)
纯 Python 3.9+ 标准库实现，零外部依赖。

基于《妙点小匠》第四阶段核心破局点：有些问题不该继续问模型，模型做不到数学级精确判定。
本模块提供确定性算法，硬性求解：
1. A* 连通性求解器 (PathConnectivitySolver): 计算敌怪出生点/关卡起点到核心/终点是否存在可行走的无障碍拓扑通路。
2. 开局矿脉覆盖度求解器 (ResourceReachabilitySolver): 计算核心建造有效半径内是否覆盖足够开采的基础矿脉 (铜/铅)。
3. 物流网络死锁与环路求解器 (LogisticsDeadlockSolver): 有向图环路检测，断言输送带网络不存在无出路的闭环死锁。
"""
import sys
import heapq
from typing import List, Tuple, Set, Dict, Any, Optional

class PathConnectivitySolver:
    """A* 算法求解 2D 离散网格地图连通性"""
    @staticmethod
    def solve_path(grid: List[List[int]], start: Tuple[int, int], target: Tuple[int, int], solid_ids: Set[int]) -> Dict[str, Any]:
        """
        grid: 2D 网格，grid[y][x] 为 BlockId
        start: (x, y)
        target: (x, y)
        solid_ids: 不可行走的障碍物 ID 集合 (如石壁、实心核心等)
        """
        h = len(grid)
        w = len(grid[0]) if h > 0 else 0
        
        sx, sy = start
        tx, ty = target
        
        if sx < 0 or sx >= w or sy < 0 or sy >= h or tx < 0 or tx >= w or ty < 0 or ty >= h:
            return {"reachable": False, "error": "起点或终点超出网格范围", "path_length": 0, "path": []}

        def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> int:
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = []
        heapq.heappush(open_set, (0 + heuristic(start, target), 0, start))
        
        came_from = {}
        g_score = {start: 0}
        visited = set()

        while open_set:
            _, current_g, current = heapq.heappop(open_set)
            if current in visited:
                continue
            visited.add(current)

            if current == target:
                # 重建路径
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return {
                    "reachable": True,
                    "path_length": len(path),
                    "visited_nodes": len(visited),
                    "path": path
                }

            cx, cy = current
            # 4 向连通移动 (上, 下, 左, 右)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                neighbor = (nx, ny)
                if 0 <= nx < w and 0 <= ny < h:
                    # 终点若是障碍允许触达（例如攻击目标核心）
                    is_blocked = grid[ny][nx] in solid_ids and neighbor != target
                    if is_blocked:
                        continue
                    
                    tentative_g = current_g + 1
                    if neighbor not in g_score or tentative_g < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g
                        f_score = tentative_g + heuristic(neighbor, target)
                        heapq.heappush(open_set, (f_score, tentative_g, neighbor))

        return {
            "reachable": False,
            "error": "无可行走通路被障碍物完全封死",
            "visited_nodes": len(visited),
            "path_length": 0,
            "path": []
        }

class ResourceReachabilitySolver:
    """开局矿脉覆盖求解器"""
    @staticmethod
    def solve_coverage(ores_map: Dict[str, List[Tuple[int, int]]], core_pos: Tuple[int, int], max_radius_tiles: float = 25.0) -> Dict[str, Any]:
        """
        ores_map: {"copper": [(x,y), ...], "lead": [(x,y), ...]}
        core_pos: (cx, cy)
        """
        cx, cy = core_pos
        report = {}
        all_covered = True
        
        for ore_name, coords in ores_map.items():
            nearest_dist = float("inf")
            count_in_range = 0
            for ox, oy in coords:
                d = ((ox - cx)**2 + (oy - cy)**2)**0.5
                if d < nearest_dist:
                    nearest_dist = d
                if d <= max_radius_tiles:
                    count_in_range += 1
            
            is_ok = count_in_range >= 4 # 至少 4 格矿块才能稳定支持前期经济
            report[ore_name] = {
                "count_in_radius": count_in_range,
                "nearest_distance": round(nearest_dist, 2),
                "satisfies_start": is_ok
            }
            if not is_ok:
                all_covered = False

        return {
            "all_ores_covered": all_covered,
            "details": report
        }

class LogisticsDeadlockSolver:
    """有向图环路与死锁拓扑求解器"""
    @staticmethod
    def solve_deadlock(conveyor_nodes: Dict[Tuple[int, int], Tuple[int, int]]) -> Dict[str, Any]:
        """
        conveyor_nodes: {(x, y): (target_x, target_y)} 传送带流向邻接表
        """
        visited = set()
        recursion_stack = set()
        cycles = []

        def dfs(node: Tuple[int, int], path: List[Tuple[int, int]]):
            visited.add(node)
            recursion_stack.add(node)
            target = conveyor_nodes.get(node)
            if target:
                if target in recursion_stack:
                    # 发现闭环死循环!
                    idx = path.index(target) if target in path else 0
                    cycles.append(path[idx:] + [target])
                elif target not in visited and target in conveyor_nodes:
                    dfs(target, path + [target])
            recursion_stack.remove(node)

        for node in list(conveyor_nodes.keys()):
            if node not in visited:
                dfs(node, [node])

        return {
            "has_deadlock_cycle": len(cycles) > 0,
            "detected_cycles_count": len(cycles),
            "cycles": cycles
        }

class DeterministicSolverSuite:
    """全套确定性求解门禁编排"""
    @staticmethod
    def run_full_suite() -> Dict[str, Any]:
        print("=== DeterministicSolverSuite: 启动确定性算法求解门禁 ===")
        
        # 1. 模拟 60x40 地图，中间放岩石阻隔，测试起点 (30, 6) 到核心 (30, 20) 的 A* 连通性
        grid = [[0 for _ in range(60)] for _ in range(40)]
        solid_blocks = {16} # 16 代表 StoneWall
        # 制造一堵带缺口的峡谷岩石墙
        for x in range(10, 50):
            if x != 30 and x != 31: # 保留峡谷通道
                grid[12][x] = 16

        path_res = PathConnectivitySolver.solve_path(grid, (30, 6), (30, 20), solid_blocks)
        p_ok = path_res["reachable"]
        print(f"  [PATH SOLVER] A* 敌怪出生点到核心连通性: {'[PASS]' if p_ok else '[FAIL]'} (路径长度: {path_res['path_length']})")

        # 2. 矿脉覆盖度求解
        ores = {
            "copper": [(22, 18), (22, 19), (22, 20), (22, 21), (22, 22)],
            "lead": [(38, 18), (38, 19), (38, 20), (38, 21)],
            "coal": [(30, 32), (30, 33), (31, 32), (31, 33)]
        }
        ore_res = ResourceReachabilitySolver.solve_coverage(ores, (30, 20), max_radius_tiles=20.0)
        o_ok = ore_res["all_ores_covered"]
        print(f"  [RESOURCE SOLVER] 开局基础矿脉有效覆盖率: {'[PASS]' if o_ok else '[FAIL]'}")

        # 3. 物流有向图环路检测
        # 测试一条健康的向核心流动的传送带网络
        conveyors = {
            (22, 18): (23, 18),
            (23, 18): (24, 18),
            (24, 18): (25, 18) # 流入核心
        }
        deadlock_res = LogisticsDeadlockSolver.solve_deadlock(conveyors)
        d_ok = not deadlock_res["has_deadlock_cycle"]
        print(f"  [DEADLOCK SOLVER] 物流拓扑无死锁环路检测: {'[PASS]' if d_ok else '[FAIL]'}")

        all_passed = p_ok and o_ok and d_ok
        verdict = "PASS" if all_passed else "FAIL"
        print(f"\n  [SOLVER VERDICT] [{verdict}] (全部物理拓扑与连通性经确定性算法证实无误)\n==========================================================")
        return {
            "verdict": verdict,
            "path_connectivity": path_res,
            "resource_coverage": ore_res,
            "logistics_deadlock": deadlock_res
        }

if __name__ == "__main__":
    DeterministicSolverSuite.run_full_suite()
