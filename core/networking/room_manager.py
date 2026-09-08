"""
Multiplayer Room & Matchmaking Manager
Room lifecycle, player seats, ready state checks, and auto-matchmaking queues.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class PlayerSeat:
    player_id: str
    username: str
    seat_index: int
    is_ready: bool = False
    ping_ms: float = 0.0


@dataclass
class Room:
    room_id: str
    name: str
    host_player_id: str
    max_players: int = 4
    seats: Dict[str, PlayerSeat] = field(default_factory=dict)
    is_in_game: bool = False

    def is_full(self) -> bool:
        return len(self.seats) >= self.max_players

    def all_ready(self) -> bool:
        if len(self.seats) < 2:
            return False
        return all(s.is_ready for s in self.seats.values())


class RoomManager:
    """Manages active game rooms and matchmaking pools."""

    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.matchmaking_queue: List[str] = []

    def create_room(self, room_id: str, name: str, host_id: str, host_name: str, max_players: int = 4) -> Room:
        r = Room(room_id=room_id, name=name, host_player_id=host_id, max_players=max_players)
        r.seats[host_id] = PlayerSeat(host_id, host_name, seat_index=0, is_ready=True)
        self.rooms[room_id] = r
        return r

    def join_room(self, room_id: str, player_id: str, username: str) -> Optional[PlayerSeat]:
        r = self.rooms.get(room_id)
        if not r or r.is_full() or r.is_in_game:
            return None
        seat_idx = len(r.seats)
        seat = PlayerSeat(player_id, username, seat_index=seat_idx, is_ready=False)
        r.seats[player_id] = seat
        return seat

    def leave_room(self, room_id: str, player_id: str) -> bool:
        r = self.rooms.get(room_id)
        if not r or player_id not in r.seats:
            return False
        del r.seats[player_id]
        if not r.seats:
            del self.rooms[room_id]
        elif r.host_player_id == player_id:
            # Transfer host to first remaining player
            r.host_player_id = next(iter(r.seats.keys()))
        return True

    def set_ready(self, room_id: str, player_id: str, is_ready: bool) -> bool:
        r = self.rooms.get(room_id)
        if r and player_id in r.seats:
            r.seats[player_id].is_ready = is_ready
            return True
        return False

    def enqueue_matchmaking(self, player_id: str):
        if player_id not in self.matchmaking_queue:
            self.matchmaking_queue.append(player_id)

    def match_pair(self) -> Optional[Tuple[str, str]]:
        if len(self.matchmaking_queue) >= 2:
            p1 = self.matchmaking_queue.pop(0)
            p2 = self.matchmaking_queue.pop(0)
            return p1, p2
        return None
