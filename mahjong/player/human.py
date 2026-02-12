"""Human player - interfaces with terminal UI for input."""

from typing import List

from rich.console import Console

from mahjong.core.tile import Tile
from mahjong.engine.action import Action, ActionType, AvailableActions
from mahjong.player.base import Player, GameView, build_game_view
from mahjong.ui.renderer import Renderer
from mahjong.ui.input_handler import get_player_input
from mahjong.ui.board_layout import render_board, render_action_prompt


class HumanPlayer(Player):
    """Human player that uses terminal UI for interaction."""

    def __init__(self, name: str, console: Console, renderer: Renderer):
        super().__init__(name)
        self.console = console
        self.renderer = renderer
        self._game_view: GameView = None

    def set_game_view(self, game_view: GameView):
        """Update the current game view (called before each decision)."""
        self._game_view = game_view

    def choose_action(self, game_view: GameView,
                      available: AvailableActions) -> Action:
        """Get action from human via UI."""
        self._game_view = game_view
        self.renderer.render_game_view(game_view)
        self.renderer.render_actions(available)
        return get_player_input(self.console, game_view, available)

    def choose_discard(self, game_view: GameView,
                       available_discards: List[Tile]) -> Tile:
        """Choose a tile to discard."""
        self._game_view = game_view
        self.renderer.render_game_view(game_view)
        # Create a simple available actions with just discard
        available = AvailableActions(player=game_view.my_seat)
        available.can_discard = available_discards
        action = get_player_input(self.console, game_view, available)
        return action.tile

    def choose_riichi_discard(self, game_view: GameView,
                              riichi_candidates: List[Tile]) -> Tile:
        """Choose riichi discard tile."""
        from mahjong.ui.tile_display import tile_to_simple_str
        self.console.print("  选择立直打出的牌:")
        for i, tile in enumerate(riichi_candidates):
            self.console.print(f"    {i+1}. {tile_to_simple_str(tile)}")
        while True:
            try:
                idx = int(self.console.input("  > 编号: ").strip()) - 1
                if 0 <= idx < len(riichi_candidates):
                    return riichi_candidates[idx]
            except ValueError:
                pass
            self.console.print("  [red]无效输入[/red]")
