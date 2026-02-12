"""Board layout rendering using Rich."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

from mahjong.player.base import GameView, OpponentView
from mahjong.core.tile import Tile
from mahjong.core.player_state import Wind
from mahjong.ui.tile_display import (
    tile_to_rich_text, tiles_to_rich_text, format_discard_pool, tile_to_simple_str
)
from mahjong.ui.i18n import *
from mahjong.rules.scoring import ScoreResult


def render_board(console: Console, game_view: GameView):
    """Render the full board state."""
    console.clear()

    # Header: round info
    dora_text = tiles_to_rich_text(game_view.dora_indicators)
    header = Text()
    header.append(f"  {game_view.round_label}  场风:{game_view.round_wind.kanji}  宝牌: ")
    header.append_text(dora_text)
    header.append(f"\n  {MSG_REMAINING.format(n=game_view.remaining_tiles)}")
    header.append(f"  {MSG_RIICHI_STICKS.format(n=game_view.riichi_sticks)}")

    console.print(Panel(header, title="[bold]日本立直麻将[/bold]", border_style="cyan"))

    # Opponents
    for opp in game_view.opponents:
        _render_opponent(console, opp)

    # Separator
    console.print("─" * 60, style="dim")

    # Player's hand
    _render_player_hand(console, game_view)


def _render_opponent(console: Console, opp: OpponentView):
    """Render an opponent's visible state."""
    riichi_mark = " [bold red]【立直!】[/bold red]" if opp.is_riichi else ""
    dealer_mark = " (庄)" if opp.is_dealer else ""

    header = (f"  {opp.name} ({opp.seat_wind.kanji}{dealer_mark}) "
              f"{opp.score}点{riichi_mark}")

    # Melds
    meld_text = Text()
    if opp.melds:
        meld_text.append("  副露: ")
        for i, meld in enumerate(opp.melds):
            if i > 0:
                meld_text.append(" | ")
            meld_text.append_text(tiles_to_rich_text(list(meld.tiles)))

    # Discard pool
    discard_text = Text("  弃牌: ")
    discard_text.append_text(format_discard_pool(
        opp.discard_pool,
        opp.discard_called,
    ))

    console.print(header)
    if opp.melds:
        console.print(meld_text)
    console.print(discard_text)
    console.print()


def _render_player_hand(console: Console, game_view: GameView):
    """Render the player's own hand."""
    hand = game_view.my_hand
    dealer_mark = " (庄)" if game_view.is_dealer else ""

    console.print(
        f"  [bold]你的手牌[/bold] ({game_view.my_wind.kanji}{dealer_mark}) "
        f"{game_view.my_score}点"
    )

    # Number labels
    tiles = hand.closed_tiles
    draw_tile = hand.draw_tile

    # Separate drawn tile from rest
    display_tiles = []
    for t in tiles:
        if t == draw_tile:
            continue
        display_tiles.append(t)
    display_tiles.sort()

    # Number row
    num_text = Text("  ")
    for i in range(len(display_tiles)):
        num_text.append(f" {i+1:2d} ", style="dim")

    if draw_tile:
        num_text.append("   ", style="dim")
        num_text.append(f" {len(display_tiles)+1:2d} ", style="dim cyan")

    console.print(num_text)

    # Tile row
    tile_text = Text("  ")
    for t in display_tiles:
        tile_text.append_text(tile_to_rich_text(t))
        tile_text.append(" ")

    if draw_tile:
        tile_text.append("  ")
        tile_text.append_text(tile_to_rich_text(draw_tile, highlight=True))

    console.print(tile_text)

    # Melds
    if hand.melds:
        meld_text = Text("  副露: ")
        for i, meld in enumerate(hand.melds):
            if i > 0:
                meld_text.append(" | ")
            meld_text.append_text(tiles_to_rich_text(list(meld.tiles)))
        console.print(meld_text)

    console.print()


def render_action_prompt(console: Console, available):
    """Render available actions."""
    actions = []
    if available.can_tsumo:
        actions.append(MSG_TSUMO)
    if available.can_ron:
        actions.append(MSG_RON)
    if available.can_riichi:
        actions.append(MSG_RIICHI)
    if available.can_pon:
        actions.append(MSG_PON)
    if available.can_chi:
        actions.append(MSG_CHI)
    if available.can_ankan or available.can_shouminkan:
        actions.append(MSG_KAN)
    if available.can_kita:
        actions.append(MSG_KITA)
    if available.can_kyuushu:
        actions.append(MSG_KYUUSHU)

    if actions:
        console.print(f"  {MSG_CHOOSE_ACTION} {' '.join(actions)}")


def render_win_screen(console: Console, player_name: str,
                      score_result: ScoreResult, is_tsumo: bool,
                      loser_name: str = ""):
    """Render winning screen with yaku and score details."""
    console.print()
    if is_tsumo:
        console.print(Panel(
            f"[bold green]{MSG_TSUMO_WIN.format(player=player_name)}[/bold green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold green]{MSG_RON_WIN.format(player=player_name, loser=loser_name)}[/bold green]",
            border_style="green"
        ))

    # Yaku list
    table = Table(title="役种", show_header=True, border_style="cyan")
    table.add_column("役名", style="bold")
    table.add_column("翻数", justify="right")

    for yaku_name, han in score_result.yaku:
        table.add_row(yaku_name, f"{han}翻")

    console.print(table)

    # Score summary
    if score_result.is_yakuman:
        console.print(f"  [bold red]{MSG_YAKUMAN.format(points=score_result.total_points)}[/bold red]")
    else:
        console.print(f"  {score_result.rank_name} "
                       f"{score_result.total_points}点")

    console.print()


def render_draw_screen(console: Console, draw_type: str,
                       tenpai_players: list = None):
    """Render draw screen."""
    console.print()
    msg = ABORTIVE_DRAW_MESSAGES.get(draw_type, MSG_EXHAUSTIVE_DRAW)
    console.print(Panel(f"[bold yellow]{msg}[/bold yellow]",
                        border_style="yellow"))

    if tenpai_players is not None and draw_type == "exhaustive":
        for name, is_tenpai in tenpai_players:
            status = MSG_TENPAI if is_tenpai else MSG_NOTEN
            console.print(f"  {name}: {status}")
    console.print()


def render_scores(console: Console, players: list):
    """Render current scores."""
    table = Table(title="得分", border_style="cyan")
    table.add_column("玩家", style="bold")
    table.add_column("得分", justify="right")

    for name, score in players:
        style = "green" if score > 0 else "red" if score < 0 else ""
        table.add_row(name, f"{score}点", style=style)

    console.print(table)


def render_game_end(console: Console, players: list):
    """Render final game results."""
    console.print()
    console.print(Panel(f"[bold]{MSG_GAME_END}[/bold]", border_style="gold1"))

    # Sort by score
    sorted_players = sorted(players, key=lambda x: x[1], reverse=True)

    table = Table(title=MSG_FINAL_SCORES, border_style="gold1")
    table.add_column("排名", justify="center")
    table.add_column("玩家", style="bold")
    table.add_column("得分", justify="right")

    for i, (name, score) in enumerate(sorted_players):
        rank = ["🥇", "🥈", "🥉", "4"][i] if i < 4 else str(i + 1)
        style = "bold green" if i == 0 else ""
        table.add_row(rank, name, f"{score}点", style=style)

    console.print(table)
    console.print(f"\n  {MSG_WINNER.format(player=sorted_players[0][0])}")
    console.print()
