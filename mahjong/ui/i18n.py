"""Internationalization support for the mahjong game.

Usage:
    from mahjong.ui.i18n import t, set_language, translate_yaku

    set_language("en")          # Switch to English
    t("msg.game_start")         # -> "Game Start!"
    t("msg.tsumo_win", player="You")  # -> "You wins by Tsumo!"
    translate_yaku("立直")       # -> "Riichi"
"""


class I18n:
    """Singleton internationalization manager."""

    _lang: str = "zh"
    _translations: dict = {}
    _loaded: bool = False

    @classmethod
    def set_language(cls, lang: str):
        """Set the active language."""
        cls._lang = lang
        cls._load_translations()

    @classmethod
    def _load_translations(cls):
        """Load translations for the current language."""
        if cls._lang == "ja":
            from mahjong.ui.locales.ja import TRANSLATIONS
        elif cls._lang == "en":
            from mahjong.ui.locales.en import TRANSLATIONS
        else:
            from mahjong.ui.locales.zh import TRANSLATIONS
        cls._translations = TRANSLATIONS
        cls._loaded = True

    @classmethod
    def get(cls, key: str, **kwargs) -> str:
        """Get a translated string by key, with optional format arguments."""
        if not cls._loaded:
            cls._load_translations()
        text = cls._translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text

    @classmethod
    def get_language(cls) -> str:
        """Get the current language code."""
        return cls._lang


def t(key: str, **kwargs) -> str:
    """Global translation function."""
    return I18n.get(key, **kwargs)


def set_language(lang: str):
    """Set the active language."""
    I18n.set_language(lang)


def get_language() -> str:
    """Get the current language code."""
    return I18n.get_language()


def translate_yaku(yaku_name: str) -> str:
    """Translate a yaku name from its Japanese key to the current language."""
    return I18n.get(f"yaku.{yaku_name}")


def get_draw_message(draw_type: str) -> str:
    """Get the localized draw message for a draw type."""
    key_map = {
        "exhaustive": "draw.exhaustive",
        "4wind": "draw.4wind",
        "4kan": "draw.4kan",
        "4riichi": "draw.4riichi",
        "kyuushu": "draw.kyuushu",
        "triple_ron": "draw.triple_ron",
    }
    key = key_map.get(draw_type, "draw.exhaustive")
    return t(key)
