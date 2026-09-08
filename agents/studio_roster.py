#!/usr/bin/env python3
"""
studio_roster.py: 49 个游戏工作室专家智能体实例花名册
自动从 registry 加载并实例化全部 6 大部门 75 位专家。
"""
import sys
from pathlib import Path
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.base_agent import BaseStudioAgent
from core.registry import STUDIO_DEPARTMENTS, get_all_agents

class StudioRoster:
    def __init__(self):
        self.agents_map: Dict[str, BaseStudioAgent] = {}
        self._load_agents()

    def _load_agents(self):
        for dept_id, dept in STUDIO_DEPARTMENTS.items():
            for a in dept["agents"]:
                agent = BaseStudioAgent(
                    agent_id=a["id"],
                    name=a["name"],
                    dept_id=dept_id,
                    role_desc=a["role"]
                )
                self.agents_map[a["id"]] = agent

    def get_agent(self, agent_id: str) -> BaseStudioAgent:
        return self.agents_map.get(agent_id)

    def list_by_department(self, dept_id: str) -> List[BaseStudioAgent]:
        return [a for a in self.agents_map.values() if a.dept_id == dept_id]

    def all_agents(self) -> List[BaseStudioAgent]:
        return list(self.agents_map.values())

studio_roster = StudioRoster()
