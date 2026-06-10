"""Rich rendering facade for the terminal UI.

The game loop (cli.py) drives rendering directly via this class.
The only event subscription is the riichi declaration notice, which
must be shown the moment it happens inside the engine loop.
"""

from rich.console import Console

from mahjong.player.base import GameView
from mahjong.engine.action import AvailableActions
from mahjong.engine.event import EventBus, EventType, GameEvent
from mahjong.ui.board_layout import render_board, render_action_prompt
from mahjong.ui.i18n import t


class Renderer:
    """Rendering facade; subscribes only to events that need instant output."""

    def __init__(self, console: Console, event_bus: EventBus,
                 human_seat: int = 0):
        self.console = console
        self.event_bus = event_bus
        self.human_seat = human_seat
        self.event_bus.subscribe(EventType.RIICHI_DECLARE, self._on_riichi)

    def render_game_view(self, game_view: GameView):
        """Render the current board state from the human player's perspective."""
        render_board(self.console, game_view)

    def render_actions(self, available: AvailableActions):
        """Show available actions to the player."""
        render_action_prompt(self.console, available)

    def _on_riichi(self, event: GameEvent):
        player_idx = event.data.get("player", -1)
        if player_idx != self.human_seat:
            self.console.print(
                f"  [bold yellow]{t('msg.riichi_declare', player=t('label.player_n', n=player_idx))}[/bold yellow]"
            )

    def pause(self, message: str = None):
        """Pause and wait for user input."""
        if message is None:
            message = t('prompt.press_enter')
        self.console.input(f"\n  {message}")
