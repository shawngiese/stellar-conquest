"""
Combat System Module for Stellar Conquest Simulation

This module handles all combat-related functionality including:
- Ship combat resolution (Rule 4.1)
- Enemy ship detection (Rule 3.8)
- Attack tables and combat mechanics
- Colony attacks and conquest
"""

import random
from stellar_conquest.core.enums import ShipType


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
    # Check if there's a star system at this location
    if hasattr(game_state, 'galaxy') and hasattr(game_state.galaxy, 'star_systems'):
        return location in game_state.galaxy.star_systems
    return False


def resolve_one_barrage_attack(attacking_warships, defending_ships, attacker_player, defender_player):
    """Resolve one barrage attack from warships against unarmed ships."""
    unarmed_types = {ShipType.SCOUT, ShipType.COLONY_TRANSPORT}
    
    # Only target unarmed ships
    unarmed_targets = {k: v for k, v in defending_ships.items() if k in unarmed_types}
    
    if not unarmed_targets:
        return  # No unarmed ships to attack
    
    total_losses = 0
    
    # Each warship type attacks with its effectiveness
    for warship_type, warship_count in attacking_warships.items():
        for target_type, target_count in unarmed_targets.items():
            if target_count <= 0:
                continue
            
            # Each warship gets one attack
            for _ in range(warship_count):
                if target_count <= 0:
                    break
                
                # Use attack table values
                if warship_type == ShipType.DEATH_STAR:
                    # Death stars auto-kill unarmed ships (1-6 on 1 die)
                    if random.randint(1, 6) <= 6:
                        target_count -= 1
                        total_losses += 1
                elif warship_type == ShipType.FIGHTER:
                    # Fighters very effective (1-5 on 1 die)
                    if random.randint(1, 6) <= 5:
                        target_count -= 1
                        total_losses += 1
                elif warship_type == ShipType.CORVETTE:
                    # Corvettes moderately effective (1-3 on 1 die)
                    if random.randint(1, 6) <= 3:
                        target_count -= 1
                        total_losses += 1
            
            # Update the defending ships count
            unarmed_targets[target_type] = target_count
    
    if total_losses > 0:
        print(f"   💥 Barrage destroys {total_losses} unarmed ships")
    else:
        print(f"   🛡️  All unarmed ships survive the barrage")


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


def resolve_ship_combat(game_state, location, attacker_player, defender_player):
    """Resolve combat between ships at a location according to rules 4.1."""
    print(f"\n⚔️  COMBAT AT {location}")
    print(f"   Attacker: {attacker_player.name}")
    print(f"   Defender: {defender_player.name}")
    
    # Get ships at this location for both players
    attacker_ships = {}
    defender_ships = {}
    attacker_taskforces = {}  # Track which ships belong to which taskforces
    defender_taskforces = {}
    
    for group in attacker_player.ship_groups:
        for ship in group.ships:
            if ship.location == location:
                if ship.ship_type not in attacker_ships:
                    attacker_ships[ship.ship_type] = 0
                attacker_ships[ship.ship_type] += ship.count
                
                # Track taskforce composition for redirection
                tf_id = ship.task_force_id
                if tf_id not in attacker_taskforces:
                    attacker_taskforces[tf_id] = {}
                if ship.ship_type not in attacker_taskforces[tf_id]:
                    attacker_taskforces[tf_id][ship.ship_type] = 0
                attacker_taskforces[tf_id][ship.ship_type] += ship.count
    
    for group in defender_player.ship_groups:
        for ship in group.ships:
            if ship.location == location:
                if ship.ship_type not in defender_ships:
                    defender_ships[ship.ship_type] = 0
                defender_ships[ship.ship_type] += ship.count
                
                # Track taskforce composition for redirection
                tf_id = ship.task_force_id
                if tf_id not in defender_taskforces:
                    defender_taskforces[tf_id] = {}
                if ship.ship_type not in defender_taskforces[tf_id]:
                    defender_taskforces[tf_id][ship.ship_type] = 0
                defender_taskforces[tf_id][ship.ship_type] += ship.count
    
    # Check if either side has only non-combat ships (Rule 4.1.3)
    combat_ship_types = {ShipType.CORVETTE, ShipType.FIGHTER, ShipType.DEATH_STAR}
    
    attacker_warships = {k: v for k, v in attacker_ships.items() if k in combat_ship_types}
    defender_warships = {k: v for k, v in defender_ships.items() if k in combat_ship_types}
    
    # Rule 4.1.3: Immediate retreat only if BOTH sides have only unarmed ships
    if not attacker_warships and not defender_warships:
        print(f"   🏃 Both sides have only unarmed ships - immediate mutual retreat (Rule 4.1.3)")
        # Handle taskforce redirection for mutual retreat
        _handle_combat_redirection(game_state, attacker_player, attacker_taskforces, location, 'mutual_retreat')
        _handle_combat_redirection(game_state, defender_player, defender_taskforces, location, 'mutual_retreat')
        return True, 'mutual_retreat'
    
    # If one side has warships and other only unarmed, warships get one barrage
    if not attacker_warships and defender_warships:
        print(f"   ⚔️  {defender_player.name} warships attack {attacker_player.name} unarmed ships before retreat")
        resolve_one_barrage_attack(defender_warships, attacker_ships, defender_player, attacker_player)
        print(f"   🏃 {attacker_player.name} surviving ships retreat after barrage")
        # Handle taskforce redirection for attacker retreat
        _handle_combat_redirection(game_state, attacker_player, attacker_taskforces, location, 'attacker_retreat_after_barrage')
        return True, 'attacker_retreat_after_barrage'
    
    if not defender_warships and attacker_warships:
        print(f"   ⚔️  {attacker_player.name} warships attack {defender_player.name} unarmed ships before retreat")
        resolve_one_barrage_attack(attacker_warships, defender_ships, attacker_player, defender_player)
        print(f"   🏃 {defender_player.name} surviving ships retreat after barrage")
        # Handle taskforce redirection for defender retreat
        _handle_combat_redirection(game_state, defender_player, defender_taskforces, location, 'defender_retreat_after_barrage')
        return True, 'defender_retreat_after_barrage'
    
    print(f"   {attacker_player.name} warships: {', '.join([f'{count} {ship_type.value.lower()}' for ship_type, count in attacker_warships.items()])}")
    print(f"   {defender_player.name} warships: {', '.join([f'{count} {ship_type.value.lower()}' for ship_type, count in defender_warships.items()])}")
    
    # Simulate simplified combat (full combat would require target selection)
    # For simulation purposes, we'll do a quick resolution based on relative strength
    attacker_strength = sum(attacker_warships.values()) * 1.2  # Attacker advantage
    defender_strength = sum(defender_warships.values())
    
    if attacker_strength > defender_strength * 1.5:
        print(f"   💥 {attacker_player.name} achieves decisive victory!")
        # Handle defender retreat after decisive loss
        _handle_combat_redirection(game_state, defender_player, defender_taskforces, location, 'defender_defeat')
        return True, 'attacker_victory'
    elif defender_strength > attacker_strength:
        print(f"   🛡️  {defender_player.name} successfully defends!")
        # Handle attacker retreat after failed assault
        _handle_combat_redirection(game_state, attacker_player, attacker_taskforces, location, 'attacker_repelled')
        return True, 'defender_victory'
    else:
        print(f"   ⚡ Inconclusive battle - both sides withdraw")
        # Handle mutual withdrawal - both sides need new destinations
        _handle_combat_redirection(game_state, attacker_player, attacker_taskforces, location, 'mutual_withdrawal')
        _handle_combat_redirection(game_state, defender_player, defender_taskforces, location, 'mutual_withdrawal')
        return True, 'mutual_withdrawal'


