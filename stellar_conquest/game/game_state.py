"""Central game state management for Stellar Conquest."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import uuid
from datetime import datetime

from ..core.enums import GamePhase, PlayStyle
from ..core.exceptions import GameStateError, ValidationError, InvalidActionError
from ..core.constants import MAX_PLAYERS, MIN_PLAYERS, STARTING_VICTORY_POINTS_TARGET
from ..utils.validation import GameValidator, Validator
from ..entities.player import Player, create_starting_player
from ..entities.base import EntityManager
from .board import GameBoard


class GameStatus(Enum):
    """Game status enumeration."""
    SETUP = "setup"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass
class GameSettings:
    """Configuration settings for a game."""
    
    max_turns: int = 50
    victory_points_target: int = STARTING_VICTORY_POINTS_TARGET
    allow_ai_players: bool = True
    enable_what_if_mode: bool = False
    auto_save_turns: bool = True
    exploration_risk: bool = True
    
    def validate(self) -> None:
        """Validate game settings."""
        Validator.validate_range(self.max_turns, 1, 200, "max_turns")
        Validator.validate_range(self.victory_points_target, 10, 1000, "victory_points_target")
        Validator.validate_type(self.allow_ai_players, bool, "allow_ai_players")
        Validator.validate_type(self.enable_what_if_mode, bool, "enable_what_if_mode")


@dataclass
class GameState:
    """Central game state coordinator."""
    
    game_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: GameStatus = GameStatus.SETUP
    settings: GameSettings = field(default_factory=GameSettings)
    
    # Game progression
    current_turn: int = 0
    current_phase: GamePhase = GamePhase.SETUP
    current_player_index: int = 0
    
    # Players and entities
    players: List[Player] = field(default_factory=list)
    player_order: List[int] = field(default_factory=list)
    eliminated_players: Set[int] = field(default_factory=set)
    
    # Game components
    board: Optional[GameBoard] = None
    entity_manager: Optional[EntityManager] = None
    
    # Game history
    turn_history: List[Dict[str, Any]] = field(default_factory=list)
    action_log: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_action_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Initialize game state."""
        if not self.board:
            self.board = GameBoard(self.game_id)
        
        if not self.entity_manager:
            self.entity_manager = EntityManager(self.game_id)
            self._setup_entity_collections()
    
    def _setup_entity_collections(self) -> None:
        """Setup entity collections in the manager."""
        from ..entities.player import Player
        from ..entities.ship import Ship
        from ..entities.colony import Colony
        from ..entities.planet import Planet, StarSystem
        
        self.entity_manager.register_collection("players", Player)
        self.entity_manager.register_collection("ships", Ship)  
        self.entity_manager.register_collection("colonies", Colony)
        self.entity_manager.register_collection("planets", Planet)
        self.entity_manager.register_collection("star_systems", StarSystem)
    
    def validate(self) -> None:
        """Validate entire game state."""
        self.settings.validate()
        Validator.validate_enum(self.status, GameStatus, "status")
        Validator.validate_enum(self.current_phase, GamePhase, "current_phase")
        Validator.validate_non_negative(self.current_turn, "current_turn")
        Validator.validate_range(self.current_player_index, 0, len(self.players), "current_player_index")
        
        # Validate players
        if len(self.players) < MIN_PLAYERS:
            raise GameStateError(f"Not enough players: {len(self.players)} < {MIN_PLAYERS}")
        
        if len(self.players) > MAX_PLAYERS:
            raise GameStateError(f"Too many players: {len(self.players)} > {MAX_PLAYERS}")
        
        for player in self.players:
            player.validate()
        
        # Validate board
        if self.board:
            self.board.validate()
    
    @property
    def is_setup(self) -> bool:
        """Check if game is in setup phase."""
        return self.status == GameStatus.SETUP
    
    @property
    def is_active(self) -> bool:
        """Check if game is actively running."""
        return self.status == GameStatus.IN_PROGRESS
    
    @property
    def is_completed(self) -> bool:
        """Check if game has ended."""
        return self.status == GameStatus.COMPLETED
    
    @property
    def current_player(self) -> Optional[Player]:
        """Get the current active player."""
        if not self.players or self.current_player_index >= len(self.players):
            return None
        
        player_id = self.player_order[self.current_player_index]
        return self.get_player_by_id(player_id)
    
    @property
    def active_players(self) -> List[Player]:
        """Get all non-eliminated players."""
        return [p for p in self.players if p.player_id not in self.eliminated_players]
    
    @property
    def game_winner(self) -> Optional[Player]:
        """Get game winner if game is completed."""
        if not self.is_completed:
            return None
        
        # Find player with most victory points
        active = self.active_players
        if not active:
            return None
        
        return max(active, key=lambda p: p.calculate_victory_points())
    
    def add_player(self, name: str, play_style: PlayStyle, entry_hex: str, is_ai: bool = False) -> Player:
        """Add a player to the game."""
        if not self.is_setup:
            raise GameStateError("Cannot add players after game starts")
        
        if len(self.players) >= MAX_PLAYERS:
            raise GameStateError(f"Cannot add more than {MAX_PLAYERS} players")
        
        # Validate entry hex is available
        if any(p.entry_hex == entry_hex for p in self.players):
            raise GameStateError(f"Entry hex {entry_hex} already taken")
        
        player_id = len(self.players) + 1
        player = create_starting_player(player_id, name, play_style, entry_hex)
        player.game_id = self.game_id
        
        self.players.append(player)
        self.player_order.append(player_id)
        
        # Add to entity manager
        players_collection = self.entity_manager.get_collection("players")
        if players_collection:
            players_collection.add(player)
        
        self._log_action("player_added", {"player_id": player_id, "name": name, "entry_hex": entry_hex})
        return player
    
    def remove_player(self, player_id: int) -> bool:
        """Remove a player from the game."""
        if not self.is_setup:
            raise GameStateError("Cannot remove players after game starts")
        
        player = self.get_player_by_id(player_id)
        if not player:
            return False
        
        self.players.remove(player)
        if player_id in self.player_order:
            self.player_order.remove(player_id)
        
        # Remove from entity manager
        players_collection = self.entity_manager.get_collection("players")
        if players_collection:
            players_collection.remove(player.id)
        
        self._log_action("player_removed", {"player_id": player_id})
        return True
    
    def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """Get player by ID."""
        for player in self.players:
            if player.player_id == player_id:
                return player
        return None
    
    def get_player_by_name(self, name: str) -> Optional[Player]:
        """Get player by name."""
        for player in self.players:
            if player.name == name:
                return player
        return None
    
    def start_game(self) -> None:
        """Start the game."""
        if not self.is_setup:
            raise GameStateError("Game is not in setup phase")
        
        if len(self.players) < MIN_PLAYERS:
            raise GameStateError(f"Need at least {MIN_PLAYERS} players to start")
        
        self.status = GameStatus.IN_PROGRESS
        self.current_turn = 1
        self.current_phase = GamePhase.MOVEMENT
        self.current_player_index = 0
        self.started_at = datetime.now()
        
        # Initialize board
        self.board.initialize_game()
        
        # Initialize starting fleets for all players
        for player in self.players:
            player.initialize_starting_fleet()
        
        self._log_action("game_started", {
            "player_count": len(self.players),
            "settings": self.settings.__dict__
        })
    
    def pause_game(self) -> None:
        """Pause the game."""
        if not self.is_active:
            raise GameStateError("Game is not active")
        
        self.status = GameStatus.PAUSED
        self._log_action("game_paused", {})
    
    def resume_game(self) -> None:
        """Resume the game."""
        if self.status != GameStatus.PAUSED:
            raise GameStateError("Game is not paused")
        
        self.status = GameStatus.IN_PROGRESS
        self._log_action("game_resumed", {})
    
    def end_game(self, reason: str = "completed") -> None:
        """End the game."""
        if self.is_completed:
            return
        
        self.status = GameStatus.COMPLETED
        self.completed_at = datetime.now()
        
        winner = self.game_winner
        self._log_action("game_ended", {
            "reason": reason,
            "winner": winner.name if winner else None,
            "final_scores": {p.name: p.calculate_victory_points() for p in self.active_players}
        })
    
    def eliminate_player(self, player_id: int, reason: str = "defeated") -> None:
        """Eliminate a player from the game."""
        if player_id in self.eliminated_players:
            return
        
        self.eliminated_players.add(player_id)
        self._log_action("player_eliminated", {"player_id": player_id, "reason": reason})
        
        # Check if game should end
        if len(self.active_players) <= 1:
            self.end_game("elimination")
    
    def check_victory_conditions(self) -> Optional[Player]:
        """Check if any player has won the game."""
        if not self.is_active:
            return None
        
        # Victory by points
        for player in self.active_players:
            if player.calculate_victory_points() >= self.settings.victory_points_target:
                self.end_game("victory_points")
                return player
        
        # Victory by turn limit
        if self.current_turn >= self.settings.max_turns:
            self.end_game("turn_limit")
            return self.game_winner
        
        return None
    
    def advance_to_next_player(self) -> None:
        """Advance to next player in turn order."""
        self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
        
        # Skip eliminated players
        attempts = 0
        while (self.player_order[self.current_player_index] in self.eliminated_players and 
               attempts < len(self.player_order)):
            self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
            attempts += 1
    
    def advance_phase(self) -> None:
        """Advance to next game phase."""
        phase_order = [
            GamePhase.MOVEMENT,
            GamePhase.EXPLORATION, 
            GamePhase.COLONIZATION,
            GamePhase.COMBAT,
            GamePhase.PRODUCTION
        ]
        
        current_index = phase_order.index(self.current_phase)
        
        if current_index < len(phase_order) - 1:
            # Move to next phase
            self.current_phase = phase_order[current_index + 1]
        else:
            # End of turn - advance to next turn
            self.advance_turn()
    
    def advance_turn(self) -> None:
        """Advance to next turn."""
        self.current_turn += 1
        self.current_phase = GamePhase.MOVEMENT
        self.current_player_index = 0
        
        # Process end-of-turn activities
        self._process_end_of_turn()
        
        # Check victory conditions
        self.check_victory_conditions()
        
        self._log_action("turn_advanced", {"turn": self.current_turn})
    
    def _process_end_of_turn(self) -> None:
        """Process end-of-turn activities."""
        # Production happens every 4th turn
        if self.current_turn % 4 == 0:
            for player in self.active_players:
                results = player.process_production_turn()
                self._log_action("production_processed", {
                    "player_id": player.player_id,
                    "results": results
                })
        
        # Cleanup destroyed entities
        total_cleaned = 0
        for player in self.players:
            cleaned = player.cleanup_destroyed_entities()
            total_cleaned += sum(cleaned.values())
        
        if total_cleaned > 0:
            self._log_action("entities_cleaned", {"count": total_cleaned})
        
        # Save turn state
        self._save_turn_state()
    
    def _save_turn_state(self) -> None:
        """Save current turn state to history."""
        turn_state = {
            "turn": self.current_turn,
            "phase": self.current_phase.value,
            "timestamp": datetime.now().isoformat(),
            "player_states": {
                p.player_id: p.get_strategic_summary() for p in self.active_players
            }
        }
        self.turn_history.append(turn_state)
    
    def _log_action(self, action_type: str, data: Dict[str, Any]) -> None:
        """Log a game action."""
        action_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "turn": self.current_turn,
            "phase": self.current_phase.value,
            "action_type": action_type,
            "current_player": self.current_player.player_id if self.current_player else None,
            "data": data
        }
        self.action_log.append(action_entry)
        self.last_action_at = datetime.now()
    
    def get_game_summary(self) -> Dict[str, Any]:
        """Get comprehensive game summary."""
        return {
            "game_id": self.game_id,
            "status": self.status.value,
            "current_turn": self.current_turn,
            "current_phase": self.current_phase.value,
            "player_count": len(self.active_players),
            "eliminated_count": len(self.eliminated_players),
            "current_player": self.current_player.name if self.current_player else None,
            "winner": self.game_winner.name if self.game_winner else None,
            "duration_minutes": (
                (self.completed_at or datetime.now()) - (self.started_at or self.created_at)
            ).total_seconds() / 60,
            "total_actions": len(self.action_log),
            "player_scores": {
                p.name: p.calculate_victory_points() for p in self.active_players
            }
        }
    
    def export_state(self) -> Dict[str, Any]:
        """Export complete game state."""
        return {
            "game_id": self.game_id,
            "status": self.status.value,
            "settings": self.settings.__dict__,
            "current_turn": self.current_turn,
            "current_phase": self.current_phase.value,
            "current_player_index": self.current_player_index,
            "players": [p.to_dict() for p in self.players],
            "player_order": self.player_order,
            "eliminated_players": list(self.eliminated_players),
            "board": self.board.to_dict() if self.board else None,
            "turn_history": self.turn_history,
            "action_log": self.action_log[-100:],  # Last 100 actions
            "timestamps": {
                "created_at": self.created_at.isoformat(),
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "last_action_at": self.last_action_at.isoformat()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameState":
        """Create game state from exported data."""
        # This would implement full deserialization
        # For now, create basic game state
        game_state = cls(
            game_id=data["game_id"],
            status=GameStatus(data["status"]),
            current_turn=data["current_turn"],
            current_phase=GamePhase(data["current_phase"]),
            current_player_index=data["current_player_index"]
        )
        
        # Would restore players, board, etc.
        return game_state
    
    def __str__(self) -> str:
        """String representation of game state."""
        return (f"Game {self.game_id[:8]} - {self.status.value.title()} - "
                f"Turn {self.current_turn} - {len(self.active_players)} players")


# Utility functions for game state management
def create_game(settings: Optional[GameSettings] = None) -> GameState:
    """Create a new game with default or custom settings."""
    if settings is None:
        settings = GameSettings()
    
    return GameState(settings=settings)


def load_game(game_data: Dict[str, Any]) -> GameState:
    """Load game from saved data."""
    return GameState.from_dict(game_data)


def validate_game_configuration(players: List[Dict[str, Any]], 
                               settings: GameSettings) -> List[str]:
    """Validate game configuration and return any errors."""
    errors = []
    
    try:
        settings.validate()
    except ValidationError as e:
        errors.append(f"Settings validation: {str(e)}")
    
    if len(players) < MIN_PLAYERS:
        errors.append(f"Need at least {MIN_PLAYERS} players")
    
    if len(players) > MAX_PLAYERS:
        errors.append(f"Cannot have more than {MAX_PLAYERS} players")
    
    # Check for duplicate names and entry hexes
    names = [p.get("name", "") for p in players]
    entry_hexes = [p.get("entry_hex", "") for p in players]
    
    if len(set(names)) != len(names):
        errors.append("Duplicate player names")
    
    if len(set(entry_hexes)) != len(entry_hexes):
        errors.append("Duplicate entry hexes")
    
    return errors