#!/usr/bin/env python3
"""日本立直麻将 - 终端CLI游戏入口"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt

from mahjong.core.player_state import Wind
from mahjong.engine.action import Action, ActionType, AvailableActions
from mahjong.engine.event import EventBus, EventType, GameEvent
from mahjong.engine.game import GameConfig, GameState, run_game
from mahjong.engine.round import RoundState, run_round
from mahjong.player.base import Player, GameView, build_game_view
from mahjong.player.greedy_ai import GreedyAI
from mahjong.player.human import HumanPlayer
from mahjong.ui.renderer import Renderer
from mahjong.ui.board_layout import (
    render_win_screen, render_draw_screen, render_scores, render_game_end,
    render_round_end_hands
)
from mahjong.ui.i18n import *

console = Console()


def show_menu() -> int:
    """Show mode selection menu and return choice."""
    console.print()
    console.print(Panel(
        "[bold cyan]日本立直麻将[/bold cyan]\n"
        "[dim]Terminal CLI Edition[/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()
    console.print(f"  {MSG_MODE_SELECT}")
    console.print(f"    1. {MSG_MODE_4P}")
    console.print(f"    2. {MSG_MODE_4P_TONPUU}")
    console.print(f"    3. {MSG_MODE_3P}")
    console.print(f"    4. {MSG_MODE_3P_TONPUU}")
    console.print(f"    5. 观战模式 (AI vs AI)")
    console.print(f"    0. {MSG_QUIT}")
    console.print()

    while True:
        try:
            choice = int(console.input("  > 请选择 (0-5): ").strip())
            if 0 <= choice <= 5:
                return choice
        except (ValueError, EOFError):
            pass
        console.print("  [red]无效输入[/red]")


def create_game(choice: int):
    """Create game based on menu choice."""
    is_sanma = choice in (3, 4)
    is_tonpuu = choice in (2, 4)
    is_spectator = choice == 5
    num_players = 3 if is_sanma else 4

    config = GameConfig(
        num_players=num_players,
        is_sanma=is_sanma,
        is_tonpuu=is_tonpuu,
    )

    event_bus = EventBus()
    renderer = Renderer(console, event_bus, human_seat=0)

    # Create players
    ai_names = ["电脑A", "电脑B", "电脑C"]
    if is_spectator:
        player_names = ["AI-东", "AI-南", "AI-西"]
        if not is_sanma:
            player_names.append("AI-北")
        players = {name: GreedyAI(name) for name in player_names}
    else:
        player_name = "你"
        player_names = [player_name] + ai_names[:num_players - 1]
        human = HumanPlayer(player_name, console, renderer)
        players = {player_name: human}
        for name in ai_names[:num_players - 1]:
            players[name] = GreedyAI(name)

    return config, event_bus, renderer, player_names, players, is_spectator


def play_game(choice: int):
    """Play a complete game."""
    config, event_bus, renderer, player_names, players, is_spectator = create_game(choice)

    game = GameState(config, player_names, event_bus)

    event_bus.emit(GameEvent(EventType.GAME_START, {
        "config": config,
        "players": [(p.name, p.score) for p in game.players],
    }))

    console.print(f"\n  [bold]{MSG_GAME_START}[/bold]")
    render_scores(console, [(p.name, p.score) for p in game.players])

    if not is_spectator:
        renderer.pause()

    round_count = 0

    while not game.is_finished:
        round_state = game.setup_round()
        console.print(f"\n  [bold cyan]{'='*50}[/bold cyan]")
        console.print(f"  [bold]{game.round_label}[/bold]")

        def get_action(player_idx, available):
            """Route action requests to appropriate player."""
            p_name = player_names[player_idx]
            player = players[p_name]

            if isinstance(player, HumanPlayer):
                # Build game view for human
                gv = build_game_view(
                    player_idx, game.players,
                    game.round_wind, game.honba, game.riichi_sticks,
                    round_state.wall.remaining,
                    round_state.wall.dora_indicators,
                    game.round_label,
                    round_state.last_discard,
                    round_state.last_discard_player,
                )
                return player.choose_action(gv, available)
            else:
                # AI player
                gv = build_game_view(
                    player_idx, game.players,
                    game.round_wind, game.honba, game.riichi_sticks,
                    round_state.wall.remaining,
                    round_state.wall.dora_indicators,
                    game.round_label,
                    round_state.last_discard,
                    round_state.last_discard_player,
                )
                return player.choose_action(gv, available)

        result = run_round(round_state, get_action)

        if result is None:
            console.print("  [red]局异常结束[/red]")
            break

        # Show round result
        _show_round_result(game, result, player_names, is_spectator)

        game.advance_round(result)
        round_count += 1

        if not game.is_finished:
            render_scores(console, [(p.name, p.score) for p in game.players])
            if not is_spectator:
                renderer.pause()

    # Game end
    render_game_end(console, [(p.name, p.score) for p in game.players])


def _show_round_result(game, result, player_names, is_spectator):
    """Display the result of a round."""
    if result.is_draw:
        if result.draw_type == "exhaustive":
            tenpai_info = [
                (player_names[i], i in result.tenpai_players)
                for i in range(len(player_names))
            ]
            render_draw_screen(console, result.draw_type, tenpai_info)
        else:
            render_draw_screen(console, result.draw_type)
    else:
        for winner_idx, score_result in result.score_results:
            winner_name = player_names[winner_idx]
            is_tsumo = score_result.is_tsumo
            loser_name = player_names[result.loser] if result.loser is not None else ""
            render_win_screen(console, winner_name, score_result,
                              is_tsumo, loser_name)

    # Show all players' hands
    render_round_end_hands(
        console, game.players, player_names,
        result.winners, result.loser,
    )

    # Show score changes
    console.print("  得分变化:")
    for i in range(len(player_names)):
        change = result.score_changes[i]
        if change != 0:
            sign = "+" if change > 0 else ""
            style = "green" if change > 0 else "red"
            console.print(f"    {player_names[i]}: [{style}]{sign}{change}[/{style}]")


def main():
    """Main entry point."""
    try:
        while True:
            choice = show_menu()
            if choice == 0:
                console.print("\n  再见！\n")
                break
            play_game(choice)
            console.print()
    except KeyboardInterrupt:
        console.print("\n\n  [dim]游戏已退出[/dim]\n")
    except EOFError:
        console.print("\n\n  [dim]游戏已退出[/dim]\n")


if __name__ == "__main__":
    main()
