"""Tests for agari.py - win detection"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.rules.agari import (
    is_agari, is_standard_agari, is_chiitoi_agari, is_kokushi_agari,
    decompose_standard, get_waiting_tiles, get_agari_type,
)


def make_34(tiles_str):
    """Helper: create 34 array from string like '1112345678999m'."""
    arr = [0] * 34
    numbers = []
    for ch in tiles_str:
        if ch.isdigit():
            numbers.append(int(ch))
        elif ch == 'm':
            for n in numbers:
                arr[n - 1] += 1
            numbers = []
        elif ch == 'p':
            for n in numbers:
                arr[9 + n - 1] += 1
            numbers = []
        elif ch == 's':
            for n in numbers:
                arr[18 + n - 1] += 1
            numbers = []
    # Handle honor tiles: E=東,S=南,W=西,N=北,H=白,G=發,R=中
    for ch in tiles_str:
        if ch == 'E':
            arr[27] += 1
        elif ch == 'S':
            arr[28] += 1
        elif ch == 'W':
            arr[29] += 1
        elif ch == 'N':
            arr[30] += 1
        elif ch == 'H':
            arr[31] += 1
        elif ch == 'G':
            arr[32] += 1
        elif ch == 'R':
            arr[33] += 1
    return arr


class TestStandardAgari:
    def test_simple_win(self):
        # 123m 456p 789s 11p = 11 tiles (valid with 1 meld called: 3 mentsu + pair)
        arr = make_34("123m456p789s11p")
        assert is_standard_agari(arr)  # 11 tiles = 3 mentsu + 1 head (1 meld called)
        # 123m 456p 789s 111p = 12 tiles (total%3=0, invalid for standard form)
        arr = make_34("123m456p789s111p")
        assert is_standard_agari(arr) is False  # 12 tiles, total%3 != 2
        # Proper 14 tile hand: 123m 456p 789s 東東東 南南
        arr = make_34("123m456p789s")
        arr[27] = 3  # 東東東
        arr[28] = 2  # 南南
        assert is_standard_agari(arr)

    def test_all_triplets(self):
        # 111m 222p 333s 444p 東東
        arr = make_34("111m222p333s444p")
        arr[27] = 2
        assert is_standard_agari(arr)

    def test_not_agari(self):
        arr = make_34("1234m456p789s")
        arr[27] = 2
        assert not is_standard_agari(arr)


class TestChiitoiAgari:
    def test_seven_pairs(self):
        arr = make_34("1199m1199p1199s")
        arr[27] = 2  # 東東
        assert is_chiitoi_agari(arr)

    def test_not_seven_pairs(self):
        arr = make_34("1199m1199p11s")
        arr[27] = 2
        assert not is_chiitoi_agari(arr)  # Only 6 pairs + extra

    def test_four_of_kind_not_chiitoi(self):
        # 1111m is not 2 pairs for chiitoi
        arr = [0] * 34
        arr[0] = 4  # 1111m
        arr[9] = 2  # 11p
        arr[10] = 2  # 22p
        arr[11] = 2  # 33p
        arr[12] = 2  # 44p
        assert not is_chiitoi_agari(arr)  # 4-of-kind doesn't count as 2 pairs


class TestKokushiAgari:
    def test_kokushi(self):
        # 1m9m1p9p1s9s東南西北白發中 + one pair
        arr = [0] * 34
        for idx in [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33]:
            arr[idx] = 1
        arr[0] = 2  # Pair of 1m
        assert is_kokushi_agari(arr)

    def test_not_kokushi_missing(self):
        arr = [0] * 34
        for idx in [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32]:  # Missing 中
            arr[idx] = 1
        arr[0] = 2
        assert not is_kokushi_agari(arr)


class TestDecomposition:
    def test_multiple_decompositions(self):
        # 111222333m 東東 - can be decomposed multiple ways
        arr = make_34("111222333m")
        arr[27] = 2
        decomps = decompose_standard(arr)
        assert len(decomps) >= 1

    def test_single_decomposition(self):
        # 123m 456p 789s 白白白 東東
        arr = make_34("123m456p789s")
        arr[31] = 3  # 白白白
        arr[27] = 2  # 東東
        decomps = decompose_standard(arr)
        assert len(decomps) >= 1


class TestWaitingTiles:
    def test_tenpai(self):
        # 123m 456p 789s 東  - waiting on 東
        arr = make_34("123m456p789s")
        arr[27] = 1
        waits = get_waiting_tiles(arr)
        assert 27 in waits  # Waiting on 東

    def test_ryanmen_wait(self):
        # 12m 456p 789s 東東東 白白 - waiting on 3m (edge)
        arr = make_34("12m456p789s")
        arr[27] = 3  # 東東東
        arr[31] = 2  # 白白
        waits = get_waiting_tiles(arr)
        assert 2 in waits  # 3m

    def test_chiitoi_wait(self):
        # 6 pairs + 1 tile = waiting for 7th pair (13 tiles total)
        arr = make_34("1199m1199p1199s")
        arr[27] = 1  # Single 東
        waits = get_waiting_tiles(arr)
        assert 27 in waits  # Waiting on 東 for pair


class TestAgariType:
    def test_standard(self):
        arr = make_34("123m456p789s")
        arr[27] = 3
        arr[28] = 2
        assert get_agari_type(arr) == 'standard'

    def test_kokushi_type(self):
        arr = [0] * 34
        for idx in [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33]:
            arr[idx] = 1
        arr[0] = 2
        assert get_agari_type(arr) == 'kokushi'
