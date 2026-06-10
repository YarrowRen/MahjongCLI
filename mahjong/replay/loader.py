"""Load and summarize game log files written by GameLogger."""

import json
import os
from dataclasses import dataclass
from typing import Dict, List

from mahjong.engine.game_logger import LOG_DIR


@dataclass
class GameSummary:
    """Lightweight summary of one logged game for list display."""
    path: str
    session_id: str
    timestamp: str
    players: List[str]
    final_scores: Dict[str, int]
    num_rounds: int
    is_sanma: bool


def list_game_logs(log_dir: str = None) -> List[GameSummary]:
    """List all game logs, newest first. Skips unreadable files."""
    log_dir = log_dir or LOG_DIR
    if not os.path.isdir(log_dir):
        return []

    summaries = []
    for name in os.listdir(log_dir):
        if not (name.startswith("game_") and name.endswith(".json")):
            continue
        path = os.path.join(log_dir, name)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            summaries.append(GameSummary(
                path=path,
                session_id=data["session_id"],
                timestamp=data["timestamp"],
                players=list(data["players"]),
                final_scores=dict(data.get("final_scores") or {}),
                num_rounds=len(data.get("rounds") or []),
                is_sanma=bool(data.get("config", {}).get("is_sanma")),
            ))
        except (OSError, ValueError, KeyError):
            continue

    summaries.sort(key=lambda s: s.timestamp, reverse=True)
    return summaries


def load_game(path: str) -> dict:
    """Load the full game log."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)
