#!/usr/bin/env python3
"""
Stellar Conquest Auto Demo with Enhanced Map Generation using mapgenerator.py approach.
Creates high-quality matplotlib-based maps showing task force movements.
"""

import sys
import os
import time
import random
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environments

# Fix Windows console encoding for Unicode/emoji support
if sys.platform == 'win32':
    try:
        # Try to set UTF-8 encoding for stdout/stderr
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        # If that fails, just replace problematic characters
        pass

# Import demo components
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'stellar_conquest'))
from stellar_conquest.core.enums import PlayStyle, GamePhase, ShipType, Technology, ColonyStatus
from stellar_conquest.core.constants import FIXED_STAR_LOCATIONS, STARTING_FLEET, IP_PER_POPULATION, IP_PER_FACTORY, MINERAL_RICH_MULTIPLIER, TERRAN_GROWTH_RATE, SUB_TERRAN_GROWTH_RATE, SHIP_COSTS, TECHNOLOGY_COSTS
from stellar_conquest.game.game_state import GameState, GameSettings, create_game
from stellar_conquest.actions.movement import MovementAction, MovementOrder
from stellar_conquest.actions.exploration import ExplorationAction, ExplorationOrder

# Import enhanced map generator
from stellar_conquest.utils.enhanced_map_generator import EnhancedMapGenerator

# Import enemy intelligence system
from stellar_conquest.utils.enemy_intelligence import intelligence_system, ActivityType

def detect_and_log_enemies(game_state, current_player, location, turn_number):
    """Detect and log enemy ships and colonies at a location."""
    enemies_detected = []
    
    # Initialize intelligence logging for current player (only if needed)
    if current_player.name not in intelligence_system.enemy_activity_logs:
        intelligence_system.initialize_player_logs(current_player.name)
    
    # Check for enemy ships at this location
    for other_player in game_state.players:
        if other_player.player_id == current_player.player_id:
            continue
            
        # Check for enemy ship groups at this location
        enemy_ships = []
        for ship_group in other_player.ship_groups:
            if ship_group.location == location:
                ship_counts = ship_group.get_ship_counts()
                ship_details = []
                total_ships = 0
                for ship_type, count in ship_counts.items():
                    if count > 0:
                        ship_details.append(f"{count} {ship_type.value}")
                        total_ships += count
                
                if ship_details:
                    enemy_ships.extend(ship_details)
                    
                    # Log enemy ship discovery
                    ship_desc = ", ".join(ship_details)
                    threat_level = 2 if total_ships <= 3 else 3 if total_ships <= 10 else 4
                    
                    intelligence_system.log_enemy_activity(
                        current_player.name, turn_number, location,
                        ActivityType.ENEMY_SHIPS_DISCOVERED, other_player.name,
                        f"Enemy fleet discovered: {ship_desc}",
                        threat_level
                    )
                    
                    enemies_detected.append(f"🚢 {other_player.name}: {ship_desc}")
        
        # Check for enemy colonies at this location
        for colony in other_player.colonies:
            if colony.location == location:
                # Log enemy colony discovery
                colony_desc = f"{colony.population}M population"
                if colony.factories > 0:
                    colony_desc += f", {colony.factories} factories"
                if colony.missile_bases > 0:
                    colony_desc += f", {colony.missile_bases} missile bases"
                    
                threat_level = 2 if colony.population <= 10 else 3 if colony.population <= 30 else 5
                if colony.missile_bases > 0:
                    threat_level += 1
                    
                intelligence_system.log_enemy_activity(
                    current_player.name, turn_number, location,
                    ActivityType.ENEMY_COLONY_DISCOVERED, other_player.name,
                    f"Enemy colony discovered: {colony_desc}",
                    threat_level
                )
                
                enemies_detected.append(f"🏛️ {other_player.name}: Colony with {colony_desc}")
    
    # Display enemy detection results
    if enemies_detected:
        print(f"      🔍 Enemy Activity Detected:")
        for enemy in enemies_detected:
            print(f"         {enemy}")
        print(f"      📝 Intelligence logged for strategic planning")
    else:
        print(f"      🔍 No enemy activity detected at {location}")

def monitor_star_system_traffic(game_state, colony_owner, location, turn_number):
    """Monitor and log enemy ships passing through player-controlled star systems."""
    # Check if colony owner has a colony at this location
    has_colony = any(colony.location == location for colony in colony_owner.colonies)
    if not has_colony:
        return
        
    if colony_owner.name not in intelligence_system.enemy_activity_logs:
        intelligence_system.initialize_player_logs(colony_owner.name)
    
    # Check for enemy ships at this star system
    for other_player in game_state.players:
        if other_player.player_id == colony_owner.player_id:
            continue
            
        for ship_group in other_player.ship_groups:
            if ship_group.location == location:
                ship_counts = ship_group.get_ship_counts()
                ship_types = []
                total_ships = 0
                
                for ship_type, count in ship_counts.items():
                    if count > 0:
                        ship_types.append(ship_type.value)
                        total_ships += count
                
                if ship_types:
                    # Determine if this is hostile activity
                    hostile = any(ship_type in ['corvette', 'fighter', 'death_star'] 
                                for ship_type in ship_types)
                    
                    intelligence_system.log_star_system_monitoring(
                        colony_owner.name, turn_number, location, other_player.name,
                        ship_types, total_ships, hostile_action=hostile
                    )
                    
                    action_desc = " (HOSTILE FLEET)" if hostile else " (peaceful passage)"
                    print(f"      🛡️ Star System Security: {other_player.name} fleet detected{action_desc}")

def print_turn_header(turn_number, player_name):
    print("\n" + "="*70)
    print(f"  TURN {turn_number} - {player_name.upper()}'S TURN")
    print("="*70)

