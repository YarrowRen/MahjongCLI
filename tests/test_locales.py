"""Locale consistency guards.

These tests ensure the three locale files stay in sync and that every
yaku name string produced by the rules engine has a translation key.
"""

from mahjong.ui.locales.zh import TRANSLATIONS as ZH
from mahjong.ui.locales.ja import TRANSLATIONS as JA
from mahjong.ui.locales.en import TRANSLATIONS as EN


# Every yaku name string that yaku.py can return (stable Japanese keys).
ALL_YAKU_NAMES = [
    # 1 han
    "立直", "一発", "門前清自摸和", "断幺九", "平和", "一杯口",
    "自風 東", "自風 南", "自風 西", "自風 北",
    "場風 東", "場風 南", "場風 西", "場風 北",
    "役牌 白", "役牌 發", "役牌 中",
    "海底摸月", "河底撈魚", "嶺上開花", "搶槓",
    # 2+ han
    "両立直", "混全帯幺九", "純全帯幺九", "一気通貫",
    "三色同順", "三色同刻", "対対和", "三暗刻",
    "混老頭", "小三元", "七対子", "二杯口", "混一色", "清一色",
    # yakuman
    "天和", "地和", "国士無双", "四暗刻", "大三元",
    "小四喜", "大四喜", "字一色", "清老頭", "緑一色",
    "九蓮宝燈", "四槓子",
    # dora (counted in yaku list for display)
    "ドラ", "裏ドラ", "赤ドラ",
]


def test_locale_keys_identical_across_languages():
    """All three locale files must define exactly the same key set."""
    zh_keys, ja_keys, en_keys = set(ZH), set(JA), set(EN)
    assert zh_keys == ja_keys, f"zh/ja key mismatch: {zh_keys ^ ja_keys}"
    assert zh_keys == en_keys, f"zh/en key mismatch: {zh_keys ^ en_keys}"


def test_all_yaku_names_have_translation_keys():
    """Every yaku name returned by yaku.py must have a yaku.* key."""
    for lang_name, table in (("zh", ZH), ("ja", JA), ("en", EN)):
        missing = [y for y in ALL_YAKU_NAMES if f"yaku.{y}" not in table]
        assert not missing, f"missing yaku keys in {lang_name}: {missing}"


def test_no_empty_translations():
    """Translation values must be non-empty strings."""
    for lang_name, table in (("zh", ZH), ("ja", JA), ("en", EN)):
        empty = [k for k, v in table.items()
                 if not isinstance(v, str) or not v.strip()]
        assert not empty, f"empty translations in {lang_name}: {empty}"
