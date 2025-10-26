"""
Stellar Conquest Simulation Package

A modular simulation system for the Stellar Conquest board game.

Modules:
- combat_system: Combat resolution and ship interactions
- movement_system: Ship movement and task force management  
- ai_strategy: AI decision making and strategy implementation
- simulation_utilities: Helper functions and utilities
"""

from .combat_system import (
    check_enemy_ships_at_location,
    is_star_hex,
    resolve_combat_phase,
    resolve_colony_attacks,
    resolve_ship_combat,
    get_combat_value
)

from .movement_system import (
    make_movement_decisions,
    place_starting_fleet_with_task_force_id,
    split_ships_into_task_force,
    move_ships_with_task_force_id,
    plan_next_move_toward_target,
    generate_route_display
)

from .ai_strategy import (
    bonus_ip_spending_phase,
    create_exploration_task_forces,
    determine_player_strategy,
    add_ships_to_main_fleet
)

from .simulation_utilities import (
    print_turn_header,
    print_phase_header,
    show_player_status,
    analyze_player_strategy,
    find_nearest_stars,
    find_nearest_yellow_stars,
    calculate_hex_distance,
    auto_explore_yellow_star,
    choose_new_destination
)

__all__ = [
    # Combat system
    'check_enemy_ships_at_location',
    'is_star_hex', 
    'resolve_combat_phase',
    'resolve_colony_attacks',
    'resolve_ship_combat',
    'get_combat_value',
    
    # Movement system
    'make_movement_decisions',
    'place_starting_fleet_with_task_force_id',
    'split_ships_into_task_force',
    'move_ships_with_task_force_id',
    'plan_next_move_toward_target',
    'generate_route_display',
    
    # AI strategy
    'bonus_ip_spending_phase',
    'create_exploration_task_forces',
    'determine_player_strategy',
    'add_ships_to_main_fleet',
    
    # Utilities
    'print_turn_header',
    'print_phase_header',
    'show_player_status',
    'analyze_player_strategy',
    'find_nearest_stars',
    'find_nearest_yellow_stars',
    'calculate_hex_distance',
    'auto_explore_yellow_star',
    'choose_new_destination'
]