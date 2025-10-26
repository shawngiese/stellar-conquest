"""Basic simulator for Stellar Conquest games."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import random
import logging
from datetime import datetime

from ..game.game_state import GameState, GameSettings, create_game
from ..game.turn_manager import TurnManager
from ..core.enums import PlayStyle, GamePhase
from ..core.exceptions import SimulationError, GameStateError
from ..actions.base_action import BaseAction, ActionResult
from ..actions.movement import MovementAction, create_movement_action
from ..actions.exploration import ExplorationAction, find_exploration_targets


class SimulationMode(Enum):
    """Simulation execution modes."""
    MANUAL = "manual"  # User controls all actions
    AUTOMATED = "automated"  # AI controls all actions
    MIXED = "mixed"  # Mix of user and AI control
    SCENARIO = "scenario"  # Specific scenario testing


@dataclass
class SimulationConfig:
    """Configuration for simulation runs."""
    
    mode: SimulationMode = SimulationMode.AUTOMATED
    max_turns: int = 50
    auto_save: bool = True
    detailed_logging: bool = True
    random_seed: Optional[int] = None
    ai_decision_delay: float = 0.0  # Seconds between AI decisions
    
    # AI behavior settings
    ai_exploration_chance: float = 0.8
    ai_movement_chance: float = 0.6
    ai_aggressive_expansion: bool = True
    
    def validate(self) -> None:
        """Validate simulation configuration."""
        if self.max_turns <= 0:
            raise SimulationError("max_turns must be positive")
        if not 0.0 <= self.ai_exploration_chance <= 1.0:
            raise SimulationError("ai_exploration_chance must be between 0.0 and 1.0")


@dataclass
class SimulationResult:
    """Results of a simulation run."""
    
    game_id: str
    config: SimulationConfig
    final_state: GameState
    winner: Optional[str] = None
    total_turns: int = 0
    total_actions: int = 0
    execution_time_seconds: float = 0.0
    
    # Detailed statistics
    player_statistics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    turn_summaries: List[Dict[str, Any]] = field(default_factory=list)
    action_statistics: Dict[str, int] = field(default_factory=dict)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get concise simulation summary."""
        return {
            "game_id": self.game_id,
            "winner": self.winner,
            "total_turns": self.total_turns,
            "total_actions": self.total_actions,
            "execution_time": f"{self.execution_time_seconds:.2f}s",
            "final_scores": {
                name: stats.get("final_victory_points", 0)
                for name, stats in self.player_statistics.items()
            }
        }


