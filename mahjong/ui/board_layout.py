"""Board layout rendering using Rich."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

from mahjong.player.base import GameView, OpponentView
from mahjong.core.tile import Tile
from mahjong.core.player_state import PlayerState, Wind
from mahjong.ui.tile_display import (
    tile_to_rich_text, tiles_to_rich_text, format_discard_pool,
    tile_to_display_str, _tile_display_width
)
from mahjong.ui.i18n import t, translate_yaku, get_draw_message
from mahjong.rules.scoring import ScoreResult


def render_board(console: Console, game_view: GameView):
    """Render the full board state."""
    console.clear()

    # Header: round info
    dora_text = tiles_to_rich_text(game_view.dora_indicators)
    header = Text()
    header.append(f"  {game_view.round_label}  {t('label.round_wind')}:{game_view.round_wind.display_name}  {t('label.dora')}: ")
    header.append_text(dora_text)
    header.append(f"\n  {t('label.remaining', n=game_view.remaining_tiles)}")
    header.append(f"  {t('label.riichi_sticks', n=game_view.riichi_sticks)}")

    console.print(Panel(header, title=f"[bold]{t('label.game_title')}[/bold]", border_style="cyan"))

    # Build all-player list sorted by seat wind (東→南→西→北 = turn order)
    _render_all_players(console, game_view)

    # Separator
    console.print("─" * 60, style="dim")

    # Player's hand tiles
    _render_player_hand(console, game_view)


def _render_all_players(console: Console, game_view: GameView):
    """Render all players' info and discard pools in turn order."""
    entries = []

    # Self
    hand = game_view.my_hand
    entries.append({
        'wind': game_view.my_wind,
        'is_self': True,
        'name': t('label.you'),
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

    entries.sort(key=lambda e: e['wind'].value)

    for e in entries:
        _render_player_row(console, e)


def _render_player_row(console: Console, entry: dict):
    """Render one player's header + melds + discard pool."""
    wind_display = entry['wind'].display_name
    dealer_mark = f" ({t('label.dealer_mark')})" if entry['is_dealer'] else ""
    riichi_mark = f" [bold red]【{t('label.riichi_mark')}】[/bold red]" if entry['is_riichi'] else ""

    if entry['is_self']:
        name_display = f"[bold cyan]{t('label.you')}[/bold cyan]"
    else:
        name_display = entry['name']

    pts = t('label.points_suffix')
    console.print(
        f"  {name_display} ({wind_display}{dealer_mark}) "
        f"{entry['score']}{pts}{riichi_mark}"
    )

    # Melds
    if entry['melds']:
        meld_text = Text(f"  {t('label.melds')} ")
        for i, meld in enumerate(entry['melds']):
            if i > 0:
                meld_text.append(" | ")
            meld_text.append_text(tiles_to_rich_text(list(meld.tiles)))
        console.print(meld_text)

    # Discard pool
    if entry['discard_pool']:
        discard_text = Text(f"  {t('label.discards')} ")
        discard_text.append_text(format_discard_pool(
            entry['discard_pool'],
            entry['discard_called'],
            entry['riichi_discard_index'],
        ))
        console.print(discard_text)
    else:
        console.print(f"  {t('label.discards')} ", style="dim")

    console.print()


def _render_player_hand(console: Console, game_view: GameView):
    """Render the player's own hand tiles (cards only, no info header)."""
    hand = game_view.my_hand

    console.print(
        f"  [bold]{t('label.your_hand')}[/bold]"
    )

    # Number labels
    tiles = hand.closed_tiles
    draw_tile = hand.draw_tile

    # Separate drawn tile from rest
    display_tiles = []
    for tile in tiles:
        if tile == draw_tile:
            continue
        display_tiles.append(tile)
    display_tiles.sort()

    # Calculate per-tile column width: each tile displays as "[XX]" or "[X]"
    COL_WIDTH = 5

    # Build tile name strings first to compute padding
    tile_names = []
    for tile in display_tiles:
        name = tile_to_display_str(tile)
        tile_names.append(f"[{name}]")
    if draw_tile:
        name = tile_to_display_str(draw_tile)
        tile_names.append(f"[{name}]")

    # Number row - pad each number to match tile column width
    num_text = Text("  ")
    for i in range(len(display_tiles)):
        cell_width = _tile_display_width(tile_names[i]) + 1
        label = str(i + 1)
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
        num_text.append("  ", style="dim")
        num_text.append(" " * pad_left + label + " " * pad_right, style="dim cyan")

    console.print(num_text)

    # Tile row - pad each tile cell to match column width
    tile_text = Text("  ")
    for i, tile in enumerate(display_tiles):
        tile_text.append_text(tile_to_rich_text(tile))
        display_w = _tile_display_width(tile_names[i])
        gap = COL_WIDTH - display_w
        if gap < 1:
            gap = 1
        tile_text.append(" " * gap)

    if draw_tile:
        tile_text.append(" ")
        tile_text.append_text(tile_to_rich_text(draw_tile, highlight=True))

    console.print(tile_text)

    # Melds
    if hand.melds:
        meld_text = Text(f"  {t('label.melds')} ")
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
        actions.append(t('action.tsumo'))
    if available.can_ron:
        actions.append(t('action.ron'))
    if available.can_riichi:
        actions.append(t('action.riichi'))
    if available.can_pon:
        actions.append(t('action.pon'))
    if available.can_chi:
        actions.append(t('action.chi'))
    if available.can_ankan or available.can_shouminkan:
        actions.append(t('action.kan'))
    if available.can_kita:
        actions.append(t('action.kita'))
    if available.can_kyuushu:
        actions.append(t('action.kyuushu'))

    if actions:
        console.print(f"  {t('prompt.choose_action')} {' '.join(actions)}")


def render_win_screen(console: Console, player_name: str,
                      score_result: ScoreResult, is_tsumo: bool,
                      loser_name: str = ""):
    """Render winning screen with yaku and score details."""
    console.print()
    if is_tsumo:
        console.print(Panel(
            f"[bold green]{t('msg.tsumo_win', player=player_name)}[/bold green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold green]{t('msg.ron_win', player=player_name, loser=loser_name)}[/bold green]",
            border_style="green"
        ))

    # Yaku list
    table = Table(title=t('label.yaku_list'), show_header=True, border_style="cyan")
    table.add_column(t('label.yaku_name'), style="bold")
    table.add_column(t('label.han_count'), justify="right")

    for yaku_name, han in score_result.yaku:
        table.add_row(translate_yaku(yaku_name), t('label.han_format', han=han))

    console.print(table)

    # Score summary
    pts = t('label.points_suffix')
    if score_result.is_yakuman:
        console.print(f"  [bold red]{t('msg.yakuman', points=score_result.total_points)}[/bold red]")
    else:
        console.print(f"  {score_result.rank_name} "
                       f"{score_result.total_points}{pts}")

    console.print()


def render_round_end_hands(console: Console, players: list,
                           player_names: list, winners: list,
                           loser: int = None):
    """Render all players' hands after a round ends (win or draw)."""
    ron_tile = None
    if loser is not None and players[loser].hand.discard_pool:
        ron_tile = players[loser].hand.discard_pool[-1]

    console.print(f"  [bold]{t('label.all_hands')}[/bold]")
    console.print()

    for i, p in enumerate(players):
        hand = p.hand
        wind_display = p.seat_wind.display_name
        is_winner = i in winners

        # Name header
        if is_winner:
            tag = f" [bold green]【{t('label.winner_tag')}】[/bold green]"
        elif i == loser:
            tag = f" [red]【{t('label.loser_tag')}】[/red]"
        else:
            tag = ""

        console.print(f"  {player_names[i]} ({wind_display}){tag}")

        # Hand tiles
        if is_winner and hand.draw_tile:
            display = [tile for tile in hand.closed_tiles if tile != hand.draw_tile]
            display.sort()
            tile_text = Text(f"  {t('label.hand_tiles')} ")
            for tile in display:
                tile_text.append_text(tile_to_rich_text(tile))
                tile_text.append(" ")
            tile_text.append(" ")
            tile_text.append_text(tile_to_rich_text(hand.draw_tile, highlight=True))
            tile_text.append(f" {t('label.tsumo_indicator')}", style="bold green")
            console.print(tile_text)
        elif is_winner and ron_tile:
            display = sorted(hand.closed_tiles)
            tile_text = Text(f"  {t('label.hand_tiles')} ")
            for tile in display:
                tile_text.append_text(tile_to_rich_text(tile))
                tile_text.append(" ")
            tile_text.append(" ")
            tile_text.append_text(tile_to_rich_text(ron_tile, highlight=True))
            tile_text.append(f" {t('label.ron_indicator')}", style="bold green")
            console.print(tile_text)
        else:
            display = sorted(hand.closed_tiles)
            if display:
                tile_text = Text(f"  {t('label.hand_tiles')} ")
                for tile in display:
                    tile_text.append_text(tile_to_rich_text(tile))
                    tile_text.append(" ")
                console.print(tile_text)
            else:
                console.print(f"  {t('label.hand_tiles')} {t('label.none')}", style="dim")

        # Melds
        if hand.melds:
            meld_text = Text(f"  {t('label.melds')} ")
            for j, meld in enumerate(hand.melds):
                if j > 0:
                    meld_text.append(" | ")
                meld_text.append_text(tiles_to_rich_text(list(meld.tiles)))
            console.print(meld_text)

        console.print()


def render_draw_screen(console: Console, draw_type: str,
                       tenpai_players: list = None):
    """Render draw screen."""
    console.print()
    msg = get_draw_message(draw_type)
    console.print(Panel(f"[bold yellow]{msg}[/bold yellow]",
                        border_style="yellow"))

    if tenpai_players is not None and draw_type == "exhaustive":
        for name, is_tenpai in tenpai_players:
            status = t('msg.tenpai') if is_tenpai else t('msg.noten')
            console.print(f"  {name}: {status}")
    console.print()


def render_scores(console: Console, players: list):
    """Render current scores."""
    table = Table(title=t('label.scores_title'), border_style="cyan")
    table.add_column(t('label.player'), style="bold")
    table.add_column(t('label.score'), justify="right")

    pts = t('label.points_suffix')
    for name, score in players:
        style = "green" if score > 0 else "red" if score < 0 else ""
        table.add_row(name, f"{score}{pts}", style=style)

    console.print(table)


def render_game_end(console: Console, players: list):
    """Render final game results."""
    console.print()
    console.print(Panel(f"[bold]{t('msg.game_end')}[/bold]", border_style="gold1"))

    sorted_players = sorted(players, key=lambda x: x[1], reverse=True)

    table = Table(title=t('label.final_scores'), border_style="gold1")
    table.add_column(t('label.rank'), justify="center")
    table.add_column(t('label.player'), style="bold")
    table.add_column(t('label.score'), justify="right")

    pts = t('label.points_suffix')
    for i, (name, score) in enumerate(sorted_players):
        rank = ["🥇", "🥈", "🥉", "4"][i] if i < 4 else str(i + 1)
        style = "bold green" if i == 0 else ""
        table.add_row(rank, name, f"{score}{pts}", style=style)

    console.print(table)
    console.print(f"\n  {t('msg.winner', player=sorted_players[0][0])}")
    console.print()
