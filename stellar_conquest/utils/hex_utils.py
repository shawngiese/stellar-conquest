"""Hex grid mathematics and utilities for Stellar Conquest."""

import math
import re
from typing import List, Tuple, Optional, Set, Dict
from dataclasses import dataclass
from ..core.exceptions import InvalidHexError, PathfindingError
from ..core.constants import BOARD_DIMENSIONS, GAS_CLOUD_HEXES


@dataclass(frozen=True)
class HexCoordinate:
    """Represents a hex coordinate with column and row."""
    column: str
    row: int
    
    def __post_init__(self):
        """Validate hex coordinate on creation."""
        if not self.is_valid():
            raise InvalidHexError(f"Invalid hex coordinate: {self.column}{self.row}")
    
    def __str__(self) -> str:
        """String representation of hex coordinate."""
        return f"{self.column}{self.row}"
    
    def is_valid(self) -> bool:
        """Check if this hex coordinate is valid on the game board."""
        # Direct validation without recursion
        try:
            max_row = hex_grid.get_max_row(self.column)
            return 1 <= self.row <= max_row
        except (InvalidHexError, ValueError):
            return False
    
    def to_string(self) -> str:
        """Convert to string format."""
        return f"{self.column}{self.row}"
    
    @classmethod
    def from_string(cls, hex_string: str) -> "HexCoordinate":
        """Create HexCoordinate from string."""
        match = re.match(r'^([A-Z]{1,2})(\d+)$', hex_string)
        if not match:
            raise InvalidHexError(f"Invalid hex format: {hex_string}")
        
        column, row_str = match.groups()
        return cls(column, int(row_str))


