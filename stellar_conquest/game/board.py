"""Hex board management and star system tracking for Stellar Conquest."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
import random

from ..core.enums import StarColor, PlanetType
from ..core.exceptions import ValidationError, GameStateError
from ..core.constants import BOARD_SIZE, HEX_GRID_SIZE, FIXED_STAR_LOCATIONS, GAS_CLOUD_HEXES, RULES_COLOR_TO_STARCOLOR
from ..data import STAR_CARDS, get_star_card, StarCardData
from ..utils.validation import GameValidator
from ..utils.hex_utils import calculate_hex_distance, get_adjacent_hexes, is_valid_hex
from ..entities.planet import Planet, StarSystem


@dataclass
class ExplorationResult:
    """Result of exploring a star system."""
    
    star_card_number: int
    star_system: StarSystem
    planets_discovered: List[Planet]
    exploration_risk_result: Optional[str] = None
    ships_lost: int = 0


class GameBoard:
    """Manages the hex board and star system exploration."""
    
    def __init__(self, game_id: str):
        self.game_id = game_id
        
        # Board state
        self.star_systems: Dict[str, StarSystem] = {}  # hex -> StarSystem
        self.explored_systems: Dict[str, Set[int]] = {}  # hex -> set of player_ids who explored
        self.star_card_decks: Dict[StarColor, List[int]] = {}  # Star cards by color
        self.used_star_cards: Set[int] = set()
        
        # Board configuration
        self.board_size = HEX_GRID_SIZE
        self.valid_hexes: Set[str] = set()
        self.entry_hexes: Set[str] = set()
        self.gas_cloud_hexes: Set[str] = set()
        
        # Initialize board
        self._initialize_board_layout()
        self._initialize_star_card_deck()
    
    def _initialize_board_layout(self) -> None:
        """Initialize the hex board layout."""
        # Generate valid hex coordinates for full Stellar Conquest board
        from ..utils.hex_utils import hex_grid
        
        # Generate all valid columns (A-Z, then AA-FF)
        for col_num in range(1, hex_grid.total_columns + 1):
            try:
                column = hex_grid.number_to_column(col_num)
                max_row = hex_grid.get_max_row(column)
                
                # Generate all valid rows for this column
                for row in range(1, max_row + 1):
                    hex_coord = f"{column}{row}"
                    if self._is_hex_on_board(hex_coord):
                        self.valid_hexes.add(hex_coord)
            except Exception:
                continue  # Skip invalid columns
        
        # Define entry hexes (corners of the board)
        self.entry_hexes = {"A1", "A21", "FF1", "FF20"}
        
        # Define gas cloud hexes (obstacles to movement) - from rules
        self.gas_cloud_hexes = GAS_CLOUD_HEXES
    
    def _is_hex_on_board(self, hex_coord: str) -> bool:
        """Check if hex coordinate is on the game board."""
        return is_valid_hex(hex_coord)
    
    def _initialize_star_card_deck(self) -> None:
        """Initialize star card decks by color."""
        from ..core.constants import STAR_CARD_RANGES
        
        # Initialize separate decks for each star color
        self.star_card_decks: Dict[StarColor, List[int]] = {}
        
        for star_color, (start_card, end_card) in STAR_CARD_RANGES.items():
            # Create deck for this color and shuffle
            color_deck = list(range(start_card, end_card + 1))
            random.shuffle(color_deck)
            self.star_card_decks[star_color] = color_deck
    
    def initialize_game(self) -> None:
        """Initialize board for game start."""
        # Clear any existing state
        self.star_systems.clear()
        self.explored_systems.clear()
        self.used_star_cards.clear()
        
        # Reinitialize deck
        self._initialize_star_card_deck()
        
        # Initialize fixed star locations
        self._initialize_fixed_stars()
    
    def validate(self) -> None:
        """Validate board state."""
        # Validate all star systems
        for hex_coord, system in self.star_systems.items():
            if hex_coord not in self.valid_hexes:
                raise ValidationError(f"Star system at invalid hex: {hex_coord}")
            system.validate()
        
        # Validate exploration tracking
        for hex_coord, explorers in self.explored_systems.items():
            if hex_coord not in self.valid_hexes:
                raise ValidationError(f"Exploration record at invalid hex: {hex_coord}")
    
    def is_valid_location(self, hex_coord: str) -> bool:
        """Check if hex coordinate is valid on this board."""
        return hex_coord in self.valid_hexes
    
    def is_entry_hex(self, hex_coord: str) -> bool:
        """Check if hex is a player entry point."""
        return hex_coord in self.entry_hexes
    
    def is_gas_cloud(self, hex_coord: str) -> bool:
        """Check if hex contains a gas cloud."""
        return hex_coord in self.gas_cloud_hexes
    
    def is_system_explored(self, hex_coord: str, player_id: int) -> bool:
        """Check if a system has been explored by a player."""
        explorers = self.explored_systems.get(hex_coord, set())
        return player_id in explorers
    
    def get_star_system(self, hex_coord: str) -> Optional[StarSystem]:
        """Get star system at hex coordinate."""
        return self.star_systems.get(hex_coord)
    
    def explore_system(self, hex_coord: str, player_id: int, has_warship_escort: bool = False) -> ExplorationResult:
        """Explore a star system and return results."""
        if not self.is_valid_location(hex_coord):
            raise ValidationError(f"Invalid hex coordinate: {hex_coord}")
        
        # Check if this location has a star
        if not self.is_star_location(hex_coord):
            raise ValidationError(f"No star system at location: {hex_coord}")
        
        if self.is_system_explored(hex_coord, player_id):
            raise GameStateError(f"System {hex_coord} already explored by player {player_id}")
        
        # Get star color for this location
        star_data = FIXED_STAR_LOCATIONS[hex_coord]
        star_color = RULES_COLOR_TO_STARCOLOR[star_data["color"]]
        
        # Draw star card from appropriate color deck
        if star_color not in self.star_card_decks or not self.star_card_decks[star_color]:
            raise GameStateError(f"No more star cards available for {star_color.value} stars")
        
        star_card_number = self.star_card_decks[star_color].pop(0)
        self.used_star_cards.add(star_card_number)
        
        # Get star card data using the constants structure
        from ..core.constants import STAR_CARDS
        if star_card_number not in STAR_CARDS:
            raise GameStateError(f"Invalid star card number: {star_card_number}")
        
        star_card_data = STAR_CARDS[star_card_number]
        
        # Create star system if this is first exploration
        if hex_coord not in self.star_systems:
            star_system = StarSystem(
                location=hex_coord,
                star_color=star_color,
                name=star_data["starname"]
            )
            star_system.game_id = self.game_id
            self.star_systems[hex_coord] = star_system
        else:
            star_system = self.star_systems[hex_coord]
        
        # Add planets from star card
        self._add_planets_from_card_dict(star_system, star_card_data)
        
        # Mark as explored
        if hex_coord not in self.explored_systems:
            self.explored_systems[hex_coord] = set()
        self.explored_systems[hex_coord].add(player_id)
        star_system.explore(player_id, star_card_number)
        
        # Handle exploration risks
        exploration_result = ExplorationResult(
            star_card_number=star_card_number,
            star_system=star_system,
            planets_discovered=star_system.planets.copy()
        )
        
        # Check for exploration risks (unarmed ships)
        if not has_warship_escort:
            risk_result = self._handle_exploration_risk()
            exploration_result.exploration_risk_result = risk_result
            if "lost" in risk_result.lower():
                exploration_result.ships_lost = 1  # Simplified - would be more complex
        
        return exploration_result
    
    def _create_star_system_from_card(self, hex_coord: str, star_card_data: StarCardData) -> StarSystem:
        """Create a star system from star card data."""
        star_system = StarSystem(
            location=hex_coord,
            star_color=star_card_data.star_color,
            name=f"System-{star_card_data.card_number}"
        )
        star_system.star_card_number = star_card_data.card_number
        star_system.game_id = self.game_id
        
        # Add planets from card data
        for planet_data in star_card_data.planets:
            planet = Planet(
                location=hex_coord,
                planet_type=planet_data.planet_type,
                max_population=planet_data.max_population,
                is_mineral_rich=planet_data.is_mineral_rich,
                orbit=planet_data.orbit,
                star_color=star_card_data.star_color,
                game_id=self.game_id
            )
            star_system.add_planet(planet)
        
        return star_system
    
    def _add_planets_from_card(self, star_system: StarSystem, star_card_data: StarCardData) -> None:
        """Add planets from star card data to existing star system."""
        # Clear any existing planets (shouldn't be any, but just in case)
        star_system.planets.clear()
        
        # Add planets from card data
        for planet_data in star_card_data.planets:
            planet = Planet(
                location=star_system.location,
                planet_type=planet_data.planet_type,
                max_population=planet_data.max_population,
                is_mineral_rich=planet_data.is_mineral_rich,
                orbit=planet_data.orbit,
                star_color=star_system.star_color,
                game_id=self.game_id
            )
            star_system.add_planet(planet)
    
    def _add_planets_from_card_dict(self, star_system: StarSystem, star_card_data: Dict[str, Any]) -> None:
        """Add planets from star card dictionary data to existing star system."""
        # Clear any existing planets (shouldn't be any, but just in case)
        star_system.planets.clear()
        
        # Add planets from card data dictionary
        for planet_data in star_card_data.get("planets", []):
            # Convert string planet type to PlanetType enum
            planet_type_str = planet_data["type"]
            planet_type = PlanetType(planet_type_str)
            
            planet = Planet(
                location=star_system.location,
                planet_type=planet_type,
                max_population=planet_data["max_pop"],
                is_mineral_rich=planet_data["mineral_rich"],
                orbit=planet_data["orbit"],
                star_color=star_system.star_color,
                game_id=self.game_id
            )
            star_system.add_planet(planet)
    
    def _handle_exploration_risk(self) -> str:
        """Handle exploration risk for unarmed ships."""
        # Simplified risk calculation
        risk_roll = random.randint(1, 6)
        
        if risk_roll <= 1:
            return "Ship lost to exploration hazard"
        elif risk_roll <= 2:
            return "Ship damaged but survives"
        else:
            return "Exploration successful"
    
    def get_adjacent_systems(self, hex_coord: str, include_gas_clouds: bool = False) -> List[str]:
        """Get adjacent hex coordinates that are valid for movement."""
        adjacent = get_adjacent_hexes(hex_coord)
        valid_adjacent = []
        
        for adj_hex in adjacent:
            if self.is_valid_location(adj_hex):
                if include_gas_clouds or not self.is_gas_cloud(adj_hex):
                    valid_adjacent.append(adj_hex)
        
        return valid_adjacent
    
    def get_systems_within_range(self, center_hex: str, max_range: int) -> List[str]:
        """Get all systems within movement range."""
        systems_in_range = []
        
        for hex_coord in self.valid_hexes:
            distance = calculate_hex_distance(center_hex, hex_coord)
            if distance <= max_range:
                systems_in_range.append(hex_coord)
        
        return systems_in_range
    
    def calculate_hex_distance(self, hex1: str, hex2: str) -> int:
        """Calculate distance between two hex coordinates."""
        return calculate_hex_distance(hex1, hex2)
    
    def find_path(self, start_hex: str, end_hex: str, max_range: int) -> Optional[List[str]]:
        """Find shortest path between two hexes within range."""
        from ..utils.hex_utils import find_path
        
        path = find_path(start_hex, end_hex, self.gas_cloud_hexes)
        
        # Validate path hexes are on board
        if path:
            for hex_coord in path:
                if not self.is_valid_location(hex_coord):
                    return None
        
        return path
    
    def _initialize_fixed_stars(self) -> None:
        """Initialize fixed star locations from rules."""
        # Stars exist at fixed locations but are not "discovered" until explored
        # We don't add them to star_systems until they're actually explored
        # This method just sets up the knowledge of where stars are
        pass
    
    def is_star_location(self, hex_coord: str) -> bool:
        """Check if hex coordinate contains a fixed star location."""
        return hex_coord in FIXED_STAR_LOCATIONS
    
    def get_star_at_location(self, hex_coord: str) -> Optional[StarSystem]:
        """Get the star system at a location (if it exists)."""
        return self.star_systems.get(hex_coord)
    
    def get_all_explored_systems(self, player_id: int) -> List[StarSystem]:
        """Get all systems explored by a player."""
        explored_systems = []
        
        for hex_coord, explorers in self.explored_systems.items():
            if player_id in explorers:
                system = self.star_systems.get(hex_coord)
                if system:
                    explored_systems.append(system)
        
        return explored_systems
    
    def get_colonizable_planets(self, player_id: int, has_cet: bool = False) -> List[Planet]:
        """Get all planets that can be colonized by a player."""
        colonizable = []
        
        explored_systems = self.get_all_explored_systems(player_id)
        for system in explored_systems:
            for planet in system.get_colonizable_planets(has_cet):
                # Check if planet is already colonized
                # In full implementation, would check colony ownership
                colonizable.append(planet)
        
        return colonizable
    
    def get_board_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current board state."""
        total_systems = len(self.star_systems)
        total_planets = sum(len(system.planets) for system in self.star_systems.values())
        
        # Count planets by type
        planet_type_counts = {}
        for system in self.star_systems.values():
            for planet in system.planets:
                planet_type = planet.planet_type.value
                planet_type_counts[planet_type] = planet_type_counts.get(planet_type, 0) + 1
        
        # Count systems by star color
        star_color_counts = {}
        for system in self.star_systems.values():
            color = system.star_color.value
            star_color_counts[color] = star_color_counts.get(color, 0) + 1
        
        return {
            "total_valid_hexes": len(self.valid_hexes),
            "total_systems_discovered": total_systems,
            "total_planets_discovered": total_planets,
            "star_cards_remaining": len(self.star_card_deck),
            "star_cards_used": len(self.used_star_cards),
            "entry_hexes": list(self.entry_hexes),
            "gas_cloud_hexes": list(self.gas_cloud_hexes),
            "planet_type_distribution": planet_type_counts,
            "star_color_distribution": star_color_counts,
            "exploration_coverage": len(self.explored_systems)
        }
    
    def get_strategic_locations(self) -> Dict[str, List[str]]:
        """Get strategically important locations on the board."""
        strategic = {
            "entry_points": list(self.entry_hexes),
            "gas_clouds": list(self.gas_cloud_hexes),
            "high_value_systems": [],
            "chokepoints": []
        }
        
        # Find high-value systems (multiple planets, mineral-rich, etc.)
        for hex_coord, system in self.star_systems.items():
            strategic_value = system.get_strategic_value()
            if strategic_value >= 20.0:  # Threshold for "high value"
                strategic["high_value_systems"].append(hex_coord)
        
        # Find chokepoints (hexes that control access to regions)
        # Simplified implementation
        for hex_coord in self.valid_hexes:
            adjacent = self.get_adjacent_systems(hex_coord, include_gas_clouds=False)
            if len(adjacent) <= 2:  # Potential chokepoint
                strategic["chokepoints"].append(hex_coord)
        
        return strategic
    
    def to_dict(self) -> Dict[str, Any]:
        """Export board state to dictionary."""
        return {
            "game_id": self.game_id,
            "board_size": self.board_size,
            "valid_hexes": list(self.valid_hexes),
            "entry_hexes": list(self.entry_hexes),
            "gas_cloud_hexes": list(self.gas_cloud_hexes),
            "star_systems": {
                hex_coord: system.to_dict() 
                for hex_coord, system in self.star_systems.items()
            },
            "explored_systems": {
                hex_coord: list(explorers)
                for hex_coord, explorers in self.explored_systems.items()
            },
            "star_card_deck": self.star_card_deck.copy(),
            "used_star_cards": list(self.used_star_cards),
            "statistics": self.get_board_statistics(),
            "strategic_locations": self.get_strategic_locations()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameBoard":
        """Create board from exported data."""
        board = cls(data["game_id"])
        
        # Restore basic state
        board.board_size = data["board_size"]
        board.valid_hexes = set(data["valid_hexes"])
        board.entry_hexes = set(data["entry_hexes"])
        board.gas_cloud_hexes = set(data["gas_cloud_hexes"])
        board.star_card_deck = data["star_card_deck"]
        board.used_star_cards = set(data["used_star_cards"])
        
        # Restore star systems
        for hex_coord, system_data in data["star_systems"].items():
            system = StarSystem.from_dict(system_data)
            board.star_systems[hex_coord] = system
        
        # Restore exploration tracking
        for hex_coord, explorers in data["explored_systems"].items():
            board.explored_systems[hex_coord] = set(explorers)
        
        return board
    
    def __str__(self) -> str:
        """String representation of board."""
        stats = self.get_board_statistics()
        return (f"GameBoard {self.game_id[:8]} - "
                f"{stats['total_systems_discovered']} systems discovered, "
                f"{stats['star_cards_remaining']} cards remaining")


# Utility functions for board operations
def create_game_board(game_id: str) -> GameBoard:
    """Create a new game board."""
    return GameBoard(game_id)


def generate_random_star_system(hex_coord: str, game_id: str) -> StarSystem:
    """Generate a random star system for testing."""
    star_colors = list(StarColor)
    star_color = random.choice(star_colors)
    
    system = StarSystem(
        location=hex_coord,
        star_color=star_color,
        name=f"Random-{hex_coord}"
    )
    system.game_id = game_id
    
    # Add 1-3 random planets
    num_planets = random.randint(1, 3)
    for orbit in range(1, num_planets + 1):
        planet_types = list(PlanetType)
        planet_type = random.choice(planet_types)
        
        # Random population based on type
        max_pop_ranges = {
            PlanetType.TERRAN: (40, 80),
            PlanetType.SUB_TERRAN: (20, 60),
            PlanetType.MINIMAL_TERRAN: (10, 30),
            PlanetType.BARREN: (5, 20)
        }
        
        pop_range = max_pop_ranges.get(planet_type, (10, 40))
        max_population = random.randint(*pop_range)
        
        planet = Planet(
            location=hex_coord,
            planet_type=planet_type,
            max_population=max_population,
            is_mineral_rich=random.random() < 0.2,  # 20% chance
            orbit=orbit,
            star_color=star_color,
            game_id=game_id
        )
        
        system.add_planet(planet)
    
    return system


def calculate_board_connectivity(board: GameBoard) -> Dict[str, float]:
    """Calculate connectivity metrics for the board."""
    connectivity = {}
    
    for hex_coord in board.valid_hexes:
        adjacent_count = len(board.get_adjacent_systems(hex_coord))
        # Normalize by maximum possible adjacent hexes (6)
        connectivity[hex_coord] = adjacent_count / 6.0
    
    return connectivity


def find_optimal_expansion_targets(board: GameBoard, player_id: int, 
                                 current_location: str, max_range: int) -> List[str]:
    """Find optimal systems for expansion within range."""
    targets = []
    systems_in_range = board.get_systems_within_range(current_location, max_range)
    
    for hex_coord in systems_in_range:
        # Skip already explored systems
        if board.is_system_explored(hex_coord, player_id):
            continue
        
        # Skip gas clouds
        if board.is_gas_cloud(hex_coord):
            continue
        
        # Calculate strategic value based on position
        distance = calculate_hex_distance(current_location, hex_coord)
        adjacency_bonus = len(board.get_adjacent_systems(hex_coord))
        
        # Simple scoring: closer is better, more connections is better
        score = (max_range - distance) + (adjacency_bonus * 0.5)
        
        targets.append({
            "hex": hex_coord,
            "distance": distance,
            "score": score
        })
    
    # Sort by score descending
    targets.sort(key=lambda t: t["score"], reverse=True)
    return [t["hex"] for t in targets[:5]]  # Top 5 targets