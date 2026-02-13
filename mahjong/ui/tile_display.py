"""Tile display formatting with colors for terminal output."""

from rich.text import Text

from mahjong.core.tile import Tile, TileSuit, TILE_NAMES_34


# Internal short names (stable, language-independent, used by game_logger)
TILE_SHORT_NAMES = [
    "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
    "東", "南", "西", "北", "白", "發", "中",
]


def get_tile_short_names() -> list:
    """Get localized tile short names for display.

    Number tiles (1m-9s) are universal. Honor tiles are translated.
    """
    from mahjong.ui.i18n import t
    return [
        "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
        "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
        "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
        t("tile.east"), t("tile.south"), t("tile.west"), t("tile.north"),
        t("tile.haku"), t("tile.hatsu"), t("tile.chun"),
    ]


# Color schemes
SUIT_COLORS = {
    TileSuit.MAN: "red",
    TileSuit.PIN: "blue",
    TileSuit.SOU: "green",
    TileSuit.WIND: "yellow",
    TileSuit.DRAGON: "yellow",
}


def _tile_display_width(name: str) -> int:
    """Calculate the display width of a tile name, accounting for fullwidth chars."""
    w = 0
    for ch in name:
        if '\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u30ff' or '\uff00' <= ch <= '\uffef':
            w += 2  # Fullwidth character
        else:
            w += 1
    return w


def tile_to_rich_text(tile: Tile, highlight: bool = False) -> Text:
    """Convert a tile to a Rich Text object with appropriate colors."""
    names = get_tile_short_names()
    if tile.is_red:
        suit_char = {TileSuit.MAN: 'm', TileSuit.PIN: 'p', TileSuit.SOU: 's'}
        name = f"0{suit_char[tile.suit]}"
        style = "bold red on white"
    else:
        name = names[tile.index34]
        color = SUIT_COLORS[tile.suit]
        style = f"bold {color}"
        if highlight:
            style += " on white"

    return Text(f"[{name}]", style=style)


def tile_to_simple_str(tile: Tile) -> str:
    """Simple string representation of a tile (stable, for logging)."""
    if tile.is_red:
        suit_char = {TileSuit.MAN: 'm', TileSuit.PIN: 'p', TileSuit.SOU: 's'}
        return f"0{suit_char[tile.suit]}"
    return TILE_SHORT_NAMES[tile.index34]


def tile_to_display_str(tile: Tile) -> str:
    """Localized string representation of a tile (for UI display)."""
    names = get_tile_short_names()
    if tile.is_red:
        suit_char = {TileSuit.MAN: 'm', TileSuit.PIN: 'p', TileSuit.SOU: 's'}
        return f"0{suit_char[tile.suit]}"
    return names[tile.index34]


def tiles_to_rich_text(tiles: list, separator: str = " ") -> Text:
    """Convert a list of tiles to Rich Text."""
    result = Text()
    for i, tile in enumerate(tiles):
        if i > 0:
            result.append(separator)
        result.append_text(tile_to_rich_text(tile))
    return result


def format_discard_pool(tiles: list, called: list = None,
                        riichi_index: int = -1) -> Text:
    """Format a discard pool with called tiles marked."""
    result = Text()
    for i, tile in enumerate(tiles):
        if i > 0:
            result.append(" ")
        t = tile_to_rich_text(tile)
        if called and i < len(called) and called[i]:
            # Tile was called - show with strikethrough
            t.stylize("dim")
        if i == riichi_index:
            # Riichi declaration tile - show sideways (indicated by parentheses)
            t = Text("(", style="bold") + t + Text(")", style="bold")
        result.append_text(t)
    return result
