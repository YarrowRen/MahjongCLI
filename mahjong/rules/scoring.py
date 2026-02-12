"""Score calculation - convert han + fu to points."""

from typing import List, Tuple, Optional
from dataclasses import dataclass

from mahjong.core.tile import Tile, tiles_to_34_array
from mahjong.core.meld import Meld
from mahjong.core.hand import Hand
from mahjong.rules.agari import decompose_standard, is_chiitoi_agari, is_kokushi_agari, Decomposition
from mahjong.rules.yaku import HandContext, detect_all_yaku, total_han, has_yaku, YakuResult
from mahjong.rules.fu import calculate_fu


@dataclass
class ScoreResult:
    """Result of score calculation."""
    yaku: List[YakuResult]
    han: int
    fu: int
    base_points: int
    # Actual payment amounts
    total_points: int
    dealer_payment: int  # Amount the dealer pays (for tsumo by non-dealer)
    non_dealer_payment: int  # Amount each non-dealer pays (for tsumo)
    ron_payment: int  # Amount the loser pays (for ron)
    is_dealer: bool
    is_tsumo: bool
    honba: int

    @property
    def is_yakuman(self) -> bool:
        return self.han >= 13

    @property
    def rank_name(self) -> str:
        if self.han >= 13:
            return "役満"
        if self.han >= 11:
            return "三倍満"
        if self.han >= 8:
            return "倍満"
        if self.han >= 6:
            return "跳満"
        if self.han >= 5 or (self.han >= 4 and self.fu >= 30) or (self.han >= 3 and self.fu >= 60):
            return "満貫"
        return f"{self.han}翻{self.fu}符"


def calculate_score(
    hand: Hand,
    win_tile: Tile,
    is_tsumo: bool,
    seat_wind_34: int,
    round_wind_34: int,
    is_dealer: bool,
    dora_tiles_34: List[int],
    uradora_tiles_34: List[int],
    honba: int = 0,
    is_riichi: bool = False,
    is_double_riichi: bool = False,
    is_ippatsu: bool = False,
    is_haitei: bool = False,
    is_houtei: bool = False,
    is_rinshan: bool = False,
    is_chankan: bool = False,
    is_tenhou: bool = False,
    is_chiihou: bool = False,
    is_sanma: bool = False,
) -> Optional[ScoreResult]:
    """Calculate score for a winning hand. Returns None if no valid yaku."""
    best_result = None

    # Count dora in all tiles
    all_tiles = list(hand.closed_tiles)
    for meld in hand.melds:
        all_tiles.extend(meld.tiles)
    all_tiles_34 = tiles_to_34_array(all_tiles)

    dora_count = sum(all_tiles_34[d] for d in dora_tiles_34)
    red_dora_count = sum(1 for t in all_tiles if t.is_red)

    # Ura-dora only for riichi
    uradora_count = 0
    if is_riichi or is_double_riichi:
        uradora_count = sum(all_tiles_34[d] for d in uradora_tiles_34)

    # Try all possible decompositions and pick the highest score
    closed_34 = hand.to_34_array()

    # Try standard decompositions
    decompositions = decompose_standard(closed_34)
    for head, mentsu_list in decompositions:
        ctx = _build_context(
            head, mentsu_list, hand, win_tile, is_tsumo,
            seat_wind_34, round_wind_34, dora_count, uradora_count,
            red_dora_count, is_riichi, is_double_riichi, is_ippatsu,
            is_haitei, is_houtei, is_rinshan, is_chankan,
            is_tenhou, is_chiihou, False, False,
        )
        result = _evaluate_context(ctx, is_dealer, honba, is_sanma)
        if result and (best_result is None or result.total_points > best_result.total_points):
            best_result = result

    # Try chiitoi
    if is_chiitoi_agari(closed_34) and len(hand.melds) == 0:
        ctx = _build_context(
            -1, [], hand, win_tile, is_tsumo,
            seat_wind_34, round_wind_34, dora_count, uradora_count,
            red_dora_count, is_riichi, is_double_riichi, is_ippatsu,
            is_haitei, is_houtei, is_rinshan, is_chankan,
            is_tenhou, is_chiihou, True, False,
        )
        result = _evaluate_context(ctx, is_dealer, honba, is_sanma)
        if result and (best_result is None or result.total_points > best_result.total_points):
            best_result = result

    # Try kokushi
    if is_kokushi_agari(closed_34) and len(hand.melds) == 0:
        ctx = _build_context(
            -1, [], hand, win_tile, is_tsumo,
            seat_wind_34, round_wind_34, dora_count, uradora_count,
            red_dora_count, is_riichi, is_double_riichi, is_ippatsu,
            is_haitei, is_houtei, is_rinshan, is_chankan,
            is_tenhou, is_chiihou, False, True,
        )
        result = _evaluate_context(ctx, is_dealer, honba, is_sanma)
        if result and (best_result is None or result.total_points > best_result.total_points):
            best_result = result

    return best_result


