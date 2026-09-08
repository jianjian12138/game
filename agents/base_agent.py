#!/usr/bin/env python3
"""
base_agent.py: 游戏工作室智能体基类 (Base Studio Agent)
"""
from typing import Dict, List, Any

class BaseStudioAgent:
    def __init__(self, agent_id: str, name: str, dept_id: str, role_desc: str, skills: List[str] = None):
        self.agent_id = agent_id
        self.name = name
        self.dept_id = dept_id
        self.role_desc = role_desc
        self.skills = skills or []

    def perform_action(self, action_name: str, payload: dict) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "action": action_name,
            "status": "success",
            "output": payload
        }
