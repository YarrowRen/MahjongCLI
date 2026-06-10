"""Regression tests for chankan (搶槓 / robbing a kan).

Bug: yaku.py and scoring.py supported is_chankan, but round.py never
passed it, so the chankan yaku was never awarded and a hand whose only
yaku would be chankan could not rob a kan at all.
"""

from mahjong.core.meld import Meld, MeldType
from mahjong.core.player_state import PlayerState, Wind
from mahjong.core.tile import make_tiles_from_string
from mahjong.core.wall import Wall
from mahjong.engine.event import EventBus
from mahjong.engine.round import RoundState


def _make_round():
    players = [PlayerState(i, f"P{i}") for i in range(4)]
    for i, p in enumerate(players):
        p.seat_wind = Wind(i)
        p.is_dealer = (i == 0)
    rs = RoundState(
        players=players,
        wall=Wall(),
        round_wind=Wind.EAST,
        honba=0,
        riichi_sticks=0,
        event_bus=EventBus(),
    )
    return rs, players


def _setup_yakuless_open_tenpai(player):
    """Open hand waiting on 5p/8p with no yaku (9m pair kills tanyao).

    Closed: 67p 234s 678s 99m (10 tiles) + chi 234m.
    Winning on 5p: 567p 234s 678s 99m + 234m — no yaku at all.
    """
    chi_tiles = tuple(make_tiles_from_string("234m"))
    player.hand.melds.append(Meld(MeldType.CHI, chi_tiles, chi_tiles[0], 3))
    player.hand.closed_tiles = list(make_tiles_from_string("67p234s678s99m"))


class TestChankan:
    def test_yakuless_hand_can_only_ron_via_chankan(self):
        rs, players = _make_round()
        _setup_yakuless_open_tenpai(players[1])
        five_p = make_tiles_from_string("5p")[0]

        normal = rs.get_response_actions(1, five_p, 0)
        assert not normal.can_ron, "no yaku: normal ron must be rejected"

        chankan = rs.get_response_actions(1, five_p, 0, is_chankan=True)
        assert chankan.can_ron, "chankan yaku must enable the ron"

    def test_chankan_yaku_awarded_in_score(self):
        rs, players = _make_round()
        _setup_yakuless_open_tenpai(players[1])
        five_p = make_tiles_from_string("5p")[0]

        result = rs.process_ron(1, 0, five_p, is_chankan=True)
        assert result is not None
        yaku_names = [name for name, _ in result.yaku]
        assert "搶槓" in yaku_names

    def test_normal_ron_does_not_get_chankan_yaku(self):
        rs, players = _make_round()
        # Closed tenpai with riichi so the hand has a yaku anyway
        players[1].hand.closed_tiles = list(
            make_tiles_from_string("234m567m67p234s99s"))
        players[1].hand.is_riichi = True
        five_p = make_tiles_from_string("5p")[0]

        result = rs.process_ron(1, 0, five_p)
        assert result is not None
        yaku_names = [name for name, _ in result.yaku]
        assert "搶槓" not in yaku_names

    def test_chankan_response_offers_no_calls(self):
        """When robbing a kan, pon/chi/kan on that tile are impossible."""
        rs, players = _make_round()
        # Player 2 holds two 5p (could normally pon)
        players[2].hand.closed_tiles = list(
            make_tiles_from_string("55p123m456m789m9s"))
        five_p = make_tiles_from_string("5p")[0]

        resp = rs.get_response_actions(2, five_p, 0, is_chankan=True)
        assert not resp.can_pon
        assert not resp.can_daiminkan
        assert not resp.can_chi
