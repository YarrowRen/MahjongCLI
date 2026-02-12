"""Tests for greedy_ai.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.core.tile import ALL_TILES_136, make_tiles_from_string
from mahjong.core.hand import Hand
from mahjong.core.player_state import Wind
from mahjong.engine.action import ActionType, AvailableActions
from mahjong.player.base import GameView, OpponentView
from mahjong.player.greedy_ai import GreedyAI


def make_game_view(hand, seat=0, wind=Wind.EAST, score=25000,
                   opponents=None) -> GameView:
    return GameView(
        my_hand=hand,
        my_seat=seat,
        my_wind=wind,
        my_score=score,
        is_dealer=(wind == Wind.EAST),
        opponents=opponents or [],
        round_wind=Wind.EAST,
        remaining_tiles=70,
    )


class TestGreedyAIDiscard:
    def test_discard_reduces_shanten(self):
        """AI should choose discard that minimizes shanten."""
        ai = GreedyAI("test")
        hand = Hand()
        tiles = make_tiles_from_string("123m456p789s東東")
        for t in tiles:
            hand.closed_tiles.append(t)
        # Add an isolated honor tile
        north = make_tiles_from_string("北")[0]
        hand.draw(north)

        gv = make_game_view(hand)
        discard = ai.choose_discard(gv, hand.closed_tiles)
        # Should discard the isolated 北
        assert discard.index34 == 30  # 北

    def test_always_tsumo(self):
        """AI should always tsumo when available."""
        ai = GreedyAI("test")
        hand = Hand()
        tiles = make_tiles_from_string("123m456p789s東東東南")
        for t in tiles:
            hand.closed_tiles.append(t)

        gv = make_game_view(hand)
        available = AvailableActions(player=0)
        available.can_tsumo = True
        available.can_discard = list(hand.closed_tiles)

        action = ai.choose_action(gv, available)
        assert action.action_type == ActionType.TSUMO

    def test_always_ron(self):
        """AI should always ron when available."""
        ai = GreedyAI("test")
        hand = Hand()

        gv = make_game_view(hand)
        available = AvailableActions(player=0)
        available.can_ron = True

        action = ai.choose_action(gv, available)
        assert action.action_type == ActionType.RON


class TestGreedyAIDefense:
    def test_defense_mode(self):
        """AI should enter defense when opponent is riichi and own shanten >= 2."""
        ai = GreedyAI("test")
        hand = Hand()
        # Bad hand with high shanten
        tiles = make_tiles_from_string("159m159p159s東南西北")
        for t in tiles:
            hand.closed_tiles.append(t)

        opp = OpponentView(
            seat=1, name="opp", score=25000, seat_wind=Wind.SOUTH,
            is_dealer=False, is_riichi=True, melds=[], discard_pool=[],
            discard_called=[], num_closed_tiles=13,
        )

        gv = make_game_view(hand, opponents=[opp])
        assert ai._should_defend(gv)
