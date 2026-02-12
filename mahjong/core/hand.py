"""Hand management - closed tiles, melds, discard pool."""

from typing import List, Optional

from .tile import Tile, tiles_to_34_array
from .meld import Meld


class Hand:
    """Manages a player's hand state during a round.

    Attributes:
        closed_tiles: Tiles in hand (not melded)
        melds: Open/closed melds
        discard_pool: Tiles discarded (in order)
        draw_tile: The most recently drawn tile (for display separation)
        is_riichi: Whether riichi has been declared
        is_double_riichi: Whether double riichi
        is_ippatsu: Whether ippatsu is still active (one-shot)
        riichi_discard_index: Index in discard_pool where riichi was declared
    """

    def __init__(self):
        self.closed_tiles: List[Tile] = []
        self.melds: List[Meld] = []
        self.discard_pool: List[Tile] = []
        self.discard_is_tsumogiri: List[bool] = []  # Whether each discard was tsumogiri
        self.discard_called: List[bool] = []  # Whether each discard was called by someone
        self.draw_tile: Optional[Tile] = None
        self.is_riichi: bool = False
        self.is_double_riichi: bool = False
        self.is_ippatsu: bool = False
        self.riichi_discard_index: int = -1

    def draw(self, tile: Tile):
        """Draw a tile from the wall."""
        self.closed_tiles.append(tile)
        self.draw_tile = tile

    def discard(self, tile: Tile, is_tsumogiri: bool = False):
        """Discard a tile from hand."""
        self.closed_tiles.remove(tile)
        self.discard_pool.append(tile)
        self.discard_is_tsumogiri.append(is_tsumogiri)
        self.discard_called.append(False)
        self.draw_tile = None

    def add_meld(self, meld: Meld):
        """Add a meld to the hand."""
        self.melds.append(meld)

    def sort_closed(self):
        """Sort closed tiles by 34 index then tile id."""
        self.closed_tiles.sort()

    def to_34_array(self) -> List[int]:
        """Convert closed tiles to 34-length count array."""
        return tiles_to_34_array(self.closed_tiles)

    @property
    def is_menzen(self) -> bool:
        """Whether hand is fully closed (門前)."""
        return all(not m.is_open for m in self.melds)

    @property
    def num_melds(self) -> int:
        return len(self.melds)

    @property
    def total_tiles(self) -> int:
        """Total tiles (closed + melded)."""
        meld_tile_count = sum(len(m.tiles) for m in self.melds)
        return len(self.closed_tiles) + meld_tile_count

    def clone(self) -> 'Hand':
        """Create a deep copy for simulation."""
        h = Hand()
        h.closed_tiles = list(self.closed_tiles)
        h.melds = list(self.melds)
        h.discard_pool = list(self.discard_pool)
        h.discard_is_tsumogiri = list(self.discard_is_tsumogiri)
        h.discard_called = list(self.discard_called)
        h.draw_tile = self.draw_tile
        h.is_riichi = self.is_riichi
        h.is_double_riichi = self.is_double_riichi
        h.is_ippatsu = self.is_ippatsu
        h.riichi_discard_index = self.riichi_discard_index
        return h
