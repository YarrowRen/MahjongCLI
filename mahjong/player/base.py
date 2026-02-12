"""Abstract player interface and GameView (read-only information barrier)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from mahjong.core.tile import Tile
from mahjong.core.meld import Meld
from mahjong.core.hand import Hand
from mahjong.core.player_state import Wind
from mahjong.engine.action import Action, AvailableActions


@dataclass
class OpponentView:
    """Read-only view of an opponent (no hidden tiles)."""
    seat: int
    name: str
    score: int
    seat_wind: Wind
    is_dealer: bool
    is_riichi: bool
    melds: List[Meld]
    discard_pool: List[Tile]
    discard_called: List[bool]
    num_closed_tiles: int
    kita_count: int = 0


@dataclass
class GameView:
    """Read-only view of visible game state.

    This is the information barrier - players can only see what's
    legally visible. No access to other players' closed tiles or wall.
    """
    # Own hand (full access)
    my_hand: Hand
    my_seat: int
    my_wind: Wind
    my_score: int
    is_dealer: bool

    # Opponents (limited view)
    opponents: List[OpponentView] = field(default_factory=list)

    # Table state
    round_wind: Wind = Wind.EAST
    honba: int = 0
    riichi_sticks: int = 0
    remaining_tiles: int = 70
    dora_indicators: List[Tile] = field(default_factory=list)
    round_label: str = ""

    # Turn info
    last_discard: Optional[Tile] = None
    last_discard_player: Optional[int] = None


class Player(ABC):
    """Abstract base class for all players."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def choose_action(self, game_view: GameView,
                      available: AvailableActions) -> Action:
        """Choose an action from available options.

        This is called in two contexts:
        1. After drawing: can tsumo/riichi/kan/discard
        2. After opponent's discard: can ron/pon/chi/skip
        """
        ...

    @abstractmethod
    def choose_discard(self, game_view: GameView,
                       available_discards: List[Tile]) -> Tile:
        """Choose a tile to discard from available options."""
        ...

    @abstractmethod
    def choose_riichi_discard(self, game_view: GameView,
                              riichi_candidates: List[Tile]) -> Tile:
        """Choose which tile to discard when declaring riichi."""
        ...


def build_game_view(
    player_idx: int,
    players: List,  # List[PlayerState]
    round_wind: Wind,
    honba: int,
    riichi_sticks: int,
    remaining_tiles: int,
    dora_indicators: List[Tile],
    round_label: str = "",
    last_discard: Optional[Tile] = None,
    last_discard_player: Optional[int] = None,
) -> GameView:
    """Build a GameView for the given player."""
    me = players[player_idx]

    opponents = []
    for p in players:
        if p.seat == player_idx:
            continue
        opponents.append(OpponentView(
            seat=p.seat,
            name=p.name,
            score=p.score,
            seat_wind=p.seat_wind,
            is_dealer=p.is_dealer,
            is_riichi=p.hand.is_riichi,
            melds=list(p.hand.melds),
            discard_pool=list(p.hand.discard_pool),
            discard_called=list(p.hand.discard_called),
            num_closed_tiles=len(p.hand.closed_tiles),
            kita_count=len(p.kita_tiles),
        ))

    return GameView(
        my_hand=me.hand,
        my_seat=player_idx,
        my_wind=me.seat_wind,
        my_score=me.score,
        is_dealer=me.is_dealer,
        opponents=opponents,
        round_wind=round_wind,
        honba=honba,
        riichi_sticks=riichi_sticks,
        remaining_tiles=remaining_tiles,
        dora_indicators=dora_indicators,
        round_label=round_label,
        last_discard=last_discard,
        last_discard_player=last_discard_player,
    )
