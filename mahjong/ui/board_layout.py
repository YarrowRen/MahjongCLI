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
    tile_to_rich_text, tiles_to_rich_text, format_discard_pool,
    tile_to_simple_str, _tile_display_width
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

    # Build all-player list sorted by seat wind (東→南→西→北 = turn order)
    _render_all_players(console, game_view)

    # Separator
    console.print("─" * 60, style="dim")

    # Player's hand tiles
    _render_player_hand(console, game_view)


def _render_all_players(console: Console, game_view: GameView):
    """Render all players' info and discard pools in turn order (東→南→西→北)."""
    # Collect all players into a unified list: (wind_value, is_self, data)
    entries = []

    # Self
    hand = game_view.my_hand
    entries.append({
        'wind': game_view.my_wind,
        'is_self': True,
        'name': '你',
        'score': game_view.my_score,
        'is_dealer': game_view.is_dealer,
        'is_riichi': hand.is_riichi,
        'melds': hand.melds,
        'discard_pool': hand.discard_pool,
        'discard_called': hand.discard_called,
        'riichi_discard_index': hand.riichi_discard_index,
    })

    # Opponents
    for opp in game_view.opponents:
        entries.append({
            'wind': opp.seat_wind,
            'is_self': False,
            'name': opp.name,
            'score': opp.score,
            'is_dealer': opp.is_dealer,
            'is_riichi': opp.is_riichi,
            'melds': opp.melds,
            'discard_pool': opp.discard_pool,
            'discard_called': opp.discard_called,
            'riichi_discard_index': -1,
        })

    # Sort by wind value: 東(0) → 南(1) → 西(2) → 北(3)
    entries.sort(key=lambda e: e['wind'].value)

    for e in entries:
        _render_player_row(console, e)


def _render_player_row(console: Console, entry: dict):
    """Render one player's header + melds + discard pool."""
    wind_kanji = entry['wind'].kanji
    dealer_mark = " (庄)" if entry['is_dealer'] else ""
    riichi_mark = " [bold red]【立直!】[/bold red]" if entry['is_riichi'] else ""

    if entry['is_self']:
        name_display = f"[bold cyan]你[/bold cyan]"
    else:
        name_display = entry['name']

    console.print(
        f"  {name_display} ({wind_kanji}{dealer_mark}) "
        f"{entry['score']}点{riichi_mark}"
    )

    # Melds
    if entry['melds']:
        meld_text = Text("  副露: ")
        for i, meld in enumerate(entry['melds']):
            if i > 0:
                meld_text.append(" | ")
            meld_text.append_text(tiles_to_rich_text(list(meld.tiles)))
        console.print(meld_text)

    # Discard pool
    if entry['discard_pool']:
        discard_text = Text("  弃牌: ")
        discard_text.append_text(format_discard_pool(
            entry['discard_pool'],
            entry['discard_called'],
            entry['riichi_discard_index'],
        ))
        console.print(discard_text)
    else:
        console.print("  弃牌: ", style="dim")

    console.print()


def _render_player_hand(console: Console, game_view: GameView):
    """Render the player's own hand tiles (cards only, no info header)."""
    hand = game_view.my_hand

    console.print(
        f"  [bold]你的手牌[/bold]"
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

    # Calculate per-tile column width: each tile displays as "[XX]" or "[X]"
    # We need both rows to use the same column widths for alignment.
    COL_WIDTH = 5  # Fixed display column width per tile slot

    # Build tile name strings first to compute padding
    tile_names = []
    for t in display_tiles:
        name = tile_to_simple_str(t)
        tile_names.append(f"[{name}]")
    if draw_tile:
        name = tile_to_simple_str(draw_tile)
        tile_names.append(f"[{name}]")

    # Number row - pad each number to match tile column width
    num_text = Text("  ")
    for i in range(len(display_tiles)):
        cell_width = _tile_display_width(tile_names[i]) + 1  # +1 for gap
        label = str(i + 1)
        # Center the number within cell_width
        pad_total = cell_width - len(label)
        pad_left = pad_total // 2
        pad_right = pad_total - pad_left
        num_text.append(" " * pad_left + label + " " * pad_right, style="dim")

    if draw_tile:
        idx = len(display_tiles)
        cell_width = _tile_display_width(tile_names[idx]) + 1
        label = str(idx + 1)
        pad_total = cell_width - len(label)
        pad_left = pad_total // 2
        pad_right = pad_total - pad_left
        num_text.append("  ", style="dim")  # gap before draw tile
        num_text.append(" " * pad_left + label + " " * pad_right, style="dim cyan")

    console.print(num_text)

    # Tile row - pad each tile cell to match column width
    tile_text = Text("  ")
    for i, t in enumerate(display_tiles):
        tile_text.append_text(tile_to_rich_text(t))
        display_w = _tile_display_width(tile_names[i])
        gap = COL_WIDTH - display_w
        if gap < 1:
            gap = 1
        tile_text.append(" " * gap)

    if draw_tile:
        tile_text.append(" ")
        tile_text.append_text(tile_to_rich_text(draw_tile, highlight=True))

    console.print(tile_text)

    # Melds (also shown in player row above, but repeat here near hand for convenience)
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
