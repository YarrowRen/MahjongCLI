"""Localized label construction for engine-level objects.

Keeps i18n strictly inside the UI layer: core/engine/rules objects expose
stable data only (Wind.kanji, han/fu numbers, round numbers); these
helpers translate them for display.
"""

from mahjong.core.player_state import Wind
from mahjong.ui.i18n import t

_WIND_KEYS = ['wind.east', 'wind.south', 'wind.west', 'wind.north']


def wind_display(wind: Wind) -> str:
    """Localized wind name (東/南/西/北 in the current language)."""
    return t(_WIND_KEYS[wind.value])


def round_label(round_wind: Wind, round_number: int, honba: int = 0) -> str:
    """Human-readable round label like '東一局 1本場' (localized)."""
    wind = wind_display(round_wind)
    number = t(f'round.numbers.{round_number}')
    label = t('round.format', wind=wind, number=number)
    honba_str = t('round.honba', n=honba) if honba > 0 else ""
    return f"{label}{honba_str}"


def rank_display(score_result) -> str:
    """Localized score rank name ('满贯', '跳满', '3翻30符', ...)."""
    han, fu = score_result.han, score_result.fu
    if han >= 13:
        return t("rank.yakuman")
    if han >= 11:
        return t("rank.sanbaiman")
    if han >= 8:
        return t("rank.baiman")
    if han >= 6:
        return t("rank.haneman")
    if han >= 5 or (han >= 4 and fu >= 30) or (han >= 3 and fu >= 60):
        return t("rank.mangan")
    return t("rank.han_fu", han=han, fu=fu)
