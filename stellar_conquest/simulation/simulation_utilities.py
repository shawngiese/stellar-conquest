"""
Simulation Utilities Module for Stellar Conquest Simulation

This module contains utility functions for:
- Printing and formatting output
- Data management and calculations
- Helper functions used across modules
- Player status and game state queries
"""


def print_turn_header(turn_number, player_name):
    """Print a formatted turn header."""
    print("\n" + "="*70)
    print(f"  TURN {turn_number} - {player_name.upper()}'S TURN")
    print("="*70)


def print_phase_header(turn_number, phase_letter, phase_name):
    """Print a formatted phase header."""
    print(f"\n🔸 PHASE {turn_number}{phase_letter}: {phase_name.upper()}")
    print("-" * 50)


def calculate_hex_distance(hex1, hex2):
    """Calculate distance between two hex coordinates."""
    from stellar_conquest.utils.hex_utils import calculate_hex_distance as calc_dist
    return calc_dist(hex1, hex2)


def show_player_status(player):
    """Display comprehensive player status."""
    print(f"\n📊 {player.name}'s Status:")
    print(f"   Victory Points: {getattr(player, 'victory_points', 0)}")
    
    # Count total ships
    total_ships = 0
    task_forces = {}
    
    for group in player.ship_groups:
        for ship in group.ships:
            total_ships += ship.count
            tf_id = ship.task_force_id
            if tf_id not in task_forces:
                task_forces[tf_id] = []
            task_forces[tf_id].append(f"{ship.count} {ship.ship_type.value.lower()}")
    
    print(f"   Total Ships: {total_ships}")
    print(f"   Ship Speed: {player.current_ship_speed} hexes/turn")
    
    # Show task force breakdown
    if task_forces:
        print(f"   Task Forces:")
        for tf_id in sorted(task_forces.keys()):
            # Get location of this task force
            tf_location = None
            for group in player.ship_groups:
                for ship in group.ships:
                    if ship.task_force_id == tf_id:
                        tf_location = ship.location
                        break
                if tf_location:
                    break
            
            ships_desc = ", ".join(task_forces[tf_id])
            print(f"     TF{tf_id} at {tf_location}: {ships_desc}")
    
    # Show colonies
    colony_count = len(player.colonies) if hasattr(player, 'colonies') else 0
    if colony_count > 0:
        print(f"   Colonies: {colony_count}")
    else:
        print(f"   Colonies: None")
    
    # Show strategy
    strategy = analyze_player_strategy(player)
    print(f"   Strategy: {strategy}")


def analyze_player_strategy(player):
    """Analyze and describe the player's current strategy."""
    # Count ship types
    scouts = 0
    corvettes = 0
    transports = 0
    
    for group in player.ship_groups:
        for ship in group.ships:
            if ship.ship_type.value == 'SCOUT':
                scouts += ship.count
            elif ship.ship_type.value == 'CORVETTE':
                corvettes += ship.count
            elif ship.ship_type.value == 'COLONY_TRANSPORT':
                transports += ship.count
    
    total_ships = scouts + corvettes + transports
    
    if total_ships == 0:
        return "🤔 No ships deployed"
    
    # Determine strategy based on ship composition and deployment
    scout_ratio = scouts / total_ships
    corvette_ratio = corvettes / total_ships
    transport_ratio = transports / total_ships
    
    # Count task forces (exploration aggressiveness)
    task_force_count = len(set(ship.task_force_id for group in player.ship_groups for ship in group.ships))
    
    if task_force_count >= 6:
        return "🚀 Aggressive Scout Swarm - Multiple single-scout task forces for maximum exploration coverage"
    elif corvette_ratio > 0.3:
        return "⚔️ Military Focus - Heavy corvette deployment for combat readiness"
    elif transport_ratio > 0.7:
        return "🏰 Colonization Rush - Mass transport deployment for rapid settlement"
    elif scout_ratio > 0.4:
        return "🔍 Exploration Specialist - Scout-heavy approach for intelligence gathering"
    else:
        return "⚖️ Balanced Approach - Mixed fleet composition for flexibility"


def find_nearest_stars(player_location, max_distance=4):
    """Find nearest stars within a specified distance."""
    # This would normally interface with the galaxy map
    # For simulation purposes, returning mock data
    return [
        ("D4", 3, "Indi", "orange"),
        ("G5", 4, "Canis", "yellow"),
        ("H2", 4, "Ophiuchi", "red")
    ]


def find_nearest_yellow_stars(player_location, max_distance=8):
    """Find nearest yellow stars (preferred for colonization)."""
    from stellar_conquest.data.star_data import STAR_DATA
    
    yellow_stars = []
    
    for star_location, star_data in STAR_DATA.items():
        if star_data.get('color') == 'yellow':
            distance = calculate_hex_distance(player_location, star_location)
            if distance <= max_distance:
                yellow_stars.append((star_location, distance, star_data['starname'], star_data['color']))
    
    yellow_stars.sort(key=lambda x: x[1])
    return yellow_stars


def add_command_post(game_state, player_id, location):
    """Add a command post at a location."""
    if not hasattr(game_state, 'command_posts'):
        game_state.command_posts = {}
    if player_id not in game_state.command_posts:
        game_state.command_posts[player_id] = []
    
    if location not in game_state.command_posts[player_id]:
        game_state.command_posts[player_id].append(location)


def has_command_post(game_state, player_id, location):
    """Check if a player has a command post at a location."""
    if not hasattr(game_state, 'command_posts'):
        return False
    if player_id not in game_state.command_posts:
        return False
    return location in game_state.command_posts[player_id]


def auto_explore_yellow_star(game_state, location, star_name, player_id):
    """Automatically explore a yellow star and return planet data."""
    # Mock exploration for simulation - would normally draw star cards
    planet_types = ["terran", "sub_terran", "minimal_terran"]
    import random
    
    # Generate 1-3 planets for yellow stars
    num_planets = random.randint(1, 3)
    planets = []
    
    for i in range(num_planets):
        planet_type = random.choice(planet_types)
        # Terran planets are more common around yellow stars
        if random.random() < 0.6:  # 60% chance for terran
            planet_type = "terran"
        
        capacity = 20 if planet_type == "terran" else 10  # Basic capacity
        planets.append({
            'type': planet_type,
            'capacity': capacity,
            'mineral_rich': random.random() < 0.2  # 20% chance
        })
    
    return {
        'planets': planets,
        'explored_by': player_id,
        'star_name': star_name
    }


def choose_new_destination(game_state, player, tf_number, current_location):
    """Choose a new destination for a task force that has reached its target."""
    # Simple strategy: find nearest unexplored star
    nearest_stars = find_nearest_stars(current_location, max_distance=8)
    
    if nearest_stars:
        target_location, distance, name, color = nearest_stars[0]
        print(f"   🎯 New destination selected: {name} at {target_location}")
        return target_location, name
    
    # If no stars found, stay put
    print(f"   ⏸️  No suitable destinations found - TF{tf_number} will hold position")
    return current_location, "Hold Position"


def remove_transport_from_task_force(task_force_group, count):
    """Remove colony transports from a task force (they disappear after debarking)."""
    from stellar_conquest.core.enums import ShipType
    
    removed = 0
    ships_to_remove = []
    
    for ship in task_force_group.ships:
        if ship.ship_type == ShipType.COLONY_TRANSPORT and removed < count:
            to_remove = min(ship.count, count - removed)
            ship.count -= to_remove
            removed += to_remove
            
            if ship.count == 0:
                ships_to_remove.append(ship)
    
    for ship in ships_to_remove:
        task_force_group.ships.remove(ship)
    
    return removed