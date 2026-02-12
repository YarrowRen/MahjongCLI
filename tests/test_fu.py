"""Tests for fu.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.rules.fu import calculate_fu
from mahjong.core.meld import Meld, MeldType
from mahjong.core.tile import ALL_TILES_136


class TestFu:
    def test_pinfu_tsumo(self):
        """Pinfu tsumo = 20 fu."""
        fu = calculate_fu(
            head_34=5,  # 6m (non-yakuhai)
            mentsu_list=[('shuntsu', 0), ('shuntsu', 3),
                         ('shuntsu', 9), ('shuntsu', 18)],
            melds=[],
            win_tile_34=0,  # 1m, ryanmen (23m wait)
            is_tsumo=True,
            is_menzen=True,
            seat_wind_34=27,
            round_wind_34=27,
            is_pinfu=True,
        )
        assert fu == 20

    def test_pinfu_ron(self):
        """Pinfu ron = 30 fu (20 base + 10 menzen ron)."""
        fu = calculate_fu(
            head_34=5,
            mentsu_list=[('shuntsu', 0), ('shuntsu', 3),
                         ('shuntsu', 9), ('shuntsu', 18)],
            melds=[],
            win_tile_34=0,  # 1m, ryanmen (23m wait)
            is_tsumo=False,
            is_menzen=True,
            seat_wind_34=27,
            round_wind_34=27,
            is_pinfu=True,
        )
        assert fu == 30

    def test_chiitoi(self):
        """Chiitoi = 25 fu always."""
        fu = calculate_fu(
            head_34=0,
            mentsu_list=[],
            melds=[],
            win_tile_34=0,
            is_tsumo=True,
            is_menzen=True,
            seat_wind_34=27,
            round_wind_34=27,
            is_chiitoi=True,
        )
        assert fu == 25

    def test_closed_koutsu_terminal(self):
        """Closed koutsu of terminal = 8 fu."""
        fu = calculate_fu(
            head_34=5,
            mentsu_list=[('koutsu', 0), ('shuntsu', 3),
                         ('shuntsu', 9), ('shuntsu', 18)],
            melds=[],
            win_tile_34=5,  # tanki (pair wait)
            is_tsumo=True,
            is_menzen=True,
            seat_wind_34=27,
            round_wind_34=27,
        )
        # 20 base + 8 (closed terminal koutsu) + 2 (tanki) + 2 (tsumo) = 32 -> 40
        assert fu == 40

    def test_open_pon_middle(self):
        """Open pon of middle tile = 2 fu."""
        pon = Meld(MeldType.PON,
                   (ALL_TILES_136[20], ALL_TILES_136[21], ALL_TILES_136[22]),
                   ALL_TILES_136[22], 1)
        fu = calculate_fu(
            head_34=5,
            mentsu_list=[('shuntsu', 0), ('shuntsu', 9), ('shuntsu', 18)],
            melds=[pon],
            win_tile_34=2,
            is_tsumo=False,
            is_menzen=False,
            seat_wind_34=27,
            round_wind_34=27,
        )
        # 20 base + 2 (open middle pon) = 22 -> 30 (minimum for open hand)
        assert fu == 30

    def test_ankan_terminal(self):
        """Ankan of terminal = 32 fu."""
        ankan = Meld(MeldType.ANKAN,
                     (ALL_TILES_136[0], ALL_TILES_136[1],
                      ALL_TILES_136[2], ALL_TILES_136[3]))
        fu = calculate_fu(
            head_34=5,
            mentsu_list=[('shuntsu', 3), ('shuntsu', 9), ('shuntsu', 18)],
            melds=[ankan],
            win_tile_34=5,
            is_tsumo=True,
            is_menzen=True,
            seat_wind_34=27,
            round_wind_34=27,
        )
        # 20 + 32 (ankan terminal) + 2 (tanki) + 2 (tsumo) = 56 -> 60
        assert fu == 60

    def test_yakuhai_head(self):
        """Pair of yakuhai = 2 fu each."""
        fu = calculate_fu(
            head_34=33,  # 中
            mentsu_list=[('shuntsu', 0), ('shuntsu', 3),
                         ('shuntsu', 9), ('shuntsu', 18)],
            melds=[],
            win_tile_34=2,
            is_tsumo=False,
            is_menzen=True,
            seat_wind_34=27,
            round_wind_34=27,
        )
        # 20 + 2 (中 head) + 10 (menzen ron) = 32 -> 40
        assert fu == 40

    def test_double_wind_head(self):
        """Pair of double wind (seat + round) = 4 fu."""
        fu = calculate_fu(
            head_34=27,  # 東 (both seat and round wind)
            mentsu_list=[('shuntsu', 0), ('shuntsu', 3),
                         ('shuntsu', 9), ('shuntsu', 18)],
            melds=[],
            win_tile_34=2,
            is_tsumo=False,
            is_menzen=True,
            seat_wind_34=27,
            round_wind_34=27,
        )
        # 20 + 4 (double wind head) + 10 (menzen ron) = 34 -> 40
        assert fu == 40

    def test_kanchan_wait(self):
        """Kanchan (middle wait) = 2 fu."""
        fu = calculate_fu(
            head_34=5,
            mentsu_list=[('shuntsu', 0), ('shuntsu', 3),
                         ('shuntsu', 9), ('shuntsu', 18)],
            melds=[],
            win_tile_34=1,  # 2m, kanchan in 1-3m
            is_tsumo=True,
            is_menzen=True,
            seat_wind_34=27,
            round_wind_34=27,
        )
        # 20 + 2 (kanchan) + 2 (tsumo) = 24 -> 30
        assert fu == 30
