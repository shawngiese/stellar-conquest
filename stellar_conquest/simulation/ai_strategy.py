"""
AI Strategy Module for Stellar Conquest Simulation

This module handles all AI decision-making including:
- Initial investment strategies  
- Task force creation and deployment
- Exploration target selection
- Production and research decisions
- Colonization strategies
"""

from stellar_conquest.core.enums import Technology, ShipType
from simulation.simulation_utilities import find_nearest_stars, find_nearest_yellow_stars, calculate_hex_distance
from simulation.movement_system import split_ships_into_task_force, generate_route_display


def bonus_ip_spending_phase(game_state, player, turn_number):
    """Handle bonus IP spending at the start of turn 1 for each player."""
    if turn_number != 1:
        return  # Only happens on turn 1
    
    from stellar_conquest.core.enums import Technology
    
    bonus_ip = 25  # Starting bonus IP
    remaining_ip = bonus_ip
    
    print(f"   {player.name} receives {bonus_ip} bonus Industrial Points for initial investment")
    print(f"   Available for: Scouts, Corvettes, and Level 1 Research items")
    
    # Determine player strategy based on name/characteristics
    strategy = determine_player_strategy(player)
    
    if strategy == "expansionist":
        print(f"   🚀 Expansionist Strategy: Investing in Speed 3 research for faster exploration (15 IP)")
        if remaining_ip >= 15:
            # Invest in speed research
            player.research_investments[Technology.SPEED] = 1
            player.current_ship_speed = 3  # Speed 3 technology
            remaining_ip -= 15
            print(f"   🚀 Expansionist Strategy: Maximize exploration capability with speed and scouts")
            
        # Buy scouts with remaining IP
        scouts_to_buy = min(remaining_ip // 2, 4)  # 2 IP per scout, max 4
        if scouts_to_buy > 0:
            add_ships_to_main_fleet(player, ShipType.SCOUT, scouts_to_buy)
            remaining_ip -= scouts_to_buy * 2
            print(f"   ✅ Purchased {scouts_to_buy} scouts ({scouts_to_buy * 2} IP)")
            
        if remaining_ip >= 15:  # If we have enough for speed research
            player.research_investments[Technology.SPEED] = 1
            player.current_ship_speed = 3
            remaining_ip -= 15
            print(f"   ✅ Invested in 1 Speed 3 research (15 IP)")
            print(f"   🚀 Speed upgrade completed! All ships now move 3 hexes per turn")
            
    elif strategy == "warlord":
        print(f"   ⚔️ Warlord Strategy: Build military strength")
        # Buy scouts and corvettes
        scouts_to_buy = min(remaining_ip // 2, 2)  # 2 IP per scout
        corvettes_to_buy = min((remaining_ip - scouts_to_buy * 2) // 5, 4)  # 5 IP per corvette
        
        if scouts_to_buy > 0:
            add_ships_to_main_fleet(player, ShipType.SCOUT, scouts_to_buy)
            remaining_ip -= scouts_to_buy * 2
            print(f"   ✅ Purchased {scouts_to_buy} scouts ({scouts_to_buy * 2} IP)")
            
        if corvettes_to_buy > 0:
            add_ships_to_main_fleet(player, ShipType.CORVETTE, corvettes_to_buy)
            remaining_ip -= corvettes_to_buy * 5
            print(f"   ✅ Purchased {corvettes_to_buy} corvettes ({corvettes_to_buy * 5} IP)")
            
    elif strategy == "technophile":
        print(f"   🔬 Technophile Strategy: Invest in technological advancement")
        # Buy scouts first
        scouts_to_buy = min(remaining_ip // 2, 4)  # 2 IP per scout
        if scouts_to_buy > 0:
            add_ships_to_main_fleet(player, ShipType.SCOUT, scouts_to_buy)
            remaining_ip -= scouts_to_buy * 2
            print(f"   ✅ Purchased {scouts_to_buy} scouts ({scouts_to_buy * 2} IP)")
            
        # Invest in speed research if possible
        if remaining_ip >= 15:
            player.research_investments[Technology.SPEED] = 1
            player.current_ship_speed = 3
            remaining_ip -= 15
            print(f"   ✅ Invested in 1 Speed 3 research (15 IP)")
            print(f"   🚀 Speed upgrade completed! All ships now move 3 hexes per turn")
            
    else:  # balanced strategy
        print(f"   ⚖️ Balanced Strategy: Well-rounded fleet expansion")
        # Buy mix of scouts and corvettes
        scouts_to_buy = min(remaining_ip // 2, 4)  # 2 IP per scout
        corvettes_to_buy = min((remaining_ip - scouts_to_buy * 2) // 5, 2)  # 5 IP per corvette
        
        if scouts_to_buy > 0:
            add_ships_to_main_fleet(player, ShipType.SCOUT, scouts_to_buy)
            remaining_ip -= scouts_to_buy * 2
            print(f"   ✅ Purchased {scouts_to_buy} scouts ({scouts_to_buy * 2} IP)")
            
        if corvettes_to_buy > 0:
            add_ships_to_main_fleet(player, ShipType.CORVETTE, corvettes_to_buy)
            remaining_ip -= corvettes_to_buy * 5
            print(f"   ✅ Purchased {corvettes_to_buy} corvettes ({corvettes_to_buy * 5} IP)")
    
    if remaining_ip > 0:
        print(f"   💰 Unspent IP: {remaining_ip}")
    
    print(f"   📊 Total IP spent: {bonus_ip - remaining_ip}/{bonus_ip}")


def determine_player_strategy(player):
    """Determine player strategy based on name or other characteristics."""
    name_lower = player.name.lower()
    
    if 'nova' in name_lower or 'admiral' in name_lower:
        return "expansionist"
    elif 'vega' in name_lower or 'general' in name_lower:
        return "warlord"
    elif 'luna' in name_lower or 'commander' in name_lower:
        return "technophile"
    else:
        return "balanced"


def add_ships_to_main_fleet(player, ship_type, count):
    """Add purchased ships to the player's main fleet (TF1)."""
    from stellar_conquest.entities.ship import Ship
    
    # Find the main fleet (TF1) at entry hex
    main_group = None
    for group in player.ship_groups:
        for ship in group.ships:
            if ship.task_force_id == 1:  # TF1 is main fleet
                main_group = group
                break
        if main_group:
            break
    
    if main_group:
        # Add ships to existing main fleet
        new_ship = Ship(ship_type, count, main_group.location, task_force_id=1)
        main_group.add_ships(new_ship)
        player.update_modified_time()
        return True
    
    return False


def create_exploration_task_forces(game_state, player, turn_number=2):
    """Split starting fleet into multiple exploration task forces."""
    print(f"   {player.name} organizes multiple task forces for exploration:")
    
    # Get entry hex location
    entry_hex = player.entry_hex
    
    # Find main fleet group (TF1)
    main_group = None
    for group in player.ship_groups:
        for ship in group.ships:
            if ship.task_force_id == 1:  # TF1 is main fleet
                main_group = group
                break
        if main_group:
            break
    
    if not main_group:
        print(f"   ❌ No main fleet found for {player.name}")
        return False
    
    # Get available ships from main fleet
    available_ships = {}
    for ship in main_group.ships:
        if ship.task_force_id == 1:
            available_ships[ship.ship_type] = ship.count
    
    scouts_available = available_ships.get(ShipType.SCOUT, 0)
    corvettes_available = available_ships.get(ShipType.CORVETTE, 0)
    
    # Initialize movement plans for this player
    if not hasattr(game_state, 'movement_plans'):
        game_state.movement_plans = {}
    if player.player_id not in game_state.movement_plans:
        game_state.movement_plans[player.player_id] = {}
    
    # Find exploration targets
    exploration_targets = find_exploration_targets(entry_hex)
    print(f"   Strategic exploration targets identified:")
    for i, (location, distance, name, color) in enumerate(exploration_targets[:3]):
        print(f"     Target {i+1}: {location} - {name} ({color} star, {distance} hexes away)")
    
    task_force_count = 1  # Start at 1 (TF1 is main fleet)
    assigned_targets = set()
    
    # Create exploration task forces
    for i, (target_location, distance, name, color) in enumerate(exploration_targets):
        if scouts_available <= 0:
            break
            
        task_force_count += 1
        
        # Determine task force composition
        if corvettes_available > 0 and i < 3:  # First 3 get corvette escorts
            # Create task force with scout + corvette
            success = create_single_exploration_task_force(
                game_state, player, entry_hex, main_group, task_force_count,
                target_location, name, scout_count=1, corvette_count=1, turn_number=turn_number
            )
            if success:
                scouts_available -= 1
                corvettes_available -= 1
                assigned_targets.add(target_location)
        else:
            # Create scout-only task force
            success = create_single_exploration_task_force(
                game_state, player, entry_hex, main_group, task_force_count,
                target_location, name, scout_count=1, corvette_count=0, turn_number=turn_number
            )
            if success:
                scouts_available -= 1
                assigned_targets.add(target_location)
    
    # Create additional long-range scout task forces if we have more scouts
    if scouts_available > 0:
        distant_targets = find_distant_exploration_targets(entry_hex, assigned_targets)
        print(f"   📡 Expanding search radius - targeting distant stars")
        
        for target_location, distance, name, color in distant_targets:
            if scouts_available <= 0:
                break
                
            task_force_count += 1
            print(f"   Creating TF{task_force_count}: 1 scout → target {name} at {target_location}")
            
            success = create_single_exploration_task_force(
                game_state, player, entry_hex, main_group, task_force_count,
                target_location, name, scout_count=1, corvette_count=0, turn_number=turn_number
            )
            if success:
                scouts_available -= 1
                assigned_targets.add(target_location)
    
    # Create colony transport task forces to nearby yellow stars (for first 4 turns)
    if turn_number <= 4:
        task_force_count = create_colonization_task_forces(game_state, player, entry_hex, main_group, task_force_count, assigned_targets, turn_number)
    
    # Check if all ships have been assigned to task forces
    remaining_ships = main_group.get_ship_counts()
    total_remaining = sum(remaining_ships.values())
    
    if total_remaining > 0:
        print(f"   ⚠️  {total_remaining} ships still unassigned in TF1:")
        for ship_type, count in remaining_ships.items():
            if count > 0:
                print(f"     {count} {ship_type.value.lower()}")
        print(f"   TF1 at {entry_hex} holds remaining ships")
    else:
        print(f"   ✅ All ships successfully deployed - TF1 at {entry_hex} is empty")
    
    return True


def create_single_exploration_task_force(game_state, player, entry_hex, main_group, tf_number, 
                                       target_location, target_name, scout_count, corvette_count, turn_number):
    """Create a single exploration task force."""
    from stellar_conquest.utils.hex_utils import find_path
    
    print(f"   Creating TF{tf_number}: {scout_count} scout", end="")
    if corvette_count > 0:
        print(f" + {corvette_count} corvette", end="")
    print(f" → target {target_name} at {target_location}")
    
    # Create the task force by splitting ships from main fleet
    success = True
    
    if scout_count > 0:
        success &= split_ships_into_task_force(player, entry_hex, ShipType.SCOUT, scout_count, tf_number)
    
    if corvette_count > 0 and success:
        success &= split_ships_into_task_force(player, entry_hex, ShipType.CORVETTE, corvette_count, tf_number)
    
    if success:
        # Calculate route and store movement plan
        planned_path = find_path(entry_hex, target_location)
        if not planned_path:
            planned_path = [entry_hex, target_location]  # Fallback direct path
        
        route_display = generate_route_display(game_state, entry_hex, target_location, player.current_ship_speed, turn_number)
        print(f"     🚌 Planned route: {route_display}")
        print(f"     📋 Task force will start moving in movement phase")
        
        # Store movement plan
        game_state.movement_plans[player.player_id][tf_number] = {
            'planned_path': planned_path,
            'final_destination': target_location,
            'target_name': target_name,
            'path_index': 0,
            'current_location': entry_hex,
            'can_move_this_turn': True
        }
        
        print(f"     ✅ TF{tf_number} created at {entry_hex}, ready to move toward {target_name}")
        return True
    else:
        print(f"     ❌ TF{tf_number} creation failed")
        return False


def find_exploration_targets(entry_hex):
    """Find good exploration targets based on entry hex."""
    return find_nearest_stars(entry_hex, max_distance=8)


def find_distant_exploration_targets(entry_hex, assigned_targets):
    """Find distant exploration targets not already assigned."""
    all_targets = find_nearest_stars(entry_hex, max_distance=15)
    return [target for target in all_targets if target[0] not in assigned_targets]


def create_colonization_task_forces(game_state, player, entry_hex, main_group, starting_tf_count, assigned_targets, turn_number):
    """Create task forces with colony transports to colonize nearby yellow stars."""
    print(f"   {player.name} also sends colony transports for early colonization:")
    print(f"   📊 Starting TF count for colonization: {starting_tf_count}")
    
    # Find nearest yellow stars (can share targets with exploration task forces)
    yellow_stars = find_nearest_yellow_stars(entry_hex, max_distance=8)
    
    if not yellow_stars:
        print(f"   ⚠️  No yellow stars found within range for colonization")
        return starting_tf_count
    
    # Get available ships
    available_ships = main_group.get_ship_counts()
    transports_available = available_ships.get(ShipType.COLONY_TRANSPORT, 0)
    corvettes_available = available_ships.get(ShipType.CORVETTE, 0)
    
    if transports_available == 0:
        print(f"   ⚠️  No colony transports available for colonization")
        return starting_tf_count
    
    # Strategy: Send ALL transports to single best target for maximum early production
    best_target = yellow_stars[0]  # Nearest yellow star
    target_location, distance, name, color = best_target
    
    tf_number = starting_tf_count + 1
    
    print(f"   Creating TF{tf_number}: {transports_available} colony transports + {corvettes_available} corvette escorts → colonize {name} at {target_location}")
    print(f"     🎯 Strategic goal: Establish major colony with ALL transports for maximum early production")
    
    # Create the colonization task force
    success = True
    success &= split_ships_into_task_force(player, entry_hex, ShipType.COLONY_TRANSPORT, transports_available, tf_number)
    if corvettes_available > 0:
        success &= split_ships_into_task_force(player, entry_hex, ShipType.CORVETTE, corvettes_available, tf_number)
    
    if success:
        # Calculate route and store movement plan
        from stellar_conquest.utils.hex_utils import find_path
        planned_path = find_path(entry_hex, target_location)
        if not planned_path:
            planned_path = [entry_hex, target_location]
        
        route_display = generate_route_display(game_state, entry_hex, target_location, player.current_ship_speed, turn_number)
        print(f"     🚌 Planned route: {route_display}")
        print(f"     📋 Major colonization fleet will start moving in movement phase")
        
        # Store movement plan
        game_state.movement_plans[player.player_id][tf_number] = {
            'planned_path': planned_path,
            'final_destination': target_location,
            'target_name': name,
            'path_index': 0,
            'current_location': entry_hex,
            'can_move_this_turn': True
        }
        
        print(f"     ✅ TF{tf_number} created at {entry_hex}, ready to move toward {name}")
        print(f"     📊 Colonization fleet: {transports_available} million colonists ready for deployment")
        
        return tf_number
    else:
        print(f"     ❌ TF{tf_number} creation failed")
        return starting_tf_count