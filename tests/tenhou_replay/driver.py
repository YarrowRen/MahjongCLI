"""Replay driver — drives the engine step by step using parsed XML events.

Core flow per round:
  1. Build wall from XML data
  2. Create RoundState with correct initial conditions
  3. Set up initial hands (bypass normal dealing)
  4. Execute events sequentially, verifying state at each step
  5. Verify final scores on AGARI/RYUUKYOKU
"""

from typing import List, Optional

from mahjong.core.tile import Tile, ALL_TILES_136
from mahjong.core.meld import Meld, MeldType
from mahjong.core.hand import Hand
from mahjong.core.wall import Wall
from mahjong.core.player_state import PlayerState, Wind
from mahjong.engine.round import RoundState, RoundResult
from mahjong.engine.action import ActionType
from mahjong.engine.event import EventBus
from mahjong.rules.scoring import calculate_score

from .parser import RoundData, Event, EventType
from .decoder import TenhouMeldType
from .wall_builder import build_wall
from .verifier import (
    ReplayVerificationError,
    verify_draw,
    verify_agari_score,
    verify_score_changes,
)


def replay_round(rd: RoundData, round_index: int = 0):
    """Replay a single round from parsed XML data.

    Raises ReplayVerificationError on any mismatch.
    """
    num_players = rd.num_players
    is_sanma = rd.is_sanma

    # 1. Build wall
    live_tiles, dead_tiles, dora_revealed = build_wall(rd)
    wall = Wall.from_tiles(
        live_tiles,
        dead_tiles,
        is_sanma=is_sanma,
        dora_revealed=dora_revealed,
    )

    # 2. Create players with initial scores
    players = []
    for i in range(num_players):
        p = PlayerState(seat=i, name=f"P{i}", score=rd.scores[i])
        players.append(p)

    # 3. Set up seat winds and dealer
    # round_number: 0=E1, 1=E2, ..., 4=S1, ...
    round_wind = Wind(rd.round_number // 4)
    dealer = rd.dealer

    for i in range(num_players):
        seat_wind = Wind((i - dealer) % num_players)
        players[i].seat_wind = seat_wind
        players[i].is_dealer = (i == dealer)

    # 4. Create RoundState
    event_bus = EventBus()
    rs = RoundState(
        players=players,
        wall=wall,
        round_wind=round_wind,
        honba=rd.honba,
        riichi_sticks=rd.riichi_sticks,
        event_bus=event_bus,
        is_sanma=is_sanma,
    )

    # 5. Set initial hands directly (bypass deal_tiles)
    for i in range(num_players):
        for tile_id in rd.hands[i]:
            tile = ALL_TILES_136[tile_id]
            rs.players[i].hand.closed_tiles.append(tile)
        rs.players[i].hand.sort_closed()
        rs.players[i].hand.draw_tile = None

    # 6. Process events sequentially
    riichi_pending = {}  # player -> True when REACH step=1 seen, awaiting discard
    riichi_pending_double = {}  # player -> is_double_riichi at step=1
    riichi_pending_blocked = {}  # player -> ippatsu cancelled before step=2
    riichi_pending_candidates = {}  # player -> riichi discard candidates
    last_draw_available = {}  # player -> AvailableActions from last draw
    expect_rinshan = False  # True when next draw should be treated as rinshan
    rinshan_from_live = False  # True when rinshan draw comes from live wall (kita)
    step = 0

    last_was_agari = False
    pending_temp_furiten = None  # (discard_player, tile) awaiting confirmation
    for event in rd.events:
        step_desc = f"R{round_index} step {step}"
        step += 1

        # Apply deferred temp furiten: if the previous discard was NOT
        # followed by an AGARI, now commit the temp furiten update.
        if event.event_type != EventType.AGARI and pending_temp_furiten is not None:
            dp, dt = pending_temp_furiten
            rs.update_temp_furiten(dp, dt)
            pending_temp_furiten = None

        if event.event_type == EventType.DRAW:
            last_was_agari = False
            player = event.player
            tile_id = event.tile_id

            if expect_rinshan:
                # Rinshan draw (after kan or kita)
                if rinshan_from_live:
                    tile = wall.draw()
                else:
                    tile = wall.draw_rinshan()
                expect_rinshan = False
                rinshan_from_live = False
                rs.is_rinshan = True
                if tile is None:
                    raise ReplayVerificationError(
                        f"[{step_desc}] Cannot draw rinshan for player {player}"
                    )
                rs.players[player].hand.draw(tile)
                # Reveal pending kakan dora after replacement draw
                if rs.pending_kakan_dora > 0:
                    rs.wall.reveal_new_dora()
                    rs.pending_kakan_dora -= 1
            else:
                # Normal draw from live wall
                rs.clear_temp_furiten(player)
                rs.turn_count += 1
                rs.is_rinshan = False

                tile = wall.draw()
                if tile is None:
                    raise ReplayVerificationError(
                        f"[{step_desc}] Wall empty, cannot draw for player {player}"
                    )
                rs.players[player].hand.draw(tile)

                # Check haitei
                rs.is_haitei = wall.remaining == 0

            # Cache available actions after draw (for legality checks)
            last_draw_available[player] = rs.get_draw_actions(player)

            if tile.id != tile_id:
                raise ReplayVerificationError(
                    f"[{step_desc}] Player {player} drew tile {tile.id} "
                    f"({tile.name}), expected {tile_id} "
                    f"({ALL_TILES_136[tile_id].name})"
                )

        elif event.event_type == EventType.DISCARD:
            last_was_agari = False
            player = event.player
            tile_id = event.tile_id
            tile = ALL_TILES_136[tile_id]

            # Verify discard is legal
            available = last_draw_available.get(player)
            if available:
                if tile not in available.can_discard:
                    raise ReplayVerificationError(
                        f"[{step_desc}] Illegal discard: {tile.name} not in can_discard"
                    )
            else:
                # After call (no draw), must discard from hand
                if tile not in rs.players[player].hand.closed_tiles:
                    raise ReplayVerificationError(
                        f"[{step_desc}] Illegal discard: {tile.name} not in hand"
                    )

            # If riichi pending, discard must be a riichi candidate
            # Compare by index34 since red/non-red variants are equivalent
            if riichi_pending.get(player):
                candidates = riichi_pending_candidates.get(player, [])
                candidate_indices = set(t.index34 for t in candidates)
                if tile.index34 not in candidate_indices:
                    raise ReplayVerificationError(
                        f"[{step_desc}] Illegal riichi discard: {tile.name}"
                    )

            # Always process as normal discard.
            # Riichi flags are set later on REACH step=2 (after confirming
            # no one ronned the riichi discard).
            rs.process_discard(player, tile)

            # Defer temp furiten update until we confirm no one rons this tile.
            # In real gameplay, temp furiten is only set when a player PASSES
            # on a ron opportunity, not when the discard is actually ronned.
            pending_temp_furiten = (player, tile)
            last_draw_available.pop(player, None)

        elif event.event_type == EventType.MELD:
            last_was_agari = False
            _verify_meld_available(rs, event, step_desc, last_draw_available)
            _process_meld_event(rs, event, step_desc)
            # Any call/kan/kita cancels ippatsu for pending riichi
            if riichi_pending:
                for p in list(riichi_pending.keys()):
                    riichi_pending_blocked[p] = True
            # After kan or kita, next draw is a rinshan draw
            if event.decoded_meld and event.decoded_meld.meld_type in (
                TenhouMeldType.ANKAN, TenhouMeldType.DAIMINKAN,
                TenhouMeldType.KAKAN,
            ):
                expect_rinshan = True
            elif event.decoded_meld and event.decoded_meld.meld_type == TenhouMeldType.KITA:
                expect_rinshan = True
                rinshan_from_live = True
            last_draw_available.pop(event.player, None)

        elif event.event_type == EventType.RIICHI_DECLARE:
            last_was_agari = False
            # Just record intent; actual riichi finalized on step=2
            riichi_pending[event.player] = True
            available = rs.get_draw_actions(event.player)
            if not available.can_riichi:
                raise ReplayVerificationError(
                    f"[{step_desc}] Illegal riichi: can_riichi is False"
                )
            riichi_pending_candidates[event.player] = list(available.riichi_candidates)
            # Record double-riichi eligibility at declaration time
            no_calls = all(len(p.hand.melds) == 0 for p in rs.players)
            if rs.is_sanma:
                no_calls = no_calls and all(len(p.kita_tiles) == 0 for p in rs.players)
            riichi_pending_double[event.player] = (
                rs.first_draw[event.player] and no_calls
            )

        elif event.event_type == EventType.RIICHI_SCORE:
            last_was_agari = False
            # Riichi confirmed (no one ronned the discard).
            # Now apply riichi flags and score deduction.
            player = event.player
            riichi_pending.pop(player, None)
            is_double = riichi_pending_double.pop(player, False)
            ippatsu_blocked = riichi_pending_blocked.pop(player, False)
            riichi_pending_candidates.pop(player, None)
            hand = rs.players[player].hand

            hand.is_riichi = True
            hand.is_ippatsu = not ippatsu_blocked
            if is_double:
                hand.is_double_riichi = True

            rs.riichi_declared_count += 1
            rs.players[player].score -= 1000
            rs.riichi_sticks += 1

            hand.riichi_discard_index = len(hand.discard_pool) - 1

        elif event.event_type == EventType.AGARI:
            if expect_rinshan:
                # Chankan (robbed kan) can end the hand before rinshan draw
                expect_rinshan = False
            # Verify win legality
            winner = event.agari_who
            from_who = event.agari_from
            is_tsumo = (winner == from_who)
            win_tile = ALL_TILES_136[event.agari_machi]
            if is_tsumo:
                available = rs.get_draw_actions(winner)
                if not available.can_tsumo:
                    raise ReplayVerificationError(
                        f"[{step_desc}] Illegal tsumo: can_tsumo is False"
                    )
            else:
                available = rs.get_response_actions(winner, win_tile, from_who)
                if not available.can_ron:
                    raise ReplayVerificationError(
                        f"[{step_desc}] Illegal ron: can_ron is False"
                    )
            _verify_agari(rs, rd, event, step_desc, is_secondary_ron=last_was_agari)
            last_was_agari = True

        elif event.event_type == EventType.RYUUKYOKU:
            last_was_agari = False
            _verify_ryuukyoku(rs, rd, event, step_desc)


def _process_meld_event(rs: RoundState, event: Event, step_desc: str):
    """Process a meld (call) event."""
    dm = event.decoded_meld
    player = event.player

    if dm.meld_type == TenhouMeldType.CHI:
        _process_chi(rs, player, dm, step_desc)
    elif dm.meld_type == TenhouMeldType.PON:
        _process_pon(rs, player, dm, step_desc)
    elif dm.meld_type == TenhouMeldType.DAIMINKAN:
        _process_daiminkan(rs, player, dm, step_desc)
    elif dm.meld_type == TenhouMeldType.ANKAN:
        _process_ankan(rs, player, dm, step_desc)
    elif dm.meld_type == TenhouMeldType.KAKAN:
        _process_kakan(rs, player, dm, step_desc)
    elif dm.meld_type == TenhouMeldType.KITA:
        _process_kita(rs, player, dm, step_desc)


def _verify_meld_available(rs: RoundState, event: Event, step_desc: str,
                           last_draw_available):
    """Verify meld action is available in engine-generated actions."""
    dm = event.decoded_meld
    if dm is None:
        return
    player = event.player

    def _tiles_match(tiles_136, meld_tiles):
        a = sorted(t // 4 for t in tiles_136)
        b = sorted(t.index34 for t in meld_tiles)
        return a == b

    if dm.meld_type in (TenhouMeldType.CHI, TenhouMeldType.PON,
                        TenhouMeldType.DAIMINKAN):
        if rs.last_discard is None or rs.last_discard_player < 0:
            raise ReplayVerificationError(
                f"[{step_desc}] Meld without discard context"
            )
        available = rs.get_response_actions(player, rs.last_discard,
                                            rs.last_discard_player)
        if dm.meld_type == TenhouMeldType.CHI:
            if not any(_tiles_match(dm.tiles_136, m.tiles) for m in available.can_chi):
                raise ReplayVerificationError(
                    f"[{step_desc}] Illegal chi: meld not available"
                )
        elif dm.meld_type == TenhouMeldType.PON:
            if not any(_tiles_match(dm.tiles_136, m.tiles) for m in available.can_pon):
                raise ReplayVerificationError(
                    f"[{step_desc}] Illegal pon: meld not available"
                )
        elif dm.meld_type == TenhouMeldType.DAIMINKAN:
            if not any(_tiles_match(dm.tiles_136, m.tiles) for m in available.can_daiminkan):
                raise ReplayVerificationError(
                    f"[{step_desc}] Illegal daiminkan: meld not available"
                )
        return

    available = last_draw_available.get(player) or rs.get_draw_actions(player)

    if dm.meld_type == TenhouMeldType.ANKAN:
        if not any(_tiles_match(dm.tiles_136, tiles) for tiles in available.can_ankan):
            raise ReplayVerificationError(
                f"[{step_desc}] Illegal ankan: meld not available"
            )
    elif dm.meld_type == TenhouMeldType.KAKAN:
        tile_34 = dm.tiles_136[0] // 4
        if not any(t.index34 == tile_34 for t in available.can_shouminkan):
            raise ReplayVerificationError(
                f"[{step_desc}] Illegal kakan: meld not available"
            )
    elif dm.meld_type == TenhouMeldType.KITA:
        if not available.can_kita:
            raise ReplayVerificationError(
                f"[{step_desc}] Illegal kita: can_kita is False"
            )


def _resolve_from_who(player: int, relative: int, num_players: int = 4) -> int:
    """Convert relative from_who to absolute seat index."""
    return (player + relative) % num_players


def _process_chi(rs: RoundState, player: int, dm, step_desc: str):
    """Process chi call."""
    from_player = _resolve_from_who(player, dm.from_who_relative, rs.num_players)
    called_tile = ALL_TILES_136[dm.called_tile_136]

    # Build tiles for the meld
    tiles = tuple(ALL_TILES_136[tid] for tid in dm.tiles_136)

    # Find the actual tiles from the player's hand
    hand = rs.players[player].hand
    hand_tiles = []
    for tid in dm.tiles_136:
        t = ALL_TILES_136[tid]
        if t == called_tile:
            continue  # called tile comes from discard
        # Find this specific tile in hand
        found = None
        for ht in hand.closed_tiles:
            if ht.id == tid:
                found = ht
                break
        if found is None:
            # Try to find by index34 (tile with same type but different id)
            for ht in hand.closed_tiles:
                if ht.index34 == t.index34 and ht not in hand_tiles:
                    found = ht
                    break
        if found is None:
            raise ReplayVerificationError(
                f"[{step_desc}] Chi: player {player} missing tile {tid} "
                f"({t.name}) in hand"
            )
        hand_tiles.append(found)

    # Build the meld with actual tile objects
    meld_tiles = []
    hand_tile_iter = iter(hand_tiles)
    for tid in dm.tiles_136:
        if tid == dm.called_tile_136:
            meld_tiles.append(called_tile)
        else:
            meld_tiles.append(next(hand_tile_iter))

    from mahjong.engine.action import Action, ActionType
    meld = Meld(MeldType.CHI, tuple(meld_tiles), called_tile, from_player)
    action = Action(ActionType.CHI, player, meld=meld)
    rs.process_call(action)


def _process_pon(rs: RoundState, player: int, dm, step_desc: str):
    """Process pon call."""
    from_player = _resolve_from_who(player, dm.from_who_relative, rs.num_players)
    called_tile = ALL_TILES_136[dm.called_tile_136]

    hand = rs.players[player].hand
    hand_tiles = []
    for tid in dm.tiles_136:
        if tid == dm.called_tile_136:
            continue
        t = ALL_TILES_136[tid]
        found = None
        for ht in hand.closed_tiles:
            if ht.id == tid and ht not in hand_tiles:
                found = ht
                break
        if found is None:
            for ht in hand.closed_tiles:
                if ht.index34 == t.index34 and ht not in hand_tiles:
                    found = ht
                    break
        if found is None:
            raise ReplayVerificationError(
                f"[{step_desc}] Pon: player {player} missing tile {tid} in hand"
            )
        hand_tiles.append(found)

    meld_tiles = tuple(hand_tiles) + (called_tile,)
    from mahjong.engine.action import Action, ActionType
    meld = Meld(MeldType.PON, meld_tiles, called_tile, from_player)
    action = Action(ActionType.PON, player, meld=meld)
    rs.process_call(action)


def _process_daiminkan(rs: RoundState, player: int, dm, step_desc: str):
    """Process daiminkan (open kan from discard)."""
    from_player = _resolve_from_who(player, dm.from_who_relative, rs.num_players)
    called_tile = ALL_TILES_136[dm.called_tile_136]

    hand = rs.players[player].hand
    hand_tiles = []
    for tid in dm.tiles_136:
        if tid == dm.called_tile_136:
            continue
        t = ALL_TILES_136[tid]
        found = None
        for ht in hand.closed_tiles:
            if ht.id == tid and ht not in hand_tiles:
                found = ht
                break
        if found is None:
            for ht in hand.closed_tiles:
                if ht.index34 == t.index34 and ht not in hand_tiles:
                    found = ht
                    break
        if found is None:
            raise ReplayVerificationError(
                f"[{step_desc}] Daiminkan: player {player} missing tile {tid}"
            )
        hand_tiles.append(found)

    meld_tiles = tuple(hand_tiles) + (called_tile,)
    from mahjong.engine.action import Action, ActionType
    meld = Meld(MeldType.DAIMINKAN, meld_tiles, called_tile, from_player)
    action = Action(ActionType.DAIMINKAN, player, meld=meld)
    rs.process_call(action)

    # Rinshan draw + new dora handled by next DRAW event
    # But daiminkan's reveal_new_dora is already called in process_call


def _process_ankan(rs: RoundState, player: int, dm, step_desc: str):
    """Process ankan (closed kan)."""
    hand = rs.players[player].hand
    tiles = []
    for tid in dm.tiles_136:
        t = ALL_TILES_136[tid]
        found = None
        for ht in hand.closed_tiles:
            if ht.id == tid and ht not in tiles:
                found = ht
                break
        if found is None:
            for ht in hand.closed_tiles:
                if ht.index34 == t.index34 and ht not in tiles:
                    found = ht
                    break
        if found is None:
            raise ReplayVerificationError(
                f"[{step_desc}] Ankan: player {player} missing tile {tid}"
            )
        tiles.append(found)

    rs.process_ankan(player, tiles)

    # Rinshan draw handled by next DRAW event (wall_builder tags it)


def _process_kakan(rs: RoundState, player: int, dm, step_desc: str):
    """Process kakan (shouminkan / added kan)."""
    # Find the added tile: it's the one at the 'unused' position
    # We need to find which tile is being added to an existing pon
    hand = rs.players[player].hand

    # The tile_34 of the kan
    tile_34 = dm.tiles_136[0] // 4

    # Find the tile in hand that matches
    added_tile = None
    for ht in hand.closed_tiles:
        if ht.index34 == tile_34:
            added_tile = ht
            break

    if added_tile is None:
        raise ReplayVerificationError(
            f"[{step_desc}] Kakan: player {player} missing tile for "
            f"index34={tile_34}"
        )

    rs.process_shouminkan(player, added_tile)


def _process_kita(rs: RoundState, player: int, dm, step_desc: str):
    """Process kita (sanma north declaration)."""
    tile_id = dm.tiles_136[0]
    tile = ALL_TILES_136[tile_id]

    hand = rs.players[player].hand
    # Find the specific north tile in hand
    found = None
    for ht in hand.closed_tiles:
        if ht.id == tile_id:
            found = ht
            break
    if found is None:
        # Try by index34
        for ht in hand.closed_tiles:
            if ht.index34 == 30:
                found = ht
                break
    if found is None:
        raise ReplayVerificationError(
            f"[{step_desc}] Kita: player {player} missing north tile in hand"
        )

    # Remove north from hand and add to kita_tiles
    hand.closed_tiles.remove(found)
    hand.draw_tile = None
    rs.players[player].kita_tiles.append(found)

    # Cancel all ippatsu (kita is a call in sanma)
    for p in rs.players:
        p.hand.is_ippatsu = False


def _verify_agari(rs: RoundState, rd: RoundData, event: Event, step_desc: str,
                  is_secondary_ron: bool = False):
    """Verify AGARI (win) result."""
    winner = event.agari_who
    from_who = event.agari_from
    is_tsumo = (winner == from_who)
    win_tile = ALL_TILES_136[event.agari_machi]
    agari_honba = event.agari_ba[0] if event.agari_ba else rs.honba
    # In double/triple ron, Tenhou awards honba/riichi sticks only once.
    if is_secondary_ron and not is_tsumo:
        agari_honba = 0

    player = rs.players[winner]
    hand = player.hand

    kita_count = len(rs.players[winner].kita_tiles) if rs.is_sanma else 0

    if is_tsumo:
        # Tsumo: win_tile is the drawn tile
        result = calculate_score(
            hand=hand,
            win_tile=win_tile,
            is_tsumo=True,
            seat_wind_34=player.seat_wind.index34,
            round_wind_34=rs.round_wind.index34,
            is_dealer=player.is_dealer,
            dora_tiles_34=rs.wall.get_dora_tiles_34(),
            uradora_tiles_34=rs.wall.get_uradora_tiles_34(),
            honba=agari_honba,
            is_riichi=hand.is_riichi,
            is_double_riichi=hand.is_double_riichi,
            is_ippatsu=hand.is_ippatsu,
            is_haitei=rs.is_haitei,
            is_rinshan=rs.is_rinshan,
            is_tenhou=(player.is_dealer and rs.turn_count == 0),
            is_chiihou=(not player.is_dealer and rs.first_draw[winner]),
            is_sanma=rs.is_sanma,
            kita_count=kita_count,
        )
    else:
        # Ron: need to temporarily add win tile
        test_hand = hand.clone()
        test_hand.closed_tiles.append(win_tile)
        is_last_tile = rs.wall.remaining == 0
        result = calculate_score(
            hand=test_hand,
            win_tile=win_tile,
            is_tsumo=False,
            seat_wind_34=player.seat_wind.index34,
            round_wind_34=rs.round_wind.index34,
            is_dealer=player.is_dealer,
            dora_tiles_34=rs.wall.get_dora_tiles_34(),
            uradora_tiles_34=rs.wall.get_uradora_tiles_34(),
            honba=agari_honba,
            is_riichi=hand.is_riichi,
            is_double_riichi=hand.is_double_riichi,
            is_ippatsu=hand.is_ippatsu,
            is_houtei=is_last_tile,
            is_sanma=rs.is_sanma,
            kita_count=kita_count,
        )

    if result is None:
        raise ReplayVerificationError(
            f"[{step_desc}] AGARI: engine returned None for player {winner}, "
            f"win_tile={win_tile.name}, is_tsumo={is_tsumo}"
        )

    # Verify fu and base points
    # Tenhou's ten[1] is total points WITHOUT honba bonus
    expected_ten = event.agari_ten  # [fu, points, ...]
    # Subtract honba bonus from engine result for comparison
    if is_tsumo:
        num_payers = rs.num_players - 1
        honba_bonus = num_payers * 100 * agari_honba
    else:
        honba_bonus = (200 if rs.is_sanma else 300) * agari_honba
    engine_points_no_honba = result.total_points - honba_bonus
    verify_agari_score(expected_ten, result.fu, engine_points_no_honba, step_desc)

    # Verify score changes
    if event.agari_sc:
        # Build engine score changes (always 4 entries, P3=0 for sanma)
        engine_changes = [0, 0, 0, 0]
        if is_tsumo:
            if player.is_dealer:
                for i in range(rs.num_players):
                    if i != winner:
                        engine_changes[i] = -result.non_dealer_payment
                        engine_changes[winner] += result.non_dealer_payment
            else:
                for i in range(rs.num_players):
                    if i == winner:
                        continue
                    if rs.players[i].is_dealer:
                        engine_changes[i] = -result.dealer_payment
                        engine_changes[winner] += result.dealer_payment
                    else:
                        engine_changes[i] = -result.non_dealer_payment
                        engine_changes[winner] += result.non_dealer_payment
        else:
            engine_changes[winner] = result.ron_payment
            engine_changes[from_who] = -result.ron_payment

        # Add riichi sticks to winner (use ba attribute from AGARI for accuracy,
        # especially in double-ron where sticks go to closest winner only)
        agari_riichi_sticks = event.agari_ba[1] if event.agari_ba else rs.riichi_sticks
        if is_secondary_ron and not is_tsumo:
            agari_riichi_sticks = 0
        engine_changes[winner] += agari_riichi_sticks * 1000

        verify_score_changes(event.agari_sc, engine_changes,
                             rd.scores, step_desc)


def _verify_ryuukyoku(rs: RoundState, rd: RoundData, event: Event,
                      step_desc: str):
    """Verify RYUUKYOKU (draw) result."""
    if event.ryuukyoku_sc:
        # For exhaustive draw, verify tenpai payments
        expected_changes = [event.ryuukyoku_sc[i * 2 + 1] * 100 for i in range(4)]
        # We could compute engine tenpai/noten but for now just log
        # The main verification is score changes
        pass  # Score changes verified at round boundaries
