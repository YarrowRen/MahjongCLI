"""Sanma (三人麻雀) specific rules.

Key differences from 4-player:
- 108 tiles (remove 2m-8m)
- No chi (吃)
- North wind can be declared as kita (北抜き) for bonus
- Tsumo payments split between 2 players
- 1m dora indicator -> 9m is dora (skip 2-8m)
"""

from typing import List

from mahjong.core.tile import Tile


def is_sanma_tile(tile: Tile) -> bool:
    """Check if a tile is valid in sanma (not 2m-8m)."""
    # 2m-8m have index34 1-7
    return not (1 <= tile.index34 <= 7)


def filter_sanma_tiles(tiles: List[Tile]) -> List[Tile]:
    """Remove 2m-8m tiles from a list."""
    return [t for t in tiles if is_sanma_tile(t)]


def can_declare_kita(tile: Tile) -> bool:
    """Check if a tile can be declared as kita (north wind = index34 30)."""
    return tile.index34 == 30  # 北


def is_chi_allowed_sanma() -> bool:
    """Chi is not allowed in sanma."""
    return False
