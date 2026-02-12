"""Rich rendering engine - ties together all UI components."""

from rich.console import Console

from mahjong.player.base import GameView
from mahjong.engine.action import AvailableActions
from mahjong.engine.event import EventBus, EventType, GameEvent
from mahjong.rules.scoring import ScoreResult
from mahjong.ui.board_layout import (
    render_board, render_action_prompt, render_win_screen,
    render_draw_screen, render_scores, render_game_end,
)
from mahjong.ui.i18n import *


class Renderer:
    """Main rendering engine that subscribes to game events."""

    def __init__(self, console: Console, event_bus: EventBus,
                 human_seat: int = 0):
        self.console = console
        self.event_bus = event_bus
        self.human_seat = human_seat
        self._subscribe_events()

    def _subscribe_events(self):
        """Subscribe to relevant game events."""
        self.event_bus.subscribe(EventType.ROUND_START, self._on_round_start)
        self.event_bus.subscribe(EventType.TSUMO, self._on_tsumo)
        self.event_bus.subscribe(EventType.RON, self._on_ron)
        self.event_bus.subscribe(EventType.EXHAUSTIVE_DRAW, self._on_exhaustive_draw)
        self.event_bus.subscribe(EventType.ABORTIVE_DRAW, self._on_abortive_draw)
        self.event_bus.subscribe(EventType.RIICHI_DECLARE, self._on_riichi)
        self.event_bus.subscribe(EventType.KAN, self._on_kan)
        self.event_bus.subscribe(EventType.GAME_END, self._on_game_end)

    def render_game_view(self, game_view: GameView):
        """Render the current board state from the human player's perspective."""
        render_board(self.console, game_view)

    def render_actions(self, available: AvailableActions):
        """Show available actions to the player."""
        render_action_prompt(self.console, available)

    def _on_round_start(self, event: GameEvent):
        pass  # Board will be rendered on player's turn

    def _on_tsumo(self, event: GameEvent):
        pass  # Handled by game loop

    def _on_ron(self, event: GameEvent):
        pass  # Handled by game loop

    def _on_exhaustive_draw(self, event: GameEvent):
        pass

    def _on_abortive_draw(self, event: GameEvent):
        pass

    def _on_riichi(self, event: GameEvent):
        player_idx = event.data.get("player", -1)
        if player_idx != self.human_seat:
            self.console.print(
                f"  [bold yellow]{MSG_RIICHI_DECLARE.format(player=f'玩家{player_idx}')}[/bold yellow]"
            )

    def _on_kan(self, event: GameEvent):
        pass

    def _on_game_end(self, event: GameEvent):
        players = event.data.get("players", [])
        render_game_end(self.console, players)

    def show_win(self, player_name: str, result: ScoreResult,
                 is_tsumo: bool, loser_name: str = ""):
        """Display win screen."""
        render_win_screen(self.console, player_name, result, is_tsumo, loser_name)

    def show_draw(self, draw_type: str, tenpai_info: list = None):
        """Display draw screen."""
        render_draw_screen(self.console, draw_type, tenpai_info)

    def show_scores(self, players: list):
        """Display current scores."""
        render_scores(self.console, players)

    def pause(self, message: str = "按回车继续..."):
        """Pause and wait for user input."""
        self.console.input(f"\n  {message}")
