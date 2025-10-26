"""Turn management and phase progression for Stellar Conquest."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import logging

from ..core.enums import GamePhase
from ..core.exceptions import GameStateError, InvalidActionError
from ..utils.validation import Validator
from .game_state import GameState


class PhaseResult(Enum):
    """Result of processing a game phase."""
    CONTINUE = "continue"
    ADVANCE_PHASE = "advance_phase"
    ADVANCE_TURN = "advance_turn"
    END_GAME = "end_game"


@dataclass
class PhaseProcessor:
    """Handles processing of a specific game phase."""
    
    phase: GamePhase
    name: str
    description: str
    process_func: Callable[[GameState], PhaseResult]
    auto_advance: bool = True
    requires_player_input: bool = False
    
    def process(self, game_state: GameState) -> PhaseResult:
        """Process this phase for the current game state."""
        try:
            return self.process_func(game_state)
        except Exception as e:
            logging.error(f"Error processing {self.phase.value}: {str(e)}")
            raise GameStateError(f"Failed to process {self.phase.value}: {str(e)}")


class TurnManager:
    """Manages turn progression and phase processing."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.phase_processors: Dict[GamePhase, PhaseProcessor] = {}
        self.phase_callbacks: Dict[GamePhase, List[Callable]] = {}
        self._setup_default_processors()
    
    def _setup_default_processors(self) -> None:
        """Setup default phase processors."""
        
        # Movement Phase
        self.register_phase_processor(PhaseProcessor(
            phase=GamePhase.MOVEMENT,
            name="Movement",
            description="Players move ships between star systems",
            process_func=self._process_movement_phase,
            requires_player_input=True,
            auto_advance=False
        ))
        
        # Exploration Phase
        self.register_phase_processor(PhaseProcessor(
            phase=GamePhase.EXPLORATION,
            name="Exploration", 
            description="Players explore new star systems",
            process_func=self._process_exploration_phase,
            requires_player_input=True,
            auto_advance=False
        ))
        
        # Colonization Phase
        self.register_phase_processor(PhaseProcessor(
            phase=GamePhase.COLONIZATION,
            name="Colonization",
            description="Players establish colonies on planets",
            process_func=self._process_colonization_phase,
            requires_player_input=True,
            auto_advance=False
        ))
        
        # Combat Phase
        self.register_phase_processor(PhaseProcessor(
            phase=GamePhase.COMBAT,
            name="Combat",
            description="Resolve combat between opposing forces",
            process_func=self._process_combat_phase,
            auto_advance=True
        ))
        
        # Production Phase
        self.register_phase_processor(PhaseProcessor(
            phase=GamePhase.PRODUCTION,
            name="Production", 
            description="Colonies produce ships and research technology",
            process_func=self._process_production_phase,
            requires_player_input=True,
            auto_advance=False
        ))
    
    def register_phase_processor(self, processor: PhaseProcessor) -> None:
        """Register a phase processor."""
        self.phase_processors[processor.phase] = processor
    
    def register_phase_callback(self, phase: GamePhase, callback: Callable) -> None:
        """Register a callback for a specific phase."""
        if phase not in self.phase_callbacks:
            self.phase_callbacks[phase] = []
        self.phase_callbacks[phase].append(callback)
    
    def get_current_phase_processor(self) -> Optional[PhaseProcessor]:
        """Get processor for current phase."""
        return self.phase_processors.get(self.game_state.current_phase)
    
    def process_current_phase(self) -> PhaseResult:
        """Process the current game phase."""
        if not self.game_state.is_active:
            raise GameStateError("Cannot process phase - game is not active")
        
        processor = self.get_current_phase_processor()
        if not processor:
            raise GameStateError(f"No processor registered for phase {self.game_state.current_phase}")
        
        # Run pre-phase callbacks
        self._run_phase_callbacks(self.game_state.current_phase, "pre")
        
        # Process the phase
        result = processor.process(self.game_state)
        
        # Run post-phase callbacks
        self._run_phase_callbacks(self.game_state.current_phase, "post")
        
        # Handle phase result
        return self._handle_phase_result(result)
    
    def _handle_phase_result(self, result: PhaseResult) -> PhaseResult:
        """Handle the result of phase processing."""
        if result == PhaseResult.ADVANCE_PHASE:
            self.advance_phase()
        elif result == PhaseResult.ADVANCE_TURN:
            self.advance_turn()
        elif result == PhaseResult.END_GAME:
            self.game_state.end_game("phase_result")
        
        return result
    
    def advance_phase(self) -> None:
        """Advance to the next phase."""
        self.game_state.advance_phase()
    
    def advance_turn(self) -> None:
        """Advance to the next turn."""
        self.game_state.advance_turn()
    
    def skip_to_phase(self, target_phase: GamePhase) -> None:
        """Skip to a specific phase."""
        if not self.game_state.is_active:
            raise GameStateError("Cannot skip phase - game is not active")
        
        self.game_state.current_phase = target_phase
        self.game_state._log_action("phase_skipped", {"target_phase": target_phase.value})
    
    def _run_phase_callbacks(self, phase: GamePhase, timing: str) -> None:
        """Run callbacks for a phase."""
        callbacks = self.phase_callbacks.get(phase, [])
        for callback in callbacks:
            try:
                callback(self.game_state, timing)
            except Exception as e:
                logging.warning(f"Phase callback error for {phase.value}: {str(e)}")
    
    # Default phase processors
    
    def _process_movement_phase(self, game_state: GameState) -> PhaseResult:
        """Process movement phase."""
        current_player = game_state.current_player
        if not current_player:
            return PhaseResult.ADVANCE_PHASE
        
        # In a real implementation, this would:
        # 1. Check for pending ship movements
        # 2. Execute movement orders
        # 3. Handle movement restrictions (command post range, etc.)
        # 4. Process ship arrivals at destinations
        
        # For now, auto-advance if no movements pending
        has_pending_movements = any(
            ship.destination for group in current_player.ship_groups 
            for ship in group.ships if ship.destination
        )
        
        if not has_pending_movements:
            return PhaseResult.ADVANCE_PHASE
        
        return PhaseResult.CONTINUE
    
    def _process_exploration_phase(self, game_state: GameState) -> PhaseResult:
        """Process exploration phase."""
        current_player = game_state.current_player
        if not current_player:
            return PhaseResult.ADVANCE_PHASE
        
        # In a real implementation, this would:
        # 1. Identify ships at unexplored star systems
        # 2. Draw star cards for exploration
        # 3. Handle exploration risks for unarmed ships
        # 4. Create new planets and update board state
        
        # For now, auto-advance
        return PhaseResult.ADVANCE_PHASE
    
    def _process_colonization_phase(self, game_state: GameState) -> PhaseResult:
        """Process colonization phase."""
        current_player = game_state.current_player
        if not current_player:
            return PhaseResult.ADVANCE_PHASE
        
        # In a real implementation, this would:
        # 1. Identify colony transports at uncolonized planets
        # 2. Check technology requirements (CET for barren planets)
        # 3. Create new colonies
        # 4. Handle population transfers
        
        # Check for colony transports with population
        has_colony_transports = any(
            ship.ship_type.value == "colony_transport" and ship.carried_population > 0
            for group in current_player.ship_groups
            for ship in group.ships
        )
        
        if not has_colony_transports:
            return PhaseResult.ADVANCE_PHASE
        
        return PhaseResult.CONTINUE
    
    def _process_combat_phase(self, game_state: GameState) -> PhaseResult:
        """Process combat phase."""
        # In a real implementation, this would:
        # 1. Identify locations with opposing forces
        # 2. Resolve combat using attack tables
        # 3. Handle ship destruction and colony conquest
        # 4. Apply combat results to game state
        
        # For now, check for potential combat situations
        combat_locations = self._find_combat_locations()
        
        if combat_locations:
            # Process combat at each location
            for location in combat_locations:
                self._resolve_combat_at_location(location)
        
        return PhaseResult.ADVANCE_PHASE
    
    def _process_production_phase(self, game_state: GameState) -> PhaseResult:
        """Process production phase."""
        # Production only happens every 4th turn
        if game_state.current_turn % 4 != 0:
            return PhaseResult.ADVANCE_TURN
        
        current_player = game_state.current_player
        if not current_player:
            return PhaseResult.ADVANCE_TURN
        
        # In a real implementation, this would:
        # 1. Calculate industrial points for each colony
        # 2. Handle factory construction
        # 3. Process ship construction orders
        # 4. Apply research investments
        # 5. Handle population growth
        
        # For now, just process basic production
        production_results = current_player.process_production_turn()
        
        game_state._log_action("production_completed", {
            "player_id": current_player.player_id,
            "results": production_results
        })
        
        return PhaseResult.CONTINUE
    
    def _find_combat_locations(self) -> List[str]:
        """Find locations where combat should occur."""
        combat_locations = []
        
        # Group all ship groups by location
        location_players: Dict[str, Set[int]] = {}
        
        for player in self.game_state.active_players:
            for ship_group in player.ship_groups:
                location = ship_group.location
                if location not in location_players:
                    location_players[location] = set()
                location_players[location].add(player.player_id)
        
        # Find locations with multiple players
        for location, players in location_players.items():
            if len(players) > 1:
                # Check if any player has warships
                has_warships = False
                for player in self.game_state.active_players:
                    if player.player_id in players:
                        ship_group = player.get_ship_group_at_location(location)
                        if ship_group and ship_group.has_warships():
                            has_warships = True
                            break
                
                if has_warships:
                    combat_locations.append(location)
        
        return combat_locations
    
    def _resolve_combat_at_location(self, location: str) -> Dict[str, Any]:
        """Resolve combat at a specific location."""
        # This would implement the full combat resolution system
        # For now, just log that combat would occur
        
        participants = []
        for player in self.game_state.active_players:
            ship_group = player.get_ship_group_at_location(location)
            if ship_group:
                participants.append({
                    "player_id": player.player_id,
                    "player_name": player.name,
                    "combat_strength": ship_group.get_total_combat_strength(),
                    "ship_counts": ship_group.get_ship_counts()
                })
        
        combat_result = {
            "location": location,
            "participants": participants,
            "resolution": "simulated"  # Would contain actual combat results
        }
        
        self.game_state._log_action("combat_resolved", combat_result)
        return combat_result
    
    def get_phase_status(self) -> Dict[str, Any]:
        """Get status of current phase."""
        processor = self.get_current_phase_processor()
        
        return {
            "current_phase": self.game_state.current_phase.value,
            "phase_name": processor.name if processor else "Unknown",
            "phase_description": processor.description if processor else "",
            "requires_input": processor.requires_player_input if processor else False,
            "auto_advance": processor.auto_advance if processor else False,
            "current_player": self.game_state.current_player.name if self.game_state.current_player else None,
            "turn": self.game_state.current_turn
        }
    
    def get_available_actions(self) -> List[Dict[str, Any]]:
        """Get list of actions available in current phase."""
        current_phase = self.game_state.current_phase
        current_player = self.game_state.current_player
        
        if not current_player:
            return []
        
        actions = []
        
        if current_phase == GamePhase.MOVEMENT:
            # Check for ships that can move
            for ship_group in current_player.ship_groups:
                if ship_group.get_total_ships() > 0:
                    actions.append({
                        "type": "move_ships",
                        "location": ship_group.location,
                        "ship_counts": ship_group.get_ship_counts()
                    })
        
        elif current_phase == GamePhase.EXPLORATION:
            # Check for ships at unexplored systems
            for ship_group in current_player.ship_groups:
                if not self.game_state.board.is_system_explored(ship_group.location, current_player.player_id):
                    actions.append({
                        "type": "explore_system", 
                        "location": ship_group.location
                    })
        
        elif current_phase == GamePhase.COLONIZATION:
            # Check for colony transport opportunities
            for ship_group in current_player.ship_groups:
                colony_transports = ship_group.get_ships_by_type("colony_transport")
                if colony_transports:
                    actions.append({
                        "type": "establish_colony",
                        "location": ship_group.location,
                        "transports": len(colony_transports)
                    })
        
        elif current_phase == GamePhase.PRODUCTION:
            # Production actions available at colonies
            for colony in current_player.colonies:
                if colony.can_produce:
                    actions.append({
                        "type": "allocate_production",
                        "colony_id": colony.id,
                        "location": colony.location,
                        "available_ip": colony.calculate_industrial_points()
                    })
        
        # Always available: end phase
        actions.append({
            "type": "end_phase",
            "description": f"End {current_phase.value} phase"
        })
        
        return actions
    
    def can_advance_phase(self) -> bool:
        """Check if current phase can be advanced."""
        processor = self.get_current_phase_processor()
        if not processor:
            return True
        
        # If phase doesn't require input, it can advance
        if not processor.requires_player_input:
            return True
        
        # Check if current player has completed required actions
        # This would be more sophisticated in a full implementation
        return True
    
    def force_advance_phase(self) -> None:
        """Force advance to next phase (admin/debug function)."""
        self.game_state._log_action("phase_force_advanced", {
            "from_phase": self.game_state.current_phase.value
        })
        self.advance_phase()
    
    def __str__(self) -> str:
        """String representation of turn manager."""
        return (f"TurnManager - Turn {self.game_state.current_turn} - "
                f"{self.game_state.current_phase.value} - "
                f"Player: {self.game_state.current_player.name if self.game_state.current_player else 'None'}")


