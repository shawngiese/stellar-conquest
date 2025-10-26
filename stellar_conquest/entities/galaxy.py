"""Galaxy map and spatial logic."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import re
from .colony import Planet, PlanetType


class StarColor(Enum):
    """Star colors corresponding to spectral classes."""
    BLUE = "blue"
    GREEN = "green" 
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


@dataclass
class StarSystem:
    """Represents a star system with potential planets."""
    
    location: str  # Hex coordinate like "A1"
    color: StarColor
    name: Optional[str] = None
    planets: List[Planet] = field(default_factory=list)
    explored_by: Set[int] = field(default_factory=set)  # Player IDs who have explored
    star_card_number: Optional[int] = None
    
    @property
    def is_explored(self) -> bool:
        """Check if any player has explored this system."""
        return len(self.explored_by) > 0
    
    @property
    def has_habitable_planets(self) -> bool:
        """Check if system has terran or sub-terran planets."""
        return any(p.planet_type in [PlanetType.TERRAN, PlanetType.SUB_TERRAN] 
                  for p in self.planets)


@dataclass 
class Galaxy:
    """Represents the game map and spatial relationships."""
    
    star_systems: Dict[str, StarSystem] = field(default_factory=dict)
    gas_cloud_hexes: Set[str] = field(default_factory=set)
    entry_hexes: Dict[int, str] = field(default_factory=dict)  # Player ID -> hex
    
    def __post_init__(self):
        """Initialize the galaxy with standard Stellar Conquest setup."""
        self._initialize_entry_hexes()
        self._initialize_gas_clouds()
        self._initialize_star_systems()
    
    def _initialize_entry_hexes(self):
        """Set up the four corner entry hexes."""
        # Based on rules - corners of the map
        self.entry_hexes = {
            1: "A1",    # Top-left corner (approximate)
            2: "FF1",   # Top-right corner  
            3: "A21",   # Bottom-left corner
            4: "FF20"   # Bottom-right corner
        }
    
    def _initialize_gas_clouds(self):
        """Initialize gas/dust cloud locations."""
        # From rules - 7 distinct gas/dust clouds that slow movement
        cloud_hexes = [
            # Cloud 1
            ["A10", "A11", "A12", "A13", "B10", "B11", "B12", "C11"],
            # Cloud 2  
            ["I7", "I8", "I13", "I14", "J6", "J7", "J8", "J12", "J13", "J14", "K6", "K7", "K14", "K15", "K16", "L5", "L15"],
            # Cloud 3
            ["O1", "O20", "P1", "P19", "P20", "Q1", "Q2", "Q20", "R1", "R2", "R19"],
            # Cloud 4
            ["U6", "V5", "V6", "V14", "V15", "W6", "W7", "W15", "X6", "X7", "X8", "X13", "X14", "Y12", "Y13", "Y14"],
            # Additional clouds would be added based on full map data
        ]
        
        for cloud in cloud_hexes:
            self.gas_cloud_hexes.update(cloud)
    
    def _initialize_star_systems(self):
        """Initialize star systems from the rules data."""
        # Sample star systems from the rules
        star_data = [
            ("AA15", StarColor.ORANGE, "Hamal"),
            ("AA19", StarColor.YELLOW, "Scorpii"),
            ("AA9", StarColor.GREEN, "Wezen"),
            ("B11", StarColor.BLUE, "Sirius"),
            ("B18", StarColor.RED, "Lalande"),
            # ... would include all 54 star systems from rules
        ]
        
        for location, color, name in star_data:
            self.star_systems[location] = StarSystem(location, color, name)
    
    def get_adjacent_hexes(self, hex_coord: str) -> List[str]:
        """Get adjacent hex coordinates."""
        # Parse hex coordinate (e.g., "A1", "BB15")
        match = re.match(r'^([A-Z]+)(\d+)$', hex_coord)
        if not match:
            return []
        
        col_str, row_str = match.groups()
        row = int(row_str)
        
        # Convert column string to number
        col_num = self._column_to_number(col_str)
        if col_num is None:
            return []
        
        # Get adjacent coordinates based on hex grid
        adjacent = []
        is_odd_col = col_num % 2 == 1
        
        # Standard hex adjacency (6 directions)
        if is_odd_col:
            # Odd columns
            deltas = [(-1, -1), (-1, 0), (0, -1), (0, 1), (1, -1), (1, 0)]
        else:
            # Even columns  
            deltas = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1)]
        
        for dc, dr in deltas:
            new_col = col_num + dc
            new_row = row + dr
            
            if new_col >= 1 and new_row >= 1:
                new_col_str = self._number_to_column(new_col)
                if new_col_str and self._is_valid_hex(new_col_str, new_row):
                    adjacent.append(f"{new_col_str}{new_row}")
        
        return adjacent
    
    def _column_to_number(self, col_str: str) -> Optional[int]:
        """Convert column string like 'A' or 'BB' to number."""
        if len(col_str) == 1:
            return ord(col_str) - ord('A') + 1
        elif len(col_str) == 2 and col_str[0] == col_str[1]:
            return ord(col_str[0]) - ord('A') + 27  # AA=27, BB=28, etc.
        return None
    
    def _number_to_column(self, col_num: int) -> Optional[str]:
        """Convert column number to string."""
        if 1 <= col_num <= 26:
            return chr(ord('A') + col_num - 1)
        elif 27 <= col_num <= 32:  # AA through FF
            char = chr(ord('A') + col_num - 27)
            return char + char
        return None
    
    def _is_valid_hex(self, col_str: str, row: int) -> bool:
        """Check if hex coordinate is valid on the board."""
        col_num = self._column_to_number(col_str)
        if not col_num:
            return False
        
        # Odd columns have 21 hexes, even have 20
        max_row = 21 if col_num % 2 == 1 else 20
        return 1 <= row <= max_row
    
    def calculate_distance(self, hex1: str, hex2: str) -> int:
        """Calculate hex distance between two coordinates."""
        # Simplified Manhattan distance approximation
        # Real hex distance calculation would be more complex
        return abs(hash(hex1) % 20 - hash(hex2) % 20)  # Placeholder
    
    def is_gas_cloud_hex(self, hex_coord: str) -> bool:
        """Check if hex contains gas/dust cloud."""
        return hex_coord in self.gas_cloud_hexes
    
    def get_star_system(self, hex_coord: str) -> Optional[StarSystem]:
        """Get star system at hex coordinate."""
        return self.star_systems.get(hex_coord)
    
    def find_path(self, start: str, end: str, max_distance: int) -> Optional[List[str]]:
        """Find shortest path between hexes within max distance."""
        # Simplified pathfinding - would implement proper A* algorithm
        if self.calculate_distance(start, end) <= max_distance:
            return [start, end]  # Direct path placeholder
        return None