class StellarConquestSimulator:
    """Main simulator for Stellar Conquest games."""
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        self.config.validate()
        
        # Simulation state
        self.game_state: Optional[GameState] = None
        self.turn_manager: Optional[TurnManager] = None
        self.action_queue: List[BaseAction] = []
        self.simulation_callbacks: Dict[str, List[Callable]] = {}
        
        # Statistics tracking
        self.action_count = 0
        self.turn_summaries = []
        self.start_time: Optional[datetime] = None
        
        # Setup logging
        if self.config.detailed_logging:
            logging.basicConfig(level=logging.INFO)
        
        # Set random seed for reproducibility
        if self.config.random_seed is not None:
            random.seed(self.config.random_seed)
    
    def create_game(self, players: List[Dict[str, Any]], 
                   settings: Optional[GameSettings] = None) -> GameState:
        """Create a new game with specified players."""
        if settings is None:
            settings = GameSettings(max_turns=self.config.max_turns)
        
        self.game_state = create_game(settings)
        
        # Add players
        entry_hexes = ["A1", "A14", "N1", "N14", "G1", "H14"]  # Available entry points
        
        for i, player_data in enumerate(players):
            if i >= len(entry_hexes):
                raise SimulationError(f"Too many players: max {len(entry_hexes)}")
            
            play_style = PlayStyle(player_data.get("play_style", "balanced"))
            self.game_state.add_player(
                name=player_data["name"],
                play_style=play_style,
                entry_hex=entry_hexes[i],
                is_ai=player_data.get("is_ai", True)
            )
        
        # Initialize turn manager
        self.turn_manager = TurnManager(self.game_state)
        
        return self.game_state
    
    def run_simulation(self, players: List[Dict[str, Any]], 
                      settings: Optional[GameSettings] = None) -> SimulationResult:
        """Run a complete simulation."""
        self.start_time = datetime.now()
        
        try:
            # Create and start game
            self.create_game(players, settings)
            self.game_state.start_game()
            
            logging.info(f"Starting simulation with {len(players)} players")
            
            # Run simulation loop
            while self.game_state.is_active and self.game_state.current_turn <= self.config.max_turns:
                self._execute_simulation_turn()
                
                # Check for victory conditions
                winner = self.game_state.check_victory_conditions()
                if winner:
                    break
            
            # Generate results
            result = self._generate_simulation_result()
            
            end_time = datetime.now()
            result.execution_time_seconds = (end_time - self.start_time).total_seconds()
            
            logging.info(f"Simulation completed: {result.get_summary()}")
            return result
            
        except Exception as e:
            logging.error(f"Simulation failed: {str(e)}")
            raise SimulationError(f"Simulation execution failed: {str(e)}")
    
    def _execute_simulation_turn(self) -> None:
        """Execute one complete turn of the simulation."""
        turn_start_summary = {
            "turn": self.game_state.current_turn,
            "phase": self.game_state.current_phase.value,
            "active_players": len(self.game_state.active_players)
        }
        
        # Process all phases in the turn
        phase_results = []
        
        while True:
            phase_result = self._execute_simulation_phase()
            phase_results.append(phase_result)
            
            # Check if turn or game ended
            if (phase_result.get("turn_advanced", False) or 
                not self.game_state.is_active):
                break
        
        # Record turn summary
        turn_summary = {
            **turn_start_summary,
            "phase_results": phase_results,
            "actions_executed": self.action_count,
            "turn_end": {
                "turn": self.game_state.current_turn,
                "phase": self.game_state.current_phase.value
            }
        }
        
        self.turn_summaries.append(turn_summary)
    
    def _execute_simulation_phase(self) -> Dict[str, Any]:
        """Execute current phase of the simulation."""
        current_phase = self.game_state.current_phase
        current_player = self.game_state.current_player
        
        phase_summary = {
            "phase": current_phase.value,
            "player": current_player.name if current_player else None,
            "actions_generated": 0,
            "actions_executed": 0
        }
        
        # Generate and execute actions based on phase
        if current_player and self.config.mode == SimulationMode.AUTOMATED:
            actions = self._generate_ai_actions(current_player, current_phase)
            phase_summary["actions_generated"] = len(actions)
            
            for action in actions:
                result = action.execute(self.game_state)
                self.action_count += 1
                
                if result.result == ActionResult.SUCCESS:
                    phase_summary["actions_executed"] += 1
        
        # Process phase through turn manager
        turn_result = self.turn_manager.process_current_phase()
        phase_summary["turn_result"] = turn_result.value
        phase_summary["turn_advanced"] = turn_result.value == "advance_turn"
        
        return phase_summary
    
    def _generate_ai_actions(self, player, phase: GamePhase) -> List[BaseAction]:
        """Generate AI actions for the current phase."""
        actions = []
        
        if phase == GamePhase.MOVEMENT:
            # Generate movement actions
            if random.random() < self.config.ai_movement_chance:
                movement_actions = self._generate_movement_actions(player)
                actions.extend(movement_actions)
        
        elif phase == GamePhase.EXPLORATION:
            # Generate exploration actions
            if random.random() < self.config.ai_exploration_chance:
                exploration_actions = self._generate_exploration_actions(player)
                actions.extend(exploration_actions)
        
        elif phase == GamePhase.COLONIZATION:
            # Generate colonization actions (simplified)
            # Would implement colony transport and planet colonization
            pass
        
        elif phase == GamePhase.PRODUCTION:
            # Generate production actions (simplified)
            # Would implement industrial spending and ship construction
            pass
        
        return actions
    
    def _generate_movement_actions(self, player) -> List[MovementAction]:
        """Generate AI movement actions."""
        actions = []
        
        # Simple AI: move scouts to explore new systems
        for ship_group in player.ship_groups:
            scout_count = ship_group.get_ship_counts().get("scout", 0)
            
            if scout_count > 0:
                # Find nearby unexplored systems
                max_range = player.current_ship_speed
                nearby_systems = self.game_state.board.get_systems_within_range(
                    ship_group.location, max_range
                )
                
                unexplored = [
                    sys for sys in nearby_systems 
                    if not self.game_state.board.is_system_explored(sys, player.player_id)
                ]
                
                if unexplored:
                    target = random.choice(unexplored)
                    movement_data = [{
                        "from": ship_group.location,
                        "to": target,
                        "ship_type": "scout",
                        "count": min(1, scout_count)
                    }]
                    
                    action = create_movement_action(player.player_id, movement_data)
                    actions.append(action)
        
        return actions
    
    def _generate_exploration_actions(self, player) -> List[ExplorationAction]:
        """Generate AI exploration actions."""
        actions = []
        
        # Find exploration targets
        targets = find_exploration_targets(self.game_state, player.player_id)
        
        if targets:
            # Create exploration action for accessible targets
            exploration_data = []
            
            for target in targets[:3]:  # Limit to 3 explorations per turn
                # Check if player has ships at the location
                ship_group = player.get_ship_group_at_location(target["hex"])
                if ship_group:
                    ship_counts = ship_group.get_ship_counts()
                    
                    # Prefer scouts for exploration
                    if "scout" in ship_counts and ship_counts["scout"] > 0:
                        exploration_data.append({
                            "location": target["hex"],
                            "ship_type": "scout",
                            "count": 1,
                            "has_escort": ship_group.has_warships()
                        })
            
            if exploration_data:
                from ..actions.exploration import create_exploration_action
                action = create_exploration_action(player.player_id, exploration_data)
                actions.append(action)
        
        return actions
    
    def _generate_simulation_result(self) -> SimulationResult:
        """Generate final simulation results."""
        result = SimulationResult(
            game_id=self.game_state.game_id,
            config=self.config,
            final_state=self.game_state,
            total_turns=self.game_state.current_turn,
            total_actions=self.action_count,
            turn_summaries=self.turn_summaries
        )
        
        # Determine winner
        winner = self.game_state.game_winner
        if winner:
            result.winner = winner.name
        
        # Generate player statistics
        for player in self.game_state.players:
            stats = player.get_strategic_summary()
            stats["final_victory_points"] = player.calculate_victory_points()
            result.player_statistics[player.name] = stats
        
        # Count action types
        for action_entry in self.game_state.action_log:
            action_type = action_entry.get("action_type", "unknown")
            result.action_statistics[action_type] = result.action_statistics.get(action_type, 0) + 1
        
        return result
    
    def run_scenario(self, scenario_config: Dict[str, Any]) -> SimulationResult:
        """Run a specific scenario for testing."""
        # This would implement scenario-specific setup and execution
        # For now, run a basic automated simulation
        
        players = scenario_config.get("players", [
            {"name": "Player1", "play_style": "expansionist", "is_ai": True},
            {"name": "Player2", "play_style": "balanced", "is_ai": True}
        ])
        
        settings = GameSettings(
            max_turns=scenario_config.get("max_turns", 20),
            victory_points_target=scenario_config.get("victory_target", 100)
        )
        
        return self.run_simulation(players, settings)
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register callback for simulation events."""
        if event_type not in self.simulation_callbacks:
            self.simulation_callbacks[event_type] = []
        self.simulation_callbacks[event_type].append(callback)
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get current simulation status."""
        if not self.game_state:
            return {"status": "not_started"}
        
        return {
            "status": self.game_state.status.value,
            "current_turn": self.game_state.current_turn,
            "current_phase": self.game_state.current_phase.value,
            "active_players": len(self.game_state.active_players),
            "actions_executed": self.action_count,
            "execution_time": (
                (datetime.now() - self.start_time).total_seconds() 
                if self.start_time else 0
            )
        }


