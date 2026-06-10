"""Replay state reconstruction from logged actions.

GameLogger records stable tile strings ("5m", "0m" for red five, kanji
honors) and the full post-shuffle wall as 136-encoding ids. This module
rebuilds per-step board states by applying logged actions in order.

No UI dependencies: rendering lives in mahjong/ui/replay_screen.py.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from mahjong.core.tile import (
    Tile, ALL_TILES_136, next_tile_index,
    RED_FIVE_MAN, RED_FIVE_PIN, RED_FIVE_SOU,
)

_HONOR_NAMES = {"東": 27, "南": 28, "西": 29, "北": 30,
                "白": 31, "發": 32, "中": 33}
_RED_IDS = {"0m": RED_FIVE_MAN, "0p": RED_FIVE_PIN, "0s": RED_FIVE_SOU}
_SUIT_OFFSETS = {"m": 0, "p": 9, "s": 18}


def parse_tile_str(s: str) -> Tile:
    """Parse a logged tile string back into a Tile object.

    Red fives map to their unique red tile ids; everything else maps to
    the first tile id of its kind (identity within a kind is irrelevant
    for replay display).
    """
    if s in _RED_IDS:
        return ALL_TILES_136[_RED_IDS[s]]
    if s in _HONOR_NAMES:
        return ALL_TILES_136[_HONOR_NAMES[s] * 4]
    if len(s) == 2 and s[0].isdigit() and s[1] in _SUIT_OFFSETS:
        index34 = _SUIT_OFFSETS[s[1]] + int(s[0]) - 1
        tile = ALL_TILES_136[index34 * 4]
        if tile.is_red:
            # The first id of each five IS the red tile; "5m" means non-red
            tile = ALL_TILES_136[index34 * 4 + 1]
        return tile
    raise ValueError(f"unknown tile string: {s!r}")


@dataclass
class ReplayMeld:
    """A meld as reconstructed from the log."""
    kind: str  # "chi" / "pon" / "ankan" / "daiminkan" / "shouminkan"
    tiles: List[Tile]


@dataclass
class PlayerReplay:
    """One player's visible state at the current replay step."""
    seat: int
    name: str
    is_dealer: bool = False
    closed: List[Tile] = field(default_factory=list)
    draw_tile: Optional[Tile] = None
    discards: List[Tile] = field(default_factory=list)
    discard_called: List[bool] = field(default_factory=list)
    melds: List[ReplayMeld] = field(default_factory=list)
    is_riichi: bool = False
    riichi_index: int = -1
    kita_count: int = 0

    def _remove(self, tile_str: str):
        """Remove one tile matching the logged string from the closed hand."""
        from mahjong.ui.tile_display import tile_to_simple_str
        for i, t in enumerate(self.closed):
            if tile_to_simple_str(t) == tile_str:
                return self.closed.pop(i)
        raise ValueError(
            f"replay desync: {self.name} has no {tile_str!r} in hand")


