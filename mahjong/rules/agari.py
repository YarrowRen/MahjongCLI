"""Win (和了) detection - standard form, seven pairs, thirteen orphans.

Returns all possible decompositions for a winning hand.
"""

from typing import List, Tuple, Optional

from mahjong.core.tile import YAOCHU_INDICES


# A decomposition is (head_34, mentsu_list) where mentsu_list is list of (type, index34)
# type: 'shuntsu' (顺子) or 'koutsu' (刻子)
Mentsu = Tuple[str, int]
Decomposition = Tuple[int, List[Mentsu]]


def is_agari(tiles_34: List[int]) -> bool:
    """Check if the 34-array represents a winning hand (any form)."""
    return (is_standard_agari(tiles_34) or
            is_chiitoi_agari(tiles_34) or
            is_kokushi_agari(tiles_34))


def is_standard_agari(tiles_34: List[int]) -> bool:
    """Check standard form (4 mentsu + 1 jantai)."""
    return len(decompose_standard(tiles_34)) > 0


def decompose_standard(tiles_34: List[int]) -> List[Decomposition]:
    """Find all standard decompositions (4 mentsu + 1 head).

    Works on 34-array of closed tiles only (melds already extracted).
    The array should have exactly 14, 11, 8, 5, or 2 tiles total
    depending on number of melds.
    """
    total = sum(tiles_34)
    if total % 3 != 2:
        return []

    num_mentsu_needed = (total - 2) // 3
    results = []

    # Try each possible head (pair)
    for head in range(34):
        if tiles_34[head] < 2:
            continue
        remaining = list(tiles_34)
        remaining[head] -= 2
        mentsu_list: List[Mentsu] = []
        if _extract_mentsu(remaining, 0, num_mentsu_needed, mentsu_list):
            results.append((head, list(mentsu_list)))
            # Continue searching for more decompositions
            # We need a more thorough search
        mentsu_list.clear()

    # Do a thorough search
    return _decompose_all(tiles_34)


def _decompose_all(tiles_34: List[int]) -> List[Decomposition]:
    """Find ALL possible standard decompositions."""
    total = sum(tiles_34)
    if total % 3 != 2:
        return []

    num_mentsu_needed = (total - 2) // 3
    results = []

    for head in range(34):
        if tiles_34[head] < 2:
            continue
        remaining = list(tiles_34)
        remaining[head] -= 2
        found = []
        _find_all_mentsu(remaining, 0, num_mentsu_needed, [], found)
        for mentsu_list in found:
            results.append((head, mentsu_list))

    return results


def _find_all_mentsu(tiles: List[int], start: int, needed: int,
                     current: List[Mentsu], results: List[List[Mentsu]]):
    """Recursively find all possible mentsu decompositions."""
    if needed == 0:
        if all(t == 0 for t in tiles):
            results.append(list(current))
        return

    # Find next non-zero position
    idx = start
    while idx < 34 and tiles[idx] == 0:
        idx += 1

    if idx >= 34:
        return

    # Try koutsu (triplet) first
    if tiles[idx] >= 3:
        tiles[idx] -= 3
        current.append(('koutsu', idx))
        _find_all_mentsu(tiles, idx, needed - 1, current, results)
        current.pop()
        tiles[idx] += 3

    # Try shuntsu (sequence) - only for number tiles (0-26)
    if idx < 27 and idx % 9 <= 6:  # Can form sequence (not 8 or 9 of suit)
        if tiles[idx] >= 1 and tiles[idx + 1] >= 1 and tiles[idx + 2] >= 1:
            tiles[idx] -= 1
            tiles[idx + 1] -= 1
            tiles[idx + 2] -= 1
            current.append(('shuntsu', idx))
            _find_all_mentsu(tiles, idx, needed - 1, current, results)
            current.pop()
            tiles[idx] += 1
            tiles[idx + 1] += 1
            tiles[idx + 2] += 1


def _extract_mentsu(tiles: List[int], start: int, needed: int,
                    result: List[Mentsu]) -> bool:
    """Extract exactly 'needed' mentsu from tiles (greedy, finds one solution)."""
    if needed == 0:
        return all(t == 0 for t in tiles)

    idx = start
    while idx < 34 and tiles[idx] == 0:
        idx += 1

    if idx >= 34:
        return False

    # Try koutsu
    if tiles[idx] >= 3:
        tiles[idx] -= 3
        result.append(('koutsu', idx))
        if _extract_mentsu(tiles, idx, needed - 1, result):
            return True
        result.pop()
        tiles[idx] += 3

    # Try shuntsu
    if idx < 27 and idx % 9 <= 6:
        if tiles[idx + 1] >= 1 and tiles[idx + 2] >= 1:
            tiles[idx] -= 1
            tiles[idx + 1] -= 1
            tiles[idx + 2] -= 1
            result.append(('shuntsu', idx))
            if _extract_mentsu(tiles, idx, needed - 1, result):
                return True
            result.pop()
            tiles[idx] += 1
            tiles[idx + 1] += 1
            tiles[idx + 2] += 1

    return False


def is_chiitoi_agari(tiles_34: List[int]) -> bool:
    """Check seven pairs (七対子) form."""
    if sum(tiles_34) != 14:
        return False
    pairs = sum(1 for c in tiles_34 if c == 2)
    return pairs == 7


def is_kokushi_agari(tiles_34: List[int]) -> bool:
    """Check thirteen orphans (国士無双) form."""
    if sum(tiles_34) != 14:
        return False
    has_pair = False
    for idx in YAOCHU_INDICES:
        if tiles_34[idx] == 0:
            return False
        if tiles_34[idx] == 2:
            has_pair = True
    # Must have exactly 14 tiles all yaochu with one pair
    non_yaochu = sum(tiles_34[i] for i in range(34) if i not in YAOCHU_INDICES)
    return has_pair and non_yaochu == 0


def get_agari_type(tiles_34: List[int]) -> Optional[str]:
    """Determine the agari type: 'standard', 'chiitoi', 'kokushi', or None."""
    if is_kokushi_agari(tiles_34):
        return 'kokushi'
    if is_chiitoi_agari(tiles_34):
        return 'chiitoi'
    if is_standard_agari(tiles_34):
        return 'standard'
    return None


def get_waiting_tiles(tiles_34: List[int]) -> List[int]:
    """Find all tiles (34 indices) that would complete this hand.

    The hand should have 13 tiles (tenpai check) or appropriate for melds.
    """
    total = sum(tiles_34)
    if total % 3 != 1:
        return []

    waits = []
    for i in range(34):
        if tiles_34[i] >= 4:
            continue
        test = list(tiles_34)
        test[i] += 1
        if is_agari(test):
            waits.append(i)
    return waits
