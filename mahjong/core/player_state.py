"""Player state tracking during a game."""

from enum import IntEnum
from typing import List

from .hand import Hand
from .tile import Tile


class Wind(IntEnum):
    EAST = 0    # 東
    SOUTH = 1   # 南
    WEST = 2    # 西
    NORTH = 3   # 北

    @property
    def kanji(self) -> str:
        return ['東', '南', '西', '北'][self.value]

    @property
    def index34(self) -> int:
        """34 encoding index for this wind tile."""
        return 27 + self.value


class PlayerState:
    """Complete state for one player across a game.

    Attributes:
        seat: Seat index (0-3, fixed)
        name: Display name
        score: Current score in points
        hand: Current hand state (reset each round)
        seat_wind: Current seat wind (changes each round)
        is_dealer: Whether this player is the dealer this round
        kita_tiles: Tiles declared as kita (sanma north tiles)
    """

    def __init__(self, seat: int, name: str, score: int = 25000):
        self.seat = seat
        self.name = name
        self.score = score
        self.hand = Hand()
        self.seat_wind = Wind.EAST
        self.is_dealer = False
        self.kita_tiles: List[Tile] = []

    def reset_for_round(self, seat_wind: Wind, is_dealer: bool):
        """Reset hand state for a new round."""
        self.hand = Hand()
        self.seat_wind = seat_wind
        self.is_dealer = is_dealer
        self.kita_tiles = []

    @property
    def is_riichi(self) -> bool:
        return self.hand.is_riichi

    @property
    def is_menzen(self) -> bool:
        return self.hand.is_menzen

    def __repr__(self):
        return f"PlayerState({self.name}, {self.seat_wind.kanji}, {self.score}点)"
