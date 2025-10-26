"""Player entity for Stellar Conquest."""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict

from ..core.enums import PlayStyle, Technology, ShipType
from ..core.exceptions import ValidationError, InsufficientResourcesError, TechnologyNotAvailableError, InvalidActionError
from ..core.constants import (
    STARTING_FLEET, STARTING_BONUS_IP, TECHNOLOGY_COSTS, TECHNOLOGY_PREREQUISITES,
    SHIP_COSTS, DEFAULT_SHIP_SPEED, COMMAND_POST_RANGE
)
from ..data import get_technology_data
from ..utils.validation import GameValidator, Validator
from .base import GameEntity
from .ship import Ship, ShipGroup
from .colony import Colony


@dataclass
class ResearchProgress:
    """Tracks progress toward a technology."""
    technology: Technology
    invested_ip: int = 0
    completed: bool = False
    
    def add_investment(self, ip: int) -> bool:
        """Add IP investment. Returns True if completed."""
        self.invested_ip += ip
        required_ip = TECHNOLOGY_COSTS.get(self.technology, 50)
        
        if self.invested_ip >= required_ip:
            self.completed = True
            return True
        return False
    
    def get_completion_percentage(self) -> float:
        """Get completion percentage (0.0 to 1.0)."""
        required_ip = TECHNOLOGY_COSTS.get(self.technology, 50)
        return min(1.0, self.invested_ip / required_ip)


