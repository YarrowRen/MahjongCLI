"""Single round (局) flow control - the core game loop."""

from typing import List, Optional, Tuple, Set

from mahjong.core.tile import Tile, tiles_to_34_array, ALL_TILES_136, YAOCHU_INDICES
from mahjong.core.meld import Meld, MeldType
from mahjong.core.hand import Hand
from mahjong.core.wall import Wall
from mahjong.core.player_state import PlayerState, Wind
from mahjong.engine.action import Action, ActionType, AvailableActions
from mahjong.engine.event import EventBus, EventType, GameEvent
from mahjong.rules.agari import is_agari, get_waiting_tiles
from mahjong.rules.shanten import shanten
from mahjong.rules.scoring import calculate_score, ScoreResult
from mahjong.rules.furiten import is_discard_furiten, get_hand_waiting_tiles


class RoundResult:
    """Result of a completed round."""

    def __init__(self):
        self.winners: List[int] = []  # Seat indices of winners
        self.loser: Optional[int] = None  # Seat index of deal-in player
        self.score_results: List[Tuple[int, ScoreResult]] = []  # (seat, result) pairs
        self.score_changes: List[int] = [0, 0, 0, 0]
        self.is_draw: bool = False
        self.draw_type: str = ""  # "exhaustive", "4kan", "4wind", "4riichi", "kyuushu"
        self.tenpai_players: List[int] = []  # For exhaustive draw
        self.dealer_continues: bool = False
        self.riichi_sticks_winner: Optional[int] = None


