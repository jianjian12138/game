"""
UGC Level Editor Engine
Entity placement, spatial validation (spawn points, win conditions), and level serialization.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class LevelEntity:
    entity_id: str
    entity_type: str  # "SPAWN", "EXIT", "ENEMY", "PLATFORM", "COIN"
    x: float
    y: float
    properties: Dict[str, Any] = field(default_factory=dict)


class LevelEditor:
    """Core logic for player-facing 2D level creation and authoring."""

    def __init__(self, width: float = 800.0, height: float = 600.0):
        self.width = width
        self.height = height
        self.entities: Dict[str, LevelEntity] = {}
        self._seq = 0

    def add_entity(self, entity_type: str, x: float, y: float, props: Optional[Dict[str, Any]] = None) -> LevelEntity:
        self._seq += 1
        eid = f"ent_{self._seq}"
        ent = LevelEntity(entity_id=eid, entity_type=entity_type, x=x, y=y, properties=props or {})
        self.entities[eid] = ent
        return ent

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id in self.entities:
            del self.entities[entity_id]
            return True
        return False

    def validate_level(self) -> Dict[str, Any]:
        """Validates minimum playability criteria: must have 1 spawn point and at least 1 goal/exit."""
        has_spawn = any(e.entity_type == "SPAWN" for e in self.entities.values())
        has_exit = any(e.entity_type == "EXIT" for e in self.entities.values())

        errors = []
        if not has_spawn:
            errors.append("MISSING_PLAYER_SPAWN")
        if not has_exit:
            errors.append("MISSING_LEVEL_EXIT")

        is_valid = len(errors) == 0
        return {
            "valid": is_valid,
            "errors": errors,
            "total_entities": len(self.entities)
        }

    def serialize(self) -> Dict[str, Any]:
        return {
            "bounds": {"width": self.width, "height": self.height},
            "entities": [
                {"id": e.entity_id, "type": e.entity_type, "x": e.x, "y": e.y, "props": e.properties}
                for e in self.entities.values()
            ]
        }
