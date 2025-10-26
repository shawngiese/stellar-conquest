"""Main game simulation orchestration."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from enum import Enum
import uuid
from datetime import datetime

from ..core.game_state import GameState
from ..entities.player import Player, PlayStyle
from ..ai.base_strategy import BaseStrategy
from ..ai.expansionist_strategy import ExpansionistStrategy
from ..ai.warlord_strategy import WarlordStrategy
from ..ai.technophile_strategy import TechnophileStrategy
from ..scenarios.scenario_runner import ScenarioRunner


class SimulationMode(Enum):
    """Different simulation execution modes."""
    STEP_BY_STEP = "step_by_step"      # Manual turn advancement
    AUTOMATED = "automated"            # Full auto-play
    DEBUG = "debug"                    # Detailed logging
    MONTE_CARLO = "monte_carlo"        # Multiple iterations for analysis


@dataclass
class SimulationConfig:
    """Configuration for game simulation."""
    mode: SimulationMode = SimulationMode.AUTOMATED
    debug_logging: bool = False
    save_snapshots: bool = True
    player_strategies: Dict[int, str] = None  # Player ID -> strategy name
    iterations: int = 1
    max_turns: int = 44
    random_seed: Optional[int] = None


@dataclass
class SimulationResult:
    """Result of a game simulation."""
    game_id: str
    config: SimulationConfig
    final_scores: Dict[int, int]
    winner_id: Optional[int]
    turns_completed: int
    execution_time: float
    action_log: List[Dict]
    player_statistics: Dict[int, Dict]
    

class GameSimulator:
    """Orchestrates complete game simulations."""
    
    def __init__(self):
        self.strategy_factories = {
            "expansionist": ExpansionistStrategy,
            "warlord": WarlordStrategy,
            "technophile": TechnophileStrategy,
            "balanced": ExpansionistStrategy  # Placeholder
        }
        self.scenario_runner = ScenarioRunner()
    
    def run_simulation(self, config: SimulationConfig) -> SimulationResult:
        """Run a complete game simulation."""
        if config.mode == SimulationMode.MONTE_CARLO:
            return self._run_monte_carlo_simulation(config)
        else:
            return self._run_single_simulation(config)
    
    def _run_single_simulation(self, config: SimulationConfig) -> SimulationResult:
        """Run a single game simulation."""
        import time
        start_time = time.time()
        
        # Set up game
        game_id = str(uuid.uuid4())
        game_state = GameState(game_id=game_id, max_turns=config.max_turns)
        
        # Configure player strategies
        player_strategies = self._setup_player_strategies(game_state, config)
        
        # Set random seed if specified
        if config.random_seed:
            import random
            random.seed(config.random_seed)
        
        # Run game loop
        turn_count = 0
        while not game_state.is_game_over and turn_count < config.max_turns:
            if config.mode == SimulationMode.DEBUG:
                print(f"Turn {game_state.current_turn}, Player {game_state.current_player_id}")
            
            # Execute player turn
            self._execute_player_turn(game_state, player_strategies, config)
            
            # Advance to next turn
            game_continues = game_state.advance_turn()
            if not game_continues:
                break
            
            turn_count += 1
        
        execution_time = time.time() - start_time
        
        # Collect results
        final_scores = {pid: p.calculate_victory_points() for pid, p in game_state.players.items()}
        player_stats = {pid: self._calculate_player_statistics(p, game_state) 
                       for pid, p in game_state.players.items()}
        
        return SimulationResult(
            game_id=game_id,
            config=config,
            final_scores=final_scores,
            winner_id=game_state.winner_id,
            turns_completed=game_state.current_turn,
            execution_time=execution_time,
            action_log=game_state.action_history,
            player_statistics=player_stats
        )
    
    def _run_monte_carlo_simulation(self, config: SimulationConfig) -> SimulationResult:
        """Run multiple simulations for statistical analysis."""
        results = []
        
        for iteration in range(config.iterations):
            # Create config for single run
            single_config = SimulationConfig(
                mode=SimulationMode.AUTOMATED,
                debug_logging=False,
                save_snapshots=False,
                player_strategies=config.player_strategies,
                random_seed=config.random_seed + iteration if config.random_seed else None
            )
            
            result = self._run_single_simulation(single_config)
            results.append(result)
        
        # Aggregate results
        return self._aggregate_monte_carlo_results(results, config)
    
    def _setup_player_strategies(self, game_state: GameState, config: SimulationConfig) -> Dict[int, BaseStrategy]:
        """Set up AI strategies for players."""
        strategies = {}
        
        # Use configured strategies or defaults
        strategy_assignments = config.player_strategies or {
            1: "expansionist",
            2: "warlord", 
            3: "technophile",
            4: "balanced"
        }
        
        for player_id, strategy_name in strategy_assignments.items():
            if player_id in game_state.players:
                strategy_class = self.strategy_factories.get(strategy_name, ExpansionistStrategy)
                strategies[player_id] = strategy_class()
        
        return strategies
    
    def _execute_player_turn(self, game_state: GameState, strategies: Dict[int, BaseStrategy], 
                           config: SimulationConfig):
        """Execute a complete player turn."""
        current_player = game_state.get_current_player()
        strategy = strategies.get(current_player.player_id)
        
        if not strategy:
            # Skip turn if no strategy assigned
            return
        
        # Get actions from AI strategy
        actions = strategy.decide_turn_actions(current_player, game_state)
        
        # Execute each action in sequence
        for action in actions:
            if config.debug_logging:
                print(f"  Executing {action.action_type}")
            
            try:
                outcome = action.execute(game_state)
                if config.debug_logging:
                    print(f"    Result: {outcome.result.value} - {outcome.message}")
            except Exception as e:
                if config.debug_logging:
                    print(f"    Error: {e}")
                # Log error but continue
                game_state.log_action("action_error", {
                    "action_type": action.action_type,
                    "error": str(e)
                })
        
        # Mark player turn complete
        current_player.turns_completed += 1
    
    def _calculate_player_statistics(self, player: Player, game_state: GameState) -> Dict:
        """Calculate comprehensive player statistics."""
        return {
            "final_population": sum(c.population for c in player.colonies),
            "total_colonies": len(player.colonies),
            "total_factories": sum(c.factories for c in player.colonies),
            "technologies_researched": len(player.completed_technologies),
            "victory_points": player.calculate_victory_points(),
            "play_style": player.play_style.value,
            "ships_remaining": sum(f.total_ships for f in player.fleets)
        }
    
    def _aggregate_monte_carlo_results(self, results: List[SimulationResult], 
                                     config: SimulationConfig) -> SimulationResult:
        """Aggregate multiple simulation results for Monte Carlo analysis."""
        # Calculate win rates
        win_counts = {}
        total_games = len(results)
        
        for result in results:
            winner = result.winner_id
            if winner:
                win_counts[winner] = win_counts.get(winner, 0) + 1
        
        win_rates = {pid: count/total_games for pid, count in win_counts.items()}
        
        # Average statistics
        avg_scores = {}
        avg_stats = {}
        
        if results:
            # Get all player IDs
            all_player_ids = set()
            for result in results:
                all_player_ids.update(result.final_scores.keys())
            
            # Calculate averages
            for pid in all_player_ids:
                scores = [r.final_scores.get(pid, 0) for r in results]
                avg_scores[pid] = sum(scores) / len(scores)
                
                stats_list = [r.player_statistics.get(pid, {}) for r in results]
                avg_stats[pid] = {}
                
                if stats_list and stats_list[0]:
                    for stat_name in stats_list[0].keys():
                        values = [s.get(stat_name, 0) for s in stats_list if isinstance(s.get(stat_name, 0), (int, float))]
                        if values:
                            avg_stats[pid][stat_name] = sum(values) / len(values)
        
        # Create aggregate result
        total_time = sum(r.execution_time for r in results)
        
        return SimulationResult(
            game_id=f"monte_carlo_{total_games}_games",
            config=config,
            final_scores=avg_scores,
            winner_id=max(win_rates.items(), key=lambda x: x[1])[0] if win_rates else None,
            turns_completed=int(sum(r.turns_completed for r in results) / total_games) if results else 0,
            execution_time=total_time,
            action_log=[],  # Don't aggregate action logs
            player_statistics={
                **avg_stats,
                "win_rates": win_rates,
                "total_iterations": total_games
            }
        )
    
    def run_what_if_scenario(self, base_game_state: GameState, scenario_description: str) -> Dict:
        """Run a what-if scenario based on natural language description."""
        # Parse scenario description and create appropriate scenario
        scenario_config = self._parse_scenario_description(scenario_description)
        
        if scenario_config:
            return self.scenario_runner.run_scenario(base_game_state, scenario_config)
        else:
            return {"error": "Could not parse scenario description"}
    
    def _parse_scenario_description(self, description: str):
        """Parse natural language scenario description (simplified)."""
        # This would implement natural language parsing
        # For now, return None as placeholder
        return None
    
    def create_game_snapshot(self, game_state: GameState) -> Dict:
        """Create a saveable snapshot of game state."""
        return {
            "timestamp": datetime.now().isoformat(),
            "turn": game_state.current_turn,
            "phase": game_state.turn_phase,
            "players": {
                pid: {
                    "name": p.name,
                    "play_style": p.play_style.value,
                    "colonies": len(p.colonies),
                    "victory_points": p.calculate_victory_points()
                }
                for pid, p in game_state.players.items()
            },
            "game_status": {
                "is_over": game_state.is_game_over,
                "winner": game_state.winner_id
            }
        }
    
    def get_debug_summary(self, game_state: GameState) -> str:
        """Get a human-readable summary of current game state."""
        summary = f"Turn {game_state.current_turn} - Player {game_state.current_player_id}'s turn ({game_state.turn_phase})\n"
        summary += "=" * 50 + "\n"
        
        for pid, player in game_state.players.items():
            summary += f"Player {pid} ({player.play_style.value}):\n"
            summary += f"  Colonies: {len(player.colonies)}\n"
            summary += f"  Population: {sum(c.population for c in player.colonies)}\n"
            summary += f"  Victory Points: {player.calculate_victory_points()}\n"
            summary += f"  Technologies: {len(player.completed_technologies)}\n"
            summary += "\n"
        
        return summary