def bonus_ip_spending_phase(game_state, player, turn_number):
    """Handle bonus IP spending at the start of turn 1 for each player."""
    if turn_number != 1:
        return  # Only happens on turn 1
    
    from stellar_conquest.core.enums import Technology
    
    print("\n🔸 PHASE 0: BONUS IP SPENDING")
    print("-" * 50)
    
    bonus_ip = 25
    print(f"   {player.name} receives {bonus_ip} bonus Industrial Points for initial investment")
    print(f"   Available for: Scouts, Corvettes, and Level 1 Research items")
    
    # Define costs for purchasable items
    single_scout_cost = 1  # single scouts cost 1 IP
    scout_pair_cost = 5  # pairs of scouts cost 5 IP total
    corvette_cost = 5  # corvettes cost 5 IP  
    speed_3_research_cost = TECHNOLOGY_COSTS[Technology.SPEED_3_HEX]  # Speed 3 technology costs 15 IP
    
    def calculate_scout_cost(num_scouts):
        """Calculate optimal cost for purchasing scouts (pairs cost 5, singles cost 1)."""
        pairs = num_scouts // 2
        singles = num_scouts % 2
        return pairs * scout_pair_cost + singles * single_scout_cost
    
    # Strategic spending based on play style
    scouts_to_buy = 0
    corvettes_to_buy = 0
    research_items = 0
    remaining_ip = bonus_ip
    
    # Play style-specific spending strategies
    if player.play_style.value == "expansionist":
        # Expansionist: Prioritize speed research, then scouts for maximum exploration
        # First invest in speed 3 research for faster exploration
        if player.can_research_technology(Technology.SPEED_3_HEX) and remaining_ip >= speed_3_research_cost:
            research_items = 1  # Speed 3 research
            remaining_ip -= speed_3_research_cost
            print(f"   🚀 Expansionist Strategy: Investing in Speed 3 research for faster exploration ({speed_3_research_cost} IP)")
        elif Technology.SPEED_3_HEX in player.completed_technologies:
            print(f"   🚀 Expansionist Strategy: Already has Speed 3 research, focusing on scouts")
        
        # Then buy scouts with remaining IP - optimize for pairs
        scouts_to_buy = 0
        for potential_scouts in range(10, 0, -1):  # Try up to 10 scouts, working backwards
            scout_cost = calculate_scout_cost(potential_scouts)
            if scout_cost <= remaining_ip:
                scouts_to_buy = potential_scouts
                remaining_ip -= scout_cost
                break
        
        # Use any remaining IP for corvettes
        if remaining_ip >= corvette_cost:
            corvettes_to_buy = remaining_ip // corvette_cost
            remaining_ip -= corvettes_to_buy * corvette_cost
        
        print(f"   🚀 Expansionist Strategy: Maximize exploration capability with speed and scouts")
        
    elif player.play_style.value == "warlord":
        # Warlord: Focus on corvettes for military power
        corvettes_to_buy = min(remaining_ip // corvette_cost, 4)  # Buy up to 4 corvettes
        remaining_ip -= corvettes_to_buy * corvette_cost
        
        # Fill remaining with scouts - optimize for pairs
        scouts_to_buy = 0
        for potential_scouts in range(8, 0, -1):  # Try up to 8 scouts
            scout_cost = calculate_scout_cost(potential_scouts)
            if scout_cost <= remaining_ip:
                scouts_to_buy = potential_scouts
                remaining_ip -= scout_cost
                break
        
        print(f"   ⚔️ Warlord Strategy: Build military strength")
        
    elif player.play_style.value == "technophile":
        # Technophile: Invest in research first - focus on Speed 3 as primary research
        if player.can_research_technology(Technology.SPEED_3_HEX) and remaining_ip >= speed_3_research_cost:
            research_items = 1  # Speed 3 research 
            remaining_ip -= speed_3_research_cost
        elif Technology.SPEED_3_HEX in player.completed_technologies:
            print(f"   🔬 Technophile Strategy: Already has Speed 3 research, focusing on other techs")
        
        # Use remaining for scouts - optimize for pairs
        scouts_to_buy = 0
        for potential_scouts in range(8, 0, -1):  # Try up to 8 scouts
            scout_cost = calculate_scout_cost(potential_scouts)
            if scout_cost <= remaining_ip:
                scouts_to_buy = potential_scouts
                remaining_ip -= scout_cost
                break
        
        print(f"   🔬 Technophile Strategy: Invest in technological advancement")
        
    else:  # balanced
        # Balanced: Mix of scouts and corvettes - optimize scout pairs
        scouts_to_buy = 4  # Try for 4 scouts first
        scout_cost = calculate_scout_cost(scouts_to_buy)
        remaining_ip -= scout_cost
        
        corvettes_to_buy = min(remaining_ip // corvette_cost, 2)  # 10 IP
        remaining_ip -= corvettes_to_buy * corvette_cost
        
        print(f"   ⚖️ Balanced Strategy: Well-rounded fleet expansion")
    
    # Apply purchases to player's fleet
    if scouts_to_buy > 0:
        add_ships_to_main_fleet(player, ShipType.SCOUT, scouts_to_buy)
        scout_purchase_cost = calculate_scout_cost(scouts_to_buy)
        print(f"   ✅ Purchased {scouts_to_buy} scout{'s' if scouts_to_buy > 1 else ''} ({scout_purchase_cost} IP)")
    
    if corvettes_to_buy > 0:
        add_ships_to_main_fleet(player, ShipType.CORVETTE, corvettes_to_buy)
        print(f"   ✅ Purchased {corvettes_to_buy} corvette{'s' if corvettes_to_buy > 1 else ''} ({corvettes_to_buy * corvette_cost} IP)")
    
    if research_items > 0:
        print(f"   ✅ Invested in {research_items} Speed 3 research ({speed_3_research_cost} IP)")
        # Apply speed research immediately using proper technology system
        if research_items >= 1:
            completed = player.add_research_investment(Technology.SPEED_3_HEX, speed_3_research_cost)
            if completed:
                new_speed = player.current_ship_speed
                print(f"   🚀 Speed upgrade completed! All ships now move {new_speed} hexes per turn")
            else:
                print(f"   🔬 Speed 3 research in progress (needs more IP to complete)")
    
    if remaining_ip > 0:
        print(f"   💰 Unspent IP: {remaining_ip}")
    
    print(f"   📊 Total IP spent: {bonus_ip - remaining_ip}/{bonus_ip}")

def add_ships_to_main_fleet(player, ship_type, count):
    """Add purchased ships to the player's main fleet (TF1)."""
    from stellar_conquest.entities.ship import Ship
    
    # Find the main fleet (TF1) at entry hex
    main_group = None
    for group in player.ship_groups:
        if group.location == player.entry_hex:
            main_group = group
            break
    
    if not main_group:
        print(f"   ⚠️  No main fleet found at {player.entry_hex}")
        return
    
    # Check if ship type already exists in the fleet
    existing_ship = None
    for ship in main_group.ships:
        if ship.ship_type == ship_type and ship.task_force_id == 1:
            existing_ship = ship
            break
    
    if existing_ship:
        # Add to existing ship count
        existing_ship.count += count
    else:
        # Create new ship entry
        new_ship = Ship(
            ship_type=ship_type,
            count=count,
            location=player.entry_hex,
            player_id=player.player_id,
            game_id=player.game_id,
            task_force_id=1
        )
        main_group.add_ships(new_ship)

def print_phase_header(turn_number, phase_letter, phase_name):
    print(f"\n🔸 PHASE {turn_number}{phase_letter}: {phase_name}")
    print("-" * 50)

def split_ships_into_task_force(player, location, ship_type, count, task_force_id):
    """Split ships from existing group into a new task force (same location)."""
    from stellar_conquest.entities.ship import Ship, ShipGroup
    
    # Find the main group at this location that has enough ships of the required type
    main_group = None
    for group in player.ship_groups:
        if group.location == location:
            # Check if this group has enough ships of the required type (total)
            ship_counts = group.get_ship_counts()
            if ship_counts.get(ship_type, 0) >= count:
                main_group = group
                break
    
    if not main_group:
        return False
    
    # Find ships to split from - may need multiple ships to reach desired count
    available_ships = []
    total_available = 0
    for ship in main_group.ships:
        if ship.ship_type == ship_type:
            available_ships.append(ship)
            total_available += ship.count
    
    if total_available < count:
        return False
    
    # Split the ships - collect from multiple ship entities if needed
    remaining_to_split = count
    ships_to_modify = []
    
    for ship in available_ships:
        if remaining_to_split <= 0:
            break
        
        take_from_this_ship = min(ship.count, remaining_to_split)
        ships_to_modify.append((ship, take_from_this_ship))
        remaining_to_split -= take_from_this_ship
    
    # Apply the splits
    for ship, take_count in ships_to_modify:
        ship.count -= take_count
    
    # Create new ship with the new task force ID
    new_ship = Ship(
        ship_type=ship_type,
        count=count,
        location=location,
        player_id=player.player_id,
        game_id=player.game_id,
        task_force_id=task_force_id
    )
    
    # Add to the same group (they'll stay separate due to different task force IDs)
    main_group.add_ships(new_ship)
    
    # Remove ships that have no count left
    ships_to_remove = []
    for ship, take_count in ships_to_modify:
        if ship.count <= 0:
            ships_to_remove.append(ship)
    
    for ship in ships_to_remove:
        main_group.ships.remove(ship)
    
    return True

def remove_ships_from_task_force(player, location, ship_type, count, task_force_id):
    """Remove ships from a specific task force at a location."""
    removed_count = 0
    groups_to_remove = []
    
    # Find all ship groups at this location
    for group in player.ship_groups[:]:  # Use slice to avoid modification during iteration
        if group.location == location:
            # Find ships in this group with matching task force ID and ship type
            for ship in group.ships[:]:  # Use slice to avoid modification during iteration
                if ship.ship_type == ship_type and ship.task_force_id == task_force_id:
                    # Remove the requested count (or as many as available)
                    can_remove = min(ship.count, count - removed_count)
                    ship.count -= can_remove
                    removed_count += can_remove
                    
                    # Remove ship if count reaches zero
                    if ship.count <= 0:
                        group.ships.remove(ship)
                    
                    # Stop if we've removed enough ships
                    if removed_count >= count:
                        break
            
            # Remove group if it has no ships left
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
    if removed <= 0:
        return False
    
    # Create new ship with task force ID
    ship = Ship(
        ship_type=ship_type,
        count=removed,
        location=to_location,
        player_id=player.player_id,
        game_id=player.game_id,
        task_force_id=task_force_id
    )
    
    # Find existing ship group with matching task force ID at destination
    matching_group = None
    for group in player.ship_groups:
        if group.location == to_location:
            # Check if any ship in this group has the same task force ID
            for existing_ship in group.ships:
                if existing_ship.task_force_id == task_force_id:
                    matching_group = group
                    break
            if matching_group:
                break
    
    # If no matching group found, create a new one
    if not matching_group:
        matching_group = ShipGroup(to_location, player.player_id)
        player.ship_groups.append(matching_group)
    
    # Add ship to the matching group (will only merge with same task force ID)
    matching_group.add_ships(ship)
    player.update_modified_time()
    
    return True

def show_intelligence_reports(player):
    """Display enemy intelligence reports for a player."""
    # Only initialize if player logs don't exist yet (don't clear existing data)
    if player.name not in intelligence_system.enemy_activity_logs:
        intelligence_system.initialize_player_logs(player.name)
    
    print(f"\n   🕵️ Enemy Intelligence Report:")
    
    # Debug: Check what data exists
    if hasattr(intelligence_system, 'enemy_activity_logs') and player.name in intelligence_system.enemy_activity_logs:
        entry_count = len(intelligence_system.enemy_activity_logs[player.name])
    
    # Get recent enemy activity report
    activity_report = intelligence_system.get_enemy_activity_report(player.name, recent_turns=5)
    # Always show the activity report, even if no activity
    if "No activity recorded" in activity_report:
        print(f"     📊 Enemy Activity: No intelligence data collected yet")
    elif "No enemy activity detected" in activity_report:
        print(f"     📊 Enemy Activity: No enemy encounters recorded")
    elif "No recent enemy activity" in activity_report:
        print(f"     📊 Enemy Activity: No recent enemy encounters")
    else:
        print(f"     {activity_report}")
    
    # Get star system monitoring report  
    monitoring_report = intelligence_system.get_star_monitoring_report(player.name, recent_turns=5)
    # Always show the monitoring report, even if no activity
    if "No monitoring data" in monitoring_report:
        print(f"     🛡️ System Security: No monitoring systems active")
    elif "No enemy incursions" in monitoring_report:
        print(f"     🛡️ System Security: No enemy incursions detected")
    elif "No recent incursions" in monitoring_report:
        print(f"     🛡️ System Security: No recent enemy activity")
    else:
        print(f"     {monitoring_report}")
    
    # Get strategic recommendations
    strategic_report = intelligence_system.get_strategic_recommendations(player.name)
    if "No data available" not in strategic_report and "Galaxy appears peaceful" not in strategic_report:
        print(f"     🎯 Strategic Recommendations: {strategic_report}")
    else:
        print(f"     🎯 Strategic Assessment: Galaxy appears peaceful - continue expansion")
    
    # Check for defensive responses to enemy activity near colonies
    evaluate_colony_defense_responses(player)


def evaluate_colony_defense_responses(player):
    """Evaluate if player should take defensive action based on intelligence reports."""
    if player.name not in intelligence_system.enemy_activity_logs:
        return
    
    # Get recent enemy activities
    activities = intelligence_system.enemy_activity_logs[player.name]
    if not activities:
        return
    
    # Get the most recent turn number
    latest_turn = max(activity.turn for activity in activities) if activities else 1
    recent_activities = [activity for activity in activities if activity.turn >= max(1, latest_turn - 3)]  # Last 3 turns
    
    # Find enemy activities at locations where player has colonies
    colony_locations = {colony.location for colony in player.colonies}
    threatened_locations = {}
    
    for activity in recent_activities:
        location = activity.location
        if location in colony_locations:
            # Enemy activity detected at a colony location
            activity_type = activity.activity_type.value if hasattr(activity.activity_type, 'value') else str(activity.activity_type)
            enemy_player = activity.enemy_player
            threat_level = activity.threat_level
            
            if activity_type in ['enemy_ships_discovered', 'enemy_ships_detected']:
                if location not in threatened_locations:
                    threatened_locations[location] = []
                threatened_locations[location].append({
                    'enemy': enemy_player,
                    'threat_level': threat_level,
                    'activity': activity.details,
                    'turn': activity.turn
                })
    
    # Process each threatened location
    for location, threats in threatened_locations.items():
        max_threat_level = max(threat['threat_level'] for threat in threats)
        colonies_at_location = [colony for colony in player.colonies if colony.location == location]
        
        if colonies_at_location:
            consider_defensive_response(player, location, colonies_at_location, max_threat_level, threats)


def consider_defensive_response(player, location, colonies, max_threat_level, threats):
    """Consider defensive response for a threatened colony location."""
    # Calculate strategic value of colonies at this location
    total_current_ip = sum(colony.calculate_industrial_points() for colony in colonies)
    total_potential_ip = sum(colony.planet.max_population for colony in colonies)
    total_vp = sum(colony.planet.victory_points for colony in colonies)
    has_mineral_rich = any(colony.planet.is_mineral_rich for colony in colonies)
    
    # Calculate base defense probability
    base_defense_chance = 0.1  # 10% base chance
    
    # Increase chance based on production value
    if total_current_ip >= 20:
        base_defense_chance += 0.4  # +40% for high production colonies
    elif total_current_ip >= 10:
        base_defense_chance += 0.2  # +20% for medium production
    elif total_current_ip >= 5:
        base_defense_chance += 0.1  # +10% for some production
    
    # Increase chance based on potential value
    if total_potential_ip >= 60:
        base_defense_chance += 0.3  # +30% for high potential
    elif total_potential_ip >= 40:
        base_defense_chance += 0.2  # +20% for medium potential
    
    # Increase chance based on victory points
    if total_vp >= 6:
        base_defense_chance += 0.3  # +30% for high VP colonies
    elif total_vp >= 3:
        base_defense_chance += 0.2  # +20% for medium VP
    
    # Bonus for mineral-rich planets
    if has_mineral_rich:
        base_defense_chance += 0.2  # +20% for mineral rich
    
    # Adjust for threat level
    threat_multiplier = {1: 1.0, 2: 1.2, 3: 1.5, 4: 2.0, 5: 2.5}.get(max_threat_level, 1.0)
    base_defense_chance *= threat_multiplier
    
    # Adjust based on player strategy
    if hasattr(player, 'play_style'):
        if player.play_style.value == 'warlord':
            base_defense_chance *= 1.5  # More likely to defend
        elif player.play_style.value == 'technophile':
            base_defense_chance *= 0.8  # Less likely to spend on defense
        elif player.play_style.value == 'balanced':
            base_defense_chance *= 1.1  # Slightly more likely to defend
    
    # Cap at 80% maximum
    defense_chance = min(base_defense_chance, 0.8)
    
    if random.random() < defense_chance:
        execute_colony_defensive_response(player, location, colonies, max_threat_level, threats)


def execute_colony_defensive_response(player, location, colonies, threat_level, threats):
    """Execute defensive response for threatened colonies."""
    from stellar_conquest.core.enums import Technology
    
    threat_description = ", ".join(set(threat['enemy'] + " forces" for threat in threats))
    
    print(f"     🚨 Defensive Response: {player.name} reacts to {threat_description} near {location}")
    
    # Determine available response options
    response_options = []
    
    # Option 1: Send warship protection
    available_warships = get_available_warships_for_defense(player, location)
    if available_warships:
        response_options.append(("send_warship", 0.4))
    
    # Option 2: Build missile bases (if technology available)
    if Technology.MISSILE_BASE in player.completed_technologies:
        can_build_missiles = any(colony.missile_bases < 3 for colony in colonies)
        if can_build_missiles:
            response_options.append(("build_missiles", 0.4))
    
    # Option 3: Build planet shield (if technology available and high value target)
    if Technology.PLANET_SHIELD in player.completed_technologies:
        high_value_colony = any(colony.calculate_industrial_points() >= 15 for colony in colonies)
        no_shield_yet = any(not colony.has_planet_shield for colony in colonies)
        if high_value_colony and no_shield_yet:
            response_options.append(("build_shield", 0.3))
    
    # Option 4: Do nothing (always available)
    response_options.append(("do_nothing", 0.2))
    
    # Weight responses by threat level
    if threat_level >= 4:  # High threat (death stars, fighters)
        weighted_options = []
        for option, base_weight in response_options:
            if option == "build_shield":
                weighted_options.append((option, base_weight * 2.0))
            elif option == "send_warship":
                weighted_options.append((option, base_weight * 1.5))
            else:
                weighted_options.append((option, base_weight))
        response_options = weighted_options
    
    # Choose response based on weights
    total_weight = sum(weight for _, weight in response_options)
    if total_weight == 0:
        return
    
    choice = random.uniform(0, total_weight)
    current_weight = 0
    chosen_response = "do_nothing"
    
    for option, weight in response_options:
        current_weight += weight
        if choice <= current_weight:
            chosen_response = option
            break
    
    # Execute the chosen response
    if chosen_response == "send_warship":
        execute_warship_deployment(player, location, available_warships)
    elif chosen_response == "build_missiles":
        execute_missile_base_construction(player, location, colonies)
    elif chosen_response == "build_shield":
        execute_planet_shield_construction(player, location, colonies)
    else:
        print(f"       🤷 {player.name} decides the threat is manageable - no defensive action taken")


def get_available_warships_for_defense(player, threatened_location):
    """Get warships that could be sent to defend a location."""
    available_warships = []
    
    for group in player.ship_groups:
        if group.location == threatened_location:
            continue  # Skip ships already at the location
        
        # Look for warships
        warships = []
        for ship in group.ships:
            if ship.ship_type.value in ['corvette', 'fighter', 'death_star'] and ship.count > 0:
                warships.append((ship.ship_type, ship.count))
        
        if warships:
            available_warships.append((group.location, warships))
    
    return available_warships


def execute_warship_deployment(player, location, available_warships):
    """Deploy a warship to protect threatened colony."""
    if not available_warships:
        return
    
    # Choose the closest or best available warship
    best_source = available_warships[0][0]  # Simplified - take first available
    best_ships = available_warships[0][1]
    
    # Choose the best ship type available
    ship_priorities = {'death_star': 3, 'fighter': 2, 'corvette': 1}
    best_ship = None
    best_priority = 0
    
    for ship_type, count in best_ships:
        priority = ship_priorities.get(ship_type.value, 0)
        if priority > best_priority and count > 0:
            best_priority = priority
            best_ship = (ship_type, min(1, count))  # Send just 1 ship
    
    if best_ship:
        ship_type, ship_count = best_ship
        print(f"       🛡️ Dispatches {ship_count} {ship_type.value} from {best_source} → {location} for protection")


def execute_missile_base_construction(player, location, colonies):
    """Plan missile base construction for colony defense."""
    target_colony = max(colonies, key=lambda c: c.calculate_industrial_points())
    
    if target_colony.missile_bases < 3:
        bases_needed = min(2, 3 - target_colony.missile_bases)
        cost = bases_needed * 4  # 4 IP per missile base
        
        print(f"       🏗️ Plans to build {bases_needed} missile base{'s' if bases_needed > 1 else ''} at {location} (cost: {cost} IP)")


def execute_planet_shield_construction(player, location, colonies):
    """Plan planet shield construction for ultimate colony defense."""
    target_colony = max(colonies, key=lambda c: c.calculate_industrial_points())
    
    if not target_colony.has_planet_shield:
        cost = 30  # 30 IP for planet shield
        print(f"       🛡️ Plans to build planet shield at {location} (cost: {cost} IP)")


def show_player_status(player):
    """Show comprehensive player status."""
    print(f"\n📊 {player.name}'s Status:")
    print(f"   Victory Points: {player.calculate_victory_points()}")
    print(f"   Total Ships: {player.total_ships}")
    print(f"   Ship Speed: {player.current_ship_speed} hexes/turn")
    
    # Show task forces with TF designations
    if player.ship_groups:
        print(f"   Task Forces:")
        for i, group in enumerate(player.ship_groups, 1):
            ship_counts = group.get_ship_counts()
            ship_details = []
            for ship_type, count in ship_counts.items():
                ship_details.append(f"{count} {ship_type.value}")
            print(f"     TF{i} at {group.location}: {', '.join(ship_details)}")
    else:
        print(f"   Task Forces: None on board")
    
    # Show colonies with detailed planet information
    if player.colonies:
        print(f"   Colonies:")
        total_population = 0
        total_factories = 0
        for colony in player.colonies:
            planet_type = colony.planet.planet_type.value.replace('_', '-').title()
            max_pop = colony.planet.max_population
            mineral_status = " (Mineral Rich)" if colony.planet.is_mineral_rich else ""
            factories_text = f", {colony.factories} factories" if colony.factories > 0 else ""
            
            print(f"     {colony.location}: {colony.population}M pop{factories_text} - {planet_type}{mineral_status} planet (max {max_pop}M)")
            total_population += colony.population
            total_factories += colony.factories
        
        print(f"   📊 Total Colonial Empire: {total_population}M population across {len(player.colonies)} colonies, {total_factories} factories")
    else:
        print(f"   Colonies: None")
    
    # Show enemy intelligence reports
    show_intelligence_reports(player)
    
    # Add strategic analysis
    analyze_player_strategy(player)

def analyze_player_strategy(player):
    """Analyze player strategy and suggest tactical deployments."""
    print(f"   Strategy: 🚀 Aggressive Scout Swarm - Multiple single-scout task forces for maximum exploration coverage")
    
    # Get priority targets from intelligence
    priority_targets = intelligence_system.get_priority_targets(player.name)
    if priority_targets:
        print(f"   🎯 Priority Military Targets: {', '.join(priority_targets[:3])}")  # Show top 3
    
    # Suggest deployment strategy based on intelligence
    activities = intelligence_system.enemy_activity_logs.get(player.name, [])
    if activities:
        recent_threats = [a for a in activities if a.threat_level >= 3]
        if recent_threats:
            print(f"   ⚠️ High-threat locations detected: Consider deploying warships")
        else:
            print(f"   📊 Low-threat environment: Continue exploration focus")

def choose_new_destination(game_state, player, tf_number, current_location):
    """Choose a new destination for a task force that has reached its target."""
    # Get destinations already targeted by other task forces
    other_targets = set()
    if hasattr(game_state, 'movement_plans') and game_state.movement_plans:
        if player.player_id in game_state.movement_plans:
            for other_tf_id, other_plan in game_state.movement_plans[player.player_id].items():
                if other_tf_id != tf_number:  # Don't include this task force's current plan
                    other_destination = other_plan.get('final_destination')
                    if other_destination:
                        other_targets.add(other_destination)
    
    # Find unexplored nearby stars not already targeted
    nearby_unexplored = []
    for star_location, star_data in FIXED_STAR_LOCATIONS.items():
        # Skip if already explored by this player
        if game_state.board.is_system_explored(star_location, player.player_id):
            continue
        # Skip if current location
        if star_location == current_location:
            continue
        # Skip if already targeted by another task force
        if star_location in other_targets:
            continue
        
        distance = calculate_hex_distance(current_location, star_location)
        if distance <= 8:  # Within reasonable exploration range
            nearby_unexplored.append((star_location, distance, star_data['starname'], star_data['color']))
    
    if nearby_unexplored:
        # Sort by distance and pick closest unexplored star
        nearby_unexplored.sort(key=lambda x: x[1])
        new_target, distance, name, color = nearby_unexplored[0]
        
        # Create new path to the target using proper gas cloud pathfinding
        from stellar_conquest.utils.hex_utils import HexGrid
        hex_grid = HexGrid()
        
        try:
            # Use hex grid pathfinding that properly handles gas cloud destinations
            new_path = hex_grid.find_shortest_path(current_location, new_target)
            if not new_path:
                # If pathfinding fails, fall back to direct path
                new_path = [current_location, new_target]
        except Exception as e:
            # If there's any error, fall back to direct path
            print(f"     ⚠️  Pathfinding error: {e}, using direct path")
            new_path = [current_location, new_target]
        
        # Calculate actual movement time considering gas cloud rules
        from stellar_conquest.utils.hex_utils import calculate_movement_turns
        actual_turns = calculate_movement_turns(new_path, player.current_ship_speed)
        
        # Update the movement plan with new destination
        # Ensure movement plan exists for this task force
        if player.player_id not in game_state.movement_plans:
            game_state.movement_plans[player.player_id] = {}
        if tf_number not in game_state.movement_plans[player.player_id]:
            game_state.movement_plans[player.player_id][tf_number] = {}
            
        game_state.movement_plans[player.player_id][tf_number].update({
            'planned_path': new_path,
            'path_index': 0,
            'final_destination': new_target,
            'target_name': name
        })
        
        print(f"   🎯 TF{tf_number} selecting new target: {name} at {new_target} ({distance} hexes away, {actual_turns} turns)")
        if other_targets:
            avoided_list = ', '.join(sorted(other_targets))
            print(f"     💭 Avoided targeting systems already assigned: {avoided_list}")
    else:
        reason = "no more targets in range"
        if other_targets:
            reason += f" (avoided {len(other_targets)} already-targeted systems)"
        print(f"   🏁 TF{tf_number} has {reason}, continuing patrol")

def calculate_hex_distance(hex1, hex2):
    """Calculate distance between two hex coordinates."""
    from stellar_conquest.utils.hex_utils import calculate_hex_distance as calc_dist
    return calc_dist(hex1, hex2)

def analyze_player_strategy(player):
    """Analyze and explain player's current strategic approach."""
    print(f"   Strategy: ", end="")
    
    # Count total task forces and analyze composition
    num_task_forces = len(player.ship_groups)
    scattered_tfs = 0
    single_scout_tfs = 0
    
    for group in player.ship_groups:
        if group.location != player.entry_hex:
            scattered_tfs += 1
        
        # Check if this is a single-scout task force
        ship_counts = group.get_ship_counts()
        if ship_counts.get(ShipType.SCOUT, 0) == 1 and ship_counts.get(ShipType.CORVETTE, 0) <= 1:
            total_ships = sum(ship_counts.values())
            if total_ships <= 2:  # Single scout or scout + corvette
                single_scout_tfs += 1
    
    # Count corvette-only task forces
    corvette_only_tfs = 0
    for group in player.ship_groups:
        ship_counts = group.get_ship_counts()
        if (ship_counts.get(ShipType.CORVETTE, 0) >= 1 and 
            ship_counts.get(ShipType.SCOUT, 0) == 0 and
            ship_counts.get(ShipType.COLONY_TRANSPORT, 0) == 0):
            corvette_only_tfs += 1
    
    # Determine strategy based on behavior and play style
    if player.play_style.value == "expansionist" and corvette_only_tfs >= 1:
        print("⚔️ Expansionist Corsair Strategy - Corvette task forces for aggressive territorial expansion")
    elif player.play_style.value == "warlord" and corvette_only_tfs >= 1:
        print("🗡️ Warlord Raider Strategy - Corvette penetration missions for disruption and conquest")
    elif single_scout_tfs >= 3:
        print("🚀 Aggressive Scout Swarm - Multiple single-scout task forces for maximum exploration coverage")
    elif num_task_forces >= 4 and scattered_tfs >= 3:
        print("🔍 Wide Exploration - Multiple task forces spreading across the galaxy to discover star systems")
    elif scattered_tfs >= 1 and num_task_forces >= 2:
        print("🎯 Focused Exploration - Limited task forces targeting specific high-value star systems")
    elif num_task_forces == 1:
        print("🏰 Conservative Consolidation - Keeping main fleet together, possibly preparing for future expansion")
    else:
        print("📋 Early Setup - Organizing initial exploration strategy")

def find_nearest_stars(player_location, max_distance=4):
    """Find nearest unexplored star systems."""
    from stellar_conquest.utils.hex_utils import calculate_hex_distance
    
    nearby_stars = []
    for star_location, star_data in FIXED_STAR_LOCATIONS.items():
        distance = calculate_hex_distance(player_location, star_location)
        if distance <= max_distance:
            nearby_stars.append((star_location, distance, star_data['starname'], star_data['color']))
    
    nearby_stars.sort(key=lambda x: x[1])
    return nearby_stars

def find_nearest_yellow_stars(player_location, max_distance=8):
    """Find nearest yellow stars for colonization (always have planets)."""
    from stellar_conquest.utils.hex_utils import calculate_hex_distance
    
    yellow_stars = []
    for star_location, star_data in FIXED_STAR_LOCATIONS.items():
        if star_data['color'] == 'yellow':  # Yellow stars always have planets
            distance = calculate_hex_distance(player_location, star_location)
            if distance <= max_distance:
                yellow_stars.append((star_location, distance, star_data['starname'], star_data['color']))
    
    yellow_stars.sort(key=lambda x: x[1])
    return yellow_stars

def check_enemy_ships_at_location(game_state, location, current_player):
    """Check if there are enemy ships at a given location."""
    enemy_ships = {}
    
    for player in game_state.players:
        if player.player_id == current_player.player_id:
            continue  # Skip current player
            
        # Check all ship groups for this enemy player
        for group in player.ship_groups:
            for ship in group.ships:
                if ship.location == location:
                    if player.player_id not in enemy_ships:
                        enemy_ships[player.player_id] = {}
                    if ship.ship_type not in enemy_ships[player.player_id]:
                        enemy_ships[player.player_id][ship.ship_type] = 0
                    enemy_ships[player.player_id][ship.ship_type] += ship.count
    
    return enemy_ships

def is_star_hex(game_state, location):
    """Check if a location contains a star (required for combat interaction)."""
    # Check if there's a star system at this location using FIXED_STAR_LOCATIONS
    return location in FIXED_STAR_LOCATIONS

def plan_next_move_toward_target(game_state, current_location, target_location, ship_speed, turn_number=1):
    """Plan next hex to move toward a distant target."""
    from stellar_conquest.utils.hex_utils import calculate_hex_distance
    
    if current_location == target_location:
        return current_location
    
    # Calculate effective movement for this turn
    # Turn 1 has -1 penalty for entering the game map
    effective_speed = ship_speed
    if turn_number == 1:
        effective_speed = max(1, ship_speed - 1)  # -1 penalty, minimum 1 movement
    
    # Try pathfinding with extended range
    max_search_distance = calculate_hex_distance(current_location, target_location) + 5
    path = game_state.board.find_path(current_location, target_location, max_search_distance)
    
    if path and len(path) > 1:
        # Move as far as possible this turn using effective speed
        steps_this_turn = min(effective_speed, len(path) - 1)
        return path[steps_this_turn]
    
    # Enhanced fallback: try multiple movement steps using greedy approach
    current_pos = current_location
    for step in range(effective_speed):
        adjacent = game_state.board.get_adjacent_systems(current_pos)
        if not adjacent:
            break
        
        best_hex = None
        best_distance = float('inf')
        
        for adj_hex in adjacent:
            if not game_state.board.is_gas_cloud(adj_hex):
                distance = calculate_hex_distance(adj_hex, target_location)
                if distance < best_distance:
                    best_distance = distance
                    best_hex = adj_hex
        
        if best_hex and best_hex != current_pos:
            current_pos = best_hex
        else:
            break  # Can't find better position
    
    return current_pos if current_pos != current_location else None

def generate_route_display(game_state, start_hex, destination_hex, ship_speed, turn_number=1):
    """Generate a bus-route style display of the path from start to destination."""
    # Get the complete path using proper hex grid pathfinding
    from stellar_conquest.utils.hex_utils import HexGrid
    hex_grid = HexGrid()
    
    try:
        path = hex_grid.find_shortest_path(start_hex, destination_hex)
    except Exception:
        path = None
    
    if not path or len(path) < 2:
        return f"{start_hex} → {destination_hex}"
    
    # Calculate effective movement for this turn
    # Turn 1 has -1 penalty for entering the game map
    effective_speed = ship_speed
    if turn_number == 1:
        effective_speed = max(1, ship_speed - 1)  # -1 penalty, minimum 1 movement
    
    # Determine which hex will be reached at the end of this turn
    steps_this_turn = min(effective_speed, len(path) - 1)
    current_turn_destination = path[steps_this_turn]
    
    # Create the route display
    route_parts = []
    for i, hex_coord in enumerate(path):
        if hex_coord == current_turn_destination and i > 0:  # Don't bold the starting position
            route_parts.append(f"**{hex_coord}**")  # Bold the current turn destination
        else:
            route_parts.append(hex_coord)
    
    return " → ".join(route_parts)

def send_warlord_scouts_to_enemy_yellow_stars(game_state, player, main_group, turn_number):
    """Send scouts to yellow stars near enemy entry hexes to discover their colonies.

    Yellow stars are guaranteed to have planets, so they're prime colonization targets.
    This reconnaissance helps the Warlord discover enemy colonies for future attacks.
    """
    # Track which enemy yellow stars we've already sent scouts to
    if not hasattr(game_state, 'warlord_recon_targets'):
        game_state.warlord_recon_targets = {}
    if player.player_id not in game_state.warlord_recon_targets:
        game_state.warlord_recon_targets[player.player_id] = set()

    already_scouted = game_state.warlord_recon_targets[player.player_id]

    # Get available scouts
    ship_counts = main_group.get_ship_counts()
    available_scouts = ship_counts.get(ShipType.SCOUT, 0)

    if available_scouts == 0:
        return  # No scouts available

    # Find enemy entry hexes
    enemy_entry_hexes = []
    for other_player in game_state.players:
        if other_player.player_id != player.player_id:
            enemy_entry_hexes.append({
                'location': other_player.entry_hex,
                'player_name': other_player.name
            })

    if not enemy_entry_hexes:
        return

    # Find yellow stars near enemy entry hexes
    enemy_yellow_stars = []
    for enemy_info in enemy_entry_hexes:
        enemy_hex = enemy_info['location']
        enemy_name = enemy_info['player_name']

        # Find all stars within 8 hexes of enemy entry hex
        for star_loc, star_data in FIXED_STAR_LOCATIONS.items():
            if star_data.get('color') == 'yellow':
                distance = calculate_hex_distance(enemy_hex, star_loc)
                if distance <= 8 and star_loc not in already_scouted:
                    # Check if we've already explored this system
                    if hasattr(game_state.board, 'explored_systems'):
                        if star_loc in game_state.board.explored_systems:
                            if player.player_id in game_state.board.explored_systems[star_loc]:
                                continue  # Already explored

                    enemy_yellow_stars.append({
                        'location': star_loc,
                        'name': star_data['starname'],
                        'distance_from_enemy': distance,
                        'distance_from_us': calculate_hex_distance(player.entry_hex, star_loc),
                        'enemy_name': enemy_name
                    })

    if not enemy_yellow_stars:
        return  # No new targets

    # Sort by distance from us (closest first)
    enemy_yellow_stars.sort(key=lambda x: x['distance_from_us'])

    # Send scouts to enemy yellow stars
    scouts_sent = 0
    max_recon_scouts = min(2, available_scouts)  # Send up to 2 scouts for recon per turn

    print(f"   🔍 WARLORD RECONNAISSANCE: Scouting enemy yellow stars")

    for target_star in enemy_yellow_stars[:max_recon_scouts]:
        if scouts_sent >= max_recon_scouts:
            break

        location = target_star['location']
        star_name = target_star['name']
        enemy_name = target_star['enemy_name']

        # Find next TF number
        tf_number = 2
        if hasattr(game_state, 'movement_plans') and player.player_id in game_state.movement_plans:
            existing_tfs = set(game_state.movement_plans[player.player_id].keys())
            while tf_number in existing_tfs:
                tf_number += 1

        # Get path
        from stellar_conquest.utils.hex_utils import HexGrid
        hex_grid = HexGrid()

        try:
            complete_path = hex_grid.find_shortest_path(player.entry_hex, location)
            if not complete_path:
                continue
        except Exception:
            continue

        # Send 1 scout with 1 corvette escort
        available_corvettes = ship_counts.get(ShipType.CORVETTE, 0)
        send_corvette = available_corvettes > 0

        # Split ships
        scout_success = split_ships_into_task_force(player, player.entry_hex, ShipType.SCOUT, 1, tf_number)
        if not scout_success:
            continue

        if send_corvette:
            split_ships_into_task_force(player, player.entry_hex, ShipType.CORVETTE, 1, tf_number)

        # Store movement plan
        if not hasattr(game_state, 'movement_plans'):
            game_state.movement_plans = {}
        if player.player_id not in game_state.movement_plans:
            game_state.movement_plans[player.player_id] = {}

        game_state.movement_plans[player.player_id][tf_number] = {
            'planned_path': complete_path,
            'path_index': 0,
            'final_destination': location,
            'target_name': star_name,
            'can_move_this_turn': True,
            'mission_type': 'recon'
        }

        # Track this target as scouted
        already_scouted.add(location)

        escort_str = " + 1 corvette escort" if send_corvette else ""
        distance = target_star['distance_from_us']
        turns_to_reach = (distance + player.current_ship_speed - 1) // player.current_ship_speed

        print(f"      🔭 TF{tf_number}: Scout{escort_str} → {star_name} at {location} (near {enemy_name}, ETA {turns_to_reach} turns)")

        scouts_sent += 1

    if scouts_sent > 0:
        print(f"      ✅ {scouts_sent} reconnaissance mission{'s' if scouts_sent > 1 else ''} dispatched")

def find_enemy_colonies(game_state, player):
    """Find known enemy colony locations - only from systems this player has actually explored."""
    enemy_colonies = []

    # Get systems this player has explored
    if not hasattr(game_state.board, 'explored_systems'):
        return enemy_colonies

    explored_by_player = set()
    for system_location, explorer_ids in game_state.board.explored_systems.items():
        if player.player_id in explorer_ids:
            explored_by_player.add(system_location)

    if not explored_by_player:
        return enemy_colonies

    # Only check colonies in systems this player has explored
    for other_player in game_state.players:
        if other_player.player_id == player.player_id:
            continue

        # Check if we've discovered their colonies in systems we've explored
        for colony in other_player.colonies:
            location = colony.location

            # Only add if we've explored this system
            if location in explored_by_player:
                distance = calculate_hex_distance(player.entry_hex, location)
                enemy_colonies.append({
                    'location': location,
                    'distance': distance,
                    'owner': other_player.name,
                    'population': colony.population,
                    'factories': colony.factories,
                    'defenses': getattr(colony, 'missile_bases', 0)
                })

    # Sort by distance (closest first)
    enemy_colonies.sort(key=lambda x: x['distance'])
    return enemy_colonies

def create_opportunistic_attacks(game_state, player, enemy_targets, turn_number):
    """Create direct attack task forces for non-Warlord players (simpler strategy).

    Attacks nearby weak targets if:
    - Target is within reasonable range
    - Player has available warships (excluding guards)
    - Target appears vulnerable (low defenses)
    """
    # Get warships reserved for guarding conquered colonies
    guards_needed = get_guarding_warships(player)

    # Find all available warships across locations (excluding guards)
    warships_by_location = {}
    for group in player.ship_groups:
        location = group.location

        # Get available warships at this location (excluding guards)
        available = get_available_warships_at_location(player, location, guards_needed)
        corvettes = available[ShipType.CORVETTE]
        fighters = available[ShipType.FIGHTER]
        death_stars = available[ShipType.DEATH_STAR]

        if corvettes + fighters + death_stars > 0:
            warships_by_location[location] = {
                'corvettes': corvettes,
                'fighters': fighters,
                'death_stars': death_stars
            }

    if not warships_by_location:
        return  # No warships available

    total_warships = sum(w['corvettes'] + w['fighters'] + w['death_stars'] for w in warships_by_location.values())

    # Look for weak, nearby targets
    attacks_launched = 0
    for target in enemy_targets:
        if attacks_launched >= 1:  # Limit to 1 attack per turn for non-Warlords
            break

        target_location = target['location']
        target_strength = target['population'] + (target['defenses'] * 3)

        # Only attack weak targets (population < 15M and defenses < 2)
        if target['population'] > 15 or target['defenses'] >= 2:
            continue

        # Find closest location with warships
        best_location = None
        best_distance = float('inf')

        for loc in warships_by_location.keys():
            distance = calculate_hex_distance(loc, target_location)
            if distance < best_distance and distance <= 12:  # Only attack if within 12 hexes
                best_distance = distance
                best_location = loc

        if best_location is None:
            continue

        ships = warships_by_location[best_location]

        # Determine attack force (send minimal force for weak targets)
        corvettes_to_send = min(1, ships['corvettes'])
        fighters_to_send = min(1, ships['fighters'])

        if corvettes_to_send + fighters_to_send == 0:
            continue

        print(f"   ⚔️  Opportunistic attack: {target['owner']}'s colony at {target_location} ({target['population']}M pop, {target['defenses']} bases)")

        # Launch direct attack
        success = create_single_attack_task_force(
            game_state, player, best_location, target_location,
            target['owner'], target['population'], target['defenses'],
            corvettes_to_send, fighters_to_send, 0, turn_number
        )

        if success:
            attacks_launched += 1
            # Remove used ships from available pool
            ships['corvettes'] -= corvettes_to_send
            ships['fighters'] -= fighters_to_send

def find_rally_point_star(game_state, player, warship_locations, target_location):
    """Find a suitable star hex to use as a rally point for assembling attack forces.

    Prioritizes:
    1. Star hexes the player controls (has colonies)
    2. Star hexes the player has explored
    3. Nearby star hexes between warship locations and target
    """
    # Get player's colony locations (best rally points)
    player_star_hexes = set()
    for colony in player.colonies:
        player_star_hexes.add(colony.location)

    # Get explored star systems
    explored_stars = set()
    if hasattr(game_state.board, 'explored_systems'):
        for system_location, explorer_ids in game_state.board.explored_systems.items():
            if player.player_id in explorer_ids:
                explored_stars.add(system_location)

    # Calculate average position of warship locations
    if not warship_locations:
        return None

    # Prefer player's own stars closest to the target
    if player_star_hexes:
        best_rally = None
        best_score = float('inf')

        for star_hex in player_star_hexes:
            # Score = distance to target + average distance from warships
            dist_to_target = calculate_hex_distance(star_hex, target_location)
            avg_dist_from_ships = sum(calculate_hex_distance(star_hex, loc) for loc in warship_locations) / len(warship_locations)
            score = dist_to_target + avg_dist_from_ships

            if score < best_score:
                best_score = score
                best_rally = star_hex

        if best_rally:
            return best_rally

    # Otherwise use explored stars
    if explored_stars:
        best_rally = None
        best_score = float('inf')

        for star_hex in explored_stars:
            dist_to_target = calculate_hex_distance(star_hex, target_location)
            avg_dist_from_ships = sum(calculate_hex_distance(star_hex, loc) for loc in warship_locations) / len(warship_locations)
            score = dist_to_target + avg_dist_from_ships

            if score < best_score:
                best_score = score
                best_rally = star_hex

        if best_rally:
            return best_rally

    # Fallback: use player's entry hex
    return player.entry_hex

def create_attack_task_forces_from_all_locations(game_state, player, enemy_targets, turn_number):
    """Create attack task forces by first rallying warships at a staging point, then attacking.

    Strategy:
    1. Select a rally point (nearby star hex)
    2. Send warships from various locations to the rally point (excluding guards)
    3. Wait for all ships to arrive
    4. Launch unified attack from rally point
    """
    print(f"   🎯 Planning coordinated attack with rally point strategy:")

    # Get warships reserved for guarding conquered colonies
    guards_needed = get_guarding_warships(player)

    # Find all available warships across ALL locations (excluding guards)
    warships_by_location = {}

    for group in player.ship_groups:
        location = group.location

        # Get available warships at this location (excluding guards)
        available = get_available_warships_at_location(player, location, guards_needed)

        if location not in warships_by_location:
            warships_by_location[location] = {
                'corvettes': 0,
                'fighters': 0,
                'death_stars': 0,
                'group': group
            }

        # Add available warships (already has guards subtracted)
        warships_by_location[location]['corvettes'] = available[ShipType.CORVETTE]
        warships_by_location[location]['fighters'] = available[ShipType.FIGHTER]
        warships_by_location[location]['death_stars'] = available[ShipType.DEATH_STAR]

    # Filter to only locations with available warships
    locations_with_warships = {
        loc: ships for loc, ships in warships_by_location.items()
        if (ships['corvettes'] + ships['fighters'] + ships['death_stars']) > 0
    }

    if not locations_with_warships:
        print(f"   ⚠️  No warships available for attack (guards are busy)")
        return

    # Show available forces by location
    total_corvettes = sum(s['corvettes'] for s in locations_with_warships.values())
    total_fighters = sum(s['fighters'] for s in locations_with_warships.values())
    total_death_stars = sum(s['death_stars'] for s in locations_with_warships.values())

    print(f"   Available forces across {len(locations_with_warships)} location{'s' if len(locations_with_warships) != 1 else ''}:")
    print(f"      Total: {total_corvettes} corvettes, {total_fighters} fighters, {total_death_stars} death stars")

    for loc, ships in locations_with_warships.items():
        if ships['corvettes'] + ships['fighters'] + ships['death_stars'] > 0:
            parts = []
            if ships['corvettes'] > 0:
                parts.append(f"{ships['corvettes']} corvette{'s' if ships['corvettes'] > 1 else ''}")
            if ships['fighters'] > 0:
                parts.append(f"{ships['fighters']} fighter{'s' if ships['fighters'] > 1 else ''}")
            if ships['death_stars'] > 0:
                parts.append(f"{ships['death_stars']} death star{'s' if ships['death_stars'] > 1 else ''}")
            print(f"      At {loc}: {', '.join(parts)}")

    # Track ongoing attack preparations
    if not hasattr(game_state, 'attack_staging'):
        game_state.attack_staging = {}
    if player.player_id not in game_state.attack_staging:
        game_state.attack_staging[player.player_id] = []

    # Process each enemy target
    for target in enemy_targets[:1]:  # Focus on one target at a time
        target_location = target['location']
        owner = target['owner']
        population = target['population']
        defenses = target['defenses']
        target_strength = population + (defenses * 3)

        # Determine how many ships we want for this attack
        corvettes_needed = 0
        fighters_needed = 0
        death_stars_needed = 0

        if target_strength > 15:  # Strong target
            corvettes_needed = min(3, total_corvettes)
            fighters_needed = min(2, total_fighters)
            death_stars_needed = min(1, total_death_stars)
        elif target_strength > 8:  # Medium target
            corvettes_needed = min(2, total_corvettes)
            fighters_needed = min(2, total_fighters)
        else:  # Weak target
            corvettes_needed = min(1, total_corvettes)
            fighters_needed = min(1, total_fighters)

        if corvettes_needed + fighters_needed + death_stars_needed == 0:
            print(f"   ⚠️  Insufficient forces available for attack")
            continue

        # Find rally point
        rally_point = find_rally_point_star(game_state, player, list(locations_with_warships.keys()), target_location)

        star_data = FIXED_STAR_LOCATIONS.get(rally_point, {})
        rally_name = star_data.get('starname', f'Star_{rally_point}')

        print(f"   🏴 Rally Point: {rally_name} at {rally_point}")
        print(f"   🎯 Target: {owner}'s colony at {target_location} ({population}M pop, {defenses} bases)")

        # Send warships to rally point
        rally_tf_list = send_warships_to_rally_point(
            game_state, player, locations_with_warships, rally_point,
            corvettes_needed, fighters_needed, death_stars_needed, turn_number
        )

        if rally_tf_list:
            # Track this attack staging
            game_state.attack_staging[player.player_id].append({
                'rally_point': rally_point,
                'rally_tfs': rally_tf_list,  # List of TFs heading to rally point
                'target': target_location,
                'target_owner': owner,
                'turn_initiated': turn_number,
                'ships_needed': {
                    'corvettes': corvettes_needed,
                    'fighters': fighters_needed,
                    'death_stars': death_stars_needed
                }
            })

        break  # Only plan one attack at a time

def send_warships_to_rally_point(game_state, player, locations_with_warships, rally_point,
                                  corvettes_needed, fighters_needed, death_stars_needed, turn_number):
    """Send warships from various locations to converge at a rally point.

    Returns: List of TF numbers heading to rally point, or None if failed
    """
    from stellar_conquest.utils.hex_utils import HexGrid
    hex_grid = HexGrid()

    corvettes_sent = 0
    fighters_sent = 0
    death_stars_sent = 0
    rally_tfs = []  # Track all TFs heading to rally point

    # Send warships from each location to rally point
    for location, ships_here in locations_with_warships.items():
        if location == rally_point:
            # Already at rally point - will be included in final count
            corvettes_sent += min(ships_here['corvettes'], corvettes_needed - corvettes_sent)
            fighters_sent += min(ships_here['fighters'], fighters_needed - fighters_sent)
            death_stars_sent += min(ships_here['death_stars'], death_stars_needed - death_stars_sent)
            continue

        # Determine what to send from this location
        corvettes_from_here = min(ships_here['corvettes'], corvettes_needed - corvettes_sent)
        fighters_from_here = min(ships_here['fighters'], fighters_needed - fighters_sent)
        death_stars_from_here = min(ships_here['death_stars'], death_stars_needed - death_stars_sent)

        if corvettes_from_here + fighters_from_here + death_stars_from_here == 0:
            continue  # Nothing to send from here

        # Get unique TF number for this group
        tf_number = 2
        if hasattr(game_state, 'movement_plans') and player.player_id in game_state.movement_plans:
            existing_tfs = set(game_state.movement_plans[player.player_id].keys())
            while tf_number in existing_tfs:
                tf_number += 1

        # Get path to rally point
        try:
            path_to_rally = hex_grid.find_shortest_path(location, rally_point)
            if not path_to_rally:
                print(f"     ⚠️  Cannot find path from {location} to rally point")
                continue
        except Exception as e:
            print(f"     ⚠️  Path error from {location}: {e}")
            continue

        # Create movement orders for ships from this location
        ships_split = False
        if corvettes_from_here > 0:
            success = split_ships_into_task_force(player, location, ShipType.CORVETTE, corvettes_from_here, tf_number)
            if success:
                corvettes_sent += corvettes_from_here
                ships_split = True

        if fighters_from_here > 0:
            success = split_ships_into_task_force(player, location, ShipType.FIGHTER, fighters_from_here, tf_number)
            if success:
                fighters_sent += fighters_from_here
                ships_split = True

        if death_stars_from_here > 0:
            success = split_ships_into_task_force(player, location, ShipType.DEATH_STAR, death_stars_from_here, tf_number)
            if success:
                death_stars_sent += death_stars_from_here
                ships_split = True

        if not ships_split:
            continue

        # Store movement plan to rally point
        if not hasattr(game_state, 'movement_plans'):
            game_state.movement_plans = {}
        if player.player_id not in game_state.movement_plans:
            game_state.movement_plans[player.player_id] = {}

        game_state.movement_plans[player.player_id][tf_number] = {
            'planned_path': path_to_rally,
            'path_index': 0,
            'final_destination': rally_point,
            'target_name': f'Rally Point',
            'can_move_this_turn': True,
            'mission_type': 'rally',
        }

        rally_tfs.append(tf_number)

        distance = calculate_hex_distance(location, rally_point)
        turns_to_rally = (distance + player.current_ship_speed - 1) // player.current_ship_speed

        parts = []
        if corvettes_from_here > 0:
            parts.append(f"{corvettes_from_here} corvette{'s' if corvettes_from_here > 1 else ''}")
        if fighters_from_here > 0:
            parts.append(f"{fighters_from_here} fighter{'s' if fighters_from_here > 1 else ''}")
        if death_stars_from_here > 0:
            parts.append(f"{death_stars_from_here} death star{'s' if death_stars_from_here > 1 else ''}")

        print(f"     ⚙️  TF{tf_number}: {', '.join(parts)} from {location} → rally point (ETA {turns_to_rally} turns)")

    if corvettes_sent + fighters_sent + death_stars_sent == 0:
        print(f"     ⚠️  Failed to send any ships to rally point")
        return None

    total_sent = corvettes_sent + fighters_sent + death_stars_sent
    print(f"     ✅ {total_sent} warships ordered to rally point")
    return rally_tfs if rally_tfs else None

def create_single_attack_task_force(game_state, player, launch_location, target_location, owner, population, defenses,
                                    corvettes_to_send, fighters_to_send, death_stars_to_send, turn_number):
    """Create a single attack task force from a specific location."""
    # Find next available task force number
    tf_number = 2
    if hasattr(game_state, 'movement_plans') and player.player_id in game_state.movement_plans:
        existing_tfs = set(game_state.movement_plans[player.player_id].keys())
        while tf_number in existing_tfs:
            tf_number += 1

    # Build force description
    force_parts = []
    if corvettes_to_send > 0:
        force_parts.append(f"{corvettes_to_send} corvette{'s' if corvettes_to_send > 1 else ''}")
    if fighters_to_send > 0:
        force_parts.append(f"{fighters_to_send} fighter{'s' if fighters_to_send > 1 else ''}")
    if death_stars_to_send > 0:
        force_parts.append(f"{death_stars_to_send} death star{'s' if death_stars_to_send > 1 else ''}")
    force_desc = " + ".join(force_parts)

    # Show target strength
    if defenses > 0:
        target_desc = f"{population}M pop, {defenses} missile bases"
    else:
        target_desc = f"{population}M pop, undefended"

    distance = calculate_hex_distance(launch_location, target_location)
    print(f"   🗡️  Creating TF{tf_number}: {force_desc} from {launch_location} → ATTACK {owner}'s colony at {target_location} ({target_desc}, {distance} hexes)")

    # Get path
    from stellar_conquest.utils.hex_utils import HexGrid
    hex_grid = HexGrid()

    try:
        complete_path = hex_grid.find_shortest_path(launch_location, target_location)
        if not complete_path:
            print(f"     ⚠️  Unable to find path, skipping")
            return False
    except Exception as e:
        print(f"     ⚠️  Path finding error: {e}, skipping")
        return False

    # Create the task force by splitting ships
    all_success = True

    if corvettes_to_send > 0:
        success = split_ships_into_task_force(player, launch_location, ShipType.CORVETTE, corvettes_to_send, tf_number)
        if not success:
            all_success = False

    if fighters_to_send > 0:
        success = split_ships_into_task_force(player, launch_location, ShipType.FIGHTER, fighters_to_send, tf_number)
        if not success:
            all_success = False

    if death_stars_to_send > 0:
        success = split_ships_into_task_force(player, launch_location, ShipType.DEATH_STAR, death_stars_to_send, tf_number)
        if not success:
            all_success = False

    if all_success:
        # Store movement plan
        if not hasattr(game_state, 'movement_plans'):
            game_state.movement_plans = {}
        if player.player_id not in game_state.movement_plans:
            game_state.movement_plans[player.player_id] = {}

        game_state.movement_plans[player.player_id][tf_number] = {
            'planned_path': complete_path,
            'path_index': 0,
            'final_destination': target_location,
            'target_name': f"{owner}'s colony",
            'can_move_this_turn': True,
            'mission_type': 'attack',
            'target_owner': owner
        }

        turns_to_reach = (distance + player.current_ship_speed - 1) // player.current_ship_speed
        print(f"     ✅ Attack force created - ETA {turns_to_reach} turns")
        return True
    else:
        print(f"     ❌ Attack force creation failed")
        return False

def create_attack_task_forces(game_state, player, entry_hex, main_group, enemy_targets, turn_number):
    """Create attack task forces to raid enemy colonies (Warlord strategy)."""
    print(f"   🎯 Planning attack missions against discovered enemy colonies:")

    # Get available warships
    available_corvettes = main_group.get_ship_counts().get(ShipType.CORVETTE, 0)
    available_fighters = main_group.get_ship_counts().get(ShipType.FIGHTER, 0)
    available_death_stars = main_group.get_ship_counts().get(ShipType.DEATH_STAR, 0)

    total_warships = available_corvettes + available_fighters + available_death_stars

    if total_warships == 0:
        print(f"   ⚠️  No warships available for attack missions")
        return

    print(f"   Available forces: {available_corvettes} corvettes, {available_fighters} fighters, {available_death_stars} death stars")

    # Target multiple enemy colonies based on available forces
    attacks_launched = 0
    max_attacks = min(len(enemy_targets), (total_warships + 1) // 2)  # At least 2 ships per attack

    for target in enemy_targets[:max_attacks]:
        if available_corvettes == 0 and available_fighters == 0 and available_death_stars == 0:
            break

        target_location = target['location']
        owner = target['owner']
        population = target['population']
        defenses = target['defenses']

        # Determine attack force composition based on target strength and available ships
        # Stronger colonies (more population/defenses) get larger attack forces
        target_strength = population + (defenses * 3)  # Missile bases count more

        # Flexible force composition
        corvettes_to_send = 0
        fighters_to_send = 0
        death_stars_to_send = 0

        if target_strength > 15:  # Strong target
            # Send overwhelming force
            corvettes_to_send = min(3, available_corvettes)
            fighters_to_send = min(2, available_fighters)
            death_stars_to_send = min(1, available_death_stars)
        elif target_strength > 8:  # Medium target
            # Send moderate force with varied composition
            if available_corvettes >= 2:
                corvettes_to_send = 2
            elif available_corvettes == 1:
                corvettes_to_send = 1
                fighters_to_send = min(1, available_fighters)
            else:
                fighters_to_send = min(2, available_fighters)
        else:  # Weak target
            # Send minimal raiding force - mix it up
            if available_fighters >= 2:
                fighters_to_send = 2  # Fast fighter raid
            elif available_corvettes >= 1:
                corvettes_to_send = 1  # Single corvette raid
                if available_fighters >= 1:
                    fighters_to_send = 1  # Plus a fighter
            else:
                # Use whatever we have
                corvettes_to_send = min(1, available_corvettes)
                fighters_to_send = min(1, available_fighters)

        # Ensure we're sending at least something
        total_ships_to_send = corvettes_to_send + fighters_to_send + death_stars_to_send
        if total_ships_to_send == 0:
            continue

        # Find next available task force number
        tf_number = 2
        if hasattr(game_state, 'movement_plans') and player.player_id in game_state.movement_plans:
            existing_tfs = set(game_state.movement_plans[player.player_id].keys())
            while tf_number in existing_tfs:
                tf_number += 1

        # Build attack force description
        force_parts = []
        if corvettes_to_send > 0:
            force_parts.append(f"{corvettes_to_send} corvette{'s' if corvettes_to_send > 1 else ''}")
        if fighters_to_send > 0:
            force_parts.append(f"{fighters_to_send} fighter{'s' if fighters_to_send > 1 else ''}")
        if death_stars_to_send > 0:
            force_parts.append(f"{death_stars_to_send} death star{'s' if death_stars_to_send > 1 else ''}")
        force_desc = " + ".join(force_parts)

        # Show target strength assessment
        if defenses > 0:
            target_desc = f"{population}M pop, {defenses} missile bases"
        else:
            target_desc = f"{population}M pop, undefended"

        print(f"   🗡️  Creating TF{tf_number}: {force_desc} → ATTACK {owner}'s colony at {target_location} ({target_desc})")

        # Get path to target
        from stellar_conquest.utils.hex_utils import HexGrid
        hex_grid = HexGrid()

        try:
            complete_path = hex_grid.find_shortest_path(entry_hex, target_location)
            if not complete_path:
                print(f"     ⚠️  Unable to find path to {target_location}, skipping")
                continue
        except Exception as e:
            print(f"     ⚠️  Path finding error: {e}, skipping")
            continue

        # Create the attack task force
        all_success = True

        if corvettes_to_send > 0:
            corvette_success = split_ships_into_task_force(
                player, entry_hex, ShipType.CORVETTE, corvettes_to_send, tf_number
            )
            if corvette_success:
                available_corvettes -= corvettes_to_send
            else:
                all_success = False

        if fighters_to_send > 0:
            fighter_success = split_ships_into_task_force(
                player, entry_hex, ShipType.FIGHTER, fighters_to_send, tf_number
            )
            if fighter_success:
                available_fighters -= fighters_to_send
            else:
                all_success = False

        if death_stars_to_send > 0:
            death_star_success = split_ships_into_task_force(
                player, entry_hex, ShipType.DEATH_STAR, death_stars_to_send, tf_number
            )
            if death_star_success:
                available_death_stars -= death_stars_to_send
            else:
                all_success = False

        if all_success:
            # Store movement plan for attack mission
            if not hasattr(game_state, 'movement_plans'):
                game_state.movement_plans = {}
            if player.player_id not in game_state.movement_plans:
                game_state.movement_plans[player.player_id] = {}

            game_state.movement_plans[player.player_id][tf_number] = {
                'planned_path': complete_path,
                'path_index': 0,
                'final_destination': target_location,
                'target_name': f"{owner}'s colony",
                'can_move_this_turn': True,
                'mission_type': 'attack',
                'target_owner': owner
            }

            distance = target['distance']
            turns_to_reach = (distance + player.current_ship_speed - 1) // player.current_ship_speed
            print(f"     ✅ Attack force created - ETA {turns_to_reach} turns")
            attacks_launched += 1
        else:
            print(f"     ❌ Attack force creation failed")

    if attacks_launched > 0:
        print(f"   ⚔️  {attacks_launched} attack mission{'s' if attacks_launched > 1 else ''} launched!")

def create_exploration_task_forces(game_state, player, turn_number=2):
    """Split starting fleet into multiple exploration task forces."""
    print(f"   {player.name} organizes multiple task forces for exploration:")

    entry_hex = player.entry_hex
    main_group = None
    for group in player.ship_groups:
        if group.location == entry_hex:
            main_group = group
            break

    if not main_group:
        print(f"   No ships found at entry hex {entry_hex}")
        return

    # For Warlord play style: Send scouts to enemy yellow stars for reconnaissance (turn 2+)
    if player.play_style.value == "warlord" and turn_number >= 2:
        send_warlord_scouts_to_enemy_yellow_stars(game_state, player, main_group, turn_number)

    # For Warlord play style after turn 4, check for attack opportunities
    if player.play_style.value == "warlord" and turn_number >= 4:
        enemy_targets = find_enemy_colonies(game_state, player)

        if enemy_targets:
            print(f"   ⚔️  WARLORD MODE ACTIVATED: {len(enemy_targets)} enemy colony location{'s' if len(enemy_targets) != 1 else ''} discovered in explored systems!")
            for i, target in enumerate(enemy_targets[:3], 1):  # Show top 3 targets
                print(f"      Target {i}: {target['owner']}'s colony at {target['location']} - {target['distance']} hexes away")
            create_attack_task_forces_from_all_locations(game_state, player, enemy_targets, turn_number)
        else:
            print(f"   🔍 Warlord scouting: No enemy colonies discovered yet in explored systems")

    nearby_stars = find_nearest_stars(entry_hex, 8)
    
    if len(nearby_stars) >= 2:
        print(f"   Strategic exploration targets identified:")
        for i, (location, distance, name, color) in enumerate(nearby_stars[:3]):
            print(f"     Target {i+1}: {location} - {name} ({color} star, {distance} hexes away)")
        
        # Aggressive early exploration: scouts are ideal, but any ship can explore
        # Send out ALL scouts and most corvettes for maximum coverage
        available_scouts = main_group.get_ship_counts().get(ShipType.SCOUT, 0)
        available_corvettes = main_group.get_ship_counts().get(ShipType.CORVETTE, 0)
        
        # Send out ALL scouts, use corvettes for escort missions
        max_corvette_tfs = min(available_corvettes, len(nearby_stars), 6)  # Use corvettes for escort missions
        
        # Create task forces to send out ALL scouts - ensure unique targets per task force
        scouts_sent = 0
        corvettes_sent = 0
        task_force_count = 0
        assigned_targets = set()  # Track already assigned star targets
        
        # First, send out all scouts (one per task force initially)
        while scouts_sent < available_scouts and task_force_count < 15:  # Increased cap to handle more scouts
            # Always assign one scout
            scouts_to_move = 1
            scouts_sent += 1
            corvettes_to_move = 0
            
            # Find next available unique target
            target_location = None
            for star_location, distance, name, color in nearby_stars:
                if star_location not in assigned_targets:
                    target_location = star_location
                    assigned_targets.add(star_location)
                    break
            
            # If all nearby stars are assigned, look for more distant ones
            if target_location is None:
                all_stars = find_nearest_stars(entry_hex, 15)  # Expand search radius
                for star_location, distance, name, color in all_stars:
                    if star_location not in assigned_targets:
                        target_location = star_location
                        assigned_targets.add(star_location)
                        print(f"   📡 Expanding search radius - targeting distant star {name} at {star_location}")
                        break
            
            # If still no target found, reuse existing targets to deploy remaining scouts
            if target_location is None:
                if nearby_stars:
                    # Reuse the first target for remaining scouts
                    target_location, distance, name, color = nearby_stars[0]
                    print(f"   📡 Reusing target {name} at {target_location} for remaining scouts")
                else:
                    print(f"   ⚠️  No targets available at all - {scouts_sent - 1} scouts deployed")
                    scouts_sent -= 1  # Revert the scout count since we're not using this one
                    break
            
            # Modify composition based on play style for corvette assignment
            if player.play_style.value == "expansionist":
                if task_force_count < 2 and corvettes_sent < max_corvette_tfs:
                    # Expansionist: Add corvette escorts to first few missions
                    corvettes_to_move = 1
                    corvettes_sent += 1
            elif player.play_style.value == "warlord":
                if task_force_count == 0 and corvettes_sent < max_corvette_tfs:
                    # Warlord: Escort the first deep penetration mission
                    corvettes_to_move = 1
                    corvettes_sent += 1
            elif task_force_count < 2 and corvettes_sent < max_corvette_tfs:
                # Conservative styles: escort first few missions only
                corvettes_to_move = 1
                corvettes_sent += 1
            
            # Get target information from FIXED_STAR_LOCATIONS
            target_data = FIXED_STAR_LOCATIONS.get(target_location, {})
            name = target_data.get('starname', f'Star_{target_location}')
            color = target_data.get('color', 'unknown')
            distance = calculate_hex_distance(entry_hex, target_location)
            next_hex = plan_next_move_toward_target(game_state, entry_hex, target_location, player.current_ship_speed, turn_number)
            
            if next_hex and next_hex != entry_hex:
                tf_number = task_force_count + 2  # TF2, TF3, etc.
                
                # Create task force by splitting ships from main fleet - NO MOVEMENT YET
                if scouts_to_move > 0 and corvettes_to_move > 0:
                    tf_description = f"{scouts_to_move} scout + {corvettes_to_move} corvette"
                elif scouts_to_move > 0:
                    tf_description = f"{scouts_to_move} scout"
                elif corvettes_to_move > 0:
                    tf_description = f"{corvettes_to_move} corvette"
                else:
                    continue  # Skip if no ships to move
                
                print(f"   Creating TF{tf_number}: {tf_description} → target {name} at {target_location}")
                
                # Get the complete planned path using proper hex grid pathfinding
                from stellar_conquest.utils.hex_utils import HexGrid
                hex_grid = HexGrid()
                
                try:
                    complete_path = hex_grid.find_shortest_path(entry_hex, target_location)
                    if not complete_path:
                        print(f"     ⚠️  Unable to find path to {target_location}, skipping this task force")
                        continue
                except Exception as e:
                    print(f"     ⚠️  Path finding error to {target_location}: {e}, skipping this task force")
                    continue
                
                # Generate and display the complete route
                route_display = generate_route_display(game_state, entry_hex, target_location, player.current_ship_speed, turn_number)
                print(f"     🚌 Planned route: {route_display}")
                print(f"     📋 Task force will start moving in movement phase")
                
                # Split ships from main fleet to create new task force at same location
                scout_success = True
                if scouts_to_move > 0:
                    scout_success = split_ships_into_task_force(
                        player, entry_hex, ShipType.SCOUT, scouts_to_move, tf_number
                    )
                
                # Split corvette if available
                corvette_success = True
                if corvettes_to_move > 0:
                    corvette_success = split_ships_into_task_force(
                        player, entry_hex, ShipType.CORVETTE, corvettes_to_move, tf_number
                    )
                
                if scout_success and corvette_success:
                    # Store movement plan - task force starts at entry hex
                    game_state.movement_plans[player.player_id][tf_number] = {
                        'current_location': entry_hex,
                        'planned_path': complete_path,
                        'path_index': 0,  # Starting at beginning of path
                        'final_destination': target_location,
                        'target_name': name,
                        'can_move_this_turn': True  # New task forces can move in movement phase
                    }
                    print(f"     ✅ TF{tf_number} created at {entry_hex}, ready to move toward {name}")
                else:
                    print(f"     ❌ TF{tf_number} creation failed")
            
            # Increment task force counter
            task_force_count += 1
        
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
                print(f"     {count} {ship_type.value}")
        print(f"   TF1 at {entry_hex} holds remaining ships")
    else:
        print(f"   ✅ All ships successfully deployed - TF1 at {entry_hex} is empty")
    return True

def create_colonization_task_forces(game_state, player, entry_hex, main_group, starting_tf_count, assigned_targets, turn_number):
    """Create task forces with colony transports to colonize nearby yellow stars."""
    print(f"   {player.name} also sends colony transports for early colonization:")
    print(f"   📊 Starting TF count for colonization: {starting_tf_count}")
    
    # Find nearest yellow stars (can share targets with exploration task forces)
    yellow_stars = find_nearest_yellow_stars(entry_hex, 10)  # Increased radius for colonization
    available_yellow_targets = []
    
    # Allow colony transports to target yellow stars even if scouts are also going there
    for star_location, distance, name, color in yellow_stars:
        available_yellow_targets.append((star_location, distance, name, color))
    
    if not available_yellow_targets:
        print(f"   No suitable yellow stars available for colonization")
        return starting_tf_count
    
    # Get available ships for colonization
    available_transports = main_group.get_ship_counts().get(ShipType.COLONY_TRANSPORT, 0)
    available_corvettes = main_group.get_ship_counts().get(ShipType.CORVETTE, 0)
    
    if available_transports == 0:
        print(f"   No colony transports available")
        return starting_tf_count
    
    # Send ALL colony transports to the closest yellow star
    if available_yellow_targets:
        target_location, distance, name, color = available_yellow_targets[0]  # Closest yellow star
        
        # Find next available task force number by checking movement plans
        tf_number = 2  # Start at 2 (TF1 is main fleet)
        if hasattr(game_state, 'movement_plans') and player.player_id in game_state.movement_plans:
            existing_tfs = set(game_state.movement_plans[player.player_id].keys())
            while tf_number in existing_tfs:
                tf_number += 1
        
        # Send ALL colony transports to maximize early colonization
        transports_to_move = available_transports
        # Send ALL available corvettes as escorts - no need to reserve any for TF1
        corvettes_to_move = available_corvettes
        
        tf_description = f"{transports_to_move} colony transport{'s' if transports_to_move > 1 else ''}"
        if corvettes_to_move > 0:
            tf_description += f" + {corvettes_to_move} corvette escort{'s' if corvettes_to_move > 1 else ''}"
        
        print(f"   Creating TF{tf_number}: {tf_description} → colonize {name} at {target_location}")
        print(f"     🎯 Strategic goal: Establish major colony with ALL transports for maximum early production")
        
        # Get the complete planned path using hex grid pathfinding
        from stellar_conquest.utils.hex_utils import HexGrid
        hex_grid = HexGrid()
        
        try:
            complete_path = hex_grid.find_shortest_path(entry_hex, target_location)
            if not complete_path:
                print(f"     ⚠️  Unable to find path to {target_location}, no colonization possible")
                return starting_tf_count
        except Exception as e:
            print(f"     ⚠️  Path finding error to {target_location}: {e}, no colonization possible")
            return starting_tf_count
        
        # Generate and display the complete route
        route_display = generate_route_display(game_state, entry_hex, target_location, player.current_ship_speed, turn_number)
        print(f"     🚌 Planned route: {route_display}")
        print(f"     📋 Major colonization fleet will start moving in movement phase")
        
        # Split ships from main fleet to create new task force
        transport_success = split_ships_into_task_force(
            player, entry_hex, ShipType.COLONY_TRANSPORT, transports_to_move, tf_number
        )
        
        corvette_success = True
        if corvettes_to_move > 0:
            corvette_success = split_ships_into_task_force(
                player, entry_hex, ShipType.CORVETTE, corvettes_to_move, tf_number
            )
        
        if transport_success and corvette_success:
            # Store movement plan for this task force
            if not hasattr(game_state, 'movement_plans'):
                game_state.movement_plans = {}
            if player.player_id not in game_state.movement_plans:
                game_state.movement_plans[player.player_id] = {}
            
            # Store the movement plan 
            game_state.movement_plans[player.player_id][tf_number] = {
                'planned_path': complete_path,
                'path_index': 0,  # Starting at beginning of path
                'final_destination': target_location,
                'target_name': name,
                'can_move_this_turn': True,  # New task forces can move in movement phase
                'mission_type': 'major_colonization'  # Mark as major colonization mission
            }
            print(f"     ✅ TF{tf_number} created at {entry_hex}, ready to move toward {name}")
            print(f"     📊 Colonization fleet: {transports_to_move} million colonists ready for deployment")
            
            return tf_number
        else:
            print(f"     ❌ TF{tf_number} creation failed")
    
    return starting_tf_count

def place_starting_fleet_with_task_force_id(player):
    """Place starting fleet with task force ID 1."""
    from stellar_conquest.core.constants import STARTING_FLEET
    from stellar_conquest.entities.ship import Ship, ShipGroup
    
    if player.has_entered_board:
        return
    
    # Create ship group for TF1
    group = ShipGroup(player.entry_hex, player.player_id)
    player.ship_groups.append(group)
    
    # Add each ship type with task force ID 1
    for ship_type, count in STARTING_FLEET.items():
        if count > 0:
            ship = Ship(
                ship_type=ship_type,
                count=count,
                location=player.entry_hex,
                player_id=player.player_id,
                game_id=player.game_id,
                task_force_id=1  # TF1 always gets ID 1
            )
            group.add_ships(ship)
    
    player.has_entered_board = True
    player.update_modified_time()

def make_movement_decisions(game_state, player, turn_number):
    """Execute movement for existing task forces along their declared paths."""
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
                
                # Log intelligence for both sides about the encounter
                if player.name not in intelligence_system.enemy_activity_logs:
                    intelligence_system.initialize_player_logs(player.name)
                
                # Get our ships for intelligence logging
                our_ships = {}
                for group in player.ship_groups:
                    for ship in group.ships:
                        if ship.location == current_location:  # Our ships are still at previous location
                            if ship.ship_type not in our_ships:
                                our_ships[ship.ship_type] = 0
                            our_ships[ship.ship_type] += ship.count
                
                our_ship_list = []
                for ship_type, count in our_ships.items():
                    ship_name = ship_type.value.lower()
                    our_ship_list.append(f"{count} {ship_name}{'s' if count > 1 else ''}")
                
                for enemy_id, ships in enemy_ships.items():
                    enemy_player = next(p for p in game_state.players if p.player_id == enemy_id)
                    enemy_ship_summary = ", ".join([f"{count} {ship_type.value.lower()}" for ship_type, count in ships.items()])
                    print(f"       {enemy_player.name}: {enemy_ship_summary}")
                    
                    # Log from our perspective: we encountered enemy ships and were forced to stop
                    intelligence_msg = f"Forced stop at {step_location} - enemy ships present: {enemy_ship_summary}"
                    intelligence_system.log_enemy_activity(
                        player.name, turn_number, step_location,
                        ActivityType.MOVEMENT_ENCOUNTER, enemy_player.name, intelligence_msg, 3
                    )
                    
                    # Log from enemy perspective: they detected approaching ships
                    if enemy_player.name not in intelligence_system.enemy_activity_logs:
                        intelligence_system.initialize_player_logs(enemy_player.name)
                    intelligence_msg = f"Enemy ships approached {step_location} but stopped: {', '.join(our_ship_list)}"
                    intelligence_system.log_enemy_activity(
                        enemy_player.name, turn_number, step_location,
                        ActivityType.MOVEMENT_ENCOUNTER, player.name, intelligence_msg, 2
                    )
                
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
                
                # Monitor enemy activity at the new location (for all players with colonies there)
                for colony_owner in game_state.players:
                    if colony_owner.player_id != player.player_id:
                        monitor_star_system_traffic(game_state, colony_owner, new_location, turn_number)
                
                # Update movement plan with new position
                game_state.movement_plans[player.player_id][tf_number].update({
                    'current_location': new_location,
                    'path_index': actual_end_index
                })
                
                # Mark if this task force is now in combat position
                if forced_stop_location:
                    game_state.movement_plans[player.player_id][tf_number]['in_combat'] = True
                    game_state.movement_plans[player.player_id][tf_number]['combat_location'] = forced_stop_location
                
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

def make_exploration_decisions(game_state, player, turn_number):
    """Make exploration decisions for a player."""
    print_phase_header(turn_number, "b", "STAR EXPLORATION")
    
    explorations_made = 0
    
    for tf_index, group in enumerate(player.ship_groups):
        location = group.location
        tf_number = tf_index + 1
        
        print(f"\n🔍 TF{tf_number} at {location}:")
        
        if game_state.board.is_star_location(location):
            if not game_state.board.is_system_explored(location, player.player_id):
                ship_counts = group.get_ship_counts()
                star_data = FIXED_STAR_LOCATIONS[location]
                
                print(f"   Star: {star_data['starname']} ({star_data['color']} star)")
                
                has_warships = group.has_warships()
                has_unarmed = any(ship.is_unarmed for ship in group.ships if ship.count > 0)
                
                # Any ship can explore, choose the best available explorer
                available_ships = [(ship_type, count) for ship_type, count in ship_counts.items() if count > 0]
                if not available_ships:
                    print(f"   No ships available for exploration")
                    continue
                
                # Prefer scouts for exploration if available, but any ship can do it
                if ShipType.SCOUT in ship_counts and ship_counts[ShipType.SCOUT] > 0:
                    explorer_type = ShipType.SCOUT
                    print(f"   Explorer: 1 scout (ideal for exploration)")
                else:
                    # Choose any available ship - corvettes, transports, fighters, etc. all can explore
                    explorer_type = available_ships[0][0]
                    print(f"   Explorer: 1 {explorer_type.value} (any ship can explore)")
                
                print(f"   Escort: {'Yes' if has_warships else 'No'} (warship protection)")
                
                # Show safety check info for unarmed vessels
                if has_unarmed and not has_warships:
                    print(f"   ⚠️  Safety risk: Unarmed vessels (scouts/transports) face 1/6 chance of loss")
                elif has_unarmed and has_warships:
                    print(f"   🛡️  Safety: Warships protect unarmed vessels from exploration risks")
                else:
                    print(f"   🛡️  Safety: Warships face no exploration risks")
                
                # Note: Exploration hazards are handled by the ExplorationAction itself
                
                print(f"   Decision: Explore {star_data['starname']} with {explorer_type.value}")
                
                exploration_order = ExplorationOrder(
                    location=location,
                    explorer_ship_type=explorer_type,
                    explorer_count=1,
                    has_warship_escort=has_warships
                )
                
                exploration_action = ExplorationAction(player.player_id, [exploration_order])
                result = exploration_action.execute(game_state)
                
                
                if result.result.value == "success" and result.data:
                    exploration_results = result.data.get('exploration_results', [])
                    for exp_result in exploration_results:
                        # Check if it's the detailed exploration result object
                        if hasattr(exp_result, 'planets_discovered'):
                            planets = exp_result.planets_discovered
                            ships_lost = getattr(exp_result, 'ships_lost', 0)
                            colonies_revealed = getattr(exp_result, 'colonies_revealed', [])
                            ships_revealed = getattr(exp_result, 'ships_revealed', [])
                            
                            print(f"   ✨ Exploration successful!")
                            print(f"      Star card drawn: #{exp_result.star_card_number}")
                            
                            # Create summary of planet types discovered  
                            if planets:
                                planet_types = [planet.planet_type.value for planet in planets]
                                planet_summary = ", ".join(planet_types)
                                print(f"      Planets discovered: {len(planets)} ({planet_summary})")
                                
                                # Show detailed planet information
                                for i, planet in enumerate(planets, 1):
                                    mineral_str = " (mineral-rich)" if planet.is_mineral_rich else ""
                                    print(f"         Planet {i}: {planet.planet_type.value} (max {planet.max_population}M pop){mineral_str}")
                            else:
                                print(f"      Planets discovered: 0 (empty system)")
                            
                            # Display enemy colonies and ships revealed during exploration (per rules)
                            if colonies_revealed:
                                print(f"      🏛️ Enemy colonies revealed:")
                                for colony_info in colonies_revealed:
                                    other_player = game_state.players[colony_info['player_id']]
                                    shield_info = " (PLANET SHIELD)" if colony_info['has_planet_shield'] else ""
                                    print(f"         • {other_player.name}: {colony_info['population']}M pop, {colony_info['factories']} factories, {colony_info['planet_type']}{shield_info}")
                                    
                                    # Log colony discovery to intelligence
                                    from stellar_conquest.utils.enemy_intelligence import intelligence_system, ActivityType
                                    intelligence_system.log_enemy_activity(
                                        observer_player=player.name,
                                        turn=turn_number,
                                        location=location,
                                        activity_type=ActivityType.ENEMY_COLONY_DISCOVERED,
                                        enemy_player=other_player.name,
                                        details=f"Colony discovered: {colony_info['population']}M pop, {colony_info['factories']} factories on {colony_info['planet_type']}{shield_info}",
                                        threat_level=3 if colony_info['has_planet_shield'] else 2
                                    )
                            
                            if ships_revealed:
                                print(f"      🚢 Enemy ships revealed:")
                                for ship_info in ships_revealed:
                                    other_player = game_state.players[ship_info['player_id']]
                                    ship_details = []
                                    for ship_type, count in ship_info['ship_counts'].items():
                                        if count > 0:
                                            ship_details.append(f"{count} {ship_type}")
                                    ships_str = ", ".join(ship_details)
                                    print(f"         • {other_player.name}: {ships_str}")
                                    
                                    # Log ship discovery to intelligence
                                    from stellar_conquest.utils.enemy_intelligence import intelligence_system, ActivityType
                                    intelligence_system.log_enemy_activity(
                                        observer_player=player.name,
                                        turn=turn_number,
                                        location=location,
                                        activity_type=ActivityType.ENEMY_SHIPS_DISCOVERED,
                                        enemy_player=other_player.name,
                                        details=f"Ships discovered: {ships_str}",
                                        threat_level=4 if 'death_star' in ships_str else 3 if 'fighter' in ships_str else 2
                                    )
                            
                            # Additional enemy detection (for ships that moved here after initial exploration) 
                            detect_and_log_enemies(game_state, player, location, turn_number)
                            
                            if ships_lost > 0:
                                print(f"      💥 Ships lost to hazards: {ships_lost}")
                                # Remove destroyed ships from the task force
                                removed = remove_ships_from_task_force(player, location, explorer_type, ships_lost, tf_number)
                                if removed > 0:
                                    print(f"      🚢 Removed {removed} destroyed {explorer_type.value}{'s' if removed > 1 else ''} from TF{tf_number}")
                            
                            explorations_made += 1
                            
                            # After successful exploration, choose new destination
                            choose_new_destination(game_state, player, tf_number, location)
                        elif isinstance(exp_result, dict):
                            # Fallback for dict format
                            planets = exp_result.get('planets_discovered', 0)
                            ships_lost = exp_result.get('ships_lost', 0)
                            colonies_revealed = exp_result.get('colonies_revealed', [])
                            ships_revealed = exp_result.get('ships_revealed', [])
                            
                            print(f"   ✨ Exploration successful!")
                            print(f"      Star card drawn: #{exp_result.get('star_card_number', '?')}")
                            print(f"      Planets discovered: {planets}")
                            
                            # Display enemy information revealed during exploration
                            if colonies_revealed:
                                print(f"      🏛️ Enemy colonies revealed:")
                                for colony_info in colonies_revealed:
                                    other_player = game_state.players[colony_info['player_id']]
                                    shield_info = " (PLANET SHIELD)" if colony_info['has_planet_shield'] else ""
                                    print(f"         • {other_player.name}: {colony_info['population']}M pop, {colony_info['factories']} factories{shield_info}")
                            
                            if ships_revealed:
                                print(f"      🚢 Enemy ships revealed:")
                                for ship_info in ships_revealed:
                                    other_player = game_state.players[ship_info['player_id']]
                                    print(f"         • {other_player.name}: {ship_info['total_ships']} ships")
                            
                            # Enemy Detection and Intelligence Logging
                            detect_and_log_enemies(game_state, player, location, turn_number)
                            
                            if ships_lost > 0:
                                print(f"      💥 Ships lost to hazards: {ships_lost}")
                                # Remove destroyed ships from the task force
                                removed = remove_ships_from_task_force(player, location, explorer_type, ships_lost, tf_number)
                                if removed > 0:
                                    print(f"      🚢 Removed {removed} destroyed {explorer_type.value}{'s' if removed > 1 else ''} from TF{tf_number}")
                            
                            explorations_made += 1
                            
                            # After successful exploration, choose new destination
                            choose_new_destination(game_state, player, tf_number, location)
                else:
                    # Provide detailed failure information
                    print(f"   ❌ Exploration failed!")
                    print(f"      Reason: {result.message}")
                    
                    # Check if the failure was due to ship destruction
                    if result.data and 'exploration_results' in result.data:
                        exploration_results = result.data['exploration_results']
                        for exp_result in exploration_results:
                            ships_lost = 0
                            if hasattr(exp_result, 'ships_lost'):
                                ships_lost = exp_result.ships_lost
                            elif isinstance(exp_result, dict):
                                ships_lost = exp_result.get('ships_lost', 0)
                            
                            if ships_lost > 0:
                                print(f"      💥 {ships_lost} {explorer_type.value}{'s' if ships_lost > 1 else ''} destroyed during exploration attempt")
                                # Remove destroyed ships from the task force
                                removed = remove_ships_from_task_force(player, location, explorer_type, ships_lost, tf_number)
                                if removed > 0:
                                    print(f"      🚢 Removed {removed} destroyed {explorer_type.value}{'s' if removed > 1 else ''} from TF{tf_number}")
                    
                    # Check for common failure reasons and provide specific explanations
                    if "no ships" in result.message.lower():
                        print(f"      📝 No ships available for exploration at {location}")
                    elif "escort" in result.message.lower() or "warship" in result.message.lower():
                        print(f"      📝 Exploration requires warship escort for safety")
                    elif "hazard" in result.message.lower() or "destroyed" in result.message.lower():
                        print(f"      📝 Explorer ship destroyed by space hazards")
                    elif "invalid" in result.message.lower():
                        print(f"      📝 Invalid exploration parameters")
                    else:
                        print(f"      📝 General exploration failure - check exploration requirements")
            else:
                print(f"   Already explored this star system")
                # Even if already explored, task force should choose new destination
                choose_new_destination(game_state, player, tf_number, location)
        else:
            print(f"   No star at this location")
    
    if explorations_made == 0:
        print(f"\n{player.name} has no exploration opportunities this turn")
    
    return explorations_made > 0

def get_combat_value(attacker_type, target_type):
    """Get combat values based on attack table from rules."""
    # Attack table from rules 4.1 - returns (dice_needed, target_number)
    # Format: {(attacker, target): (dice_count, target_range)}
    attack_table = {
        # Corvette attacks
        ('corvette', 'scout'): (1, 3),           # 1-3 on 1 die
        ('corvette', 'colony_transport'): (1, 3), # 1-3 on 1 die  
        ('corvette', 'corvette'): (1, 1),        # 1 on 1 die
        ('corvette', 'fighter'): (1, 0),         # No kill possible
        ('corvette', 'death_star'): (1, 0),      # No kill possible
        
        # Fighter attacks (superior to corvettes)
        ('fighter', 'scout'): (1, 5),            # 1-5 on 1 die
        ('fighter', 'colony_transport'): (1, 5),  # 1-5 on 1 die
        ('fighter', 'corvette'): (1, 3),         # 1-3 on 1 die
        ('fighter', 'fighter'): (1, 1),          # 1 on 1 die
        ('fighter', 'death_star'): (1, 0),       # No kill possible
        
        # Death Star attacks (most powerful)
        ('death_star', 'scout'): (1, 6),         # Auto-kill
        ('death_star', 'colony_transport'): (1, 6), # Auto-kill
        ('death_star', 'corvette'): (1, 5),      # 1-5 on 1 die
        ('death_star', 'fighter'): (1, 3),       # 1-3 on 1 die
        ('death_star', 'death_star'): (2, 10),   # 10 exactly on 2 dice
    }
    
    return attack_table.get((attacker_type.value.lower(), target_type.value.lower()), (1, 0))

def resolve_detailed_combat(attacker_player, defender_player, attacker_warships, defender_warships, location):
    """
    Resolve detailed combat according to rules 4.1 with turn-by-turn accounting.
    Returns (combat_result, detailed_log)
    """
    import random
    from stellar_conquest.core.enums import ShipType
    
    # Create combat log
    combat_log = []
    combat_log.append(f"\n📜 DETAILED COMBAT LOG - {location}")
    combat_log.append(f"⚔️  Battle between {attacker_player.name} (Attacker) vs {defender_player.name} (Defender)")
    
    # Initialize ship counts for combat (working copies)
    attacker_ships = dict(attacker_warships)
    defender_ships = dict(defender_warships)
    
    # Show initial forces
    att_force = [f"{count} {ship_type.value.lower()}{'s' if count > 1 else ''}" 
                 for ship_type, count in attacker_ships.items()]
    def_force = [f"{count} {ship_type.value.lower()}{'s' if count > 1 else ''}" 
                 for ship_type, count in defender_ships.items()]
    
    combat_log.append(f"🔴 {attacker_player.name} Initial Forces: {', '.join(att_force)}")
    combat_log.append(f"🔵 {defender_player.name} Initial Forces: {', '.join(def_force)}")
    combat_log.append("")
    
    barrage_round = 1
    
    while attacker_ships and defender_ships:
        combat_log.append(f"📊 BARRAGE ROUND {barrage_round}")
        
        # Attacker fires first (rules 4.1.5.c)
        combat_log.append(f"🔴 {attacker_player.name} Fires:")
        attacker_kills = 0
        
        for ship_type, count in list(attacker_ships.items()):
            for i in range(count):
                # Simple AI targeting - target strongest enemy ship available
                if defender_ships:
                    target_ship = max(defender_ships.keys(), 
                                    key=lambda x: {'death_star': 3, 'fighter': 2, 'corvette': 1}.get(x.value.lower(), 0))
                    
                    # Get attack values
                    dice_count, hit_range = get_combat_value(ship_type, target_ship)
                    
                    if hit_range > 0:  # Can actually damage this target
                        if dice_count == 1:
                            roll = random.randint(1, 6)
                            hit = roll <= hit_range
                            combat_log.append(f"   • {ship_type.value.lower()} vs {target_ship.value.lower()}: rolled {roll}, need ≤{hit_range} - {'HIT' if hit else 'MISS'}")
                        else:  # 2 dice, need exactly 10
                            roll1, roll2 = random.randint(1, 6), random.randint(1, 6)
                            total = roll1 + roll2
                            hit = total == 10
                            combat_log.append(f"   • {ship_type.value.lower()} vs {target_ship.value.lower()}: rolled {roll1}+{roll2}={total}, need exactly 10 - {'HIT' if hit else 'MISS'}")
                        
                        if hit:
                            defender_ships[target_ship] -= 1
                            attacker_kills += 1
                            if defender_ships[target_ship] <= 0:
                                del defender_ships[target_ship]
                    else:
                        combat_log.append(f"   • {ship_type.value.lower()} cannot damage {target_ship.value.lower()}")
        
        # Defender fires back (rules 4.1.5.c - destroyed ships still fire)
        combat_log.append(f"🔵 {defender_player.name} Returns Fire:")
        defender_kills = 0
        
        # Use original defender ships for return fire (Rule 4.1.5.c - destroyed ships still fire)
        for ship_type, count in list(defender_warships.items()):
            for i in range(count):
                if attacker_ships:
                    target_ship = max(attacker_ships.keys(),
                                    key=lambda x: {'death_star': 3, 'fighter': 2, 'corvette': 1}.get(x.value.lower(), 0))
                    
                    dice_count, hit_range = get_combat_value(ship_type, target_ship)
                    
                    if hit_range > 0:
                        if dice_count == 1:
                            roll = random.randint(1, 6)
                            hit = roll <= hit_range
                            combat_log.append(f"   • {ship_type.value.lower()} vs {target_ship.value.lower()}: rolled {roll}, need ≤{hit_range} - {'HIT' if hit else 'MISS'}")
                        else:
                            roll1, roll2 = random.randint(1, 6), random.randint(1, 6)
                            total = roll1 + roll2
                            hit = total == 10
                            combat_log.append(f"   • {ship_type.value.lower()} vs {target_ship.value.lower()}: rolled {roll1}+{roll2}={total}, need exactly 10 - {'HIT' if hit else 'MISS'}")
                        
                        if hit:
                            attacker_ships[target_ship] -= 1
                            defender_kills += 1
                            if attacker_ships[target_ship] <= 0:
                                del attacker_ships[target_ship]
                    else:
                        combat_log.append(f"   • {ship_type.value.lower()} cannot damage {target_ship.value.lower()}")
        
        # Update warship counts for next round
        defender_warships = dict(defender_ships)
        attacker_warships = dict(attacker_ships)
        
        # Show round results
        combat_log.append(f"📈 Round {barrage_round} Results: {attacker_player.name} destroyed {attacker_kills} ships, {defender_player.name} destroyed {defender_kills} ships")
        
        if attacker_ships:
            remaining_att = [f"{count} {ship_type.value.lower()}{'s' if count > 1 else ''}" 
                           for ship_type, count in attacker_ships.items()]
            combat_log.append(f"🔴 {attacker_player.name} Remaining: {', '.join(remaining_att)}")
        else:
            combat_log.append(f"🔴 {attacker_player.name}: All ships destroyed")
            
        if defender_ships:
            remaining_def = [f"{count} {ship_type.value.lower()}{'s' if count > 1 else ''}" 
                           for ship_type, count in defender_ships.items()]
            combat_log.append(f"🔵 {defender_player.name} Remaining: {', '.join(remaining_def)}")
        else:
            combat_log.append(f"🔵 {defender_player.name}: All ships destroyed")
        
        combat_log.append("")
        barrage_round += 1
        
        # Optional withdrawal check (simplified - assume both sides fight to the death in simulation)
        if barrage_round > 10:  # Safety valve to prevent infinite combat
            combat_log.append("⏰ Combat continues beyond 10 rounds - both sides withdraw")
            break
    
    # Determine final result
    if not attacker_ships and not defender_ships:
        result = 'mutual_annihilation'
        combat_log.append("💀 MUTUAL ANNIHILATION - Both forces destroyed")
    elif not attacker_ships:
        result = 'defender_victory'
        combat_log.append(f"🛡️  DEFENDER VICTORY - {defender_player.name} retains control")
    elif not defender_ships:
        result = 'attacker_victory'
        combat_log.append(f"⚔️  ATTACKER VICTORY - {attacker_player.name} seizes control")
    else:
        result = 'mutual_withdrawal'
        combat_log.append(f"🤝 MUTUAL WITHDRAWAL - Both sides withdraw")
    
    # Print detailed log to console
    for line in combat_log:
        print(line)
    
    return result, "\n".join(combat_log)

def resolve_ship_combat(game_state, location, attacker_player, defender_player, battle_stats=None):
    """Resolve combat between ships at a location according to rules 4.1."""
    import random

    # Get current turn number for intelligence logging
    current_turn = game_state.turn_number if hasattr(game_state, 'turn_number') else 1
    
    print(f"\n⚔️  COMBAT ENCOUNTER AT {location}")
    print(f"   Attacker: {attacker_player.name}")
    print(f"   Defender: {defender_player.name}")
    
    # Get ships at this location for both players
    attacker_ships = {}
    defender_ships = {}
    
    for group in attacker_player.ship_groups:
        for ship in group.ships:
            if ship.location == location:
                if ship.ship_type not in attacker_ships:
                    attacker_ships[ship.ship_type] = 0
                attacker_ships[ship.ship_type] += ship.count
    
    for group in defender_player.ship_groups:
        for ship in group.ships:
            if ship.location == location:
                if ship.ship_type not in defender_ships:
                    defender_ships[ship.ship_type] = 0
                defender_ships[ship.ship_type] += ship.count
    
    # Display detailed ship inventories for both players
    print(f"\n   📊 SHIP FORCES AT {location}:")
    
    # Show attacker's forces
    attacker_ship_list = []
    for ship_type, count in attacker_ships.items():
        ship_name = ship_type.value.lower()
        attacker_ship_list.append(f"{count} {ship_name}{'s' if count > 1 else ''}")
    print(f"   🔴 {attacker_player.name}: {', '.join(attacker_ship_list) if attacker_ship_list else 'No ships'}")
    
    # Show defender's forces  
    defender_ship_list = []
    for ship_type, count in defender_ships.items():
        ship_name = ship_type.value.lower()
        defender_ship_list.append(f"{count} {ship_name}{'s' if count > 1 else ''}")
    print(f"   🔵 {defender_player.name}: {', '.join(defender_ship_list) if defender_ship_list else 'No ships'}")
    
    # Check if either side has only non-combat ships (Rule 4.1.3)
    from stellar_conquest.core.enums import ShipType
    combat_ship_types = {ShipType.CORVETTE, ShipType.FIGHTER, ShipType.DEATH_STAR}
    
    attacker_warships = {k: v for k, v in attacker_ships.items() if k in combat_ship_types}
    defender_warships = {k: v for k, v in defender_ships.items() if k in combat_ship_types}
    
    # Determine combat result
    combat_result = None
    actual_combat_occurred = False
    
    if not attacker_warships and not defender_warships:
        print(f"   🏃 No warships present - no combat possible")
        combat_result = 'no_combat_possible'
    elif not attacker_warships:
        print(f"   🏃 {attacker_player.name} has no warships - must retreat immediately (Rule 4.1.3)")
        combat_result = 'attacker_retreat'
        
        # Log retreat intelligence - attacker retreated due to no warships
        if attacker_player.name not in intelligence_system.enemy_activity_logs:
            intelligence_system.initialize_player_logs(attacker_player.name)
        intelligence_msg = f"Retreat from {location}: no warships to engage {', '.join(defender_ship_list)}"
        print(f"   📝 Logging retreat intelligence for {attacker_player.name}: {intelligence_msg}")
        intelligence_system.log_enemy_activity(
            attacker_player.name, current_turn, location,
            ActivityType.RETREAT_RECORDED, defender_player.name, intelligence_msg, 2
        )
        
        # Log from defender perspective - enemy retreated
        if defender_player.name not in intelligence_system.enemy_activity_logs:
            intelligence_system.initialize_player_logs(defender_player.name)
        intelligence_msg = f"Enemy retreat at {location}: {', '.join(attacker_ship_list)} withdrew"
        print(f"   📝 Logging retreat intelligence for {defender_player.name}: {intelligence_msg}")
        intelligence_system.log_enemy_activity(
            defender_player.name, current_turn, location,
            ActivityType.RETREAT_RECORDED, attacker_player.name, intelligence_msg, 1
        )
        
    elif not defender_warships:
        print(f"   🏃 {defender_player.name} has no warships - {attacker_player.name} wins immediately")
        combat_result = 'defender_retreat'
        
        # Log victory intelligence - defender retreated due to no warships
        if attacker_player.name not in intelligence_system.enemy_activity_logs:
            intelligence_system.initialize_player_logs(attacker_player.name)
        intelligence_msg = f"Victory at {location}: enemy {', '.join(defender_ship_list)} retreated (no warships)"
        intelligence_system.log_enemy_activity(
            attacker_player.name, current_turn, location,
            ActivityType.RETREAT_RECORDED, defender_player.name, intelligence_msg, 2
        )
        
        # Log from defender perspective - forced to retreat
        if defender_player.name not in intelligence_system.enemy_activity_logs:
            intelligence_system.initialize_player_logs(defender_player.name)
        intelligence_msg = f"Forced retreat from {location}: no warships vs {', '.join(attacker_ship_list)}"
        intelligence_system.log_enemy_activity(
            defender_player.name, current_turn, location,
            ActivityType.RETREAT_RECORDED, attacker_player.name, intelligence_msg, 3
        )
    else:
        # Actual combat between warships
        actual_combat_occurred = True
        print(f"\n   ⚔️  WARSHIP BATTLE:")
        attacker_warship_list = []
        for ship_type, count in attacker_warships.items():
            ship_name = ship_type.value.lower()
            attacker_warship_list.append(f"{count} {ship_name}{'s' if count > 1 else ''}")
        print(f"   🔴 {attacker_player.name} warships: {', '.join(attacker_warship_list)}")
        
        defender_warship_list = []
        for ship_type, count in defender_warships.items():
            ship_name = ship_type.value.lower()
            defender_warship_list.append(f"{count} {ship_name}{'s' if count > 1 else ''}")
        print(f"   🔵 {defender_player.name} warships: {', '.join(defender_warship_list)}")
        
        # Detailed combat resolution according to rules 4.1
        combat_result, detailed_combat_log = resolve_detailed_combat(
            attacker_player, defender_player, attacker_warships, defender_warships, location
        )
    
    # Log intelligence for both players - they've discovered each other's forces
    # Attacker learns about defender's ships - log to global intelligence system
    if attacker_player.name not in intelligence_system.enemy_activity_logs:
        intelligence_system.initialize_player_logs(attacker_player.name)
    if actual_combat_occurred:
        # Log the detailed combat report for the attacker
        intelligence_msg = f"Combat at {location}: {', '.join(defender_ship_list)} - {combat_result}"
        activity_type = ActivityType.ENEMY_SHIPS_ENGAGED
        print(f"   📝 Logging combat intelligence for {attacker_player.name}: {intelligence_msg}")
        intelligence_system.log_enemy_activity(
            attacker_player.name, current_turn, location, activity_type, defender_player.name, intelligence_msg, 3
        )
        # Also log the detailed combat log as a separate entry
        print(f"   📝 Logging detailed combat report for {attacker_player.name}")
        intelligence_system.log_enemy_activity(
            attacker_player.name, current_turn, location, ActivityType.DETAILED_COMBAT_REPORT, 
            defender_player.name, detailed_combat_log, 4
        )
    else:
        intelligence_msg = f"Ship encounter at {location}: {', '.join(defender_ship_list)} - {combat_result}"
        activity_type = ActivityType.ENEMY_SHIPS_DISCOVERED
        intelligence_system.log_enemy_activity(
            attacker_player.name, current_turn, location, activity_type, defender_player.name, intelligence_msg, 3
        )
    
    # Defender learns about attacker's ships - log to global intelligence system
    if defender_player.name not in intelligence_system.enemy_activity_logs:
        intelligence_system.initialize_player_logs(defender_player.name)
    if actual_combat_occurred:
        # Log the detailed combat report for the defender
        intelligence_msg = f"Combat at {location}: {', '.join(attacker_ship_list)} - {combat_result}"
        activity_type = ActivityType.ENEMY_SHIPS_ENGAGED
        print(f"   📝 Logging combat intelligence for {defender_player.name}: {intelligence_msg}")
        intelligence_system.log_enemy_activity(
            defender_player.name, current_turn, location, activity_type, attacker_player.name, intelligence_msg, 3
        )
        # Also log the detailed combat log as a separate entry
        print(f"   📝 Logging detailed combat report for {defender_player.name}")
        intelligence_system.log_enemy_activity(
            defender_player.name, current_turn, location, ActivityType.DETAILED_COMBAT_REPORT, 
            attacker_player.name, detailed_combat_log, 4
        )
    else:
        intelligence_msg = f"Ship encounter at {location}: {', '.join(attacker_ship_list)} - {combat_result}"
        activity_type = ActivityType.ENEMY_SHIPS_DISCOVERED
        intelligence_system.log_enemy_activity(
            defender_player.name, current_turn, location, activity_type, attacker_player.name, intelligence_msg, 3
        )

    # Track battle statistics if battle_stats is provided and actual combat occurred
    if battle_stats and actual_combat_occurred:
        # Both players were in a battle
        if attacker_player.name in battle_stats:
            battle_stats[attacker_player.name]['battles'] += 1
        if defender_player.name in battle_stats:
            battle_stats[defender_player.name]['battles'] += 1

        # Determine winner based on combat_result
        # Combat results are: 'attacker_victory', 'defender_victory', 'mutual_annihilation', 'mutual_withdrawal'
        if combat_result == 'attacker_victory':
            if attacker_player.name in battle_stats:
                battle_stats[attacker_player.name]['victories'] += 1
        elif combat_result == 'defender_victory':
            if defender_player.name in battle_stats:
                battle_stats[defender_player.name]['victories'] += 1
        # Note: mutual_annihilation and mutual_withdrawal don't count as victories for either side

    return True, combat_result

def log_intelligence_encounters(game_state, player, turn_number):
    """Log intelligence for all ship encounters, whether combat occurs or not."""
    # Check all locations where this player has ships
    player_locations = set()
    for group in player.ship_groups:
        for ship in group.ships:
            player_locations.add(ship.location)
    
    
    # For each location, check for enemy ships and log intelligence
    for location in player_locations:
        # Only check star hexes for encounters
        if not is_star_hex(game_state, location):
            continue
            
        enemy_ships = check_enemy_ships_at_location(game_state, location, player)
        
        if enemy_ships:
            # Initialize intelligence logging for current player (only if needed)
            if player.name not in intelligence_system.enemy_activity_logs:
                intelligence_system.initialize_player_logs(player.name)
            
            # Get our ships at this location
            our_ships = {}
            for group in player.ship_groups:
                for ship in group.ships:
                    if ship.location == location:
                        if ship.ship_type not in our_ships:
                            our_ships[ship.ship_type] = 0
                        our_ships[ship.ship_type] += ship.count
            
            # Create ship list for our forces
            our_ship_list = []
            for ship_type, count in our_ships.items():
                ship_name = ship_type.value.lower()
                our_ship_list.append(f"{count} {ship_name}{'s' if count > 1 else ''}")
            
            # Log encounter with each enemy player
            for enemy_id, ships in enemy_ships.items():
                enemy_player = next(p for p in game_state.players if p.player_id == enemy_id)
                
                # Create ship list for enemy forces
                enemy_ship_list = []
                for ship_type, count in ships.items():
                    ship_name = ship_type.value.lower()
                    enemy_ship_list.append(f"{count} {ship_name}{'s' if count > 1 else ''}")
                
                # Log intelligence for current player about enemy encounter
                intelligence_msg = f"Ship encounter at {location}: {', '.join(enemy_ship_list)}"
                print(f"   📝 log_intelligence_encounters: Logging for {player.name}: {intelligence_msg}")
                intelligence_system.log_enemy_activity(
                    player.name, turn_number, location, 
                    ActivityType.ENEMY_SHIPS_DISCOVERED, enemy_player.name, intelligence_msg, 2
                )
                
                # Initialize intelligence logging for enemy player and log mutual encounter
                if enemy_player.name not in intelligence_system.enemy_activity_logs:
                    intelligence_system.initialize_player_logs(enemy_player.name)
                intelligence_msg = f"Ship encounter at {location}: {', '.join(our_ship_list)}"
                print(f"   📝 log_intelligence_encounters: Logging for {enemy_player.name}: {intelligence_msg}")
                intelligence_system.log_enemy_activity(
                    enemy_player.name, turn_number, location, 
                    ActivityType.ENEMY_SHIPS_DISCOVERED, player.name, intelligence_msg, 2
                )

def resolve_combat_phase(game_state, player, turn_number, battle_stats=None):
    """Resolve combat phase according to rules 4.1."""
    print_phase_header(turn_number, "c", "COMBAT RESOLUTION")
    print(f"{player.name} checks for combat opportunities...")
    
    # First, log intelligence for all encounters
    log_intelligence_encounters(game_state, player, turn_number)
    
    combat_occurred = False
    
    # Check all locations where this player has ships
    player_locations = set()
    for group in player.ship_groups:
        for ship in group.ships:
            player_locations.add(ship.location)
    
    # For each location, check for enemy ships
    for location in player_locations:
        # Only combat in star hexes (Rule 3.8.2)
        if not is_star_hex(game_state, location):
            continue
            
        enemy_ships = check_enemy_ships_at_location(game_state, location, player)
        
        if enemy_ships:
            print(f"   ⚔️  Combat situation detected at {location}")
            
            # Rule 4.1.1: Must attack all enemy ships in same star hex
            for enemy_id, ships in enemy_ships.items():
                enemy_player = next(p for p in game_state.players if p.player_id == enemy_id)
                print(f"   🎯 Engaging {enemy_player.name} forces")
                
                # Resolve combat (intelligence logging now happens in log_intelligence_encounters)
                combat_resolved, result = resolve_ship_combat(game_state, location, player, enemy_player, battle_stats)
                if combat_resolved:
                    combat_occurred = True
                    print(f"   📊 Combat result: {result}")
    
    if not combat_occurred:
        print("   No enemy ships encountered this turn")
    else:
        # Show updated intelligence reports after combat
        print(f"\n   📋 Updated Intelligence After Combat:")
        show_intelligence_reports(player)
    
    return combat_occurred

def resolve_colony_attack_combat(attacker_player, defender_player, colony, attacker_warships, location):
    """
    Resolve combat against a colony's missile bases.
    Rules 4.2: Combat against missile bases uses same method as ship combat.
    Missile bases = corvette strength, Advanced missile bases = fighter strength.
    Returns (combat_result, bases_destroyed_count)
    """
    import random
    from stellar_conquest.core.enums import ShipType

    # Check for planet shield (unconquerable)
    if colony.has_planet_shield:
        print(f"   🛡️  Colony has planet shield - UNCONQUERABLE")
        return 'planet_shield', {'missile_bases': 0, 'advanced_missile_bases': 0}

    # Get missile base counts
    missile_bases = colony.missile_bases
    advanced_missile_bases = colony.advanced_missile_bases

    if missile_bases == 0 and advanced_missile_bases == 0:
        # No defenses - instant conquest
        print(f"   ⚡ No defenses - colony conquered immediately!")
        return 'instant_conquest', {'missile_bases': 0, 'advanced_missile_bases': 0}

    # Reveal defenses to attacker (rule 4.2.3)
    print(f"   🛡️  Colony defenses revealed: {missile_bases} missile bases, {advanced_missile_bases} advanced bases")

    # Create combat log
    combat_log = []
    combat_log.append(f"\n📜 COLONY ATTACK COMBAT - {location}")
    combat_log.append(f"⚔️  {attacker_player.name} attacks {defender_player.name}'s colony")

    # Initialize forces
    attacker_ships = dict(attacker_warships)

    # Treat missile bases as corvettes, advanced as fighters (per rules)
    defender_bases = {}
    if missile_bases > 0:
        defender_bases[ShipType.CORVETTE] = missile_bases  # Missile bases = corvette strength
    if advanced_missile_bases > 0:
        defender_bases[ShipType.FIGHTER] = advanced_missile_bases  # Advanced = fighter strength

    # Show initial forces
    att_force = [f"{count} {ship_type.value.lower()}{'s' if count > 1 else ''}"
                 for ship_type, count in attacker_ships.items()]
    def_force = [f"{missile_bases} missile base{'s' if missile_bases > 1 else ''}"] if missile_bases > 0 else []
    if advanced_missile_bases > 0:
        def_force.append(f"{advanced_missile_bases} advanced base{'s' if advanced_missile_bases > 1 else ''}")

    combat_log.append(f"🔴 {attacker_player.name} Forces: {', '.join(att_force)}")
    combat_log.append(f"🔵 Colony Defenses: {', '.join(def_force)}")
    combat_log.append("")

    barrage_round = 1
    bases_destroyed = {'missile_bases': 0, 'advanced_missile_bases': 0}

    while attacker_ships and defender_bases:
        combat_log.append(f"📊 BARRAGE ROUND {barrage_round}")

        # Attacker fires first
        combat_log.append(f"🔴 {attacker_player.name} Fires:")
        attacker_kills = 0

        for ship_type, count in list(attacker_ships.items()):
            for i in range(count):
                if defender_bases:
                    # Target strongest defense first
                    target_type = max(defender_bases.keys(),
                                    key=lambda x: {'fighter': 2, 'corvette': 1}.get(x.value.lower(), 0))

                    dice_count, hit_range = get_combat_value(ship_type, target_type)

                    if hit_range > 0:
                        if dice_count == 1:
                            roll = random.randint(1, 6)
                            hit = roll <= hit_range
                            base_name = "advanced base" if target_type == ShipType.FIGHTER else "missile base"
                            combat_log.append(f"   • {ship_type.value.lower()} vs {base_name}: rolled {roll}, need ≤{hit_range} - {'HIT' if hit else 'MISS'}")
                        else:
                            roll1, roll2 = random.randint(1, 6), random.randint(1, 6)
                            total = roll1 + roll2
                            hit = total == 10
                            base_name = "advanced base" if target_type == ShipType.FIGHTER else "missile base"
                            combat_log.append(f"   • {ship_type.value.lower()} vs {base_name}: rolled {roll1}+{roll2}={total}, need exactly 10 - {'HIT' if hit else 'MISS'}")

                        if hit:
                            defender_bases[target_type] -= 1
                            # Track which type of base was destroyed
                            if target_type == ShipType.FIGHTER:
                                bases_destroyed['advanced_missile_bases'] += 1
                            else:  # CORVETTE = regular missile base
                                bases_destroyed['missile_bases'] += 1
                            attacker_kills += 1
                            if defender_bases[target_type] <= 0:
                                del defender_bases[target_type]

        # Bases fire back
        combat_log.append(f"🔵 Colony Defenses Return Fire:")
        defender_kills = 0

        # Bases fire using same counts (destroyed bases still fire this round per rules 4.1.5.c)
        original_bases = {}
        if missile_bases > 0:
            original_bases[ShipType.CORVETTE] = missile_bases
        if advanced_missile_bases > 0:
            original_bases[ShipType.FIGHTER] = advanced_missile_bases

        for base_type, count in list(original_bases.items()):
            for i in range(count):
                if attacker_ships:
                    # Target strongest ship
                    target_ship = max(attacker_ships.keys(),
                                    key=lambda x: {'death_star': 3, 'fighter': 2, 'corvette': 1}.get(x.value.lower(), 0))

                    dice_count, hit_range = get_combat_value(base_type, target_ship)

                    if hit_range > 0:
                        if dice_count == 1:
                            roll = random.randint(1, 6)
                            hit = roll <= hit_range
                            base_name = "advanced base" if base_type == ShipType.FIGHTER else "missile base"
                            combat_log.append(f"   • {base_name} vs {target_ship.value.lower()}: rolled {roll}, need ≤{hit_range} - {'HIT' if hit else 'MISS'}")
                        else:
                            roll1, roll2 = random.randint(1, 6), random.randint(1, 6)
                            total = roll1 + roll2
                            hit = total == 10
                            base_name = "advanced base" if base_type == ShipType.FIGHTER else "missile base"
                            combat_log.append(f"   • {base_name} vs {target_ship.value.lower()}: rolled {roll1}+{roll2}={total}, need exactly 10 - {'HIT' if hit else 'MISS'}")

                        if hit:
                            attacker_ships[target_ship] -= 1
                            defender_kills += 1
                            if attacker_ships[target_ship] <= 0:
                                del attacker_ships[target_ship]

        # Update base counts for next round
        missile_bases = defender_bases.get(ShipType.CORVETTE, 0)
        advanced_missile_bases = defender_bases.get(ShipType.FIGHTER, 0)

        # Show round results
        combat_log.append(f"📈 Round {barrage_round}: {attacker_kills} defenses destroyed, {defender_kills} ships destroyed")

        if attacker_ships:
            remaining_att = [f"{count} {ship_type.value.lower()}{'s' if count > 1 else ''}"
                           for ship_type, count in attacker_ships.items()]
            combat_log.append(f"🔴 {attacker_player.name} Remaining: {', '.join(remaining_att)}")
        else:
            combat_log.append(f"🔴 {attacker_player.name}: All ships destroyed")

        if defender_bases:
            remaining_def = []
            if missile_bases > 0:
                remaining_def.append(f"{missile_bases} missile base{'s' if missile_bases > 1 else ''}")
            if advanced_missile_bases > 0:
                remaining_def.append(f"{advanced_missile_bases} advanced base{'s' if advanced_missile_bases > 1 else ''}")
            combat_log.append(f"🔵 Colony Defenses Remaining: {', '.join(remaining_def)}")
        else:
            combat_log.append(f"🔵 All defenses destroyed - COLONY CONQUERED")

        combat_log.append("")
        barrage_round += 1

        # Safety valve
        if barrage_round > 10:
            combat_log.append("⏰ Combat exceeds 10 rounds - attacker calls off attack")
            break

    # Determine result
    if not attacker_ships:
        result = 'attacker_eliminated'
        combat_log.append(f"💀 ATTACK FAILED - {attacker_player.name} forces destroyed")
    elif not defender_bases:
        result = 'conquest_successful'
        combat_log.append(f"⚔️  CONQUEST SUCCESSFUL - All defenses destroyed")
    else:
        result = 'attack_called_off'
        combat_log.append(f"🤝 Attack called off - defenses still standing")

    # Print log
    for line in combat_log:
        print(line)

    return result, bases_destroyed

def conquer_colony(game_state, colony, attacker_player, defender_player, location):
    """
    Transfer control of a colony to the attacker.
    Rules 4.2.6 and 4.4: Colony is conquered and comes under attacker's control.
    """
    print(f"   👑 {attacker_player.name} CONQUERS {defender_player.name}'s colony at {location}!")
    print(f"   📊 Colony: {colony.population}M population, {colony.factories} factories")

    # Use the Colony's conquer method
    colony.conquer(attacker_player.player_id)

    # Move colony from defender to attacker
    defender_player.colonies.remove(colony)
    attacker_player.colonies.append(colony)

    return True

def get_guarding_warships(player):
    """
    Identify warships that must remain to guard conquered colonies.
    Returns dict: {location: {ShipType: count}} for minimum guards needed.
    """
    guards_needed = {}

    for colony in player.colonies:
        if colony.is_conquered:
            location = colony.location
            # Need to keep 1-2 warships at each conquered colony
            # Prefer keeping 2 for safety, but minimum 1
            if location not in guards_needed:
                guards_needed[location] = {
                    ShipType.CORVETTE: 1,  # Minimum: 1 corvette
                    ShipType.FIGHTER: 0,
                    ShipType.DEATH_STAR: 0
                }

    return guards_needed

def find_liberation_targets(game_state, player):
    """
    Find player's own conquered/besieged colonies that need liberation.
    Returns list of liberation opportunities with enemy forces present.
    """
    liberation_targets = []

    # Priority 1: Find conquered colonies (owned by enemy)
    for other_player in game_state.players:
        if other_player.player_id == player.player_id:
            continue

        # Check if other_player has conquered any of our colonies
        for colony in other_player.colonies:
            if colony.is_conquered and colony.original_owner == player.player_id:
                location = colony.location

                # Check if there are enemy warships at this location
                enemy_warships = {ShipType.CORVETTE: 0, ShipType.FIGHTER: 0, ShipType.DEATH_STAR: 0}
                for group in other_player.ship_groups:
                    if group.location == location:
                        counts = group.get_ship_counts()
                        enemy_warships[ShipType.CORVETTE] += counts.get(ShipType.CORVETTE, 0)
                        enemy_warships[ShipType.FIGHTER] += counts.get(ShipType.FIGHTER, 0)
                        enemy_warships[ShipType.DEATH_STAR] += counts.get(ShipType.DEATH_STAR, 0)

                total_enemy_warships = sum(enemy_warships.values())
                if total_enemy_warships > 0:
                    liberation_targets.append({
                        'location': location,
                        'colony': colony,
                        'occupier': other_player,
                        'enemy_warships': enemy_warships,
                        'population': colony.population,
                        'status': 'CONQUERED',
                        'priority': 'LIBERATION'
                    })

    # Priority 2: Find besieged colonies (still owned by us but under siege)
    for colony in player.colonies:
        if colony.is_besieged:
            location = colony.location

            # Find who is besieging
            for other_player in game_state.players:
                if other_player.player_id == player.player_id:
                    continue

                enemy_warships = {ShipType.CORVETTE: 0, ShipType.FIGHTER: 0, ShipType.DEATH_STAR: 0}
                for group in other_player.ship_groups:
                    if group.location == location:
                        counts = group.get_ship_counts()
                        enemy_warships[ShipType.CORVETTE] += counts.get(ShipType.CORVETTE, 0)
                        enemy_warships[ShipType.FIGHTER] += counts.get(ShipType.FIGHTER, 0)
                        enemy_warships[ShipType.DEATH_STAR] += counts.get(ShipType.DEATH_STAR, 0)

                total_enemy_warships = sum(enemy_warships.values())
                if total_enemy_warships > 0:
                    liberation_targets.append({
                        'location': location,
                        'colony': colony,
                        'occupier': other_player,
                        'enemy_warships': enemy_warships,
                        'population': colony.population,
                        'status': 'BESIEGED',
                        'priority': 'LIBERATION'
                    })
                    break  # Found the besieger

    return liberation_targets

def get_available_warships_at_location(player, location, guards_needed):
    """
    Calculate warships available for attack at a location, excluding guards.
    """
    # Count all warships at location
    total_warships = {ShipType.CORVETTE: 0, ShipType.FIGHTER: 0, ShipType.DEATH_STAR: 0}
    for group in player.ship_groups:
        if group.location == location:
            counts = group.get_ship_counts()
            total_warships[ShipType.CORVETTE] += counts.get(ShipType.CORVETTE, 0)
            total_warships[ShipType.FIGHTER] += counts.get(ShipType.FIGHTER, 0)
            total_warships[ShipType.DEATH_STAR] += counts.get(ShipType.DEATH_STAR, 0)

    # Subtract guards needed at this location
    if location in guards_needed:
        guards = guards_needed[location]
        for ship_type, guard_count in guards.items():
            total_warships[ship_type] = max(0, total_warships[ship_type] - guard_count)

    return total_warships

def resolve_colony_attacks(game_state, player, turn_number):
    """Resolve colony attack phase."""
    print_phase_header(turn_number, "d", "COLONY ATTACKS")
    print(f"{player.name} checks for colony attack opportunities...")

    attacks_made = False

    # First, identify warships reserved for guarding conquered colonies
    guards_needed = get_guarding_warships(player)
    if guards_needed:
        guard_locations = ', '.join(guards_needed.keys())
        print(f"   🛡️  Guarding conquered colonies at: {guard_locations}")

    # Priority 1: Check for liberation opportunities (own conquered colonies)
    liberation_targets = find_liberation_targets(game_state, player)

    if liberation_targets:
        conquered_count = sum(1 for t in liberation_targets if t.get('status') == 'CONQUERED')
        besieged_count = sum(1 for t in liberation_targets if t.get('status') == 'BESIEGED')

        if conquered_count > 0 and besieged_count > 0:
            print(f"\n   🚩 LIBERATION OPPORTUNITIES: {conquered_count} conquered + {besieged_count} besieged colonies!")
        elif conquered_count > 0:
            print(f"\n   🚩 LIBERATION OPPORTUNITIES: {conquered_count} conquered colony/colonies!")
        else:
            print(f"\n   🚩 LIBERATION OPPORTUNITIES: {besieged_count} besieged colony/colonies!")

        for target in liberation_targets:
            location = target['location']
            colony = target['colony']
            occupier = target['occupier']
            status = target.get('status', 'UNKNOWN')

            star_data = FIXED_STAR_LOCATIONS.get(location, {})
            star_name = star_data.get('starname', location)

            # Check if we have warships at this location
            available_warships = get_available_warships_at_location(player, location, guards_needed)
            total_available = sum(available_warships.values())

            if total_available > 0:
                if status == 'CONQUERED':
                    print(f"\n   ⚔️  LIBERATING conquered colony at {star_name} from {occupier.name}!")
                else:
                    print(f"\n   ⚔️  BREAKING SIEGE at {star_name} (besieged by {occupier.name})!")

                force_desc = ", ".join([f"{count} {ship_type.value.lower()}{'s' if count > 1 else ''}"
                                       for ship_type, count in available_warships.items() if count > 0])
                print(f"   🗡️  Liberation force: {force_desc}")

                # Resolve combat against occupier's forces
                # This will be ship-to-ship combat, handled in combat phase
                # For now, just mark that we attempted liberation
                print(f"   ℹ️  Ship combat with {occupier.name} will be resolved in combat phase")
                # Note: Conquest reverts in check_conquered_colonies_maintenance()
                # Siege lifts in check_besieged_colonies_status() when enemy ships defeated
            else:
                print(f"   ⚠️  Cannot liberate {star_name} - no available warships (guards are busy)")

    # Priority 2: Find conquest opportunities (enemy colonies)
    attack_opportunities = []
    seen_colonies = set()

    for group in player.ship_groups:
        location = group.location

        # Get available warships (excluding guards)
        available_warships = get_available_warships_at_location(player, location, guards_needed)
        has_available_warships = sum(available_warships.values()) > 0

        if not has_available_warships:
            continue

        # Check for enemy colonies at this location
        for other_player in game_state.players:
            if other_player.player_id == player.player_id:
                continue

            for colony in other_player.colonies:
                if colony.location == location:
                    # Skip if this is a liberation target (already handled above)
                    if colony.is_conquered and colony.original_owner == player.player_id:
                        continue

                    colony_id = id(colony)
                    if colony_id in seen_colonies:
                        continue

                    seen_colonies.add(colony_id)

                    attack_opportunities.append({
                        'location': location,
                        'colony': colony,
                        'defender': other_player,
                        'warships': available_warships
                    })

    if not attack_opportunities and not liberation_targets:
        print("   No enemy colonies at locations with available warships")
        return False

    # AI decision: Should we attack?
    for opportunity in attack_opportunities:
        location = opportunity['location']
        colony = opportunity['colony']
        defender = opportunity['defender']
        warships = {k: v for k, v in opportunity['warships'].items() if v > 0}  # Filter out zeros

        star_data = FIXED_STAR_LOCATIONS.get(location, {})
        star_name = star_data.get('starname', location)

        # Decide whether to attack based on play style
        should_attack = False

        if player.play_style.value == "warlord":
            # Warlord: Always attack if colony is weak or undefended
            if colony.missile_bases + colony.advanced_missile_bases <= 1:
                should_attack = True
        else:
            # Others: Only attack if undefended
            if colony.missile_bases == 0 and colony.advanced_missile_bases == 0 and not colony.has_planet_shield:
                should_attack = True

        if should_attack:
            print(f"\n   🎯 Attacking {defender.name}'s colony at {star_name} ({location})")

            force_desc = ", ".join([f"{count} {ship_type.value.lower()}{'s' if count > 1 else ''}"
                                   for ship_type, count in warships.items()])
            print(f"   ⚔️  Attacking force: {force_desc}")

            # Resolve combat
            result, bases_destroyed = resolve_colony_attack_combat(
                player, defender, colony, warships, location
            )

            # Destroy the bases from the colony using the correct method
            if bases_destroyed['missile_bases'] > 0 or bases_destroyed['advanced_missile_bases'] > 0:
                colony.destroy_defenses(
                    missile_bases=bases_destroyed['missile_bases'],
                    advanced_bases=bases_destroyed['advanced_missile_bases']
                )

            # Check if conquest was successful
            if result in ['instant_conquest', 'conquest_successful']:
                conquer_colony(game_state, colony, player, defender, location)
                attacks_made = True
            elif result == 'planet_shield':
                print(f"   ❌ Cannot conquer - planet shield protects colony")
            elif result == 'attacker_eliminated':
                print(f"   ❌ Attack failed - all attacking ships destroyed")
            else:
                print(f"   ⚠️  Attack incomplete - defenses still standing")

    if not attacks_made:
        print("   No attacks initiated this turn")

    return attacks_made

def check_conquered_colonies_maintenance(game_state):
    """
    Check all conquered colonies and revert those without warship protection.
    Rules 4.4.6: Colony reverts to original owner if all warships leave its hex.
    """
    colonies_reverted = []

    for player in game_state.players:
        # Check each conquered colony this player owns
        for colony in list(player.colonies):  # Use list() to allow modification during iteration
            if not colony.is_conquered:
                continue

            location = colony.location

            # Check if player has at least one warship at this location
            has_warship_protection = False
            for group in player.ship_groups:
                if group.location == location:
                    ship_counts = group.get_ship_counts()
                    if (ship_counts.get(ShipType.CORVETTE, 0) > 0 or
                        ship_counts.get(ShipType.FIGHTER, 0) > 0 or
                        ship_counts.get(ShipType.DEATH_STAR, 0) > 0):
                        has_warship_protection = True
                        break

            # If no warship protection, revert to original owner
            if not has_warship_protection and colony.original_owner is not None:
                # Find original owner
                original_owner = next((p for p in game_state.players if p.player_id == colony.original_owner), None)

                if original_owner:
                    star_data = FIXED_STAR_LOCATIONS.get(location, {})
                    star_name = star_data.get('starname', location)

                    print(f"   🔄 {player.name}'s conquered colony at {star_name} REVERTS to {original_owner.name} (no warship protection)")

                    # Revert colony
                    colony.status = ColonyStatus.ACTIVE
                    colony.player_id = colony.original_owner
                    colony.original_owner = None
                    colony.turns_under_control = 0

                    # Move colony from current owner to original owner
                    player.colonies.remove(colony)
                    original_owner.colonies.append(colony)

                    colonies_reverted.append({
                        'colony': colony,
                        'location': location,
                        'conqueror': player.name,
                        'original_owner': original_owner.name
                    })

    return colonies_reverted

def check_besieged_colonies_status(game_state):
    """
    Check all active colonies and update their besieged status.
    Rules 4.3: Colony is under siege if enemy warship is in its hex.
    """
    besieged_changes = []

    for player in game_state.players:
        for colony in player.colonies:
            # Only check active (non-conquered) colonies
            if colony.is_conquered:
                continue

            location = colony.location
            was_besieged = colony.is_besieged

            # Check if there are enemy warships at this location
            has_enemy_warships = False
            besieging_player = None

            for other_player in game_state.players:
                if other_player.player_id == player.player_id:
                    continue

                for group in other_player.ship_groups:
                    if group.location == location:
                        # Check if this group has warships
                        ship_counts = group.get_ship_counts()
                        if (ship_counts.get(ShipType.CORVETTE, 0) > 0 or
                            ship_counts.get(ShipType.FIGHTER, 0) > 0 or
                            ship_counts.get(ShipType.DEATH_STAR, 0) > 0):
                            has_enemy_warships = True
                            besieging_player = other_player
                            break

                if has_enemy_warships:
                    break

            # Update siege status
            if has_enemy_warships and not was_besieged:
                # Colony is now under siege
                colony.status = ColonyStatus.BESIEGED
                star_data = FIXED_STAR_LOCATIONS.get(location, {})
                star_name = star_data.get('starname', location)
                besieged_changes.append({
                    'type': 'besieged',
                    'colony': colony,
                    'location': location,
                    'owner': player.name,
                    'besieger': besieging_player.name
                })
                print(f"   ⚠️  {player.name}'s colony at {star_name} is now UNDER SIEGE by {besieging_player.name}!")

            elif not has_enemy_warships and was_besieged:
                # Siege lifted
                colony.status = ColonyStatus.ACTIVE
                star_data = FIXED_STAR_LOCATIONS.get(location, {})
                star_name = star_data.get('starname', location)
                besieged_changes.append({
                    'type': 'siege_lifted',
                    'colony': colony,
                    'location': location,
                    'owner': player.name
                })
                print(f"   ✅ Siege lifted on {player.name}'s colony at {star_name}")

    return besieged_changes

def debark_colonists(game_state, player, turn_number):
    """Handle colonist debarking phase."""
    print_phase_header(turn_number, "e", "COLONIST DEBARKING")
    
    colonization_attempts = 0
    
    # Find all task forces with colony transports
    for group in player.ship_groups:
        ship_counts = group.get_ship_counts()
        colony_transports = ship_counts.get(ShipType.COLONY_TRANSPORT, 0)
        
        if colony_transports > 0:
            location = group.location
            
            # Check if there's a star at this location
            star_data = FIXED_STAR_LOCATIONS.get(location)
            if star_data:
                star_name = star_data['starname']
                star_color = star_data['color']
                
                # If it's a yellow star (guaranteed planets), auto-explore if not already explored
                if star_color == 'yellow':
                    star_system = game_state.board.star_systems.get(location)
                    if not star_system or not game_state.board.is_system_explored(location, player.player_id):
                        print(f"   🔍 {star_name} at {location}: Auto-exploring yellow star (guaranteed planets)")
                        # Directly create star system with planets for yellow stars (they always have planets)
                        success = auto_explore_yellow_star(game_state, location, star_name, player.player_id)
                        
                        if success:
                            print(f"   ✨ {star_name} exploration successful - planets discovered!")
                        else:
                            print(f"   ❌ {star_name} exploration failed")
                
                # Now attempt colonization
                star_system = game_state.board.star_systems.get(location)
                if star_system and hasattr(star_system, 'planets') and star_system.planets:
                    # Find colonizable planets
                    colonizable_planets = []
                    for planet in star_system.planets:
                        if can_colonize_planet(planet, player, game_state):
                            colonizable_planets.append(planet)
                    
                    if colonizable_planets:
                        print(f"   🏴 {star_name} at {location}: Found {len(colonizable_planets)} colonizable planets")
                        
                        # Deploy ALL transports across available planets
                        transports_remaining = colony_transports
                        planet_index = 0
                        
                        while transports_remaining > 0 and planet_index < len(colonizable_planets):
                            planet = colonizable_planets[planet_index]
                            
                            # Deploy up to planet's max capacity (each transport = 1M population)
                            max_capacity = planet.max_population
                            transports_for_this_planet = min(transports_remaining, max_capacity)
                            
                            if attempt_colonization_with_multiple_transports(game_state, player, group, planet, transports_for_this_planet, turn_number):
                                colonization_attempts += 1
                                print(f"   🏘️ Deployed {transports_for_this_planet}M colonists to planet {planet_index + 1}")
                                
                                # Log intelligence about enemy presence after successful colonization
                                detect_and_log_enemies(game_state, player, location, turn_number)
                            
                            transports_remaining -= transports_for_this_planet
                            planet_index += 1
                        
                        if transports_remaining > 0:
                            print(f"   ⚠️ {transports_remaining} transports couldn't be deployed (all suitable planets full)")
                    else:
                        print(f"   🚫 {star_name}: No colonizable planets available")
                        # Retarget to a new star system with habitable planets
                        retarget_colony_transports(game_state, player, group, location, turn_number)
                else:
                    print(f"   📍 Task force at {location}: Star system not explored or no planets")
            else:
                print(f"   📍 Task force at {location}: No star at this location")
    
    if colonization_attempts == 0:
        print(f"   {player.name} has no colonization opportunities this turn")
        return False
    else:
        print(f"   {player.name} successfully established {colonization_attempts} new colonies")
        return True

def retarget_colony_transports(game_state, player, group, current_location, turn_number):
    """Retarget colony transports to a new star system when current target has no colonizable planets.

    Priority:
    1. Systems with known Terran planets (discovered by scouts)
    2. Systems with known Sub-Terran planets
    3. Unexplored yellow stars (high probability of habitable planets)
    """
    from stellar_conquest.utils.hex_utils import HexGrid
    from stellar_conquest.core.enums import PlanetType

    # Find systems with known habitable planets
    systems_with_terran = []
    systems_with_subterran = []

    # Check explored systems
    if hasattr(game_state.board, 'star_systems'):
        for star_location, star_system in game_state.board.star_systems.items():
            if star_location == current_location:
                continue  # Skip current location

            # Only consider systems this player has explored
            if hasattr(game_state.board, 'explored_systems'):
                if star_location not in game_state.board.explored_systems:
                    continue
                if player.player_id not in game_state.board.explored_systems[star_location]:
                    continue

            # Check for habitable planets
            if hasattr(star_system, 'planets') and star_system.planets:
                for planet in star_system.planets:
                    # Check if planet is colonizable
                    if can_colonize_planet(planet, player, game_state):
                        distance = calculate_hex_distance(current_location, star_location)
                        star_data = FIXED_STAR_LOCATIONS.get(star_location, {})
                        star_name = star_data.get('starname', f'Star_{star_location}')

                        if planet.planet_type == PlanetType.TERRAN:
                            systems_with_terran.append({
                                'location': star_location,
                                'name': star_name,
                                'distance': distance,
                                'planet_type': 'Terran'
                            })
                        elif planet.planet_type == PlanetType.SUB_TERRAN:
                            systems_with_subterran.append({
                                'location': star_location,
                                'name': star_name,
                                'distance': distance,
                                'planet_type': 'Sub-Terran'
                            })
                        break  # Found at least one habitable planet

    # Sort by distance
    systems_with_terran.sort(key=lambda x: x['distance'])
    systems_with_subterran.sort(key=lambda x: x['distance'])

    # Select target (prioritize Terran, then Sub-Terran)
    new_target = None
    if systems_with_terran:
        new_target = systems_with_terran[0]
        print(f"      🎯 Retargeting to {new_target['name']} at {new_target['location']} (known {new_target['planet_type']} planet, {new_target['distance']} hexes)")
    elif systems_with_subterran:
        new_target = systems_with_subterran[0]
        print(f"      🎯 Retargeting to {new_target['name']} at {new_target['location']} (known {new_target['planet_type']} planet, {new_target['distance']} hexes)")
    else:
        # No known habitable planets - target nearest unexplored yellow star
        yellow_stars = find_nearest_yellow_stars(current_location, 15)

        for star_location, distance, name, color in yellow_stars:
            # Skip if already explored or already targeted
            if hasattr(game_state.board, 'explored_systems'):
                if star_location in game_state.board.explored_systems:
                    if player.player_id in game_state.board.explored_systems[star_location]:
                        continue  # Already explored

            new_target = {
                'location': star_location,
                'name': name,
                'distance': distance,
                'planet_type': 'Unknown (yellow star)'
            }
            print(f"      🎯 Retargeting to {new_target['name']} at {new_target['location']} (unexplored yellow star, {new_target['distance']} hexes)")
            break

    if new_target:
        # Create new movement plan
        hex_grid = HexGrid()
        try:
            new_path = hex_grid.find_shortest_path(current_location, new_target['location'])
            if new_path:
                # Find the TF number for this group
                tf_number = group.task_force_id if hasattr(group, 'task_force_id') else None

                # If we can't find TF number from group, look for it in ships
                if tf_number is None and group.ships:
                    tf_number = group.ships[0].task_force_id

                if tf_number is not None:
                    # Update movement plan
                    if not hasattr(game_state, 'movement_plans'):
                        game_state.movement_plans = {}
                    if player.player_id not in game_state.movement_plans:
                        game_state.movement_plans[player.player_id] = {}

                    game_state.movement_plans[player.player_id][tf_number] = {
                        'planned_path': new_path,
                        'path_index': 0,
                        'final_destination': new_target['location'],
                        'target_name': new_target['name'],
                        'can_move_this_turn': False,  # Already moved this turn
                        'mission_type': 'colonization'
                    }

                    turns_to_reach = (new_target['distance'] + player.current_ship_speed - 1) // player.current_ship_speed
                    print(f"      ✅ New colonization target set - ETA {turns_to_reach} turns")
                else:
                    print(f"      ⚠️  Could not retarget: unable to find task force number")
        except Exception as e:
            print(f"      ⚠️  Could not retarget: {e}")
    else:
        print(f"      ⚠️  No suitable colonization targets found")

def can_colonize_planet(planet, player, game_state):
    """Check if a planet can be colonized by the player."""
    from stellar_conquest.core.enums import PlanetType, Technology
    
    # Check if planet already has a colony
    existing_colony = None
    for colony in player.colonies:
        if colony.planet.location == planet.location and colony.planet == planet:
            existing_colony = colony
            break
    
    # Check for enemy colonies on this planet
    for other_player in game_state.players:
        if other_player.player_id != player.player_id:
            for colony in other_player.colonies:
                if colony.planet.location == planet.location and colony.planet == planet:
                    print(f"     🚫 Planet has enemy colony, cannot colonize")
                    return False
    
    # Check if it's a barren planet and player has C.E.T.
    if planet.planet_type == PlanetType.BARREN:
        # TODO: Check if player has Controlled Environment Technology
        has_cet = False  # For now, assume no C.E.T.
        if not has_cet:
            print(f"     🚫 Barren planet requires C.E.T. technology")
            return False
    
    # If we already have a colony, we can add population (expand existing colony)
    if existing_colony:
        if existing_colony.population < planet.max_population:
            return True
        else:
            print(f"     🚫 Colony already at maximum population ({planet.max_population})")
            return False
    
    # New colony can be established
    return True

def attempt_colonization_with_multiple_transports(game_state, player, task_force_group, planet, transport_count, turn_number):
    """Attempt to establish a colony or add population using multiple transports."""
    from stellar_conquest.entities.colony import Colony
    
    # Each colony transport carries 1 million population
    total_population = transport_count * 1
    
    print(f"     🚀 Deploying {transport_count} transports with {total_population}M colonists")
    
    # Check if we already have a colony on this planet
    existing_colony = None
    for colony in player.colonies:
        if colony.planet.location == planet.location:
            existing_colony = colony
            break
    
    if existing_colony:
        # Add population to existing colony
        space_available = planet.max_population - existing_colony.population
        population_to_add = min(total_population, space_available)
        
        if population_to_add > 0:
            existing_colony.population += population_to_add
            transports_used = population_to_add  # 1 transport per 1M population
            print(f"     ✅ Added {population_to_add}M population to existing colony (now {existing_colony.population}M)")
            
            # Remove used transports from task force
            remove_transport_from_task_force(task_force_group, transports_used)
            return True
        else:
            print(f"     🚫 Colony already at maximum capacity")
            return False
    else:
        # Create new colony
        try:
            # Ensure population doesn't exceed planet capacity
            initial_population = min(total_population, planet.max_population)
            transports_used = initial_population  # 1 transport per 1M population
            
            new_colony = Colony(
                planet=planet,
                population=initial_population,
                player_id=player.player_id
            )
            player.colonies.append(new_colony)
            
            print(f"     ✅ Established new colony with {initial_population}M population")
            
            # Add command post for this player at this star system
            add_command_post(game_state, player.player_id, planet.location)
            
            # Remove used transports from task force
            remove_transport_from_task_force(task_force_group, transports_used)
            return True
            
        except Exception as e:
            print(f"     ❌ Failed to create colony: {e}")
            return False

def attempt_colonization(game_state, player, task_force_group, planet, turn_number):
    """Attempt to establish a colony or add population to existing colony."""
    from stellar_conquest.entities.colony import Colony
    
    # Each colony transport carries 1 million population
    population_to_debark = 1
    
    # Check if we already have a colony on this planet
    existing_colony = None
    for colony in player.colonies:
        if colony.planet.location == planet.location and colony.planet == planet:
            existing_colony = colony
            break
    
    if existing_colony:
        # Add population to existing colony
        excess = existing_colony.add_population(population_to_debark)
        actual_added = population_to_debark - excess
        
        if actual_added > 0:
            print(f"   🏘️  Added {actual_added} million population to existing colony at {planet.location}")
            print(f"       Colony now has {existing_colony.population} million population")
            
            # Remove one colony transport (it's been used)
            remove_transport_from_task_force(task_force_group, 1)
            return True
        else:
            print(f"   🚫 Colony at {planet.location} is already at maximum capacity")
            return False
    else:
        # Establish new colony
        new_colony = Colony(
            planet=planet,
            population=population_to_debark,
            player_id=player.player_id
        )
        
        player.colonies.append(new_colony)
        
        print(f"   🏗️  Established new colony at {planet.location}")
        print(f"       Planet: {planet.planet_type.value} (max pop: {planet.max_population} million)")
        print(f"       Starting population: {population_to_debark} million")
        
        # Remove one colony transport (it's been used)
        remove_transport_from_task_force(task_force_group, 1)
        return True

def auto_explore_yellow_star(game_state, location, star_name, player_id):
    """Directly explore a yellow star using actual star card data."""
    try:
        from stellar_conquest.entities.planet import Planet, StarSystem
        from stellar_conquest.core.enums import PlanetType, StarColor
        
        # Yellow star cards (numbers 24-43 from the star card table)
        yellow_star_cards = [
            # Format: [card_number, [planets...]]
            # Each planet: [orbit, planet_type, max_pop, is_mineral_rich]
            [24, [[3, 'terran', 80, False], [4, 'sub_terran', 40, False]]],
            [25, [[3, 'terran', 80, False]]],
            [26, [[5, 'terran', 60, False]]],
            [27, [[3, 'minimal_terran', 40, False], [4, 'barren', 20, True]]],
            [28, [[3, 'terran', 80, False]]],
            [29, [[3, 'terran', 60, False]]],
            [30, [[5, 'terran', 60, False]]],
            [31, [[2, 'minimal_terran', 40, False]]],
            [32, [[4, 'terran', 80, False], [5, 'barren', 10, False]]],
            [33, [[3, 'terran', 60, False]]],
            [34, [[5, 'terran', 40, False]]],
            [35, [[3, 'barren', 20, False]]],
            [36, [[4, 'terran', 80, False]]],
            [37, [[3, 'barren', 20, False], [4, 'terran', 60, False]]],
            [38, [[3, 'sub_terran', 40, False], [4, 'minimal_terran', 20, False]]],
            [39, [[4, 'minimal_terran', 20, False], [5, 'terran', 60, False]]],
            [40, [[4, 'terran', 80, False], [5, 'barren', 10, False]]],
            [41, [[4, 'sub_terran', 60, False], [5, 'barren', 10, True]]],
            [42, [[5, 'terran', 60, False]]],
            [43, [[4, 'terran', 80, False]]],
        ]
        
        # Randomly select a yellow star card
        import random
        card_number, planet_data = random.choice(yellow_star_cards)
        
        # Create the star system
        star_system = StarSystem(location=location, star_color=StarColor.YELLOW, name=star_name)
        star_system.star_card_number = card_number
        star_system.explore(player_id, card_number)
        
        # Create planets from the star card data
        planet_type_map = {
            'terran': PlanetType.TERRAN,
            'sub_terran': PlanetType.SUB_TERRAN,
            'minimal_terran': PlanetType.MINIMAL_TERRAN,
            'barren': PlanetType.BARREN
        }
        
        for orbit, planet_type_str, max_pop, is_mineral_rich in planet_data:
            planet_type = planet_type_map[planet_type_str]
            planet = Planet(
                location=location,
                planet_type=planet_type,
                max_population=max_pop,
                is_mineral_rich=is_mineral_rich,
                orbit=orbit,
                star_color=StarColor.YELLOW
            )
            star_system.add_planet(planet)
        
        # Add to game board
        game_state.board.star_systems[location] = star_system
        
        # Debug output
        planet_descriptions = []
        for planet in star_system.planets:
            mineral_str = " (mineral-rich)" if planet.is_mineral_rich else ""
            planet_descriptions.append(f"orbit {planet.orbit}: {planet.planet_type.value} (max {planet.max_population}M){mineral_str}")
        
        print(f"   🌟 Yellow star {star_name} explored - Card #{card_number} drawn")
        print(f"      Planets: {', '.join(planet_descriptions)}")
        
        return True
        
    except Exception as e:
        print(f"   ⚠️ Error creating star system: {e}")
        import traceback
        traceback.print_exc()
        return False

def remove_transport_from_task_force(task_force_group, count):
    """Remove colony transports from a task force after colonization."""
    # Find and remove colony transports
    transports_removed = 0
    ships_to_remove = []
    
    for ship in task_force_group.ships:
        if ship.ship_type == ShipType.COLONY_TRANSPORT and transports_removed < count:
            ships_to_remove.append(ship)
            transports_removed += 1
    
    for ship in ships_to_remove:
        task_force_group.ships.remove(ship)
    
    print(f"       🚢 Removed {transports_removed} colony transport(s) from task force")

def add_command_post(game_state, player_id, location):
    """Add a command post for a player at the specified star system location.

    Note: Per Rule 4.3.2, besieged colonies cannot be used as command posts.
    This is enforced by preventing ship orders that exceed 8-hex range from besieged colonies.
    """
    # Initialize command post tracking if not exists
    if not hasattr(game_state, 'command_posts'):
        game_state.command_posts = {}  # location -> set of player_ids

    # Add this location if not exists
    if location not in game_state.command_posts:
        game_state.command_posts[location] = set()

    # Check if player already has a command post here
    if player_id not in game_state.command_posts[location]:
        game_state.command_posts[location].add(player_id)
        player_name = game_state.get_player_by_id(player_id).name
        print(f"       📡 Command post established for {player_name} at {location}")
    else:
        # Player already has command post here - no additional message needed
        pass

def has_command_post(game_state, player_id, location):
    """Check if a player has a command post at the specified location."""
    if not hasattr(game_state, 'command_posts'):
        return False
    return location in game_state.command_posts and player_id in game_state.command_posts[location]

def show_production_choices(game_state, player):
    """Execute full production phase for a player."""
    print(f"\n🏭 {player.name}'s Production Phase:")
    
    # Step 0: Colony Summary - List all colonized planets and current populations
    print(f"\n   🏛️ Current Colonies:")
    
    if not player.colonies:
        print(f"     No colonies established yet")
    else:
        total_population = 0
        total_factories = 0
        for colony in player.colonies:
            planet_type = colony.planet.planet_type.value
            max_pop = colony.planet.max_population
            mineral_status = " (Mineral Rich)" if colony.planet.is_mineral_rich else ""
            factories_text = f", {colony.factories} factories" if colony.factories > 0 else ""
            print(f"     {colony.location} ({planet_type}{mineral_status}): {colony.population}M population{factories_text} [capacity {max_pop}M]")
            total_population += colony.population
            total_factories += colony.factories
        
        print(f"   📊 Total Empire: {total_population}M population across {len(player.colonies)} colonies, {total_factories} factories")
    
    # Step 0b: Ship Inventory and Locations
    print(f"\n   🚢 Fleet Status:")
    ship_totals = {}
    ship_locations = {}
    
    for i, group in enumerate(player.ship_groups):
        tf_number = i + 1
        location = group.location
        ship_counts = group.get_ship_counts()
        
        if any(count > 0 for count in ship_counts.values()):
            ship_summary = []
            for ship_type, count in ship_counts.items():
                if count > 0:
                    ship_name = ship_type.value.lower()
                    ship_summary.append(f"{count} {ship_name}{'s' if count > 1 else ''}")
                    # Add to totals
                    if ship_name not in ship_totals:
                        ship_totals[ship_name] = 0
                    ship_totals[ship_name] += count
                    # Track locations
                    if ship_name not in ship_locations:
                        ship_locations[ship_name] = []
                    ship_locations[ship_name].extend([location] * count)
            
            if ship_summary:
                print(f"     TF{tf_number} at {location}: {', '.join(ship_summary)}")
    
    if ship_totals:
        total_ships = sum(ship_totals.values())
        ship_summary = []
        for ship_type, count in ship_totals.items():
            ship_summary.append(f"{count} {ship_type}{'s' if count > 1 else ''}")
        print(f"   📊 Total Fleet: {total_ships} ships ({', '.join(ship_summary)})")
    else:
        print(f"     No ships remaining in fleet")
    
    # Step 0c: Enemy Intelligence Report
    show_intelligence_reports(player)
    
    # Step 1: Population Growth (always check and report)
    print(f"\n   🌱 Population Growth Check:")
    
    if not player.colonies:
        print(f"     No colonies established yet - no population growth possible this turn")
        print(f"   No colonies - no IP production this turn")
        return
    
    total_growth = 0
    colony_growth_data = {}  # Store actual growth applied for emigration calculations
    
    for colony in player.colonies:
        old_pop = colony.population
        growth = calculate_population_growth(colony)
        colony.population += growth
        total_growth += growth
        
        # Store the actual growth applied for this colony
        colony_growth_data[colony.location] = growth
        
        planet_type = colony.planet.planet_type.value
        max_pop = colony.planet.max_population
        if growth > 0:
            print(f"     {colony.location} ({planet_type}): Population grows from {old_pop}M to {colony.population}M (+{growth}M) [capacity {max_pop}M]")
        else:
            print(f"     {colony.location} ({planet_type}): No growth possible ({old_pop}M population) [capacity {max_pop}M]")
    
    if total_growth > 0:
        print(f"   📊 Total population growth: +{total_growth}M across all colonies")
    else:
        print(f"   📊 No population growth was possible this production phase")
    
    # Step 2: Calculate IP Production
    total_ip = 0
    colony_ip_breakdown = []
    
    for colony in player.colonies:
        # Base IP from population and factories
        pop_ip = colony.population * IP_PER_POPULATION
        factory_ip = colony.factories * IP_PER_FACTORY
        base_ip = pop_ip + factory_ip
        
        # Apply mineral rich bonus if applicable
        planet_type = colony.planet.planet_type.value
        if colony.planet.is_mineral_rich:
            final_ip = base_ip * MINERAL_RICH_MULTIPLIER
            colony_ip_breakdown.append(f"{colony.location} ({planet_type}): {final_ip}IP ({base_ip}IP × {MINERAL_RICH_MULTIPLIER} mineral rich)")
        else:
            final_ip = base_ip
            colony_ip_breakdown.append(f"{colony.location} ({planet_type}): {final_ip}IP ({colony.population}M pop + {colony.factories} factories)")
        
        total_ip += final_ip
    
    print(f"\n   💰 Industrial Points Production:")
    for breakdown in colony_ip_breakdown:
        print(f"     {breakdown}")
    print(f"   📊 Total IP Available: {total_ip}")
    
    # Step 3: Emigration Decisions (if colonies are getting crowded)
    emigration_transports = plan_emigration(player, total_ip, colony_growth_data, game_state)
    remaining_ip = total_ip - emigration_transports
    
    # Step 4: Factory Construction (if player has Industrial Technology)
    factory_cost = build_factories(player, remaining_ip)
    remaining_ip -= factory_cost
    
    # Step 5: Display Current Research Status
    display_research_status(player)
    
    # Step 6: Spend Remaining IP on Research and Ships
    spending_decisions = make_production_spending(player, remaining_ip)
    
    # Step 6: Execute the decisions
    execute_production_decisions(game_state, player, spending_decisions)


def calculate_factory_spending_limit(player, available_ip):
    """Calculate strategic limit for factory spending based on player strategy and game state."""
    
    # Base spending percentage by strategy
    strategy_limits = {
        'expansionist': 0.30,    # 30% - moderate factory investment for growth
        'warlord': 0.15,         # 15% - minimal factories, focus on military
        'technophile': 0.40,     # 40% - higher factory investment for research funding
        'balanced': 0.25         # 25% - balanced approach
    }
    
    base_percentage = strategy_limits.get(player.play_style.value, 0.25)
    
    # Adjust based on current economic development
    total_colonies = len(player.colonies)
    total_factories = sum(colony.factories for colony in player.colonies)
    
    # Early game (few colonies) - higher factory investment
    if total_colonies <= 2:
        base_percentage += 0.15  # +15% early game bonus
    elif total_colonies <= 4:
        base_percentage += 0.10  # +10% mid-early game bonus
    
    # Late game adjustment - reduce factory building if already well-developed
    if total_factories >= total_colonies * 3:  # Average 3+ factories per colony
        base_percentage *= 0.5  # Cut factory spending in half
    elif total_factories >= total_colonies * 2:  # Average 2+ factories per colony
        base_percentage *= 0.7  # Reduce by 30%
    
    # Minimum and maximum limits
    base_percentage = max(0.10, min(0.50, base_percentage))  # Between 10-50%
    
    # Calculate actual IP limit
    spending_limit = int(available_ip * base_percentage)
    
    # Ensure at least one factory can be built if we have the tech and IP
    if spending_limit < 4 and available_ip >= 8:
        spending_limit = 4  # At least one factory if we can afford it
    
    return spending_limit


def build_factories(player, available_ip):
    """Build factories on colonies where beneficial, prioritizing by strategic value."""
    from stellar_conquest.core.enums import Technology
    
    if not player.can_build_factories():
        return 0  # No factory building capability
    
    print(f"\n   🏭 Factory Construction Assessment:")
    
    if not player.colonies:
        print(f"     No colonies available for factory construction")
        return 0
    
    # Constants for factory building
    FACTORY_COST = 4  # 4 IP per factory according to rules
    factory_limit_per_million = player.get_factory_limit_per_population()
    
    # Strategic spending limits based on available IP and game phase
    max_factory_spending = calculate_factory_spending_limit(player, available_ip)
    
    total_cost = 0
    construction_plans = []
    
    # Assess each colony for factory building potential
    for colony in player.colonies:
        planet_type = colony.planet.planet_type.value
        max_factories = colony.population * factory_limit_per_million if factory_limit_per_million else float('inf')
        current_factories = colony.factories
        
        # Calculate how many factories we can still build
        if factory_limit_per_million is None:  # Robotic Industry
            max_buildable = (available_ip - total_cost) // FACTORY_COST  # Build as many as IP allows
            tech_info = "Robotic Industry (unlimited)"
        else:
            available_slots = max_factories - current_factories
            max_buildable = min(available_slots, (available_ip - total_cost) // FACTORY_COST)
            if factory_limit_per_million == 1:
                tech_info = "Industrial Technology (1 per million)"
            elif factory_limit_per_million == 2:
                tech_info = "Improved Industrial Technology (2 per million)"
            else:
                tech_info = f"Unknown ({factory_limit_per_million} per million)"
        
        # Strategic priority: Mineral-rich planets get highest priority
        # Then planets with no growth potential (Minimal-Terran, Barren)
        # Finally other planets
        priority_score = 0
        
        if colony.planet.is_mineral_rich:
            priority_score += 100  # Highest priority - mineral rich doubles IP output
            priority_reason = "mineral-rich planet (2× IP bonus)"
        elif planet_type in ["Minimal-Terran", "Barren"]:
            priority_score += 50   # High priority - no population growth alternative
            priority_reason = "no population growth alternative"
        else:
            priority_score += 10   # Normal priority - population can still grow
            priority_reason = "general economic benefit"
        
        # Add current IP contribution to prioritize larger economies
        current_contribution = colony.population + current_factories
        if colony.planet.is_mineral_rich:
            current_contribution *= 2
        priority_score += current_contribution
        
        if max_buildable > 0:
            construction_plans.append({
                'colony': colony,
                'max_buildable': max_buildable,
                'priority_score': priority_score,
                'priority_reason': priority_reason,
                'current_factories': current_factories,
                'max_factories': max_factories,
                'planet_type': planet_type
            })
    
    if not construction_plans:
        print(f"     No factory construction opportunities available")
        print(f"     Technology: {tech_info}")
        return 0
    
    # Sort by priority (highest first)
    construction_plans.sort(key=lambda x: x['priority_score'], reverse=True)
    
    print(f"     Technology: {tech_info}")
    print(f"     Available IP for factories: {available_ip - total_cost}")
    
    factories_built = 0
    
    # Build factories in priority order, respecting spending limit
    print(f"     Maximum factory spending this turn: {max_factory_spending} IP")
    
    for plan in construction_plans:
        colony = plan['colony']
        remaining_budget = min(max_factory_spending - total_cost, available_ip - total_cost)
        max_buildable = min(plan['max_buildable'], remaining_budget // FACTORY_COST)
        
        if max_buildable > 0:
            cost = max_buildable * FACTORY_COST
            colony.factories += max_buildable
            total_cost += cost
            factories_built += max_buildable
            
            print(f"     ✅ {colony.location} ({plan['planet_type']}): Built {max_buildable} factories for {cost} IP")
            print(f"        → Reason: {plan['priority_reason']}")
            print(f"        → Factories: {plan['current_factories']} → {colony.factories} (max: {plan['max_factories']:.0f})")
            
            # Check if we've hit our strategic spending limit
            if total_cost >= max_factory_spending:
                print(f"        → Reached strategic factory spending limit ({max_factory_spending} IP)")
                break
            
            remaining_ip_after = available_ip - total_cost
            if remaining_ip_after < FACTORY_COST:
                print(f"        → Insufficient IP remaining for more factories ({remaining_ip_after} IP left)")
                break
    
    if factories_built > 0:
        print(f"   📊 Factory Construction Summary: Built {factories_built} factories for {total_cost} IP")
        print(f"     🏭 Economic Impact: +{factories_built} IP per turn from new factories")
    else:
        print(f"     No factories built this turn")
    
    return total_cost

def display_research_status(player):
    """Display player's current research status before making new investments."""
    from stellar_conquest.core.enums import Technology
    
    print(f"\n   🔬 Current Research Status:")
    
    # Display completed technologies
    if player.completed_technologies:
        print(f"     ✅ Completed Technologies:")
        for tech in sorted(player.completed_technologies, key=lambda t: t.value):
            tech_name = tech.value.replace('_', ' ').title()
            print(f"       • {tech_name}")
    else:
        print(f"     ✅ No technologies completed yet")
    
    # Display ongoing research investments (if any)
    if hasattr(player, 'research_investments') and player.research_investments:
        print(f"     🔬 Ongoing Research Investments:")
        for tech, invested_ip in player.research_investments.items():
            total_cost = player.get_technology_cost(tech)
            remaining_cost = total_cost - invested_ip
            tech_name = tech.value.replace('_', ' ').title()
            print(f"       • {tech_name}: {invested_ip}/{total_cost} IP invested ({remaining_cost} IP remaining)")
    else:
        print(f"     🔬 No ongoing research investments")

def select_banking_research(player, available_ip):
    """Select the best research technology to invest leftover IP in for banking."""
    from stellar_conquest.core.enums import Technology
    
    # Priority order for banking research based on strategic value
    research_priorities = [
        Technology.INDUSTRIAL_TECHNOLOGY,  # Economic boost - highest priority
        Technology.CONTROLLED_ENVIRONMENT_TECH,  # Allows barren planet colonization
        Technology.FIGHTER_SHIP,      # Always valuable for military
        Technology.SPEED_4_HEX,       # Next speed level if player has Speed 3
        Technology.MISSILE_BASE,      # Defensive capability
        Technology.SPEED_5_HEX,       # Higher speed levels
        Technology.IMPROVED_INDUSTRIAL_TECH,
        Technology.ADVANCED_MISSILE_BASE,
        Technology.UNLIMITED_SHIP_RANGE,
        Technology.UNLIMITED_SHIP_COMMUNICATION,
        Technology.DEATH_STAR,
        Technology.PLANET_SHIELD,
        Technology.ROBOTIC_INDUSTRY,
        Technology.IMPROVED_SHIP_WEAPONRY
    ]
    
    # If player already has partial investment, prioritize completing it
    if hasattr(player, 'research_progress') and player.research_progress:
        for progress in player.research_progress.values():
            tech = progress.technology
            # Don't invest in technologies that are already completed
            if tech in player.completed_technologies:
                continue
            if not progress.completed:
                remaining_cost = player.get_technology_cost(tech) - progress.invested_ip
                if remaining_cost > 0:  # Still needs more investment
                    tech_name = tech.value.replace('_', ' ').title()
                    print(f"     🎯 Continuing investment in {tech_name} (need {remaining_cost} more IP)")
                    return tech
    
    # Otherwise, find the first technology the player can research
    for tech in research_priorities:
        if player.can_research_technology(tech):
            return tech
    
    # No valid research found
    return None

def calculate_population_growth(colony):
    """Calculate population growth for a colony based on planet type per rules 6.2."""
    if colony.population == 0:
        return 0
    
    # Population growth rules from rules.txt section 6.2:
    # - Terran: 1M growth per 5M population
    # - Sub-Terran: 1M growth per 10M population  
    # - Minimal-Terran: NO growth
    # - Barren: NO growth
    
    planet_type = colony.planet.planet_type.value
    
    if planet_type == "terran":
        # 1 million growth per 5 million population (integer division)
        growth = colony.population // TERRAN_GROWTH_RATE
    elif planet_type == "sub_terran":
        # 1 million growth per 10 million population (integer division)
        growth = colony.population // SUB_TERRAN_GROWTH_RATE
    elif planet_type in ["minimal_terran", "barren"]:
        # No population growth allowed on minimal-terran or barren planets
        return 0
    else:
        # Unknown planet type - no growth
        print(f"Warning: Unknown planet type '{planet_type}' - no growth applied")
        return 0
    
    # Rule 6.2.4: Population can never exceed planet capacity
    max_growth = colony.planet.max_population - colony.population
    return min(growth, max_growth)

def plan_emigration(player, total_ip, colony_growth_data, game_state=None):
    """Plan emigration with population bonus system and create actual task forces for new colonies."""
    total_emigration_cost = 0
    emigration_task_forces = []
    
    # Check for colonies that can benefit from emigration
    emigration_candidates = []
    for colony in player.colonies:
        # Use the actual growth that was applied this turn (from stored data)
        growth_this_turn = colony_growth_data.get(colony.location, 0)
        
        # Calculate bonus limit: growth + 3M (per rules 6.4.a)
        bonus_limit = growth_this_turn + 3
        
        if bonus_limit > 0:  # Only consider if there's a bonus limit
            emigration_candidates.append((colony, growth_this_turn, bonus_limit))
    
    if emigration_candidates:
        print(f"\n   🚀 Emigration Planning and Task Force Creation:")
        
        # Find colonization targets from discovered star systems
        colonization_targets = find_emigration_targets(player, game_state)
        
        if not colonization_targets:
            print(f"     No suitable colonization targets found in discovered systems")
            return 0
        
        target_index = 0
        next_tf_number = len(player.ship_groups) + 1
        
        for colony, growth, bonus_limit in emigration_candidates:
            # Strategic emigration: Use full bonus limit for maximum population bonus
            planned_emigrants = min(bonus_limit, colony.population - 1)  # Keep at least 1M on planet
            planned_emigrants = min(planned_emigrants, total_ip - total_emigration_cost)  # Limited by available IP
            
            if planned_emigrants > 0 and target_index < len(colonization_targets):
                # Calculate population bonus: +1M for every 3M emigrated (up to bonus limit)
                bonus_population = min(planned_emigrants // 3, bonus_limit // 3)
                total_emigrants = planned_emigrants + bonus_population
                
                # Cost: 1 IP per 1M population (including bonus population)
                emigration_cost = total_emigrants  # 1 transport per 1M population
                
                if emigration_cost <= (total_ip - total_emigration_cost):
                    target_location, target_name, target_distance = colonization_targets[target_index]
                    
                    total_emigration_cost += emigration_cost
                    print(f"     {colony.location}: Bonus limit {bonus_limit}M (growth {growth}M + 3M)")
                    print(f"       Emigrating {planned_emigrants}M → gain {bonus_population}M bonus = {total_emigrants}M total")
                    print(f"       Cost: {emigration_cost} IP ({emigration_cost} transports needed)")
                    print(f"       Target: {target_name} at {target_location} ({target_distance} hexes away)")
                    
                    # Create emigration task force
                    emigration_tf = create_emigration_task_force(
                        player, colony, target_location, target_name, 
                        total_emigrants, next_tf_number, game_state
                    )
                    
                    if emigration_tf:
                        emigration_task_forces.append(emigration_tf)
                        next_tf_number += 1
                        target_index += 1
                        
                        # Remove emigrants from source colony
                        colony.population -= planned_emigrants
                        print(f"       📉 {colony.location} population reduced from {colony.population + planned_emigrants}M to {colony.population}M")
                    
                else:
                    print(f"     {colony.location}: Bonus limit {bonus_limit}M but insufficient IP")
            else:
                if planned_emigrants <= 0:
                    print(f"     {colony.location}: Bonus limit {bonus_limit}M but no emigration planned")
                else:
                    print(f"     {colony.location}: Bonus limit {bonus_limit}M but no more colonization targets")
    
    if total_emigration_cost > 0:
        print(f"   💰 Total emigration cost: {total_emigration_cost} IP")
        if emigration_task_forces:
            print(f"   🚀 Created {len(emigration_task_forces)} emigration task forces")
    
    return total_emigration_cost

def find_emigration_targets(player, game_state):
    """Find suitable colonization targets from discovered star systems."""
    if not game_state or not hasattr(game_state, 'board'):
        return []
    
    from stellar_conquest.utils.hex_utils import calculate_hex_distance
    from stellar_conquest.core.enums import PlanetType
    
    targets = []
    
    # Look through all discovered star systems
    for location, star_system in game_state.board.star_systems.items():
        # Check if this player has explored this system
        if hasattr(game_state.board, 'explored_systems'):
            explorers = game_state.board.explored_systems.get(location, set())
            if player.player_id not in explorers:
                continue  # Player hasn't explored this system
        
        # Check if system has colonizable planets
        for planet in star_system.planets:
            # Skip barren planets unless player has Controlled Environment Technology
            if planet.planet_type == PlanetType.BARREN:
                if not hasattr(player, 'completed_technologies') or not any(
                    'CONTROLLED_ENVIRONMENT' in tech.value for tech in player.completed_technologies
                ):
                    continue
            
            # Check if planet is already colonized
            already_colonized = False
            for check_player in game_state.players:
                for colony in check_player.colonies:
                    if colony.location == location:
                        already_colonized = True
                        break
                if already_colonized:
                    break
            
            if not already_colonized:
                # Find distance from any of player's colonies (closest one)
                min_distance = float('inf')
                for colony in player.colonies:
                    distance = calculate_hex_distance(colony.location, location)
                    min_distance = min(min_distance, distance)
                
                # Only consider targets within reasonable range
                if min_distance <= 12:  # Reasonable emigration range
                    targets.append((location, star_system.name, min_distance))
                break  # Only need one uncolonized planet per system
    
    # Sort by distance (closest first)
    targets.sort(key=lambda x: x[2])
    return targets

def create_emigration_task_force(player, source_colony, target_location, target_name, 
                               emigrants_count, tf_number, game_state):
    """Create a task force with colony transports for emigration."""
    from stellar_conquest.entities.ship import Ship, ShipGroup
    from stellar_conquest.core.enums import ShipType
    from stellar_conquest.utils.hex_utils import find_path
    
    try:
        # Create colony transports for emigrants
        transports = []
        for i in range(emigrants_count):
            transport = Ship(
                ship_type=ShipType.COLONY_TRANSPORT,
                location=source_colony.location,
                count=1,
                task_force_id=tf_number,
                player_id=player.player_id
            )
            transports.append(transport)
        
        # Create ship group for the emigration task force
        emigration_group = ShipGroup(source_colony.location, player.player_id)
        
        # Add ships to the group
        for transport in transports:
            emigration_group.add_ships(transport)
        
        # Add to player's ship groups
        player.ship_groups.append(emigration_group)
        
        # Create movement plan for the task force
        if not hasattr(game_state, 'movement_plans'):
            game_state.movement_plans = {}
        if player.player_id not in game_state.movement_plans:
            game_state.movement_plans[player.player_id] = {}
        
        # Calculate path to target (simplified for emigration)
        try:
            # For emigration, we'll create a simple direct path plan
            # The actual pathfinding will be handled during movement phase
            simple_path = [source_colony.location, target_location]
            
            # Store movement plan
            game_state.movement_plans[player.player_id][tf_number] = {
                'planned_path': simple_path,
                'final_destination': target_location,
                'current_path_index': 0,
                'purpose': 'emigration_colonization'
            }
            
            print(f"       ✅ Created TF{tf_number}: {emigrants_count} colony transports → {target_name}")
            print(f"       🚌 Destination: {target_location} ({target_name})")
            
            return {
                'tf_number': tf_number,
                'target': target_location,
                'emigrants': emigrants_count,
                'path': simple_path
            }
                
        except Exception as e:
            print(f"       ❌ Task force setup failed: {e}")
            return None
            
    except Exception as e:
        print(f"       ❌ Task force creation failed: {e}")
        return None

def add_defense_purchases(player, decisions, remaining_ip):
    """Add defense purchases if player has the required technologies."""
    from stellar_conquest.core.enums import Technology
    from stellar_conquest.core.constants import BUILDING_COSTS
    
    # Only purchase defenses if we have colonies to defend
    if not player.colonies:
        return remaining_ip
    
    defense_purchased = False
    
    # Prioritize the most valuable/vulnerable colonies
    priority_colonies = sorted(player.colonies, 
                              key=lambda c: c.calculate_industrial_points(), 
                              reverse=True)[:3]  # Top 3 most productive colonies
    
    for colony in priority_colonies:
        if remaining_ip < 4:  # Minimum cost for any defense
            break
            
        # Check if colony already has adequate defenses
        if colony.has_planet_shield:
            continue  # Already has best protection
            
        # Purchase missile bases if technology is available and affordable
        if (Technology.MISSILE_BASE in player.completed_technologies and 
            remaining_ip >= 4 and colony.missile_bases < 3):  # Cap at 3 missile bases
            cost = 4
            decisions.append(("defense", "missile_base", colony.location, 1, cost))
            remaining_ip -= cost
            print(f"     🛡️ Defense: 1 missile base for {colony.location} ({cost} IP)")
            defense_purchased = True
            
        # Purchase advanced missile bases if available and better value
        elif (Technology.ADVANCED_MISSILE_BASE in player.completed_technologies and 
              remaining_ip >= 10 and colony.advanced_missile_bases < 2):  # Cap at 2 advanced
            cost = 10
            decisions.append(("defense", "advanced_missile_base", colony.location, 1, cost))
            remaining_ip -= cost
            print(f"     🛡️ Defense: 1 advanced missile base for {colony.location} ({cost} IP)")
            defense_purchased = True
            
        # Purchase planet shield if available (ultimate defense)
        elif (Technology.PLANET_SHIELD in player.completed_technologies and 
              remaining_ip >= 30 and not colony.has_planet_shield):
            cost = 30
            decisions.append(("defense", "planet_shield", colony.location, 1, cost))
            remaining_ip -= cost
            print(f"     🛡️ Defense: planet shield for {colony.location} ({cost} IP)")
            defense_purchased = True
    
    if not defense_purchased and player.colonies:
        print(f"     🛡️ No defense purchases made this turn")
    
    return remaining_ip

def add_advanced_ship_purchases(player, decisions, remaining_ip, play_style="warlord"):
    """Add advanced ship purchases if player has the required technologies."""
    from stellar_conquest.core.enums import Technology, ShipType
    from stellar_conquest.core.constants import SHIP_COSTS
    
    ships_purchased = False
    
    # Fighters are available if FIGHTER_SHIP technology is researched
    if (Technology.FIGHTER_SHIP in player.completed_technologies and 
        remaining_ip >= 20 and play_style in ["warlord", "balanced"]):
        fighter_count = min(remaining_ip // 20, 2)  # Cap at 2 fighters per turn
        if fighter_count > 0:
            fighter_cost = fighter_count * 20
            decisions.append(("ships", ShipType.FIGHTER, fighter_count, fighter_cost))
            remaining_ip -= fighter_cost
            print(f"     ⚔️ Advanced: {fighter_count} fighter{'s' if fighter_count > 1 else ''} ({fighter_cost} IP)")
            ships_purchased = True
    
    # Death stars are available if DEATH_STAR technology is researched
    if (Technology.DEATH_STAR in player.completed_technologies and 
        remaining_ip >= 40 and play_style == "warlord"):
        death_star_count = min(remaining_ip // 40, 1)  # Cap at 1 death star per turn (expensive!)
        if death_star_count > 0:
            death_star_cost = death_star_count * 40
            decisions.append(("ships", ShipType.DEATH_STAR, death_star_count, death_star_cost))
            remaining_ip -= death_star_cost
            print(f"     💀 Ultimate: {death_star_count} death star ({death_star_cost} IP)")
            ships_purchased = True
    
    if not ships_purchased:
        print(f"     ⚔️ No advanced ships purchased this turn")
    
    return remaining_ip


def calculate_balanced_spending_allocation(player, available_ip):
    """Calculate balanced spending allocation across research, ships, and defenses."""
    
    # Base allocation percentages by play style
    allocations = {
        'expansionist': {'research': 0.50, 'ships': 0.30, 'defenses': 0.20},  # Focus on tech and growth
        'warlord': {'research': 0.25, 'ships': 0.55, 'defenses': 0.20},      # Focus on military might
        'technophile': {'research': 0.65, 'ships': 0.20, 'defenses': 0.15},  # Focus on research
        'balanced': {'research': 0.40, 'ships': 0.35, 'defenses': 0.25}      # Balanced approach
    }
    
    base_allocation = allocations.get(player.play_style.value, allocations['balanced'])
    
    # Adjust based on game state and threats
    research_pct = base_allocation['research']
    ships_pct = base_allocation['ships']
    defenses_pct = base_allocation['defenses']
    
    # Early game adjustments (first few colonies)
    colony_count = len(player.colonies)
    if colony_count <= 2:
        # Early game - prioritize expansion tech and basic ships
        research_pct += 0.10
        ships_pct += 0.05
        defenses_pct -= 0.15
    elif colony_count >= 6:
        # Late game - more defensive, less pure research
        research_pct -= 0.10
        defenses_pct += 0.10
    
    # Check if player has basic technologies (adjust if missing key tech)
    has_speed_tech = any(tech.value.startswith('SPEED') for tech in player.completed_technologies)
    has_industrial_tech = any(tech.value.startswith('INDUSTRIAL') for tech in player.completed_technologies)
    
    if not has_speed_tech or not has_industrial_tech:
        research_pct += 0.15  # Need basic tech
        ships_pct -= 0.10
        defenses_pct -= 0.05
    
    # Ensure percentages are valid
    total_pct = research_pct + ships_pct + defenses_pct
    if total_pct != 1.0:
        # Normalize to 100%
        research_pct /= total_pct
        ships_pct /= total_pct
        defenses_pct /= total_pct
    
    return {
        'research': int(available_ip * research_pct),
        'ships': int(available_ip * ships_pct),
        'defenses': int(available_ip * defenses_pct)
    }


def make_production_spending(player, available_ip):
    """Make strategic spending decisions based on play style with balanced allocation."""
    from stellar_conquest.core.enums import Technology
    
    decisions = []
    remaining_ip = available_ip
    
    print(f"\n   🛠️ Strategic Spending ({available_ip} IP available):")
    
    # Allocate spending budgets by category to ensure balance
    spending_allocation = calculate_balanced_spending_allocation(player, available_ip)
    research_budget = spending_allocation['research']
    ships_budget = spending_allocation['ships'] 
    defenses_budget = spending_allocation['defenses']
    
    print(f"     📊 Spending Plan: Research {research_budget} IP, Ships {ships_budget} IP, Defenses {defenses_budget} IP")
    
    if player.play_style.value == "expansionist":
        # Expansionist: Prioritize industrial tech for economic expansion, then speed research
        # Industrial tech enables factories and C.E.T. allows barren planet colonization
        tech_purchased = False
        for tech in [Technology.INDUSTRIAL_TECHNOLOGY, Technology.CONTROLLED_ENVIRONMENT_TECH,
                     Technology.SPEED_4_HEX, Technology.SPEED_5_HEX, Technology.SPEED_6_HEX, 
                     Technology.SPEED_7_HEX, Technology.SPEED_8_HEX, Technology.SPEED_3_HEX]:
            if player.can_research_technology(tech):
                cost = player.get_technology_cost(tech)
                if remaining_ip >= cost:
                    tech_name = tech.value.replace('_', ' ').title()
                    decisions.append(("research", tech, cost))
                    remaining_ip -= cost
                    
                    # Show cost details including any partial investments
                    base_cost = TECHNOLOGY_COSTS.get(tech, cost)
                    partial_investment = 0
                    if hasattr(player, 'research_progress') and tech in player.research_progress:
                        partial_investment = player.research_progress[tech].invested_ip
                    
                    if partial_investment > 0:
                        print(f"     🚀 Research: {tech_name} technology ({cost} IP, completing {partial_investment} IP previous investment)")
                    elif cost < base_cost:
                        print(f"     🚀 Research: {tech_name} technology ({cost} IP, reduced from {base_cost} IP due to prerequisites)")
                    else:
                        print(f"     🚀 Research: {tech_name} technology ({cost} IP)")
                    tech_purchased = True
                    break
        
        if not tech_purchased:
            print(f"     🚀 No research available or affordable this turn")
        
        # Buy scouts for exploration
        scout_count = min(remaining_ip // 3, 10)  # Cap at 10 scouts per turn
        if scout_count > 0:
            scout_cost = scout_count * 3
            decisions.append(("ships", ShipType.SCOUT, scout_count, scout_cost))
            remaining_ip -= scout_cost
            print(f"     🔍 Build: {scout_count} scouts ({scout_cost} IP)")
            
    elif player.play_style.value == "warlord":
        # Warlord: Industrial tech first for economic base, then military technologies
        # Industrial power supports military buildup
        tech_purchased = False
        for tech in [Technology.INDUSTRIAL_TECHNOLOGY, Technology.MISSILE_BASE, 
                     Technology.FIGHTER_SHIP, Technology.CONTROLLED_ENVIRONMENT_TECH,
                     Technology.ADVANCED_MISSILE_BASE, Technology.DEATH_STAR, Technology.IMPROVED_SHIP_WEAPONRY]:
            if player.can_research_technology(tech):
                cost = player.get_technology_cost(tech)
                if remaining_ip >= cost:
                    tech_name = tech.value.replace('_', ' ').title()
                    decisions.append(("research", tech, cost))
                    remaining_ip -= cost
                    
                    # Show cost details including any partial investments
                    base_cost = TECHNOLOGY_COSTS.get(tech, cost)
                    partial_investment = 0
                    if hasattr(player, 'research_progress') and tech in player.research_progress:
                        partial_investment = player.research_progress[tech].invested_ip
                    
                    if partial_investment > 0:
                        print(f"     🚀 Research: {tech_name} technology ({cost} IP, completing {partial_investment} IP previous investment)")
                    elif cost < base_cost:
                        print(f"     🚀 Research: {tech_name} technology ({cost} IP, reduced from {base_cost} IP due to prerequisites)")
                    else:
                        print(f"     🚀 Research: {tech_name} technology ({cost} IP)")
                    tech_purchased = True
                    break
        
        if not tech_purchased:
            print(f"     🚀 No research available or affordable this turn")
        
        # Purchase defenses if technologies are available
        remaining_ip = add_defense_purchases(player, decisions, remaining_ip)
        
        # Purchase advanced ships if technologies are available
        remaining_ip = add_advanced_ship_purchases(player, decisions, remaining_ip, "warlord")
        
        # Build corvettes with remaining IP
        corvette_count = min(remaining_ip // 8, 5)  # Cap at 5 corvettes per turn
        if corvette_count > 0:
            corvette_cost = corvette_count * 8
            decisions.append(("ships", ShipType.CORVETTE, corvette_count, corvette_cost))
            remaining_ip -= corvette_cost
            print(f"     ⚔️ Build: {corvette_count} corvettes ({corvette_cost} IP)")
            
    elif player.play_style.value == "balanced":
        # Balanced: Industrial foundation first, then balanced research 
        # Industrial tech and C.E.T. provide strong economic base for balanced strategy
        tech_purchased = False
        for tech in [Technology.INDUSTRIAL_TECHNOLOGY, Technology.CONTROLLED_ENVIRONMENT_TECH,
                     Technology.SPEED_3_HEX, Technology.SPEED_4_HEX, Technology.SPEED_5_HEX, 
                     Technology.MISSILE_BASE, Technology.FIGHTER_SHIP]:
            if player.can_research_technology(tech):
                cost = player.get_technology_cost(tech)
                if remaining_ip >= cost:
                    tech_name = tech.value.replace('_', ' ').title()
                    decisions.append(("research", tech, cost))
                    remaining_ip -= cost
                    
                    # Show cost details including any partial investments
                    base_cost = TECHNOLOGY_COSTS.get(tech, cost)
                    partial_investment = 0
                    if hasattr(player, 'research_progress') and tech in player.research_progress:
                        partial_investment = player.research_progress[tech].invested_ip
                    
                    if partial_investment > 0:
                        print(f"     🚀 Research: {tech_name} technology ({cost} IP, completing {partial_investment} IP previous investment)")
                    elif cost < base_cost:
                        print(f"     🚀 Research: {tech_name} technology ({cost} IP, reduced from {base_cost} IP due to prerequisites)")
                    else:
                        print(f"     🚀 Research: {tech_name} technology ({cost} IP)")
                    tech_purchased = True
                    break
        
        if not tech_purchased:
            print(f"     🚀 No research available or affordable this turn")
        
        # Purchase defenses if technologies are available
        remaining_ip = add_defense_purchases(player, decisions, remaining_ip)
        
        # Purchase advanced ships if technologies are available (balanced approach)
        remaining_ip = add_advanced_ship_purchases(player, decisions, remaining_ip, "balanced")
        
        # Split remaining IP between corvettes and scouts
        if remaining_ip >= 8:
            decisions.append(("ships", ShipType.CORVETTE, 1, 8))
            remaining_ip -= 8
            print(f"     ⚔️ Build: 1 corvette (8 IP)")
        
        scout_count = min(remaining_ip // 3, 5)
        if scout_count > 0:
            scout_cost = scout_count * 3
            decisions.append(("ships", ShipType.SCOUT, scout_count, scout_cost))
            remaining_ip -= scout_cost
            print(f"     🔍 Build: {scout_count} scouts ({scout_cost} IP)")
            
    else:  # technophile
        # Technophile: Heavy research investment - prioritize industrial techs first
        research_technologies = [
            Technology.INDUSTRIAL_TECHNOLOGY, Technology.CONTROLLED_ENVIRONMENT_TECH,
            Technology.IMPROVED_INDUSTRIAL_TECH, Technology.ROBOTIC_INDUSTRY,
            Technology.SPEED_3_HEX, Technology.SPEED_4_HEX, Technology.SPEED_5_HEX,
            Technology.MISSILE_BASE, Technology.FIGHTER_SHIP, Technology.ADVANCED_MISSILE_BASE,
            Technology.DEATH_STAR, Technology.UNLIMITED_SHIP_RANGE, Technology.UNLIMITED_SHIP_COMMUNICATION
        ]
        
        techs_purchased = 0
        for tech in research_technologies:
            if techs_purchased >= 2:  # Limit to 2 techs per turn for variety
                break
            if player.can_research_technology(tech):
                cost = player.get_technology_cost(tech)
                if remaining_ip >= cost:
                    tech_name = tech.value.replace('_', ' ').title()
                    decisions.append(("research", tech, cost))
                    remaining_ip -= cost
                    print(f"     🚀 Research: {tech_name} technology ({cost} IP)")
                    techs_purchased += 1
        
        if techs_purchased == 0:
            print(f"     🚀 No research available or affordable this turn")
        
        # Purchase defenses if technologies are available  
        remaining_ip = add_defense_purchases(player, decisions, remaining_ip)
        
        # Remaining IP on scouts
        scout_count = min(remaining_ip // 3, 8)
        if scout_count > 0:
            scout_cost = scout_count * 3
            decisions.append(("ships", ShipType.SCOUT, scout_count, scout_cost))
            remaining_ip -= scout_cost
            print(f"     🔍 Build: {scout_count} scouts ({scout_cost} IP)")
    
    # Research-based IP banking - invest leftover IP in selected research
    if remaining_ip > 0:
        # Find the best research to invest leftover IP in
        banking_research = select_banking_research(player, remaining_ip)
        if banking_research:
            tech_name = banking_research.value.replace('_', ' ').title()
            total_cost = player.get_technology_cost(banking_research)
            
            # Calculate how much IP is actually needed (don't over-invest)
            current_progress = getattr(player, 'research_progress', {})
            already_invested = 0
            if banking_research in current_progress:
                already_invested = current_progress[banking_research].invested_ip
            
            needed_ip = max(0, total_cost - already_invested)
            actual_investment = min(remaining_ip, needed_ip)
            
            if actual_investment > 0:
                print(f"     🏦 Investing {actual_investment} IP in {tech_name} research")
                print(f"         (Total cost: {total_cost} IP, {already_invested + actual_investment}/{total_cost} IP after investment)")
                decisions.append(("research_banking", banking_research, actual_investment))
                remaining_ip -= actual_investment
            
            # Bank any excess IP if technology doesn't need full amount
            if remaining_ip > 0:
                print(f"     💰 Banking remaining {remaining_ip} IP (no technologies need this much)")
                decisions.append(("bank", remaining_ip))
        else:
            # Fallback - no valid research targets found
            print(f"     💰 No research targets available - banking {remaining_ip} IP")
            decisions.append(("bank", remaining_ip))
    
    return decisions

def execute_production_decisions(game_state, player, decisions):
    """Actually implement the production decisions."""
    for decision in decisions:
        decision_type = decision[0]
        
        if decision_type == "research":
            technology = decision[1]  # This is now a Technology enum
            cost = decision[2]
            
            # Safety check: Don't invest in already completed technologies
            if technology in player.completed_technologies:
                print(f"     ⚠️  Cannot invest in {technology.value.replace('_', ' ').title()} - already completed")
                continue
            
            # Use the proper technology investment system
            completed = player.add_research_investment(technology, cost)
            tech_name = technology.value.replace('_', ' ').title()
            
            if completed:
                # Technology completed this turn
                if technology in [Technology.SPEED_3_HEX, Technology.SPEED_4_HEX, Technology.SPEED_5_HEX, 
                                Technology.SPEED_6_HEX, Technology.SPEED_7_HEX, Technology.SPEED_8_HEX]:
                    print(f"     ✅ {player.name} completed {tech_name} - ships now move {player.current_ship_speed} hexes per turn")
                else:
                    print(f"     ✅ {player.name} completed {tech_name} research")
            else:
                print(f"     🔬 {player.name} invested {cost} IP in {tech_name} research (needs more IP to complete)")
                
        elif decision_type == "ships":
            ship_type = decision[1]
            count = decision[2]
            cost = decision[3]

            # Ships are produced at colonies and placed in their star hex (per rules)
            # Use the most productive NON-BESIEGED colony for ship production (Rule 4.3.2)
            if player.colonies:
                # Filter out besieged colonies - they cannot build ships
                eligible_colonies = [c for c in player.colonies if not c.is_besieged]

                if not eligible_colonies:
                    print(f"     ⚠️  Cannot build ships - all colonies are under siege!")
                    continue

                producing_colony = max(eligible_colonies, key=lambda c: c.calculate_industrial_points())
                production_location = producing_colony.location
                
                # Find or create ship group at the producing colony's star hex
                production_group = None
                for group in player.ship_groups:
                    if group.location == production_location:
                        production_group = group
                        break
                
                if not production_group:
                    # Create new ship group at production location
                    from stellar_conquest.entities.ship import ShipGroup, Ship
                    production_group = ShipGroup(production_location, player.player_id)
                    player.ship_groups.append(production_group)
                    print(f"     🏭 Created new fleet at {production_location} (producing colony)")
                
                # Find existing ship of this type or create new one
                existing_ship = None
                for ship in production_group.ships:
                    if ship.ship_type == ship_type:
                        existing_ship = ship
                        break
                
                if existing_ship:
                    existing_ship.count += count
                else:
                    from stellar_conquest.entities.ship import Ship
                    new_ship = Ship(ship_type=ship_type, count=count, player_id=player.player_id)
                    production_group.ships.append(new_ship)
                
                colony_info = f" at {production_location} (built by {producing_colony.location} colony)"
                print(f"     🏭 Built {count} {ship_type.value}{'s' if count > 1 else ''}{colony_info}")
            else:
                # Fallback: if no colonies (shouldn't happen), use entry hex
                main_group = None
                for group in player.ship_groups:
                    if group.location == player.entry_hex:
                        main_group = group
                        break
                
                if main_group:
                    existing_ship = None
                    for ship in main_group.ships:
                        if ship.ship_type == ship_type:
                            existing_ship = ship
                            break
                    
                    if existing_ship:
                        existing_ship.count += count
                    else:
                        from stellar_conquest.entities.ship import Ship
                        new_ship = Ship(ship_type=ship_type, count=count, player_id=player.player_id)
                        main_group.ships.append(new_ship)
                    
                    print(f"     ⚠️  Built {count} {ship_type.value}{'s' if count > 1 else ''} at entry hex (no colonies)")
                
        elif decision_type == "research_banking":
            # Research-based banking - invest leftover IP in selected research
            technology = decision[1]
            investment_amount = decision[2]
            
            # Safety check: Don't invest in already completed technologies
            if technology in player.completed_technologies:
                print(f"     ⚠️  Cannot invest in {technology.value.replace('_', ' ').title()} - already completed")
                continue
            
            # Use the proper technology investment system
            completed = player.add_research_investment(technology, investment_amount)
            tech_name = technology.value.replace('_', ' ').title()
            
            if completed:
                print(f"     🎉 Research banking completed {tech_name}! (invested {investment_amount} IP)")
            else:
                current_progress = getattr(player, 'research_progress', {})
                if technology in current_progress:
                    progress = current_progress[technology]
                    total_cost = player.get_technology_cost(technology)
                    print(f"     🏦 Banked {investment_amount} IP in {tech_name} research ({progress.invested_ip}/{total_cost} IP total)")
                else:
                    print(f"     🏦 Started banking in {tech_name} research ({investment_amount} IP invested)")
                
        elif decision_type == "defense":
            # Purchase colony defenses (missile bases, planet shields)
            defense_type = decision[1]
            colony_location = decision[2]
            count = decision[3] if len(decision) > 3 else 1
            cost = decision[4] if len(decision) > 4 else decision[3]
            
            # Find the colony
            colony = None
            for c in player.colonies:
                if c.location == colony_location:
                    colony = c
                    break
            
            if colony:
                if defense_type == "missile_base":
                    colony.add_missile_bases(count)
                    print(f"     🛡️ Added {count} missile base{'s' if count > 1 else ''} to {colony_location} ({cost} IP)")
                elif defense_type == "advanced_missile_base":
                    colony.add_advanced_missile_bases(count)
                    print(f"     🛡️ Added {count} advanced missile base{'s' if count > 1 else ''} to {colony_location} ({cost} IP)")
                elif defense_type == "planet_shield":
                    if not colony.has_planet_shield:
                        colony.install_planet_shield()
                        print(f"     🛡️ Installed planet shield on {colony_location} ({cost} IP)")
                    else:
                        print(f"     ⚠️ {colony_location} already has a planet shield")
                        
        elif decision_type == "bank":
            # Banking IP for future - could be implemented as player attribute
            banked_amount = decision[1]
            if not hasattr(player, 'banked_ip'):
                player.banked_ip = 0
            player.banked_ip += banked_amount
    
    print(f"   ✅ Production turn completed")

def create_new_task_forces(game_state, player, turn_number):
    """Create new task forces from unassigned ships at start of turn."""
    print_phase_header(turn_number, "0", "TASK FORCE CREATION")
    
    # Initialize movement plans if not exists
    if not hasattr(game_state, 'movement_plans'):
        game_state.movement_plans = {}
    if player.player_id not in game_state.movement_plans:
        game_state.movement_plans[player.player_id] = {}
    
    # Task forces can only be created on Turn 1 or when at star hexes
    if turn_number == 1:
        # Turn 1: Create task forces from starting fleet at entry point
        if not player.has_entered_board:
            place_starting_fleet_with_task_force_id(player)
            print(f"   {player.name} enters the game at {player.entry_hex}")

        # Create additional task forces from the starting fleet
        create_exploration_task_forces(game_state, player, turn_number)
    else:
        # Later turns: Warlord sends scouts to enemy yellow stars for reconnaissance
        if player.play_style.value == "warlord" and turn_number >= 2:
            # Find main group at entry hex
            main_group = None
            for group in player.ship_groups:
                if group.location == player.entry_hex:
                    main_group = group
                    break

            if main_group:
                send_warlord_scouts_to_enemy_yellow_stars(game_state, player, main_group, turn_number)

        # Later turns: Check if any rally forces have assembled and launch attacks
        if player.play_style.value == "warlord" and hasattr(game_state, 'attack_staging'):
            if player.player_id in game_state.attack_staging:
                staging_list = game_state.attack_staging[player.player_id]

                # Check each staged attack
                for staging in staging_list[:]:  # Use slice to allow removal during iteration
                    rally_point = staging['rally_point']
                    rally_tfs = staging.get('rally_tfs', [])  # List of TFs heading to rally
                    target = staging['target']
                    target_owner = staging['target_owner']

                    # Check if ALL rally TFs have arrived at rally point
                    all_arrived = True

                    if rally_tfs:
                        # Check that each rally TF has arrived
                        for tf_num in rally_tfs:
                            tf_arrived = False
                            for group in player.ship_groups:
                                if group.location == rally_point:
                                    # Check if this group contains ships from this TF
                                    for ship in group.ships:
                                        if ship.task_force_id == tf_num:
                                            tf_arrived = True
                                            break
                                if tf_arrived:
                                    break

                            if not tf_arrived:
                                all_arrived = False
                                break

                    # If all rally TFs have arrived (or no rally TFs), count ALL warships at rally point
                    total_corvettes = 0
                    total_fighters = 0
                    total_death_stars = 0

                    if all_arrived:
                        for group in player.ship_groups:
                            if group.location == rally_point:
                                ship_counts = group.get_ship_counts()
                                total_corvettes += ship_counts.get(ShipType.CORVETTE, 0)
                                total_fighters += ship_counts.get(ShipType.FIGHTER, 0)
                                total_death_stars += ship_counts.get(ShipType.DEATH_STAR, 0)

                    if all_arrived and (total_corvettes + total_fighters + total_death_stars > 0):
                        # Forces have assembled! Launch the attack
                        print(f"   ⚔️  FORCES ASSEMBLED at {rally_point}!")
                        print(f"      {total_corvettes} corvettes, {total_fighters} fighters, {total_death_stars} death stars ready")
                        print(f"      Launching attack on {target_owner}'s colony at {target}")

                        # Find target info
                        target_pop = 0
                        target_defenses = 0
                        for other_player in game_state.players:
                            if other_player.name == target_owner:
                                for colony in other_player.colonies:
                                    if colony.location == target:
                                        target_pop = colony.population
                                        target_defenses = getattr(colony, 'missile_bases', 0)
                                        break

                        # Launch the attack from rally point
                        success = create_single_attack_task_force(
                            game_state, player, rally_point, target, target_owner,
                            target_pop, target_defenses, total_corvettes, total_fighters, total_death_stars, turn_number
                        )

                        if success:
                            # Remove from staging list
                            staging_list.remove(staging)

        # ALL players should check for attack opportunities every turn (turn 4+)
        if turn_number >= 4:
            enemy_targets = find_enemy_colonies(game_state, player)

            if enemy_targets:
                # Warlord uses sophisticated rally point strategy
                if player.play_style.value == "warlord":
                    # Check if we already have an attack staged for this target
                    already_staging = False
                    if hasattr(game_state, 'attack_staging') and player.player_id in game_state.attack_staging:
                        for staging in game_state.attack_staging[player.player_id]:
                            if staging['target'] == enemy_targets[0]['location']:
                                already_staging = True
                                break

                    if not already_staging:
                        print(f"   ⚔️  WARLORD MODE ACTIVATED: {len(enemy_targets)} enemy colony location{'s' if len(enemy_targets) != 1 else ''} discovered in explored systems!")
                        for i, target in enumerate(enemy_targets[:3], 1):  # Show top 3 targets
                            print(f"      Target {i}: {target['owner']}'s colony at {target['location']} - {target['distance']} hexes away")
                        create_attack_task_forces_from_all_locations(game_state, player, enemy_targets, turn_number)
                else:
                    # Other play styles use simpler opportunistic attacks
                    create_opportunistic_attacks(game_state, player, enemy_targets, turn_number)
            else:
                if player.play_style.value == "warlord":
                    print(f"   🔍 Warlord scouting: No enemy colonies discovered yet in explored systems")

        # Later turns: Can only create task forces when at star hexes
        for tf_index, group in enumerate(player.ship_groups):
            tf_number = tf_index + 1
            location = group.location

            if game_state.board.is_star_location(location):
                # At star hex - can potentially create new task forces
                # For now, keep existing logic simple
                pass

def run_player_turn(game_state, player, turn_number, map_generator, executor=None, map_futures=None, generate_range_maps=True, battle_stats=None):
    """Run a complete player turn following the sequence of play.

    Args:
        generate_range_maps: If True, generate individual player range maps showing command post coverage.
                           If False, skip range maps (saves time and reduces file count by ~176 files in a 44-turn game).
        battle_stats: Dictionary tracking battle statistics for each player.
    """
    print_turn_header(turn_number, player.name)

    print(f"Game State: Turn {turn_number}, {len(game_state.board.star_systems)} systems discovered")

    # 0. Bonus IP spending phase (turn 1 only)
    bonus_ip_spending_phase(game_state, player, turn_number)

    # 1. Create new task forces (start of turn only)
    create_new_task_forces(game_state, player, turn_number)

    # 1b. Check conquered colonies maintenance (all players)
    reverted_colonies = check_conquered_colonies_maintenance(game_state)
    if reverted_colonies:
        print(f"\n⚠️  Conquered Colony Maintenance:")
        for reversion in reverted_colonies:
            print(f"   • {reversion['location']}: {reversion['conqueror']} → {reversion['original_owner']}")

    # 1c. Check besieged colonies status (all players)
    besieged_changes = check_besieged_colonies_status(game_state)
    # (Output is printed directly in check_besieged_colonies_status)

    # 2. Move spaceships
    make_movement_decisions(game_state, player, turn_number)

    # 3. Explore new stars
    make_exploration_decisions(game_state, player, turn_number)

    # 4. Resolve combat
    resolve_combat_phase(game_state, player, turn_number, battle_stats)
    
    # 5. Attack enemy colonies  
    resolve_colony_attacks(game_state, player, turn_number)
    
    # 6. Debark colonists
    debark_colonists(game_state, player, turn_number)
    
    # 7. Record turn
    print_phase_header(turn_number, "f", "RECORD TURN")
    print(f"{player.name} completes turn {turn_number}")
    
    show_player_status(player)
    
    # 8. Generate range map showing command post coverage (optional, in background if executor available)
    if generate_range_maps:
        if executor and map_futures is not None:
            print(f"\n🗺️  Queuing range map for {player.name} (running in background)...")
            # Create a snapshot of game_state for thread safety
            game_state_snapshot = copy.deepcopy(game_state)
            future = executor.submit(map_generator.create_player_range_map, game_state_snapshot, turn_number, player.player_id)
            map_futures.append((f"Turn {turn_number} - {player.name} range map", future))
        elif map_futures is None:  # Only generate synchronously if not using threading
            print(f"\n🗺️  Generating range map for {player.name}...")
            map_generator.create_player_range_map(game_state, turn_number, player.player_id)


def cleanup_empty_task_forces(game_state):
    """Remove empty task forces for all players during maintenance phase."""
    total_removed = 0
    
    for player in game_state.players:
        removed_count = cleanup_player_empty_task_forces(player)
        if removed_count > 0:
            print(f"   🗑️  {player.name}: Removed {removed_count} empty task force{'s' if removed_count > 1 else ''}")
            total_removed += removed_count
    
    if total_removed == 0:
        print(f"   ✅ No empty task forces found")
    else:
        print(f"   📊 Total cleanup: {total_removed} empty task force{'s' if total_removed > 1 else ''} removed")


def cleanup_player_empty_task_forces(player):
    """Remove empty task forces for a single player."""
    removed_count = 0
    groups_to_remove = []
    
    # Find empty task forces
    for group in player.ship_groups:
        total_ships = group.get_total_ships()
        if total_ships == 0:
            groups_to_remove.append(group)
    
    # Remove empty groups
    for group in groups_to_remove:
        player.ship_groups.remove(group)
        removed_count += 1
    
    return removed_count


def run_production_turn(game_state, turn_number):
    """Run production turn for all players."""
    print("\n" + "="*70)
    print(f"  PRODUCTION TURN {turn_number} - ALL PLAYERS")
    print("="*70)
    
    print(f"\n🏭 PRODUCTION PHASE (Every 4th Turn)")
    print(f"All players make production decisions simultaneously")
    
    for player in game_state.players:
        show_production_choices(game_state, player)
    
    # Clean up empty task forces after production phase
    print(f"\n🧹 MAINTENANCE PHASE")
    cleanup_empty_task_forces(game_state)

def auto_demo_with_enhanced_maps(speed_mode='NORMAL', generate_maps=True, max_turns=44):
    """Run automatic demo with enhanced matplotlib-based maps.

    Runs a complete 44-turn Stellar Conquest simulation with production phases
    every 4th turn (turns 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44).

    Args:
        speed_mode: 'NORMAL', 'FAST', or 'ULTRA_FAST' - controls sleep delays and range map generation
        generate_maps: If True, generate turn maps; if False, skip all map generation
        max_turns: Number of turns to simulate (default 44 = full campaign)

    Note:
        Range maps (individual player command post coverage) are disabled by default.
        Enable by setting speed_configs[mode]['range_maps'] = True
        This will generate ~176 extra files in a 44-turn game (4 players × 44 turns).
    """
    # Speed mode configuration
    # range_maps: Generate individual player range maps (8-hex command post coverage)
    #   True = Generate range maps for each player every turn (lots of files!)
    #   False = Only generate overall turn maps (much faster, fewer files)
    speed_configs = {
        'ULTRA_FAST': {'sleep_delay': 0, 'detailed_output': False, 'range_maps': False},
        'FAST': {'sleep_delay': 0.1, 'detailed_output': False, 'range_maps': False},
        'NORMAL': {'sleep_delay': 0.5, 'detailed_output': True, 'range_maps': False}
    }
    
    config = speed_configs.get(speed_mode.upper(), speed_configs['NORMAL'])
    
    print("="*70)
    print(f"  🌌 STELLAR CONQUEST AUTO DEMO - {speed_mode.upper()} MODE")
    print("  Enhanced Map Generation with matplotlib")
    print("="*70)
    
    if speed_mode != 'NORMAL':
        print(f"\n⚡ Speed optimizations enabled:")
        print(f"   Sleep delay: {config['sleep_delay']}s")
        print(f"   Detailed output: {config['detailed_output']}")
        print(f"   Range maps: {config['range_maps']}")
        print(f"   Map generation: {generate_maps}")
        print(f"   Max turns: {max_turns}")
    
    print("\nDemonstrating proper sequence of play per rules 3.2:")
    print("1. Move spaceships")
    print("2. Explore new stars") 
    print("3. Resolve combat")
    print("4. Attack enemy colonies")
    print("5. Debark colonists")
    print("6. Record turn")
    print("7. Production turn (every 4th turn)")
    
    # Create enhanced map generator
    map_generator = EnhancedMapGenerator()

    # Create thread pool for async map generation
    map_futures = []
    executor = ThreadPoolExecutor(max_workers=2) if generate_maps else None

    # Create game
    settings = GameSettings(max_turns=max_turns, victory_points_target=50)
    game_state = create_game(settings)

    # Add players with different play styles
    game_state.add_player("Admiral Nova", PlayStyle.EXPANSIONIST, "A1")
    game_state.add_player("General Vega", PlayStyle.WARLORD, "A21")
    game_state.add_player("Captain Rex", PlayStyle.BALANCED, "FF1")
    game_state.add_player("Commander Luna", PlayStyle.TECHNOPHILE, "FF20")

    # Start game
    game_state.start_game()

    # Initialize battle statistics tracker
    battle_stats = {player.name: {'battles': 0, 'victories': 0} for player in game_state.players}

    # Generate initial map (turn 0) in background thread
    if generate_maps:
        print("\n🗺️  Queuing initial map generation (running in background)...")
        # Create a snapshot of game_state for thread safety
        game_state_snapshot = copy.deepcopy(game_state)
        future = executor.submit(map_generator.create_turn_map, game_state_snapshot, 0, "output/maps/enhanced_turn_0_initial.svg")
        map_futures.append(("Turn 0 initial", future))
    else:
        print("\n⚡ Skipping map generation for maximum speed...")
    
    # Run turns until first production turn
    turn_number = 1
    
    while turn_number <= max_turns:
        for player in game_state.players:
            run_player_turn(game_state, player, turn_number, map_generator, executor, map_futures, config['range_maps'], battle_stats)
            if config['sleep_delay'] > 0:
                time.sleep(config['sleep_delay'])
        
        # Generate map after each complete turn in background thread
        if generate_maps:
            print(f"\n🗺️  Queuing map generation for turn {turn_number} (running in background)...")
            # Create a snapshot of game_state for thread safety
            game_state_snapshot = copy.deepcopy(game_state)
            future = executor.submit(map_generator.create_turn_map, game_state_snapshot, turn_number,
                                   f"output/maps/enhanced_turn_{turn_number}_map.svg")
            map_futures.append((f"Turn {turn_number}", future))
        elif turn_number % 4 == 0:  # Only show progress on production turns
            print(f"\n⚡ Turn {turn_number} complete (production turn)")
        
        if turn_number % 4 == 0:
            run_production_turn(game_state, turn_number)
        
        turn_number += 1
    
    # Final summary
    print("\n" + "="*70)
    print("  DEMO SUMMARY")
    print("="*70)
    
    print(f"\n📊 Game Statistics after {turn_number} turns:")
    print(f"   Systems discovered: {len(game_state.board.star_systems)}")
    print(f"   Total task forces: {sum(len(p.ship_groups) for p in game_state.players)}")
    
    print(f"\n🏆 Player Standings:")
    for i, player in enumerate(game_state.players, 1):
        vp = player.calculate_victory_points(game_state)
        systems_explored = sum(1 for explorers in game_state.board.explored_systems.values() 
                             if player.player_id in explorers)
        task_forces = len(player.ship_groups)
        
        # Calculate detailed ship counts
        ship_totals = {}
        for group in player.ship_groups:
            ship_counts = group.get_ship_counts()
            for ship_type, count in ship_counts.items():
                if count > 0:
                    ship_name = ship_type.value.lower()
                    if ship_name not in ship_totals:
                        ship_totals[ship_name] = 0
                    ship_totals[ship_name] += count
        
        total_ships = sum(ship_totals.values())
        ship_breakdown = []
        for ship_type, count in ship_totals.items():
            ship_breakdown.append(f"{count} {ship_type}{'s' if count > 1 else ''}")
        
        # Calculate colony statistics
        total_colonies = len(player.colonies)
        conquered_colonies = sum(1 for colony in player.colonies if colony.is_conquered)
        total_population = sum(colony.population for colony in player.colonies)
        total_factories = sum(colony.factories for colony in player.colonies)

        # Get battle statistics
        battles = battle_stats.get(player.name, {}).get('battles', 0)
        victories = battle_stats.get(player.name, {}).get('victories', 0)

        print(f"   {i}. {player.name}")
        print(f"      Play Style: {player.play_style.value}")
        print(f"      Victory Points: {vp}")
        print(f"      Task Forces: {task_forces}")
        print(f"      Total Ships: {total_ships} ({', '.join(ship_breakdown) if ship_breakdown else 'no ships'})")
        colony_desc = f"{total_colonies} colonies"
        if conquered_colonies > 0:
            colony_desc += f" ({conquered_colonies} conquered)"
        print(f"      Colonies: {colony_desc}, {total_population}M total population, {total_factories} factories")
        print(f"      Systems Explored: {systems_explored}")
        print(f"      Battles: {battles} fought, {victories} won")
    
    # Victory Points Breakdown Report
    print(f"\n📊 VICTORY POINTS BREAKDOWN:")
    for i, player in enumerate(game_state.players, 1):
        total_vp = player.calculate_victory_points(game_state)
        detailed_breakdown = player.get_detailed_victory_points_breakdown(game_state)
        
        print(f"\n   {i}. {player.name} - Total Victory Points: {total_vp}")
        
        # Show each rule's contribution
        for rule_key, rule_data in detailed_breakdown.items():
            if rule_data['points'] > 0:
                rule_name = {
                    'rule_a': 'Rule A - Colony Control',
                    'rule_b': 'Rule B - Conquered Colony + Warship',
                    'rule_c': 'Rule C - Ship-Controlled Unoccupied Planet',
                    'rule_d': 'Rule D - Colony System Extension'
                }[rule_key]
                
                rule_icon = {
                    'rule_a': '🏛️',
                    'rule_b': '⚔️',
                    'rule_c': '🚀',
                    'rule_d': '🏛️'
                }[rule_key]
                
                print(f"      {rule_icon} {rule_name}: {rule_data['points']} VP")
                
                for planet_info in rule_data['planets']:
                    planet_type_display = planet_info['planet_type'].replace('_', '-').title()
                    vp = planet_info['victory_points']
                    location = planet_info['location']
                    
                    if rule_key == 'rule_a':
                        status = f" ({planet_info['status'].title()})" if planet_info['status'] == 'conquered' else ""
                        print(f"        • {location} ({planet_type_display}{status}) = {vp} VP")
                    else:
                        explanation = planet_info['explanation']
                        print(f"        • {location} ({planet_type_display}) = {vp} VP - {explanation}")
        
        # Show non-scoring colonies if any
        non_scoring = []
        for colony in player.colonies:
            if (colony.is_active or colony.is_conquered) and colony.planet.victory_points == 0:
                planet_type = colony.planet.planet_type.value.replace('_', '-').title()
                status = " (Conquered)" if colony.is_conquered else ""
                non_scoring.append(f"{colony.location} ({planet_type}{status})")
        
        if non_scoring:
            print(f"      🌑 Non-Victory Point Colonies:")
            for colony_info in non_scoring:
                print(f"        • {colony_info} = 0 VP")
        
        # Victory Points Summary
        if total_vp > 0:
            print(f"      📊 Victory Points Summary:")
            for rule_key, rule_data in detailed_breakdown.items():
                if rule_data['points'] > 0:
                    rule_short = rule_key.replace('_', ' ').title()
                    planet_count = len(rule_data['planets'])
                    print(f"        • {rule_short}: {planet_count} planet{'s' if planet_count > 1 else ''} = {rule_data['points']} VP")
        else:
            print(f"      No victory points earned")
    
    # Show Star Systems Discovered Report
    show_star_systems_discovered(game_state)


def show_star_systems_discovered(game_state):
    """Show detailed report of all discovered star systems, planets, and colonies."""
    if game_state.board.star_systems:
        print(f"\n🌟 Star Systems Discovered:")
        for location, system in game_state.board.star_systems.items():
            explorers = game_state.board.explored_systems.get(location, set())
            explorer_names = []
            for pid in explorers:
                player = game_state.get_player_by_id(pid)
                if player:
                    explorer_names.append(player.name)
            
            planet_count = len(system.planets)
            print(f"   {location}: {system.name} ({system.star_color.value} star, {planet_count} planets)")
            print(f"      Discovered by: {', '.join(explorer_names) if explorer_names else 'Unknown'}")
            
            # Show detailed planet information
            if system.planets:
                print(f"      Planets:")
                for i, planet in enumerate(system.planets, 1):
                    planet_type = planet.planet_type.value.replace('_', '-').title()
                    mineral_status = " (Mineral Rich)" if planet.is_mineral_rich else ""
                    
                    # Find any colony on this planet
                    colony_info = ""
                    colony_owner = None
                    colony_population = 0
                    colony_factories = 0
                    
                    for player in game_state.players:
                        for colony in player.colonies:
                            # Check if colony is on this planet (match location and planet)
                            if colony.location == location and colony.planet == planet:
                                colony_owner = player.name
                                colony_population = colony.population
                                colony_factories = colony.factories
                                break
                        if colony_owner:
                            break
                    
                    if colony_owner:
                        factory_info = f", {colony_factories} factories" if colony_factories > 0 else ""
                        colony_info = f" - Colony: {colony_population}M pop{factory_info} ({colony_owner})"
                    else:
                        colony_info = " - Uncolonized"
                    
                    print(f"        Orbit {planet.orbit}: {planet_type}{mineral_status} (max {planet.max_population}M){colony_info}")
            else:
                print(f"      No planets in system")
    else:
        print(f"\n🌟 Star Systems Discovered: None")


def show_planet_control_breakdown(player, game_state):
    """Show detailed breakdown of planet control victory points."""
    processed_planets = set()
    
    # Track planets already counted from colonies
    colonized_planets = set()
    for colony in player.colonies:
        if colony.is_active or colony.is_conquered:
            planet_id = id(colony.planet)  # Use object ID as unique identifier
            colonized_planets.add((colony.location, planet_id))
    
    # Check all star systems for planet control bonuses
    for location, star_system in game_state.board.star_systems.items():
        for planet in star_system.planets:
            planet_id = id(planet)
            planet_key = (location, planet_id)
            
            # Skip planets already counted from colonies
            if planet_key in colonized_planets:
                continue
            
            # Skip if already processed
            if planet_key in processed_planets:
                continue
            
            # Only count planets that give victory points
            if planet.victory_points <= 0:
                continue
            
            # Check each rule and explain why points were awarded
            rule_applied = None
            explanation = ""
            
            # Rule b: Conquered colony with warship protection
            conquered_colony = player._has_conquered_colony_at_planet(location, planet)
            if conquered_colony and player._has_warship_at_location(location):
                rule_applied = "B"
                explanation = f"Conquered colony protected by warship"
            
            # Rule c: Unoccupied planet with spaceship present
            elif (player._is_planet_unoccupied(location, planet, game_state) and 
                  player._has_any_ship_at_location(location)):
                rule_applied = "C"
                ship_group = player.get_ship_group_at_location(location)
                ship_desc = f"{ship_group.get_total_ships()} ship{'s' if ship_group.get_total_ships() > 1 else ''}"
                explanation = f"Unoccupied planet controlled by {ship_desc}"
            
            # Rule d: Unoccupied planet in same system as colony, no enemy ships
            elif (player._is_planet_unoccupied(location, planet, game_state) and 
                  player._has_colony_in_same_system(location) and 
                  not player._has_enemy_ships_at_location(location, game_state)):
                rule_applied = "D"
                explanation = f"Unoccupied planet in same system as player colony"
            
            if rule_applied:
                planet_type = planet.planet_type.value.replace('_', '-').title()
                vp = planet.victory_points
                print(f"        • Rule {rule_applied}: {location} ({planet_type}) = {vp} VP - {explanation}")
                processed_planets.add(planet_key)
    
    # Wait for all background map generation to complete
    if generate_maps and map_futures:
        print(f"\n⏳ Waiting for {len(map_futures)} background map generation tasks to complete...")
        completed = 0
        failed = 0
        for name, future in map_futures:
            try:
                future.result()  # Wait for completion and check for exceptions
                completed += 1
                print(f"   ✓ {name} map completed ({completed}/{len(map_futures)})")
            except Exception as e:
                failed += 1
                print(f"   ✗ {name} map failed: {str(e)}")

        # Shutdown the thread pool
        executor.shutdown(wait=True)

        if failed > 0:
            print(f"\n⚠️  {completed} maps generated successfully, {failed} failed")
        else:
            print(f"\n✅ All {completed} maps generated successfully!")

    print(f"\n🗺️  Enhanced Maps Generated:")
    print(f"   • output/maps/enhanced_turn_0_initial.svg - Starting positions")
    for turn in range(1, turn_number + 1):
        print(f"   • output/maps/enhanced_turn_{turn}_map.svg - End of turn {turn}")

    print(f"\n✅ Demo completed! Check the SVG files for high-quality scalable maps!")
    print(f"🎨 Maps use your existing mapgenerator.py hex grid with enhanced task force visualization!")

def main():
    """Main entry point for the demo."""
    try:
        auto_demo_with_enhanced_maps()
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()