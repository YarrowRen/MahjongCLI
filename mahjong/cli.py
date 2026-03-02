#!/usr/bin/env python3
"""Japanese Riichi Mahjong - Terminal CLI Game

This is the package entry point, invoked by the `riichi` console command.
"""

import time

from rich.console import Console
from rich.panel import Panel

from mahjong.engine.event import EventBus, EventType, GameEvent
from mahjong.engine.game import GameConfig, GameState
from mahjong.engine.round import run_round
from mahjong.player.base import build_game_view
from mahjong.player.greedy_ai import GreedyAI
from mahjong.player.human import HumanPlayer
from mahjong.ui.renderer import Renderer
from mahjong.ui.board_layout import (
    render_win_screen, render_draw_screen, render_scores, render_game_end,
    render_round_end_hands
)
from mahjong.engine.game_logger import GameLogger
from mahjong.engine.time_control import TIME_CONTROL_PRESETS, TimeControl
from mahjong.engine.ai_delay import AI_DELAY_PRESETS, AIDelay
from mahjong.ui.i18n import t, set_language, get_language

console = Console()


def _change_language():
    """Language selection sub-screen."""
    console.print(f"\n  {t('lang.select')}")
    console.print(f"    1. {t('lang.zh')}")
    console.print(f"    2. {t('lang.ja')}")
    console.print(f"    3. {t('lang.en')}")
    console.print()

    while True:
        try:
            choice = int(console.input("  > 1/2/3: ").strip())
            if choice == 1:
                set_language("zh")
                return
            elif choice == 2:
                set_language("ja")
                return
            elif choice == 3:
                set_language("en")
                return
        except (ValueError, EOFError):
            pass
        console.print("  [red]Invalid / 无效 / 無効[/red]")


def _choose_time_control(current: TimeControl) -> TimeControl:
    """Time control selection sub-screen. Returns new selection."""
    console.print(f"\n  {t('tc.select')}")
    for i, tc in enumerate(TIME_CONTROL_PRESETS):
        marker = " *" if tc is current else ""
        console.print(f"    {i}. {t(tc.name)}{marker}")
    console.print()

    while True:
        try:
            idx = int(console.input(
                f"  > {t('prompt.choose_mode', n=len(TIME_CONTROL_PRESETS) - 1)} "
            ).strip())
            if 0 <= idx < len(TIME_CONTROL_PRESETS):
                return TIME_CONTROL_PRESETS[idx]
        except (ValueError, EOFError):
            pass
        console.print(f"  [red]{t('prompt.invalid_input')}[/red]")


def _choose_ai_delay(current: AIDelay) -> AIDelay:
    """AI delay selection sub-screen. Returns new selection."""
    console.print(f"\n  {t('ai_delay.select')}")
    for i, d in enumerate(AI_DELAY_PRESETS):
        marker = " *" if d is current else ""
        console.print(f"    {i}. {t(d.name)}{marker}")
    console.print()

    while True:
        try:
            idx = int(console.input(
                f"  > {t('prompt.choose_mode', n=len(AI_DELAY_PRESETS) - 1)} "
            ).strip())
            if 0 <= idx < len(AI_DELAY_PRESETS):
                return AI_DELAY_PRESETS[idx]
        except (ValueError, EOFError):
            pass
        console.print(f"  [red]{t('prompt.invalid_input')}[/red]")


def show_settings(current_time_control: TimeControl,
                  current_ai_delay: AIDelay) -> tuple[TimeControl, AIDelay]:
    """Show settings submenu. Returns (possibly updated) time control and ai delay."""
    while True:
        lang_name = t(f"lang.{get_language()}")
        tc_name = t(current_time_control.name)
        delay_name = t(current_ai_delay.name)

        console.print()
        console.print(Panel(
            f"[bold]{t('settings.title')}[/bold]\n"
            f"[dim]{t('settings.current_lang', lang=lang_name)}[/dim]\n"
            f"[dim]{t('settings.current_time', tc=tc_name)}[/dim]\n"
            f"[dim]{t('settings.current_ai_delay', delay=delay_name)}[/dim]",
            border_style="dim",
            padding=(0, 4),
        ))
        console.print()
        console.print(f"    1. {t('settings.change_lang')}")
        console.print(f"    2. {t('settings.change_time')}")
        console.print(f"    3. {t('settings.change_ai_delay')}")
        console.print(f"    0. {t('settings.back')}")
        console.print()

        while True:
            try:
                choice = int(console.input(f"  > {t('prompt.choose_mode', n=3)} ").strip())
                if 0 <= choice <= 3:
                    break
            except (ValueError, EOFError):
                pass
            console.print(f"  [red]{t('prompt.invalid_input')}[/red]")

        if choice == 0:
            return current_time_control, current_ai_delay
        elif choice == 1:
            _change_language()
        elif choice == 2:
            current_time_control = _choose_time_control(current_time_control)
        elif choice == 3:
            current_ai_delay = _choose_ai_delay(current_ai_delay)