class HexGrid:
    """Hex grid utilities for Stellar Conquest board."""
    
    def __init__(self):
        """Initialize hex grid with board dimensions."""
        self.odd_column_rows = BOARD_DIMENSIONS["odd_column_rows"]
        self.even_column_rows = BOARD_DIMENSIONS["even_column_rows"]
        self.total_columns = BOARD_DIMENSIONS["columns"]
    
    def column_to_number(self, column: str) -> int:
        """Convert column string to number (A=1, B=2, ..., AA=27, BB=28, etc.)."""
        if len(column) == 1:
            return ord(column) - ord('A') + 1
        elif len(column) == 2 and column[0] == column[1]:
            if column in ['AA', 'BB', 'CC', 'DD', 'EE', 'FF']:
                return ord(column[0]) - ord('A') + 27
        raise InvalidHexError(f"Invalid column: {column}")
    
    def number_to_column(self, number: int) -> str:
        """Convert column number to string."""
        if 1 <= number <= 26:
            return chr(ord('A') + number - 1)
        elif 27 <= number <= 32:  # AA through FF
            char = chr(ord('A') + number - 27)
            return char + char
        raise InvalidHexError(f"Invalid column number: {number}")
    
    def is_odd_column(self, column: str) -> bool:
        """Check if column is odd-numbered (has 21 rows)."""
        col_num = self.column_to_number(column)
        return col_num % 2 == 1
    
    def get_max_row(self, column: str) -> int:
        """Get maximum row for a column."""
        return self.odd_column_rows if self.is_odd_column(column) else self.even_column_rows
    
    def get_adjacent_coordinates(self, hex_coord: str) -> List[str]:
        """Get all adjacent hex coordinates."""
        coord = HexCoordinate.from_string(hex_coord)
        col_num = self.column_to_number(coord.column)
        row = coord.row
        
        adjacent = []
        is_odd_col = self.is_odd_column(coord.column)
        
        # Six directions for hex adjacency
        if is_odd_col:
            # Odd columns: NW, NE, E, SE, SW, W
            deltas = [(-1, -1), (-1, 0), (0, 1), (1, 0), (1, -1), (0, -1)]
        else:
            # Even columns: NW, NE, E, SE, SW, W
            deltas = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (0, -1)]
        
        for dc, dr in deltas:
            new_col_num = col_num + dc
            new_row = row + dr
            
            if 1 <= new_col_num <= self.total_columns and new_row >= 1:
                try:
                    new_col = self.number_to_column(new_col_num)
                    max_row = self.get_max_row(new_col)
                    
                    if new_row <= max_row:
                        adjacent.append(f"{new_col}{new_row}")
                except InvalidHexError:
                    continue  # Skip invalid columns
        
        return adjacent
    
    def calculate_distance(self, hex1: str, hex2: str) -> int:
        """Calculate hex distance between two coordinates using cube coordinates."""
        cube1 = self.hex_to_cube(hex1)
        cube2 = self.hex_to_cube(hex2)
        
        return max(abs(cube1[0] - cube2[0]), abs(cube1[1] - cube2[1]), abs(cube1[2] - cube2[2]))
    
    def hex_to_cube(self, hex_coord: str) -> Tuple[int, int, int]:
        """Convert hex coordinate to cube coordinates for distance calculation."""
        coord = HexCoordinate.from_string(hex_coord)
        col_num = self.column_to_number(coord.column)
        row = coord.row
        
        # Convert offset coordinates to cube coordinates
        # This is an approximation for the Stellar Conquest board layout
        q = col_num - 1
        r = row - 1 - (col_num - 1) // 2
        s = -q - r
        
        return (q, r, s)
    
    def find_shortest_path(self, start: str, end: str, blocked_hexes: Set[str] = None) -> Optional[List[str]]:
        """Find shortest path between two hexes using A* algorithm with gas cloud movement rules."""
        if blocked_hexes is None:
            blocked_hexes = set()
        
        if start == end:
            return [start]
        
        if not is_valid_hex(start) or not is_valid_hex(end):
            raise PathfindingError(f"Invalid hex coordinates: {start} or {end}")
        
        # A* pathfinding with gas cloud costs
        open_set = {start}
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self.calculate_distance(start, end)}
        
        max_iterations = 1000  # Prevent infinite loops
        iterations = 0
        
        while open_set and iterations < max_iterations:
            iterations += 1
            
            # Get node with lowest f_score
            current = min(open_set, key=lambda x: f_score.get(x, float('inf')))
            
            if current == end:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]
            
            open_set.remove(current)
            
            for neighbor in self.get_adjacent_coordinates(current):
                if neighbor in blocked_hexes:
                    continue
                
                # Calculate cost considering gas cloud movement rules
                move_cost = self._calculate_gas_cloud_move_cost(current, neighbor)
                tentative_g_score = g_score[current] + move_cost
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.calculate_distance(neighbor, end)
                    
                    if neighbor not in open_set:
                        open_set.add(neighbor)
        
        return None  # No path found
    
    def _calculate_gas_cloud_move_cost(self, current_hex: str, next_hex: str) -> int:
        """Calculate movement cost considering gas cloud rules."""
        gas_cloud_hexes = set(GAS_CLOUD_HEXES)
        
        # Standard movement cost is 1
        base_cost = 1
        
        # If moving into a gas cloud, apply heavy penalty to represent turn-ending restriction
        if next_hex in gas_cloud_hexes:
            # Gas clouds require a full turn to enter and limit movement to 1 hex
            # Use higher cost to discourage gas cloud paths unless necessary
            return base_cost + 2  # Extra cost reflects the movement limitation
        
        # If moving through or out of gas cloud, normal cost
        return base_cost
    
    def get_hexes_within_range(self, center: str, range_limit: int, 
                              blocked_hexes: Set[str] = None) -> List[str]:
        """Get all hexes within range of center hex."""
        if blocked_hexes is None:
            blocked_hexes = set()
        
        reachable = []
        visited = set()
        queue = [(center, 0)]  # (hex, distance)
        
        while queue:
            current_hex, distance = queue.pop(0)
            
            if current_hex in visited:
                continue
            
            visited.add(current_hex)
            
            if distance <= range_limit:
                reachable.append(current_hex)
                
                if distance < range_limit:  # Can still move further
                    for neighbor in self.get_adjacent_coordinates(current_hex):
                        if neighbor not in visited and neighbor not in blocked_hexes:
                            queue.append((neighbor, distance + 1))
        
        return reachable
    
    def calculate_movement_cost(self, path: List[str], gas_cloud_hexes: Set[str] = None) -> int:
        """
        Calculate movement cost for a path, considering gas cloud rules.
        This represents the actual number of movement points needed.
        """
        if gas_cloud_hexes is None:
            gas_cloud_hexes = set(GAS_CLOUD_HEXES)
        
        if len(path) <= 1:
            return 0
        
        # Use the turn-based calculation to get accurate movement cost
        # Each turn costs movement points equal to the ship's speed
        ship_speed = 2  # Standard ship speed
        turns_needed = calculate_movement_turns(path, ship_speed, gas_cloud_hexes)
        
        # Calculate actual movement points used
        total_cost = 0
        current_position = 0
        
        for turn in range(turns_needed):
            movement_this_turn = 0
            current_hex = path[current_position] if current_position < len(path) else path[-1]
            is_starting_in_gas_cloud = current_hex in gas_cloud_hexes
            
            # Simulate movement for this turn
            if is_starting_in_gas_cloud:
                # Leaving gas cloud - can move full speed
                while (movement_this_turn < ship_speed and 
                       current_position + 1 < len(path)):
                    
                    next_hex = path[current_position + 1]
                    current_position += 1
                    movement_this_turn += 1
                    
                    # If entering another gas cloud, movement ends
                    if next_hex in gas_cloud_hexes:
                        break
            else:
                # Starting in normal space
                while (movement_this_turn < ship_speed and 
                       current_position + 1 < len(path)):
                    
                    next_hex = path[current_position + 1]
                    
                    if next_hex in gas_cloud_hexes:
                        # Entering gas cloud ends turn
                        current_position += 1
                        movement_this_turn += 1
                        break
                    else:
                        # Normal movement
                        current_position += 1
                        movement_this_turn += 1
            
            total_cost += movement_this_turn
        
        return total_cost
    
    def get_line_of_sight(self, start: str, end: str) -> List[str]:
        """Get hexes in line of sight between two points."""
        # Simplified line of sight - returns direct path
        path = self.find_shortest_path(start, end)
        return path if path else []
    
    def get_ring_coordinates(self, center: str, radius: int) -> List[str]:
        """Get coordinates in a ring around center at specified radius."""
        if radius == 0:
            return [center]
        
        ring_hexes = []
        center_cube = self.hex_to_cube(center)
        
        # Generate ring using cube coordinate arithmetic
        for direction in range(6):  # 6 directions
            for step in range(radius):
                # This is a simplified ring generation
                # In a full implementation, would use proper cube coordinate ring algorithm
                pass
        
        # Simplified: get all hexes at exact distance
        all_reachable = self.get_hexes_within_range(center, radius)
        ring_hexes = [hex_coord for hex_coord in all_reachable 
                     if self.calculate_distance(center, hex_coord) == radius]
        
        return ring_hexes
    
    def get_sector_coordinates(self, center: str, direction: int, angle: int, radius: int) -> List[str]:
        """Get coordinates in a sector (cone) from center."""
        # Simplified sector calculation
        # Would implement proper angular calculations in full version
        reachable = self.get_hexes_within_range(center, radius)
        return reachable  # Placeholder


