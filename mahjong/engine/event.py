"""Event system for decoupling engine from UI."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List


class EventType(Enum):
    GAME_START = "game_start"
    GAME_END = "game_end"
    ROUND_START = "round_start"
    ROUND_END = "round_end"
    DRAW = "draw"
    DISCARD = "discard"
    CHI = "chi"
    PON = "pon"
    KAN = "kan"
    KITA = "kita"
    RIICHI_DECLARE = "riichi_declare"
    RIICHI_ACCEPTED = "riichi_accepted"
    TSUMO = "tsumo"
    RON = "ron"
    DORA_REVEAL = "dora_reveal"
    EXHAUSTIVE_DRAW = "exhaustive_draw"
    ABORTIVE_DRAW = "abortive_draw"
    SCORE_CHANGE = "score_change"
    TURN_START = "turn_start"
    IPPATSU_CANCEL = "ippatsu_cancel"


@dataclass
class GameEvent:
    """An event emitted by the game engine."""
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Simple publish/subscribe event bus."""

    def __init__(self):
        self._listeners: Dict[EventType, List[Callable]] = {}

    def subscribe(self, event_type: EventType, callback: Callable):
        """Register a callback for an event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def emit(self, event: GameEvent):
        """Emit an event to all registered listeners."""
        listeners = self._listeners.get(event.event_type, [])
        for callback in listeners:
            callback(event)

    def clear(self):
        """Remove all listeners."""
        self._listeners.clear()
