"""Tests for game.py - full game management"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mahjong.engine.action import Action, ActionType
from mahjong.engine.event import EventBus
from mahjong.engine.game import GameConfig, GameState


def simple_ai(player_idx, available):
    """Minimal AI for testing."""
    if available.can_tsumo:
        return Action(ActionType.TSUMO, player_idx)
    if available.can_ron:
        return Action(ActionType.RON, player_idx)
    if available.can_discard:
        return Action(ActionType.DISCARD, player_idx, tile=available.can_discard[0])
    return Action(ActionType.SKIP, player_idx)


class TestGameConfig:
    def test_default_config(self):
        config = GameConfig()
        assert config.num_players == 4
        assert not config.is_sanma
        assert not config.is_tonpuu

    def test_sanma_config(self):
        config = GameConfig(is_sanma=True)
        assert config.num_players == 3
        assert config.is_sanma


class TestGameState:
    def test_round_label(self):
        config = GameConfig()
        event_bus = EventBus()
        game = GameState(config, ["A", "B", "C", "D"], event_bus)
        assert "東一局" in game.round_label

    def test_setup_round(self):
        config = GameConfig()
        event_bus = EventBus()
        game = GameState(config, ["A", "B", "C", "D"], event_bus)
        rs = game.setup_round()
        assert rs is not None
        # Dealer should be player 0 initially
        assert game.players[0].is_dealer