class RoundState:
    """State for a single round of play."""

    def __init__(
        self,
        players: List[PlayerState],
        wall: Wall,
        round_wind: Wind,
        honba: int,
        riichi_sticks: int,
        event_bus: EventBus,
        is_sanma: bool = False,
    ):
        self.players = players
        self.wall = wall
        self.round_wind = round_wind
        self.honba = honba
        self.riichi_sticks = riichi_sticks
        self.event_bus = event_bus
        self.is_sanma = is_sanma
        self.num_players = 3 if is_sanma else 4

        self.current_player = 0  # Dealer starts
        self.turn_count = 0
        self.first_draw = [True] * self.num_players
        self.kan_count_total = 0
        self.kan_this_turn = False
        self.last_discard: Optional[Tile] = None
        self.last_discard_player: int = -1
        self.is_rinshan = False
        self.is_haitei = False

        # Furiten tracking
        self.temp_furiten: List[Set[int]] = [set() for _ in range(self.num_players)]
        self.riichi_furiten: List[Set[int]] = [set() for _ in range(self.num_players)]

        # Abortive draw tracking
        self.first_discard_winds: List[int] = []  # 34 indices of first discards
        self.riichi_declared_count = 0

        # Result
        self.result: Optional[RoundResult] = None
        self.is_finished = False

    def deal_tiles(self):
        """Deal initial hands."""
        for _ in range(13):
            for i in range(self.num_players):
                tile = self.wall.draw()
                if tile:
                    self.players[i].hand.draw(tile)

        for i in range(self.num_players):
            self.players[i].hand.sort_closed()
            self.players[i].hand.draw_tile = None

        self.event_bus.emit(GameEvent(EventType.ROUND_START, {
            "round_wind": self.round_wind,
            "honba": self.honba,
            "dora_indicators": self.wall.dora_indicators,
        }))

    def get_draw_actions(self, player_idx: int) -> AvailableActions:
        """Get available actions after drawing a tile."""
        hand = self.players[player_idx].hand
        closed_34 = hand.to_34_array()
        actions = AvailableActions(player=player_idx)

        # Check tsumo (win)
        if is_agari(closed_34):
            # Check furiten - if furiten, can still tsumo
            actions.can_tsumo = True

        # Check riichi
        if (hand.is_menzen and not hand.is_riichi and
                self.players[player_idx].score >= 1000 and
                self.wall.remaining >= self.num_players):
            riichi_tiles = self._get_riichi_candidates(player_idx)
            if riichi_tiles:
                actions.can_riichi = True
                actions.riichi_candidates = riichi_tiles

        # Check ankan
        for i in range(34):
            if closed_34[i] == 4:
                # Can't change wait after riichi (simplified: allow if tenpai stays)
                if hand.is_riichi:
                    # Only allow if the remaining hand is still tenpai
                    test_34 = list(closed_34)
                    test_34[i] -= 4
                    if sum(test_34) % 3 == 1 and get_waiting_tiles(test_34):
                        tiles = [t for t in hand.closed_tiles if t.index34 == i]
                        actions.can_ankan.append(tiles)
                else:
                    tiles = [t for t in hand.closed_tiles if t.index34 == i]
                    actions.can_ankan.append(tiles)

        # Check shouminkan (promote pon to kan)
        if not hand.is_riichi:
            for meld in hand.melds:
                if meld.meld_type == MeldType.PON:
                    idx = meld.tile_index34
                    matching = [t for t in hand.closed_tiles if t.index34 == idx]
                    if matching:
                        actions.can_shouminkan.append(matching[0])

        # Check kita (sanma north)
        if self.is_sanma:
            north_tiles = [t for t in hand.closed_tiles if t.index34 == 30]
            if north_tiles:
                actions.can_kita = True

        # Check kyuushu kyuuhai (nine terminals redraw) - only on first draw
        if self.first_draw[player_idx] and self.turn_count < self.num_players:
            yaochu_types = sum(1 for i in YAOCHU_INDICES if closed_34[i] > 0)
            if yaochu_types >= 9:
                actions.can_kyuushu = True

        # Always can discard
        if hand.is_riichi:
            # Must tsumogiri (discard drawn tile)
            if hand.draw_tile:
                actions.can_discard = [hand.draw_tile]
        else:
            actions.can_discard = list(hand.closed_tiles)

        return actions

    def get_response_actions(self, player_idx: int, discard_tile: Tile,
                             discard_player: int) -> AvailableActions:
        """Get available actions in response to another player's discard."""
        hand = self.players[player_idx].hand
        closed_34 = hand.to_34_array()
        actions = AvailableActions(player=player_idx)

        tile_34 = discard_tile.index34

        # Check ron
        test_34 = list(closed_34)
        test_34[tile_34] += 1
        if is_agari(test_34):
            # Check furiten
            waiting = get_hand_waiting_tiles(hand)
            discard_furiten = is_discard_furiten(hand)
            temp_f = any(w in self.temp_furiten[player_idx] for w in waiting)
            riichi_f = any(w in self.riichi_furiten[player_idx] for w in waiting)

            if not discard_furiten and not temp_f and not riichi_f:
                actions.can_ron = True

        if hand.is_riichi:
            # Can only ron after riichi, no other calls
            return actions

        # Check pon
        if closed_34[tile_34] >= 2:
            pon_tiles = [t for t in hand.closed_tiles if t.index34 == tile_34][:2]
            meld = Meld(
                meld_type=MeldType.PON,
                tiles=tuple(pon_tiles) + (discard_tile,),
                called_tile=discard_tile,
                from_player=discard_player,
            )
            actions.can_pon.append(meld)

        # Check daiminkan
        if closed_34[tile_34] >= 3:
            kan_tiles = [t for t in hand.closed_tiles if t.index34 == tile_34][:3]
            meld = Meld(
                meld_type=MeldType.DAIMINKAN,
                tiles=tuple(kan_tiles) + (discard_tile,),
                called_tile=discard_tile,
                from_player=discard_player,
            )
            actions.can_daiminkan.append(meld)

        # Check chi - only from the player to the left (previous player)
        if not self.is_sanma:
            left_player = (player_idx - 1) % self.num_players
            if discard_player == left_player:
                self._check_chi(actions, hand, discard_tile, discard_player)

        return actions

    def _check_chi(self, actions: AvailableActions, hand: Hand,
                   discard_tile: Tile, from_player: int):
        """Check possible chi combinations."""
        if discard_tile.is_honor:
            return

        idx = discard_tile.index34
        suit_start = (idx // 9) * 9
        num = idx - suit_start  # 0-8

        closed_34 = hand.to_34_array()

        # Pattern: [discard]-X-Y
        if num <= 6 and closed_34[idx + 1] >= 1 and closed_34[idx + 2] >= 1:
            t1 = next(t for t in hand.closed_tiles if t.index34 == idx + 1)
            t2 = next(t for t in hand.closed_tiles if t.index34 == idx + 2)
            meld = Meld(MeldType.CHI, (discard_tile, t1, t2),
                        discard_tile, from_player)
            actions.can_chi.append(meld)

        # Pattern: X-[discard]-Y
        if num >= 1 and num <= 7 and closed_34[idx - 1] >= 1 and closed_34[idx + 1] >= 1:
            t1 = next(t for t in hand.closed_tiles if t.index34 == idx - 1)
            t2 = next(t for t in hand.closed_tiles if t.index34 == idx + 1)
            meld = Meld(MeldType.CHI, (t1, discard_tile, t2),
                        discard_tile, from_player)
            actions.can_chi.append(meld)

        # Pattern: X-Y-[discard]
        if num >= 2 and closed_34[idx - 2] >= 1 and closed_34[idx - 1] >= 1:
            t1 = next(t for t in hand.closed_tiles if t.index34 == idx - 2)
            t2 = next(t for t in hand.closed_tiles if t.index34 == idx - 1)
            meld = Meld(MeldType.CHI, (t1, t2, discard_tile),
                        discard_tile, from_player)
            actions.can_chi.append(meld)

    def _get_riichi_candidates(self, player_idx: int) -> List[Tile]:
        """Get tiles that can be discarded for riichi (must result in tenpai)."""
        hand = self.players[player_idx].hand
        candidates = []
        seen = set()

        for tile in hand.closed_tiles:
            if tile.index34 in seen:
                continue
            seen.add(tile.index34)

            test_34 = hand.to_34_array()
            test_34[tile.index34] -= 1
            if get_waiting_tiles(test_34):
                candidates.append(tile)

        return candidates

    def process_draw(self, player_idx: int) -> Optional[Tile]:
        """Draw a tile for a player. Returns None if wall is empty."""
        if self.wall.is_empty:
            return None

        self.is_haitei = self.wall.remaining == 1
        tile = self.wall.draw()
        if tile:
            self.players[player_idx].hand.draw(tile)
            self.event_bus.emit(GameEvent(EventType.DRAW, {
                "player": player_idx,
                "tile": tile,
            }))
        return tile

    def process_rinshan_draw(self, player_idx: int) -> Optional[Tile]:
        """Draw a rinshan tile after kan."""
        tile = self.wall.draw_rinshan()
        if tile:
            self.players[player_idx].hand.draw(tile)
            self.is_rinshan = True
            self.event_bus.emit(GameEvent(EventType.DRAW, {
                "player": player_idx,
                "tile": tile,
                "is_rinshan": True,
            }))
        return tile

    def process_discard(self, player_idx: int, tile: Tile):
        """Process a discard action."""
        hand = self.players[player_idx].hand
        is_tsumogiri = (tile == hand.draw_tile)
        hand.discard(tile, is_tsumogiri)

        self.last_discard = tile
        self.last_discard_player = player_idx
        self.is_rinshan = False

        # Cancel ippatsu for all players
        for p in self.players:
            if p.hand.is_ippatsu:
                p.hand.is_ippatsu = False
                self.event_bus.emit(GameEvent(EventType.IPPATSU_CANCEL, {
                    "player": p.seat,
                }))

        # Restore: only cancel OTHER players' ippatsu
        self.players[player_idx].hand.is_ippatsu = False  # own ippatsu cancels on discard anyway

        # Track first discards for 4-wind abort
        if self.first_draw[player_idx]:
            self.first_draw[player_idx] = False
            self.first_discard_winds.append(tile.index34)

        self.event_bus.emit(GameEvent(EventType.DISCARD, {
            "player": player_idx,
            "tile": tile,
            "is_tsumogiri": is_tsumogiri,
        }))

    def process_call(self, action: Action):
        """Process a meld call (chi/pon/kan)."""
        player_idx = action.player
        hand = self.players[player_idx].hand
        meld = action.meld

        # Cancel all ippatsu
        for p in self.players:
            p.hand.is_ippatsu = False

        if meld.meld_type == MeldType.CHI:
            # Remove the tiles from hand (not the called tile)
            for t in meld.tiles:
                if t != meld.called_tile and t in hand.closed_tiles:
                    hand.closed_tiles.remove(t)
            hand.add_meld(meld)
            # Mark the discard as called
            if self.last_discard_player >= 0:
                dp = self.players[self.last_discard_player].hand.discard_pool
                if dp:
                    self.players[self.last_discard_player].hand.discard_called[-1] = True
            self.event_bus.emit(GameEvent(EventType.CHI, {
                "player": player_idx,
                "meld": meld,
            }))

        elif meld.meld_type == MeldType.PON:
            for t in meld.tiles:
                if t != meld.called_tile and t in hand.closed_tiles:
                    hand.closed_tiles.remove(t)
            hand.add_meld(meld)
            if self.last_discard_player >= 0:
                self.players[self.last_discard_player].hand.discard_called[-1] = True
            self.event_bus.emit(GameEvent(EventType.PON, {
                "player": player_idx,
                "meld": meld,
            }))

        elif meld.meld_type == MeldType.DAIMINKAN:
            for t in meld.tiles:
                if t != meld.called_tile and t in hand.closed_tiles:
                    hand.closed_tiles.remove(t)
            hand.add_meld(meld)
            if self.last_discard_player >= 0:
                self.players[self.last_discard_player].hand.discard_called[-1] = True
            self.kan_count_total += 1
            self.wall.reveal_new_dora()
            self.event_bus.emit(GameEvent(EventType.KAN, {
                "player": player_idx,
                "meld": meld,
                "new_dora": self.wall.dora_indicators[-1],
            }))

    def process_ankan(self, player_idx: int, tiles: List[Tile]):
        """Process an ankan (closed kan)."""
        hand = self.players[player_idx].hand
        for t in tiles:
            hand.closed_tiles.remove(t)
        meld = Meld(MeldType.ANKAN, tuple(tiles))
        hand.add_meld(meld)
        self.kan_count_total += 1
        self.wall.reveal_new_dora()

        # Cancel all ippatsu
        for p in self.players:
            p.hand.is_ippatsu = False

        self.event_bus.emit(GameEvent(EventType.KAN, {
            "player": player_idx,
            "meld": meld,
            "new_dora": self.wall.dora_indicators[-1],
        }))

    def process_shouminkan(self, player_idx: int, tile: Tile):
        """Process a shouminkan (added kan / promote pon)."""
        hand = self.players[player_idx].hand
        hand.closed_tiles.remove(tile)

        # Find the pon meld to upgrade
        for i, meld in enumerate(hand.melds):
            if meld.meld_type == MeldType.PON and meld.tile_index34 == tile.index34:
                new_meld = Meld(
                    MeldType.SHOUMINKAN,
                    meld.tiles + (tile,),
                    meld.called_tile,
                    meld.from_player,
                )
                hand.melds[i] = new_meld
                break

        self.kan_count_total += 1
        self.wall.reveal_new_dora()

        # Cancel all ippatsu
        for p in self.players:
            p.hand.is_ippatsu = False

        self.event_bus.emit(GameEvent(EventType.KAN, {
            "player": player_idx,
            "meld": new_meld,
            "new_dora": self.wall.dora_indicators[-1],
        }))

    def process_riichi(self, player_idx: int, discard_tile: Tile):
        """Process riichi declaration."""
        hand = self.players[player_idx].hand

        # Check for double riichi (first turn, no calls made)
        is_double = self.first_draw[player_idx] and all(
            len(p.hand.melds) == 0 for p in self.players
        )

        hand.is_riichi = True
        hand.is_ippatsu = True
        if is_double:
            hand.is_double_riichi = True

        self.riichi_declared_count += 1
        self.players[player_idx].score -= 1000
        self.riichi_sticks += 1

        hand.riichi_discard_index = len(hand.discard_pool)

        self.event_bus.emit(GameEvent(EventType.RIICHI_DECLARE, {
            "player": player_idx,
            "is_double": is_double,
        }))

        # Discard the riichi tile
        self.process_discard(player_idx, discard_tile)
        # Re-enable ippatsu (discard cancels it, but riichi discard should keep it)
        hand.is_ippatsu = True

    def process_tsumo(self, player_idx: int) -> ScoreResult:
        """Process tsumo (self-draw win)."""
        player = self.players[player_idx]
        hand = player.hand

        result = calculate_score(
            hand=hand,
            win_tile=hand.draw_tile,
            is_tsumo=True,
            seat_wind_34=player.seat_wind.index34,
            round_wind_34=self.round_wind.index34,
            is_dealer=player.is_dealer,
            dora_tiles_34=self.wall.get_dora_tiles_34(),
            uradora_tiles_34=self.wall.get_uradora_tiles_34(),
            honba=self.honba,
            is_riichi=hand.is_riichi,
            is_double_riichi=hand.is_double_riichi,
            is_ippatsu=hand.is_ippatsu,
            is_haitei=self.is_haitei,
            is_rinshan=self.is_rinshan,
            is_tenhou=(player.is_dealer and self.turn_count == 0),
            is_chiihou=(not player.is_dealer and self.first_draw[player_idx]),
            is_sanma=self.is_sanma,
        )

        if result:
            self.event_bus.emit(GameEvent(EventType.TSUMO, {
                "player": player_idx,
                "score_result": result,
            }))

            # Calculate score changes
            round_result = RoundResult()
            round_result.winners = [player_idx]
            round_result.score_results = [(player_idx, result)]

            if player.is_dealer:
                for i in range(self.num_players):
                    if i != player_idx:
                        round_result.score_changes[i] = -result.non_dealer_payment
                        round_result.score_changes[player_idx] += result.non_dealer_payment
            else:
                for i in range(self.num_players):
                    if i == player_idx:
                        continue
                    if self.players[i].is_dealer:
                        round_result.score_changes[i] = -result.dealer_payment
                        round_result.score_changes[player_idx] += result.dealer_payment
                    else:
                        round_result.score_changes[i] = -result.non_dealer_payment
                        round_result.score_changes[player_idx] += result.non_dealer_payment

            # Riichi sticks go to winner
            round_result.score_changes[player_idx] += self.riichi_sticks * 1000
            round_result.riichi_sticks_winner = player_idx

            round_result.dealer_continues = player.is_dealer
            self.result = round_result
            self.is_finished = True

        return result

    def process_ron(self, winner_idx: int, loser_idx: int,
                    win_tile: Tile) -> Optional[ScoreResult]:
        """Process ron (win off discard)."""
        player = self.players[winner_idx]
        hand = player.hand

        # Temporarily add the win tile for scoring
        test_hand = hand.clone()
        test_hand.closed_tiles.append(win_tile)

        is_last_tile = self.wall.remaining == 0

        result = calculate_score(
            hand=test_hand,
            win_tile=win_tile,
            is_tsumo=False,
            seat_wind_34=player.seat_wind.index34,
            round_wind_34=self.round_wind.index34,
            is_dealer=player.is_dealer,
            dora_tiles_34=self.wall.get_dora_tiles_34(),
            uradora_tiles_34=self.wall.get_uradora_tiles_34(),
            honba=self.honba,
            is_riichi=hand.is_riichi,
            is_double_riichi=hand.is_double_riichi,
            is_ippatsu=hand.is_ippatsu,
            is_houtei=is_last_tile,
            is_sanma=self.is_sanma,
        )

        return result

    def process_ron_result(self, winners: List[Tuple[int, ScoreResult]],
                           loser_idx: int):
        """Finalize ron results (supports multiple winners / double ron)."""
        round_result = RoundResult()
        round_result.loser = loser_idx

        total_from_loser = 0
        for winner_idx, result in winners:
            round_result.winners.append(winner_idx)
            round_result.score_results.append((winner_idx, result))
            round_result.score_changes[winner_idx] += result.ron_payment
            total_from_loser += result.ron_payment

            self.event_bus.emit(GameEvent(EventType.RON, {
                "player": winner_idx,
                "from_player": loser_idx,
                "score_result": result,
            }))

        round_result.score_changes[loser_idx] -= total_from_loser

        # Riichi sticks go to closest winner (head bump / 頭ハネ)
        closest = self._closest_player(loser_idx, [w for w, _ in winners])
        round_result.score_changes[closest] += self.riichi_sticks * 1000
        round_result.riichi_sticks_winner = closest

        round_result.dealer_continues = any(
            self.players[w].is_dealer for w, _ in winners
        )

        self.result = round_result
        self.is_finished = True

    def check_abortive_draw(self) -> Optional[str]:
        """Check for abortive draw conditions."""
        # Four winds (四風連打) - all 4 first discards are the same wind
        if (len(self.first_discard_winds) == self.num_players and
                all(w == self.first_discard_winds[0] for w in self.first_discard_winds) and
                27 <= self.first_discard_winds[0] <= 30):
            return "4wind"

        # Four kans by different players (四開槓)
        if self.kan_count_total >= 4:
            kan_players = set()
            for p in self.players[:self.num_players]:
                for m in p.hand.melds:
                    if m.is_kan:
                        kan_players.add(p.seat)
            if len(kan_players) >= 2:
                return "4kan"

        # Four riichi (四家立直)
        if self.riichi_declared_count >= self.num_players:
            return "4riichi"

        return None

    def process_exhaustive_draw(self):
        """Handle exhaustive draw (荒牌流局) with tenpai payments."""
        round_result = RoundResult()
        round_result.is_draw = True
        round_result.draw_type = "exhaustive"

        tenpai_players = []
        for i in range(self.num_players):
            hand = self.players[i].hand
            closed_34 = hand.to_34_array()
            if get_waiting_tiles(closed_34):
                tenpai_players.append(i)

        round_result.tenpai_players = tenpai_players
        noten_players = [i for i in range(self.num_players) if i not in tenpai_players]

        # Tenpai payments: 3000 total from noten to tenpai
        if 0 < len(tenpai_players) < self.num_players:
            total_payment = 3000
            pay_per_noten = total_payment // len(noten_players)
            receive_per_tenpai = total_payment // len(tenpai_players)

            for i in noten_players:
                round_result.score_changes[i] -= pay_per_noten
            for i in tenpai_players:
                round_result.score_changes[i] += receive_per_tenpai

        # Dealer continues if tenpai
        dealer_idx = next(
            (i for i in range(self.num_players) if self.players[i].is_dealer),
            0  # Default to player 0 if no dealer flag is set
        )
        round_result.dealer_continues = dealer_idx in tenpai_players

        self.result = round_result
        self.is_finished = True

        self.event_bus.emit(GameEvent(EventType.EXHAUSTIVE_DRAW, {
            "tenpai_players": tenpai_players,
        }))

    def process_abortive_draw(self, draw_type: str):
        """Handle abortive draw."""
        round_result = RoundResult()
        round_result.is_draw = True
        round_result.draw_type = draw_type
        round_result.dealer_continues = True  # Dealer always continues on abortive

        self.result = round_result
        self.is_finished = True

        self.event_bus.emit(GameEvent(EventType.ABORTIVE_DRAW, {
            "type": draw_type,
        }))

    def update_temp_furiten(self, discard_player: int, discard_tile: Tile):
        """Update temporary furiten for all other players."""
        tile_34 = discard_tile.index34
        for i in range(self.num_players):
            if i != discard_player:
                waits = get_hand_waiting_tiles(self.players[i].hand)
                if tile_34 in waits:
                    self.temp_furiten[i].add(tile_34)
                    if self.players[i].hand.is_riichi:
                        self.riichi_furiten[i].add(tile_34)

    def clear_temp_furiten(self, player_idx: int):
        """Clear temporary furiten when a player draws."""
        if not self.players[player_idx].hand.is_riichi:
            self.temp_furiten[player_idx].clear()

    def next_player(self, current: int) -> int:
        """Get the next player index."""
        return (current + 1) % self.num_players

    def _closest_player(self, from_player: int, candidates: List[int]) -> int:
        """Find the closest player in turn order (for head bump)."""
        for offset in range(1, self.num_players):
            check = (from_player + offset) % self.num_players
            if check in candidates:
                return check
        return candidates[0]

    def process_kita(self, player_idx: int):
        """Process kita (north tile declaration in sanma)."""
        hand = self.players[player_idx].hand
        north_tile = next(t for t in hand.closed_tiles if t.index34 == 30)
        hand.closed_tiles.remove(north_tile)
        self.players[player_idx].kita_tiles.append(north_tile)

        self.event_bus.emit(GameEvent(EventType.KITA, {
            "player": player_idx,
        }))


def run_round(round_state: RoundState, get_player_action) -> RoundResult:
    """Execute a complete round.

    Args:
        round_state: The round state
        get_player_action: Callable(player_idx, available_actions) -> Action

    Returns:
        RoundResult with final scores and outcomes.
    """
    rs = round_state
    rs.deal_tiles()

    current = rs.current_player
    need_draw = True

    while not rs.is_finished:
        if need_draw:
            # Draw phase
            if rs.wall.is_empty:
                rs.process_exhaustive_draw()
                break

            tile = rs.process_draw(current)
            if tile is None:
                rs.process_exhaustive_draw()
                break

            rs.clear_temp_furiten(current)
            rs.turn_count += 1

        need_draw = True

        # Player decides after draw
        available = rs.get_draw_actions(current)
        action = get_player_action(current, available)

        if action.action_type == ActionType.TSUMO:
            rs.process_tsumo(current)
            break

        elif action.action_type == ActionType.KYUUSHU:
            rs.process_abortive_draw("kyuushu")
            break

        elif action.action_type == ActionType.ANKAN:
            rs.process_ankan(current, [t for tiles in available.can_ankan
                                        for t in tiles
                                        if tiles[0].index34 == action.tile.index34])
            # Draw rinshan tile
            rtile = rs.process_rinshan_draw(current)
            if rtile is None:
                rs.process_exhaustive_draw()
                break

            # Check 4 kan abort
            abort = rs.check_abortive_draw()
            if abort:
                rs.process_abortive_draw(abort)
                break

            need_draw = False
            continue

        elif action.action_type == ActionType.SHOUMINKAN:
            # Check chankan (robbing the kan)
            chankan_winners = []
            for i in range(rs.num_players):
                if i == current:
                    continue
                resp = rs.get_response_actions(i, action.tile, current)
                if resp.can_ron:
                    chankan_action = get_player_action(i, resp)
                    if chankan_action.action_type == ActionType.RON:
                        result = rs.process_ron(i, current, action.tile)
                        if result:
                            chankan_winners.append((i, result))

            if chankan_winners:
                rs.process_ron_result(chankan_winners, current)
                break

            rs.process_shouminkan(current, action.tile)
            rtile = rs.process_rinshan_draw(current)
            if rtile is None:
                rs.process_exhaustive_draw()
                break

            abort = rs.check_abortive_draw()
            if abort:
                rs.process_abortive_draw(abort)
                break

            need_draw = False
            continue

        elif action.action_type == ActionType.KITA:
            rs.process_kita(current)
            rtile = rs.process_rinshan_draw(current)
            if rtile is None:
                rs.process_exhaustive_draw()
                break
            need_draw = False
            continue

        elif action.action_type == ActionType.RIICHI:
            discard_tile = action.riichi_discard or action.tile
            rs.process_riichi(current, discard_tile)

        elif action.action_type == ActionType.DISCARD:
            rs.process_discard(current, action.tile)

        else:
            # Shouldn't happen, but treat as discard of drawn tile
            if rs.players[current].hand.draw_tile:
                rs.process_discard(current, rs.players[current].hand.draw_tile)

        # After discard, check other players' responses
        discard_tile = rs.last_discard
        discard_player = rs.last_discard_player

        if discard_tile is None:
            current = rs.next_player(current)
            continue

        # Update furiten
        rs.update_temp_furiten(discard_player, discard_tile)

        # Collect responses
        ron_actions = []
        call_action = None

        # Check all players for ron first (highest priority)
        for offset in range(1, rs.num_players):
            i = (discard_player + offset) % rs.num_players
            resp = rs.get_response_actions(i, discard_tile, discard_player)
            if resp.can_ron:
                player_action = get_player_action(i, resp)
                if player_action.action_type == ActionType.RON:
                    result = rs.process_ron(i, discard_player, discard_tile)
                    if result:
                        ron_actions.append((i, result))

        if ron_actions:
            # Triple ron = abortive draw (in 4-player)
            if len(ron_actions) >= 3 and not rs.is_sanma:
                rs.process_abortive_draw("triple_ron")
                break
            rs.process_ron_result(ron_actions, discard_player)
            break

        # Check pon/kan (higher priority than chi)
        for offset in range(1, rs.num_players):
            i = (discard_player + offset) % rs.num_players
            resp = rs.get_response_actions(i, discard_tile, discard_player)
            has_call = resp.can_pon or resp.can_daiminkan
            if has_call:
                player_action = get_player_action(i, resp)
                if player_action.action_type in (ActionType.PON, ActionType.DAIMINKAN):
                    call_action = player_action
                    break

        # Check chi (lowest priority, only next player)
        if call_action is None:
            next_p = rs.next_player(discard_player)
            resp = rs.get_response_actions(next_p, discard_tile, discard_player)
            if resp.can_chi:
                player_action = get_player_action(next_p, resp)
                if player_action.action_type == ActionType.CHI:
                    call_action = player_action

        if call_action:
            rs.process_call(call_action)
            current = call_action.player

            if call_action.action_type == ActionType.DAIMINKAN:
                # Draw rinshan
                rtile = rs.process_rinshan_draw(current)
                if rtile is None:
                    rs.process_exhaustive_draw()
                    break
                abort = rs.check_abortive_draw()
                if abort:
                    rs.process_abortive_draw(abort)
                    break
                need_draw = False
                continue
            else:
                # After chi/pon, player must discard (no draw)
                available = rs.get_draw_actions(current)
                disc_action = get_player_action(current, available)
                if disc_action.action_type == ActionType.DISCARD:
                    rs.process_discard(current, disc_action.tile)
                else:
                    # Force discard last tile
                    rs.process_discard(current, available.can_discard[0])

                # Continue checking responses to this new discard
                current = rs.next_player(current)
                need_draw = True
                # Need to re-check after this discard
                # This is handled by the loop continuing
                # But we need to check for abort and go back to response phase
                discard_tile = rs.last_discard
                discard_player = rs.last_discard_player
                rs.update_temp_furiten(discard_player, discard_tile)

                abort = rs.check_abortive_draw()
                if abort:
                    rs.process_abortive_draw(abort)
                    break

                # Check for ron on this new discard
                new_ron_actions = []
                for offset in range(1, rs.num_players):
                    ii = (discard_player + offset) % rs.num_players
                    resp = rs.get_response_actions(ii, discard_tile, discard_player)
                    if resp.can_ron:
                        pa = get_player_action(ii, resp)
                        if pa.action_type == ActionType.RON:
                            res = rs.process_ron(ii, discard_player, discard_tile)
                            if res:
                                new_ron_actions.append((ii, res))
                if new_ron_actions:
                    if len(new_ron_actions) >= 3 and not rs.is_sanma:
                        rs.process_abortive_draw("triple_ron")
                    else:
                        rs.process_ron_result(new_ron_actions, discard_player)
                    break

                continue
        else:
            # No calls, move to next player
            abort = rs.check_abortive_draw()
            if abort:
                rs.process_abortive_draw(abort)
                break
            current = rs.next_player(current)

    return rs.result
