"""Shanten (向聴数) calculation.

Shanten = minimum number of tiles needed to reach tenpai (waiting to win).
-1 means already a complete hand (agari).
0 means tenpai (one tile away).
"""

from typing import List


def shanten(tiles_34: List[int]) -> int:
    """Calculate minimum shanten number across all hand forms."""
    return min(
        shanten_standard(tiles_34),
        shanten_chiitoi(tiles_34),
        shanten_kokushi(tiles_34),
    )


def shanten_standard(tiles_34: List[int]) -> int:
    """Shanten for standard form (4 mentsu + 1 jantai).

    Formula: shanten = (4 - mentsu) * 2 - 1 - partial
    where partial = taatsu (partial sequences) + pairs as head candidate.
    """
    total = sum(tiles_34)
    # Number of mentsu we need from closed tiles
    # With N melds already called, we need (4-N) mentsu + 1 head from closed
    # total closed tiles = 3*(4-N)+2 when complete, meaning N = (14-total)//3
    # But total could be 14,11,8,5,2 for 0,1,2,3,4 melds
    if total > 14 or total < 2:
        return 8  # Invalid

    num_melds_called = (14 - total) // 3
    mentsu_needed = 4 - num_melds_called

    best = 8  # Worst case

    # Try each tile as potential head
    for head in range(34):
        if tiles_34[head] >= 2:
            tiles_34[head] -= 2
            mentsu, partial = _count_mentsu_and_partial(tiles_34, mentsu_needed)
            s = (mentsu_needed - mentsu) * 2 - 1 - partial
            best = min(best, s)
            tiles_34[head] += 2

    # Also try without designating a head yet
    mentsu, partial = _count_mentsu_and_partial(tiles_34, mentsu_needed)
    s = (mentsu_needed - mentsu) * 2 - partial
    best = min(best, s)

    return max(best, -1)


def _count_mentsu_and_partial(tiles_34: List[int], max_mentsu: int) -> tuple:
    """Count mentsu and partial groups using backtracking.

    Returns (mentsu_count, partial_count) that minimizes shanten.
    """
    best = [0, 0]  # [mentsu, partial]
    tiles = list(tiles_34)
    _backtrack(tiles, 0, 0, 0, max_mentsu, best)
    return best[0], best[1]


def _backtrack(tiles: List[int], idx: int, mentsu: int, partial: int,
               max_mentsu: int, best: List[int]):
    """Backtrack to find optimal mentsu + partial decomposition."""
    # Pruning: can't do better than current best
    # shanten = (max_mentsu - mentsu) * 2 - 1 - partial  (with head)
    # We want to minimize this, so maximize mentsu*2 + partial
    current_score = mentsu * 2 + partial
    best_score = best[0] * 2 + best[1]

    # Upper bound: remaining could contribute at most remaining_tiles//3 mentsu
    # + remaining pairs/sequences as partial
    if idx >= 34:
        if current_score > best_score:
            best[0] = mentsu
            best[1] = partial
        return

    # Skip if this tile count is 0
    if tiles[idx] == 0:
        _backtrack(tiles, idx + 1, mentsu, partial, max_mentsu, best)
        return

    # Cap: mentsu + partial <= max_mentsu (4 or fewer groups needed)
    can_add_mentsu = mentsu < max_mentsu
    can_add_partial = (mentsu + partial) < max_mentsu

    found_group = False

    # Try koutsu (triplet)
    if tiles[idx] >= 3 and can_add_mentsu:
        found_group = True
        tiles[idx] -= 3
        _backtrack(tiles, idx, mentsu + 1, partial, max_mentsu, best)
        tiles[idx] += 3

    # Try shuntsu (sequence) for number tiles
    if idx < 27 and idx % 9 <= 6 and can_add_mentsu:
        if tiles[idx] >= 1 and tiles[idx + 1] >= 1 and tiles[idx + 2] >= 1:
            found_group = True
            tiles[idx] -= 1
            tiles[idx + 1] -= 1
            tiles[idx + 2] -= 1
            _backtrack(tiles, idx, mentsu + 1, partial, max_mentsu, best)
            tiles[idx] += 1
            tiles[idx + 1] += 1
            tiles[idx + 2] += 1

    # Try partial groups (taatsu)
    # Pair
    if tiles[idx] >= 2 and can_add_partial:
        tiles[idx] -= 2
        _backtrack(tiles, idx, mentsu, partial + 1, max_mentsu, best)
        tiles[idx] += 2

    # Adjacent pair (e.g., 12, 23) for number tiles
    if idx < 27 and idx % 9 <= 7 and can_add_partial:
        if tiles[idx] >= 1 and tiles[idx + 1] >= 1:
            tiles[idx] -= 1
            tiles[idx + 1] -= 1
            _backtrack(tiles, idx, mentsu, partial + 1, max_mentsu, best)
            tiles[idx] += 1
            tiles[idx + 1] += 1

    # Gap pair (e.g., 13, 24) for number tiles
    if idx < 27 and idx % 9 <= 6 and can_add_partial:
        if tiles[idx] >= 1 and tiles[idx + 2] >= 1:
            tiles[idx] -= 1
            tiles[idx + 2] -= 1
            _backtrack(tiles, idx, mentsu, partial + 1, max_mentsu, best)
            tiles[idx] += 1
            tiles[idx + 2] += 1

    # Skip this tile entirely
    _backtrack(tiles, idx + 1, mentsu, partial, max_mentsu, best)


def shanten_chiitoi(tiles_34: List[int]) -> int:
    """Shanten for seven pairs (七対子).

    Formula: 6 - (number of pairs).
    Only valid when total=13 or 14 (no melds).
    """
    total = sum(tiles_34)
    if total not in (13, 14):
        return 99  # Not applicable with melds

    pairs = sum(1 for c in tiles_34 if c >= 2)
    # Count unique types that contribute
    kinds = sum(1 for c in tiles_34 if c >= 1)

    s = 6 - pairs
    # If we don't have 7 different types, we need extra tiles
    if kinds < 7:
        s += 7 - kinds
    return s


def shanten_kokushi(tiles_34: List[int]) -> int:
    """Shanten for thirteen orphans (国士無双).

    Formula: 13 - (number of yaochu types) - (1 if any yaochu pair).
    Only valid when total=13 or 14 (no melds).
    """
    total = sum(tiles_34)
    if total not in (13, 14):
        return 99

    yaochu = [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33]
    types = sum(1 for idx in yaochu if tiles_34[idx] >= 1)
    has_pair = any(tiles_34[idx] >= 2 for idx in yaochu)

    return 13 - types - (1 if has_pair else 0)
