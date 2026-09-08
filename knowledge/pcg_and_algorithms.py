#!/usr/bin/env python3
"""
pcg_and_algorithms.py: 关卡设计、程序化内容生成 (PCG) 与寻路算法知识库
为关卡设计师与主程智能体提供地牢生成、噪声地形、A* 寻路与四叉树空间索引。
"""
import math
import heapq
import random
from typing import List, Dict, Tuple, Set, Optional, Any

class PCGAndAlgorithmsKnowledge:

    # 1. BSP (二叉空间分割) 随机地牢生成算法
    @staticmethod
    def generate_bsp_dungeon(width: int = 50, height: int = 40, min_room_size: int = 6, max_splits: int = 4) -> Dict[str, Any]:
        """使用 BSP 树递归切分空间，生成彼此连通的房间与走廊"""
        grid = [[1 for _ in range(width)] for _ in range(height)] # 1=墙, 0=地板
        rooms = []

        def split_space(x, y, w, h, depth):
            if depth >= max_splits or (w <= min_room_size * 2 and h <= min_room_size * 2):
                # 创建房间
                rw = random.randint(min_room_size, max(min_room_size, w - 2))
                rh = random.randint(min_room_size, max(min_room_size, h - 2))
                rx = x + random.randint(1, w - rw - 1)
                ry = y + random.randint(1, h - rh - 1)
                rooms.append({"x": rx, "y": ry, "w": rw, "h": rh, "cx": rx + rw//2, "cy": ry + rh//2})
                for r in range(ry, ry + rh):
                    for c in range(rx, rx + rw):
                        if 0 <= r < height and 0 <= c < width:
                            grid[r][c] = 0
                return

            split_horiz = random.choice([True, False]) if (w >= min_room_size*2 and h >= min_room_size*2) else (h > w)
            if split_horiz and h >= min_room_size * 2:
                split_y = random.randint(min_room_size, h - min_room_size)
                split_space(x, y, w, split_y, depth + 1)
                split_space(x, y + split_y, w, h - split_y, depth + 1)
            elif w >= min_room_size * 2:
                split_x = random.randint(min_room_size, w - min_room_size)
                split_space(x, y, split_x, h, depth + 1)
                split_space(x + split_x, y, w - split_x, h, depth + 1)

        split_space(0, 0, width, height, 0)

        # 连接走廊 (L型连接)
        for i in range(len(rooms) - 1):
            r1, r2 = rooms[i], rooms[i+1]
            cx1, cy1 = r1["cx"], r1["cy"]
            cx2, cy2 = r2["cx"], r2["cy"]

            # 横向
            for c in range(min(cx1, cx2), max(cx1, cx2) + 1):
                if 0 <= cy1 < height and 0 <= c < width: grid[cy1][c] = 0
            # 纵向
            for r in range(min(cy1, cy2), max(cy1, cy2) + 1):
                if 0 <= r < height and 0 <= cx2 < width: grid[r][cx2] = 0

        return {"width": width, "height": height, "grid": grid, "rooms": rooms}

    # 2. A* 启发式网格寻路算法
    @staticmethod
    def a_star_search(grid: List[List[int]], start: Tuple[int, int], target: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """A* 寻路算法 (0=可通行, 1=障碍物)
        返回路径坐标序列 [(x1,y1), (x2,y2), ...]
        """
        rows, cols = len(grid), len(grid[0])
        start_x, start_y = start
        target_x, target_y = target

        if grid[target_y][target_x] != 0 or grid[start_y][start_x] != 0:
            return None

        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1]) # 曼哈顿距离

        open_set = []
        heapq.heappush(open_set, (0 + heuristic(start, target), 0, start, [start]))
        visited_costs = {start: 0}

        dirs = [(0,1), (0,-1), (1,0), (-1,0)]

        while open_set:
            _, g_cost, current, path = heapq.heappop(open_set)

            if current == target:
                return path

            for dx, dy in dirs:
                nx, ny = current[0] + dx, current[1] + dy
                neighbor = (nx, ny)

                if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] == 0:
                    new_g = g_cost + 1
                    if neighbor not in visited_costs or new_g < visited_costs[neighbor]:
                        visited_costs[neighbor] = new_g
                        f_cost = new_g + heuristic(neighbor, target)
                        heapq.heappush(open_set, (f_cost, new_g, neighbor, path + [neighbor]))

        return None

    # 3. 四叉树空间分区索引 (用于千万级碰撞对过滤)
    class SimpleQuadTree:
        def __init__(self, boundary: Tuple[float, float, float, float], capacity: int = 4):
            # boundary: (x, y, w, h)
            self.boundary = boundary
            self.capacity = capacity
            self.points = []
            self.divided = False

        def subdivide(self):
            x, y, w, h = self.boundary
            hw, hh = w / 2, h / 2
            self.nw = PCGAndAlgorithmsKnowledge.SimpleQuadTree((x, y, hw, hh), self.capacity)
            self.ne = PCGAndAlgorithmsKnowledge.SimpleQuadTree((x + hw, y, hw, hh), self.capacity)
            self.sw = PCGAndAlgorithmsKnowledge.SimpleQuadTree((x, y + hh, hw, hh), self.capacity)
            self.se = PCGAndAlgorithmsKnowledge.SimpleQuadTree((x + hw, y + hh, hw, hh), self.capacity)
            self.divided = True

        def insert(self, point: Dict[str, Any]) -> bool:
            x, y, w, h = self.boundary
            px, py = point["x"], point["y"]
            if not (x <= px < x + w and y <= py < y + h):
                return False

            if len(self.points) < self.capacity and not self.divided:
                self.points.append(point)
                return True

            if not self.divided:
                self.subdivide()

            return (self.nw.insert(point) or self.ne.insert(point) or
                    self.sw.insert(point) or self.se.insert(point))
