"""Reconstruct wall tile order from XML events.

Instead of re-implementing Tenhou's MT19937 shuffle, we reconstruct
the wall from the information available in the XML:
  - Initial hands (52 tiles)
  - Draw events in order (live wall)
  - Dora indicators + uradora (dead wall positions 0-9)
  - Rinshan draws after kan (dead wall positions 10-13)
"""

from typing import List, Tuple

from mahjong.core.tile import Tile, ALL_TILES_136

from .parser import RoundData, EventType
from .decoder import TenhouMeldType


def build_wall(rd: RoundData) -> Tuple[List[Tile], List[Tile]]:
    """Build live_wall and dead_wall tile lists from round data.

    Returns:
        (live_wall_tiles, dead_wall_tiles) where:
        - live_wall_tiles: tiles in draw order (after initial deal)
        - dead_wall_tiles: 14 tiles laid out as:
            [dora0, ura0, dora1, ura1, dora2, ura2, dora3, ura3, dora4, ura4,
             rinshan3, rinshan2, rinshan1, rinshan0]
          (rinshan drawn in reverse: index 13 first, then 12, 11, 10)
    """
    # Collect all draw tile_ids in order from events
    live_draw_ids: List[int] = []
    rinshan_ids: List[int] = []

    # Track kan/kita events to identify rinshan draws
    expect_rinshan = False

    for event in rd.events:
        if event.event_type == EventType.MELD and event.decoded_meld is not None:
            mt = event.decoded_meld.meld_type
            if mt in (TenhouMeldType.ANKAN, TenhouMeldType.DAIMINKAN,
                      TenhouMeldType.KAKAN, TenhouMeldType.KITA):
                expect_rinshan = True
        elif event.event_type == EventType.DRAW:
            if expect_rinshan:
                rinshan_ids.append(event.tile_id)
                expect_rinshan = False
            else:
                live_draw_ids.append(event.tile_id)

    # Collect dora indicators and uradora from AGARI events
    dora_ids: List[int] = []
    uradora_ids: List[int] = []
    for event in rd.events:
        if event.event_type == EventType.AGARI:
            if event.agari_dora:
                dora_ids = list(event.agari_dora)
            if event.agari_uradora:
                uradora_ids = list(event.agari_uradora)
            break

    # If no AGARI, use the initial dora indicator
    if not dora_ids:
        dora_ids = [rd.dora_indicator]

    # Build dead wall:
    # Positions 0,2,4,6,8 = dora indicators
    # Positions 1,3,5,7,9 = uradora indicators
    # Positions 10,11,12,13 = rinshan tiles (drawn from 13 backwards)

    # All tiles accounted for
    used_tile_ids = set()
    for hand in rd.hands:
        used_tile_ids.update(hand)
    used_tile_ids.update(live_draw_ids)
    used_tile_ids.update(rinshan_ids)
    used_tile_ids.update(dora_ids)
    used_tile_ids.update(uradora_ids)

    # For sanma, exclude 2m-8m tiles (tile_ids 4-31)
    if rd.is_sanma:
        all_tile_ids = set(i for i in range(136) if not (4 <= i < 32))
    else:
        all_tile_ids = set(range(136))
    unknown_ids = sorted(all_tile_ids - used_tile_ids)

    # Build dead wall array (14 slots)
    dead_wall = [None] * 14

    # Place dora indicators at even positions
    for i, d in enumerate(dora_ids):
        if i < 5:
            dead_wall[i * 2] = d

    # Place uradora at odd positions
    for i, u in enumerate(uradora_ids):
        if i < 5:
            dead_wall[i * 2 + 1] = u

    # Place rinshan tiles at positions 13, 12, 11, 10 (draw order)
    for i, r in enumerate(rinshan_ids):
        if i < 4:
            dead_wall[13 - i] = r

    # Fill remaining dead wall slots with unknown tiles
    # Separate unknowns: first fill dead wall, then append rest to live wall
    dead_wall_used = set(x for x in dead_wall if x is not None)
    remaining_unknown = [x for x in unknown_ids if x not in dead_wall_used]

    unknown_iter = iter(remaining_unknown)
    for i in range(14):
        if dead_wall[i] is None:
            dead_wall[i] = next(unknown_iter)

    # Undrawn live wall tiles go after the drawn ones (order doesn't matter)
    undrawn_ids = list(unknown_iter)  # consume the rest
    live_all_ids = live_draw_ids + undrawn_ids

    live_wall_tiles = [ALL_TILES_136[tid] for tid in live_all_ids]
    dead_wall_tiles = [ALL_TILES_136[tid] for tid in dead_wall]

    return live_wall_tiles, dead_wall_tiles
