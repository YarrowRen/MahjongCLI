"""Decode Tenhou N(m) meld bit encoding into structured meld data.

Tenhou encodes melds as a 16-bit integer. The bit layout differs
by meld type (chi / pon / kan / kakan).

Reference: https://tenhou.net/img/tehai.js
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class TenhouMeldType(Enum):
    CHI = "chi"
    PON = "pon"
    ANKAN = "ankan"
    DAIMINKAN = "daiminkan"
    KAKAN = "kakan"  # shouminkan
    KITA = "kita"    # sanma north declaration (北抜き)


@dataclass
class DecodedMeld:
    meld_type: TenhouMeldType
    tiles_136: List[int]       # All tile IDs (136-encoding) in the meld
    called_tile_136: int       # The tile that was called (-1 for ankan)
    from_who_relative: int     # 0=self, 1=shimocha, 2=toimen, 3=kamicha


def decode_meld(m: int, is_sanma: bool = False) -> DecodedMeld:
    """Decode a Tenhou meld value into structured data."""
    from_who = m & 0x3

    if m & 0x4:
        return _decode_chi(m, from_who)
    elif m & 0x8:
        return _decode_pon(m, from_who)
    elif m & 0x10:
        return _decode_kakan(m, from_who)
    else:
        if from_who != 0:
            return _decode_daiminkan(m, from_who)
        else:
            result = _decode_ankan(m)
            # In sanma, ankan of north (tile_34==30) is kita (北抜き)
            if is_sanma and result.tiles_136[0] // 4 == 30:
                t = m >> 8
                r = t % 4
                kita_tile = 30 * 4 + r  # specific north tile ID
                return DecodedMeld(
                    meld_type=TenhouMeldType.KITA,
                    tiles_136=[kita_tile],
                    called_tile_136=-1,
                    from_who_relative=0,
                )
            return result


def _decode_chi(m: int, from_who: int) -> DecodedMeld:
    """Decode chi (吃) meld."""
    t0_offset = (m >> 3) & 0x3
    t1_offset = (m >> 5) & 0x3
    t2_offset = (m >> 7) & 0x3
    base_and_called = m >> 10
    called_idx = base_and_called % 3
    base = base_and_called // 3

    suit = base // 7
    num = base % 7
    base_34 = suit * 9 + num

    tile0 = base_34 * 4 + t0_offset
    tile1 = (base_34 + 1) * 4 + t1_offset
    tile2 = (base_34 + 2) * 4 + t2_offset

    tiles = [tile0, tile1, tile2]
    called_tile = tiles[called_idx]

    return DecodedMeld(
        meld_type=TenhouMeldType.CHI,
        tiles_136=tiles,
        called_tile_136=called_tile,
        from_who_relative=from_who,
    )


def _decode_pon(m: int, from_who: int) -> DecodedMeld:
    """Decode pon (碰) meld."""
    unused = (m >> 5) & 0x3
    t = m >> 9
    r = t % 3
    tile_34 = t // 3

    all_four = [tile_34 * 4 + i for i in range(4)]
    used_tiles = [t for i, t in enumerate(all_four) if i != unused]
    called_tile = used_tiles[r]

    return DecodedMeld(
        meld_type=TenhouMeldType.PON,
        tiles_136=used_tiles,
        called_tile_136=called_tile,
        from_who_relative=from_who,
    )


def _decode_kakan(m: int, from_who: int) -> DecodedMeld:
    """Decode kakan (加杠/shouminkan) meld."""
    unused = (m >> 5) & 0x3
    t = m >> 9
    r = t % 3
    tile_34 = t // 3

    all_four = [tile_34 * 4 + i for i in range(4)]
    # For kakan, 'unused' position is the added tile
    added_tile = all_four[unused]
    pon_tiles = [t for i, t in enumerate(all_four) if i != unused]
    called_tile = pon_tiles[r]

    return DecodedMeld(
        meld_type=TenhouMeldType.KAKAN,
        tiles_136=all_four,
        called_tile_136=called_tile,
        from_who_relative=from_who,
        # added_tile can be derived as all_four[unused]
    )


def _decode_daiminkan(m: int, from_who: int) -> DecodedMeld:
    """Decode daiminkan (大明杠) meld."""
    t = m >> 8
    r = t % 4
    tile_34 = t // 4

    tiles = [tile_34 * 4 + i for i in range(4)]
    called_tile = tiles[r]

    return DecodedMeld(
        meld_type=TenhouMeldType.DAIMINKAN,
        tiles_136=tiles,
        called_tile_136=called_tile,
        from_who_relative=from_who,
    )


def _decode_ankan(m: int) -> DecodedMeld:
    """Decode ankan (暗杠) meld."""
    t = m >> 8
    tile_34 = t // 4

    tiles = [tile_34 * 4 + i for i in range(4)]

    return DecodedMeld(
        meld_type=TenhouMeldType.ANKAN,
        tiles_136=tiles,
        called_tile_136=-1,
        from_who_relative=0,
    )