# Global hex grid instance
hex_grid = HexGrid()


# Utility functions
def is_valid_hex(hex_coord: str) -> bool:
    """Check if hex coordinate is valid on the game board."""
    try:
        coord = HexCoordinate.from_string(hex_coord)
        max_row = hex_grid.get_max_row(coord.column)
        return 1 <= coord.row <= max_row
    except (InvalidHexError, ValueError):
        return False


def parse_hex_coordinate(hex_string: str) -> Optional[HexCoordinate]:
    """Parse hex coordinate string, return None if invalid."""
    try:
        return HexCoordinate.from_string(hex_string)
    except InvalidHexError:
        return None


def get_adjacent_hexes(hex_coord: str) -> List[str]:
    """Get adjacent hex coordinates."""
    return hex_grid.get_adjacent_coordinates(hex_coord)


def calculate_hex_distance(hex1: str, hex2: str) -> int:
    """Calculate distance between two hex coordinates."""
    return hex_grid.calculate_distance(hex1, hex2)


def find_path(start: str, end: str, blocked_hexes: Set[str] = None) -> Optional[List[str]]:
    """Find shortest path between hexes."""
    return hex_grid.find_shortest_path(start, end, blocked_hexes)


def get_hexes_in_range(center: str, range_limit: int, blocked_hexes: Set[str] = None) -> List[str]:
    """Get all hexes within range."""
    return hex_grid.get_hexes_within_range(center, range_limit, blocked_hexes)


def is_adjacent(hex1: str, hex2: str) -> bool:
    """Check if two hexes are adjacent."""
    return hex2 in get_adjacent_hexes(hex1)


def get_direction_to(from_hex: str, to_hex: str) -> Optional[int]:
    """Get direction index (0-5) from one hex to adjacent hex."""
    adjacent = get_adjacent_hexes(from_hex)
    try:
        return adjacent.index(to_hex)
    except ValueError:
        return None  # Not adjacent