def _build_context(
    head, mentsu_list, hand, win_tile, is_tsumo,
    seat_wind_34, round_wind_34, dora_count, uradora_count,
    red_dora_count, is_riichi, is_double_riichi, is_ippatsu,
    is_haitei, is_houtei, is_rinshan, is_chankan,
    is_tenhou, is_chiihou, is_chiitoi, is_kokushi,
) -> HandContext:
    all_tiles = list(hand.closed_tiles)
    for meld in hand.melds:
        all_tiles.extend(meld.tiles)
    all_tiles_34 = tiles_to_34_array(all_tiles)

    ctx = HandContext(
        head_34=head,
        mentsu=mentsu_list,
        closed_tiles_34=hand.to_34_array(),
        melds=hand.melds,
        all_tiles_34=all_tiles_34,
        win_tile_34=win_tile.index34,
        is_tsumo=is_tsumo,
        is_menzen=hand.is_menzen,
        is_riichi=is_riichi,
        is_double_riichi=is_double_riichi,
        is_ippatsu=is_ippatsu,
        seat_wind_34=seat_wind_34,
        round_wind_34=round_wind_34,
        is_haitei=is_haitei,
        is_houtei=is_houtei,
        is_rinshan=is_rinshan,
        is_chankan=is_chankan,
        is_tenhou=is_tenhou,
        is_chiihou=is_chiihou,
        is_chiitoi=is_chiitoi,
        is_kokushi=is_kokushi,
        dora_count=dora_count,
        uradora_count=uradora_count,
        red_dora_count=red_dora_count,
    )
    return ctx


def _evaluate_context(ctx: HandContext, is_dealer: bool, honba: int,
                      is_sanma: bool = False) -> Optional[ScoreResult]:
    """Evaluate a hand context and return ScoreResult or None."""
    yaku_list = detect_all_yaku(ctx)
    if not has_yaku(yaku_list):
        return None

    han_val = total_han(yaku_list)

    # Calculate fu
    is_pinfu = any(name == "平和" for name, _ in yaku_list)
    if ctx.is_kokushi:
        fu_val = 30  # Kokushi: fixed 30 fu (but it's yakuman anyway)
    elif ctx.is_chiitoi:
        fu_val = 25
    else:
        fu_val = calculate_fu(
            ctx.head_34, ctx.mentsu, ctx.melds,
            ctx.win_tile_34, ctx.is_tsumo, ctx.is_menzen,
            ctx.seat_wind_34, ctx.round_wind_34,
            is_pinfu, ctx.is_chiitoi,
        )

    base_points = _calculate_base_points(han_val, fu_val)

    # Calculate actual payments
    return _build_score_result(
        yaku_list, han_val, fu_val, base_points,
        is_dealer, ctx.is_tsumo, honba, is_sanma,
    )


def _calculate_base_points(han: int, fu: int) -> int:
    """Calculate base points from han and fu."""
    if han >= 13:
        return 8000  # Yakuman
    if han >= 11:
        return 6000  # Sanbaiman
    if han >= 8:
        return 4000  # Baiman
    if han >= 6:
        return 3000  # Haneman
    if han >= 5:
        return 2000  # Mangan

    base = fu * (2 ** (2 + han))
    if base >= 2000:
        return 2000  # Mangan
    return base


def _round_up_100(points: int) -> int:
    return ((points + 99) // 100) * 100


def _build_score_result(
    yaku_list, han_val, fu_val, base_points,
    is_dealer, is_tsumo, honba, is_sanma,
) -> ScoreResult:
    """Build the final ScoreResult with payment amounts."""
    honba_bonus_ron = 300 * honba
    honba_bonus_tsumo_each = 100 * honba

    if is_tsumo:
        if is_dealer:
            # Each non-dealer pays base*2
            each_pay = _round_up_100(base_points * 2) + honba_bonus_tsumo_each
            num_payers = 2 if is_sanma else 3
            total = each_pay * num_payers
            return ScoreResult(
                yaku=yaku_list, han=han_val, fu=fu_val,
                base_points=base_points, total_points=total,
                dealer_payment=0, non_dealer_payment=each_pay,
                ron_payment=0, is_dealer=is_dealer, is_tsumo=True,
                honba=honba,
            )
        else:
            # Dealer pays base*2, non-dealers pay base*1
            dealer_pay = _round_up_100(base_points * 2) + honba_bonus_tsumo_each
            non_dealer_pay = _round_up_100(base_points) + honba_bonus_tsumo_each
            if is_sanma:
                total = dealer_pay + non_dealer_pay
            else:
                total = dealer_pay + non_dealer_pay * 2
            return ScoreResult(
                yaku=yaku_list, han=han_val, fu=fu_val,
                base_points=base_points, total_points=total,
                dealer_payment=dealer_pay, non_dealer_payment=non_dealer_pay,
                ron_payment=0, is_dealer=is_dealer, is_tsumo=True,
                honba=honba,
            )
    else:
        # Ron
        if is_dealer:
            ron_pay = _round_up_100(base_points * 6) + honba_bonus_ron
        else:
            ron_pay = _round_up_100(base_points * 4) + honba_bonus_ron
        return ScoreResult(
            yaku=yaku_list, han=han_val, fu=fu_val,
            base_points=base_points, total_points=ron_pay,
            dealer_payment=0, non_dealer_payment=0,
            ron_payment=ron_pay, is_dealer=is_dealer, is_tsumo=False,
            honba=honba,
        )
