"""Regression tests for kita (北抜き) dora in sanma scoring.

Bug: scoring.calculate_score had full kita_count support, but round.py
never passed it, so kita dora bonuses were silently dropped in live games.
"""

from mahjong.core.player_state import PlayerState, Wind
from mahjong.core.tile import make_tiles_from_string
from mahjong.core.wall import Wall
from mahjong.engine.event import EventBus
from mahjong.engine.round import RoundState


def _make_sanma_round():
    players = [PlayerState(i, f"P{i}") for i in range(3)]
    for i, p in enumerate(players):
        p.seat_wind = Wind(i)
        p.is_dealer = (i == 0)
    # Unshuffled wall: dora indicator is 北 -> actual dora is 東.
    # The test hand below contains neither, so hand dora count is 0.
    rs = RoundState(
        players=players,
        wall=Wall(is_sanma=True, shuffle=False),
        round_wind=Wind.EAST,
        honba=0,
        riichi_sticks=0,
        event_bus=EventBus(),
        is_sanma=True,
    )
    return rs, players


def _give_normal_hand(player):
    """14-tile winning hand (menzen tsumo, NOT yakuman), no 東/red fives.

    Dora must not apply to yakuman hands, so this must stay a normal hand.
    """
    tiles = make_tiles_from_string("234p567p234s567s99s")
    player.hand.closed_tiles = list(tiles)
    player.hand.draw_tile = tiles[-1]


def _dora_han(result):
    return sum(han for name, han in result.yaku if name == "ドラ")


class TestKitaDora:
    def test_kita_counts_as_dora_on_tsumo(self):
        rs, players = _make_sanma_round()
        _give_normal_hand(players[1])
        players[1].kita_tiles = make_tiles_from_string("北北")

        result = rs.process_tsumo(1)
        assert result is not None
        assert _dora_han(result) == 2, "each kita tile must count as one dora"

    def test_no_kita_no_dora(self):
        rs, players = _make_sanma_round()
        _give_normal_hand(players[1])

        result = rs.process_tsumo(1)
        assert result is not None
        assert _dora_han(result) == 0

    def test_kita_counts_as_dora_on_ron(self):
        rs, players = _make_sanma_round()
        # Tenpai version: riichi supplies the yaku, ron on 9s
        tiles = make_tiles_from_string("234p567p234s567s9s")
        players[1].hand.closed_tiles = list(tiles)
        players[1].hand.is_riichi = True
        players[1].kita_tiles = make_tiles_from_string("北")
        nine_s = make_tiles_from_string("9s")[0]

        result = rs.process_ron(1, 0, nine_s)
        assert result is not None
        assert _dora_han(result) == 1
