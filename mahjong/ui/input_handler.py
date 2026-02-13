"""User input handling for the terminal UI."""

from typing import List, Optional

from rich.console import Console

from mahjong.core.tile import Tile
from mahjong.engine.action import Action, ActionType, AvailableActions
from mahjong.core.meld import Meld
from mahjong.ui.tile_display import tile_to_display_str
from mahjong.ui.i18n import t


def get_player_input(console: Console, game_view, available: AvailableActions) -> Action:
    """Get action from human player via terminal input."""
    player_idx = available.player
    allowed_set = set(tile.id for tile in available.can_discard)

    # Riichi: only tsumogiri allowed — pause to show board, then auto-discard
    if game_view.my_hand.is_riichi and available.can_discard:
        if not available.can_tsumo and not available.can_ankan and not available.can_kita:
            tile = available.can_discard[0]
            console.print(f"  {t('msg.riichi_tsumogiri')} [bold]{tile_to_display_str(tile)}[/bold]")
            console.input(f"  > {t('prompt.press_enter')}")
            return Action(ActionType.DISCARD, player_idx, tile=tile)

    # If only discard is available (and nothing else special)
    if not available.has_action and available.can_discard:
        return _get_discard_input(console, game_view, available, allowed_set)

    # Show action options
    while True:
        # Check for auto-actions first
        if available.can_tsumo or available.can_ron:
            if available.can_tsumo:
                console.print(f"  {t('action.tsumo')}")
            if available.can_ron:
                console.print(f"  {t('action.ron')}")

        prompt_parts = []
        if available.can_tsumo:
            prompt_parts.append(t('prompt.action_tsumo'))
        if available.can_ron:
            prompt_parts.append(t('prompt.action_ron'))
        if available.can_riichi:
            prompt_parts.append(t('prompt.action_riichi'))
        if available.can_pon:
            prompt_parts.append(t('prompt.action_pon'))
        if available.can_chi:
            prompt_parts.append(t('prompt.action_chi'))
        if available.can_ankan or available.can_shouminkan:
            prompt_parts.append(t('prompt.action_kan'))
        if available.can_kita:
            prompt_parts.append(t('prompt.action_kita'))
        if available.can_kyuushu:
            prompt_parts.append(t('prompt.action_kyuushu'))
        if available.can_discard:
            prompt_parts.append(t('prompt.action_discard'))
        prompt_parts.append(t('prompt.action_skip'))

        prompt = "  > " + " | ".join(prompt_parts) + ": "
        choice = console.input(prompt).strip().lower()

        if choice == 't' and available.can_tsumo:
            return Action(ActionType.TSUMO, player_idx)

        if choice == 'h' and available.can_ron:
            return Action(ActionType.RON, player_idx)

        if choice == 'r' and available.can_riichi:
            # Choose riichi discard
            console.print(f"  {t('prompt.choose_riichi_discard')}")
            for i, tile in enumerate(available.riichi_candidates):
                console.print(f"    {i+1}. {tile_to_display_str(tile)}")
            while True:
                try:
                    idx = int(console.input(f"  > {t('prompt.number')} ").strip()) - 1
                    if 0 <= idx < len(available.riichi_candidates):
                        return Action(ActionType.RIICHI, player_idx,
                                      riichi_discard=available.riichi_candidates[idx])
                except ValueError:
                    pass
                console.print(f"  [red]{t('prompt.invalid_input')}[/red]")

        if choice == 'p' and available.can_pon:
            if len(available.can_pon) == 1:
                return Action(ActionType.PON, player_idx, meld=available.can_pon[0])
            return Action(ActionType.PON, player_idx, meld=available.can_pon[0])

        if choice == 'c' and available.can_chi:
            if len(available.can_chi) == 1:
                return Action(ActionType.CHI, player_idx, meld=available.can_chi[0])
            console.print(f"  {t('prompt.choose_chi')}")
            for i, meld in enumerate(available.can_chi):
                tiles_str = " ".join(tile_to_display_str(tile) for tile in meld.tiles)
                console.print(f"    {i+1}. {tiles_str}")
            while True:
                try:
                    idx = int(console.input(f"  > {t('prompt.number')} ").strip()) - 1
                    if 0 <= idx < len(available.can_chi):
                        return Action(ActionType.CHI, player_idx,
                                      meld=available.can_chi[idx])
                except ValueError:
                    pass
                console.print(f"  [red]{t('prompt.invalid_input')}[/red]")

        if choice == 'k':
            if available.can_ankan:
                return Action(ActionType.ANKAN, player_idx,
                              tile=available.can_ankan[0][0])
            if available.can_shouminkan:
                return Action(ActionType.SHOUMINKAN, player_idx,
                              tile=available.can_shouminkan[0])
            if available.can_daiminkan:
                return Action(ActionType.DAIMINKAN, player_idx,
                              meld=available.can_daiminkan[0])

        if choice == 'n' and available.can_kita:
            return Action(ActionType.KITA, player_idx)

        if choice == '9' and available.can_kyuushu:
            return Action(ActionType.KYUUSHU, player_idx)

        if choice == 's':
            if available.can_discard:
                return _get_discard_input(console, game_view, available, allowed_set)
            return Action(ActionType.SKIP, player_idx)

        # Try as number for discard
        if available.can_discard:
            try:
                idx = int(choice) - 1
                tiles = _get_sorted_display_tiles(game_view)
                if 0 <= idx < len(tiles):
                    tile = tiles[idx]
                    if tile.id in allowed_set:
                        return Action(ActionType.DISCARD, player_idx, tile=tile)
                    else:
                        console.print(f"  [red]{t('msg.riichi_only_tsumogiri')}[/red]")
                        continue
            except ValueError:
                pass

        console.print(f"  [red]{t('prompt.invalid_retry')}[/red]")


def _get_discard_input(console: Console, game_view, available: AvailableActions,
                       allowed_set: set) -> Action:
    """Get discard tile selection, validating against allowed tiles."""
    tiles = _get_sorted_display_tiles(game_view)
    n = len(tiles)

    prompt = f"  > {t('prompt.choose_discard', n=n)} "
    while True:
        choice = console.input(prompt).strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < n:
                tile = tiles[idx]
                if tile.id in allowed_set:
                    return Action(ActionType.DISCARD, available.player, tile=tile)
                else:
                    console.print(f"  [red]{t('msg.riichi_only_tsumogiri')}[/red]")
                    continue
        except ValueError:
            pass
        console.print(f"  [red]{t('prompt.invalid_input')}[/red]")


def _get_sorted_display_tiles(game_view) -> list:
    """Get tiles in display order (sorted, draw tile last)."""
    hand = game_view.my_hand
    draw_tile = hand.draw_tile

    display = []
    for tile in hand.closed_tiles:
        if tile == draw_tile:
            continue
        display.append(tile)
    display.sort()

    if draw_tile:
        display.append(draw_tile)

    return display
