"""Tests for yaku.py - role detection"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.rules.yaku import (
    HandContext, detect_all_yaku, total_han, has_yaku,
    check_tanyao, check_pinfu, check_toitoi, check_honitsu,
    check_chinitsu, check_chiitoi, check_iipeikou, check_ittsu,
    check_chanta, check_junchan, check_honroutou,
    check_sanshoku_doujun, check_sanankou, check_shousangen,
    check_daisangen, check_tsuuiisou,
    check_suuankou, check_ryuuiisou, check_chuuren,
)
from mahjong.core.meld import Meld, MeldType
from mahjong.core.tile import ALL_TILES_136


def make_context(**kwargs) -> HandContext:
    """Helper to build HandContext with defaults."""
    ctx = HandContext()
    for k, v in kwargs.items():
        setattr(ctx, k, v)
    return ctx


def make_all_34(closed_str, honor_counts=None):
    """Build all_tiles_34 from string."""
    arr = [0] * 34
    numbers = []
    for ch in closed_str:
        if ch.isdigit():
            numbers.append(int(ch))
        elif ch in ('m', 'p', 's'):
            offset = {'m': 0, 'p': 9, 's': 18}[ch]
            for n in numbers:
                arr[offset + n - 1] += 1
            numbers = []
    if honor_counts:
        for idx, count in honor_counts.items():
            arr[idx] = count
    return arr


class TestTanyao:
    def test_valid(self):
        arr = make_all_34("234m567p345s")
        arr[1] = 2  # 22m pair (2 is index 1)
        # Actually 22m = index34=1, which is 2m
        # Fix: 234m means indices 1,2,3 so 234m567p345s + pair of something
        ctx = make_context(all_tiles_34=make_all_34("234m567p345s678m"))
        # Recalculate: 234m678m567p345s = all middle tiles
        arr2 = make_all_34("234m567p345s")
        arr2[5] = 2  # 66m pair
        ctx = make_context(all_tiles_34=arr2)
        result = check_tanyao(ctx)
        assert result is not None
        assert result[0] == "断幺九"

    def test_invalid_with_terminal(self):
        arr = make_all_34("123m456p789s")
        arr[27] = 2
        ctx = make_context(all_tiles_34=arr)
        assert check_tanyao(ctx) is None


class TestPinfu:
    def test_valid(self):
        ctx = make_context(
            is_menzen=True,
            head_34=5,  # 6m (not yakuhai)
            mentsu=[('shuntsu', 0), ('shuntsu', 3), ('shuntsu', 9), ('shuntsu', 18)],
            melds=[],
            seat_wind_34=27,
            round_wind_34=27,
            win_tile_34=0,  # 1m, completing 123m shuntsu with ryanmen (23m wait)
            is_chiitoi=False,
            is_kokushi=False,
        )
        result = check_pinfu(ctx)
        assert result is not None
        assert result[0] == "平和"

    def test_invalid_with_koutsu(self):
        ctx = make_context(
            is_menzen=True,
            head_34=5,
            mentsu=[('koutsu', 0), ('shuntsu', 3), ('shuntsu', 9), ('shuntsu', 18)],
            melds=[],
            seat_wind_34=27,
            round_wind_34=27,
            win_tile_34=11,
        )
        assert check_pinfu(ctx) is None

    def test_invalid_yakuhai_head(self):
        ctx = make_context(
            is_menzen=True,
            head_34=33,  # 中 is yakuhai
            mentsu=[('shuntsu', 0), ('shuntsu', 3), ('shuntsu', 9), ('shuntsu', 18)],
            melds=[],
            seat_wind_34=27,
            round_wind_34=27,
            win_tile_34=2,
        )
        assert check_pinfu(ctx) is None


class TestToitoi:
    def test_valid(self):
        ctx = make_context(
            mentsu=[('koutsu', 0), ('koutsu', 9)],
            melds=[
                Meld(MeldType.PON, (ALL_TILES_136[72], ALL_TILES_136[73], ALL_TILES_136[74]),
                     ALL_TILES_136[74], 1),
                Meld(MeldType.PON, (ALL_TILES_136[108], ALL_TILES_136[109], ALL_TILES_136[110]),
                     ALL_TILES_136[110], 2),
            ],
            head_34=5,
            is_chiitoi=False,
        )
        result = check_toitoi(ctx)
        assert result is not None
        assert result[0] == "対対和"


class TestHonitsu:
    def test_valid(self):
        arr = [0] * 34
        for i in range(9):  # All man
            arr[i] = 1
        arr[0] = 3  # 111m
        arr[27] = 3  # 東東東
        arr[28] = 2  # 南南
        ctx = make_context(all_tiles_34=arr, is_menzen=True)
        result = check_honitsu(ctx)
        assert result is not None
        assert "混一色" in result[0]

    def test_invalid_two_suits(self):
        arr = make_all_34("123m123p")
        arr[27] = 2
        ctx = make_context(all_tiles_34=arr, is_menzen=True)
        assert check_honitsu(ctx) is None


class TestChinitsu:
    def test_valid(self):
        arr = [0] * 34
        arr[0] = 3  # 111m
        arr[1] = 1
        arr[2] = 1
        arr[3] = 1  # 234m
        arr[4] = 1
        arr[5] = 1
        arr[6] = 1  # 567m
        arr[7] = 1
        arr[8] = 1  # 89m...wait need 14
        arr[6] = 2  # Make it work: 111m234m567m789m + 77m pair
        arr[7] = 1
        arr[8] = 1
        # 111m 234m 567m 789m 77m = 3+3+3+3+2 = 14
        # Rebuild
        arr = [0] * 34
        arr[0] = 3
        arr[1] = 1; arr[2] = 1; arr[3] = 1
        arr[4] = 1; arr[5] = 1; arr[6] = 2
        arr[7] = 1; arr[8] = 1
        ctx = make_context(all_tiles_34=arr, is_menzen=True)
        result = check_chinitsu(ctx)
        assert result is not None
        assert "清一色" in result[0]


class TestChiitoi:
    def test_valid(self):
        ctx = make_context(is_chiitoi=True)
        result = check_chiitoi(ctx)
        assert result is not None
        assert result[1] == 2  # 2 han


class TestIipeikou:
    def test_valid(self):
        ctx = make_context(
            is_menzen=True,
            mentsu=[('shuntsu', 0), ('shuntsu', 0), ('shuntsu', 9), ('shuntsu', 18)],
        )
        result = check_iipeikou(ctx)
        assert result is not None

    def test_invalid_not_menzen(self):
        ctx = make_context(
            is_menzen=False,
            mentsu=[('shuntsu', 0), ('shuntsu', 0), ('shuntsu', 9)],
        )
        assert check_iipeikou(ctx) is None


class TestIttsu:
    def test_valid(self):
        ctx = make_context(
            mentsu=[('shuntsu', 0), ('shuntsu', 3), ('shuntsu', 6), ('koutsu', 27)],
            melds=[],
            is_menzen=True,
        )
        result = check_ittsu(ctx)
        assert result is not None
        assert result[1] == 2  # 2 han menzen

    def test_valid_open(self):
        ctx = make_context(
            mentsu=[('shuntsu', 0), ('shuntsu', 3)],
            melds=[
                Meld(MeldType.CHI, (ALL_TILES_136[24], ALL_TILES_136[28], ALL_TILES_136[32]),
                     ALL_TILES_136[24], 1)
            ],
            is_menzen=False,
        )
        result = check_ittsu(ctx)
        assert result is not None
        assert result[1] == 1  # 1 han open


class TestSanshoku:
    def test_valid(self):
        ctx = make_context(
            mentsu=[('shuntsu', 0), ('shuntsu', 9), ('shuntsu', 18), ('koutsu', 27)],
            melds=[],
            is_menzen=True,
        )
        result = check_sanshoku_doujun(ctx)
        assert result is not None


class TestSanankou:
    def test_valid_tsumo(self):
        ctx = make_context(
            mentsu=[('koutsu', 0), ('koutsu', 9), ('koutsu', 18), ('shuntsu', 3)],
            melds=[],
            is_tsumo=True,
            win_tile_34=0,
            is_chiitoi=False,
        )
        result = check_sanankou(ctx)
        assert result is not None

    def test_ron_reduces_count(self):
        """Ron on shanpon reduces closed koutsu count by 1."""
        ctx = make_context(
            mentsu=[('koutsu', 0), ('koutsu', 9), ('koutsu', 18), ('shuntsu', 3)],
            melds=[],
            is_tsumo=False,
            win_tile_34=0,
            is_chiitoi=False,
        )
        result = check_sanankou(ctx)
        # One koutsu formed by ron is "open", so only 2 concealed
        assert result is None


class TestYakuman:
    def test_daisangen(self):
        ctx = make_context(
            mentsu=[('koutsu', 31), ('koutsu', 32), ('koutsu', 33), ('shuntsu', 0)],
            melds=[],
            head_34=27,
        )
        result = check_daisangen(ctx)
        assert result is not None
        assert result[1] == 13

    def test_tsuuiisou(self):
        arr = [0] * 34
        arr[27] = 3; arr[28] = 3; arr[29] = 3; arr[30] = 3; arr[31] = 2
        ctx = make_context(all_tiles_34=arr)
        result = check_tsuuiisou(ctx)
        assert result is not None
        assert result[1] == 13

    def test_suuankou(self):
        ctx = make_context(
            mentsu=[('koutsu', 0), ('koutsu', 9), ('koutsu', 18), ('koutsu', 27)],
            melds=[],
            is_tsumo=True,
            win_tile_34=5,  # Not on any koutsu
            head_34=5,
            is_chiitoi=False,
            is_kokushi=False,
        )
        result = check_suuankou(ctx)
        assert result is not None
        assert result[1] == 13

    def test_ryuuiisou(self):
        arr = [0] * 34
        arr[19] = 3  # 222s
        arr[20] = 3  # 333s
        arr[21] = 3  # 444s
        arr[23] = 3  # 666s
        arr[32] = 2  # 發發
        ctx = make_context(all_tiles_34=arr)
        result = check_ryuuiisou(ctx)
        assert result is not None

    def test_chuuren(self):
        arr = [0] * 34
        arr[0] = 3; arr[1] = 1; arr[2] = 1; arr[3] = 1
        arr[4] = 1; arr[5] = 1; arr[6] = 1; arr[7] = 1; arr[8] = 3
        # Extra one tile to make 14 total: add another 5m
        arr[4] = 2
        ctx = make_context(all_tiles_34=arr, is_menzen=True)
        result = check_chuuren(ctx)
        assert result is not None


class TestDetectAllYaku:
    def test_riichi_tsumo(self):
        arr = make_all_34("123m456p789s")
        arr[27] = 3; arr[28] = 2
        ctx = make_context(
            all_tiles_34=arr,
            head_34=28,
            mentsu=[('shuntsu', 0), ('shuntsu', 12), ('shuntsu', 24), ('koutsu', 27)],
            melds=[],
            is_menzen=True,
            is_riichi=True,
            is_tsumo=True,
            win_tile_34=0,
            seat_wind_34=27,
            round_wind_34=27,
        )
        yaku = detect_all_yaku(ctx)
        names = [name for name, _ in yaku]
        assert "立直" in names
        assert "門前清自摸和" in names
