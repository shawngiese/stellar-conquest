"""Exploration actions for discovering new star systems."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .base_action import BaseAction, ActionResult, ActionOutcome
from ..game.game_state import GameState
from ..core.enums import ShipType
from ..core.exceptions import InvalidActionError, GameStateError
from ..utils.validation import GameValidator


@dataclass
class ExplorationOrder:
    """Individual exploration order."""
    location: str
    explorer_ship_type: ShipType
    explorer_count: int
    has_warship_escort: bool = False


class ExplorationAction(BaseAction):
    """Handle star system exploration and discovery."""
    
    def __init__(self, player_id: int, exploration_orders: List[ExplorationOrder]):
        super().__init__(player_id, "exploration")
        self.exploration_orders = exploration_orders
    
    def validate(self, game_state: GameState) -> bool:
        """Validate all exploration orders."""
        player = game_state.get_player_by_id(self.player_id)
        if not player:
            return False
        
        for order in self.exploration_orders:
            if not self._validate_single_exploration(order, player, game_state):
                return False
        
        return True
    
    def _validate_single_exploration(self, order: ExplorationOrder, player, game_state: GameState) -> bool:
        """Validate a single exploration order."""
        try:
            # Validate hex coordinate
            GameValidator.validate_hex_coordinate(order.location)
            
            # Check if system is already explored by this player
            if game_state.board.is_system_explored(order.location, self.player_id):
                return False
            
            # Check if player has ships at location
            ship_group = player.get_ship_group_at_location(order.location)
            if not ship_group:
                return False
            
            # Check if has required explorer ships
            ship_counts = ship_group.get_ship_counts()
            if ship_counts.get(order.explorer_ship_type, 0) < order.explorer_count:
                return False
            
            # Check for warship escort if needed
            if order.has_warship_escort:
                if not ship_group.has_warships():
                    return False
            
            # Check if location is valid for exploration
            if not game_state.board.is_valid_location(order.location):
                return False
            
            return True
            
        except Exception:
            return False
    
    def execute(self, game_state: GameState) -> ActionOutcome:
        """Execute all exploration orders."""
        if not self.validate(game_state):
            return ActionOutcome(ActionResult.INVALID, "Exploration validation failed")
        
        player = game_state.get_player_by_id(self.player_id)
        if not player:
            return ActionOutcome(ActionResult.FAILURE, "Player not found")
        
        successful_explorations = []
        failed_explorations = []
        
        for order in self.exploration_orders:
            try:
                result = self._execute_single_exploration(order, player, game_state)
                successful_explorations.append(result)
            except Exception as e:
                failed_explorations.append((order, str(e)))
        
        # Determine result
        if failed_explorations:
            result = ActionResult.PARTIAL if successful_explorations else ActionResult.FAILURE
            message = f"Completed {len(successful_explorations)}/{len(self.exploration_orders)} explorations"
        else:
            result = ActionResult.SUCCESS
            message = f"All {len(self.exploration_orders)} systems explored successfully"
        
        self.executed = True
        self.outcome = ActionOutcome(
            result, message,
            {
                "successful_explorations": len(successful_explorations),
                "failed_explorations": len(failed_explorations),
                "exploration_results": successful_explorations
            }
        )
        
        self.log_execution(game_state, self.outcome)
        return self.outcome
    
    def _execute_single_exploration(self, order: ExplorationOrder, player, game_state: GameState) -> Dict[str, Any]:
        """Execute a single exploration order."""
        # Perform exploration through board
        exploration_result = game_state.board.explore_system(
            order.location, 
            self.player_id,
            order.has_warship_escort
        )
        
        # Handle exploration risks
        ships_lost = 0
        if exploration_result.ships_lost > 0:
            # Remove lost ships
            ships_lost = player.remove_ships_from_location(
                order.location, 
                order.explorer_ship_type, 
                exploration_result.ships_lost
            )
        
        # Create exploration result summary
        result = {
            "location": order.location,
            "star_card_number": exploration_result.star_card_number,
            "star_color": exploration_result.star_system.star_color.value,
            "planets_discovered": len(exploration_result.planets_discovered),
            "planet_details": [
                {
                    "orbit": p.orbit,
                    "type": p.planet_type.value,
                    "max_population": p.max_population,
                    "is_mineral_rich": p.is_mineral_rich,
                    "victory_points": p.victory_points
                }
                for p in exploration_result.planets_discovered
            ],
            "ships_lost": ships_lost,
            "exploration_risk": exploration_result.exploration_risk_result,
            "strategic_value": exploration_result.star_system.get_strategic_value()
        }
        
        return result


class AutoExplorationAction(BaseAction):
    """Automatically explore all reachable unexplored systems."""
    
    def __init__(self, player_id: int, max_systems: int = 5, prefer_scouts: bool = True):
        super().__init__(player_id, "auto_exploration")
        self.max_systems = max_systems
        self.prefer_scouts = prefer_scouts
    
    def validate(self, game_state: GameState) -> bool:
        """Validate auto-exploration parameters."""
        player = game_state.get_player_by_id(self.player_id)
        if not player:
            return False
        
        # Check if player has any ships that can explore
        for ship_group in player.ship_groups:
            if ship_group.get_total_ships() > 0:
                return True
        
        return False
    
    def execute(self, game_state: GameState) -> ActionOutcome:
        """Execute automatic exploration."""
        if not self.validate(game_state):
            return ActionOutcome(ActionResult.INVALID, "Auto-exploration validation failed")
        
        player = game_state.get_player_by_id(self.player_id)
        exploration_orders = self._generate_exploration_orders(player, game_state)
        
        if not exploration_orders:
            return ActionOutcome(
                ActionResult.SUCCESS,
                "No unexplored systems within range",
                {"exploration_orders": 0}
            )
        
        # Execute exploration using regular exploration action
        exploration_action = ExplorationAction(self.player_id, exploration_orders)
        result = exploration_action.execute(game_state)
        
        self.executed = True
        self.outcome = ActionOutcome(
            result.result,
            f"Auto-exploration: {result.message}",
            result.data
        )
        
        self.log_execution(game_state, self.outcome)
        return self.outcome
    
    def _generate_exploration_orders(self, player, game_state: GameState) -> List[ExplorationOrder]:
        """Generate exploration orders for reachable unexplored systems."""
        orders = []
        systems_to_explore = []
        
        # Find all ship locations
        for ship_group in player.ship_groups:
            location = ship_group.location
            
            # Find unexplored systems within range
            max_range = player.current_ship_speed
            nearby_systems = game_state.board.get_systems_within_range(location, max_range)
            
            for system_hex in nearby_systems:
                if (not game_state.board.is_system_explored(system_hex, player.player_id) and
                    system_hex not in [s["hex"] for s in systems_to_explore]):
                    
                    # Calculate strategic priority
                    distance = game_state.board.calculate_hex_distance(location, system_hex)
                    priority = max_range - distance  # Closer is higher priority
                    
                    systems_to_explore.append({
                        "hex": system_hex,
                        "from_location": location,
                        "distance": distance,
                        "priority": priority,
                        "ship_group": ship_group
                    })
        
        # Sort by priority and limit
        systems_to_explore.sort(key=lambda s: s["priority"], reverse=True)
        systems_to_explore = systems_to_explore[:self.max_systems]
        
        # Create exploration orders
        for system_info in systems_to_explore:
            ship_group = system_info["ship_group"]
            
            # Choose explorer ship type
            if self.prefer_scouts and ShipType.SCOUT in ship_group.get_ship_counts():
                explorer_type = ShipType.SCOUT
                explorer_count = min(1, ship_group.get_ship_counts()[ShipType.SCOUT])
            else:
                # Use any available ship
                ship_counts = ship_group.get_ship_counts()
                for ship_type, count in ship_counts.items():
                    if count > 0:
                        explorer_type = ship_type
                        explorer_count = 1
                        break
                else:
                    continue  # No ships available
            
            # Check for warship escort
            has_warships = ship_group.has_warships()
            
            # Move ship to exploration target first (would need movement action)
            # For now, assume ship is already at location
            if system_info["from_location"] == system_info["hex"]:
                order = ExplorationOrder(
                    location=system_info["hex"],
                    explorer_ship_type=explorer_type,
                    explorer_count=explorer_count,
                    has_warship_escort=has_warships
                )
                orders.append(order)
        
        return orders


class ScoutingMissionAction(BaseAction):
    """Specialized exploration action for scouting missions."""
    
    def __init__(self, player_id: int, target_locations: List[str], scout_count: int = 1):
        super().__init__(player_id, "scouting_mission")
        self.target_locations = target_locations
        self.scout_count = scout_count
    
    def validate(self, game_state: GameState) -> bool:
        """Validate scouting mission."""
        player = game_state.get_player_by_id(self.player_id)
        if not player:
            return False
        
        # Check if player has enough scouts
        total_scouts = 0
        for ship_group in player.ship_groups:
            total_scouts += ship_group.get_ship_counts().get(ShipType.SCOUT, 0)
        
        required_scouts = len(self.target_locations) * self.scout_count
        if total_scouts < required_scouts:
            return False
        
        # Validate all target locations
        for location in self.target_locations:
            try:
                GameValidator.validate_hex_coordinate(location)
                if not game_state.board.is_valid_location(location):
                    return False
            except Exception:
                return False
        
        return True
    
    def execute(self, game_state: GameState) -> ActionOutcome:
        """Execute scouting mission."""
        if not self.validate(game_state):
            return ActionOutcome(ActionResult.INVALID, "Scouting mission validation failed")
        
        player = game_state.get_player_by_id(self.player_id)
        
        # Find optimal scout deployment
        scout_assignments = self._assign_scouts_to_targets(player, game_state)
        
        # Create exploration orders for assigned scouts
        exploration_orders = []
        for assignment in scout_assignments:
            if assignment["scouts_available"] > 0:
                order = ExplorationOrder(
                    location=assignment["target"],
                    explorer_ship_type=ShipType.SCOUT,
                    explorer_count=min(self.scout_count, assignment["scouts_available"]),
                    has_warship_escort=False  # Scouts don't need escort
                )
                exploration_orders.append(order)
        
        if not exploration_orders:
            return ActionOutcome(
                ActionResult.FAILURE,
                "No scouts could be assigned to targets"
            )
        
        # Execute explorations
        exploration_action = ExplorationAction(self.player_id, exploration_orders)
        result = exploration_action.execute(game_state)
        
        self.executed = True
        self.outcome = ActionOutcome(
            result.result,
            f"Scouting mission: {result.message}",
            {
                **result.data,
                "targets_assigned": len(scout_assignments),
                "scouts_deployed": sum(o.explorer_count for o in exploration_orders)
            }
        )
        
        self.log_execution(game_state, self.outcome)
        return self.outcome
    
    def _assign_scouts_to_targets(self, player, game_state: GameState) -> List[Dict[str, Any]]:
        """Assign scouts to exploration targets optimally."""
        assignments = []
        
        for target in self.target_locations:
            best_assignment = None
            min_distance = float('inf')
            
            # Find closest ship group with scouts
            for ship_group in player.ship_groups:
                scout_count = ship_group.get_ship_counts().get(ShipType.SCOUT, 0)
                if scout_count > 0:
                    distance = game_state.board.calculate_hex_distance(
                        ship_group.location, target
                    )
                    
                    if distance < min_distance and distance <= player.current_ship_speed:
                        min_distance = distance
                        best_assignment = {
                            "target": target,
                            "source_location": ship_group.location,
                            "distance": distance,
                            "scouts_available": scout_count
                        }
            
            if best_assignment:
                assignments.append(best_assignment)
        
        return assignments


# Utility functions for exploration actions
def find_exploration_targets(game_state: GameState, player_id: int, 
                           max_range: int = None) -> List[Dict[str, Any]]:
    """Find potential exploration targets for a player."""
    player = game_state.get_player_by_id(player_id)
    if not player:
        return []
    
    if max_range is None:
        max_range = player.current_ship_speed
    
    targets = []
    
    # Check from each ship location
    for ship_group in player.ship_groups:
        location = ship_group.location
        
        # Find systems within range
        nearby_systems = game_state.board.get_systems_within_range(location, max_range)
        
        for system_hex in nearby_systems:
            if not game_state.board.is_system_explored(system_hex, player_id):
                distance = game_state.board.calculate_hex_distance(location, system_hex)
                
                targets.append({
                    "hex": system_hex,
                    "from_location": location,
                    "distance": distance,
                    "exploration_value": _calculate_exploration_value(system_hex, game_state)
                })
    
    # Remove duplicates and sort by value
    unique_targets = {t["hex"]: t for t in targets}.values()
    return sorted(unique_targets, key=lambda t: t["exploration_value"], reverse=True)


def _calculate_exploration_value(hex_coord: str, game_state: GameState) -> float:
    """Calculate exploration value for a hex coordinate."""
    # Basic value based on strategic position
    base_value = 1.0
    
    # Bonus for connectivity (more adjacent systems)
    adjacent_count = len(game_state.board.get_adjacent_systems(hex_coord))
    connectivity_bonus = adjacent_count * 0.1
    
    # Penalty for gas clouds
    gas_cloud_penalty = -0.5 if game_state.board.is_gas_cloud(hex_coord) else 0.0
    
    return base_value + connectivity_bonus + gas_cloud_penalty


def estimate_exploration_risk(ship_type: ShipType, has_escort: bool) -> float:
    """Estimate exploration risk (0.0 = no risk, 1.0 = maximum risk)."""
    if ship_type in [ShipType.CORVETTE, ShipType.FIGHTER, ShipType.DEATH_STAR]:
        return 0.0  # Warships have no exploration risk
    
    if has_escort:
        return 0.0  # Escorted ships have no risk
    
    # Unarmed ships have exploration risk
    if ship_type == ShipType.SCOUT:
        return 0.16  # 1/6 chance of loss
    elif ship_type == ShipType.COLONY_TRANSPORT:
        return 0.16  # Same risk as scouts
    
    return 0.0


def create_exploration_action(player_id: int, exploration_data: List[Dict[str, Any]]) -> ExplorationAction:
    """Create exploration action from exploration data."""
    orders = []
    
    for explore_data in exploration_data:
        order = ExplorationOrder(
            location=explore_data["location"],
            explorer_ship_type=ShipType(explore_data["ship_type"]),
            explorer_count=explore_data["count"],
            has_warship_escort=explore_data.get("has_escort", False)
        )
        orders.append(order)
    
    return ExplorationAction(player_id, orders)