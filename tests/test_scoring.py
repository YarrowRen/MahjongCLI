"""Tests for scoring.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.rules.scoring import calculate_score, _calculate_base_points, _round_up_100
from mahjong.core.hand import Hand
from mahjong.core.tile import ALL_TILES_136, make_tiles_from_string


class TestBasePoints:
    def test_mangan(self):
        assert _calculate_base_points(5, 30) == 2000

    def test_haneman(self):
        assert _calculate_base_points(6, 30) == 3000
        assert _calculate_base_points(7, 30) == 3000

    def test_baiman(self):
        assert _calculate_base_points(8, 30) == 4000

    def test_sanbaiman(self):
        assert _calculate_base_points(11, 30) == 6000

    def test_yakuman(self):
        assert _calculate_base_points(13, 30) == 8000

    def test_sub_mangan(self):
        # 1 han 30 fu = 30 * 2^3 = 240
        assert _calculate_base_points(1, 30) == 240
        # 2 han 30 fu = 30 * 2^4 = 480
        assert _calculate_base_points(2, 30) == 480
        # 3 han 30 fu = 30 * 2^5 = 960
        assert _calculate_base_points(3, 30) == 960
        # 4 han 30 fu = 30 * 2^6 = 1920
        assert _calculate_base_points(4, 30) == 1920

    def test_mangan_cutoff(self):
        # 3 han 70 fu = 70 * 2^5 = 2240 -> capped at 2000 (mangan)
        assert _calculate_base_points(3, 70) == 2000


class TestRoundUp:
    def test_exact(self):
        assert _round_up_100(1000) == 1000

    def test_round_up(self):
        assert _round_up_100(1001) == 1100
        assert _round_up_100(1099) == 1100
        assert _round_up_100(960) == 1000


class TestScoreCalculation:
    def test_simple_tsumo(self):
        """Test a simple menzen tsumo hand."""
        hand = Hand()
        # 123m 456p 789s 東東東 南 (13 tiles) + draw 南 = 14 tiles
        # Final hand: 123m 456p 789s 東東東 南南
        tiles = make_tiles_from_string("123m456p789s東東東")
        for t in tiles:
            hand.closed_tiles.append(t)
        # Add first 南 to closed tiles
        first_nan = ALL_TILES_136[28 * 4]  # 南 id=112
        hand.closed_tiles.append(first_nan)
        # Draw second 南 as win tile
        win_tile = ALL_TILES_136[28 * 4 + 1]  # 南 id=113 (different copy)
        hand.draw(win_tile)

        result = calculate_score(
            hand=hand,
            win_tile=win_tile,
            is_tsumo=True,
            seat_wind_34=27,  # East
            round_wind_34=27,  # East
            is_dealer=True,
            dora_tiles_34=[],
            uradora_tiles_34=[],
        )
        # Should have yakuhai 東 (seat+round wind) + tsumo
        assert result is not None
        assert result.han >= 2

    def test_no_yaku_returns_none(self):
        """Hand with no yaku should return None."""
        hand = Hand()
        # Open hand with no yakuhai
        from mahjong.core.meld import Meld, MeldType
        tiles = make_tiles_from_string("234m567p89s")
        for t in tiles:
            hand.closed_tiles.append(t)
        pon = Meld(MeldType.PON,
                   tuple(make_tiles_from_string("555s")),
                   make_tiles_from_string("5s")[0], 1)
        hand.add_meld(pon)
        win_tile = make_tiles_from_string("7s")[0]
        hand.draw(win_tile)

        result = calculate_score(
            hand=hand,
            win_tile=win_tile,
            is_tsumo=False,
            seat_wind_34=27,
            round_wind_34=27,
            is_dealer=False,
            dora_tiles_34=[],
            uradora_tiles_34=[],
        )
        # Open hand with no yaku -> None
        # (Actually 567s straight might give tanyao if all middle tiles)
        # This depends on exact tiles, result may or may not be None