def show_menu() -> int:
    """Show mode selection menu and return choice."""
    console.print()
    console.print(Panel(
        f"[bold cyan]{t('label.game_title')}[/bold cyan]\n"
        f"[dim]{t('label.subtitle')}[/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()
    console.print(f"  {t('mode.select')}")
    console.print(f"    1. {t('mode.4p')}")
    console.print(f"    2. {t('mode.4p_tonpuu')}")
    console.print(f"    3. {t('mode.3p')}")
    console.print(f"    4. {t('mode.3p_tonpuu')}")
    console.print(f"    5. {t('mode.spectator')}")
    console.print(f"    6. {t('mode.settings')}")
    console.print(f"    0. {t('mode.quit')}")
    console.print()

    while True:
        try:
            choice = int(console.input(f"  > {t('prompt.choose_mode', n=6)} ").strip())
            if 0 <= choice <= 6:
                return choice
        except (ValueError, EOFError):
            pass
        console.print(f"  [red]{t('prompt.invalid_input')}[/red]")


def create_game(choice: int, time_control: TimeControl = None):
    """Create game based on menu choice."""
    is_sanma = choice in (3, 4)
    is_tonpuu = choice in (2, 4)
    is_spectator = choice == 5
    num_players = 3 if is_sanma else 4

    config = GameConfig(
        num_players=num_players,
        is_sanma=is_sanma,
        is_tonpuu=is_tonpuu,
        time_control=time_control,
    )

    event_bus = EventBus()
    renderer = Renderer(console, event_bus, human_seat=0)

    # Create players
    ai_names = [t('ai.name_a'), t('ai.name_b'), t('ai.name_c')]
    if is_spectator:
        player_names = [
            t('ai.spectator.east'), t('ai.spectator.south'), t('ai.spectator.west')
        ]
        if not is_sanma:
            player_names.append(t('ai.spectator.north'))
        players = {name: GreedyAI(name) for name in player_names}
    else:
        player_name = t('label.you')
        player_names = [player_name] + ai_names[:num_players - 1]
        human = HumanPlayer(player_name, console, renderer, time_control)
        players = {player_name: human}
        for name in ai_names[:num_players - 1]:
            players[name] = GreedyAI(name)

    return config, event_bus, renderer, player_names, players, is_spectator


def play_game(choice: int, time_control: TimeControl, ai_delay: AIDelay):
    """Play a complete game."""
    is_spectator = choice == 5
    config, event_bus, renderer, player_names, players, is_spectator = create_game(
        choice, time_control if not is_spectator else None
    )

    game = GameState(config, player_names, event_bus)

    # Initialize game logger
    logger = GameLogger(player_names, {
        "num_players": config.num_players,
        "is_sanma": config.is_sanma,
        "is_tonpuu": config.is_tonpuu,
        "starting_score": config.starting_score,
    })
    logger.subscribe_events(event_bus)

    event_bus.emit(GameEvent(EventType.GAME_START, {
        "config": config,
        "players": [(p.name, p.score) for p in game.players],
    }))

    console.print(f"\n  [bold]{t('msg.game_start')}[/bold]")
    console.print(f"  [dim]{t('msg.session_id', id=logger.session_id)}[/dim]")
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

            if isinstance(player, GreedyAI):
                # Render current board state (from seat-0 perspective) before AI thinks,
                # so the human sees each board update immediately (e.g. their own discard,
                # previous AI discard) rather than waiting until their next turn.
                gv_render = build_game_view(
                    0, game.players,
                    game.round_wind, game.honba, game.riichi_sticks,
                    round_state.wall.remaining,
                    round_state.wall.dora_indicators,
                    game.round_label,
                    round_state.last_discard,
                    round_state.last_discard_player,
                )
                renderer.render_game_view(gv_render)
                time.sleep(ai_delay.get_delay())

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
            console.print(f"  [red]{t('msg.round_error')}[/red]")
            break

        logger.end_round(result)

        # Show round result
        _show_round_result(game, result, player_names)

        game.advance_round(result)
        round_count += 1

        if not game.is_finished:
            render_scores(console, [(p.name, p.score) for p in game.players])
            if not is_spectator:
                renderer.pause()

    # Game end
    render_game_end(console, [(p.name, p.score) for p in game.players])

    # Save game log
    final_scores = {p.name: p.score for p in game.players}
    log_path = logger.save(final_scores)
    console.print(f"  [dim]{t('msg.log_saved', path=log_path)}[/dim]")


def _show_round_result(game, result, player_names):
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
    console.print(f"  {t('label.score_changes')}")
    for i in range(len(player_names)):
        change = result.score_changes[i]
        if change != 0:
            sign = "+" if change > 0 else ""
            style = "green" if change > 0 else "red"
            console.print(f"    {player_names[i]}: [{style}]{sign}{change}[/{style}]")


def main():
    """Main entry point."""
    try:
        set_language("zh")
        time_control = TIME_CONTROL_PRESETS[0]  # default: unlimited
        ai_delay = AI_DELAY_PRESETS[0]          # default: 1s
        while True:
            choice = show_menu()
            if choice == 0:
                console.print(f"\n  {t('msg.goodbye')}\n")
                break
            elif choice == 6:
                time_control, ai_delay = show_settings(time_control, ai_delay)
                continue
            play_game(choice, time_control, ai_delay)
            console.print()
    except KeyboardInterrupt:
        console.print(f"\n\n  [dim]{t('msg.game_exit')}[/dim]\n")
    except EOFError:
        console.print(f"\n\n  [dim]{t('msg.game_exit')}[/dim]\n")
