"""Regression tests for first-turn rules: tenhou, chiihou, kyuushu kyuuhai.

These were broken by a turn_count off-by-one: the main loop increments
turn_count right after drawing, so `turn_count == 0` was never true at
the dealer's first action, and the 4th player could never declare kyuushu.
"""

from mahjong.core.meld import Meld, MeldType
from mahjong.core.player_state import PlayerState, Wind
from mahjong.core.tile import make_tiles_from_string
from mahjong.core.wall import Wall
from mahjong.engine.event import EventBus
from mahjong.engine.round import RoundState


def _make_round(num_players=4, is_sanma=False):
    players = [PlayerState(i, f"P{i}") for i in range(num_players)]
    for i, p in enumerate(players):
        p.seat_wind = Wind(i)
        p.is_dealer = (i == 0)
    rs = RoundState(
        players=players,
        wall=Wall(is_sanma=is_sanma),
        round_wind=Wind.EAST,
        honba=0,
        riichi_sticks=0,
        event_bus=EventBus(),
        is_sanma=is_sanma,
    )
    return rs, players


def _give_winning_hand(player):
    """14-tile standard winning hand (has tanyao so always has yaku)."""
    tiles = make_tiles_from_string("234m567m234p567p55s")
    player.hand.closed_tiles = list(tiles)
    player.hand.draw_tile = tiles[-1]


class TestTenhou:
    def test_dealer_first_draw_win_is_tenhou(self):
        """Dealer winning on the very first draw must score 天和."""
        rs, players = _make_round()
        _give_winning_hand(players[0])
        # Simulate state at dealer's first action: drew, turn_count bumped
        rs.turn_count = 1
        rs.first_draw = [True] * 4

        actions = rs.get_draw_actions(0)
        assert actions.can_tsumo

        result = rs.process_tsumo(0)
        assert result is not None
        yaku_names = [name for name, _ in result.yaku]
        assert "天和" in yaku_names

    def test_dealer_win_after_discard_is_not_tenhou(self):
        """Dealer winning later in the round must not score 天和."""
        rs, players = _make_round()
        _give_winning_hand(players[0])
        rs.turn_count = 5
        rs.first_draw = [False] * 4

        result = rs.process_tsumo(0)
        assert result is not None
        yaku_names = [name for name, _ in result.yaku]
        assert "天和" not in yaku_names

    def test_dealer_rinshan_after_own_kan_is_not_tenhou(self):
        """Dealer kan then rinshan tsumo: a call was made, not 天和."""
        rs, players = _make_round()
        _give_winning_hand(players[0])
        rs.turn_count = 1
        rs.first_draw = [True] * 4
        # Dealer declared an ankan before winning
        kan_tiles = tuple(make_tiles_from_string("東東東東"))
        players[0].hand.melds.append(Meld(MeldType.ANKAN, kan_tiles))
        # 11 closed tiles (3 mentsu + pair, draw included); 東 kan gives yakuhai
        tiles = make_tiles_from_string("234m567m234p55s")
        players[0].hand.closed_tiles = list(tiles)
        players[0].hand.draw_tile = tiles[-1]

        result = rs.process_tsumo(0)
        assert result is not None, "hand should win via yakuhai 東"
        yaku_names = [name for name, _ in result.yaku]
        assert "天和" not in yaku_names


class TestChiihou:
    def test_non_dealer_first_draw_win_is_chiihou(self):
        """Non-dealer winning on their first draw with no calls is 地和."""
        rs, players = _make_round()
        _give_winning_hand(players[1])
        rs.turn_count = 2  # dealer acted, now player 1's first draw
        rs.first_draw = [False, True, True, True]

        result = rs.process_tsumo(1)
        assert result is not None
        yaku_names = [name for name, _ in result.yaku]
        assert "地和" in yaku_names

    def test_chiihou_cancelled_by_call(self):
        """A call before the first draw cancels 地和."""
        rs, players = _make_round()
        _give_winning_hand(players[1])
        rs.turn_count = 2
        rs.first_draw = [False, True, True, True]
        # Another player has melded — chiihou is dead
        pon_tiles = tuple(make_tiles_from_string("白白白"))
        players[3].hand.melds.append(
            Meld(MeldType.PON, pon_tiles, pon_tiles[0], 0))

        result = rs.process_tsumo(1)
        assert result is not None
        yaku_names = [name for name, _ in result.yaku]
        assert "地和" not in yaku_names


class TestKyuushu:
    def _give_kyuushu_hand(self, player):
        """14 tiles with 13 distinct terminals/honors."""
        tiles = make_tiles_from_string("19m19p19s東南西北白發中東")
        player.hand.closed_tiles = list(tiles)
        player.hand.draw_tile = tiles[-1]

    def test_all_seats_can_declare_kyuushu(self):
        """Every player (including the 4th) can declare on their first draw."""
        for seat in range(4):
            rs, players = _make_round()
            self._give_kyuushu_hand(players[seat])
            # turn_count after this player's first draw == seat + 1
            rs.turn_count = seat + 1
            rs.first_draw = [i >= seat for i in range(4)]

            actions = rs.get_draw_actions(seat)
            assert actions.can_kyuushu, f"seat {seat} cannot declare kyuushu"

    def test_kyuushu_blocked_after_call(self):
        """A call before the first draw blocks kyuushu."""
        rs, players = _make_round()
        self._give_kyuushu_hand(players[2])
        rs.turn_count = 3
        rs.first_draw = [False, False, True, True]
        pon_tiles = tuple(make_tiles_from_string("白白白"))
        players[0].hand.melds.append(
            Meld(MeldType.PON, pon_tiles, pon_tiles[0], 1))

        actions = rs.get_draw_actions(2)
        assert not actions.can_kyuushu