def calculate_movement_turns(path: List[str], ship_speed: int, gas_cloud_hexes: Set[str] = None) -> int:
    """
    Calculate how many turns it takes to move along a path considering gas cloud rules:
    1. Ships must start adjacent to gas cloud to enter it
    2. Entering a gas cloud ends the turn (no further movement)
    3. Moving through gas clouds: 1 hex per turn maximum
    4. Leaving gas cloud allows full speed movement
    """
    if gas_cloud_hexes is None:
        gas_cloud_hexes = set(GAS_CLOUD_HEXES)
    
    if len(path) <= 1:
        return 0
    
    turns = 0
    current_position = 0
    
    while current_position < len(path) - 1:
        turns += 1
        movement_this_turn = 0
        current_hex = path[current_position]
        is_starting_in_gas_cloud = current_hex in gas_cloud_hexes
        
        # If starting in a gas cloud, can move full speed when leaving
        if is_starting_in_gas_cloud:
            # Can move up to full speed when leaving gas cloud
            while (movement_this_turn < ship_speed and 
                   current_position + 1 < len(path)):
                
                next_hex = path[current_position + 1]
                current_position += 1
                movement_this_turn += 1
                
                # If entering another gas cloud, movement ends
                if next_hex in gas_cloud_hexes:
                    break
        else:
            # Starting in normal space
            while (movement_this_turn < ship_speed and 
                   current_position + 1 < len(path)):
                
                next_hex = path[current_position + 1]
                
                # Check if entering gas cloud
                if next_hex in gas_cloud_hexes:
                    # Can only enter gas cloud if starting adjacent (movement_this_turn == 0)
                    # or if already moved to adjacent hex this turn
                    current_position += 1
                    movement_this_turn = ship_speed  # Entering gas cloud ends turn
                    break
                else:
                    # Normal movement
                    current_position += 1
                    movement_this_turn += 1
    
    return turns


def get_command_post_coverage(command_post_locations: List[str], range_limit: int = 8) -> Set[str]:
    """Get all hexes covered by command posts."""
    covered = set()
    
    for cp_location in command_post_locations:
        reachable = get_hexes_in_range(cp_location, range_limit)
        covered.update(reachable)
    
    return covered


def validate_movement_path(path: List[str], ship_speed: int, 
                          gas_cloud_hexes: Set[str] = None) -> bool:
    """Validate that a movement path is legal for given ship speed."""
    if gas_cloud_hexes is None:
        gas_cloud_hexes = set(GAS_CLOUD_HEXES)
    
    if len(path) <= 1:
        return True
    
    # Check path connectivity
    for i in range(len(path) - 1):
        if not is_adjacent(path[i], path[i + 1]):
            return False
    
    # Check movement constraints
    movement_cost = hex_grid.calculate_movement_cost(path, gas_cloud_hexes)
    return movement_cost <= ship_speed


def get_exploration_candidates(explored_systems: Set[str], player_locations: List[str], 
                              max_range: int) -> List[str]:
    """Get unexplored star systems within range of player ships."""
    from ..data import STAR_SYSTEMS
    
    candidates = []
    
    for system_location in STAR_SYSTEMS.keys():
        if system_location not in explored_systems:
            # Check if any player ship can reach this system
            for ship_location in player_locations:
                distance = calculate_hex_distance(ship_location, system_location)
                if distance <= max_range:
                    candidates.append(system_location)
                    break
    
    return candidates


def get_optimal_expansion_positions(current_colonies: List[str], 
                                  candidate_systems: List[str]) -> List[str]:
    """Get optimal positions for expansion based on current colonies."""
    # Score systems based on distance from existing colonies
    scored_systems = []
    
    for candidate in candidate_systems:
        if not current_colonies:
            # First colony - all positions equally good
            scored_systems.append((candidate, 1.0))
        else:
            # Prefer systems that are not too close or too far from existing colonies
            min_distance = min(calculate_hex_distance(candidate, colony) 
                             for colony in current_colonies)
            
            # Optimal distance is 3-6 hexes (close enough for support, far enough for expansion)
            if 3 <= min_distance <= 6:
                score = 1.0
            elif min_distance < 3:
                score = 0.5  # Too close
            else:
                score = 0.8 - (min_distance - 6) * 0.1  # Further away is worse
            
            scored_systems.append((candidate, max(0.1, score)))
    
    # Sort by score descending
    scored_systems.sort(key=lambda x: x[1], reverse=True)
    return [system for system, score in scored_systems]