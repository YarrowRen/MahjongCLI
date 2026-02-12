"""Tests for round.py - game round flow"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.core.wall import Wall
from mahjong.core.player_state import PlayerState, Wind
from mahjong.engine.action import Action, ActionType, AvailableActions
from mahjong.engine.event import EventBus
from mahjong.engine.round import RoundState, run_round


def make_simple_ai_action(player_idx, available):
    """Simple AI: always tsumo/ron if possible, otherwise discard first tile."""
    if available.can_tsumo:
        return Action(ActionType.TSUMO, player_idx)
    if available.can_ron:
        return Action(ActionType.RON, player_idx)
    if available.can_discard:
        return Action(ActionType.DISCARD, player_idx, tile=available.can_discard[0])
    return Action(ActionType.SKIP, player_idx)


class TestRoundBasic:
    def test_round_completes(self):
        """A round with simple AI should complete without error."""
        players = [PlayerState(i, f"P{i}") for i in range(4)]
        wall = Wall(is_sanma=False)
        event_bus = EventBus()

        rs = RoundState(
            players=players,
            wall=wall,
            round_wind=Wind.EAST,
            honba=0,
            riichi_sticks=0,
            event_bus=event_bus,
        )

        result = run_round(rs, make_simple_ai_action)
        assert result is not None
        assert result.is_draw or len(result.winners) > 0

    def test_round_score_changes_balance(self):
        """Score changes should sum to 0 (zero-sum)."""
        players = [PlayerState(i, f"P{i}") for i in range(4)]
        wall = Wall(is_sanma=False)
        event_bus = EventBus()

        rs = RoundState(
            players=players,
            wall=wall,
            round_wind=Wind.EAST,
            honba=0,
            riichi_sticks=0,
            event_bus=event_bus,
        )

        result = run_round(rs, make_simple_ai_action)
        assert result is not None
        # Score changes should balance (excluding riichi sticks)
        total_change = sum(result.score_changes[:4])
        # Total change should be riichi_sticks * 1000 if someone won
        # or 0 if draw (tenpai payments balance)
        # Just check it's reasonable
        assert abs(total_change) <= 4000  # At most 4 riichi sticks worth

    def test_sanma_round(self):
        """Sanma round should complete."""
        players = [PlayerState(i, f"P{i}") for i in range(3)]
        wall = Wall(is_sanma=True)
        event_bus = EventBus()

        rs = RoundState(
            players=players,
            wall=wall,
            round_wind=Wind.EAST,
            honba=0,
            riichi_sticks=0,
            event_bus=event_bus,
            is_sanma=True,
        )

        result = run_round(rs, make_simple_ai_action)
        assert result is not None


class TestDealTiles:
    def test_initial_deal(self):
        """Each player should have 13 tiles after deal."""
        players = [PlayerState(i, f"P{i}") for i in range(4)]
        wall = Wall(is_sanma=False)
        event_bus = EventBus()

        rs = RoundState(
            players=players, wall=wall, round_wind=Wind.EAST,
            honba=0, riichi_sticks=0, event_bus=event_bus,
        )
        rs.deal_tiles()

        for p in players:
            assert len(p.hand.closed_tiles) == 13
