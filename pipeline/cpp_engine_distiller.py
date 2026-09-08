# =================================================================
# 📖 Game-Agent: C++ 游戏引擎与极客时间系统工程自动化蒸馏器
# (cpp_engine_distiller.py)
# 对应著作：
# 1. ThisisGame/cpp-game-engine-book (22章从零手写C++游戏引擎)
# 2. it-ebooks-0/geektime-books (极客时间现代C++、V8底层原理与系统工程)
# =================================================================

import json
from pathlib import Path
from typing import Dict, List, Any

class CppEngineDistiller:
    """
    C++ 游戏引擎与底层系统工程知识蒸馏器
    负责将底层 C++ 引擎的渲染管线、场景图、合批、视锥裁剪以及 V8 零GC系统优化
    完整编译为规范化的工程技能库与代码生成器规范。
    """
    
    CPP_ENGINE_CHAPTERS = [
        {"chap": 1, "name": "编译环境与基础窗口", "principle": "严禁平台锁死，统一跨平台抽象与生命周期入口。"},
        {"chap": 2, "name": "游戏主循环与时钟系统", "principle": "定频 FixedUpdate 驱动物理与逻辑，变频 Update 驱动平滑渲染，解决螺旋断步与掉帧穿墙。"},
        {"chap": 3, "name": "现代图形流水线与顶点缓冲", "principle": "VAO/VBO/EBO 顶点规约，显卡与 CPU 零冗余数据传输，绘制指令封装。"},
        {"chap": 4, "name": "矩阵数学与坐标空间变换", "principle": "统一 4x4 仿射矩阵变换 (Local -> World -> View -> Projection)，规范右手坐标系。"},
        {"chap": 5, "name": "摄像机系统与视锥裁剪", "principle": "视锥体 (View Frustum) 平面方程求交，视口外实体 100% 裁剪，杜绝浪费光栅化带宽。"},
        {"chap": 6, "name": "纹理采样与图集优化", "principle": "贴图状态合并，Texture Atlas 图集切片，消除显卡纹理单元切换开销。"},
        {"chap": 7, "name": "网格几何体与文件序列化", "principle": "紧凑二进制/结构化顶点数据组织，避免冗余反序列化耗时。"},
        {"chap": 8, "name": "GameObject-Component 场景图架构", "principle": "Transform 父子层级树，父节点世界矩阵递归级联，脏标记 (is_dirty) 链式传播与惰性求值。"},
        {"chap": 9, "name": "材质参数槽与着色器抽象", "principle": "Material 封装 Shader Program、Uniform 参数表、混合模式 (BlendMode) 与深度写入状态。"},
        {"chap": 10, "name": "多摄像机与分层遮罩", "principle": "Camera Layer Mask 与渲染目标 (FBO) 离屏渲染，隔离 UI、背景与主场景。"},
        {"chap": 11, "name": "渲染指令队列与动态合批", "principle": "绘制与逻辑解耦，RenderQueue 多级排序 (Opaque/Transparent/UI)，连续相同材质自动合批折叠。"},
        {"chap": 12, "name": "光照模型与阴影映射", "principle": "Phong/Blinn-Phong 光照计算，法线贴图与阴影贴图 (Shadow Map) 采样。"},
        {"chap": 13, "name": "字体图集与文字矢量渲染", "principle": "FreeType 动态字形烘焙至 Texture Atlas，单次 DrawCall 合批绘制全屏文本。"},
        {"chap": 14, "name": "GUI 树状层级与画布适配", "principle": "UI 2D 锚点 (Anchor)、轴心点 (Pivot) 与射线拾取事件冒泡。"},
        {"chap": 15, "name": "音频总线与空间声场", "principle": "Master/BGM/SFX 混音总线，3D 听者空间衰减与多音轨自适应切换。"},
        {"chap": 16, "name": "全景运行时性能分析器", "principle": "EasyProfiler 级监控，实时统计 FrameTime、DrawCalls、Batch Ratio、Memory Heap。"},
        {"chap": 17, "name": "脚本语言与数据驱动绑定", "principle": "C++/JS 核心引擎暴露轻量组件 API，数据驱动热插拔。"},
        {"chap": 18, "name": "骨骼蒙皮动画与矩阵调色板", "principle": "骨骼关节层级树，四元数/矩阵时间轴 LERP/SLERP 插值，顶点权重蒙皮。"},
        {"chap": 19, "name": "粒子系统发射器", "principle": "结构体连续内存粒子池，发射速率、重力、阻尼、生命周期 Alpha 渐变。"},
        {"chap": 20, "name": "物理系统与宽相窄相碰撞", "principle": "空间分区 (Grid/Quadtree) 宽相过滤 + SAT/AABB 窄相求交 + 冲量守恒解算。"},
        {"chap": 21, "name": "多线程/指令双缓冲架构", "principle": "主逻辑线程生产 RenderCommand，渲染线程消费并执行底层 API，消除管线空泡。"},
        {"chap": 22, "name": "商业化打包与跨端交付", "principle": "资源压缩打包、无死锁依赖、零缺失完整验收交付。"}
    ]

    GEEKTIME_SYSTEMS_CORE = [
        {
            "book": "图解 Google V8",
            "topic": "Hidden Class 隐藏类与内联缓存 (IC)",
            "rules": [
                "构造函数必须一次性初始化全部字段，绝对不可在对象生成后动态挂载属性，确保单态内联缓存 (Monomorphic IC)。",
                "保持字段赋值顺序绝对一致，避免产生隐藏类变异分支树。",
                "热循环中消灭 delete 操作，delete 会使对象退化为哈希慢速字典模式。"
            ]
        },
        {
            "book": "图解 Google V8 & 现代C++实战",
            "topic": "零堆分配热循环 (Zero-GC Hot Loop)",
            "rules": [
                "Update/Render 热路径中杜绝 new/[]/{}，所有临时对象使用预分配 Scratch 变量复用。",
                "弹幕、粒子、敌人采用固定上限预分配对象池 (Pre-allocated Object Pool)。",
                "使用 TypedArray (Float32Array, Int32Array) 连续内存存储矩阵、坐标与粒子属性，最大化 L1 Cache 命中并根绝垃圾回收。"
            ]
        },
        {
            "book": "从0开始学架构 & 软件设计之美",
            "topic": "正交微内核与事件总线解耦",
            "rules": [
                "系统分层正交：Input 采集 -> GameLogic 模拟 -> RenderQueue 呈现 -> WebAudio 响应，层与层单向流动。",
                "模块之间禁止直接硬编码互调，统一通过发布-订阅 (Publish-Subscribe) 事件总线通信。"
            ]
        },
        {
            "book": "性能工程高手课 & Linux性能优化实战",
            "topic": "硬性性能预算与透明可观测性",
            "rules": [
                "严格把守 16.6ms (60fps) 帧耗时预算，CPU 纯逻辑耗时控制在 4ms 以内。",
                "单屏 DrawCall 预算 <= 25，动态合批折叠率必须 >= 80%。",
                "提供全景实时 Profiler HUD，使性能瓶颈在开发期即可无死角暴露。"
            ]
        }
    ]

    def __init__(self, output_dir: Path = (Path(__file__).resolve().parent / 'knowledge/book_skills')):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def distill_cpp_game_engine(self) -> Path:
        """编译生成 C++ 游戏引擎 22 章技能大典"""
        file_path = self.output_dir / "CppGameEngine_SKILL.md"
        content = [
            "# 📚 工业级 C++ 游戏引擎架构大典 (ThisisGame/cpp-game-engine-book)",
            "- **来源文献**: 《从零手写C++游戏引擎》全 22 章",
            "- **核心定位**: 游戏引擎骨架、场景图、渲染指令队列、材质系统与动态合批",
            "\n---\n",
            "## 🏛️ 22 章全景架构精要与设计规约\n"
        ]
        
        for item in self.CPP_ENGINE_CHAPTERS:
            content.append(f"### 第 {item['chap']} 章: {item['name']}")
            content.append(f"- **核心架构原则**: {item['principle']}")
            content.append("")

        content.extend([
            "\n---\n",
            "## ⚡ 核心子系统代码落地范式 (C++ & Native Web)\n",
            "### 1. Scene Graph Transform 树与脏标记惰性求值",
            "```javascript",
            "// TransformNode 规范：支持父子级联与脏标记",
            "class TransformNode {",
            "    constructor(name) {",
            "        this.name = name;",
            "        this.parent = null;",
            "        this.children = [];",
            "        this.localPosition = { x: 0, y: 0 };",
            "        this.localRotation = 0;",
            "        this.localScale = { x: 1, y: 1 };",
            "        this.worldMatrix = new Float32Array(6); // 2D 仿射矩阵",
            "        this.isDirty = true;",
            "    }",
            "    addChild(node) { node.parent = this; this.children.push(node); node.markDirty(); }",
            "    markDirty() {",
            "        this.isDirty = true;",
            "        for (let i = 0; i < this.children.length; i++) this.children[i].markDirty();",
            "    }",
            "    getWorldMatrix() {",
            "        if (this.isDirty) this.updateWorldMatrix();",
            "        return this.worldMatrix;",
            "    }",
            "}",
            "```\n",
            "### 2. RenderCommand 队列与材质动态合批",
            "```javascript",
            "// 严禁在 Entity 中直接调用 ctx 绘制，统一提交 RenderCommand",
            "class RenderQueue {",
            "    constructor() {",
            "        this.commands = [];",
            "    }",
            "    submit(cmd) { this.commands.push(cmd); }",
            "    sort() {",
            "        // 排序规则: Phase -> Layer -> Material -> Depth",
            "        this.commands.sort((a, b) => a.phase - b.phase || a.layer - b.layer || a.materialId - b.materialId || a.depth - b.depth);",
            "    }",
            "}",
            "```"
        ])

        file_path.write_text("\n".join(content), encoding="utf-8")
        return file_path

    def distill_geektime_systems(self) -> Path:
        """编译生成极客时间系统工程与 V8 零GC大典"""
        file_path = self.output_dir / "GeekTimeSystems_SKILL.md"
        content = [
            "# ⚡ 极客时间底层系统工程与高并发架构大典 (it-ebooks-0/geektime-books)",
            "- **来源文献**: 《图解 Google V8》、《现代C++实战30讲》、《从0开始学架构》、《性能工程高手课》",
            "- **核心定位**: 内存对齐、零GC热循环、Hidden Class 稳定化、微内核正交解耦与稳帧红线",
            "\n---\n",
            "## 🧬 底层系统工程三大定律\n"
        ]

        for item in self.GEEKTIME_SYSTEMS_CORE:
            content.append(f"### 📘 《{item['book']}》: {item['topic']}")
            for r in item["rules"]:
                content.append(f"- **准则**: {r}")
            content.append("")

        content.extend([
            "\n---\n",
            "## 🛑 交付验收 V8 防暴毙军规",
            "1. **禁止在 Update/Render 内声明新对象**: 消除所有 `let obj = { ... }`，改用预分配静态复用池。",
            "2. **构造函数形状一致性**: 严禁在初始化后动态添加或修改属性键名，确保 V8 TurboFan 生成最优汇编代码。",
            "3. **TypedArray SoA 内存布局**: 采用 `Float32Array` 代替普通的 JS 稀疏对象数组，零垃圾回收负担。"
        ])

        file_path.write_text("\n".join(content), encoding="utf-8")
        return file_path

    def distill_all(self) -> Dict[str, str]:
        p1 = self.distill_cpp_game_engine()
        p2 = self.distill_geektime_systems()
        return {
            "cpp_engine_skill": str(p1),
            "geektime_systems_skill": str(p2)
        }

if __name__ == "__main__":
    distiller = CppEngineDistiller()
    res = distiller.distill_all()
    print("Distillation Complete:", json.dumps(res, indent=2, ensure_ascii=False))
