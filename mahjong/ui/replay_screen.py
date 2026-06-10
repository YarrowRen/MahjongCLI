"""Interactive replay browser - step through logged games.

Entry point: show_replay_browser(console), wired to the main menu.
God view: all hands are visible (it is a record of a finished game).
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mahjong.core.player_state import Wind
from mahjong.replay.loader import GameSummary, list_game_logs, load_game
from mahjong.replay.state import RoundReplay, parse_tile_str
from mahjong.ui.board_layout import _render_melds_line
from mahjong.ui.i18n import t, translate_yaku, get_draw_message
from mahjong.ui.labels import wind_display
from mahjong.ui.tile_display import (
    tile_to_rich_text, tiles_to_rich_text, tile_to_display_str,
    format_discard_pool,
)

_KANJI_TO_WIND = {"東": Wind.EAST, "南": Wind.SOUTH,
                  "西": Wind.WEST, "北": Wind.NORTH}


def show_replay_browser(console: Console):
    """Top level: pick a logged game, then browse its rounds."""
    while True:
        summaries = list_game_logs()
        if not summaries:
            console.print(f"\n  [yellow]{t('replay.no_logs')}[/yellow]")
            return

        console.print(f"\n  [bold]{t('replay.title')}[/bold]")
        for i, s in enumerate(summaries):
            console.print(f"    {i + 1}. {_game_line(s)}")
        console.print(f"    0. {t('replay.back')}")

        idx = _read_index(console, t('replay.select_game'), len(summaries))
        if idx is None or idx == 0:
            return
        _browse_game(console, summaries[idx - 1])


def _game_line(s: GameSummary) -> str:
    """One list row: time, players with final scores, round count."""
    when = s.timestamp[:16].replace("T", " ")
    scores = " ".join(
        f"{name}({s.final_scores.get(name, '?')})" for name in s.players)
    return f"{when}  {scores}  [{t('replay.rounds_count', n=s.num_rounds)}]"


def _browse_game(console: Console, summary: GameSummary):
    """Round list for one game."""
    data = load_game(summary.path)
    rounds = data.get("rounds", [])
    is_sanma = bool(data.get("config", {}).get("is_sanma"))

    while True:
        console.print(f"\n  [bold]{t('replay.select_round')}[/bold]")
        for i, rd in enumerate(rounds):
            console.print(f"    {i + 1}. {t('replay.round_item', n=i + 1)}"
                          f"  {_round_summary(rd)}")
        console.print(f"    0. {t('replay.back')}")

        idx = _read_index(console, t('replay.select_round'), len(rounds))
        if idx is None or idx == 0:
            return
        _step_through(console, rounds[idx - 1], data["players"], is_sanma)


def _round_summary(round_data: dict) -> str:
    """Short result line for the round list."""
    result = round_data.get("result")
    if not result:
        return ""
    if result.get("is_draw"):
        return get_draw_message(result.get("draw_type") or "exhaustive")
    winners = result.get("winners") or []
    return " ".join(t('replay.winner', player=w) for w in winners)


def _step_through(console: Console, round_data: dict,
                  player_names: list, is_sanma: bool):
    """Step viewer: Enter=next, b=prev, number=jump, q=quit."""
    rr = RoundReplay(round_data, player_names, is_sanma)
    rr.goto(0)

    while True:
        _render_board(console, rr)

        if rr.is_finished:
            _render_result(console, rr)

        console.print(f"  [dim]{t('replay.controls')}[/dim]")
        try:
            raw = console.input(
                f"  {t('replay.step', i=rr.step, n=rr.num_steps)} > ").strip().lower()
        except EOFError:
            return

        if raw == "q":
            return
        elif raw == "b":
            rr.goto(rr.step - 1)
        elif raw.isdigit():
            rr.goto(int(raw))
        else:  # Enter or anything else = next
            if rr.is_finished:
                return
            rr.goto(rr.step + 1)


def _render_board(console: Console, rr: RoundReplay):
    """Render the full god-view board at the current step."""
    console.clear()

    header = Text()
    header.append(f"  {t('label.dora')}: ")
    header.append_text(tiles_to_rich_text(rr.dora_indicators))
    header.append(f"   {t('label.remaining', n=rr.remaining)}")
    console.print(Panel(header, title=f"[bold]{t('replay.title')}[/bold]",
                        border_style="cyan"))

    for p in rr.players:
        _render_player(console, rr, p)

    desc = _action_description(rr)
    if desc:
        console.print(Panel(desc, border_style="yellow", padding=(0, 2)))


def _render_player(console: Console, rr: RoundReplay, p):
    """One player block: header, hand, melds, discards."""
    wind = rr.data["initial_hands"][p.name].get("wind", "")
    wind_str = wind_display(_KANJI_TO_WIND[wind]) if wind in _KANJI_TO_WIND else wind
    dealer = f" ({t('label.dealer_mark')})" if p.is_dealer else ""
    riichi = (f" [bold red]【{t('label.riichi_mark')}】[/bold red]"
              if p.is_riichi else "")
    kita = (f" [yellow]{t('replay.kita_count', n=p.kita_count)}[/yellow]"
            if p.kita_count else "")
    console.print(f"  [bold]{p.name}[/bold] ({wind_str}{dealer}){riichi}{kita}")

    hand_text = Text(f"  {t('label.hand_tiles')} ")
    shown = [tile for tile in p.closed if tile is not p.draw_tile]
    for tile in sorted(shown):
        hand_text.append_text(tile_to_rich_text(tile))
        hand_text.append(" ")
    if p.draw_tile is not None:
        hand_text.append(" ")
        hand_text.append_text(tile_to_rich_text(p.draw_tile, highlight=True))
    console.print(hand_text)

    _render_melds_line(console, [_MeldView(m.tiles) for m in p.melds])

    if p.discards:
        discard_text = Text(f"  {t('label.discards')} ")
        discard_text.append_text(format_discard_pool(
            p.discards, p.discard_called, p.riichi_index))
        console.print(discard_text)
    console.print()


class _MeldView:
    """Adapter: _render_melds_line expects objects with a .tiles attribute."""

    def __init__(self, tiles):
        self.tiles = tiles


def _action_description(rr: RoundReplay) -> str:
    """Localized description of the action that produced this state."""
    action = rr.current_action
    if action is None:
        return t('replay.deal')

    kind = action["action"]
    player = action["player"]

    if kind == "draw":
        tile = tile_to_display_str(parse_tile_str(action["tile"]))
        return t('replay.act.draw', player=player, tile=tile)
    if kind == "discard":
        tile = tile_to_display_str(parse_tile_str(action["tile"]))
        key = ('replay.act.discard_tsumogiri' if action.get("tsumogiri")
               else 'replay.act.discard')
        return t(key, player=player, tile=tile)
    if kind in ("chi", "pon", "ankan", "daiminkan", "shouminkan",
                "riichi", "kita", "tsumo"):
        return t(f'replay.act.{kind}', player=player)
    if kind == "ron":
        return t('replay.act.ron', player=player,
                 from_player=action.get("from_player", ""))
    return f"{player}: {kind}"


def _render_result(console: Console, rr: RoundReplay):
    """Result panel at the final step."""
    result = rr.result
    if not result:
        return

    if result.get("is_draw"):
        msg = get_draw_message(result.get("draw_type") or "exhaustive")
        console.print(Panel(f"[bold yellow]{msg}[/bold yellow]",
                            border_style="yellow"))
    else:
        for winner, info in (result.get("yaku") or {}).items():
            table = Table(title=f"{t('replay.winner', player=winner)}  "
                                f"{info['total_points']}{t('label.points_suffix')}",
                          border_style="green")
            table.add_column(t('label.yaku_name'), style="bold")
            table.add_column(t('label.han_count'), justify="right")
            for y in info.get("yaku_list", []):
                table.add_row(translate_yaku(y["name"]),
                              t('label.han_format', han=y["han"]))
            console.print(table)

    changes = result.get("score_changes") or {}
    if any(v != 0 for v in changes.values()):
        console.print(f"  {t('label.score_changes')}")
        for name, change in changes.items():
            if change:
                style = "green" if change > 0 else "red"
                sign = "+" if change > 0 else ""
                console.print(f"    {name}: [{style}]{sign}{change}[/{style}]")
    console.print()


def _read_index(console: Console, prompt: str, max_idx: int):
    """Read an index 0..max_idx; None on EOF."""
    while True:
        try:
            raw = console.input(f"  > {prompt} ").strip()
            idx = int(raw)
            if 0 <= idx <= max_idx:
                return idx
        except ValueError:
            pass
        except EOFError:
            return None
        console.print(f"  [red]{t('prompt.invalid_input')}[/red]")
