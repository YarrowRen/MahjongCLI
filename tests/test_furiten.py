"""Tests for furiten.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.rules.furiten import (
    is_discard_furiten, is_temporary_furiten, is_riichi_furiten,
    get_hand_waiting_tiles,
)
from mahjong.core.hand import Hand
from mahjong.core.tile import ALL_TILES_136, make_tiles_from_string


class TestDiscardFuriten:
    def test_furiten_discard_in_pool(self):
        """If a waiting tile is in discard pool, it's furiten."""
        hand = Hand()
        # Tenpai: 123m 456p 789s 東 - waiting on 東
        tiles = make_tiles_from_string("123m456p789s東")
        for t in tiles:
            hand.closed_tiles.append(t)
        # Discard 東 earlier
        east = make_tiles_from_string("東")[0]
        hand.discard_pool.append(east)
        hand.discard_is_tsumogiri.append(False)
        hand.discard_called.append(False)

        assert is_discard_furiten(hand)

    def test_not_furiten(self):
        """If no waiting tiles in discard pool, not furiten."""
        hand = Hand()
        tiles = make_tiles_from_string("123m456p789s東")
        for t in tiles:
            hand.closed_tiles.append(t)
        # Discard something else
        west = make_tiles_from_string("西")[0]
        hand.discard_pool.append(west)
        hand.discard_is_tsumogiri.append(False)
        hand.discard_called.append(False)

        assert not is_discard_furiten(hand)


class TestTemporaryFuriten:
    def test_temp_furiten(self):
        waits = [27]  # Waiting on 東
        missed = {27}  # 東 was discarded and not claimed
        assert is_temporary_furiten(waits, missed)

    def test_no_temp_furiten(self):
        waits = [27]
        missed = {28}  # Different tile missed
        assert not is_temporary_furiten(waits, missed)


class TestRiichiFuriten:
    def test_riichi_furiten(self):
        waits = [27]
        missed = {27}
        assert is_riichi_furiten(waits, missed)

    def test_no_riichi_furiten(self):
        waits = [27]
        missed = set()
        assert not is_riichi_furiten(waits, missed)


class TestGetWaitingTiles:
    def test_tenpai_hand(self):
        hand = Hand()
        tiles = make_tiles_from_string("123m456p789s東")
        for t in tiles:
            hand.closed_tiles.append(t)
        waits = get_hand_waiting_tiles(hand)
        assert 27 in waits  # Waiting on 東
