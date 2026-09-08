"""
Chart Note DSL — 节奏谱面方言
================================
描述节奏游戏的谱面，支持 Tap/Hold/Flick/Slide 四种Note类型。

YAML 示例::

    id: sample_chart
    title: 示例谱面
    artist: Unknown
    bpm: 138
    offset: 0.05          # 音频偏移校正（秒）
    difficulty: 8
    notes:
      - beat: 1.0         # 在第 1 拍出现
        lane: 2           # 轨道（0–3 代表4轨）
        type: tap
      - beat: 1.5
        lane: 1
        type: tap
      - beat: 2.0
        lane: 3
        type: hold
        duration: 1.0     # Hold 持续 1 拍
      - beat: 3.0
        lane: 0
        type: flick
        direction: up
      - beat: 4.0
        lane: 1
        type: slide
        path: [{lane: 1, beat: 4.0}, {lane: 3, beat: 4.5}]
"""


class ChartNoteDSL:
    """节奏谱面方言：BPM→时间戳转换，Note规范化。"""

    VALID_NOTE_TYPES = {"tap", "hold", "flick", "slide"}
    VALID_FLICK_DIRS = {"up", "down", "left", "right"}

    def preprocess(self, raw: dict) -> dict:
        raw.setdefault("bpm", 120.0)
        raw.setdefault("offset", 0.0)
        raw.setdefault("difficulty", 5)
        raw.setdefault("lanes", 4)          # 默认4轨

        bpm = raw["bpm"]
        offset = raw["offset"]
        spb = 60.0 / bpm                    # 每拍秒数

        notes = raw.get("notes", []) or []
        converted = []
        for note in notes:
            note = dict(note)               # 不修改原始数据
            note.setdefault("type", "tap")
            note.setdefault("lane", 0)
            # beat → timestamp（秒）
            beat = note.get("beat", 0)
            note["timestamp"] = round(beat * spb + offset, 6)
            if note["type"] == "hold":
                dur_beats = note.get("duration", 1.0)
                note["end_timestamp"] = round(note["timestamp"] + dur_beats * spb, 6)
            converted.append(note)

        # 按时间戳排序
        converted.sort(key=lambda n: n["timestamp"])
        raw["notes"] = converted
        return raw

    def validate(self, ast: dict) -> list[str]:
        errors = []
        bpm = ast.get("bpm", 120)
        if not isinstance(bpm, (int, float)) or bpm <= 0:
            errors.append(f"bpm 必须是正数: {bpm}")
        lanes = ast.get("lanes", 4)
        for i, note in enumerate(ast.get("notes", [])):
            ntype = note.get("type", "tap")
            if ntype not in self.VALID_NOTE_TYPES:
                errors.append(f"notes[{i}].type 无效: '{ntype}'")
            if note.get("lane", 0) >= lanes:
                errors.append(f"notes[{i}].lane={note['lane']} 超出轨道范围 0–{lanes-1}")
            if ntype == "flick":
                d = note.get("direction", "up")
                if d not in self.VALID_FLICK_DIRS:
                    errors.append(f"notes[{i}].direction 无效: '{d}'")
        return errors
