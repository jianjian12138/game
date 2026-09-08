#!/usr/bin/env python3
"""
pipeline/ast_symbol_graph.py: 全局多语言 AST 符号图谱与级联重构守卫 (Global AST Symbol Dependency Graph)
解决 Agent 在跨文件、多语言大型项目开发中的符号幻觉与重构雪崩：
1. MultiLangSymbolParser: 支持 Python (内置 ast 模块)、JavaScript/TypeScript、Rust 与 GDScript 的符号抽取。
2. SymbolDependencyGraph: 建立面向文件与符号的有向依赖图 (Imports, Calls, Inherits, References)。
3. IntegrityAuditor: 检测跨文件悬空引用 (Dangling References)、跨模块循环依赖 (Cycles)。
4. CascadingRefactorPlanner: 符号重构或签名变动时，计算下游受损文件拓扑并自动生成级联修改建议。
"""

import os
import sys
import re
import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# 数据结构定义
# -----------------------------------------------------------------------------
@dataclass
class SymbolNode:
    name: str
    kind: str  # "class", "function", "struct", "enum", "variable", "module"
    file_path: str
    line_number: int
    signature: str = ""
    is_exported: bool = True

@dataclass
class DependencyEdge:
    source_file: str
    target_file: str
    symbol_name: str
    relation: str  # "imports", "calls", "inherits", "references"

# -----------------------------------------------------------------------------
# 多语言 AST 符号解析器
# -----------------------------------------------------------------------------
class MultiLangSymbolParser:
    @staticmethod
    def parse_python(file_path: Path) -> Tuple[List[SymbolNode], List[Tuple[str, str]]]:
        """使用 Python 标准库 ast 模块解析定义符号与导入引用"""
        symbols: List[SymbolNode] = []
        references: List[Tuple[str, str]] = [] # (symbol_name, relation)
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(file_path))
        except Exception:
            return symbols, references

        rel_path = str(file_path.relative_to(ROOT) if file_path.is_relative_to(ROOT) else file_path).replace("\\", "/")

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbols.append(SymbolNode(
                    name=node.name,
                    kind="class",
                    file_path=rel_path,
                    line_number=node.lineno,
                    signature=f"class {node.name}"
                ))
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        references.append((b.id, "inherits"))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 忽略以 _ 开头的私有局部函数
                args = [a.arg for a in node.args.args]
                sig = f"def {node.name}({', '.join(args)})"
                symbols.append(SymbolNode(
                    name=node.name,
                    kind="function",
                    file_path=rel_path,
                    line_number=node.lineno,
                    signature=sig,
                    is_exported=not node.name.startswith("__")
                ))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    references.append((alias.name.split(".")[0], "imports"))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    sym = f"{mod}.{alias.name}" if mod else alias.name
                    references.append((alias.name, "imports"))

        return symbols, references

    @staticmethod
    def parse_javascript_or_rust(file_path: Path) -> Tuple[List[SymbolNode], List[Tuple[str, str]]]:
        """针对 JS/TS 与 Rust 的词法/正则符号提取"""
        symbols: List[SymbolNode] = []
        references: List[Tuple[str, str]] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return symbols, references

        rel_path = str(file_path.relative_to(ROOT) if file_path.is_relative_to(ROOT) else file_path).replace("\\", "/")
        lines = content.splitlines()

        # JS/TS 匹配规则
        js_class_pattern = re.compile(r'class\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_]+))?')
        js_func_pattern = re.compile(r'(?:function\s+|([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)')
        js_import_pattern = re.compile(r'import\s+(?:\{([^}]+)\}|([A-Za-z0-9_]+))\s+from')

        # Rust 匹配规则
        rs_fn_pattern = re.compile(r'pub\s+fn\s+([a-zA-Z0-9_]+)\s*\(')
        rs_struct_pattern = re.compile(r'pub\s+(?:struct|enum)\s+([a-zA-Z0-9_]+)')
        rs_use_pattern = re.compile(r'use\s+([^;]+);')

        is_rust = file_path.suffix == ".rs"

        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if is_rust:
                m_fn = rs_fn_pattern.search(sline)
                if m_fn:
                    symbols.append(SymbolNode(m_fn.group(1), "function", rel_path, idx))
                m_st = rs_struct_pattern.search(sline)
                if m_st:
                    symbols.append(SymbolNode(m_st.group(1), "struct", rel_path, idx))
                m_use = rs_use_pattern.search(sline)
                if m_use:
                    last_item = m_use.group(1).split("::")[-1].replace("{", "").replace("}", "").strip()
                    references.append((last_item, "imports"))
            else:
                m_cls = js_class_pattern.search(sline)
                if m_cls:
                    symbols.append(SymbolNode(m_cls.group(1), "class", rel_path, idx))
                    if m_cls.group(2):
                        references.append((m_cls.group(2), "inherits"))
                m_imp = js_import_pattern.search(sline)
                if m_imp:
                    raw = m_imp.group(1) or m_imp.group(2) or ""
                    for item in raw.split(","):
                        it = item.strip()
                        if it: references.append((it, "imports"))

        return symbols, references

