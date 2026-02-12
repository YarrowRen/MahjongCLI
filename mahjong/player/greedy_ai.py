"""Greedy AI player - optimizes for shanten reduction with basic defense."""

from typing import List, Optional

from mahjong.core.tile import Tile, YAOCHU_INDICES, tiles_to_34_array
from mahjong.core.meld import Meld
from mahjong.engine.action import Action, ActionType, AvailableActions
from mahjong.player.base import Player, GameView
from mahjong.rules.shanten import shanten


class GreedyAI(Player):
    """AI that greedily minimizes shanten with basic defensive play.

    Strategy:
    - Offense: Choose discards that minimize shanten number
    - Calling: Accept pon/chi if it reduces shanten (but protect menzen potential)
    - Riichi: Declare if tenpai and score >= 1000
    - Defense: When opponent riichi and own shanten >= 2, play safe tiles
    """

    def choose_action(self, game_view: GameView,
                      available: AvailableActions) -> Action:
        """Choose the best available action."""
        # Always tsumo if possible
        if available.can_tsumo:
            return Action(ActionType.TSUMO, available.player)

        # Always ron if possible
        if available.can_ron:
            return Action(ActionType.RON, available.player)

        # Consider riichi
        if available.can_riichi:
            best_discard = self.choose_riichi_discard(
                game_view, available.riichi_candidates)
            return Action(ActionType.RIICHI, available.player,
                          riichi_discard=best_discard)

        # Consider ankan (if it doesn't worsen shanten)
        if available.can_ankan:
            for kan_tiles in available.can_ankan:
                return Action(ActionType.ANKAN, available.player,
                              tile=kan_tiles[0])

        # Consider shouminkan
        if available.can_shouminkan:
            # Only kan if not in danger
            if not self._should_defend(game_view):
                return Action(ActionType.SHOUMINKAN, available.player,
                              tile=available.can_shouminkan[0])

        # Consider pon
        if available.can_pon:
            if self._should_call_pon(game_view, available.can_pon[0]):
                return Action(ActionType.PON, available.player,
                              meld=available.can_pon[0])

        # Consider chi
        if available.can_chi:
            for chi_meld in available.can_chi:
                if self._should_call_chi(game_view, chi_meld):
                    return Action(ActionType.CHI, available.player,
                                  meld=chi_meld)

        # Default: discard
        if available.can_discard:
            tile = self.choose_discard(game_view, available.can_discard)
            return Action(ActionType.DISCARD, available.player, tile=tile)

        return Action(ActionType.SKIP, available.player)

    def choose_discard(self, game_view: GameView,
                       available_discards: List[Tile]) -> Tile:
        """Choose the best tile to discard."""
        hand = game_view.my_hand

        # If defending, play safe
        if self._should_defend(game_view):
            safe = self._find_safe_tile(game_view, available_discards)
            if safe:
                return safe

        # Offense: minimize shanten
        return self._best_discard_for_shanten(hand, available_discards)

    def choose_riichi_discard(self, game_view: GameView,
                              riichi_candidates: List[Tile]) -> Tile:
        """Choose the best riichi discard (maximize waiting tiles)."""
        hand = game_view.my_hand
        best_tile = riichi_candidates[0]
        best_waits = 0

        from mahjong.rules.agari import get_waiting_tiles

        for tile in riichi_candidates:
            test_34 = hand.to_34_array()
            test_34[tile.index34] -= 1
            waits = get_waiting_tiles(test_34)
            # Count remaining copies of waiting tiles
            wait_count = sum(4 - test_34[w] for w in waits)  # Rough estimate
            if wait_count > best_waits:
                best_waits = wait_count
                best_tile = tile

        return best_tile

    def _best_discard_for_shanten(self, hand, available: List[Tile]) -> Tile:
        """Find the discard that minimizes shanten."""
        best_tile = available[0]
        best_shanten = 99
        best_priority = 99

        current_34 = hand.to_34_array()

        seen = set()
        for tile in available:
            if tile.index34 in seen:
                continue
            seen.add(tile.index34)

            test_34 = list(current_34)
            test_34[tile.index34] -= 1
            s = shanten(test_34)

            # Tiebreaker priority: honors > terminals > middle tiles
            priority = self._tile_discard_priority(tile)

            if s < best_shanten or (s == best_shanten and priority < best_priority):
                best_shanten = s
                best_priority = priority
                best_tile = tile

        return best_tile

    def _tile_discard_priority(self, tile: Tile) -> int:
        """Lower = more willing to discard. Prefer discarding isolated tiles."""
        if tile.is_honor:
            return 0  # Most willing to discard isolated honors
        if tile.is_terminal:
            return 1
        return 2  # Middle tiles last

    def _should_defend(self, game_view: GameView) -> bool:
        """Check if we should switch to defensive play."""
        hand = game_view.my_hand
        current_shanten = shanten(hand.to_34_array())

        # Defend if any opponent declared riichi and we're far from tenpai
        for opp in game_view.opponents:
            if opp.is_riichi and current_shanten >= 2:
                return True
        return False

    def _find_safe_tile(self, game_view: GameView,
                        available: List[Tile]) -> Optional[Tile]:
        """Find a safe tile to discard (defensive play)."""
        riichi_players = [opp for opp in game_view.opponents if opp.is_riichi]
        if not riichi_players:
            return None

        # Collect all discards from riichi players (genbutsu / 現物 = safe tiles)
        safe_indices = set()
        for opp in riichi_players:
            for t in opp.discard_pool:
                safe_indices.add(t.index34)

        # Priority 1: Play genbutsu (tiles already in riichi player's discard)
        for tile in available:
            if tile.index34 in safe_indices:
                return tile

        # Priority 2: Play tiles that have 3+ visible copies (suji/kabe defense)
        # This is a simplified version
        all_visible_34 = [0] * 34
        for opp in game_view.opponents:
            for t in opp.discard_pool:
                all_visible_34[t.index34] += 1
            for m in opp.melds:
                for t in m.tiles:
                    all_visible_34[t.index34] += 1

        for t in game_view.my_hand.discard_pool:
            all_visible_34[t.index34] += 1

        # Prefer honor tiles and terminals when no safe tile available
        available_sorted = sorted(available,
                                  key=lambda t: self._danger_score(t, all_visible_34))
        return available_sorted[0]

    def _danger_score(self, tile: Tile, visible_34: List[int]) -> int:
        """Lower = safer. Score danger level of a tile."""
        # Already 3+ visible = very safe
        if visible_34[tile.index34] >= 3:
            return 0
        if tile.is_honor:
            if visible_34[tile.index34] >= 2:
                return 1
            return 5
        if tile.is_terminal:
            return 3
        return 7  # Middle number tiles are most dangerous

    def _should_call_pon(self, game_view: GameView, meld: Meld) -> bool:
        """Decide whether to call pon."""
        hand = game_view.my_hand

        # Don't call if defending
        if self._should_defend(game_view):
            return False

        # Calculate shanten before and after
        current_34 = hand.to_34_array()
        current_s = shanten(current_34)

        # Simulate: remove 2 tiles for pon, reduce closed count
        test_34 = list(current_34)
        idx = meld.tile_index34
        test_34[idx] -= 2

        # After pon, we need to discard, find best
        new_s = 99
        for i in range(34):
            if test_34[i] > 0:
                test_34[i] -= 1
                s = shanten(test_34)
                new_s = min(new_s, s)
                test_34[i] += 1

        return new_s < current_s

    def _should_call_chi(self, game_view: GameView, meld: Meld) -> bool:
        """Decide whether to call chi."""
        hand = game_view.my_hand

        if self._should_defend(game_view):
            return False

        current_34 = hand.to_34_array()
        current_s = shanten(current_34)

        # Simulate chi
        test_34 = list(current_34)
        for t in meld.tiles:
            if t != meld.called_tile:
                test_34[t.index34] -= 1

        new_s = 99
        for i in range(34):
            if test_34[i] > 0:
                test_34[i] -= 1
                s = shanten(test_34)
                new_s = min(new_s, s)
                test_34[i] += 1

        return new_s < current_s
