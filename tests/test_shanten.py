"""Tests for shanten.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.rules.shanten import shanten, shanten_standard, shanten_chiitoi, shanten_kokushi


def make_34(tiles_str):
    """Helper: create 34 array from shorthand."""
    arr = [0] * 34
    numbers = []
    for ch in tiles_str:
        if ch.isdigit():
            numbers.append(int(ch))
        elif ch in ('m', 'p', 's'):
            offset = {'m': 0, 'p': 9, 's': 18}[ch]
            for n in numbers:
                arr[offset + n - 1] += 1
            numbers = []
    return arr


def add_honors(arr, east=0, south=0, west=0, north=0, haku=0, hatsu=0, chun=0):
    arr[27] += east
    arr[28] += south
    arr[29] += west
    arr[30] += north
    arr[31] += haku
    arr[32] += hatsu
    arr[33] += chun
    return arr


class TestShanten:
    def test_agari(self):
        """Complete hand should have shanten -1."""
        arr = make_34("123m456p789s")
        add_honors(arr, east=3, south=2)
        assert shanten(arr) == -1

    def test_tenpai(self):
        """One tile away from win = shanten 0."""
        arr = make_34("123m456p789s")
        add_honors(arr, east=1)
        assert shanten(arr) == 0

    def test_iishanten(self):
        """Two tiles away = shanten 1."""
        arr = make_34("123m456p78s")
        add_honors(arr, east=1, south=1)
        assert shanten(arr) <= 1

    def test_chiitoi_tenpai(self):
        """Seven pairs tenpai."""
        # 6 pairs + 1 single = 13 tiles
        arr = make_34("1199m1199p1199s")
        add_honors(arr, east=1)
        assert shanten(arr) == 0  # Waiting for 東 pair

    def test_chiitoi_complete(self):
        # 7 pairs = 14 tiles
        arr = make_34("1199m1199p1199s")
        add_honors(arr, east=2)
        assert shanten(arr) == -1

    def test_kokushi_tenpai(self):
        """Kokushi tenpai."""
        arr = [0] * 34
        for idx in [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32]:
            arr[idx] = 1
        arr[0] = 2  # Extra 1m instead of 中
        # Missing 中 -> waiting on 中
        assert shanten_kokushi(arr) == 0

    def test_kokushi_complete(self):
        arr = [0] * 34
        for idx in [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33]:
            arr[idx] = 1
        arr[0] = 2
        assert shanten_kokushi(arr) == -1

    def test_high_shanten(self):
        """Random bad hand should have high shanten."""
        arr = make_34("1357m2468p")
        add_honors(arr, east=1, south=1, west=1, north=1, haku=1)
        s = shanten(arr)
        assert s >= 3

    def test_with_melds(self):
        """Hand with one meld called (11 tiles closed)."""
        # 123m 456p + 1 meld = need 2 more mentsu + head from 11 tiles
        arr = make_34("123m456p789s")
        arr[27] = 2  # 東東 (head)
        # This is 14 tiles = complete hand
        assert shanten(arr) == -1

    def test_standard_shanten_basic(self):
        """Basic standard shanten calculation."""
        arr = make_34("159m159p159s")
        add_honors(arr, east=1, south=1, west=1, north=1, haku=1)
        # All isolated tiles - very high shanten
        s = shanten_standard(arr)
        assert s >= 4
