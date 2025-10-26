"""Ship movement actions."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .base_action import BaseAction, ActionResult, ActionOutcome
from ..game.game_state import GameState
from ..entities.ship import ShipType
from ..entities.fleet import Fleet
import random


@dataclass
class MovementOrder:
    """Individual ship movement order."""
    fleet_location: str  # Current hex
    ship_type: ShipType
    ship_count: int
    destination: str  # Target hex
    path: Optional[List[str]] = None  # Calculated path


class MovementAction(BaseAction):
    """Handle ship movement including first turn entry and range restrictions."""
    
    def __init__(self, player_id: int, movement_orders: List[MovementOrder]):
        super().__init__(player_id, "movement")
        self.movement_orders = movement_orders
    
    def validate(self, game_state: GameState) -> bool:
        """Validate all movement orders."""
        player = game_state.players.get(self.player_id)
        if not player:
            return False
        
        for order in self.movement_orders:
            if not self._validate_single_movement(order, player, game_state):
                return False
        
        return True
    
    def _validate_single_movement(self, order: MovementOrder, player, game_state: GameState) -> bool:
        """Validate a single movement order."""
        # Check if player has fleet at source location
        fleet = player.get_fleet_at_location(order.fleet_location)
        if not fleet:
            return False
        
        # Check if fleet has required ships
        ship_counts = fleet.ship_counts
        if ship_counts.get(order.ship_type, 0) < order.ship_count:
            return False
        
        # Check movement range
        distance = game_state.galaxy.calculate_distance(order.fleet_location, order.destination)
        max_speed = player.current_ship_speed
        if distance > max_speed:
            return False
        
        # Check command post range restrictions (unless scout or unlimited range)
        if order.ship_type != ShipType.SCOUT and not player.has_unlimited_range:
            if not self._check_command_post_range(order, player, game_state):
                return False
        
        # Check ship communication restrictions
        if not player.has_unlimited_communication:
            if not self._validate_destination_targeting(order, game_state):
                return False
        
        return True
    
    def _check_command_post_range(self, order: MovementOrder, player, game_state: GameState) -> bool:
        """Check if destination is within 8 hexes of a command post."""
        # Ships must stay within 8 hexes of friendly command post
        max_range = 8
        
        # Check distance to all command posts
        for command_post_hex in player.command_posts:
            distance = game_state.galaxy.calculate_distance(order.destination, command_post_hex)
            if distance <= max_range:
                return True
        
        # Check distance to entry hex (acts as command post)
        entry_hex = game_state.galaxy.entry_hexes.get(player.player_id)
        if entry_hex:
            distance = game_state.galaxy.calculate_distance(order.destination, entry_hex)
            if distance <= max_range:
                return True
        
        return False
    
    def _validate_destination_targeting(self, order: MovementOrder, game_state: GameState) -> bool:
        """Validate destination based on communication restrictions."""
        # Ships can only be directed to star hexes (unless unlimited communication)
        star_system = game_state.galaxy.get_star_system(order.destination)
        return star_system is not None
    
    def execute(self, game_state: GameState) -> ActionOutcome:
        """Execute all movement orders."""
        if not self.validate(game_state):
            return ActionOutcome(ActionResult.INVALID, "Movement validation failed")
        
        player = game_state.players[self.player_id]
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
                "failed_moves": len(failed_moves)
            }
        )
        
        self.log_execution(game_state, self.outcome)
        return self.outcome
    
    def _execute_single_movement(self, order: MovementOrder, player, game_state: GameState):
        """Execute a single movement order."""
        # Get source fleet
        source_fleet = player.get_fleet_at_location(order.fleet_location)
        
        # Calculate path through gas clouds
        path = self._calculate_movement_path(order, game_state)
        
        # Handle gas cloud movement restrictions
        final_destination = self._handle_gas_cloud_movement(order, path, game_state)
        
        # Remove ships from source fleet
        source_fleet.remove_ships(order.ship_type, order.ship_count)
        
        # Add ships to destination fleet (create if needed)
        dest_fleet = player.get_fleet_at_location(final_destination)
        if not dest_fleet:
            dest_fleet = Fleet(player.player_id, final_destination)
            player.fleets.append(dest_fleet)
        
        dest_fleet.add_ships(order.ship_type, order.ship_count, order.destination)
        
        # Clean up empty source fleet
        if source_fleet.total_ships == 0:
            player.fleets.remove(source_fleet)
        
        # Handle forced stops in star hexes with enemy ships
        self._handle_enemy_contact(final_destination, player, game_state)
    
    def _calculate_movement_path(self, order: MovementOrder, game_state: GameState) -> List[str]:
        """Calculate movement path considering gas clouds."""
        # Use galaxy pathfinding
        path = game_state.galaxy.find_path(
            order.fleet_location, 
            order.destination, 
            game_state.players[self.player_id].current_ship_speed
        )
        return path or [order.fleet_location, order.destination]
    
    def _handle_gas_cloud_movement(self, order: MovementOrder, path: List[str], game_state: GameState) -> str:
        """Handle movement through gas clouds (1 hex per turn limit)."""
        current_location = order.fleet_location
        
        for hex_coord in path[1:]:  # Skip starting hex
            if game_state.galaxy.is_gas_cloud_hex(hex_coord):
                # Ship can only move 1 hex into gas cloud and must stop
                return hex_coord
            current_location = hex_coord
        
        return order.destination
    
    def _handle_enemy_contact(self, location: str, player, game_state: GameState):
        """Handle forced stops when entering hex with enemy ships."""
        enemy_players = game_state.get_player_at_location(location)
        enemy_players = [pid for pid in enemy_players if pid != player.player_id]
        
        if enemy_players:
            # Check if arriving ships are unarmed and face immediate attack
            arriving_fleet = player.get_fleet_at_location(location)
            if arriving_fleet:
                unarmed_ships = [ship for ship in arriving_fleet.ships if ship.is_unarmed]
                if unarmed_ships:
                    self._resolve_unarmed_ship_attacks(location, player, game_state, unarmed_ships)
            
            # Ship is forced to stop - combat will be resolved in combat phase
            game_state.log_action("enemy_contact", {
                "location": location,
                "player": player.player_id,
                "enemies": enemy_players
            })
    
    def _resolve_unarmed_ship_attacks(self, location: str, player, game_state: GameState, unarmed_ships):
        """Resolve enemy warship attacks on unarmed ships during movement."""
        # Get enemy warships at this location
        enemy_warships = self._get_enemy_warships_at_location(location, player, game_state)
        
        if not enemy_warships:
            return  # No enemy warships to attack with
        
        losses = []
        flee_ships = []
        
        for ship_group in unarmed_ships:
            for _ in range(ship_group.count):
                # Each unarmed ship faces attack from enemy warships
                if self._attempt_unarmed_ship_destruction(ship_group.ship_type, enemy_warships):
                    losses.append({
                        "ship_type": ship_group.ship_type.value,
                        "location": location,
                        "destroyed_by": "enemy_warships"
                    })
                    # Remove ship from fleet
                    ship_group.remove_ships(1)
                else:
                    # Ship survives - can potentially flee
                    flee_ships.append(ship_group)
        
        # Log losses
        if losses:
            game_state.log_action("unarmed_ships_destroyed", {
                "location": location,
                "player": player.player_id,
                "losses": losses
            })
        
        # Handle fleeing for survivors
        if flee_ships:
            self._handle_unarmed_ship_flee(location, player, game_state, flee_ships)
    
    def _get_enemy_warships_at_location(self, location: str, player, game_state: GameState):
        """Get all enemy warships at the specified location."""
        enemy_warships = []
        
        for other_player in game_state.players.values():
            if other_player.player_id == player.player_id:
                continue
            
            enemy_fleet = other_player.get_fleet_at_location(location)
            if enemy_fleet:
                warships = [ship for ship in enemy_fleet.ships if ship.is_warship]
                enemy_warships.extend(warships)
        
        return enemy_warships
    
    def _attempt_unarmed_ship_destruction(self, target_ship_type: ShipType, enemy_warships) -> bool:
        """Attempt to destroy an unarmed ship using enemy warships."""
        # Use simplified attack resolution - stronger warships have better chances
        # Death stars auto-kill scouts/transports, fighters are very effective, corvettes less so
        
        for enemy_ship in enemy_warships:
            if enemy_ship.ship_type == ShipType.DEATH_STAR:
                # Death stars auto-kill unarmed ships (Rules 4.1 - 1-6 on 1 die)
                return True
            elif enemy_ship.ship_type == ShipType.FIGHTER:
                # Fighters very effective against unarmed ships (1-5 on 1 die)
                if random.randint(1, 6) <= 5:
                    return True
            elif enemy_ship.ship_type == ShipType.CORVETTE:
                # Corvettes moderately effective (1-3 on 1 die) 
                if random.randint(1, 6) <= 3:
                    return True
        
        return False  # Ship survives all attacks
    
    def _handle_unarmed_ship_flee(self, location: str, player, game_state: GameState, surviving_ships):
        """Handle fleeing of surviving unarmed ships to adjacent hexes."""
        if not surviving_ships:
            return
        
        # Get adjacent hexes
        adjacent_hexes = game_state.galaxy.get_adjacent_hexes(location)
        
        if not adjacent_hexes:
            return  # Nowhere to flee
        
        # Choose random adjacent hex for immediate fleeing
        flee_destination = random.choice(adjacent_hexes)
        
        # Group ships by taskforce to handle redirection properly
        taskforce_ships = {}
        for ship_group in surviving_ships:
            if ship_group.count > 0:
                tf_id = getattr(ship_group, 'task_force_id', 1)
                if tf_id not in taskforce_ships:
                    taskforce_ships[tf_id] = {}
                if ship_group.ship_type not in taskforce_ships[tf_id]:
                    taskforce_ships[tf_id][ship_group.ship_type] = 0
                taskforce_ships[tf_id][ship_group.ship_type] += ship_group.count
        
        # Move surviving ships to flee destination
        for ship_group in surviving_ships:
            if ship_group.count > 0:  # Still has ships after attacks
                # Create new fleet at flee destination or add to existing
                flee_fleet = player.get_fleet_at_location(flee_destination)
                if not flee_fleet:
                    flee_fleet = Fleet(player.player_id, flee_destination)
                    player.fleets.append(flee_fleet)
                
                # Move all remaining ships of this type
                flee_fleet.add_ships(ship_group.ship_type, ship_group.count, flee_destination)
                
                # Remove from original location
                original_fleet = player.get_fleet_at_location(location)
                if original_fleet:
                    original_fleet.remove_ships(ship_group.ship_type, ship_group.count)
        
        # Now handle redirection of movement plans to avoid returning to the problem location
        self._redirect_fled_taskforces(game_state, player, taskforce_ships, location, flee_destination)
        
        game_state.log_action("unarmed_ships_flee", {
            "from_location": location,
            "to_location": flee_destination,
            "player": player.player_id,
            "taskforces_affected": list(taskforce_ships.keys())
        })
    
    def _redirect_fled_taskforces(self, game_state: GameState, player, taskforce_ships, fled_from_location, current_location):
        """Redirect taskforce movement plans after fleeing to avoid returning to problem location."""
        from stellar_conquest.ai.destination_selector import handle_taskforce_combat_redirect
        
        if not hasattr(game_state, 'movement_plans'):
            return
        
        if player.player_id not in game_state.movement_plans:
            return
        
        # Handle redirection for each taskforce that fled
        for tf_id, ship_composition in taskforce_ships.items():
            if tf_id == 1:  # TF1 (main base) doesn't have movement plans
                continue
                
            if tf_id not in game_state.movement_plans[player.player_id]:
                continue  # No movement plan to redirect
            
            movement_plan = game_state.movement_plans[player.player_id][tf_id]
            original_destination = movement_plan.get('final_destination')
            
            if not original_destination:
                continue
            
            # Use intelligent destination selection for new strategic destination
            new_destination = handle_taskforce_combat_redirect(
                game_state, player, tf_id, current_location, original_destination,
                'fled_from_combat', ship_composition
            )
            
            if new_destination and new_destination != original_destination:
                # Calculate new path from current flee location to new destination
                from stellar_conquest.utils.hex_utils import find_path
                new_path = find_path(current_location, new_destination)
                
                if new_path:
                    print(f"   🔄 TF{tf_id} flight path redirected from {original_destination} to {new_destination}")
                    movement_plan.update({
                        'final_destination': new_destination,
                        'planned_path': new_path,
                        'current_location': current_location,
                        'path_index': 0,  # Reset path progress
                        'original_destination': original_destination,
                        'redirected_due_to': 'fled_from_combat',
                        'fled_from_location': fled_from_location,
                        'redirect_reason': f"Fled from combat at {fled_from_location}, avoiding return"
                    })
                else:
                    print(f"   ❌ Could not find path to new destination {new_destination} for fled TF{tf_id}")
            else:
                print(f"   ➡️  TF{tf_id} will continue toward original destination {original_destination} when safe")


class FirstTurnEntryAction(MovementAction):
    """Special movement action for first turn entry."""
    
    def __init__(self, player_id: int):
        # Create movement orders for starting fleet from entry hex
        entry_orders = self._create_entry_orders(player_id)
        super().__init__(player_id, entry_orders)
    
    def _create_entry_orders(self, player_id: int) -> List[MovementOrder]:
        """Create movement orders for starting fleet entry."""
        # Starting fleet: 4 scouts, 4 corvettes, 35 colony transports
        return [
            MovementOrder(f"entry_{player_id}", ShipType.SCOUT, 4, "A1"),  # Temporary
            MovementOrder(f"entry_{player_id}", ShipType.CORVETTE, 4, "A1"),
            MovementOrder(f"entry_{player_id}", ShipType.COLONY_TRANSPORT, 35, "A1")
        ]
    
    def validate(self, game_state: GameState) -> bool:
        """First turn entry has special validation rules."""
        player = game_state.players.get(self.player_id)
        if not player:
            return False
        
        # Must be player's first turn
        if player.turns_completed > 0:
            return False
        
        # Entry hex must be available
        entry_hex = game_state.galaxy.entry_hexes.get(player.player_id)
        return entry_hex is not None