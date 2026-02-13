"""Wall and dead wall (牌山与王牌) management."""

import random
from typing import List, Optional

from .tile import Tile, ALL_TILES_136, next_tile_index


class Wall:
    """Manages the wall, dead wall, dora indicators.

    Four-player: 136 tiles. Three-player (sanma): 108 tiles (remove 2m-8m).

    Dead wall: 14 tiles
      - Dora indicators: positions 0,2,4,6,8 (up to 5 kan-dora)
      - Ura-dora indicators: positions 1,3,5,7,9
      - Rinshan (replacement) tiles: positions 10,11,12,13
    """

    def __init__(self, is_sanma: bool = False, shuffle: bool = True):
        self.is_sanma = is_sanma
        self._build_wall(shuffle)

    def _build_wall(self, shuffle: bool):
        """Build and shuffle the wall."""
        if self.is_sanma:
            # Remove 2m-8m (indices 1-7 in 34 encoding, tile_ids 4-31)
            self.all_tiles = [Tile(i) for i in range(136)
                              if not (4 <= i < 32)]
        else:
            self.all_tiles = [Tile(i) for i in range(136)]

        if shuffle:
            random.shuffle(self.all_tiles)

        # Dead wall: last 14 tiles
        self.dead_wall = self.all_tiles[-14:]
        self.live_wall = list(self.all_tiles[:-14])

        # Dora state
        self._dora_revealed = 1  # Start with 1 dora indicator revealed
        self._rinshan_drawn = 0  # How many rinshan tiles have been drawn

    @classmethod
    def from_tiles(cls, live_wall_tiles, dead_wall_tiles, is_sanma=False):
        """Build a Wall from pre-determined tile lists (for replay mode)."""
        wall = cls.__new__(cls)
        wall.is_sanma = is_sanma
        wall.all_tiles = list(live_wall_tiles) + list(dead_wall_tiles)
        wall.live_wall = list(live_wall_tiles)
        wall.dead_wall = list(dead_wall_tiles)
        wall._dora_revealed = 1
        wall._rinshan_drawn = 0
        return wall

    @property
    def remaining(self) -> int:
        """Number of drawable tiles remaining in live wall."""
        return len(self.live_wall)

    @property
    def is_empty(self) -> bool:
        return len(self.live_wall) == 0

    def draw(self) -> Optional[Tile]:
        """Draw a tile from the live wall."""
        if self.live_wall:
            return self.live_wall.pop(0)
        return None

    def draw_rinshan(self) -> Optional[Tile]:
        """Draw a replacement tile from the dead wall (for kan)."""
        if self._rinshan_drawn < 4:
            tile = self.dead_wall[13 - self._rinshan_drawn]
            self._rinshan_drawn += 1
            return tile
        return None

    def reveal_new_dora(self):
        """Reveal a new dora indicator (after kan)."""
        if self._dora_revealed < 5:
            self._dora_revealed += 1

    @property
    def dora_indicators(self) -> List[Tile]:
        """Currently revealed dora indicator tiles."""
        indicators = []
        for i in range(self._dora_revealed):
            indicators.append(self.dead_wall[i * 2])
        return indicators

    @property
    def uradora_indicators(self) -> List[Tile]:
        """Ura-dora indicator tiles (revealed only for riichi winners)."""
        indicators = []
        for i in range(self._dora_revealed):
            indicators.append(self.dead_wall[i * 2 + 1])
        return indicators

    def get_dora_tiles_34(self) -> List[int]:
        """Get 34 indices of actual dora tiles from indicators."""
        dora_indices = []
        for indicator in self.dora_indicators:
            dora_indices.append(next_tile_index(indicator.index34, self.is_sanma))
        return dora_indices

    def get_uradora_tiles_34(self) -> List[int]:
        """Get 34 indices of actual ura-dora tiles."""
        dora_indices = []
        for indicator in self.uradora_indicators:
            dora_indices.append(next_tile_index(indicator.index34, self.is_sanma))
        return dora_indices

    @property
    def total_tiles(self) -> int:
        """Total tiles in this wall configuration."""
        return 108 if self.is_sanma else 136
