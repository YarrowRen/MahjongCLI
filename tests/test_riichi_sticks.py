"""Regression tests for riichi stick accounting across rounds.

Bug: sticks declared during a round were tracked only on RoundState;
after a drawn round GameState never learned about them, so the 1000
points vanished from the game.
"""

from mahjong.engine.event import EventBus
from mahjong.engine.game import GameConfig, GameState


def _setup_game(num_players=4):
    config = GameConfig(num_players=num_players)
    names = [f"P{i}" for i in range(num_players)]
    game = GameState(config, names, EventBus())
    return game


def _declare_riichi(game, rs, seat):
    """Minimal riichi declaration side effects (as process_riichi does)."""
    game.players[seat].hand.is_riichi = True
    game.players[seat].score -= 1000
    rs.riichi_sticks += 1


def test_sticks_carry_over_after_exhaustive_draw():
    game = _setup_game()
    rs = game.setup_round()
    _declare_riichi(game, rs, 1)

    rs.process_exhaustive_draw()
    game.advance_round(rs.result)

    assert game.riichi_sticks == 1, "stick must stay on the table"
    total = sum(p.score for p in game.players) + game.riichi_sticks * 1000
    assert total == 100000, "points must be conserved"


def test_sticks_carry_over_after_abortive_draw():
    game = _setup_game()
    rs = game.setup_round()
    _declare_riichi(game, rs, 0)
    _declare_riichi(game, rs, 2)

    rs.process_abortive_draw("4riichi")
    game.advance_round(rs.result)

    assert game.riichi_sticks == 2
    total = sum(p.score for p in game.players) + game.riichi_sticks * 1000
    assert total == 100000


def test_carried_sticks_awarded_to_next_winner():
    """Sticks from a drawn round must be passed into the next round."""
    game = _setup_game()
    rs = game.setup_round()
    _declare_riichi(game, rs, 1)
    rs.process_exhaustive_draw()
    game.advance_round(rs.result)
    assert game.riichi_sticks == 1

    rs2 = game.setup_round()
    assert rs2.riichi_sticks == 1, "next round must see the carried stick"


def test_leftover_sticks_go_to_top_player_at_game_end():
    game = _setup_game()
    rs = game.setup_round()
    _declare_riichi(game, rs, 3)
    rs.process_exhaustive_draw()
    game.advance_round(rs.result)
    assert game.riichi_sticks == 1

    # Force game end
    game.players[0].score = 40000
    game.players[3].score -= 14000 - 1000  # keep arithmetic simple, not zero-sum here
    game.is_finished = True
    game._finalize()

    assert game.riichi_sticks == 0
    assert game.players[0].score == 41000, "top player receives leftover sticks"
