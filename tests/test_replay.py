"""Tests for the replay subsystem (loader + state reconstruction).

The integration tests generate real logs by running AI self-play games
with GameLogger attached, then replay every recorded action and verify
the reconstruction stays in sync (PlayerReplay._remove raises on any
desync, so completing a full replay is itself a strong check).
"""

import random

import pytest

import mahjong.engine.game_logger as game_logger_mod
from mahjong.core.tile import ALL_TILES_136
from mahjong.engine.event import EventBus
from mahjong.engine.game import GameConfig, GameState
from mahjong.engine.game_logger import GameLogger
from mahjong.engine.round import run_round
from mahjong.player.base import build_game_view
from mahjong.player.greedy_ai import GreedyAI
from mahjong.replay.loader import list_game_logs, load_game
from mahjong.replay.state import RoundReplay, parse_tile_str
from mahjong.ui.tile_display import tile_to_simple_str


class TestParseTileStr:
    def test_round_trip_all_kinds(self):
        """parse_tile_str must invert tile_to_simple_str for all 34 kinds."""
        for index34 in range(34):
            tile = ALL_TILES_136[index34 * 4]
            s = tile_to_simple_str(tile)
            assert tile_to_simple_str(parse_tile_str(s)) == s

    def test_round_trip_canonical_strings(self):
        """Round trip must hold from the string side too — '5m' is NOT red
        even though the red five occupies the first id of its kind."""
        names = [f"{n}{s}" for s in "mps" for n in range(1, 10)] + \
            list("東南西北白發中")
        for s in names:
            tile = parse_tile_str(s)
            assert not tile.is_red
            assert tile_to_simple_str(tile) == s

    def test_round_trip_red_fives(self):
        for s in ("0m", "0p", "0s"):
            tile = parse_tile_str(s)
            assert tile.is_red
            assert tile_to_simple_str(tile) == s

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            parse_tile_str("xyz")


def _generate_log(tmp_path, seed: int, config: GameConfig) -> str:
    """Run a full AI game with logging enabled; return the log path."""
    random.seed(seed)
    names = [f"AI{i}" for i in range(config.num_players)]
    event_bus = EventBus()
    game = GameState(config, names, event_bus)
    ais = [GreedyAI(n) for n in names]

    logger = GameLogger(names, {
        "num_players": config.num_players,
        "is_sanma": config.is_sanma,
        "is_tonpuu": config.is_tonpuu,
        "starting_score": config.starting_score,
    })
    logger.subscribe_events(event_bus)

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
        logger.end_round(result)
        game.advance_round(result)

    return logger.save({p.name: p.score for p in game.players})


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    """Redirect GameLogger output to a temp directory."""
    monkeypatch.setattr(game_logger_mod, "LOG_DIR", str(tmp_path))
    return str(tmp_path)


def _replay_all_rounds(log_path: str):
    """Replay every action of every round; return the loaded log."""
    data = load_game(log_path)
    is_sanma = data["config"]["is_sanma"]
    for round_data in data["rounds"]:
        rr = RoundReplay(round_data, data["players"], is_sanma)

        # Step through one by one (exercises incremental application)
        for n in range(rr.num_steps + 1):
            rr.goto(n)
        assert rr.is_finished

        # Per-player consistency against the raw action list
        for p in rr.players:
            my_discards = [a for a in round_data["actions"]
                           if a["action"] == "discard" and a["seat"] == p.seat]
            assert len(p.discards) == len(my_discards)
            assert [tile_to_simple_str(t) for t in p.discards] == \
                [a["tile"] for a in my_discards]

            my_riichi = [a for a in round_data["actions"]
                         if a["action"] == "riichi" and a["seat"] == p.seat]
            assert p.is_riichi == bool(my_riichi)

            my_kita = [a for a in round_data["actions"]
                       if a["action"] == "kita" and a["seat"] == p.seat]
            assert p.kita_count == len(my_kita)

        calls = [a for a in round_data["actions"]
                 if a["action"] in ("chi", "pon", "daiminkan")]
        called_total = sum(sum(p.discard_called) for p in rr.players)
        assert called_total == len(calls)

        assert rr.remaining >= 0
        assert 1 <= len(rr.dora_indicators) <= 5
    return data


class TestRoundReplay:
    @pytest.mark.parametrize("seed", [1, 42])
    def test_full_replay_yonma(self, log_dir, seed):
        path = _generate_log(log_dir, seed, GameConfig(num_players=4))
        data = _replay_all_rounds(path)
        assert len(data["rounds"]) > 0

    def test_full_replay_sanma(self, log_dir):
        path = _generate_log(log_dir, 7, GameConfig(num_players=3, is_sanma=True))
        data = _replay_all_rounds(path)
        assert len(data["rounds"]) > 0

    def test_backward_jump_matches_fresh_state(self, log_dir):
        """goto(k) after goto(n>k) must equal a fresh goto(k)."""
        path = _generate_log(log_dir, 42, GameConfig(num_players=4))
        data = load_game(path)
        round_data = data["rounds"][0]

        rr = RoundReplay(round_data, data["players"], False)
        rr.goto(rr.num_steps)
        k = rr.num_steps // 2
        rr.goto(k)

        fresh = RoundReplay(round_data, data["players"], False)
        fresh.goto(k)

        for a, b in zip(rr.players, fresh.players):
            assert [t.id for t in sorted(a.closed)] == \
                [t.id for t in sorted(b.closed)]
            assert [t.id for t in a.discards] == [t.id for t in b.discards]
            assert len(a.melds) == len(b.melds)
        assert rr.remaining == fresh.remaining


class TestLoader:
    def test_list_and_load(self, log_dir):
        path = _generate_log(log_dir, 3, GameConfig(num_players=4))
        summaries = list_game_logs(log_dir)
        assert len(summaries) == 1
        s = summaries[0]
        assert s.path == path
        assert len(s.players) == 4
        assert s.num_rounds > 0
        assert not s.is_sanma

        data = load_game(s.path)
        assert data["session_id"] == s.session_id

    def test_empty_dir(self, tmp_path):
        assert list_game_logs(str(tmp_path)) == []

    def test_skips_corrupt_files(self, tmp_path):
        (tmp_path / "game_bad.json").write_text("not json")
        assert list_game_logs(str(tmp_path)) == []
