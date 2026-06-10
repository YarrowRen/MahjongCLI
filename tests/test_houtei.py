"""Regression tests for houtei (河底撈魚) detection consistency.

Bug: _has_valid_score derived houtei from the is_haitei flag (set when
the LAST WALL TILE was drawn) while process_ron used wall.remaining == 0.
The two could disagree; both now use wall.remaining == 0.
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
    """Open hand waiting on 5p/8p with no yaku (see test_chankan)."""
    chi_tiles = tuple(make_tiles_from_string("234m"))
    player.hand.melds.append(Meld(MeldType.CHI, chi_tiles, chi_tiles[0], 3))
    player.hand.closed_tiles = list(make_tiles_from_string("67p234s678s99m"))


def test_houtei_enables_yakuless_ron_on_last_discard():
    rs, players = _make_round()
    _setup_yakuless_open_tenpai(players[1])
    five_p = make_tiles_from_string("5p")[0]

    # Wall not empty: no yaku, ron rejected
    resp = rs.get_response_actions(1, five_p, 0)
    assert not resp.can_ron

    # Wall empty: houtei supplies the yaku
    rs.wall.live_wall.clear()
    resp = rs.get_response_actions(1, five_p, 0)
    assert resp.can_ron

    result = rs.process_ron(1, 0, five_p)
    assert result is not None
    yaku_names = [name for name, _ in result.yaku]
    assert "河底撈魚" in yaku_names


def test_availability_and_scoring_agree_on_houtei():
    """The ron offer (_has_valid_score) and the actual scoring
    (process_ron) must use the same houtei condition."""
    rs, players = _make_round()
    _setup_yakuless_open_tenpai(players[1])
    five_p = make_tiles_from_string("5p")[0]
    rs.wall.live_wall.clear()

    resp = rs.get_response_actions(1, five_p, 0)
    result = rs.process_ron(1, 0, five_p)
    assert resp.can_ron == (result is not None)
