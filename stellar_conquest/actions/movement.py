"""Ship movement actions for Stellar Conquest."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .base_action import BaseAction, ActionResult, ActionOutcome
from ..game.game_state import GameState
from ..core.enums import ShipType
from ..core.exceptions import InvalidActionError, GameStateError
from ..utils.validation import GameValidator
from ..utils.hex_utils import calculate_hex_distance


@dataclass
class MovementOrder:
    """Individual ship movement order."""
    from_location: str
    to_location: str
    ship_type: ShipType
    ship_count: int
    path: Optional[List[str]] = None


class MovementAction(BaseAction):
    """Handle ship movement between star systems."""
    
    def __init__(self, player_id: int, movement_orders: List[MovementOrder]):
        super().__init__(player_id, "movement")
        self.movement_orders = movement_orders
    
    def validate(self, game_state: GameState) -> bool:
        """Validate all movement orders."""
        player = game_state.get_player_by_id(self.player_id)
        if not player:
            return False
        
        for order in self.movement_orders:
            if not self._validate_single_movement(order, player, game_state):
                return False
        
        return True
    
    def _validate_single_movement(self, order: MovementOrder, player, game_state: GameState) -> bool:
        """Validate a single movement order."""
        try:
            # Validate hex coordinates
            GameValidator.validate_hex_coordinate(order.from_location)
            GameValidator.validate_hex_coordinate(order.to_location)
            
            # Check if player has ships at source location
            ship_group = player.get_ship_group_at_location(order.from_location)
            if not ship_group:
                return False
            
            # Check if ship group has required ships
            ship_counts = ship_group.get_ship_counts()
            if ship_counts.get(order.ship_type, 0) < order.ship_count:
                return False
            
            # Check movement range
            distance = calculate_hex_distance(order.from_location, order.to_location)
            max_speed = player.current_ship_speed
            if distance > max_speed:
                return False
            
            # Check command post range restrictions (unless unlimited range)
            if not player.has_unlimited_range:
                if not player.is_location_in_command_range(order.to_location):
                    # Exception: scouts can move anywhere
                    if order.ship_type != ShipType.SCOUT:
                        return False
            
            # Check that destination is valid on board
            if not game_state.board.is_valid_location(order.to_location):
                return False
            
            return True
            
        except Exception:
            return False
    
    def execute(self, game_state: GameState) -> ActionOutcome:
        """Execute all movement orders."""
        if not self.validate(game_state):
            return ActionOutcome(ActionResult.INVALID, "Movement validation failed")
        
        player = game_state.get_player_by_id(self.player_id)
        if not player:
            return ActionOutcome(ActionResult.FAILURE, "Player not found")
        
        successful_moves = []
        failed_moves = []
        
        for order in self.movement_orders:
            try:
                self._execute_single_movement(order, player, game_state)
                successful_moves.append(order)
            except Exception as e:
                failed_moves.append((order, str(e)))
        
        # Determine result
        if failed_moves:
            result = ActionResult.PARTIAL if successful_moves else ActionResult.FAILURE
            message = f"Completed {len(successful_moves)}/{len(self.movement_orders)} movements"
        else:
            result = ActionResult.SUCCESS
            message = f"All {len(self.movement_orders)} ships moved successfully"
        
        self.executed = True
        self.outcome = ActionOutcome(
            result, message, 
            {
                "successful_moves": len(successful_moves),
                "failed_moves": len(failed_moves),
                "movement_details": [
                    {
                        "from": order.from_location,
                        "to": order.to_location,
                        "ship_type": order.ship_type.value,
                        "count": order.ship_count
                    }
                    for order in successful_moves
                ]
            }
        )
        
        self.log_execution(game_state, self.outcome)
        return self.outcome
    
    def _execute_single_movement(self, order: MovementOrder, player, game_state: GameState):
        """Execute a single movement order."""
        # Calculate path if needed
        if order.path is None:
            order.path = game_state.board.find_path(
                order.from_location, 
                order.to_location, 
                player.current_ship_speed
            )
        
        # Handle gas cloud movement restrictions
        final_destination = self._handle_gas_cloud_movement(order, game_state)
        
        # Move the ships
        moved_count = player.move_ships(
            order.from_location, 
            final_destination, 
            order.ship_type, 
            order.ship_count
        )
        
        if moved_count != order.ship_count:
            raise InvalidActionError(f"Only moved {moved_count}/{order.ship_count} ships")
        
        # Set destination for ships that didn't reach final target
        if final_destination != order.to_location:
            ship_group = player.get_ship_group_at_location(final_destination)
            if ship_group:
                for ship in ship_group.get_ships_by_type(order.ship_type):
                    ship.set_destination(order.to_location)
    
    def _handle_gas_cloud_movement(self, order: MovementOrder, game_state: GameState) -> str:
        """Handle movement through gas clouds (1 hex per turn limit)."""
        if not order.path:
            return order.to_location
        
        # Check each step in path for gas clouds
        for i, hex_coord in enumerate(order.path[1:], 1):  # Skip starting hex
            if game_state.board.is_gas_cloud(hex_coord):
                # Ship can only move 1 hex into gas cloud and must stop
                return hex_coord
        
        return order.to_location
    
    def can_undo(self) -> bool:
        """Movement can be undone for scenario analysis."""
        return True
    
    def undo(self, game_state: GameState) -> ActionOutcome:
        """Undo movement by reversing ship positions."""
        if not self.executed or not self.outcome:
            return ActionOutcome(ActionResult.FAILURE, "Action not executed yet")
        
        player = game_state.get_player_by_id(self.player_id)
        if not player:
            return ActionOutcome(ActionResult.FAILURE, "Player not found")
        
        # Reverse successful movements
        successful_details = self.outcome.data.get("movement_details", [])
        
        for move_detail in reversed(successful_details):
            try:
                player.move_ships(
                    move_detail["to"],
                    move_detail["from"], 
                    ShipType(move_detail["ship_type"]),
                    move_detail["count"]
                )
            except Exception as e:
                return ActionOutcome(ActionResult.FAILURE, f"Undo failed: {str(e)}")
        
        self.executed = False
        return ActionOutcome(ActionResult.SUCCESS, "Movement undone successfully")


class SetDestinationAction(BaseAction):
    """Set destinations for ships that can change course."""
    
    def __init__(self, player_id: int, location: str, ship_type: ShipType, 
                 count: int, new_destination: str):
        super().__init__(player_id, "set_destination")
        self.location = location
        self.ship_type = ship_type
        self.count = count
        self.new_destination = new_destination
    
    def validate(self, game_state: GameState) -> bool:
        """Validate destination change."""
        player = game_state.get_player_by_id(self.player_id)
        if not player:
            return False
        
        try:
            GameValidator.validate_hex_coordinate(self.location)
            GameValidator.validate_hex_coordinate(self.new_destination)
            
            # Check if player has ships at location
            ship_group = player.get_ship_group_at_location(self.location)
            if not ship_group:
                return False
            
            # Check if has required ships
            ship_counts = ship_group.get_ship_counts()
            if ship_counts.get(self.ship_type, 0) < self.count:
                return False
            
            # Check communication restrictions
            if not player.has_unlimited_communication:
                # Can only redirect to explored star systems
                if not game_state.board.is_system_explored(self.new_destination, self.player_id):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def execute(self, game_state: GameState) -> ActionOutcome:
        """Execute destination change."""
        if not self.validate(game_state):
            return ActionOutcome(ActionResult.INVALID, "Destination change validation failed")
        
        player = game_state.get_player_by_id(self.player_id)
        ship_group = player.get_ship_group_at_location(self.location)
        
        ships_updated = 0
        target_ships = ship_group.get_ships_by_type(self.ship_type)
        
        remaining_count = self.count
        for ship in target_ships:
            if remaining_count <= 0:
                break
            
            if ship.count <= remaining_count:
                # Update entire ship group
                ship.set_destination(self.new_destination)
                ships_updated += ship.count
                remaining_count -= ship.count
            else:
                # Split ship group
                split_ship = ship.split(remaining_count)
                split_ship.set_destination(self.new_destination)
                ship_group.add_ships(split_ship)
                ships_updated += remaining_count
                remaining_count = 0
        
        self.executed = True
        self.outcome = ActionOutcome(
            ActionResult.SUCCESS,
            f"Updated destination for {ships_updated} {self.ship_type.value}(s)",
            {
                "ships_updated": ships_updated,
                "new_destination": self.new_destination
            }
        )
        
        self.log_execution(game_state, self.outcome)
        return self.outcome


class FirstTurnDeploymentAction(BaseAction):
    """Special action for first turn fleet deployment from entry hex."""
    
    def __init__(self, player_id: int, deployment_plan: Dict[str, int]):
        super().__init__(player_id, "first_turn_deployment")
        self.deployment_plan = deployment_plan  # {hex_coord: ship_count}
    
    def validate(self, game_state: GameState) -> bool:
        """Validate first turn deployment."""
        player = game_state.get_player_by_id(self.player_id)
        if not player:
            return False
        
        # Must be turn 1
        if game_state.current_turn != 1:
            return False
        
        # Player must not have deployed yet
        if player.turns_completed > 0:
            return False
        
        # Check total ships don't exceed starting fleet
        total_deployed = sum(self.deployment_plan.values())
        starting_ships = player.get_ship_group_at_location(player.entry_hex)
        if not starting_ships or starting_ships.get_total_ships() < total_deployed:
            return False
        
        # Validate all deployment hexes are reachable
        for hex_coord in self.deployment_plan.keys():
            try:
                GameValidator.validate_hex_coordinate(hex_coord)
                distance = calculate_hex_distance(player.entry_hex, hex_coord)
                if distance > player.current_ship_speed:
                    return False
            except Exception:
                return False
        
        return True
    
    def execute(self, game_state: GameState) -> ActionOutcome:
        """Execute first turn deployment."""
        if not self.validate(game_state):
            return ActionOutcome(ActionResult.INVALID, "First turn deployment validation failed")
        
        player = game_state.get_player_by_id(self.player_id)
        
        deployments_made = {}
        for hex_coord, ship_count in self.deployment_plan.items():
            # Move scouts to deployment location
            moved = player.move_ships(
                player.entry_hex, 
                hex_coord, 
                ShipType.SCOUT, 
                ship_count
            )
            deployments_made[hex_coord] = moved
        
        self.executed = True
        self.outcome = ActionOutcome(
            ActionResult.SUCCESS,
            f"Deployed ships to {len(deployments_made)} locations",
            {
                "deployments": deployments_made,
                "total_ships": sum(deployments_made.values())
            }
        )
        
        self.log_execution(game_state, self.outcome)
        return self.outcome


# Utility functions for movement actions
def create_movement_action(player_id: int, movements: List[Dict[str, Any]]) -> MovementAction:
    """Create movement action from movement data."""
    orders = []
    for move_data in movements:
        order = MovementOrder(
            from_location=move_data["from"],
            to_location=move_data["to"],
            ship_type=ShipType(move_data["ship_type"]),
            ship_count=move_data["count"]
        )
        orders.append(order)
    
    return MovementAction(player_id, orders)


def validate_movement_legality(game_state: GameState, player_id: int, 
                             from_hex: str, to_hex: str, ship_type: ShipType) -> List[str]:
    """Validate movement legality and return any constraint violations."""
    violations = []
    
    player = game_state.get_player_by_id(player_id)
    if not player:
        violations.append("Player not found")
        return violations
    
    try:
        # Check distance
        distance = calculate_hex_distance(from_hex, to_hex)
        if distance > player.current_ship_speed:
            violations.append(f"Distance {distance} exceeds ship speed {player.current_ship_speed}")
        
        # Check command post range
        if not player.has_unlimited_range and ship_type != ShipType.SCOUT:
            if not player.is_location_in_command_range(to_hex):
                violations.append("Destination outside command post range")
        
        # Check board validity
        if not game_state.board.is_valid_location(to_hex):
            violations.append("Invalid destination hex")
        
    except Exception as e:
        violations.append(f"Validation error: {str(e)}")
    
    return violations


def calculate_movement_time(game_state: GameState, from_hex: str, to_hex: str) -> int:
    """Calculate turns required for movement considering gas clouds."""
    path = game_state.board.find_path(from_hex, to_hex, 10)  # Max range for calculation
    
    if not path:
        return -1  # No valid path
    
    turns = 0
    current_speed_remaining = 0
    
    for i in range(1, len(path)):  # Skip starting hex
        hex_coord = path[i]
        
        if current_speed_remaining == 0:
            turns += 1
            current_speed_remaining = game_state.get_player_by_id(1).current_ship_speed  # Default speed
        
        current_speed_remaining -= 1
        
        # Gas clouds force end of movement
        if game_state.board.is_gas_cloud(hex_coord):
            current_speed_remaining = 0
    
    return turns