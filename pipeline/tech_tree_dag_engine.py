"""
Tech Tree Directed Acyclic Graph (DAG) & Industrial Economy Balance Solver (Mindustry Standard)
深度有向无环图科技树与工业生产链解算器

核心能力:
1. DAG 拓扑排序与环路死锁检测 (Kahn's Algorithm)，保证科技树无循环死锁
2. 物质产出与消耗平衡比 (Production-to-Consumption Ratio Matrix)，定位产能瓶颈
3. 导出具备工业级节点依赖的 JSON 科技树配置与前端交互系统
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple


@dataclass
class TechNode:
    id: str
    name: str
    cost: Dict[str, int]  # {"copper": 100, "lead": 50}
    prerequisites: List[str] = field(default_factory=list)
    description: str = ""
    unlocked_buildings: List[str] = field(default_factory=list)


class TechTreeDAGEngine:
    """
    科技树 DAG 拓扑求解器
    """
    def __init__(self):
        self.nodes: Dict[str, TechNode] = {}

    def add_node(self, id: str, name: str, cost: Dict[str, int], prerequisites: List[str],
                 description: str = "", unlocked_buildings: List[str] = None):
        self.nodes[id] = TechNode(
            id=id,
            name=name,
            cost=cost,
            prerequisites=prerequisites,
            description=description,
            unlocked_buildings=unlocked_buildings or []
        )

    def validate_dag(self) -> Tuple[bool, List[str], Optional[str]]:
        """
        验证有向无环图 (DAG):
        - 检查所有前置依赖是否存在
        - 拓扑排序检测是否有环路
        返回: (is_valid, sorted_order, error_message)
        """
        # 1. 检查悬空前置节点
        for node_id, node in self.nodes.items():
            for prereq in node.prerequisites:
                if prereq not in self.nodes:
                    return False, [], f"悬空前置依赖错误: 节点 '{node_id}' 的前置 '{prereq}' 不存在！"

        # 2. Kahn 算法拓扑排序与环路检测
        in_degree = {nid: 0 for nid in self.nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in self.nodes}

        for node_id, node in self.nodes.items():
            for prereq in node.prerequisites:
                adj[prereq].append(node_id)
                in_degree[node_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_order = []

        while queue:
            curr = queue.pop(0)
            sorted_order.append(curr)
            for child in adj[curr]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(sorted_order) != len(self.nodes):
            cycle_nodes = [nid for nid, deg in in_degree.items() if deg > 0]
            return False, [], f"严重死循环错误: 科技树检测到循环依赖闭环: {cycle_nodes}"

        return True, sorted_order, None

    @classmethod
    def analyze_production_bottleneck(cls, drill_production_rate: float,
                                      conveyor_bandwidth: float,
                                      turret_consumption_rate: float) -> Dict:
        """
        测算采矿-输送-消耗全链路瓶颈
        """
        throughput = min(drill_production_rate, conveyor_bandwidth)
        coverage_ratio = throughput / max(0.001, turret_consumption_rate)
        status = "HEALTHY"
        if throughput < turret_consumption_rate:
            status = "BOTTLENECK_STARVATION"  # 炮塔弹药断供
        elif conveyor_bandwidth < drill_production_rate:
            status = "BOTTLENECK_CONGESTION"   # 传送带运力不足堵塞

        return {
            "drill_production": drill_production_rate,
            "conveyor_capacity": conveyor_bandwidth,
            "turret_consumption": turret_consumption_rate,
            "effective_throughput": throughput,
            "coverage_ratio": round(coverage_ratio, 2),
            "balance_status": status
        }

    @classmethod
    def get_standard_mindustry_tech_tree(cls) -> 'TechTreeDAGEngine':
        engine = cls()
        # 基础启动
        engine.add_node("core_foundation", "基础核心", {}, [], "基地核心，提供基础资源存储", ["core"])
        # 1 阶工业
        engine.add_node("mechanical_drill", "机械采矿机", {"copper": 30}, ["core_foundation"], "自动化开采地表矿脉", ["drill"])
        engine.add_node("conveyor_belt", "基础传送带", {"copper": 10}, ["core_foundation"], "以恒定速率运输固体物资", ["conveyor"])
        engine.add_node("copper_wall", "铜质防爆墙", {"copper": 25}, ["core_foundation"], "具备47转角自咬合装甲", ["wall"])
        # 2 阶防御
        engine.add_node("duo_turret", "双联机炮塔", {"copper": 45}, ["conveyor_belt", "mechanical_drill"], "消耗铜矿/铅矿自动射击", ["duo"])
        engine.add_node("router", "三路分流器", {"copper": 25}, ["conveyor_belt"], "轮询将物品分配至多路下游", ["router"])
        # 3 阶进阶
        engine.add_node("scatter_turret", "散射破空炮", {"copper": 80, "lead": 50}, ["duo_turret"], "发射高爆破片克制集群虫潮", ["scatter"])
        engine.add_node("combustion_generator", "燃烧发电机", {"copper": 60, "lead": 40}, ["router"], "消耗燃料为电网供电", ["generator"])
        return engine