# Utility functions for simulation
def create_quick_simulation(player_count: int = 2, max_turns: int = 20) -> SimulationResult:
    """Create and run a quick simulation for testing."""
    config = SimulationConfig(
        mode=SimulationMode.AUTOMATED,
        max_turns=max_turns,
        detailed_logging=False
    )
    
    simulator = StellarConquestSimulator(config)
    
    players = []
    play_styles = ["expansionist", "balanced", "warlord", "technophile"]
    
    for i in range(player_count):
        players.append({
            "name": f"AI_Player_{i+1}",
            "play_style": play_styles[i % len(play_styles)],
            "is_ai": True
        })
    
    return simulator.run_simulation(players)


def run_simulation_batch(batch_size: int = 10, player_count: int = 2) -> List[SimulationResult]:
    """Run multiple simulations for statistical analysis."""
    results = []
    
    for i in range(batch_size):
        logging.info(f"Running simulation {i+1}/{batch_size}")
        
        config = SimulationConfig(
            random_seed=i,  # Different seed for each simulation
            detailed_logging=False
        )
        
        result = create_quick_simulation(player_count)
        results.append(result)
    
    return results


def analyze_simulation_results(results: List[SimulationResult]) -> Dict[str, Any]:
    """Analyze multiple simulation results."""
    if not results:
        return {}
    
    # Basic statistics
    total_games = len(results)
    completed_games = len([r for r in results if r.winner])
    
    # Winner distribution
    winner_counts = {}
    for result in results:
        if result.winner:
            winner_counts[result.winner] = winner_counts.get(result.winner, 0) + 1
    
    # Average game length
    avg_turns = sum(r.total_turns for r in results) / total_games
    avg_actions = sum(r.total_actions for r in results) / total_games
    
    return {
        "total_games": total_games,
        "completed_games": completed_games,
        "completion_rate": completed_games / total_games,
        "winner_distribution": winner_counts,
        "average_turns": avg_turns,
        "average_actions": avg_actions,
        "average_execution_time": sum(r.execution_time_seconds for r in results) / total_games
    }