@dataclass
class Player(GameEntity):
    """Represents a player in the game."""
    
    name: str = ""
    play_style: PlayStyle = PlayStyle.BALANCED
    entry_hex: str = "A1"
    
    # Game entities
    colonies: List[Colony] = field(default_factory=list)
    ship_groups: List[ShipGroup] = field(default_factory=list)
    command_posts: Set[str] = field(default_factory=set)
    
    # Technologies
    completed_technologies: Set[Technology] = field(default_factory=set)
    research_progress: Dict[Technology, ResearchProgress] = field(default_factory=dict)
    
    # Turn tracking
    turns_completed: int = 0
    
    def validate(self) -> None:
        """Validate player state."""
        super().validate()
        
        GameValidator.validate_player_name(self.name)
        Validator.validate_enum(self.play_style, PlayStyle, "play_style")
        GameValidator.validate_hex_coordinate(self.entry_hex)
        Validator.validate_non_negative(self.turns_completed, "turns_completed")
        
        # Validate colonies
        for colony in self.colonies:
            colony.validate()
            if colony.player_id != self.player_id:
                raise ValidationError(f"Colony {colony.id} has wrong owner")
        
        # Validate ship groups
        for group in self.ship_groups:
            if group.player_id != self.player_id:
                raise ValidationError(f"Ship group at {group.location} has wrong owner")
        
        # Validate command posts
        for command_post in self.command_posts:
            GameValidator.validate_hex_coordinate(command_post)
    
    @property
    def player_id(self) -> int:
        """Get player ID from game ID parsing or other mechanism."""
        # This would be set by the game when creating players
        # For now, return a placeholder
        return getattr(self, '_player_id', 1)
    
    @player_id.setter
    def player_id(self, value: int):
        """Set player ID."""
        GameValidator.validate_player_id(value)
        self._player_id = value
    
    @property
    def has_entered_board(self) -> bool:
        """Check if player has entered the board with their starting fleet."""
        return len(self.ship_groups) > 0
    
    def initialize_starting_fleet(self) -> None:
        """Initialize starting fleet off-board. Called at game start."""
        # Starting fleet is stored as a special off-board group
        # This represents ships that haven't entered the board yet
        self.starting_fleet_remaining = STARTING_FLEET.copy()
    
    def place_starting_fleet_on_board(self) -> None:
        """Place the entire starting fleet at the entry hex (first turn only)."""
        if self.has_entered_board:
            raise InvalidActionError("Starting fleet already placed")
        
        if not hasattr(self, 'starting_fleet_remaining'):
            self.initialize_starting_fleet()
        
        # Place all starting ships at entry hex
        for ship_type, count in self.starting_fleet_remaining.items():
            if count > 0:
                self.add_ships_at_location(self.entry_hex, ship_type, count)
        
        # Clear the starting fleet
        self.starting_fleet_remaining.clear()
    
    @property
    def current_ship_speed(self) -> int:
        """Current maximum ship movement in hexes."""
        speed_techs = [
            (Technology.SPEED_8_HEX, 8),
            (Technology.SPEED_7_HEX, 7),
            (Technology.SPEED_6_HEX, 6),
            (Technology.SPEED_5_HEX, 5),
            (Technology.SPEED_4_HEX, 4),
            (Technology.SPEED_3_HEX, 3)
        ]
        
        for tech, speed in speed_techs:
            if tech in self.completed_technologies:
                return speed
        
        return DEFAULT_SHIP_SPEED
    
    @property
    def has_unlimited_range(self) -> bool:
        """Check if ships can move beyond command post limit."""
        return Technology.UNLIMITED_SHIP_RANGE in self.completed_technologies
    
    @property
    def has_unlimited_communication(self) -> bool:
        """Check if ships can change destinations from any hex."""
        return Technology.UNLIMITED_SHIP_COMMUNICATION in self.completed_technologies
    
    @property
    def has_improved_weaponry(self) -> bool:
        """Check if warships get extra attacks on misses."""
        return Technology.IMPROVED_SHIP_WEAPONRY in self.completed_technologies
    
    @property
    def total_population(self) -> int:
        """Get total population across all colonies."""
        return sum(colony.population for colony in self.colonies if colony.is_active)
    
    @property
    def total_factories(self) -> int:
        """Get total factories across all colonies."""
        return sum(colony.factories for colony in self.colonies if colony.is_active)
    
    @property
    def total_ships(self) -> int:
        """Get total number of ships."""
        return sum(group.get_total_ships() for group in self.ship_groups)
    
    @property
    def total_industrial_output(self) -> int:
        """Get total industrial production this turn."""
        return sum(colony.calculate_industrial_points() for colony in self.colonies if colony.can_produce)
    
    def can_build_ship_type(self, ship_type: ShipType) -> bool:
        """Check if player can build a specific ship type."""
        if ship_type in [ShipType.SCOUT, ShipType.COLONY_TRANSPORT, ShipType.CORVETTE]:
            return True
        elif ship_type == ShipType.FIGHTER:
            return Technology.FIGHTER_SHIP in self.completed_technologies
        elif ship_type == ShipType.DEATH_STAR:
            return Technology.DEATH_STAR in self.completed_technologies
        return False
    
    def can_colonize_barren(self) -> bool:
        """Check if player can colonize barren planets."""
        return Technology.CONTROLLED_ENVIRONMENT_TECH in self.completed_technologies
    
    def can_build_factories(self) -> bool:
        """Check if player can build factories."""
        return Technology.INDUSTRIAL_TECHNOLOGY in self.completed_technologies
    
    def get_factory_limit_per_population(self) -> Optional[int]:
        """Get factory limit per million population."""
        if Technology.ROBOTIC_INDUSTRY in self.completed_technologies:
            return None  # No limit
        elif Technology.IMPROVED_INDUSTRIAL_TECH in self.completed_technologies:
            return 2  # 2 per million
        elif Technology.INDUSTRIAL_TECHNOLOGY in self.completed_technologies:
            return 1  # 1 per million
        else:
            return 0  # Can't build factories
    
    def get_ship_group_at_location(self, location: str) -> Optional[ShipGroup]:
        """Get ship group at a specific hex, if any."""
        for group in self.ship_groups:
            if group.location == location:
                return group
        return None
    
    def get_colonies_at_location(self, location: str) -> List[Colony]:
        """Get all colonies at a specific hex."""
        return [colony for colony in self.colonies if colony.location == location]
    
    def get_all_locations(self) -> Set[str]:
        """Get all hex locations where player has presence."""
        locations = set()
        
        # Add ship locations
        for group in self.ship_groups:
            locations.add(group.location)
        
        # Add colony locations
        for colony in self.colonies:
            locations.add(colony.location)
        
        return locations
    
    def add_colony(self, colony: Colony) -> None:
        """Add a colony to this player."""
        colony.player_id = self.player_id
        colony.game_id = self.game_id
        self.colonies.append(colony)
        self.update_modified_time()
    
    def remove_colony(self, colony_id: str) -> Optional[Colony]:
        """Remove and return colony by ID."""
        for i, colony in enumerate(self.colonies):
            if colony.id == colony_id:
                removed_colony = self.colonies.pop(i)
                self.update_modified_time()
                return removed_colony
        return None
    
    def add_ships_at_location(self, location: str, ship_type: ShipType, count: int) -> None:
        """Add ships at a specific location."""
        # Get or create ship group at location
        group = self.get_ship_group_at_location(location)
        if not group:
            group = ShipGroup(location, self.player_id)
            self.ship_groups.append(group)
        
        # Create ships and add to group
        ship = Ship(
            ship_type=ship_type,
            count=count,
            location=location,
            player_id=self.player_id,
            game_id=self.game_id
        )
        group.add_ships(ship)
        self.update_modified_time()
    
    def remove_ships_from_location(self, location: str, ship_type: ShipType, count: int) -> int:
        """Remove ships from location, returning actual count removed."""
        group = self.get_ship_group_at_location(location)
        if not group:
            return 0
        
        removed = group.remove_ships(ship_type, count)
        
        # Clean up empty group
        if group.is_empty():
            self.ship_groups.remove(group)
        
        if removed > 0:
            self.update_modified_time()
        
        return removed
    
    def move_ships(self, from_location: str, to_location: str, 
                   ship_type: ShipType, count: int) -> int:
        """Move ships between locations. Returns actual count moved."""
        removed = self.remove_ships_from_location(from_location, ship_type, count)
        if removed > 0:
            self.add_ships_at_location(to_location, ship_type, removed)
        return removed
    
    def place_command_post(self, location: str) -> bool:
        """Place a command post at location. Returns True if successful."""
        # Must have a colony at location
        colonies = self.get_colonies_at_location(location)
        if not colonies:
            return False
        
        self.command_posts.add(location)
        self.update_modified_time()
        return True
    
    def remove_command_post(self, location: str) -> bool:
        """Remove command post at location."""
        if location in self.command_posts:
            self.command_posts.remove(location)
            self.update_modified_time()
            return True
        return False
    
    def is_location_in_command_range(self, location: str) -> bool:
        """Check if location is within command post range."""
        if self.has_unlimited_range:
            return True
        
        from ..utils.hex_utils import calculate_hex_distance
        
        # Check distance to command posts
        for cp_location in self.command_posts:
            if calculate_hex_distance(location, cp_location) <= COMMAND_POST_RANGE:
                return True
        
        # Check distance to entry hex (acts as command post)
        if calculate_hex_distance(location, self.entry_hex) <= COMMAND_POST_RANGE:
            return True
        
        return False
    
    def add_research_investment(self, technology: Technology, ip_amount: int) -> bool:
        """Invest industrial points in research. Returns True if completed."""
        if ip_amount <= 0:
            return False
        
        if technology not in self.research_progress:
            self.research_progress[technology] = ResearchProgress(technology)
        
        progress = self.research_progress[technology]
        progress.invested_ip += ip_amount
        
        # Use the player's actual technology cost (which includes discounts)
        required_ip = self.get_technology_cost(technology)
        completed = progress.invested_ip >= required_ip
        
        if completed:
            progress.completed = True
            self.completed_technologies.add(technology)
        
        self.update_modified_time()
        return completed
    
    def get_technology_cost(self, technology: Technology) -> int:
        """Get the IP cost for a technology, including prerequisites."""
        base_cost = TECHNOLOGY_COSTS.get(technology, 50)
        
        # Check for prerequisite discount
        if technology in TECHNOLOGY_PREREQUISITES:
            prereq_tech, reduced_cost = TECHNOLOGY_PREREQUISITES[technology]
            if prereq_tech in self.completed_technologies:
                return reduced_cost
        
        return base_cost
    
    def can_research_technology(self, technology: Technology) -> bool:
        """Check if player can research a technology."""
        if technology in self.completed_technologies:
            return False  # Already have it
        
        # Check prerequisites for level-based technologies
        tech_data = get_technology_data(technology)
        if tech_data.level > 1:
            # Need at least one level 1 tech in same category
            same_category_techs = self._get_same_category_technologies(technology)
            level_1_techs = [t for t in same_category_techs if get_technology_data(t).level == 1]
            
            if not any(t in self.completed_technologies for t in level_1_techs):
                return False
        
        return True
    
    def _get_same_category_technologies(self, technology: Technology) -> List[Technology]:
        """Get technologies in the same category."""
        from ..core.enums import get_speed_technologies, get_weapon_technologies, get_industrial_technologies
        
        if technology in get_speed_technologies():
            return get_speed_technologies()
        elif technology in get_weapon_technologies():
            return get_weapon_technologies()
        elif technology in get_industrial_technologies():
            return get_industrial_technologies()
        else:
            return [technology]
    
    def build_ships(self, ship_type: ShipType, count: int, location: str, 
                   available_ip: int) -> Dict[str, Any]:
        """Build ships at a location. Returns build results."""
        if not self.can_build_ship_type(ship_type):
            raise TechnologyNotAvailableError(f"Cannot build {ship_type.value}")
        
        # Check if location has a colony that can build ships
        colonies = self.get_colonies_at_location(location)
        if not colonies or not any(c.can_build_ships for c in colonies):
            raise ValidationError(f"No shipbuilding capability at {location}")
        
        # Calculate cost
        unit_cost = SHIP_COSTS[ship_type]
        total_cost = unit_cost * count
        
        if total_cost > available_ip:
            # Build as many as possible
            count = available_ip // unit_cost
            total_cost = unit_cost * count
        
        if count > 0:
            self.add_ships_at_location(location, ship_type, count)
        
        return {
            "ship_type": ship_type.value,
            "count_built": count,
            "total_cost": total_cost,
            "location": location
        }
    
    def calculate_victory_points(self, game_state=None) -> int:
        """Calculate victory points from controlled planets."""
        points = 0
        for colony in self.colonies:
            if colony.is_active or colony.is_conquered:
                points += colony.planet.victory_points
        
        # If game_state is provided, calculate additional victory points from planet control rules
        if game_state is not None:
            points += self.calculate_planet_control_victory_points(game_state)
        
        return points
    
    def calculate_planet_control_victory_points(self, game_state) -> int:
        """Calculate victory points from planet control rules (a-d) at end of game."""
        additional_points = 0
        processed_planets = set()
        
        # Track planets already counted from colonies to avoid double counting
        colonized_planets = set()
        for colony in self.colonies:
            if colony.is_active or colony.is_conquered:
                planet_id = id(colony.planet)
                colonized_planets.add((colony.location, planet_id))
        
        # Check all star systems where we have ships or potential control
        locations_to_check = set()
        
        # Add all locations where player has ships
        for ship_group in self.ship_groups:
            if ship_group.get_total_ships() > 0:
                locations_to_check.add(ship_group.location)
        
        # Add all locations where player has colonies (for rule d extension)
        for colony in self.colonies:
            if colony.is_active:
                locations_to_check.add(colony.location)
        
        # Check each location for victory point opportunities
        for location in locations_to_check:
            star_system = game_state.board.star_systems.get(location)
            if not star_system:
                continue
                
            for planet in star_system.planets:
                planet_id = id(planet)
                planet_key = (location, planet_id)
                
                # Skip planets already counted from colonies (rule a)
                if planet_key in colonized_planets:
                    continue
                
                # Skip if we've already processed this planet
                if planet_key in processed_planets:
                    continue
                
                # Only count planets that give victory points
                if planet.victory_points <= 0:
                    continue
                
                # Check rules b, c, d for this planet
                if self._check_planet_control_rules(location, planet, game_state):
                    additional_points += planet.victory_points
                    processed_planets.add(planet_key)
        
        return additional_points
    
    def get_detailed_victory_points_breakdown(self, game_state):
        """Get detailed breakdown of victory points by rule (A, B, C, D)."""
        breakdown = {
            'rule_a': {'points': 0, 'planets': []},  # Colonies
            'rule_b': {'points': 0, 'planets': []},  # Conquered colonies with warship protection
            'rule_c': {'points': 0, 'planets': []},  # Unoccupied planets with ships present
            'rule_d': {'points': 0, 'planets': []}   # Unoccupied planets in same system as colony
        }
        
        processed_planets = set()
        
        # Rule A: Colony Victory Points
        for colony in self.colonies:
            if colony.is_active or colony.is_conquered:
                planet_vp = colony.planet.victory_points
                if planet_vp > 0:
                    breakdown['rule_a']['points'] += planet_vp
                    breakdown['rule_a']['planets'].append({
                        'location': colony.location,
                        'planet_type': colony.planet.planet_type.value,
                        'victory_points': planet_vp,
                        'status': 'conquered' if colony.is_conquered else 'active'
                    })
                
                # Track to avoid double counting
                planet_id = id(colony.planet)
                processed_planets.add((colony.location, planet_id))
        
        # Rules B, C, D: Check all locations with ships or colonies
        locations_to_check = set()
        
        # Add all locations where player has ships
        for ship_group in self.ship_groups:
            if ship_group.get_total_ships() > 0:
                locations_to_check.add(ship_group.location)
        
        # Add all locations where player has colonies (for rule d extension)
        for colony in self.colonies:
            if colony.is_active:
                locations_to_check.add(colony.location)
        
        # Check each location for Rules B, C, D
        for location in locations_to_check:
            star_system = game_state.board.star_systems.get(location)
            if not star_system:
                continue
                
            for planet in star_system.planets:
                planet_id = id(planet)
                planet_key = (location, planet_id)
                
                # Skip planets already counted from Rule A
                if planet_key in processed_planets:
                    continue
                
                # Only count planets that give victory points
                if planet.victory_points <= 0:
                    continue
                
                # Determine which rule applies
                rule_applied = self._determine_planet_control_rule(location, planet, game_state)
                
                if rule_applied:
                    breakdown[rule_applied]['points'] += planet.victory_points
                    breakdown[rule_applied]['planets'].append({
                        'location': location,
                        'planet_type': planet.planet_type.value,
                        'victory_points': planet.victory_points,
                        'explanation': self._get_rule_explanation(rule_applied, location, planet, game_state)
                    })
                    processed_planets.add(planet_key)
        
        return breakdown
    
    def _determine_planet_control_rule(self, location: str, planet, game_state) -> str:
        """Determine which rule (b, c, d) applies to a planet, if any."""
        # Rule b: Conquered colony with warship protection
        if self._has_conquered_colony_at_planet(location, planet) and self._has_warship_at_location(location):
            return 'rule_b'
        
        # Rule c: Unoccupied planet with spaceship present
        elif self._is_planet_unoccupied(location, planet, game_state) and self._has_any_ship_at_location(location):
            return 'rule_c'
        
        # Rule d: Unoccupied planet in same system as player colony, no enemy ships
        elif (self._is_planet_unoccupied(location, planet, game_state) and 
              self._has_colony_in_same_system(location) and 
              not self._has_enemy_ships_at_location(location, game_state)):
            return 'rule_d'
        
        return None
    
    def _get_rule_explanation(self, rule: str, location: str, planet, game_state) -> str:
        """Get human-readable explanation for why a rule applied."""
        if rule == 'rule_b':
            return "Conquered colony protected by warship"
        elif rule == 'rule_c':
            ship_group = self.get_ship_group_at_location(location)
            ship_count = ship_group.get_total_ships() if ship_group else 0
            return f"Unoccupied planet controlled by {ship_count} ship{'s' if ship_count > 1 else ''}"
        elif rule == 'rule_d':
            return "Unoccupied planet in same system as player colony (no enemy ships)"
        else:
            return "Unknown rule"
    
    def _check_planet_control_rules(self, location: str, planet, game_state) -> bool:
        """Check if player controls planet according to rules b, c, d."""
        # Rule b: Conquered colony with warship protection
        conquered_colony = self._has_conquered_colony_at_planet(location, planet)
        if conquered_colony and self._has_warship_at_location(location):
            return True
        
        # Rule c: Unoccupied planet with spaceship present
        if self._is_planet_unoccupied(location, planet, game_state) and self._has_any_ship_at_location(location):
            return True
        
        # Rule d: Unoccupied planet in same system as player colony, no enemy ships
        if (self._is_planet_unoccupied(location, planet, game_state) and 
            self._has_colony_in_same_system(location) and 
            not self._has_enemy_ships_at_location(location, game_state)):
            return True
        
        return False
    
    def _has_conquered_colony_at_planet(self, location: str, planet) -> bool:
        """Check if player has a conquered colony on this planet."""
        for colony in self.colonies:
            if colony.location == location and colony.is_conquered:
                # In a full implementation, would check if colony is on the specific planet
                # For now, assume location matching is sufficient
                return True
        return False
    
    def _has_warship_at_location(self, location: str) -> bool:
        """Check if player has warships at location."""
        ship_group = self.get_ship_group_at_location(location)
        if ship_group:
            return any(ship.is_warship for ship in ship_group.ships if ship.count > 0)
        return False
    
    def _has_any_ship_at_location(self, location: str) -> bool:
        """Check if player has any ships at location."""
        ship_group = self.get_ship_group_at_location(location)
        if ship_group:
            return ship_group.get_total_ships() > 0
        return False
    
    def _is_planet_unoccupied(self, location: str, planet, game_state) -> bool:
        """Check if this specific planet has no colonies from any player."""
        for player in game_state.players:
            for colony in player.colonies:
                if colony.location == location and colony.is_active:
                    # Check if colony is on this specific planet
                    if colony.planet == planet or id(colony.planet) == id(planet):
                        return False
        return True
    
    def _has_colony_in_same_system(self, location: str) -> bool:
        """Check if player has any active colony in the same star system."""
        for colony in self.colonies:
            if colony.location == location and colony.is_active:
                return True
        return False
    
    def _has_enemy_ships_at_location(self, location: str, game_state) -> bool:
        """Check if there are enemy ships at this location."""
        for other_player in game_state.players:
            if other_player.player_id == self.player_id:
                continue
            
            enemy_ship_group = other_player.get_ship_group_at_location(location)
            if enemy_ship_group and enemy_ship_group.get_total_ships() > 0:
                return True
        
        return False
    
    def process_production_turn(self) -> Dict[str, Any]:
        """Process production for all colonies. Returns summary."""
        total_growth = 0
        total_ip = 0
        
        results = {
            "population_growth": 0,
            "total_ip_generated": 0,
            "colony_results": []
        }
        
        for colony in self.colonies:
            if colony.can_grow:
                growth = colony.grow_population()
                total_growth += growth
            
            if colony.can_produce:
                ip = colony.calculate_industrial_points()
                total_ip += ip
            
            colony.advance_turn()
            
            results["colony_results"].append({
                "colony_id": colony.id,
                "location": colony.location,
                "population": colony.population,
                "growth": growth if colony.can_grow else 0,
                "ip_generated": ip if colony.can_produce else 0
            })
        
        results["population_growth"] = total_growth
        results["total_ip_generated"] = total_ip
        
        return results
    
    def cleanup_destroyed_entities(self) -> Dict[str, int]:
        """Remove destroyed entities and return counts."""
        cleanup_results = {"ship_groups": 0, "ships": 0}
        
        # Clean up ship groups
        initial_groups = len(self.ship_groups)
        for group in self.ship_groups[:]:  # Copy list to avoid modification issues
            ships_removed = group.cleanup_destroyed_ships()
            cleanup_results["ships"] += ships_removed
            
            if group.is_empty():
                self.ship_groups.remove(group)
        
        cleanup_results["ship_groups"] = initial_groups - len(self.ship_groups)
        
        # Remove abandoned colonies
        self.colonies = [c for c in self.colonies if c.status != c.status.ABANDONED]
        
        return cleanup_results
    
    def get_strategic_summary(self) -> Dict[str, Any]:
        """Get strategic summary for AI decision making."""
        return {
            "total_population": self.total_population,
            "total_factories": self.total_factories,
            "total_ships": self.total_ships,
            "total_colonies": len([c for c in self.colonies if c.is_active]),
            "industrial_output": self.total_industrial_output,
            "victory_points": self.calculate_victory_points(),
            "technologies_count": len(self.completed_technologies),
            "ship_speed": self.current_ship_speed,
            "has_unlimited_range": self.has_unlimited_range,
            "command_posts": len(self.command_posts),
            "play_style": self.play_style.value
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert player to dictionary representation."""
        data = super().to_dict()
        data.update({
            "name": self.name,
            "play_style": self.play_style.value,
            "entry_hex": self.entry_hex,
            "colonies": [c.to_dict() for c in self.colonies],
            "ship_groups": [
                {
                    "location": g.location,
                    "ship_counts": {st.value: count for st, count in g.get_ship_counts().items()}
                }
                for g in self.ship_groups
            ],
            "command_posts": list(self.command_posts),
            "completed_technologies": [t.value for t in self.completed_technologies],
            "research_progress": {
                t.value: {"invested_ip": p.invested_ip, "completed": p.completed}
                for t, p in self.research_progress.items()
            },
            "turns_completed": self.turns_completed,
            "strategic_summary": self.get_strategic_summary()
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Player":
        """Create player from dictionary representation."""
        play_style = PlayStyle(data["play_style"])
        
        player = cls(
            id=data.get("id", ""),
            name=data["name"],
            play_style=play_style,
            entry_hex=data["entry_hex"],
            turns_completed=data["turns_completed"],
            game_id=data.get("game_id", "")
        )
        
        # Restore colonies
        for colony_data in data.get("colonies", []):
            colony = Colony.from_dict(colony_data)
            player.colonies.append(colony)
        
        # Restore command posts
        player.command_posts = set(data.get("command_posts", []))
        
        # Restore technologies
        for tech_str in data.get("completed_technologies", []):
            player.completed_technologies.add(Technology(tech_str))
        
        # Restore research progress
        for tech_str, progress_data in data.get("research_progress", {}).items():
            tech = Technology(tech_str)
            progress = ResearchProgress(tech, progress_data["invested_ip"], progress_data["completed"])
            player.research_progress[tech] = progress
        
        return player
    
    def __str__(self) -> str:
        """String representation of player."""
        return (f"Player {self.name} ({self.play_style.value}): "
                f"{len(self.colonies)} colonies, {self.total_ships} ships, "
                f"{self.calculate_victory_points()} victory points")


# Utility functions for player operations
def create_starting_player(player_id: int, name: str, play_style: PlayStyle, entry_hex: str) -> Player:
    """Create a new player with starting conditions."""
    player = Player(
        name=name,
        play_style=play_style,
        entry_hex=entry_hex
    )
    player.player_id = player_id
    
    # Add starting fleet at entry hex
    for ship_type, count in STARTING_FLEET.items():
        player.add_ships_at_location(entry_hex, ship_type, count)
    
    return player


def distribute_starting_bonus(player: Player, bonus_ip: int = STARTING_BONUS_IP) -> Dict[str, Any]:
    """Distribute starting bonus IP for a player."""
    # This would implement AI logic or player choice for spending bonus IP
    # For now, return summary of how it could be spent
    available_purchases = []
    
    if bonus_ip >= 3:
        available_purchases.append(f"Scouts: {bonus_ip // 3} for {(bonus_ip // 3) * 3} IP")
    
    if bonus_ip >= 8:
        available_purchases.append(f"Corvettes: {bonus_ip // 8} for {(bonus_ip // 8) * 8} IP")
    
    if bonus_ip >= 15:
        available_purchases.append("Speed 3 Hex technology for 15 IP")
    
    return {
        "available_ip": bonus_ip,
        "purchase_options": available_purchases
    }


def calculate_player_rankings(players: List[Player]) -> List[Dict[str, Any]]:
    """Calculate player rankings by victory points."""
    rankings = []
    
    for player in players:
        rankings.append({
            "player": player,
            "victory_points": player.calculate_victory_points(),
            "total_population": player.total_population,
            "total_factories": player.total_factories,
            "total_ships": player.total_ships
        })
    
    # Sort by victory points descending
    rankings.sort(key=lambda x: x["victory_points"], reverse=True)
    
    # Add rank numbers
    for i, ranking in enumerate(rankings):
        ranking["rank"] = i + 1
    
    return rankings


def find_technology_dependencies(target_tech: Technology) -> List[Technology]:
    """Find all technology dependencies for a target technology."""
    dependencies = []
    
    # Check direct prerequisite
    if target_tech in TECHNOLOGY_PREREQUISITES:
        prereq_tech, _ = TECHNOLOGY_PREREQUISITES[target_tech]
        dependencies.append(prereq_tech)
        
        # Recursively find dependencies of prerequisite
        dependencies.extend(find_technology_dependencies(prereq_tech))
    
    return dependencies


def optimize_research_path(player: Player, target_technologies: List[Technology]) -> List[Technology]:
    """Find optimal research order for target technologies."""
    # Simple implementation: sort by cost and dependencies
    research_order = []
    remaining_targets = target_technologies.copy()
    
    while remaining_targets:
        # Find technologies that can be researched now
        available = [tech for tech in remaining_targets if player.can_research_technology(tech)]
        
        if not available:
            break  # No more technologies can be researched
        
        # Choose cheapest available technology
        chosen = min(available, key=lambda t: player.get_technology_cost(t))
        research_order.append(chosen)
        remaining_targets.remove(chosen)
        
        # Simulate completing this technology
        player.completed_technologies.add(chosen)
    
    # Restore original state
    for tech in target_technologies:
        player.completed_technologies.discard(tech)
    
    return research_order