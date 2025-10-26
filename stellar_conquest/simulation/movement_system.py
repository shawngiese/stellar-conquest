"""
Movement System Module for Stellar Conquest Simulation

This module handles all movement-related functionality including:
- Ship movement with enemy interaction rules
- Task force management and coordination
- Pathfinding and route planning
- Movement validation and execution
"""

from stellar_conquest.utils.hex_utils import calculate_hex_distance, find_path
from simulation.combat_system import check_enemy_ships_at_location, is_star_hex


def split_ships_into_task_force(player, location, ship_type, count, task_force_id):
    """Split ships from main fleet into a new task force."""
    from stellar_conquest.entities.ship import Ship, ShipGroup
    
    # Find the source ship group
    source_group = None
    for group in player.ship_groups:
        for ship in group.ships:
            if ship.location == location and ship.ship_type == ship_type and ship.task_force_id == 1:
                if ship.count >= count:
                    source_group = group
                    break
        if source_group:
            break
    
    if not source_group:
        return False
        
    # Remove ships from source
    ships_to_remove = []
    for ship in source_group.ships:
        if ship.location == location and ship.ship_type == ship_type and ship.task_force_id == 1:
            if ship.count >= count:
                ship.count -= count
                if ship.count == 0:
                    ships_to_remove.append(ship)
                break
    
    for ship in ships_to_remove:
        source_group.ships.remove(ship)
    
    # Create new task force group
    new_ship = Ship(ship_type, count, location, task_force_id)
    
    # Find existing group for this task force or create new one
    target_group = None
    for group in player.ship_groups:
        if group.ships and group.ships[0].task_force_id == task_force_id:
            target_group = group
            break
    
    if not target_group:
        target_group = ShipGroup(location)
        player.ship_groups.append(target_group)
    
    target_group.add_ships(new_ship)
    return True


def remove_ships_from_task_force(player, location, ship_type, count, task_force_id):
    """Remove ships from a specific task force at a location."""
    removed_count = 0
    groups_to_remove = []
    
    # Find all ship groups at this location
    for group in player.ship_groups:
        ships_to_remove = []
        for ship in group.ships:
            if (ship.location == location and 
                ship.ship_type == ship_type and 
                ship.task_force_id == task_force_id and 
                removed_count < count):
                
                ships_to_take = min(ship.count, count - removed_count)
                ship.count -= ships_to_take
                removed_count += ships_to_take
                
                if ship.count == 0:
                    ships_to_remove.append(ship)
        
        # Remove depleted ships
        for ship in ships_to_remove:
            group.ships.remove(ship)
        
        # Mark empty groups for removal
        if not group.ships:
            groups_to_remove.append(group)
    
    # Remove empty groups
    for group in groups_to_remove:
        player.ship_groups.remove(group)
    
    return removed_count


def move_ships_with_task_force_id(game_state, player, from_location, to_location, ship_type, count, task_force_id):
    """Move ships while preserving task force identity."""
    from stellar_conquest.entities.ship import Ship, ShipGroup
    
    # Remove ships from source location - task force specific removal
    removed = remove_ships_from_task_force(player, from_location, ship_type, count, task_force_id)
    if removed == 0:
        return False
    
    # Add ships to destination location with same task force ID
    new_ship = Ship(ship_type, removed, to_location, task_force_id)
    
    # Find existing group at destination for this task force or create new one
    target_group = None
    for group in player.ship_groups:
        if (group.ships and 
            group.ships[0].location == to_location and 
            group.ships[0].task_force_id == task_force_id):
            target_group = group
            break
    
    if not target_group:
        target_group = ShipGroup(to_location)
        player.ship_groups.append(target_group)
    
    target_group.add_ships(new_ship)
    return True


def plan_next_move_toward_target(game_state, current_location, target_location, ship_speed, turn_number=1):
    """Plan next hex to move toward a distant target."""
    if current_location == target_location:
        return current_location
    
    # Calculate effective movement for this turn
    # Turn 1 has -1 penalty for entering the game map
    effective_speed = ship_speed
    if turn_number == 1:
        effective_speed = max(1, ship_speed - 1)  # -1 penalty, minimum 1 movement
    
    # Get the complete path
    path = find_path(current_location, target_location)
    if not path or len(path) <= 1:
        return current_location
    
    if path and len(path) > 1:
        # Move as far as possible this turn using effective speed
        steps_this_turn = min(effective_speed, len(path) - 1)
        return path[steps_this_turn]
    
    return current_location


