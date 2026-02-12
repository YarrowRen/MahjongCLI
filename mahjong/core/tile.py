"""Tile definition with dual encoding (136/34) and red dora support."""

from enum import IntEnum
from typing import List, Optional


class TileSuit(IntEnum):
    MAN = 0   # 万子
    PIN = 1   # 筒子
    SOU = 2   # 索子
    WIND = 3  # 风牌
    DRAGON = 4  # 三元牌


# Red dora tile IDs (in 136 encoding)
RED_FIVE_MAN = 16    # 赤5m - the first 5m (id 16 among 5m: 16,17,18,19)
RED_FIVE_PIN = 52    # 赤5p
RED_FIVE_SOU = 88    # 赤5s
RED_DORA_IDS = {RED_FIVE_MAN, RED_FIVE_PIN, RED_FIVE_SOU}

# Yaochu (terminal + honor) tile indices in 34 encoding
YAOCHU_INDICES = [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33]

# Tile names for 34 encoding
TILE_NAMES_34 = [
    "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
    "東", "南", "西", "北", "白", "發", "中",
]


class Tile:
    """Immutable tile with 136 encoding (unique identity) and 34 encoding (algorithm use)."""
    __slots__ = ('_id', '_index34', '_suit', '_number', '_is_red')

    def __init__(self, tile_id: int):
        if not (0 <= tile_id < 136):
            raise ValueError(f"tile_id must be 0..135, got {tile_id}")
        self._id = tile_id
        self._index34 = tile_id // 4
        # Determine suit and number
        if self._index34 < 9:
            self._suit = TileSuit.MAN
            self._number = self._index34 + 1
        elif self._index34 < 18:
            self._suit = TileSuit.PIN
            self._number = self._index34 - 9 + 1
        elif self._index34 < 27:
            self._suit = TileSuit.SOU
            self._number = self._index34 - 18 + 1
        elif self._index34 < 31:
            self._suit = TileSuit.WIND
            self._number = self._index34 - 27 + 1  # 1=東,2=南,3=西,4=北
        else:
            self._suit = TileSuit.DRAGON
            self._number = self._index34 - 31 + 1  # 1=白,2=發,3=中
        self._is_red = tile_id in RED_DORA_IDS

    @property
    def id(self) -> int:
        return self._id

    @property
    def index34(self) -> int:
        return self._index34

    @property
    def suit(self) -> TileSuit:
        return self._suit

    @property
    def number(self) -> int:
        return self._number

    @property
    def is_red(self) -> bool:
        return self._is_red

    @property
    def is_honor(self) -> bool:
        return self._suit in (TileSuit.WIND, TileSuit.DRAGON)

    @property
    def is_terminal(self) -> bool:
        return not self.is_honor and self._number in (1, 9)

    @property
    def is_yaochu(self) -> bool:
        return self.is_honor or self.is_terminal

    @property
    def is_number_tile(self) -> bool:
        return self._suit in (TileSuit.MAN, TileSuit.PIN, TileSuit.SOU)

    @property
    def name(self) -> str:
        if self._is_red:
            suit_char = {TileSuit.MAN: 'm', TileSuit.PIN: 'p', TileSuit.SOU: 's'}
            return f"0{suit_char[self._suit]}"
        return TILE_NAMES_34[self._index34]

    def __repr__(self):
        return f"Tile({self.name})"

    def __eq__(self, other):
        if isinstance(other, Tile):
            return self._id == other._id
        return NotImplemented

    def __hash__(self):
        return self._id

    def __lt__(self, other):
        if isinstance(other, Tile):
            if self._index34 != other._index34:
                return self._index34 < other._index34
            return self._id < other._id
        return NotImplemented


def tile_id_to_34(tile_id: int) -> int:
    """Convert 136 encoding to 34 encoding."""
    return tile_id // 4


def tile_34_to_name(index34: int) -> str:
    """Get tile name from 34 encoding."""
    return TILE_NAMES_34[index34]


def tiles_to_34_array(tiles: List[Tile]) -> List[int]:
    """Convert list of tiles to 34-length count array."""
    arr = [0] * 34
    for t in tiles:
        arr[t.index34] += 1
    return arr


def tile_34_array_from_ids(tile_ids: List[int]) -> List[int]:
    """Convert list of 136 tile IDs to 34-length count array."""
    arr = [0] * 34
    for tid in tile_ids:
        arr[tid // 4] += 1
    return arr


# Pre-create all 136 tiles
ALL_TILES_136 = [Tile(i) for i in range(136)]


def next_tile_index(index34: int, is_sanma: bool = False) -> int:
    """Get the 'next' tile index for dora indicator calculation.

    For number tiles: wraps 9->1 (sanma man: 1m indicator -> 9m dora, skipping 2-8)
    For wind: 東→南→西→北→東
    For dragon: 白→發→中→白
    """
    if index34 < 9:
        # Man tiles
        if is_sanma:
            # In sanma, 1m->9m, 9m->1m (skip 2-8m)
            if index34 == 0:
                return 8
            elif index34 == 8:
                return 0
            else:
                return (index34 + 1) % 9
        else:
            return (index34 + 1) % 9
    elif index34 < 18:
        # Pin tiles
        return 9 + (index34 - 9 + 1) % 9
    elif index34 < 27:
        # Sou tiles
        return 18 + (index34 - 18 + 1) % 9
    elif index34 < 31:
        # Wind tiles: 27=東,28=南,29=西,30=北
        return 27 + (index34 - 27 + 1) % 4
    else:
        # Dragon tiles: 31=白,32=發,33=中
        return 31 + (index34 - 31 + 1) % 3


def make_tiles_from_string(s: str) -> List[Tile]:
    """Parse a shorthand string like '123m456p789s東南西北' into tiles.

    Uses the first available tile_id for each tile (no red dora by default).
    For red dora, use '0m', '0p', '0s'.
    """
    tiles = []
    numbers = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch.isdigit():
            numbers.append(int(ch))
            i += 1
        elif ch in ('m', 'p', 's'):
            suit_offset = {'m': 0, 'p': 9, 's': 18}[ch]
            for n in numbers:
                if n == 0:
                    # Red dora
                    red_ids = {'m': RED_FIVE_MAN, 'p': RED_FIVE_PIN, 's': RED_FIVE_SOU}
                    tiles.append(ALL_TILES_136[red_ids[ch]])
                else:
                    index34 = suit_offset + n - 1
                    tiles.append(ALL_TILES_136[index34 * 4])
            numbers = []
            i += 1
        elif ch == '東':
            tiles.append(ALL_TILES_136[27 * 4])
            i += 1
        elif ch == '南':
            tiles.append(ALL_TILES_136[28 * 4])
            i += 1
        elif ch == '西':
            tiles.append(ALL_TILES_136[29 * 4])
            i += 1
        elif ch == '北':
            tiles.append(ALL_TILES_136[30 * 4])
            i += 1
        elif ch == '白':
            tiles.append(ALL_TILES_136[31 * 4])
            i += 1
        elif ch == '發':
            tiles.append(ALL_TILES_136[32 * 4])
            i += 1
        elif ch == '中':
            tiles.append(ALL_TILES_136[33 * 4])
            i += 1
        else:
            i += 1
    return tiles