# Utility functions for turn management
def create_turn_manager(game_state: GameState) -> TurnManager:
    """Create a turn manager for a game state."""
    return TurnManager(game_state)


def simulate_turn_progression(game_state: GameState, num_turns: int = 1) -> List[Dict[str, Any]]:
    """Simulate turn progression for testing."""
    turn_manager = TurnManager(game_state)
    results = []
    
    for _ in range(num_turns):
        if not game_state.is_active:
            break
        
        turn_start = {
            "turn": game_state.current_turn,
            "phase": game_state.current_phase.value,
            "player": game_state.current_player.name if game_state.current_player else None
        }
        
        # Process all phases in turn
        phases_processed = []
        while game_state.current_turn == turn_start["turn"]:
            phase_result = turn_manager.process_current_phase()
            phases_processed.append({
                "phase": game_state.current_phase.value,
                "result": phase_result.value
            })
            
            if phase_result == PhaseResult.END_GAME:
                break
            elif phase_result == PhaseResult.CONTINUE:
                # In simulation, auto-advance
                turn_manager.advance_phase()
        
        results.append({
            "turn_start": turn_start,
            "phases_processed": phases_processed,
            "turn_end": {
                "turn": game_state.current_turn,
                "phase": game_state.current_phase.value
            }
        })
    
    return results