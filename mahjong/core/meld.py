"""Meld (副露) data structures for Chi/Pon/Kan."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .tile import Tile


class MeldType(Enum):
    CHI = "chi"           # 吃
    PON = "pon"           # 碰
    ANKAN = "ankan"       # 暗杠
    DAIMINKAN = "daiminkan"  # 大明杠
    SHOUMINKAN = "shouminkan"  # 加杠 (小明杠)


@dataclass(frozen=True)
class Meld:
    """A frozen meld (副露) data structure.

    Attributes:
        meld_type: Type of meld
        tiles: All tiles in the meld
        called_tile: The tile that was called (None for ankan)
        from_player: Seat index of the player the tile was called from (None for ankan)
    """
    meld_type: MeldType
    tiles: tuple  # tuple of Tile
    called_tile: Optional[Tile] = None
    from_player: Optional[int] = None

    @property
    def is_open(self) -> bool:
        return self.meld_type != MeldType.ANKAN

    @property
    def is_kan(self) -> bool:
        return self.meld_type in (MeldType.ANKAN, MeldType.DAIMINKAN, MeldType.SHOUMINKAN)

    @property
    def tile_index34(self) -> int:
        """The 34 index of the meld's primary tile (for pon/kan, the tile type)."""
        return self.tiles[0].index34

    def contains_red(self) -> bool:
        return any(t.is_red for t in self.tiles)
