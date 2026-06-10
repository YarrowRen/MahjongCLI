"""Full-game invariant tests using AI self-play.

These act as a safety net for engine refactoring: they run complete
games with GreedyAI players and assert global invariants hold.
"""

import random

import pytest

from mahjong.engine.event import EventBus
from mahjong.engine.game import GameConfig, GameState
from mahjong.engine.round import run_round
from mahjong.player.base import build_game_view
from mahjong.player.greedy_ai import GreedyAI


def _play_full_game(seed: int, config: GameConfig) -> GameState:
    """Run a complete AI-vs-AI game and return the finished GameState."""
    random.seed(seed)
    names = [f"AI{i}" for i in range(config.num_players)]
    game = GameState(config, names, EventBus())
    ais = [GreedyAI(n) for n in names]

    rounds_played = 0
    while not game.is_finished:
        round_state = game.setup_round()

        def get_action(player_idx, available):
            gv = build_game_view(
                player_idx, game.players,
                game.round_wind, game.honba, game.riichi_sticks,
                round_state.wall.remaining,
                round_state.wall.dora_indicators,
            )
            return ais[player_idx].choose_action(gv, available)

        result = run_round(round_state, get_action)
        assert result is not None, "round ended without a result"
        game.advance_round(result)

        rounds_played += 1
        assert rounds_played < 100, "game did not terminate"

    return game


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_yonma_hanchan_completes(seed):
    """4-player hanchan: AI self-play must finish without errors."""
    config = GameConfig(num_players=4)
    game = _play_full_game(seed, config)
    assert game.is_finished
    assert len(game.round_results) > 0


@pytest.mark.parametrize("seed", [3, 11])
def test_sanma_hanchan_completes(seed):
    """3-player hanchan: AI self-play must finish without errors."""
    config = GameConfig(num_players=3, is_sanma=True)
    game = _play_full_game(seed, config)
    assert game.is_finished
    assert len(game.round_results) > 0


def test_tonpuu_completes():
    """East-only game must finish without errors."""
    config = GameConfig(num_players=4, is_tonpuu=True)
    game = _play_full_game(5, config)
    assert game.is_finished
