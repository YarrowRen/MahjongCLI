"""State comparison and score verification for replay testing."""

from typing import List, Optional

from mahjong.core.tile import Tile
from mahjong.engine.round import RoundState


class ReplayVerificationError(Exception):
    """Raised when replay state doesn't match expected."""
    pass


def verify_draw(rs: RoundState, player: int, expected_tile_id: int,
                is_rinshan: bool, step_desc: str):
    """Verify that the drawn tile matches expected."""
    hand = rs.players[player].hand
    if hand.draw_tile is None:
        raise ReplayVerificationError(
            f"[{step_desc}] Player {player} draw_tile is None, "
            f"expected tile {expected_tile_id}"
        )
    if hand.draw_tile.id != expected_tile_id:
        raise ReplayVerificationError(
            f"[{step_desc}] Player {player} drew tile {hand.draw_tile.id} "
            f"({hand.draw_tile.name}), expected {expected_tile_id}"
        )


def verify_agari_score(ten: List[int], engine_fu: int, engine_points: int,
                       step_desc: str):
    """Verify fu and total points from AGARI ten attribute.

    ten = [fu, points, tsumo_damage_flag]
    """
    expected_fu = ten[0]
    expected_points = ten[1]

    if expected_fu != 0 and engine_fu != expected_fu:
        raise ReplayVerificationError(
            f"[{step_desc}] Fu mismatch: engine={engine_fu}, expected={expected_fu}"
        )
    if engine_points != expected_points:
        raise ReplayVerificationError(
            f"[{step_desc}] Points mismatch: engine={engine_points}, "
            f"expected={expected_points}"
        )


def verify_score_changes(sc: List[int], engine_score_changes: List[int],
                         initial_scores: List[int], step_desc: str):
    """Verify score changes from AGARI/RYUUKYOKU sc attribute.

    sc = [p0_score_before/100, p0_change/100, p1_score/100, p1_change/100, ...]
    """
    expected_changes = [sc[i * 2 + 1] * 100 for i in range(4)]

    for i in range(4):
        if engine_score_changes[i] != expected_changes[i]:
            raise ReplayVerificationError(
                f"[{step_desc}] Score change mismatch for player {i}: "
                f"engine={engine_score_changes[i]}, expected={expected_changes[i]}\n"
                f"  engine_changes={engine_score_changes}\n"
                f"  expected_changes={expected_changes}"
            )
