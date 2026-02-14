"""Yaku (役) detection for Riichi Mahjong.

Each yaku function takes a HandContext and returns (yaku_name, han_value) or None.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set

from mahjong.core.tile import Tile, YAOCHU_INDICES, tiles_to_34_array
from mahjong.core.meld import Meld, MeldType
from mahjong.rules.agari import Decomposition


@dataclass
class HandContext:
    """All information needed to judge yaku."""
    # Decomposition
    head_34: int = -1
    mentsu: List[Tuple[str, int]] = field(default_factory=list)
    # Hand info
    closed_tiles_34: List[int] = field(default_factory=lambda: [0]*34)
    melds: List[Meld] = field(default_factory=list)
    all_tiles_34: List[int] = field(default_factory=lambda: [0]*34)
    # Win info
    win_tile_34: int = -1
    is_tsumo: bool = False
    is_menzen: bool = True
    is_riichi: bool = False
    is_double_riichi: bool = False
    is_ippatsu: bool = False
    # Positional
    seat_wind_34: int = 27
    round_wind_34: int = 27
    # Special conditions
    is_haitei: bool = False  # Last tile from wall
    is_houtei: bool = False  # Last discard
    is_rinshan: bool = False  # After kan draw
    is_chankan: bool = False  # Robbing a kan
    is_tenhou: bool = False  # Dealer first draw
    is_chiihou: bool = False  # Non-dealer first draw
    # Form type
    is_chiitoi: bool = False
    is_kokushi: bool = False
    # Dora
    dora_count: int = 0
    uradora_count: int = 0
    red_dora_count: int = 0

    @property
    def all_mentsu(self) -> List[Tuple[str, int]]:
        """All mentsu including those from melds."""
        result = list(self.mentsu)
        for meld in self.melds:
            if meld.is_kan:
                result.append(('koutsu', meld.tile_index34))
            elif meld.meld_type == MeldType.PON:
                result.append(('koutsu', meld.tile_index34))
            elif meld.meld_type == MeldType.CHI:
                result.append(('shuntsu', min(t.index34 for t in meld.tiles)))
        return result


YakuResult = Tuple[str, int]  # (name, han)


def detect_all_yaku(ctx: HandContext) -> List[YakuResult]:
    """Detect all applicable yaku for the given hand context."""
    results = []

    # Yakuman check first
    yakuman = _check_yakuman(ctx)
    if yakuman:
        return yakuman

    # Regular yaku
    checkers = [
        check_riichi, check_double_riichi, check_ippatsu,
        check_tsumo, check_tanyao, check_pinfu,
        check_iipeikou, check_ryanpeikou,
        check_yakuhai_seat_wind, check_yakuhai_round_wind,
        check_yakuhai_haku, check_yakuhai_hatsu, check_yakuhai_chun,
        check_haitei, check_houtei, check_rinshan, check_chankan,
        check_chanta, check_junchan, check_ittsu,
        check_sanshoku_doujun, check_sanshoku_doukou,
        check_toitoi, check_sanankou,
        check_honroutou, check_shousangen,
        check_chiitoi, check_honitsu, check_chinitsu,
    ]

    for checker in checkers:
        result = checker(ctx)
        if result:
            results.append(result)

    # Dora (not real yaku, but counted for scoring)
    if ctx.dora_count > 0:
        results.append(("ドラ", ctx.dora_count))
    if ctx.uradora_count > 0:
        results.append(("裏ドラ", ctx.uradora_count))
    if ctx.red_dora_count > 0:
        results.append(("赤ドラ", ctx.red_dora_count))

    return results


def _check_yakuman(ctx: HandContext) -> List[YakuResult]:
    """Check for yakuman hands."""
    results = []

    if ctx.is_tenhou:
        results.append(("天和", 13))
    if ctx.is_chiihou:
        results.append(("地和", 13))
    if ctx.is_kokushi:
        results.append(("国士無双", 13))

    r = check_suuankou(ctx)
    if r:
        results.append(r)
    r = check_daisangen(ctx)
    if r:
        results.append(r)
    r = check_shousuushii(ctx)
    if r:
        results.append(r)
    r = check_daisuushii(ctx)
    if r:
        results.append(r)
    r = check_tsuuiisou(ctx)
    if r:
        results.append(r)
    r = check_chinroutou(ctx)
    if r:
        results.append(r)
    r = check_ryuuiisou(ctx)
    if r:
        results.append(r)
    r = check_chuuren(ctx)
    if r:
        results.append(r)
    r = check_suukantsu(ctx)
    if r:
        results.append(r)

    return results


# === 1翻 yaku ===

def check_riichi(ctx: HandContext) -> Optional[YakuResult]:
    if ctx.is_riichi and not ctx.is_double_riichi:
        return ("立直", 1)
    return None

def check_double_riichi(ctx: HandContext) -> Optional[YakuResult]:
    if ctx.is_double_riichi:
        return ("両立直", 2)
    return None

def check_ippatsu(ctx: HandContext) -> Optional[YakuResult]:
    if ctx.is_ippatsu:
        return ("一発", 1)
    return None

def check_tsumo(ctx: HandContext) -> Optional[YakuResult]:
    if ctx.is_tsumo and ctx.is_menzen:
        return ("門前清自摸和", 1)
    return None

def check_tanyao(ctx: HandContext) -> Optional[YakuResult]:
    """All simples (断幺九) - no terminals or honors."""
    for i in range(34):
        if ctx.all_tiles_34[i] > 0 and i in YAOCHU_INDICES:
            return None
    return ("断幺九", 1)

def check_pinfu(ctx: HandContext) -> Optional[YakuResult]:
    """Pinfu - all sequences, non-yakuhai head, ryanmen wait, menzen."""
    if not ctx.is_menzen or ctx.is_chiitoi or ctx.is_kokushi:
        return None

    # All mentsu must be shuntsu
    all_m = ctx.all_mentsu
    if any(m[0] != 'shuntsu' for m in all_m):
        return None

    # Head must not be yakuhai
    head = ctx.head_34
    if head in (31, 32, 33):  # Dragons
        return None
    if head == ctx.seat_wind_34:
        return None
    if head == ctx.round_wind_34:
        return None

    # Must be ryanmen (two-sided) wait
    # The win tile must complete a shuntsu from either end
    win = ctx.win_tile_34
    for m_type, m_idx in ctx.mentsu:
        if m_type != 'shuntsu':
            continue
        if win == m_idx and m_idx % 9 != 6:  # Not 789 low end
            return ("平和", 1)
        if win == m_idx + 2 and m_idx % 9 != 0:  # Not 123 high end
            return ("平和", 1)

    return None


def check_iipeikou(ctx: HandContext) -> Optional[YakuResult]:
    """One set of identical sequences (一杯口). Menzen only."""
    if not ctx.is_menzen:
        return None
    shuntsu = [m[1] for m in ctx.mentsu if m[0] == 'shuntsu']
    pairs = 0
    seen = {}
    for s in shuntsu:
        seen[s] = seen.get(s, 0) + 1
    pairs = sum(v // 2 for v in seen.values())
    if pairs == 1:
        return ("一杯口", 1)
    return None


def check_ryanpeikou(ctx: HandContext) -> Optional[YakuResult]:
    """Two sets of identical sequences (二杯口). Menzen only."""
    if not ctx.is_menzen:
        return None
    shuntsu = [m[1] for m in ctx.mentsu if m[0] == 'shuntsu']
    seen = {}
    for s in shuntsu:
        seen[s] = seen.get(s, 0) + 1
    pairs = sum(v // 2 for v in seen.values())
    if pairs >= 2:
        return ("二杯口", 3)
    return None


def check_yakuhai_seat_wind(ctx: HandContext) -> Optional[YakuResult]:
    for m_type, m_idx in ctx.all_mentsu:
        if m_type == 'koutsu' and m_idx == ctx.seat_wind_34:
            wind_names = {27: "東", 28: "南", 29: "西", 30: "北"}
            return (f"自風 {wind_names.get(m_idx, '')}", 1)
    return None

def check_yakuhai_round_wind(ctx: HandContext) -> Optional[YakuResult]:
    for m_type, m_idx in ctx.all_mentsu:
        if m_type == 'koutsu' and m_idx == ctx.round_wind_34:
            wind_names = {27: "東", 28: "南", 29: "西", 30: "北"}
            return (f"場風 {wind_names.get(m_idx, '')}", 1)
    return None

def check_yakuhai_haku(ctx: HandContext) -> Optional[YakuResult]:
    for m_type, m_idx in ctx.all_mentsu:
        if m_type == 'koutsu' and m_idx == 31:
            return ("役牌 白", 1)
    return None

def check_yakuhai_hatsu(ctx: HandContext) -> Optional[YakuResult]:
    for m_type, m_idx in ctx.all_mentsu:
        if m_type == 'koutsu' and m_idx == 32:
            return ("役牌 發", 1)
    return None

def check_yakuhai_chun(ctx: HandContext) -> Optional[YakuResult]:
    for m_type, m_idx in ctx.all_mentsu:
        if m_type == 'koutsu' and m_idx == 33:
            return ("役牌 中", 1)
    return None


def check_haitei(ctx: HandContext) -> Optional[YakuResult]:
    if ctx.is_haitei and ctx.is_tsumo:
        return ("海底摸月", 1)
    return None

def check_houtei(ctx: HandContext) -> Optional[YakuResult]:
    if ctx.is_houtei and not ctx.is_tsumo:
        return ("河底撈魚", 1)
    return None

def check_rinshan(ctx: HandContext) -> Optional[YakuResult]:
    if ctx.is_rinshan:
        return ("嶺上開花", 1)
    return None

def check_chankan(ctx: HandContext) -> Optional[YakuResult]:
    if ctx.is_chankan:
        return ("搶槓", 1)
    return None


# === 2翻+ yaku ===

def check_chanta(ctx: HandContext) -> Optional[YakuResult]:
    """Mixed outside hand (混全帯幺九). All groups contain terminal or honor."""
    if ctx.is_chiitoi or ctx.is_kokushi:
        return None
    all_m = ctx.all_mentsu
    if len(all_m) == 0:
        return None

    has_honor = False
    has_number = False
    has_shuntsu = False

    for m_type, m_idx in all_m:
        if m_type == 'koutsu':
            if m_idx >= 27:
                has_honor = True
            elif m_idx in YAOCHU_INDICES:
                has_number = True
            else:
                return None
        elif m_type == 'shuntsu':
            has_shuntsu = True
            if m_idx % 9 == 0 or m_idx % 9 == 6:
                has_number = True
            else:
                return None

    # Head must be terminal or honor
    head = ctx.head_34
    if head >= 27:
        has_honor = True
    elif head in YAOCHU_INDICES:
        has_number = True
    else:
        return None

    if not has_honor:
        return None  # Would be junchan instead

    # Also need at least one number tile group (otherwise it's honroutou)
    if not has_number:
        return None
    # Require at least one shuntsu for chanta
    if not has_shuntsu:
        return None

    han = 1 if not ctx.is_menzen else 2
    return ("混全帯幺九", han)


def check_junchan(ctx: HandContext) -> Optional[YakuResult]:
    """Pure outside hand (純全帯幺九). All groups contain terminal, no honor."""
    if ctx.is_chiitoi or ctx.is_kokushi:
        return None
    all_m = ctx.all_mentsu
    if len(all_m) == 0:
        return None

    has_shuntsu = False
    for m_type, m_idx in all_m:
        if m_type == 'koutsu':
            if m_idx >= 27 or m_idx not in YAOCHU_INDICES:
                return None
        elif m_type == 'shuntsu':
            has_shuntsu = True
            if m_idx % 9 != 0 and m_idx % 9 != 6:
                return None

    head = ctx.head_34
    if head >= 27 or head not in YAOCHU_INDICES:
        return None
    if not has_shuntsu:
        return None

    han = 2 if not ctx.is_menzen else 3
    return ("純全帯幺九", han)


def check_ittsu(ctx: HandContext) -> Optional[YakuResult]:
    """Straight (一気通貫). 123+456+789 of one suit."""
    shuntsu_set = set()
    for m_type, m_idx in ctx.all_mentsu:
        if m_type == 'shuntsu':
            shuntsu_set.add(m_idx)

    for suit_start in (0, 9, 18):
        if (suit_start in shuntsu_set and
            suit_start + 3 in shuntsu_set and
            suit_start + 6 in shuntsu_set):
            han = 1 if not ctx.is_menzen else 2
            return ("一気通貫", han)
    return None


def check_sanshoku_doujun(ctx: HandContext) -> Optional[YakuResult]:
    """Three-colored straight (三色同順). Same sequence in all 3 suits."""
    shuntsu_list = [m[1] for m in ctx.all_mentsu if m[0] == 'shuntsu']

    for s in shuntsu_list:
        if s >= 9:
            continue
        base = s % 9
        if (base in shuntsu_list or s in shuntsu_list):
            if (base + 9) in shuntsu_list and (base + 18) in shuntsu_list and base in shuntsu_list:
                han = 1 if not ctx.is_menzen else 2
                return ("三色同順", han)
    return None


def check_sanshoku_doukou(ctx: HandContext) -> Optional[YakuResult]:
    """Three-colored triplets (三色同刻). Same triplet in all 3 suits."""
    koutsu_set = set(m[1] for m in ctx.all_mentsu if m[0] == 'koutsu')
    for k in koutsu_set:
        if k >= 9:
            continue
        base = k % 9
        if (base + 9) in koutsu_set and (base + 18) in koutsu_set:
            return ("三色同刻", 2)
    return None


def check_toitoi(ctx: HandContext) -> Optional[YakuResult]:
    """All triplets (対対和)."""
    if ctx.is_chiitoi:
        return None
    all_m = ctx.all_mentsu
    if len(all_m) != 4:
        return None
    if all(m[0] == 'koutsu' for m in all_m):
        return ("対対和", 2)
    return None


def check_sanankou(ctx: HandContext) -> Optional[YakuResult]:
    """Three concealed triplets (三暗刻)."""
    if ctx.is_chiitoi:
        return None
    # Count closed koutsu from decomposition
    closed_koutsu = sum(1 for m_type, _ in ctx.mentsu if m_type == 'koutsu')
    # Ankan also counts
    closed_koutsu += sum(1 for m in ctx.melds if m.meld_type == MeldType.ANKAN)

    # Special case: if ron on a shanpon wait, one of the koutsu is "open"
    if not ctx.is_tsumo:
        win_in_shuntsu = any(
            m_type == 'shuntsu' and ctx.win_tile_34 in (m_idx, m_idx + 1, m_idx + 2)
            for m_type, m_idx in ctx.mentsu
        )
        # Check if win tile forms one of the closed koutsu
        for m_type, m_idx in ctx.mentsu:
            if (m_type == 'koutsu' and m_idx == ctx.win_tile_34
                    and not win_in_shuntsu):
                closed_koutsu -= 1
                break

    if closed_koutsu == 3:
        return ("三暗刻", 2)
    return None


def check_honroutou(ctx: HandContext) -> Optional[YakuResult]:
    """All terminals and honors (混老頭)."""
    for i in range(34):
        if ctx.all_tiles_34[i] > 0 and i not in YAOCHU_INDICES:
            return None
    # Must have both terminals and honors
    has_terminal = any(ctx.all_tiles_34[i] > 0 for i in YAOCHU_INDICES if i < 27)
    has_honor = any(ctx.all_tiles_34[i] > 0 for i in range(27, 34))
    if has_terminal and has_honor:
        return ("混老頭", 2)
    return None


def check_shousangen(ctx: HandContext) -> Optional[YakuResult]:
    """Little three dragons (小三元). 2 dragon triplets + dragon pair."""
    dragon_koutsu = sum(1 for m_type, m_idx in ctx.all_mentsu
                        if m_type == 'koutsu' and 31 <= m_idx <= 33)
    dragon_head = 31 <= ctx.head_34 <= 33
    if dragon_koutsu == 2 and dragon_head:
        return ("小三元", 2)
    return None


def check_chiitoi(ctx: HandContext) -> Optional[YakuResult]:
    """Seven pairs (七対子)."""
    if ctx.is_chiitoi:
        return ("七対子", 2)
    return None


def check_honitsu(ctx: HandContext) -> Optional[YakuResult]:
    """Half flush (混一色). One suit + honors."""
    suits_present = set()
    has_honor = False
    for i in range(34):
        if ctx.all_tiles_34[i] > 0:
            if i < 9:
                suits_present.add('m')
            elif i < 18:
                suits_present.add('p')
            elif i < 27:
                suits_present.add('s')
            else:
                has_honor = True

    if len(suits_present) == 1 and has_honor:
        han = 2 if not ctx.is_menzen else 3
        return ("混一色", han)
    return None


def check_chinitsu(ctx: HandContext) -> Optional[YakuResult]:
    """Full flush (清一色). One suit only, no honors."""
    suits_present = set()
    has_honor = False
    for i in range(34):
        if ctx.all_tiles_34[i] > 0:
            if i < 9:
                suits_present.add('m')
            elif i < 18:
                suits_present.add('p')
            elif i < 27:
                suits_present.add('s')
            else:
                has_honor = True

    if len(suits_present) == 1 and not has_honor:
        han = 5 if not ctx.is_menzen else 6
        return ("清一色", han)
    return None


# === Yakuman ===

def check_suuankou(ctx: HandContext) -> Optional[YakuResult]:
    """Four concealed triplets (四暗刻)."""
    if ctx.is_chiitoi or ctx.is_kokushi:
        return None
    closed_koutsu = sum(1 for m_type, _ in ctx.mentsu if m_type == 'koutsu')
    closed_koutsu += sum(1 for m in ctx.melds if m.meld_type == MeldType.ANKAN)

    if not ctx.is_tsumo:
        for m_type, m_idx in ctx.mentsu:
            if m_type == 'koutsu' and m_idx == ctx.win_tile_34:
                closed_koutsu -= 1
                break

    if closed_koutsu == 4:
        return ("四暗刻", 13)
    return None


def check_daisangen(ctx: HandContext) -> Optional[YakuResult]:
    """Big three dragons (大三元)."""
    dragon_koutsu = sum(1 for m_type, m_idx in ctx.all_mentsu
                        if m_type == 'koutsu' and 31 <= m_idx <= 33)
    if dragon_koutsu == 3:
        return ("大三元", 13)
    return None


def check_shousuushii(ctx: HandContext) -> Optional[YakuResult]:
    """Little four winds (小四喜)."""
    wind_koutsu = sum(1 for m_type, m_idx in ctx.all_mentsu
                      if m_type == 'koutsu' and 27 <= m_idx <= 30)
    wind_head = 27 <= ctx.head_34 <= 30
    if wind_koutsu == 3 and wind_head:
        return ("小四喜", 13)
    return None


def check_daisuushii(ctx: HandContext) -> Optional[YakuResult]:
    """Big four winds (大四喜)."""
    wind_koutsu = sum(1 for m_type, m_idx in ctx.all_mentsu
                      if m_type == 'koutsu' and 27 <= m_idx <= 30)
    if wind_koutsu == 4:
        return ("大四喜", 13)
    return None


def check_tsuuiisou(ctx: HandContext) -> Optional[YakuResult]:
    """All honors (字一色)."""
    for i in range(27):
        if ctx.all_tiles_34[i] > 0:
            return None
    return ("字一色", 13)


def check_chinroutou(ctx: HandContext) -> Optional[YakuResult]:
    """All terminals (清老頭)."""
    terminal_indices = {0, 8, 9, 17, 18, 26}
    for i in range(34):
        if ctx.all_tiles_34[i] > 0 and i not in terminal_indices:
            return None
    return ("清老頭", 13)


def check_ryuuiisou(ctx: HandContext) -> Optional[YakuResult]:
    """All green (緑一色). Only 2s,3s,4s,6s,8s + hatsu."""
    green_indices = {19, 20, 21, 23, 25, 32}  # 2s,3s,4s,6s,8s,發
    for i in range(34):
        if ctx.all_tiles_34[i] > 0 and i not in green_indices:
            return None
    return ("緑一色", 13)


def check_chuuren(ctx: HandContext) -> Optional[YakuResult]:
    """Nine gates (九蓮宝燈). Menzen only, one suit: 1112345678999+1."""
    if not ctx.is_menzen:
        return None
    # Determine suit
    suit_start = -1
    for i in range(34):
        if ctx.all_tiles_34[i] > 0:
            if i < 9:
                suit_start = 0
            elif i < 18:
                suit_start = 9
            elif i < 27:
                suit_start = 18
            else:
                return None
            break

    if suit_start < 0:
        return None

    # All tiles must be in one suit
    for i in range(34):
        if ctx.all_tiles_34[i] > 0:
            if not (suit_start <= i < suit_start + 9):
                return None

    # Must have at least: 3,1,1,1,1,1,1,1,3 of 1-9
    required = [3, 1, 1, 1, 1, 1, 1, 1, 3]
    for j in range(9):
        if ctx.all_tiles_34[suit_start + j] < required[j]:
            return None

    return ("九蓮宝燈", 13)


def check_suukantsu(ctx: HandContext) -> Optional[YakuResult]:
    """Four kans (四槓子)."""
    kan_count = sum(1 for m in ctx.melds if m.is_kan)
    if kan_count == 4:
        return ("四槓子", 13)
    return None


def total_han(yaku_list: List[YakuResult]) -> int:
    """Sum total han from yaku list."""
    return sum(han for _, han in yaku_list)


def has_yaku(yaku_list: List[YakuResult]) -> bool:
    """Check if there's at least one real yaku (not just dora)."""
    dora_names = {"ドラ", "裏ドラ", "赤ドラ"}
    return any(name not in dora_names for name, _ in yaku_list)
