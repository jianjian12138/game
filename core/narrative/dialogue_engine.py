"""
Dialogue Engine — 对话引擎
============================
驱动NPC对话：分支选项、变量替换、条件显示、对话历史记录。

YAML 格式::

    id: innkeeper_intro
    nodes:
      - id: start
        speaker: 店主
        text: "欢迎，{player_name}。你来这里有什么事吗？"
        choices:
          - text: "我想住宿"
            next: rest_option
          - text: "有什么消息吗？"
            next: news_option
            condition: quest_active(main_quest)
          - text: "没什么，再见"
            next: end

      - id: rest_option
        speaker: 店主
        text: "住一晚需要 10 金币。"
        choices:
          - text: "好的，付钱"
            next: rest_confirm
            condition: gold_above(10)
          - text: "太贵了"
            next: end

      - id: rest_confirm
        speaker: 店主
        text: "晚安，好好休息！"
        effect:
          - type: spend_gold
            amount: 10
          - type: restore_hp
            amount: full
        next: end

      - id: end
        speaker: ""
        text: ""
        end: true
"""

from __future__ import annotations
import yaml
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DialogueLine:
    """单行对话数据。"""
    node_id: str
    speaker: str
    text: str
    choices: list[dict] = field(default_factory=list)
    effects: list[dict] = field(default_factory=list)
    next_node: Optional[str] = None
    is_end: bool = False


class DialogueEngine:
    """
    对话引擎：状态机驱动的对话流程。

    用法::
        engine = DialogueEngine.from_yaml("dialogues/innkeeper.yaml")
        engine.start(context={"player_name": "勇者"})

        while not engine.is_finished():
            line = engine.current_line()
            display(line.speaker, line.text, line.choices)

            if line.choices:
                choice_idx = get_player_input()
                engine.choose(choice_idx)
            else:
                engine.advance()
    """

    def __init__(self, nodes: dict[str, DialogueLine]):
        self._nodes = nodes
        self._current_id: Optional[str] = None
        self._context: dict = {}
        self._history: list[dict] = []

    # ------------------------------------------------------------------
    # 工厂方法
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str) -> "DialogueEngine":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "DialogueEngine":
        nodes = {}
        for node_def in data.get("nodes", []):
            nid = node_def["id"]
            nodes[nid] = DialogueLine(
                node_id=nid,
                speaker=node_def.get("speaker", ""),
                text=node_def.get("text", ""),
                choices=node_def.get("choices", []),
                effects=node_def.get("effect", []),
                next_node=node_def.get("next"),
                is_end=node_def.get("end", False),
            )
        return cls(nodes)

    # ------------------------------------------------------------------
    # 控制 API
    # ------------------------------------------------------------------

    def start(self, start_node: str = "start", context: dict = None):
        """开始对话。"""
        self._current_id = start_node
        self._context = dict(context or {})
        self._history.clear()

    def current_line(self) -> Optional[DialogueLine]:
        """返回当前对话行（文本已替换变量）。"""
        if self._current_id is None:
            return None
        node = self._nodes.get(self._current_id)
        if node is None:
            return None
        # 变量替换
        text = self._substitute(node.text)
        # 过滤条件不满足的选项
        choices = [c for c in node.choices if self._check_choice_condition(c)]
        return DialogueLine(
            node_id=node.node_id,
            speaker=node.speaker,
            text=text,
            choices=choices,
            effects=node.effects,
            next_node=node.next_node,
            is_end=node.is_end,
        )

    def advance(self) -> list[dict]:
        """推进到下一个节点（无选项时调用）。返回效果列表。"""
        node = self._nodes.get(self._current_id)
        if node is None:
            return []

        self._record_history(node)
        effects = list(node.effects)

        if node.is_end:
            self._current_id = None
        elif node.next_node:
            self._current_id = node.next_node
        else:
            self._current_id = None

        return effects

    def choose(self, choice_index: int) -> list[dict]:
        """选择选项（有选项时调用）。返回效果列表。"""
        node = self._nodes.get(self._current_id)
        if node is None:
            return []

        valid_choices = [c for c in node.choices if self._check_choice_condition(c)]
        if choice_index < 0 or choice_index >= len(valid_choices):
            return []

        choice = valid_choices[choice_index]
        self._record_history(node, choice_text=choice.get("text", ""))
        effects = list(node.effects) + list(choice.get("effect", []))
        self._current_id = choice.get("next")
        return effects

    def is_finished(self) -> bool:
        return self._current_id is None

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _substitute(self, text: str) -> str:
        """将 {variable_name} 替换为 context 中的值。"""
        def replace(match):
            key = match.group(1)
            return str(self._context.get(key, f"{{{key}}}"))
        return re.sub(r"\{(\w+)\}", replace, text)

    def _check_choice_condition(self, choice: dict) -> bool:
        """检查选项的显示条件。"""
        cond = choice.get("condition")
        if not cond:
            return True
        # gold_above(N)
        if cond.startswith("gold_above("):
            n = int(cond[len("gold_above("):-1])
            return self._context.get("gold", 0) >= n
        # quest_active(ID)
        if cond.startswith("quest_active("):
            qid = cond[len("quest_active("):-1]
            return qid in self._context.get("active_quests", [])
        return True

    def _record_history(self, node: DialogueLine, choice_text: str = ""):
        self._history.append({
            "node_id": node.node_id,
            "speaker": node.speaker,
            "text": node.text,
            "choice": choice_text,
        })
