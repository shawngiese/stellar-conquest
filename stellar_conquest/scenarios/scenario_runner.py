"""Scenario runner for what-if analysis."""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import copy
import json

from ..core.game_state import GameState
from ..actions.base_action import BaseAction
from ..combat.combat_resolver import CombatResolver


class ScenarioType(Enum):
    """Types of scenarios that can be run."""
    COMBAT_SIMULATION = "combat_simulation"
    PRODUCTION_ANALYSIS = "production_analysis"
    EXPANSION_RACE = "expansion_race"
    STRATEGIC_DECISION = "strategic_decision"
    FULL_GAME_FORK = "full_game_fork"


@dataclass
class ScenarioConfig:
    """Configuration for a scenario run."""
    scenario_type: ScenarioType
    name: str
    description: str
    parameters: Dict[str, Any]
    iterations: int = 1
    save_snapshots: bool = True


@dataclass
class ScenarioResult:
    """Result of running a scenario."""
    config: ScenarioConfig
    outcomes: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    execution_time: float
    snapshots: Optional[List[GameState]] = None


class ScenarioRunner:
    """Runs what-if scenarios on game states."""
    
    def __init__(self):
        self.scenario_handlers = {
            ScenarioType.COMBAT_SIMULATION: self._run_combat_scenario,
            ScenarioType.PRODUCTION_ANALYSIS: self._run_production_scenario,
            ScenarioType.EXPANSION_RACE: self._run_expansion_scenario,
            ScenarioType.STRATEGIC_DECISION: self._run_decision_scenario,
            ScenarioType.FULL_GAME_FORK: self._run_game_fork_scenario
        }
    
    def run_scenario(self, base_game_state: GameState, config: ScenarioConfig) -> ScenarioResult:
        """Run a scenario and return results."""
        import time
        start_time = time.time()
        
        # Get appropriate handler
        handler = self.scenario_handlers.get(config.scenario_type)
        if not handler:
            raise ValueError(f"Unknown scenario type: {config.scenario_type}")
        
        # Run scenario iterations
        outcomes = []
        snapshots = [] if config.save_snapshots else None
        
        for iteration in range(config.iterations):
            # Create isolated copy of game state
            scenario_state = self._create_scenario_copy(base_game_state)
            
            # Run scenario
            outcome = handler(scenario_state, config.parameters)
            outcomes.append(outcome)
            
            if config.save_snapshots:
                snapshots.append(copy.deepcopy(scenario_state))
        
        # Calculate statistics
        statistics = self._calculate_scenario_statistics(outcomes, config)
        
        execution_time = time.time() - start_time
        
        return ScenarioResult(
            config=config,
            outcomes=outcomes,
            statistics=statistics,
            execution_time=execution_time,
            snapshots=snapshots
        )
    
    def _create_scenario_copy(self, game_state: GameState) -> GameState:
        """Create an isolated copy for scenario testing."""
        return game_state.create_scenario_copy()
    
    def _run_combat_scenario(self, game_state: GameState, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run a combat simulation scenario."""
        location = parameters.get("location")
        attacker_id = parameters.get("attacker_id")
        defender_id = parameters.get("defender_id")
        
        if not all([location, attacker_id, defender_id]):
            raise ValueError("Combat scenario requires location, attacker_id, and defender_id")
        
        # Set up combat
        attacker = game_state.players[attacker_id]
        defender = game_state.players[defender_id]
        
        attacker_fleet = attacker.get_fleet_at_location(location)
        defender_fleet = defender.get_fleet_at_location(location)
        
        if not attacker_fleet or not defender_fleet:
            return {"result": "no_combat", "reason": "missing_fleets"}
        
        # Run combat simulation
        combat_resolver = CombatResolver()
        combat_result = combat_resolver.resolve_space_combat(
            attacker_fleet, defender_fleet, game_state
        )
        
        return {
            "result": "combat_completed",
            "winner": combat_result.winner_id,
            "attacker_losses": combat_result.attacker_losses,
            "defender_losses": combat_result.defender_losses,
            "rounds": combat_result.rounds_fought
        }
    
    def _run_production_scenario(self, game_state: GameState, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run a production turn analysis scenario."""
        player_id = parameters.get("player_id")
        spending_strategy = parameters.get("spending_strategy", {})
        turns_to_simulate = parameters.get("turns", 1)
        
        player = game_state.players[player_id]
        initial_state = self._capture_player_state(player)
        
        # Simulate production turns with different spending strategies
        for turn in range(turns_to_simulate):
            if turn % 4 == 0:  # Production turn
                self._simulate_production_turn(player, spending_strategy, game_state)
        
        final_state = self._capture_player_state(player)
        
        return {
            "result": "production_completed",
            "initial_state": initial_state,
            "final_state": final_state,
            "growth": {
                "population": final_state["population"] - initial_state["population"],
                "factories": final_state["factories"] - initial_state["factories"],
                "colonies": final_state["colonies"] - initial_state["colonies"]
            }
        }
    
    def _run_expansion_scenario(self, game_state: GameState, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run an expansion race scenario."""
        target_location = parameters.get("target_location")
        competing_players = parameters.get("players", [])
        turns_limit = parameters.get("turns_limit", 10)
        
        # Simulate race to colonize target location
        winner = None
        turn_count = 0
        
        for turn in range(turns_limit):
            turn_count += 1
            
            # Check if any player has colonized the target
            for player_id in competing_players:
                player = game_state.players[player_id]
                if self._has_colony_at_location(player, target_location):
                    winner = player_id
                    break
            
            if winner:
                break
            
            # Advance game state
            game_state.advance_turn()
        
        return {
            "result": "expansion_race_completed",
            "winner": winner,
            "turns_taken": turn_count,
            "target_location": target_location
        }
    
    def _run_decision_scenario(self, game_state: GameState, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run a strategic decision analysis scenario."""
        player_id = parameters.get("player_id")
        decision_options = parameters.get("options", [])
        evaluation_metric = parameters.get("metric", "victory_points")
        
        results = {}
        
        for option_name, actions in decision_options.items():
            # Create copy for this option
            option_state = copy.deepcopy(game_state)
            
            # Execute actions for this option
            for action_data in actions:
                action = self._create_action_from_data(action_data, player_id)
                if action:
                    action.execute(option_state)
            
            # Evaluate outcome
            outcome_value = self._evaluate_game_state(option_state, player_id, evaluation_metric)
            results[option_name] = outcome_value
        
        # Find best option
        best_option = max(results.items(), key=lambda x: x[1])
        
        return {
            "result": "decision_analysis_completed",
            "options_evaluated": results,
            "best_option": best_option[0],
            "best_value": best_option[1]
        }
    
    def _run_game_fork_scenario(self, game_state: GameState, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run a full game continuation scenario."""
        turns_to_simulate = parameters.get("turns", 10)
        ai_override = parameters.get("ai_strategies", {})
        
        initial_scores = {
            pid: player.calculate_victory_points() 
            for pid, player in game_state.players.items()
        }
        
        # Simulate game continuation
        for _ in range(turns_to_simulate):
            if game_state.is_game_over:
                break
            game_state.advance_turn()
        
        final_scores = {
            pid: player.calculate_victory_points() 
            for pid, player in game_state.players.items()
        }
        
        return {
            "result": "game_fork_completed",
            "initial_scores": initial_scores,
            "final_scores": final_scores,
            "winner": game_state.winner_id,
            "turns_simulated": min(turns_to_simulate, game_state.current_turn - game_state.current_turn + turns_to_simulate)
        }
    
    def _capture_player_state(self, player) -> Dict[str, Any]:
        """Capture current player state for comparison."""
        return {
            "population": sum(c.population for c in player.colonies),
            "factories": sum(c.factories for c in player.colonies),
            "colonies": len(player.colonies),
            "technologies": len(player.completed_technologies),
            "victory_points": player.calculate_victory_points()
        }
    
    def _simulate_production_turn(self, player, spending_strategy: Dict, game_state: GameState):
        """Simulate a production turn with specific spending."""
        total_ip = 0
        
        # Calculate production for each colony
        for colony in player.colonies:
            # Population growth
            growth = colony.calculate_growth()
            colony.population += growth
            
            # Industrial production
            colony_ip = colony.calculate_industrial_points()
            total_ip += colony_ip
        
        # Apply spending strategy
        for item, amount in spending_strategy.items():
            if amount <= total_ip:
                self._apply_production_spending(player, item, amount)
                total_ip -= amount
    
    def _apply_production_spending(self, player, item: str, amount: int):
        """Apply production spending to player state."""
        if item == "colony_transports":
            # Add colony transports to player's fleets
            pass  # Would implement actual ship creation
        elif item == "factories":
            # Add factories to colonies
            if player.colonies:
                player.colonies[0].factories += amount // 4  # 4 IP per factory
        # ... other spending types
    
    def _has_colony_at_location(self, player, location: str) -> bool:
        """Check if player has a colony at the specified location."""
        return len(player.get_colony_at_location(location)) > 0
    
    def _create_action_from_data(self, action_data: Dict, player_id: int) -> Optional[BaseAction]:
        """Create action object from serialized data."""
        # Would implement action deserialization
        return None
    
    def _evaluate_game_state(self, game_state: GameState, player_id: int, metric: str) -> float:
        """Evaluate game state using specified metric."""
        player = game_state.players[player_id]
        
        if metric == "victory_points":
            return player.calculate_victory_points()
        elif metric == "population":
            return sum(c.population for c in player.colonies)
        elif metric == "colonies":
            return len(player.colonies)
        # ... other metrics
        
        return 0.0
    
    def _calculate_scenario_statistics(self, outcomes: List[Dict], config: ScenarioConfig) -> Dict[str, Any]:
        """Calculate statistics across scenario iterations."""
        if not outcomes:
            return {}
        
        stats = {"iterations": len(outcomes)}
        
        if config.scenario_type == ScenarioType.COMBAT_SIMULATION:
            winners = [o.get("winner") for o in outcomes if o.get("winner")]
            stats["win_rates"] = {
                player: winners.count(player) / len(outcomes)
                for player in set(winners)
            }
        
        elif config.scenario_type == ScenarioType.PRODUCTION_ANALYSIS:
            growths = [o.get("growth", {}) for o in outcomes]
            if growths:
                stats["average_growth"] = {
                    key: sum(g.get(key, 0) for g in growths) / len(growths)
                    for key in growths[0].keys()
                }
        
        return stats


# Convenience functions for common scenarios
def create_combat_scenario(location: str, attacker_id: int, defender_id: int, 
                          iterations: int = 100) -> ScenarioConfig:
    """Create a combat simulation scenario."""
    return ScenarioConfig(
        scenario_type=ScenarioType.COMBAT_SIMULATION,
        name=f"Combat at {location}",
        description=f"Simulate combat between player {attacker_id} and {defender_id}",
        parameters={
            "location": location,
            "attacker_id": attacker_id,
            "defender_id": defender_id
        },
        iterations=iterations
    )


def create_production_scenario(player_id: int, spending_strategy: Dict[str, int], 
                             turns: int = 4) -> ScenarioConfig:
    """Create a production analysis scenario."""
    return ScenarioConfig(
        scenario_type=ScenarioType.PRODUCTION_ANALYSIS,
        name=f"Production Analysis Player {player_id}",
        description="Analyze production outcomes with different spending",
        parameters={
            "player_id": player_id,
            "spending_strategy": spending_strategy,
            "turns": turns
        },
        iterations=1
    )