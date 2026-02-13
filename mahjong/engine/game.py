"""Game management - hanchan (半荘) / tonpuusen (東風戦)."""

from typing import List, Optional, Callable

from mahjong.core.wall import Wall
from mahjong.core.player_state import PlayerState, Wind
from mahjong.engine.event import EventBus, EventType, GameEvent
from mahjong.engine.round import RoundState, RoundResult, run_round


class GameConfig:
    """Game configuration."""

    def __init__(
        self,
        num_players: int = 4,
        is_sanma: bool = False,
        is_tonpuu: bool = False,  # East-only (東風戦) vs half game (半荘)
        starting_score: int = 25000,
        target_score: int = 30000,
    ):
        self.num_players = num_players
        self.is_sanma = is_sanma
        self.is_tonpuu = is_tonpuu
        self.starting_score = starting_score
        self.target_score = target_score

        if is_sanma:
            self.num_players = 3


class GameState:
    """Manages a complete game (hanchan or tonpuusen)."""

    def __init__(self, config: GameConfig, player_names: List[str],
                 event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus

        # Create players
        self.players = []
        for i, name in enumerate(player_names[:config.num_players]):
            self.players.append(PlayerState(i, name, config.starting_score))

        # Game progression
        self.round_wind = Wind.EAST
        self.round_number = 0  # 0-based within current wind (東1=0, 東2=1, ...)
        self.honba = 0
        self.riichi_sticks = 0

        # History
        self.round_results: List[RoundResult] = []
        self.is_finished = False
        self.final_scores: List[int] = []

    @property
    def round_label(self) -> str:
        """Human-readable round label like '東一局' (localized)."""
        from mahjong.ui.i18n import t
        wind = self.round_wind.display_name
        number = t(f'round.numbers.{self.round_number}')
        label = t('round.format', wind=wind, number=number)
        honba_str = t('round.honba', n=self.honba) if self.honba > 0 else ""
        return f"{label}{honba_str}"

    @property
    def dealer_seat(self) -> int:
        """Current dealer seat index."""
        return self.round_number % self.config.num_players

    def setup_round(self) -> RoundState:
        """Set up state for a new round."""
        # Assign seat winds
        for i in range(self.config.num_players):
            wind_idx = (i - self.dealer_seat) % self.config.num_players
            self.players[i].seat_wind = Wind(wind_idx)
            self.players[i].is_dealer = (wind_idx == 0)
            self.players[i].reset_for_round(
                Wind(wind_idx), wind_idx == 0
            )

        wall = Wall(is_sanma=self.config.is_sanma)

        round_state = RoundState(
            players=self.players,
            wall=wall,
            round_wind=self.round_wind,
            honba=self.honba,
            riichi_sticks=self.riichi_sticks,
            event_bus=self.event_bus,
            is_sanma=self.config.is_sanma,
        )
        round_state.current_player = self.dealer_seat

        return round_state

    def advance_round(self, result: RoundResult):
        """Advance game state based on round result."""
        self.round_results.append(result)

        # Apply score changes
        for i in range(self.config.num_players):
            self.players[i].score += result.score_changes[i]

        # Handle riichi sticks
        if result.riichi_sticks_winner is not None:
            self.riichi_sticks = 0
        # Unreturned riichi sticks stay on the table

        # Check for player bust (飛び)
        for p in self.players:
            if p.score < 0:
                self.is_finished = True
                self._finalize()
                return

        if result.dealer_continues:
            self.honba += 1
        else:
            self.honba = 0 if not result.is_draw else self.honba + 1
            self._advance_dealer()

        # Check game end
        if self._check_game_end():
            self.is_finished = True
            self._finalize()

    def _advance_dealer(self):
        """Move to next round/dealer."""
        self.round_number += 1
        max_rounds = self.config.num_players

        if self.round_number >= max_rounds:
            self.round_number = 0
            if self.round_wind == Wind.EAST:
                if self.config.is_tonpuu:
                    # Check if top player has target_score
                    top_score = max(p.score for p in self.players)
                    if top_score >= self.config.target_score:
                        self.is_finished = True
                    else:
                        self.round_wind = Wind.SOUTH
                else:
                    self.round_wind = Wind.SOUTH
            elif self.round_wind == Wind.SOUTH:
                # End of south round
                self.is_finished = True

    def _check_game_end(self) -> bool:
        """Check if game should end."""
        if self.is_finished:
            return True

        # South 4 completed (or South 3 in sanma)
        if self.round_wind == Wind.SOUTH and self.round_number >= self.config.num_players:
            return True

        # Check if leader has target score at end of all-last
        max_rounds = self.config.num_players
        if self.round_wind == Wind.SOUTH and self.round_number == max_rounds - 1:
            top_score = max(p.score for p in self.players)
            if top_score >= self.config.target_score:
                return True

        return False

    def _finalize(self):
        """Calculate final scores and rankings."""
        self.final_scores = [p.score for p in self.players]

        self.event_bus.emit(GameEvent(EventType.GAME_END, {
            "scores": self.final_scores,
            "players": [(p.name, p.score) for p in self.players],
        }))


def run_game(config: GameConfig, player_names: List[str],
             get_player_action: Callable, event_bus: EventBus) -> GameState:
    """Run a complete game.

    Args:
        config: Game configuration
        player_names: Names for each player
        get_player_action: Callable(player_idx, available_actions) -> Action
        event_bus: Event bus for UI updates

    Returns:
        Completed GameState
    """
    game = GameState(config, player_names, event_bus)

    game.event_bus.emit(GameEvent(EventType.GAME_START, {
        "config": config,
        "players": [(p.name, p.score) for p in game.players],
    }))

    while not game.is_finished:
        round_state = game.setup_round()
        result = run_round(round_state, get_player_action)
        if result:
            game.advance_round(result)
        else:
            break

    return game