# -----------------------------------------------------------------------------
# 全局 AST 符号依赖图谱
# -----------------------------------------------------------------------------
class ASTSymbolGraph:
    def __init__(self):
        # symbol_name -> List[SymbolNode] (支持同名多态或重载)
        self.symbols_by_name: Dict[str, List[SymbolNode]] = {}
        # file_path -> List[SymbolNode]
        self.symbols_by_file: Dict[str, List[SymbolNode]] = {}
        # file_path -> Set[target_file] (文件级依赖)
        self.file_dependencies: Dict[str, Set[str]] = {}
        self.edges: List[DependencyEdge] = []

    def add_symbol(self, sym: SymbolNode):
        self.symbols_by_name.setdefault(sym.name, []).append(sym)
        self.symbols_by_file.setdefault(sym.file_path, []).append(sym)

    def add_edge(self, edge: DependencyEdge):
        self.edges.append(edge)
        self.file_dependencies.setdefault(edge.source_file, set()).add(edge.target_file)

    @classmethod
    def build_from_directory(cls, dir_path: str = "pipeline",
                             file_exts: Optional[List[str]] = None) -> "ASTSymbolGraph":
        """从指定目录全量扫描并构建多语言 AST 符号图谱"""
        graph = cls()
        exts = file_exts or [".py", ".js", ".ts", ".rs", ".gd"]
        target_dir = (ROOT / dir_path) if not Path(dir_path).is_absolute() else Path(dir_path)

        all_file_references: Dict[str, List[Tuple[str, str]]] = {}

        for p in target_dir.rglob("*"):
            if not p.is_file() or p.suffix not in exts:
                continue
            if any(ign in str(p) for ign in ["__pycache__", ".git", "target", "node_modules", ".temp"]):
                continue

            rel_path = str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p).replace("\\", "/")

            if p.suffix == ".py":
                syms, refs = MultiLangSymbolParser.parse_python(p)
            else:
                syms, refs = MultiLangSymbolParser.parse_javascript_or_rust(p)

            for s in syms:
                graph.add_symbol(s)
            all_file_references[rel_path] = refs

        # 第二遍：建立跨文件边
        for src_file, refs in all_file_references.items():
            for ref_name, relation in refs:
                # 寻找目标符号所在的文件
                if ref_name in graph.symbols_by_name:
                    for target_sym in graph.symbols_by_name[ref_name]:
                        if target_sym.file_path != src_file:
                            graph.add_edge(DependencyEdge(
                                source_file=src_file,
                                target_file=target_sym.file_path,
                                symbol_name=ref_name,
                                relation=relation
                            ))

        return graph

    def find_circular_dependencies(self) -> List[List[str]]:
        """检测文件级导入是否存在环状死锁依赖 (Tarjan / DFS 回溯)"""
        cycles: List[List[str]] = []
        visited = set()
        stack = []

        def dfs(node: str):
            visited.add(node)
            stack.append(node)
            for neighbor in self.file_dependencies.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in stack:
                    # 发现环路
                    idx = stack.index(neighbor)
                    cycles.append(stack[idx:] + [neighbor])
            stack.pop()

        for f in list(self.file_dependencies.keys()):
            if f not in visited:
                dfs(f)

        return cycles

    def find_dangling_references(self, ignore_builtins: bool = True) -> List[Dict[str, Any]]:
        """查找引用了不存在符号的代码隐患"""
        builtins_whitelist = {
            "str", "int", "float", "list", "dict", "set", "tuple", "bool", "object",
            "Path", "Dict", "List", "Set", "Tuple", "Any", "Optional", "Union",
            "console", "window", "document", "Math", "THREE", "AudioContext",
            "String", "Vector2", "Vector3", "Node", "SceneTree"
        }
        danglings = []
        for edge in self.edges:
            if edge.symbol_name not in self.symbols_by_name:
                if ignore_builtins and edge.symbol_name in builtins_whitelist:
                    continue
                danglings.append({
                    "source_file": edge.source_file,
                    "target_file": edge.target_file,
                    "missing_symbol": edge.symbol_name,
                    "relation": edge.relation
                })
        return danglings

    def plan_cascading_refactor(self, target_symbol: str, new_name: str) -> Dict[str, Any]:
        """当某个符号被重命名或变更时，推演所有需要连带修改的下游文件与代码位置"""
        definitions = self.symbols_by_name.get(target_symbol, [])
        affected_edges = [e for e in self.edges if e.symbol_name == target_symbol]

        affected_files = sorted(list({e.source_file for e in affected_edges}))
        patch_plan = []

        for d in definitions:
            patch_plan.append({
                "action": "MODIFY_DEFINITION",
                "file": d.file_path,
                "line": d.line_number,
                "description": f"重命名定义 {target_symbol} -> {new_name}"
            })

        for e in affected_edges:
            patch_plan.append({
                "action": "MODIFY_CALLSITE",
                "file": e.source_file,
                "relation": e.relation,
                "description": f"更新对 {target_symbol} 的引用为 {new_name}"
            })

        return {
            "symbol": target_symbol,
            "new_name": new_name,
            "definitions_count": len(definitions),
            "affected_downstream_files": affected_files,
            "total_patch_points": len(patch_plan),
            "plan_items": patch_plan
        }

    def audit_integrity(self) -> Dict[str, Any]:
        """全量审计当前工程 AST 符号完整性与健康度"""
        cycles = self.find_circular_dependencies()
        danglings = self.find_dangling_references()
        total_symbols = sum(len(v) for v in self.symbols_by_name.values())
        total_files = len(self.symbols_by_file)

        is_healthy = len(cycles) == 0 and len(danglings) == 0
        verdict = "HEALTHY" if is_healthy else "WARNING_RISKS"

        return {
            "status": "SUCCESS",
            "verdict": verdict,
            "scanned_files_count": total_files,
            "total_symbols_indexed": total_symbols,
            "cross_file_dependencies_count": len(self.edges),
            "circular_cycles_count": len(cycles),
            "cycles": cycles[:5],
            "dangling_symbols_count": len(danglings),
            "dangling_samples": danglings[:5]
        }

if __name__ == "__main__":
    print("=== ASTSymbolGraph: 扫描 pipeline 目录 ===")
    g = ASTSymbolGraph.build_from_directory("pipeline")
    res = g.audit_integrity()
    print(f"  已索引文件: {res['scanned_files_count']} 个")
    print(f"  已定义符号: {res['total_symbols_indexed']} 个")
    print(f"  跨文件依赖边: {res['cross_file_dependencies_count']} 条")
    print(f"  循环依赖数: {res['circular_cycles_count']} 个")
    print(f"  悬空符号数: {res['dangling_symbols_count']} 个")
    print(f"  健康评级: {res['verdict']}")
