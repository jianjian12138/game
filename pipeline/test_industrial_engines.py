"""
Unit Test Suite for Game-Agent Industrial Engines
针对五大工业级底层引擎的自动化单元测试集
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.logistics_topology_engine import ConveyorTile, RouterTile, PowerGridNetwork, Direction
from pipeline.autotile_bitmask_engine import Blob47BitmaskSolver
from pipeline.flow_field_pathfinding import FlowFieldGrid
from pipeline.data_oriented_ecs import DataOrientedECS
from pipeline.tech_tree_dag_engine import TechTreeDAGEngine


class TestIndustrialEngines(unittest.TestCase):

    def test_logistics_conveyor_backpressure(self):
        """测试传送带队列推进与下游满载背压堵塞"""
        c1 = ConveyorTile(0, 0, Direction.RIGHT, capacity=4, speed=2.0)
        c2 = ConveyorTile(1, 0, Direction.RIGHT, capacity=2, speed=2.0)

        # 向 c1 推进 4 个物品
        self.assertTrue(c1.push_item("copper"))
        # 推进 0.5 秒让物品移开一段间距
        c1.update(0.3)
        self.assertTrue(c1.push_item("lead"))

        # 更新推进，物品移至出口并转入 c2
        for _ in range(5):
            c1.update(0.2, downstream_tile=c2)
            c2.update(0.2)

        # 检查物品总数是否物质守恒（绝不凭空消失）
        total_items = len(c1.items) + len(c2.items)
        self.assertEqual(total_items, 2, "物质不守恒！物品数量异常")

    def test_power_grid_solver(self):
        """测试电网图连通分量与负荷满足率计算"""
        grid = PowerGridNetwork()
        grid.add_generator(0, 0, 100.0)
        grid.add_pole(1, 0, connect_radius=2)
        grid.add_consumer(2, 0, 60.0)

        subnets = grid.solve_network()
        self.assertEqual(len(subnets), 1)
        self.assertEqual(subnets[0]["total_generation"], 100.0)
        self.assertEqual(subnets[0]["total_demand"], 60.0)
        self.assertEqual(subnets[0]["satisfaction_rate"], 1.0)
        self.assertFalse(subnets[0]["is_brownout"])

    def test_autotile_47_bitmask(self):
        """测试 8 邻居 47-Tile 转角掩码算法"""
        # 测试全包围 (46)
        solid_all = lambda nx, ny: True
        mask_center = Blob47BitmaskSolver.calculate_bitmask(5, 5, solid_all)
        self.assertEqual(mask_center, 46, "全包围中心瓦片索引应为 46")

        # 测试孤岛 (0)
        solid_none = lambda nx, ny: False
        mask_lone = Blob47BitmaskSolver.calculate_bitmask(5, 5, solid_none)
        self.assertEqual(mask_lone, 0, "孤岛瓦片索引应为 0")

    def test_flow_field_pathfinding(self):
        """测试势能向量场生成与 O(1) 采样"""
        ff = FlowFieldGrid(20, 20)
        # 目标设在 (10, 10)
        ff.generate_flow_field(10, 10)

        # (10, 8) 处的梯度向量应该向下指向 (0, 1)
        dx, dy = ff.vector_field[ff.idx(10, 8)]
        self.assertAlmostEqual(dx, 0.0, places=2)
        self.assertAlmostEqual(dy, 1.0, places=2)

        # 放置一堵墙在 (10, 9)
        ff.set_obstacle(10, 9, True)
        ff.generate_flow_field(10, 10)
        # 向量应自动向左或向右绕开障碍
        dx2, dy2 = ff.vector_field[ff.idx(10, 8)]
        self.assertNotEqual(dy2, 1.0, "遇到城墙阻挡后向量场必须发生绕路偏转！")

    def test_data_oriented_ecs(self):
        """测试紧凑内存 ECS 零 GC 实体池更新"""
        ecs = DataOrientedECS(capacity=1000)
        # 产生 500 发子弹
        for i in range(500):
            idx = ecs.spawn(100.0, 100.0, 50.0, 0.0, damage=15.0, lifetime=2.0)
            self.assertGreaterEqual(idx, 0)

        self.assertEqual(ecs.active_count, 500)
        # 运行更新
        ecs.update(0.5, 800.0, 600.0)
        self.assertEqual(ecs.active_count, 500)

        # 超出寿命
        ecs.update(2.0, 800.0, 600.0)
        self.assertEqual(ecs.active_count, 0, "寿命到期后实体必须清洁回收至空闲栈")

    def test_tech_tree_dag_validation(self):
        """测试科技树 DAG 拓扑排序与死锁检测"""
        tree = TechTreeDAGEngine.get_standard_mindustry_tech_tree()
        is_valid, sorted_order, err = tree.validate_dag()
        self.assertTrue(is_valid, f"标杆科技树应无环路错误: {err}")
        self.assertEqual(sorted_order[0], "core_foundation", "拓扑根节点必须是基础核心")

        # 故意注入一个循环依赖: core -> duo -> core
        tree.nodes["core_foundation"].prerequisites = ["duo_turret"]
        is_valid2, _, err2 = tree.validate_dag()
        self.assertFalse(is_valid2, "循环依赖必须被当场捕获报错！")


if __name__ == "__main__":
    unittest.main()
