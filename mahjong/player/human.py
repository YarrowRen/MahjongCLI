"""Human player - interfaces with terminal UI for input."""

import time
from typing import List, Optional

from rich.console import Console

from mahjong.core.tile import Tile
from mahjong.engine.action import Action, ActionType, AvailableActions
from mahjong.engine.time_control import TimeControl, TIME_CONTROL_PRESETS
from mahjong.player.base import Player, GameView, build_game_view
from mahjong.ui.renderer import Renderer
from mahjong.ui.input_handler import get_player_input
from mahjong.ui.board_layout import render_board, render_action_prompt


class HumanPlayer(Player):
    """Human player that uses terminal UI for interaction."""

    def __init__(self, name: str, console: Console, renderer: Renderer,
                 time_control: Optional[TimeControl] = None):
        super().__init__(name)
        self.console = console
        self.renderer = renderer
        self._game_view: GameView = None
        self.time_control: TimeControl = time_control or TIME_CONTROL_PRESETS[0]
        self.bank_remaining: float = float(self.time_control.bank_seconds)

    def set_game_view(self, game_view: GameView):
        """Update the current game view (called before each decision)."""
        self._game_view = game_view

    def choose_action(self, game_view: GameView,
                      available: AvailableActions) -> Action:
        """Get action from human via UI."""
        self._game_view = game_view
        deadline, base_end = self._compute_deadline()

        self.renderer.render_game_view(game_view)
        self.renderer.render_actions(available)

        t_start = time.monotonic()
        action = get_player_input(self.console, game_view, available, deadline, base_end)
        self._update_bank(time.monotonic() - t_start)
        return action

    def choose_discard(self, game_view: GameView,
                       available_discards: List[Tile]) -> Tile:
        """Choose a tile to discard."""
        self._game_view = game_view
        deadline, base_end = self._compute_deadline()

        self.renderer.render_game_view(game_view)

        available = AvailableActions(player=game_view.my_seat)
        available.can_discard = available_discards

        t_start = time.monotonic()
        action = get_player_input(self.console, game_view, available, deadline, base_end)
        self._update_bank(time.monotonic() - t_start)
        return action.tile

    def choose_riichi_discard(self, game_view: GameView,
                              riichi_candidates: List[Tile]) -> Tile:
        """Choose riichi discard tile."""
        from mahjong.ui.tile_display import tile_to_display_str
        from mahjong.ui.i18n import t
        from mahjong.ui.timeout_input import timed_input

        deadline, base_end = self._compute_deadline()

        self.console.print(f"  {t('prompt.choose_riichi_discard')}")
        for i, tile in enumerate(riichi_candidates):
            self.console.print(f"    {i+1}. {tile_to_display_str(tile)}")

        t_start = time.monotonic()
        while True:
            result = timed_input(f"  > {t('prompt.number')} ", deadline, base_end=base_end)
            if result is None:
                from mahjong.ui.i18n import t as _t
                self.console.print(f"  [yellow]{_t('tc.timeout')}[/yellow]")
                self._update_bank(time.monotonic() - t_start)
                return riichi_candidates[0]
            try:
                idx = int(result.strip()) - 1
                if 0 <= idx < len(riichi_candidates):
                    self._update_bank(time.monotonic() - t_start)
                    return riichi_candidates[idx]
            except ValueError:
                pass
            self.console.print(f"  [red]{t('prompt.invalid_input')}[/red]")

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
