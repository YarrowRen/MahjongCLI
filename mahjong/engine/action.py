"""Action definitions for the game engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from mahjong.core.tile import Tile
from mahjong.core.meld import Meld


class ActionType(Enum):
    DISCARD = "discard"
    CHI = "chi"
    PON = "pon"
    ANKAN = "ankan"         # Closed kan
    DAIMINKAN = "daiminkan"  # Open kan from discard
    SHOUMINKAN = "shouminkan"  # Added kan (promote pon)
    RIICHI = "riichi"
    TSUMO = "tsumo"
    RON = "ron"
    SKIP = "skip"
    KITA = "kita"           # North tile declaration (sanma)
    KYUUSHU = "kyuushu"     # Nine different terminals/honors redraw


# Priority for resolving conflicting claims
ACTION_PRIORITY = {
    ActionType.RON: 0,      # Highest
    ActionType.DAIMINKAN: 1,
    ActionType.PON: 1,
    ActionType.CHI: 2,
    ActionType.SKIP: 99,
}


@dataclass
class Action:
    """A player action."""
    action_type: ActionType
    player: int  # Seat index
    tile: Optional[Tile] = None  # The tile involved
    meld: Optional[Meld] = None  # Meld formed (for chi/pon/kan)
    riichi_discard: Optional[Tile] = None  # Tile to discard for riichi

    def __repr__(self):
        parts = [f"{self.action_type.value}"]
        if self.tile:
            parts.append(f"tile={self.tile.name}")
        return f"Action({', '.join(parts)}, p{self.player})"


@dataclass
class AvailableActions:
    """Available actions for a player at a decision point."""
    player: int
    can_tsumo: bool = False
    can_riichi: bool = False
    can_ankan: List[List[Tile]] = field(default_factory=list)
    can_shouminkan: List[Tile] = field(default_factory=list)
    can_discard: List[Tile] = field(default_factory=list)
    can_chi: List[Meld] = field(default_factory=list)
    can_pon: List[Meld] = field(default_factory=list)
    can_daiminkan: List[Meld] = field(default_factory=list)
    can_ron: bool = False
    can_kita: bool = False
    can_kyuushu: bool = False
    riichi_candidates: List[Tile] = field(default_factory=list)

    @property
    def has_action(self) -> bool:
        """Whether there's any action available beyond just discarding."""
        return (self.can_tsumo or self.can_riichi or
                len(self.can_ankan) > 0 or len(self.can_shouminkan) > 0 or
                len(self.can_chi) > 0 or len(self.can_pon) > 0 or
                len(self.can_daiminkan) > 0 or self.can_ron or
                self.can_kita or self.can_kyuushu)
