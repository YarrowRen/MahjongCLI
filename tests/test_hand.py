"""Tests for hand.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.core.tile import ALL_TILES_136, Tile
from mahjong.core.hand import Hand
from mahjong.core.meld import Meld, MeldType


class TestHand:
    def test_draw_and_discard(self):
        hand = Hand()
        t1 = ALL_TILES_136[0]  # 1m
        t2 = ALL_TILES_136[4]  # 2m

        hand.draw(t1)
        assert len(hand.closed_tiles) == 1
        assert hand.draw_tile == t1

        hand.draw(t2)
        assert len(hand.closed_tiles) == 2

        hand.discard(t1)
        assert len(hand.closed_tiles) == 1
        assert len(hand.discard_pool) == 1
        assert hand.discard_pool[0] == t1

    def test_sort(self):
        hand = Hand()
        hand.draw(ALL_TILES_136[36])  # 1p
        hand.draw(ALL_TILES_136[0])   # 1m
        hand.draw(ALL_TILES_136[72])  # 1s

        hand.sort_closed()
        assert hand.closed_tiles[0].index34 == 0   # 1m first
        assert hand.closed_tiles[1].index34 == 9   # 1p second
        assert hand.closed_tiles[2].index34 == 18  # 1s third

    def test_menzen(self):
        hand = Hand()
        assert hand.is_menzen

        # Add open meld
        meld = Meld(MeldType.PON,
                     (ALL_TILES_136[0], ALL_TILES_136[1], ALL_TILES_136[2]),
                     ALL_TILES_136[2], 1)
        hand.add_meld(meld)
        assert not hand.is_menzen

    def test_menzen_with_ankan(self):
        hand = Hand()
        meld = Meld(MeldType.ANKAN,
                     (ALL_TILES_136[0], ALL_TILES_136[1],
                      ALL_TILES_136[2], ALL_TILES_136[3]))
        hand.add_meld(meld)
        assert hand.is_menzen  # Ankan doesn't break menzen

    def test_to_34_array(self):
        hand = Hand()
        hand.draw(ALL_TILES_136[0])   # 1m
        hand.draw(ALL_TILES_136[1])   # 1m
        hand.draw(ALL_TILES_136[36])  # 1p

        arr = hand.to_34_array()
        assert arr[0] == 2   # Two 1m
        assert arr[9] == 1   # One 1p
        assert sum(arr) == 3

    def test_clone(self):
        hand = Hand()
        hand.draw(ALL_TILES_136[0])
        hand.draw(ALL_TILES_136[4])
        hand.is_riichi = True

        clone = hand.clone()
        assert len(clone.closed_tiles) == 2
        assert clone.is_riichi
        # Modify original shouldn't affect clone
        hand.closed_tiles.pop()
        assert len(clone.closed_tiles) == 2

    def test_discard_tracking(self):
        hand = Hand()
        t1 = ALL_TILES_136[0]
        t2 = ALL_TILES_136[4]
        hand.draw(t1)
        hand.draw(t2)

        hand.discard(t2, is_tsumogiri=True)
        assert hand.discard_is_tsumogiri[0] is True
        assert hand.discard_called[0] is False