class RoundReplay:
    """Step-by-step state reconstruction for one logged round.

    Usage:
        rr = RoundReplay(round_data, player_names, is_sanma)
        rr.goto(n)       # state after the first n actions (0 = after deal)
        rr.players, rr.dora_indicators, rr.remaining, ...
    """

    def __init__(self, round_data: dict, player_names: List[str],
                 is_sanma: bool = False):
        self.data = round_data
        self.player_names = list(player_names)
        self.is_sanma = is_sanma
        self.actions: List[dict] = round_data.get("actions", [])
        self.result: Optional[dict] = round_data.get("result")

        wall_ids = round_data["wall"]["tile_ids"]
        self._dead_wall = [ALL_TILES_136[i] for i in wall_ids[-14:]]
        self._initial_live = len(wall_ids) - 14

        self.step = 0
        self.players: List[PlayerReplay] = []
        self.remaining = 0
        self.kan_count = 0
        self.last_discard: Optional[Tuple[int, str]] = None  # (seat, tile_str)
        self._pending_riichi: set = set()
        self.reset()

    # ------------------------------------------------------------------
    # State construction
    # ------------------------------------------------------------------

    def reset(self):
        """Back to the post-deal state (step 0)."""
        self.players = []
        hands = self.data["initial_hands"]
        for name in self.player_names:
            info = hands[name]
            p = PlayerReplay(seat=info["seat"], name=name,
                             is_dealer=info.get("is_dealer", False))
            p.closed = sorted(parse_tile_str(s) for s in info["tiles"])
            self.players.append(p)
        self.players.sort(key=lambda p: p.seat)

        self.remaining = self._initial_live
        self.kan_count = 0
        self.last_discard = None
        self._pending_riichi = set()
        self.step = 0

    @property
    def num_steps(self) -> int:
        return len(self.actions)

    def goto(self, n: int):
        """Rebuild the state after the first n actions (clamped to range)."""
        n = max(0, min(n, self.num_steps))
        if n < self.step:
            self.reset()
        while self.step < n:
            self._apply(self.actions[self.step])
            self.step += 1

    @property
    def dora_indicators(self) -> List[Tile]:
        """Dora indicators revealed so far (1 + one per kan, max 5).

        Note: the engine delays the kakan dora flip until after the
        replacement draw; the replay reveals it at the kan step, which can
        be one action early around shouminkan.
        """
        revealed = min(1 + self.kan_count, 5)
        return [self._dead_wall[i * 2] for i in range(revealed)]

    @property
    def dora_tiles_34(self) -> List[int]:
        return [next_tile_index(ind.index34, self.is_sanma)
                for ind in self.dora_indicators]

    @property
    def current_action(self) -> Optional[dict]:
        """The action that produced the current state (None at step 0)."""
        if self.step == 0:
            return None
        return self.actions[self.step - 1]

    @property
    def is_finished(self) -> bool:
        return self.step >= self.num_steps

    # ------------------------------------------------------------------
    # Action application
    # ------------------------------------------------------------------

    def _apply(self, action: dict):
        kind = action["action"]
        seat = action["seat"]
        p = self.players[seat]

        if kind == "draw":
            tile = parse_tile_str(action["tile"])
            p.closed.append(tile)
            p.draw_tile = tile
            if not action.get("is_rinshan"):
                self.remaining -= 1

        elif kind == "discard":
            p._remove(action["tile"])
            p.discards.append(parse_tile_str(action["tile"]))
            p.discard_called.append(False)
            p.draw_tile = None
            self.last_discard = (seat, action["tile"])
            if seat in self._pending_riichi:
                p.is_riichi = True
                p.riichi_index = len(p.discards) - 1
                self._pending_riichi.discard(seat)

        elif kind in ("chi", "pon", "daiminkan"):
            tiles = list(action["tiles"])
            # The called tile comes from the previous discard; the rest
            # leave the caller's hand.
            from_hand = list(tiles)
            if self.last_discard is not None:
                discarder, called_str = self.last_discard
                if called_str in from_hand:
                    from_hand.remove(called_str)
                dp = self.players[discarder]
                if dp.discard_called:
                    dp.discard_called[-1] = True
            for s in from_hand:
                p._remove(s)
            p.melds.append(ReplayMeld(kind, [parse_tile_str(s) for s in tiles]))
            p.draw_tile = None
            if kind == "daiminkan":
                self._on_kan()

        elif kind == "ankan":
            tiles = list(action["tiles"])
            for s in tiles:
                p._remove(s)
            p.melds.append(ReplayMeld(kind, [parse_tile_str(s) for s in tiles]))
            p.draw_tile = None
            self._on_kan()

        elif kind == "shouminkan":
            tiles = list(action["tiles"])
            # One tile leaves the hand; the pon meld upgrades in place.
            kan_index34 = parse_tile_str(tiles[0]).index34
            for s in tiles:
                try:
                    p._remove(s)
                    break
                except ValueError:
                    continue
            for m in p.melds:
                if m.kind == "pon" and m.tiles[0].index34 == kan_index34:
                    m.kind = "shouminkan"
                    m.tiles = [parse_tile_str(s) for s in tiles]
                    break
            p.draw_tile = None
            self._on_kan()

        elif kind == "riichi":
            # The riichi tile is the next discard by this player.
            self._pending_riichi.add(seat)

        elif kind == "kita":
            p._remove("北")
            p.kita_count += 1
            p.draw_tile = None

        elif kind in ("tsumo", "ron"):
            pass  # Terminal markers; result panel comes from self.result

    def _on_kan(self):
        self.kan_count += 1
        # Each kan moves one live-wall tile to replenish the dead wall.
        self.remaining -= 1
