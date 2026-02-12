"""Furiten (振聴) detection.

Three types:
1. Discard furiten: A waiting tile is in your own discard pile
2. Temporary furiten: Someone discarded a winning tile this turn but you didn't ron
3. Riichi furiten: After riichi, someone discards a winning tile but you don't ron
"""

from typing import List, Set

from mahjong.core.tile import Tile, tiles_to_34_array
from mahjong.core.hand import Hand
from mahjong.rules.agari import get_waiting_tiles


def is_discard_furiten(hand: Hand) -> bool:
    """Check if hand is in discard furiten.

    If any of the hand's winning tiles appear in the player's discard pile,
    they cannot ron (but can still tsumo).
    """
    closed_34 = hand.to_34_array()
    total = sum(closed_34)
    # Need exactly 13 tiles (tenpai)
    if total % 3 != 1:
        return False

    waits = get_waiting_tiles(closed_34)
    if not waits:
        return False

    discard_34 = set(t.index34 for t in hand.discard_pool)
    return any(w in discard_34 for w in waits)


def is_temporary_furiten(waiting_tiles_34: List[int],
                         missed_tiles_34: Set[int]) -> bool:
    """Check temporary (same-turn) furiten.

    If a winning tile was discarded by another player this turn
    and you didn't claim it, you're in temporary furiten until your next draw.
    """
    return any(w in missed_tiles_34 for w in waiting_tiles_34)


def is_riichi_furiten(waiting_tiles_34: List[int],
                      missed_since_riichi_34: Set[int]) -> bool:
    """Check riichi furiten.

    After declaring riichi, if any player discards a winning tile
    and you don't claim it, you can never ron for the rest of the round.
    """
    return any(w in missed_since_riichi_34 for w in waiting_tiles_34)


def get_hand_waiting_tiles(hand: Hand) -> List[int]:
    """Get 34 indices of all tiles the hand is waiting on."""
    closed_34 = hand.to_34_array()
    return get_waiting_tiles(closed_34)
