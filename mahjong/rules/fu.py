"""Fu (符) calculation for scoring."""

from typing import List, Tuple, Optional

from mahjong.core.tile import YAOCHU_INDICES
from mahjong.core.meld import Meld, MeldType


def calculate_fu(
    head_34: int,
    mentsu_list: List[Tuple[str, int]],
    melds: List[Meld],
    win_tile_34: int,
    is_tsumo: bool,
    is_menzen: bool,
    seat_wind_34: int,
    round_wind_34: int,
    is_pinfu: bool = False,
    is_chiitoi: bool = False,
) -> int:
    """Calculate fu (符) for a standard hand.

    Args:
        head_34: 34-index of the pair (jantai)
        mentsu_list: List of (type, index34) for closed mentsu
        melds: Open/closed melds from the hand
        win_tile_34: 34-index of the winning tile
        is_tsumo: Whether win is by tsumo
        is_menzen: Whether hand is fully closed
        seat_wind_34: 34-index of seat wind tile
        round_wind_34: 34-index of round wind tile
        is_pinfu: Whether this is a pinfu hand
        is_chiitoi: Whether this is a chiitoi hand

    Returns:
        Fu value rounded up to nearest 10.
    """
    # Special case: chiitoi is always 25 fu
    if is_chiitoi:
        return 25

    fu = 20  # Base fu (副底)

    # Mentsu fu (from closed mentsu)
    # For ron, a koutsu completed by the winning tile is treated as open (明刻)
    # only if the winning tile is not used in any shuntsu in this decomposition.
    win_in_shuntsu = any(
        m_type == 'shuntsu' and win_tile_34 in (m_idx, m_idx + 1, m_idx + 2)
        for m_type, m_idx in mentsu_list
    )
    win_koutsu_found = False
    for m_type, m_idx in mentsu_list:
        if m_type == 'koutsu':
            is_yaochu = m_idx in YAOCHU_INDICES
            if (not is_tsumo and not win_koutsu_found and m_idx == win_tile_34
                    and not win_in_shuntsu):
                # Ron completing this koutsu: treat as open
                base = 4 if is_yaochu else 2
                win_koutsu_found = True
            else:
                # Closed koutsu
                base = 8 if is_yaochu else 4
            fu += base

    # Meld fu (from open/closed melds)
    for meld in melds:
        idx = meld.tile_index34
        is_yaochu = idx in YAOCHU_INDICES

        if meld.meld_type == MeldType.ANKAN:
            fu += 32 if is_yaochu else 16
        elif meld.meld_type in (MeldType.DAIMINKAN, MeldType.SHOUMINKAN):
            fu += 16 if is_yaochu else 8
        elif meld.meld_type == MeldType.PON:
            fu += 4 if is_yaochu else 2
        # CHI: 0 fu

    # Head fu (pair of yakuhai)
    if head_34 == seat_wind_34:
        fu += 2
    if head_34 == round_wind_34:
        fu += 2
    # Dragon pair
    if head_34 in (31, 32, 33):  # 白, 發, 中
        fu += 2

    # Wait type fu
    wait_fu = _calculate_wait_fu(head_34, mentsu_list, win_tile_34)
    fu += wait_fu

    # Win method fu
    if is_tsumo:
        if not is_pinfu:  # Pinfu tsumo is special: 20 fu
            fu += 2
    else:
        if is_menzen:
            fu += 10  # Menzen ron bonus

    # Pinfu tsumo special case: exactly 20 fu
    if is_pinfu and is_tsumo:
        return 20

    # Pinfu ron special case: exactly 30 fu (20 base + 10 menzen ron, no extra fu)
    if is_pinfu and not is_tsumo and is_menzen:
        return 30

    # Open pinfu-like hand: minimum 30 fu
    if fu == 20 and not is_menzen:
        fu = 30

    # Round up to nearest 10
    return _round_up_10(fu)


def _calculate_wait_fu(head_34: int, mentsu_list: List[Tuple[str, int]],
                       win_tile_34: int) -> int:
    """Determine wait type and return fu.

    Kanchan (嵌張, middle wait): 2 fu
    Penchan (辺張, edge wait): 2 fu
    Tanki (単騎, pair wait): 2 fu
    Ryanmen (両面, two-sided): 0 fu
    Shanpon (双碰, dual pair): 0 fu
    """
    # Check if win tile is the head (tanki wait)
    if win_tile_34 == head_34:
        return 2

    # Check each shuntsu that contains the win tile
    for m_type, m_idx in mentsu_list:
        if m_type != 'shuntsu':
            continue
        # Shuntsu covers m_idx, m_idx+1, m_idx+2
        if win_tile_34 not in (m_idx, m_idx + 1, m_idx + 2):
            continue

        # Kanchan: win tile is the middle
        if win_tile_34 == m_idx + 1:
            return 2

        # Penchan: edge wait
        # 123 waiting on 3 (m_idx=0 mod 9, win=m_idx+2)
        if m_idx % 9 == 0 and win_tile_34 == m_idx + 2:
            return 2
        # 789 waiting on 7 (m_idx+2 is 9 of suit, i.e. m_idx%9==6, win=m_idx)
        if m_idx % 9 == 6 and win_tile_34 == m_idx:
            return 2

    # Otherwise: ryanmen or shanpon → 0 fu
    return 0


def _round_up_10(fu: int) -> int:
    """Round up to nearest 10."""
    return ((fu + 9) // 10) * 10
