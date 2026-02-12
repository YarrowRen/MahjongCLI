"""Tests for wall.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.core.wall import Wall


class TestWall:
    def test_four_player_wall(self):
        wall = Wall(is_sanma=False)
        assert wall.total_tiles == 136
        # 136 - 14 dead wall = 122 live
        assert wall.remaining == 122

    def test_sanma_wall(self):
        wall = Wall(is_sanma=True)
        assert wall.total_tiles == 108
        # 108 - 14 dead wall = 94 live
        assert wall.remaining == 94
        # Verify no 2m-8m tiles
        for t in wall.all_tiles:
            assert not (1 <= t.index34 <= 7), f"Found {t.name} in sanma wall"

    def test_draw(self):
        wall = Wall(is_sanma=False)
        initial = wall.remaining
        tile = wall.draw()
        assert tile is not None
        assert wall.remaining == initial - 1

    def test_draw_until_empty(self):
        wall = Wall(is_sanma=False)
        count = 0
        while not wall.is_empty:
            tile = wall.draw()
            assert tile is not None
            count += 1
        assert count == 122
        assert wall.draw() is None

    def test_dora_indicators(self):
        wall = Wall(is_sanma=False, shuffle=False)
        indicators = wall.dora_indicators
        assert len(indicators) == 1  # Initially one dora revealed

        wall.reveal_new_dora()
        assert len(wall.dora_indicators) == 2

    def test_rinshan_draw(self):
        wall = Wall(is_sanma=False)
        tile = wall.draw_rinshan()
        assert tile is not None

        # Can draw up to 4 rinshan tiles
        for _ in range(3):
            assert wall.draw_rinshan() is not None
        assert wall.draw_rinshan() is None  # 5th should fail

    def test_dora_calculation(self):
        wall = Wall(is_sanma=False, shuffle=False)
        dora_34 = wall.get_dora_tiles_34()
        assert len(dora_34) == 1
        # The actual dora depends on the indicator tile

    def test_uradora(self):
        wall = Wall(is_sanma=False, shuffle=False)
        uradora_34 = wall.get_uradora_tiles_34()
        assert len(uradora_34) == 1

    def test_max_dora_reveals(self):
        wall = Wall(is_sanma=False)
        for _ in range(5):
            wall.reveal_new_dora()
        assert len(wall.dora_indicators) == 5
        # Can't reveal more
        wall.reveal_new_dora()
        assert len(wall.dora_indicators) == 5
