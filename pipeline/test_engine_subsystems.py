# =================================================================
# 🧪 Game-Agent: 工业级引擎核心子系统单元测试套件
# (test_engine_subsystems.py)
# 针对场景图矩阵数学、动态材质合批、脏标记传播与性能探针进行 100% 确定性断言
# =================================================================

import unittest
import math
from pipeline.engine_scene_graph import Transform2D
from pipeline.engine_render_batcher import RenderQueueBatcher, RenderCommand, Material
from pipeline.engine_profiler_diagnostics import EngineProfiler
from pipeline.engine_asset_catalog import TextureAtlasCatalog

class TestEngineSubsystems(unittest.TestCase):
    
    def test_transform_matrix_identity(self):
        """测试单位矩阵初始化与局部矩阵计算"""
        node = Transform2D("root")
        node.set_position(100.0, 50.0)
        node.set_rotation(0.0)
        node.set_scale(1.0, 1.0)
        
        m = node.get_world_matrix()
        # [1, 0, 0, 1, 100, 50]
        self.assertAlmostEqual(m[0], 1.0)
        self.assertAlmostEqual(m[1], 0.0)
        self.assertAlmostEqual(m[2], 0.0)
        self.assertAlmostEqual(m[3], 1.0)
        self.assertAlmostEqual(m[4], 100.0)
        self.assertAlmostEqual(m[5], 50.0)

    def test_scene_graph_hierarchy_matrix_cascade(self):
        """测试场景图父子三级嵌套变换与旋转级联计算"""
        # 1. 根节点 (机甲底盘): 位于 (100, 200)，旋转 0 度
        chassis = Transform2D("chassis")
        chassis.set_position(100.0, 200.0)
        
        # 2. 子节点 (炮塔支架): 局部位于 (0, 0)，局部旋转 90 度 (pi/2)
        turret = Transform2D("turret")
        turret.set_rotation(math.pi / 2.0)
        chassis.add_child(turret)
        
        # 3. 孙节点 (炮管枪口): 局部向前延伸 50 像素 (局部 x=50, y=0)
        barrel = Transform2D("barrel")
        barrel.set_position(50.0, 0.0)
        turret.add_child(barrel)
        
        # 计算炮管世界坐标：
        # 炮塔旋转 90 度后，局部 x 轴指向世界 y 轴正方向
        # 故炮口的世界坐标应为 (100, 200 + 50) = (100, 250)
        gun_tip_world = barrel.transform_point(0, 0)
        self.assertAlmostEqual(gun_tip_world[0], 100.0, places=4)
        self.assertAlmostEqual(gun_tip_world[1], 250.0, places=4)

    def test_dirty_flag_lazy_evaluation(self):
        """测试脏标记链式传播与惰性求值"""
        parent = Transform2D("parent")
        child = Transform2D("child")
        parent.add_child(child)
        
        # 首次计算世界矩阵后，清除 is_dirty
        _ = child.get_world_matrix()
        self.assertFalse(child.is_dirty)
        self.assertFalse(parent.is_dirty)
        
        # 修改父节点位置，必须自动将所有子节点置脏
        parent.set_position(50.0, 60.0)
        self.assertTrue(parent.is_dirty)
        self.assertTrue(child.is_dirty)
        
        # 再次获取子节点世界矩阵，应更新为最新位置
        pos = child.get_world_position()
        self.assertAlmostEqual(pos[0], 50.0)
        self.assertAlmostEqual(pos[1], 60.0)
        self.assertFalse(child.is_dirty)

    def test_render_queue_batching_efficiency(self):
        """测试渲染指令多通道排序与 DrawCall 压缩合批"""
        batcher = RenderQueueBatcher()
        mat_chassis = Material("mat_chassis", "#2563eb")
        mat_turret = Material("mat_turret", "#dc2626")
        mat_bullet = Material("mat_bullet", "#fbbf24")

        # 模拟提交 300 个实体，包含机甲、炮塔与大量的子弹
        # 故意乱序提交
        for i in range(100):
            batcher.submit(RenderCommand("RECT", mat_bullet, [1,0,0,1,i,i], phase=1, layer=2))
            batcher.submit(RenderCommand("RECT", mat_chassis, [1,0,0,1,i,i], phase=1, layer=1))
            batcher.submit(RenderCommand("RECT", mat_turret, [1,0,0,1,i,i], phase=1, layer=1))

        # 未合批前为 300 次调用
        # 合批排序后：
        # Layer 1: mat_chassis (100个合并为1次) + mat_turret (100个合并为1次) = 2 DrawCalls
        # Layer 2: mat_bullet (100个合并为1次) = 1 DrawCall
        # 总 DrawCalls 应严格等于 3！
        stats = batcher.evaluate_batching()
        self.assertEqual(stats["total_commands"], 300)
        self.assertEqual(stats["draw_calls"], 3)
        self.assertEqual(stats["batch_ratio"], 99.0) # 压缩了 99% 的调用！

    def test_profiler_performance_budget(self):
        """测试性能分析器对 60fps 达标线的判定"""
        profiler = EngineProfiler()
        # 良好运行指标: 60fps, 8.5ms, 12 DrawCalls, 88% 合批率
        res_good = profiler.evaluate_frame_metrics(60.0, 8.5, 12, 88.0)
        self.assertTrue(res_good["all_pass"])
        self.assertEqual(res_good["summary"], "PERFECT_60FPS_BATCHED")

        # 严重卡顿指标: 24fps, 35.0ms, 85 DrawCalls, 20% 合批率
        res_bad = profiler.evaluate_frame_metrics(24.0, 35.0, 85, 20.0)
        self.assertFalse(res_bad["all_pass"])
        self.assertEqual(res_bad["summary"], "PERFORMANCE_BUDGET_EXCEEDED")

    def test_asset_catalog_ref_counting(self):
        """测试资产图集引用计数与切片检索"""
        catalog = TextureAtlasCatalog("mech_atlas", 512, 512)
        catalog.add_frame("body", 0, 0, 64, 64)
        catalog.add_frame("cannon", 64, 0, 32, 64)

        self.assertIn("body", catalog.frames)
        self.assertIn("cannon", catalog.frames)
        
        self.assertEqual(catalog.retain(), 1)
        self.assertEqual(catalog.retain(), 2)
        self.assertEqual(catalog.release(), 1)

if __name__ == "__main__":
    unittest.main()
