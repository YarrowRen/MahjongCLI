"""Human player - interfaces with terminal UI for input."""

import time
from typing import Optional

from rich.console import Console

from mahjong.engine.action import Action, AvailableActions
from mahjong.engine.time_control import TimeControl, TIME_CONTROL_PRESETS
from mahjong.player.base import Player, GameView
from mahjong.ui.renderer import Renderer
from mahjong.ui.input_handler import get_player_input


class HumanPlayer(Player):
    """Human player that uses terminal UI for interaction."""

    def __init__(self, name: str, console: Console, renderer: Renderer,
                 time_control: Optional[TimeControl] = None):
        super().__init__(name)
        self.console = console
        self.renderer = renderer
        self.time_control: TimeControl = time_control or TIME_CONTROL_PRESETS[0]
        self.bank_remaining: float = float(self.time_control.bank_seconds)

    def choose_action(self, game_view: GameView,
                      available: AvailableActions) -> Action:
        """Get action from human via UI."""
        deadline, base_end = self._compute_deadline()

        self.renderer.render_game_view(game_view)
        self.renderer.render_actions(available)

        t_start = time.monotonic()
        action = get_player_input(self.console, game_view, available,
                                  deadline, base_end)
        self._update_bank(time.monotonic() - t_start)
        return action

    # ------------------------------------------------------------------
    # Time control helpers
    # ------------------------------------------------------------------

    def _compute_deadline(self):
        """Return (deadline, base_end) for the current action."""
        tc = self.time_control
        if tc.is_unlimited:
            return None, None

        now = time.monotonic()
        base_end = now + tc.base_seconds
        deadline = now + tc.base_seconds + max(0.0, self.bank_remaining)
        return deadline, base_end

    def _update_bank(self, elapsed: float) -> None:
        """Consume bank time if the action took longer than base_seconds."""
        tc = self.time_control
        if tc.is_unlimited:
            return
        bank_used = max(0.0, elapsed - tc.base_seconds)
        self.bank_remaining = max(0.0, self.bank_remaining - bank_used)
