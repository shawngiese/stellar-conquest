"""
Destination Selection Module for Taskforces After Combat

This module handles intelligent destination selection for taskforces that have been
forced to retreat, fled from combat, or were pushed out due to having non-warship ships.
"""

import random
from typing import List, Optional, Tuple, Dict, Any
from ..core.enums import ShipType
from ..entities.player import Player
from ..game.game_state import GameState


class TaskforceDestinationSelector:
    """Handles intelligent destination selection for taskforces after combat events."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        
    def select_new_destination_after_combat(
        self, 
        player: Player, 
        taskforce_id: int,
        current_location: str,
        original_destination: str,
        combat_result: str,
        has_warships: bool,
        has_unarmed_ships: bool
    ) -> Optional[str]:
        """
        Select a new destination for a taskforce after combat.
        
        Args:
            player: The player who owns the taskforce
            taskforce_id: ID of the taskforce needing new destination
            current_location: Where the taskforce currently is
            original_destination: Where they were originally headed
            combat_result: Result of the combat that caused the retreat
            has_warships: Whether taskforce contains warships
            has_unarmed_ships: Whether taskforce contains scouts/transports
            
        Returns:
            New destination hex or None if no suitable destination found
        """
        # Get potential destinations based on taskforce composition
        candidate_destinations = self._get_candidate_destinations(
            player, current_location, original_destination, has_warships, has_unarmed_ships
        )
        
        if not candidate_destinations:
            return self._select_safe_fallback_destination(player, current_location)
            
        # Evaluate and rank destinations
        evaluated_destinations = self._evaluate_destinations(
            player, candidate_destinations, current_location, combat_result
        )
        
        if evaluated_destinations:
            # Select best destination (highest score)
            return evaluated_destinations[0][0]  # (destination, score) tuple
        
        return self._select_safe_fallback_destination(player, current_location)
    
    def _get_candidate_destinations(
        self, 
        player: Player, 
        current_location: str, 
        original_destination: str,
        has_warships: bool,
        has_unarmed_ships: bool
    ) -> List[str]:
        """Get list of potential destinations based on taskforce capabilities."""
        candidates = []
        
        # Avoid the original destination to prevent constant attempts to return
        forbidden_locations = {original_destination, current_location}
        
        # Get accessible star systems within communication range
        star_systems = self.game_state.galaxy.star_systems
        max_range = 8  # Command post range
        
        for star_hex, star_system in star_systems.items():
            if star_hex in forbidden_locations:
                continue
                
            # Check if within command post range
            if not self._is_within_command_range(player, star_hex, max_range):
                continue
                
            # For taskforces with only unarmed ships, prioritize safe locations
            if not has_warships and has_unarmed_ships:
                if self._is_location_safe_for_unarmed(player, star_hex):
                    candidates.append(star_hex)
            else:
                # Warships can consider more aggressive destinations
                candidates.append(star_hex)
        
        return candidates
    
    def _evaluate_destinations(
        self, 
        player: Player, 
        candidates: List[str], 
        current_location: str,
        combat_result: str
    ) -> List[Tuple[str, float]]:
        """Evaluate and rank potential destinations by strategic value."""
        evaluated = []
        
        for destination in candidates:
            score = self._calculate_destination_score(
                player, destination, current_location, combat_result
            )
            evaluated.append((destination, score))
        
        # Sort by score (descending - highest score first)
        evaluated.sort(key=lambda x: x[1], reverse=True)
        return evaluated
    
    def _calculate_destination_score(
        self, 
        player: Player, 
        destination: str, 
        current_location: str,
        combat_result: str
    ) -> float:
        """Calculate strategic value score for a destination."""
        score = 0.0
        
        # Distance factor - prefer closer destinations for quick repositioning
        distance = self.game_state.galaxy.calculate_distance(current_location, destination)
        if distance <= 4:
            score += 3.0  # Very close
        elif distance <= 6:
            score += 2.0  # Close
        else:
            score += 1.0  # Distant
        
        # Safety factor - avoid enemy-occupied systems
        if self._has_enemy_presence(player, destination):
            score -= 5.0  # Strong penalty for enemy presence
        
        # Strategic value - unexplored systems have potential
        star_system = self.game_state.galaxy.star_systems.get(destination)
        if star_system and not star_system.is_explored:
            score += 2.0  # Exploration opportunity
        
        # Friendly presence bonus
        if self._has_friendly_presence(player, destination):
            score += 1.5  # Safer with friendly forces nearby
        
        # Colonization opportunity
        if self._has_colonization_potential(player, destination):
            score += 2.5  # High value for colony opportunities
        
        # Adjust based on combat result
        if 'retreat' in combat_result:
            # After retreat, prefer safer, more defensive positions
            score += self._get_defensive_position_bonus(player, destination)
        elif 'barrage' in combat_result:
            # After taking losses to barrage, prefer positions with better protection
            score += self._get_protection_bonus(player, destination)
        
        return score
    
    def _is_within_command_range(self, player: Player, destination: str, max_range: int) -> bool:
        """Check if destination is within command post range."""
        # Check distance to all command posts
        for command_post_hex in player.command_posts:
            distance = self.game_state.galaxy.calculate_distance(destination, command_post_hex)
            if distance <= max_range:
                return True
        
        # Check distance to entry hex (acts as command post)
        entry_hex = self.game_state.galaxy.entry_hexes.get(player.player_id)
        if entry_hex:
            distance = self.game_state.galaxy.calculate_distance(destination, entry_hex)
            if distance <= max_range:
                return True
        
        return False
    
    def _is_location_safe_for_unarmed(self, player: Player, location: str) -> bool:
        """Check if location is safe for unarmed ships (scouts/transports)."""
        # Location is unsafe if enemies are present
        return not self._has_enemy_presence(player, location)
    
    def _has_enemy_presence(self, player: Player, location: str) -> bool:
        """Check if location has enemy ships."""
        for other_player in self.game_state.players.values():
            if other_player.player_id == player.player_id:
                continue
            
            fleet = other_player.get_fleet_at_location(location)
            if fleet and fleet.total_ships > 0:
                return True
        
        return False
    
    def _has_friendly_presence(self, player: Player, location: str) -> bool:
        """Check if location has friendly ships."""
        fleet = player.get_fleet_at_location(location)
        return fleet is not None and fleet.total_ships > 0
    
    def _has_colonization_potential(self, player: Player, location: str) -> bool:
        """Check if location has planets that can be colonized."""
        star_system = self.game_state.galaxy.star_systems.get(location)
        if not star_system:
            return False
        
        # Check for uncolonized habitable planets
        for planet in star_system.planets:
            if planet.is_habitable and not planet.colony:
                return True
        
        return False
    
    def _get_defensive_position_bonus(self, player: Player, destination: str) -> float:
        """Get bonus score for defensive positioning."""
        # Positions closer to friendly territory get higher bonus
        min_distance_to_friendly = float('inf')
        
        for colony in player.colonies:
            distance = self.game_state.galaxy.calculate_distance(destination, colony.location)
            min_distance_to_friendly = min(min_distance_to_friendly, distance)
        
        if min_distance_to_friendly <= 2:
            return 2.0  # Very close to friendly territory
        elif min_distance_to_friendly <= 4:
            return 1.0  # Moderately close
        else:
            return 0.0  # Far from friendly territory
    
    def _get_protection_bonus(self, player: Player, destination: str) -> float:
        """Get bonus score for protective positioning."""
        # Systems with defensive structures or friendly fleets get bonus
        star_system = self.game_state.galaxy.star_systems.get(destination)
        if not star_system:
            return 0.0
        
        protection_bonus = 0.0
        
        # Check for defensive colonies
        for planet in star_system.planets:
            if planet.colony and planet.colony.player_id == player.player_id:
                if planet.colony.missile_bases > 0:
                    protection_bonus += 1.5  # Missile base protection
                if planet.colony.population > 5:  # 5M+ population
                    protection_bonus += 1.0  # Strong colony protection
        
        return protection_bonus
    
    def _select_safe_fallback_destination(self, player: Player, current_location: str) -> Optional[str]:
        """Select a safe fallback destination when no good options exist."""
        # Get adjacent hexes as last resort
        adjacent_hexes = self.game_state.galaxy.get_adjacent_hexes(current_location)
        
        # Filter out enemy-occupied adjacent hexes
        safe_adjacent = []
        for hex_coord in adjacent_hexes:
            if not self._has_enemy_presence(player, hex_coord):
                safe_adjacent.append(hex_coord)
        
        if safe_adjacent:
            return random.choice(safe_adjacent)
        
        # If no safe adjacent hexes, find the closest friendly colony
        closest_colony = None
        min_distance = float('inf')
        
        for colony in player.colonies:
            distance = self.game_state.galaxy.calculate_distance(current_location, colony.location)
            if distance < min_distance:
                min_distance = distance
                closest_colony = colony.location
        
        return closest_colony


def handle_taskforce_combat_redirect(
    game_state: GameState,
    player: Player,
    taskforce_id: int,
    current_location: str,
    original_destination: str,
    combat_result: str,
    ship_types_present: Dict[ShipType, int]
) -> Optional[str]:
    """
    Handle redirection of taskforce after combat event.
    
    This function should be called when a taskforce flees or is pushed out of combat
    to automatically select a new strategic destination.
    """
    # Analyze taskforce composition
    has_warships = any(
        ship_type in [ShipType.CORVETTE, ShipType.FIGHTER, ShipType.DEATH_STAR] 
        for ship_type in ship_types_present.keys()
    )
    has_unarmed_ships = any(
        ship_type in [ShipType.SCOUT, ShipType.COLONY_TRANSPORT] 
        for ship_type in ship_types_present.keys()
    )
    
    # Get destination selector
    selector = TaskforceDestinationSelector(game_state)
    
    # Select new destination
    new_destination = selector.select_new_destination_after_combat(
        player, taskforce_id, current_location, original_destination,
        combat_result, has_warships, has_unarmed_ships
    )
    
    if new_destination:
        # Log the redirection decision
        game_state.log_action("taskforce_redirected", {
            "player_id": player.player_id,
            "taskforce_id": taskforce_id,
            "from_location": current_location,
            "original_destination": original_destination,
            "new_destination": new_destination,
            "combat_result": combat_result,
            "ship_composition": {st.value: count for st, count in ship_types_present.items()}
        })
    
    return new_destination