def generate_route_display(game_state, start_hex, destination_hex, ship_speed, turn_number=1):
    """Generate a bus-route style display of the path from start to destination."""
    # Get the complete path using proper hex grid pathfinding
    path = find_path(start_hex, destination_hex)
    
    if not path:
        return f"{start_hex} → {destination_hex}"
    
    # Calculate effective movement for this turn
    # Turn 1 has -1 penalty for entering the game map
    effective_speed = ship_speed
    if turn_number == 1:
        effective_speed = max(1, ship_speed - 1)  # -1 penalty, minimum 1 movement
    
    # Determine which hex will be reached at the end of this turn
    steps_this_turn = min(effective_speed, len(path) - 1)
    current_turn_destination = path[steps_this_turn]
    
    # Build the route string with the current turn destination bolded
    route_parts = []
    for i, hex_coord in enumerate(path):
        if hex_coord == current_turn_destination and i > 0:  # Don't bold the starting position
            route_parts.append(f"**{hex_coord}**")  # Bold the current turn destination
        else:
            route_parts.append(hex_coord)
    
    return " → ".join(route_parts)


def make_movement_decisions(game_state, player, turn_number):
    """Execute movement for existing task forces along their declared paths."""
    from simulation.simulation_utilities import print_phase_header
    
    print_phase_header(turn_number, "a", "SHIP MOVEMENT")
    
    # Initialize movement plans if not exists
    if not hasattr(game_state, 'movement_plans'):
        game_state.movement_plans = {}
    if player.player_id not in game_state.movement_plans:
        game_state.movement_plans[player.player_id] = {}
    
    movements_made = 0
    
    # Get all task forces that have movement plans
    task_forces_to_move = []
    if player.player_id in game_state.movement_plans:
        for tf_number, plan in game_state.movement_plans[player.player_id].items():
            if 'planned_path' in plan:
                task_forces_to_move.append(tf_number)
    
    # Also include TF1 for status reporting
    all_task_forces = [1] + sorted(task_forces_to_move)
    
    # Process each task force for movement
    for tf_number in all_task_forces:
        # Find ships belonging to this task force across all groups
        tf_ships = {}
        tf_location = None
        
        for group in player.ship_groups:
            for ship in group.ships:
                if ship.task_force_id == tf_number:
                    tf_location = ship.location
                    if ship.ship_type not in tf_ships:
                        tf_ships[ship.ship_type] = 0
                    tf_ships[ship.ship_type] += ship.count
        
        if not tf_ships:
            continue  # No ships found for this task force
        
        print(f"\n🚀 TF{tf_number} at {tf_location}:")
        ship_summary = ", ".join([f"{count} {ship_type.value.lower()}" for ship_type, count in tf_ships.items() if count > 0])
        print(f"   Ships: {ship_summary}")
        
        # TF1 never moves - it's the permanent home base
        if tf_number == 1:
            print(f"   🏠 TF1 remains at home base {tf_location} (command center)")
            continue
        
        # Check if this task force has a declared movement plan
        existing_plan = None
        if player.player_id in game_state.movement_plans:
            existing_plan = game_state.movement_plans[player.player_id].get(tf_number)
        
        if not existing_plan or 'planned_path' not in existing_plan:
            print(f"   ⚠️  No movement plan declared for TF{tf_number} - stays at {tf_location}")
            continue
        
        # Check if this task force can move this turn (production task forces can't move until next turn)
        can_move = existing_plan.get('can_move_this_turn', True)
        if not can_move:
            print(f"   ⏸️  TF{tf_number} created from production - cannot move until next turn")
            # Mark that it can move next turn
            existing_plan['can_move_this_turn'] = True
            continue
        
        # Execute movement along declared path
        planned_path = existing_plan['planned_path']
        path_index = existing_plan.get('path_index', 0)
        destination = existing_plan['final_destination']
        destination_name = existing_plan.get('target_name', destination)
        current_location = tf_location
        
        print(f"   📋 Declared path: {' → '.join(planned_path)}")
        print(f"   🎯 Final destination: {destination_name} at {destination}")
        print(f"   📍 Current path position: index {path_index} ({current_location})")
        
        # Calculate movement for this turn
        base_speed = player.current_ship_speed
        
        # Apply first turn movement penalty (all players get -1 movement on turn 1)
        if turn_number == 1:
            effective_speed = max(1, base_speed - 1)  # -1 penalty, minimum 1 movement
            print(f"   ⚡ Movement points this turn: {effective_speed} (base {base_speed} - 1 first turn penalty)")
        else:
            effective_speed = base_speed
            print(f"   ⚡ Movement points this turn: {effective_speed}")
        
        # Plan movement with enemy interaction rules
        original_target_index = min(path_index + effective_speed, len(planned_path) - 1)
        
        # Check each hex along the movement path for enemy presence (Rule 3.8.3)
        actual_end_index = path_index
        forced_stop_location = None
        
        for step in range(1, effective_speed + 1):
            step_index = path_index + step
            if step_index >= len(planned_path):
                break
                
            step_location = planned_path[step_index]
            
            # Check for enemy ships at this location
            enemy_ships = check_enemy_ships_at_location(game_state, step_location, player)
            
            # Rule 3.8.3: Ships forced to stop if entering star hex with enemy ships
            if enemy_ships and is_star_hex(game_state, step_location):
                print(f"   ⚠️  Enemy ships detected at {step_location} (star hex)")
                print(f"   🛑 FORCED STOP: Rule 3.8.3 - Must end turn when entering enemy-occupied star hex")
                for enemy_id, ships in enemy_ships.items():
                    enemy_player = next(p for p in game_state.players if p.player_id == enemy_id)
                    enemy_ship_summary = ", ".join([f"{count} {ship_type.value.lower()}" for ship_type, count in ships.items()])
                    print(f"       {enemy_player.name}: {enemy_ship_summary}")
                forced_stop_location = step_location
                actual_end_index = step_index
                break
            else:
                # Can continue moving through this hex
                actual_end_index = step_index
        
        new_location = planned_path[actual_end_index]
        
        if forced_stop_location:
            print(f"   📍 Forced to stop at path index {actual_end_index} ({new_location}) due to enemy presence")
        else:
            print(f"   📍 Moving to path index {actual_end_index} ({new_location})")
        
        # Execute the movement
        if new_location != current_location:
            total_ships = sum(tf_ships.values())
            
            # Move all ships in the task force together
            success = True
            for ship_type, count in tf_ships.items():
                if count > 0:
                    moved = move_ships_with_task_force_id(game_state, player, current_location, new_location, 
                                                         ship_type, count, tf_number)
                    if not moved:
                        success = False
                        break
            
            if success:
                print(f"   ✅ TF{tf_number} advanced from {current_location} to {new_location}")
                movements_made += 1
                
                # Update movement plan with new position
                game_state.movement_plans[player.player_id][tf_number].update({
                    'current_location': new_location,
                    'path_index': actual_end_index
                })
                
                # Mark if this task force is now in combat position
                if forced_stop_location:
                    game_state.movement_plans[player.player_id][tf_number]['in_combat'] = True
                    game_state.movement_plans[player.player_id][tf_number]['combat_location'] = forced_stop_location
                    
                    # Check if this taskforce contains non-warships that might be pushed out
                    has_unarmed_ships = any(ship_type in [ShipType.SCOUT, ShipType.COLONY_TRANSPORT] 
                                          for ship_type in tf_ships.keys())
                    
                    if has_unarmed_ships:
                        print(f"   ⚠️  TF{tf_number} contains unarmed ships and may be pushed out of combat")
                        print(f"   📋 Preparing potential redirection plan in case of combat retreat")
                        # Mark for potential redirection - actual redirection happens during combat resolution
                        game_state.movement_plans[player.player_id][tf_number]['may_need_redirect'] = True
                        game_state.movement_plans[player.player_id][tf_number]['original_target_before_combat'] = destination
                
                # Check if destination reached
                if new_location == destination:
                    print(f"   🏁 TF{tf_number} has reached destination {destination_name}!")
                    print(f"   🎯 Task force will choose new destination after exploration")
            else:
                print(f"   ❌ Movement failed for TF{tf_number}")
        else:
            print(f"   ⏸️  TF{tf_number} stays at {current_location} (no movement this turn)")
    
    if movements_made == 0:
        print(f"\n{player.name} chooses not to move any ships this turn")
    
    return movements_made > 0


def place_starting_fleet_with_task_force_id(player):
    """Place the player's starting fleet with task force ID tracking."""
    from stellar_conquest.entities.ship import Ship, ShipGroup
    
    entry_hex = player.entry_hex
    
    # Create ship group at entry location
    group = ShipGroup(entry_hex)
    
    # Add all starting ships to TF1 (main fleet)
    for ship_type, count in player.starting_ships.items():
        ship = Ship(ship_type, count, entry_hex, task_force_id=1)  # TF1 is main fleet
        if ship.count > 0:
            group.add_ships(ship)
    
    player.ship_groups.append(group)
    player.has_entered_board = True
    player.update_modified_time()