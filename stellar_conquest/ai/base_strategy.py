"""Base strategy class for AI decision making."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from ..game.game_state import GameState
from ..entities.player import Player
from ..actions.base_action import BaseAction
from ..actions.movement_action import MovementAction, MovementOrder
from ..core.enums import ShipType


class GamePhase(Enum):
    """Different phases of the game for strategy adaptation."""
    EARLY_EXPLORATION = "early_exploration"  # Turns 1-12
    MID_EXPANSION = "mid_expansion"          # Turns 13-28  
    LATE_MILITARY = "late_military"          # Turns 29-44


class Priority(Enum):
    """Priority levels for different objectives."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    MINIMAL = 1


@dataclass
class StrategyWeights:
    """Weights for different strategic priorities."""
    exploration: float = 1.0
    colonization: float = 1.0
    military: float = 1.0
    research: float = 1.0
    economy: float = 1.0


class BaseStrategy(ABC):
    """Base class for AI strategy implementations."""
    
    def __init__(self, strategy_name: str, weights: StrategyWeights):
        self.strategy_name = strategy_name
        self.weights = weights
        self.decision_history: List[Dict[str, Any]] = []
    
    @abstractmethod
    def decide_turn_actions(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Decide what actions to take for this player's turn."""
        pass
    
    @abstractmethod
    def decide_production_spending(self, player: Player, game_state: GameState, 
                                 available_ip: int) -> Dict[str, int]:
        """Decide how to spend industrial points during production turns."""
        pass
    
    def get_game_phase(self, game_state: GameState) -> GamePhase:
        """Determine current game phase for strategy adaptation."""
        turn = game_state.current_turn
        if turn <= 12:
            return GamePhase.EARLY_EXPLORATION
        elif turn <= 28:
            return GamePhase.MID_EXPANSION
        else:
            return GamePhase.LATE_MILITARY
    
    def evaluate_exploration_targets(self, player: Player, game_state: GameState) -> List[Tuple[str, float]]:
        """Evaluate and rank star systems for exploration."""
        candidates = []
        
        # Find unexplored star systems within range
        for location, star_system in game_state.galaxy.star_systems.items():
            if player.player_id not in star_system.explored_by:
                # Check if player has ships that can reach this system
                reachable = self._is_location_reachable(location, player, game_state)
                if reachable:
                    score = self._score_exploration_target(location, star_system, player, game_state)
                    candidates.append((location, score))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates
    
    def evaluate_colonization_targets(self, player: Player, game_state: GameState) -> List[Tuple[str, float]]:
        """Evaluate and rank planets for colonization."""
        candidates = []
        
        # Find habitable planets that player has discovered
        for location, star_system in game_state.galaxy.star_systems.items():
            if player.player_id in star_system.explored_by:
                for planet in star_system.planets:
                    # Check if planet is colonizable and unoccupied
                    if self._is_planet_colonizable(planet, player) and not self._is_planet_occupied(location, game_state):
                        score = self._score_colonization_target(location, planet, player, game_state)
                        candidates.append((location, score))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates
    
    def evaluate_military_targets(self, player: Player, game_state: GameState) -> List[Tuple[str, float]]:
        """Evaluate and rank military targets for attack."""
        candidates = []
        
        for location in game_state.galaxy.star_systems.keys():
            # Look for enemy colonies or valuable systems to attack
            enemy_presence = self._assess_enemy_strength(location, player, game_state)
            if enemy_presence["total_strength"] > 0:
                score = self._score_military_target(location, enemy_presence, player, game_state)
                candidates.append((location, score))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates
    
    def _is_location_reachable(self, location: str, player: Player, game_state: GameState) -> bool:
        """Check if player has ships that can reach the location."""
        max_speed = player.current_ship_speed
        
        for fleet in player.fleets:
            distance = game_state.galaxy.calculate_distance(fleet.location, location)
            if distance <= max_speed:
                return True
        return False
    
    def _score_exploration_target(self, location: str, star_system, player: Player, game_state: GameState) -> float:
        """Score an exploration target based on strategy."""
        base_score = 1.0
        
        # Prefer star colors more likely to have valuable planets
        color_bonus = {
            "yellow": 2.0,  # More likely to have Terran planets
            "blue": 1.5,    # More likely to have mineral-rich planets
            "green": 1.2,
            "orange": 1.0,
            "red": 0.8
        }
        base_score *= color_bonus.get(star_system.color.value, 1.0)
        
        # Distance penalty (closer is better)
        min_distance = min(
            game_state.galaxy.calculate_distance(fleet.location, location)
            for fleet in player.fleets
        )
        distance_penalty = 1.0 / (1.0 + min_distance * 0.1)
        
        return base_score * distance_penalty
    
    def _score_colonization_target(self, location: str, planet, player: Player, game_state: GameState) -> float:
        """Score a colonization target."""
        base_score = 0.0
        
        # Score based on planet type
        type_scores = {
            "terran": 5.0,
            "sub_terran": 3.0,
            "minimal_terran": 1.5,
            "barren": 0.5
        }
        base_score += type_scores.get(planet.planet_type.value, 0.0)
        
        # Population capacity bonus
        base_score += planet.max_population * 0.05
        
        # Mineral-rich bonus
        if planet.is_mineral_rich:
            base_score *= 1.5
        
        return base_score
    
    def _score_military_target(self, location: str, enemy_presence: Dict, player: Player, game_state: GameState) -> float:
        """Score a military target."""
        # Balance target value vs difficulty
        target_value = enemy_presence.get("colony_value", 0)
        enemy_strength = enemy_presence.get("total_strength", 0)
        
        if enemy_strength == 0:
            return 0.0
        
        # Simple value/cost ratio
        return target_value / enemy_strength
    
    def _is_planet_colonizable(self, planet, player: Player) -> bool:
        """Check if player can colonize this planet type."""
        if planet.planet_type.value == "barren":
            return player.can_colonize_barren()
        return True
    
    def _is_planet_occupied(self, location: str, game_state: GameState) -> bool:
        """Check if any planet at location has a colony."""
        for player in game_state.players.values():
            if player.get_colony_at_location(location):
                return True
        return False
    
    def _assess_enemy_strength(self, location: str, player: Player, game_state: GameState) -> Dict[str, Any]:
        """Assess enemy military strength at a location."""
        total_strength = 0
        colony_value = 0
        ship_counts = {}
        
        for other_player_id, other_player in game_state.players.items():
            if other_player_id == player.player_id:
                continue
            
            # Count enemy ships
            enemy_fleet = other_player.get_fleet_at_location(location)
            if enemy_fleet:
                for ship_type, count in enemy_fleet.ship_counts.items():
                    ship_counts[ship_type] = ship_counts.get(ship_type, 0) + count
                    total_strength += self._get_ship_combat_value(ship_type) * count
            
            # Assess enemy colonies
            enemy_colonies = other_player.get_colony_at_location(location)
            for colony in enemy_colonies:
                colony_value += self._get_colony_value(colony)
                total_strength += colony.missile_bases + colony.advanced_missile_bases * 2
        
        return {
            "total_strength": total_strength,
            "colony_value": colony_value,
            "ship_counts": ship_counts
        }
    
    def _get_ship_combat_value(self, ship_type) -> float:
        """Get relative combat value of ship type."""
        values = {
            "scout": 0.0,
            "colony_transport": 0.0,
            "corvette": 1.0,
            "fighter": 2.5,
            "death_star": 6.0
        }
        return values.get(ship_type.value if hasattr(ship_type, 'value') else str(ship_type), 0.0)
    
    def _get_colony_value(self, colony) -> float:
        """Estimate strategic value of a colony."""
        base_value = colony.population * 0.1
        base_value += colony.factories * 2.0
        
        if colony.planet.planet_type.value == "terran":
            base_value *= 2.0
        elif colony.planet.planet_type.value == "sub_terran":
            base_value *= 1.5
        
        if colony.planet.is_mineral_rich:
            base_value *= 1.5
        
        return base_value
    
    def evaluate_victory_point_positions(self, player: Player, game_state: GameState) -> List[Tuple[str, float]]:
        """Evaluate star systems for Rule C victory point control (ships in unoccupied systems)."""
        candidates = []
        
        # Look for star systems with unoccupied planets that give victory points
        for location, star_system in game_state.galaxy.star_systems.items():
            if player.player_id in star_system.explored_by:
                # Check if system has unoccupied planets with victory points
                unoccupied_vp_planets = []
                for planet in star_system.planets:
                    if planet.victory_points > 0:
                        # Check if this specific planet is unoccupied
                        is_unoccupied = True
                        for other_player in game_state.players:
                            for colony in other_player.colonies:
                                if (colony.location == location and colony.is_active and 
                                    (colony.planet == planet or id(colony.planet) == id(planet))):
                                    is_unoccupied = False
                                    break
                            if not is_unoccupied:
                                break
                        
                        if is_unoccupied:
                            unoccupied_vp_planets.append(planet)
                
                if unoccupied_vp_planets:
                    # Calculate value of controlling this system
                    total_vp = sum(planet.victory_points for planet in unoccupied_vp_planets)
                    
                    # Check if we already have ships there
                    has_ships = player.get_ship_group_at_location(location) is not None
                    
                    # Check for enemy ships (reduces value)
                    enemy_presence = self._assess_enemy_strength(location, player, game_state)
                    enemy_penalty = enemy_presence["total_strength"] * 0.1
                    
                    score = total_vp - enemy_penalty
                    if not has_ships:
                        score *= 2.0  # Double value if we need to send ships
                    
                    candidates.append((location, score))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def evaluate_colony_attack_targets(self, player: Player, game_state: GameState) -> List[Tuple[str, Dict[str, Any]]]:
        """Review discovered enemy colonies and evaluate them for attack opportunities."""
        attack_targets = []
        
        # Look for discovered enemy colonies (from exploration/intelligence)
        for location, star_system in game_state.galaxy.star_systems.items():
            if player.player_id in star_system.explored_by:
                # Check each enemy player for colonies at this location
                for other_player in game_state.players:
                    if other_player.player_id == player.player_id:
                        continue
                    
                    enemy_colonies = other_player.get_colonies_at_location(location)
                    if enemy_colonies:
                        # Rule: Can only attack if no enemy ships present
                        enemy_ship_group = other_player.get_ship_group_at_location(location)
                        has_enemy_ships = enemy_ship_group and enemy_ship_group.get_total_ships() > 0
                        
                        if not has_enemy_ships:
                            for colony in enemy_colonies:
                                # Evaluate colony value and attack feasibility
                                target_value = self._evaluate_colony_attack_value(colony, location, other_player, game_state)
                                
                                target_info = {
                                    'enemy_player': other_player.name,
                                    'colony': colony,
                                    'location': location,
                                    'value_score': target_value,
                                    'population': colony.population,
                                    'factories': colony.factories,
                                    'missile_bases': colony.missile_bases,
                                    'advanced_missile_bases': colony.advanced_missile_bases,
                                    'has_planet_shield': colony.has_planet_shield,
                                    'planet_type': colony.planet.planet_type.value,
                                    'mineral_rich': colony.planet.is_mineral_rich,
                                    'is_attackable': not colony.has_planet_shield,
                                    'defense_strength': colony.missile_bases + (colony.advanced_missile_bases * 2)
                                }
                                
                                if target_info['is_attackable'] and target_value > 0:
                                    attack_targets.append((location, target_info))
        
        # Sort by value (best targets first)
        attack_targets.sort(key=lambda x: x[1]['value_score'], reverse=True)
        return attack_targets
    
    def evaluate_colony_defense_needs(self, player: Player, game_state: GameState) -> List[Tuple[str, Dict[str, Any]]]:
        """Evaluate which of player's colonies need defensive reinforcement."""
        defense_needs = []
        
        for colony in player.colonies:
            if colony.is_active:
                location = colony.location
                
                # Assess threat level to this colony
                threat_assessment = self._assess_colony_threat_level(colony, location, player, game_state)
                
                if threat_assessment['threat_level'] > 0:
                    defense_info = {
                        'colony': colony,
                        'location': location,
                        'threat_level': threat_assessment['threat_level'],
                        'nearby_enemies': threat_assessment['nearby_enemies'],
                        'colony_value': self._get_colony_value(colony),
                        'current_defense': colony.missile_bases + (colony.advanced_missile_bases * 2),
                        'has_warships': player.get_ship_group_at_location(location) is not None,
                        'population': colony.population,
                        'factories': colony.factories,
                        'planet_type': colony.planet.planet_type.value,
                        'mineral_rich': colony.planet.is_mineral_rich,
                        'needs_warships': threat_assessment['threat_level'] >= 3,
                        'needs_missile_bases': threat_assessment['threat_level'] >= 2
                    }
                    
                    defense_needs.append((location, defense_info))
        
        # Sort by threat level and colony value
        defense_needs.sort(key=lambda x: (x[1]['threat_level'], x[1]['colony_value']), reverse=True)
        return defense_needs

    def _evaluate_colony_attack_value(self, colony, location: str, enemy_player: Player, game_state: GameState) -> float:
        """Calculate the strategic value of attacking an enemy colony."""
        if colony.has_planet_shield:
            return 0.0  # Cannot attack shielded colonies
        
        value = 0.0
        
        # Base value from colony productivity
        base_value = colony.population * 0.1  # Population value
        base_value += colony.factories * 2.0  # Factory value
        
        # Planet type multiplier
        if colony.planet.planet_type.value == "terran":
            base_value *= 2.0
        elif colony.planet.planet_type.value == "sub_terran":
            base_value *= 1.5
        
        # Mineral rich bonus
        if colony.planet.is_mineral_rich:
            base_value *= 1.5
        
        value += base_value
        
        # Strategic location bonus (near our colonies)
        nearby_own_colonies = len(self._get_nearby_own_colonies(location, enemy_player, game_state))
        value += nearby_own_colonies * 2.0
        
        # Defense penalty (harder to conquer)
        defense_strength = colony.missile_bases + (colony.advanced_missile_bases * 2)
        value -= defense_strength * 1.5
        
        # Conquest benefits (will provide production after first turn)
        future_production = colony.population + (colony.factories * (2.0 if colony.planet.is_mineral_rich else 1.0))
        value += future_production * 0.5
        
        return max(0.0, value)

    def _assess_colony_threat_level(self, colony, location: str, player: Player, game_state: GameState) -> Dict[str, Any]:
        """Assess the threat level to a specific colony."""
        threat_level = 0
        nearby_enemies = []
        
        # Check for enemy ships in same system
        for other_player in game_state.players:
            if other_player.player_id == player.player_id:
                continue
            
            enemy_ship_group = other_player.get_ship_group_at_location(location)
            if enemy_ship_group and enemy_ship_group.get_total_ships() > 0:
                warships = sum(ship.count for ship in enemy_ship_group.ships if ship.is_warship)
                if warships > 0:
                    threat_level = max(threat_level, 4)  # Direct threat
                    nearby_enemies.append({
                        'player': other_player.name,
                        'location': location,
                        'warships': warships,
                        'distance': 0
                    })
        
        # Check adjacent systems for enemy presence
        from ..utils.hex_utils import get_adjacent_hexes
        adjacent_hexes = get_adjacent_hexes(location)
        
        for adj_hex in adjacent_hexes:
            for other_player in game_state.players:
                if other_player.player_id == player.player_id:
                    continue
                
                enemy_ship_group = other_player.get_ship_group_at_location(adj_hex)
                if enemy_ship_group and enemy_ship_group.get_total_ships() > 0:
                    warships = sum(ship.count for ship in enemy_ship_group.ships if ship.is_warship)
                    if warships > 0:
                        threat_level = max(threat_level, 2)  # Adjacent threat
                        nearby_enemies.append({
                            'player': other_player.name,
                            'location': adj_hex,
                            'warships': warships,
                            'distance': 1
                        })
        
        return {
            'threat_level': threat_level,
            'nearby_enemies': nearby_enemies
        }

    def _get_nearby_own_colonies(self, location: str, player: Player, game_state: GameState) -> List[str]:
        """Get list of player's colonies near a location."""
        nearby_colonies = []
        from ..utils.hex_utils import calculate_hex_distance
        
        for colony in player.colonies:
            if colony.is_active:
                distance = calculate_hex_distance(location, colony.location)
                if distance <= 3:  # Within 3 hexes
                    nearby_colonies.append(colony.location)
        
        return nearby_colonies

    def split_oversized_scout_task_forces(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Split task forces with >5 scouts into smaller exploration units."""
        actions = []
        next_task_force_id = self._get_next_task_force_id(player)
        
        for ship_group in player.ship_groups[:]:  # Copy list to avoid modification issues
            oversized_scout_groups = []
            
            # Find scout groups with more than 5 ships
            for ship in ship_group.ships:
                if ship.ship_type.value == "scout" and ship.count > 5:
                    oversized_scout_groups.append(ship)
            
            if oversized_scout_groups:
                # Get potential exploration targets for new task forces
                exploration_targets = self.evaluate_exploration_targets(player, game_state)
                target_index = 0
                
                for scout_ship in oversized_scout_groups:
                    total_scouts = scout_ship.count
                    location = ship_group.location
                    
                    # Calculate how many new task forces we need
                    task_forces_needed = (total_scouts - 1) // 5  # Keep 5 or less in original
                    scouts_to_split = total_scouts - 5  # Keep 5 in original group
                    
                    if scouts_to_split > 0 and task_forces_needed > 0:
                        split_orders = []
                        scouts_split_so_far = 0
                        
                        for tf_num in range(task_forces_needed):
                            # Determine size of new task force (5 or remaining)
                            scouts_for_this_tf = min(5, scouts_to_split - scouts_split_so_far)
                            
                            if scouts_for_this_tf > 0:
                                # Find destination for this new task force
                                destination = location  # Default: stay at current location
                                if target_index < len(exploration_targets):
                                    destination = exploration_targets[target_index][0]
                                    target_index += 1
                                
                                # Create movement order to split scouts to new destination
                                split_orders.append(MovementOrder(
                                    from_location=location,
                                    ship_type=ShipType.SCOUT,
                                    count=scouts_for_this_tf,
                                    to_location=destination,
                                    task_force_id=next_task_force_id
                                ))
                                
                                scouts_split_so_far += scouts_for_this_tf
                                next_task_force_id += 1
                        
                        if split_orders:
                            actions.append(MovementAction(player.player_id, split_orders))
                            
                            self.log_decision("scout_task_force_split", {
                                "original_location": location,
                                "total_scouts": total_scouts,
                                "new_task_forces": len(split_orders),
                                "scouts_per_new_tf": [order.count for order in split_orders],
                                "destinations": [order.to_location for order in split_orders]
                            })
        
        return actions

    def _get_next_task_force_id(self, player: Player) -> int:
        """Get the next available task force ID for a player."""
        used_ids = set()
        
        for ship_group in player.ship_groups:
            for ship in ship_group.ships:
                if ship.task_force_id is not None:
                    used_ids.add(ship.task_force_id)
        
        # Find first unused ID starting from 1
        next_id = 1
        while next_id in used_ids:
            next_id += 1
        
        return next_id

    def log_decision(self, decision_type: str, decision_data: Dict[str, Any]):
        """Log a strategic decision for analysis."""
        log_entry = {
            "decision_type": decision_type,
            "data": decision_data,
            "strategy": self.strategy_name
        }
        self.decision_history.append(log_entry)