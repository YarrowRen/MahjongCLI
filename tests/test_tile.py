"""Tests for tile.py"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.core.tile import (
    Tile, TileSuit, tiles_to_34_array, tile_id_to_34, tile_34_to_name,
    ALL_TILES_136, YAOCHU_INDICES, RED_FIVE_MAN, RED_FIVE_PIN, RED_FIVE_SOU,
    next_tile_index, make_tiles_from_string,
)


class TestTileBasic:
    def test_tile_count(self):
        assert len(ALL_TILES_136) == 136

    def test_tile_id_range(self):
        for i, t in enumerate(ALL_TILES_136):
            assert t.id == i

    def test_suit_assignment(self):
        # 1m (id 0-3) should be MAN
        assert ALL_TILES_136[0].suit == TileSuit.MAN
        assert ALL_TILES_136[0].number == 1
        # 1p (id 36-39) should be PIN
        assert ALL_TILES_136[36].suit == TileSuit.PIN
        assert ALL_TILES_136[36].number == 1
        # 1s (id 72-75) should be SOU
        assert ALL_TILES_136[72].suit == TileSuit.SOU
        assert ALL_TILES_136[72].number == 1
        # East wind (id 108-111) should be WIND
        assert ALL_TILES_136[108].suit == TileSuit.WIND
        assert ALL_TILES_136[108].number == 1
        # Haku (id 124-127) should be DRAGON
        assert ALL_TILES_136[124].suit == TileSuit.DRAGON

    def test_red_dora(self):
        assert ALL_TILES_136[RED_FIVE_MAN].is_red
        assert ALL_TILES_136[RED_FIVE_PIN].is_red
        assert ALL_TILES_136[RED_FIVE_SOU].is_red
        # Normal 5m (id 17) should not be red
        assert not ALL_TILES_136[17].is_red

    def test_yaochu(self):
        # 1m is yaochu
        assert ALL_TILES_136[0].is_yaochu
        # 9m is yaochu
        assert ALL_TILES_136[32].is_yaochu
        # 5m is not yaochu
        assert not ALL_TILES_136[16].is_yaochu
        # East wind is yaochu
        assert ALL_TILES_136[108].is_yaochu

    def test_terminal(self):
        assert ALL_TILES_136[0].is_terminal  # 1m
        assert ALL_TILES_136[32].is_terminal  # 9m
        assert not ALL_TILES_136[4].is_terminal  # 2m
        assert not ALL_TILES_136[108].is_terminal  # East (honor, not terminal)


class TestTileEncoding:
    def test_tile_id_to_34(self):
        assert tile_id_to_34(0) == 0   # 1m
        assert tile_id_to_34(3) == 0   # 1m (4th copy)
        assert tile_id_to_34(36) == 9  # 1p
        assert tile_id_to_34(108) == 27  # East

    def test_tiles_to_34_array(self):
        tiles = [ALL_TILES_136[0], ALL_TILES_136[1], ALL_TILES_136[4]]  # 1m, 1m, 2m
        arr = tiles_to_34_array(tiles)
        assert arr[0] == 2  # Two 1m
        assert arr[1] == 1  # One 2m
        assert sum(arr) == 3

    def test_34_name(self):
        assert tile_34_to_name(0) == "1m"
        assert tile_34_to_name(9) == "1p"
        assert tile_34_to_name(27) == "東"
        assert tile_34_to_name(33) == "中"


class TestNextTile:
    def test_number_wrap(self):
        assert next_tile_index(8) == 0  # 9m -> 1m
        assert next_tile_index(0) == 1  # 1m -> 2m
        assert next_tile_index(17) == 9  # 9p -> 1p

    def test_wind_wrap(self):
        assert next_tile_index(27) == 28  # 東 -> 南
        assert next_tile_index(30) == 27  # 北 -> 東

    def test_dragon_wrap(self):
        assert next_tile_index(31) == 32  # 白 -> 發
        assert next_tile_index(33) == 31  # 中 -> 白

    def test_sanma_man(self):
        assert next_tile_index(0, is_sanma=True) == 8  # 1m -> 9m (skip 2-8)
        assert next_tile_index(8, is_sanma=True) == 0  # 9m -> 1m


class TestMakeTilesFromString:
    def test_basic(self):
        tiles = make_tiles_from_string("123m")
        assert len(tiles) == 3
        assert tiles[0].index34 == 0  # 1m
        assert tiles[1].index34 == 1  # 2m
        assert tiles[2].index34 == 2  # 3m

    def test_mixed_suits(self):
        tiles = make_tiles_from_string("1m1p1s")
        assert len(tiles) == 3
        assert tiles[0].suit == TileSuit.MAN
        assert tiles[1].suit == TileSuit.PIN
        assert tiles[2].suit == TileSuit.SOU

    def test_honor_tiles(self):
        tiles = make_tiles_from_string("東南西北白發中")
        assert len(tiles) == 7
        assert tiles[0].index34 == 27
        assert tiles[6].index34 == 33

    def test_red_dora(self):
        tiles = make_tiles_from_string("0m")
        assert len(tiles) == 1
        assert tiles[0].is_red
        assert tiles[0].index34 == 4  # 5m position