def resolve_combat_phase(game_state, player, turn_number):
    """Resolve combat phase according to rules 4.1."""
    from simulation.simulation_utilities import print_phase_header
    
    print_phase_header(turn_number, "c", "COMBAT RESOLUTION")
    print(f"{player.name} checks for combat opportunities...")
    
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
                
                # Resolve combat
                combat_resolved, result = resolve_ship_combat(game_state, location, player, enemy_player)
                if combat_resolved:
                    combat_occurred = True
                    print(f"   📊 Combat result: {result}")
    
    if not combat_occurred:
        print("   No enemy ships encountered this turn")
    
    return combat_occurred


def resolve_colony_attacks(game_state, player, turn_number):
    """Resolve colony attack phase."""
    from simulation.simulation_utilities import print_phase_header
    
    print_phase_header(turn_number, "d", "COLONY ATTACKS")
    print(f"{player.name} checks for colony attack opportunities...")
    print("   No enemy colonies in range")
    return False


def _handle_combat_redirection(game_state, player, taskforces_at_location, location, combat_result):
    """Handle redirection of taskforces after combat events."""
    from stellar_conquest.ai.destination_selector import handle_taskforce_combat_redirect
    
    if not taskforces_at_location:
        return
    
    # Check if movement plans exist
    if not hasattr(game_state, 'movement_plans'):
        game_state.movement_plans = {}
    if player.player_id not in game_state.movement_plans:
        game_state.movement_plans[player.player_id] = {}
    
    # Handle each taskforce that was involved in combat
    for tf_id, ship_composition in taskforces_at_location.items():
        if tf_id == 1:  # TF1 (main base) doesn't move
            continue
            
        # Get original destination from movement plan
        original_destination = None
        if tf_id in game_state.movement_plans[player.player_id]:
            original_destination = game_state.movement_plans[player.player_id][tf_id].get('final_destination')
        
        if not original_destination:
            continue  # No movement plan to redirect
        
        # Use destination selector to choose new destination
        new_destination = handle_taskforce_combat_redirect(
            game_state, player, tf_id, location, original_destination,
            combat_result, ship_composition
        )
        
        if new_destination and new_destination != original_destination:
            # Update movement plan with new destination
            print(f"   🔄 TF{tf_id} redirected from {original_destination} to {new_destination} due to {combat_result}")
            
            # Calculate new path
            from stellar_conquest.utils.hex_utils import find_path
            new_path = find_path(location, new_destination)
            
            if new_path:
                game_state.movement_plans[player.player_id][tf_id].update({
                    'final_destination': new_destination,
                    'planned_path': new_path,
                    'path_index': 0,  # Reset path progress
                    'original_destination': original_destination,  # Keep track for logging
                    'redirected_due_to': combat_result,
                    'redirected_at_location': location
                })
            else:
                print(f"   ❌ Could not find path to new destination {new_destination} for TF{tf_id}")
        elif not new_destination:
            print(f"   ⚠️  No suitable redirect destination found for TF{tf_id} after {combat_result}")
        else:
            print(f"   ➡️  TF{tf_id} continues toward original destination {original_destination}")