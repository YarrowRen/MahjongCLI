"""Game logger - records complete game state for replay and debugging."""

import json
import os
import uuid
from datetime import datetime
from typing import List, Optional

from mahjong.core.tile import Tile
from mahjong.engine.event import EventBus, EventType, GameEvent
from mahjong.ui.tile_display import tile_to_simple_str

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "logs")


def _tile_str(tile: Tile) -> str:
    return tile_to_simple_str(tile)


def _tiles_str(tiles) -> List[str]:
    return [_tile_str(t) for t in tiles]


class GameLogger:
    """Records complete game data to JSON log files."""

    def __init__(self, player_names: List[str], config_info: dict):
        self.session_id = uuid.uuid4().hex[:12]
        self.timestamp = datetime.now().isoformat()
        self.player_names = player_names
        self.config_info = config_info

        self.rounds: List[dict] = []
        self._current_round: Optional[dict] = None

        os.makedirs(LOG_DIR, exist_ok=True)

    def subscribe_events(self, event_bus: EventBus):
        """Subscribe to engine events for automatic logging."""
        event_bus.subscribe(EventType.DEAL, self._on_deal)
        event_bus.subscribe(EventType.DRAW, self._on_draw)
        event_bus.subscribe(EventType.DISCARD, self._on_discard)
        event_bus.subscribe(EventType.CHI, self._on_call)
        event_bus.subscribe(EventType.PON, self._on_call)
        event_bus.subscribe(EventType.KAN, self._on_kan)
        event_bus.subscribe(EventType.RIICHI_DECLARE, self._on_riichi)
        event_bus.subscribe(EventType.TSUMO, self._on_tsumo)
        event_bus.subscribe(EventType.RON, self._on_ron)
        event_bus.subscribe(EventType.KITA, self._on_kita)

    def end_round(self, result):
        """Log the round result."""
        if self._current_round is None:
            return

        result_data = {
            "is_draw": result.is_draw,
            "draw_type": result.draw_type if result.is_draw else None,
            "winners": [self.player_names[w] for w in result.winners],
            "loser": self.player_names[result.loser] if result.loser is not None else None,
            "score_changes": {
                self.player_names[i]: result.score_changes[i]
                for i in range(len(self.player_names))
            },
        }

        if result.score_results:
            result_data["yaku"] = {}
            for winner_idx, score_result in result.score_results:
                result_data["yaku"][self.player_names[winner_idx]] = {
                    "han": score_result.han,
                    "fu": score_result.fu,
                    "total_points": score_result.total_points,
                    "yaku_list": [
                        {"name": name, "han": han}
                        for name, han in score_result.yaku
                    ],
                }

        self._current_round["result"] = result_data
        self._current_round = None

    def save(self, final_scores: dict):
        """Save the complete game log to a JSON file."""
        log_data = {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "config": self.config_info,
            "players": self.player_names,
            "final_scores": final_scores,
            "rounds": self.rounds,
        }

        filename = f"game_{self.session_id}.json"
        filepath = os.path.join(LOG_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        return filepath

    # --- Event handlers ---

    def _on_deal(self, event: GameEvent):
        """Called after initial deal — records wall and initial hands."""
        players = event.data["players"]
        wall = event.data["wall"]

        round_data = {
            "round_id": uuid.uuid4().hex[:8],
            "wall": {
                "tile_ids": [t.id for t in wall.all_tiles],
                "tile_names": _tiles_str(wall.all_tiles),
            },
            "dora_indicators": _tiles_str(wall.dora_indicators),
            "initial_hands": {},
            "actions": [],
            "result": None,
        }

        for i, p in enumerate(players):
            round_data["initial_hands"][self.player_names[i]] = {
                "seat": i,
                "wind": p.seat_wind.kanji,
                "is_dealer": p.is_dealer,
                "tiles": _tiles_str(sorted(p.hand.closed_tiles)),
            }

        self._current_round = round_data
        self.rounds.append(round_data)

    def _log_action(self, action_type: str, player: int, **kwargs):
        """Log a game action."""
        if self._current_round is None:
            return

        entry = {
            "action": action_type,
            "player": self.player_names[player] if 0 <= player < len(self.player_names) else "?",
            "seat": player,
        }

        for key, val in kwargs.items():
            if isinstance(val, Tile):
                entry[key] = _tile_str(val)
            elif isinstance(val, (list, tuple)) and val and isinstance(val[0], Tile):
                entry[key] = _tiles_str(val)
            else:
                entry[key] = val

        self._current_round["actions"].append(entry)

    def _on_draw(self, event: GameEvent):
        d = event.data
        extra = {}
        if d.get("is_rinshan"):
            extra["is_rinshan"] = True
        self._log_action("draw", d["player"], tile=d["tile"], **extra)

    def _on_discard(self, event: GameEvent):
        d = event.data
        self._log_action("discard", d["player"],
                         tile=d["tile"], tsumogiri=d.get("is_tsumogiri", False))

    def _on_call(self, event: GameEvent):
        d = event.data
        meld = d["meld"]
        self._log_action(meld.meld_type.value, d["player"],
                         tiles=list(meld.tiles),
                         from_player=self.player_names[meld.from_player]
                         if meld.from_player is not None else None)

    def _on_kan(self, event: GameEvent):
        d = event.data
        meld = d["meld"]
        self._log_action(meld.meld_type.value, d["player"],
                         tiles=list(meld.tiles),
                         new_dora=d.get("new_dora"))

    def _on_riichi(self, event: GameEvent):
        d = event.data
        self._log_action("riichi", d["player"],
                         is_double=d.get("is_double", False))

    def _on_tsumo(self, event: GameEvent):
        d = event.data
        self._log_action("tsumo", d["player"])

    def _on_ron(self, event: GameEvent):
        d = event.data
        self._log_action("ron", d["player"],
                         from_player=self.player_names[d["from_player"]])

    def _on_kita(self, event: GameEvent):
        d = event.data
        self._log_action("kita", d["player"])
