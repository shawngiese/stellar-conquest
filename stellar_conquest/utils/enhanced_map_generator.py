#!/usr/bin/env python3
"""
Enhanced Map Generator for Stellar Conquest using the existing mapgenerator.py approach.
Integrates matplotlib-based hex map generation with task force tracking and movement visualization.
"""

import matplotlib
# Use non-interactive backend for thread safety and server environments
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import sys
import os
import warnings
from typing import Dict, List, Tuple, Set

# Import from existing mapgenerator
import importlib.util
import os

# Load mapgenerator.py from the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
mapgen_path = os.path.join(current_dir, 'mapgenerator.py')
spec = importlib.util.spec_from_file_location("mapgenerator", mapgen_path)
mapgenerator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapgenerator)

# Extract needed functions
get_hex_vertices = mapgenerator.get_hex_vertices
get_hex_label = mapgenerator.get_hex_label
star_data2 = mapgenerator.star_data2
cloud_data = mapgenerator.cloud_data
coordinate_converter = mapgenerator.coordinate_converter
star_lookup = mapgenerator.star_lookup

# Import game components
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'stellar_conquest'))
from stellar_conquest.core.enums import ShipType

class EnhancedMapGenerator:
    """Enhanced map generator using matplotlib for better visual quality."""
    
    def __init__(self, figsize=(16, 12)):
        self.figsize = figsize
        self.hex_radius = 0.5
        self.circle_radius = 0.2
        self.num_columns = 32

        # Suppress matplotlib UserWarnings for cleaner output
        warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
        
        # Player colors - more vibrant for better visibility
        self.player_colors = {
            'Admiral Nova': '#FF3333',      # Bright Red
            'General Vega': '#00CC99',      # Bright Teal  
            'Captain Rex': '#3366FF',       # Bright Blue
            'Commander Luna': '#808080',    # Medium Gray
        }
        
        # Task force symbols with better visibility
        # Use task force numbers instead of symbols for clearer identification
        self.task_force_symbols = {}
        
        # Ship type abbreviations for tooltips
        self.ship_abbrev = {
            ShipType.SCOUT: 'S',
            ShipType.CORVETTE: 'C', 
            ShipType.COLONY_TRANSPORT: 'T',
            ShipType.FIGHTER: 'F',
            ShipType.DEATH_STAR: 'D'
        }
    
    def hex_coordinate_to_matplotlib(self, hex_coord: str) -> Tuple[float, float]:
        """Convert hex coordinate (like 'A1', 'D4') to matplotlib x,y position."""
        # Parse the coordinate
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        # Handle single and double letter columns
        if len(hex_coord) >= 2 and hex_coord[:2] in ['AA', 'BB', 'CC', 'DD', 'EE', 'FF']:
            col_str = hex_coord[:2]
            row_str = hex_coord[2:]
            col = letters.index(col_str[0]) + 26  # AA=26, BB=27, etc.
        else:
            col_str = hex_coord[0]
            row_str = hex_coord[1:]
            col = letters.index(col_str)
        
        # Convert row coordinate to match get_hex_label logic
        # get_hex_label uses: row_label = str(num_rows - row)
        # So we need to invert: row = num_rows - int(row_str)
        num_rows = 21 if col % 2 == 0 else 20
        row = num_rows - int(row_str)  # This gives us the correct internal row index
        
        # Calculate matplotlib coordinates (matching mapgenerator.py logic)
        x = col * self.hex_radius * 1.5
        y = row * self.hex_radius * np.sqrt(3) + (col % 2) * self.hex_radius * np.sqrt(3) / 2
        
        return x, y
    
    def create_base_map(self, game_state=None, turn_number=0) -> Tuple:
        """Create the base hex map with stars and gas clouds."""
        fig, ax = plt.subplots(figsize=self.figsize)
        ax.set_aspect('equal')
        ax.axis('off')

        # Set background color
        fig.patch.set_facecolor('#f8f9fa')

        # Adjust subplot to minimize top margin
        fig.subplots_adjust(top=0.96, bottom=0.02, left=0.02, right=0.98)

        # Draw title with minimal top spacing
        fig.suptitle(f'Stellar Conquest - Turn {turn_number}',
                    fontsize=16, fontweight='bold', y=0.99)
        
        # Draw hex grid with proper coloring
        for col in range(self.num_columns):
            num_rows = 21 if col % 2 == 0 else 20
            for row in range(num_rows):
                x = col * self.hex_radius * 1.5
                y = row * self.hex_radius * np.sqrt(3) + (col % 2) * self.hex_radius * np.sqrt(3) / 2
                
                # Get hex label for this position
                label = get_hex_label(col, row, num_rows)
                coordinates = label.lstrip('0')
                
                # Draw hex with appropriate color
                if coordinates in cloud_data.keys():
                    # Gas cloud hex
                    hex_coords = get_hex_vertices(x, y, self.hex_radius)
                    hex_polygon = plt.Polygon(hex_coords, edgecolor='turquoise', 
                                            facecolor='silver', alpha=0.7, linewidth=0.5)
                    ax.add_patch(hex_polygon)
                    
                    # Add cloud symbol
                    ax.text(x, y, '☁', ha='center', va='center', fontsize=8, 
                           color='purple', alpha=0.8)
                else:
                    # Regular hex
                    hex_coords = get_hex_vertices(x, y, self.hex_radius)
                    hex_polygon = plt.Polygon(hex_coords, edgecolor='turquoise', 
                                            facecolor='teal', alpha=0.3, linewidth=0.3)
                    ax.add_patch(hex_polygon)
                
                # Add hex coordinate labels (darker and more readable)
                ax.text(x, y + 0.35, label, ha='center', va='center', 
                       fontsize=5, color='black', alpha=0.9, fontweight='bold')
                
                # Draw stars
                if coordinates in star_data2.keys():
                    star_info = star_data2[coordinates]
                    star_color = star_info['color']
                    star_name = star_info['starname']
                    
                    # Draw star circle
                    star_circle = plt.Circle((x, y), self.circle_radius,
                                           facecolor=star_color, alpha=0.9, zorder=5)
                    ax.add_patch(star_circle)
                    
                    # Add check mark if star has been explored
                    if game_state and game_state.board.star_systems.get(coordinates):
                        ax.text(x, y, '✓', ha='center', va='center', 
                               fontsize=12, fontweight='bold', color='white', zorder=7)
                    
                    # Add star name
                    ax.text(x, y - 0.35, star_name, ha='center', va='center', 
                           fontsize=6, color=star_color, weight='bold', zorder=6)
                    
                    # Add command post antenna icons for players with command posts
                    if game_state and hasattr(game_state, 'command_posts') and coordinates in game_state.command_posts:
                        self._draw_command_post_antennas(ax, x, y, game_state.command_posts[coordinates])
        
        # Draw communication ranges for all players (7 hex radius from entry points)
        if game_state:
            self._draw_communication_ranges(ax, game_state)
        
        # Set map boundaries
        x_min = -1 * self.hex_radius
        x_max = self.num_columns * self.hex_radius * 1.5 + self.hex_radius
        y_min = -1 * self.hex_radius
        y_max = 21 * self.hex_radius * np.sqrt(3) + self.hex_radius * np.sqrt(3) / 2
        
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        
        return fig, ax
    
    def _draw_communication_ranges(self, ax, game_state):
        """Draw communication ranges (7-hex radius) around each player's entry point."""
        player_colors = {
            'Admiral Nova': '#FF6B6B',      # Red
            'General Vega': '#4ECDC4',      # Teal  
            'Captain Rex': '#45B7D1',       # Blue
            'Commander Luna': '#96CEB4'     # Green
        }
        
        for player in game_state.players:
            entry_hex = player.entry_hex
            player_color = player_colors.get(player.name, '#666666')
            
            # Get all hexes exactly 7 distance from entry point
            range_hexes = self._get_hexes_at_distance(entry_hex, 7)
            
            # Draw colored borders on the outer edge of these hexes
            for hex_coord in range_hexes:
                try:
                    x, y = self.hex_coordinate_to_matplotlib(hex_coord)
                    
                    # Draw a thick colored border around this hex
                    hex_coords = get_hex_vertices(x, y, self.hex_radius)
                    hex_outline = plt.Polygon(hex_coords, 
                                            edgecolor=player_color, 
                                            facecolor='none', 
                                            linewidth=3.0, 
                                            alpha=0.8,
                                            zorder=2)
                    ax.add_patch(hex_outline)
                except:
                    # Skip if coordinate conversion fails
                    pass
    
    def _draw_command_post_antennas(self, ax, star_x, star_y, player_ids):
        """Draw triangle icons for players with command posts at this star system."""
        player_list = list(player_ids)
        num_players = len(player_list)
        
        if num_players == 0:
            return
        
        # Position triangles on the right side of the star hex
        triangle_spacing = 0.15  # Vertical spacing between triangles
        start_y = star_y + (num_players - 1) * triangle_spacing / 2  # Center the group
        
        for i, player_id in enumerate(player_list):
            # Calculate position for this triangle (right side of star)
            triangle_x = star_x + 0.4  # Offset to the right of star center
            triangle_y = start_y - i * triangle_spacing
            
            # Get player color (map player_id to player name and then to color)
            player_color = '#888888'  # Default gray
            if player_id == 1:
                player_color = self.player_colors.get('Admiral Nova', '#FF3333')
            elif player_id == 2:
                player_color = self.player_colors.get('General Vega', '#00CC99')
            elif player_id == 3:
                player_color = self.player_colors.get('Captain Rex', '#3366FF')
            elif player_id == 4:
                player_color = self.player_colors.get('Commander Luna', '#808080')
            
            # Draw simple triangle
            triangle_size = 0.1
            
            # Triangle pointing up
            triangle = plt.Polygon([
                [triangle_x, triangle_y + triangle_size],  # Top point
                [triangle_x - triangle_size*0.8, triangle_y - triangle_size*0.5],  # Bottom left
                [triangle_x + triangle_size*0.8, triangle_y - triangle_size*0.5]   # Bottom right
            ], color=player_color, zorder=8)
            ax.add_patch(triangle)
    
    def _get_hexes_at_distance(self, center_hex, distance):
        """Get all hex coordinates at exactly the specified distance from center."""
        # Convert center hex to cube coordinates for distance calculation
        center_cube = self._hex_to_cube(center_hex)
        if center_cube is None:
            return []
        
        result_hexes = []
        
        # Check all hexes on the map to find those at exact distance
        for col in range(self.num_columns):
            num_rows = 21 if col % 2 == 0 else 20
            for row in range(num_rows):
                hex_label = get_hex_label(col, row, num_rows)
                hex_coord = hex_label.lstrip('0')
                
                # Convert to cube coordinates and calculate distance
                hex_cube = self._hex_to_cube(hex_coord)
                if hex_cube is not None:
                    hex_distance = self._cube_distance(center_cube, hex_cube)
                    if hex_distance == distance:
                        result_hexes.append(hex_coord)
        
        return result_hexes
    
    def _hex_to_cube(self, hex_coord):
        """Convert hex coordinate (like 'A1', 'BB15') to cube coordinates (x,y,z)."""
        try:
            # Parse the hex coordinate
            col_part = ''
            row_part = ''
            
            for char in hex_coord:
                if char.isalpha():
                    col_part += char
                else:
                    row_part += char
            
            if not col_part or not row_part:
                return None
            
            # Convert column letters to number using same logic as hex_coordinate_to_matplotlib
            letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            if len(col_part) == 2 and col_part in ['AA', 'BB', 'CC', 'DD', 'EE', 'FF']:
                # Double letter: AA=26, BB=27, CC=28, DD=29, EE=30, FF=31
                col = letters.index(col_part[0]) + 26
            else:
                # Single letter: A=0, B=1, ..., Z=25
                col = letters.index(col_part)
            
            # Convert row coordinate to match get_hex_label logic (same as hex_coordinate_to_matplotlib)
            num_rows = 21 if col % 2 == 0 else 20
            row = num_rows - int(row_part)  # This gives us the correct internal row index
            
            # Convert offset coordinates to cube coordinates
            # For hex grids with offset coordinates
            q = col
            r = row - (col - (col & 1)) // 2
            s = -q - r
            
            return (q, r, s)
        except:
            return None
    
    def _cube_distance(self, cube1, cube2):
        """Calculate distance between two cube coordinates."""
        return (abs(cube1[0] - cube2[0]) + abs(cube1[1] - cube2[1]) + abs(cube1[2] - cube2[2])) // 2
    
    def _get_hex_neighbors(self, hex_coord):
        """Get all 6 neighboring hex coordinates for a given hex."""
        cube = self._hex_to_cube(hex_coord)
        if cube is None:
            return []
        
        # Cube coordinate directions for 6 neighbors
        directions = [
            (1, -1, 0), (1, 0, -1), (0, 1, -1),
            (-1, 1, 0), (-1, 0, 1), (0, -1, 1)
        ]
        
        neighbors = []
        for dx, dy, dz in directions:
            neighbor_cube = (cube[0] + dx, cube[1] + dy, cube[2] + dz)
            neighbor_hex = self._cube_to_hex(neighbor_cube)
            if neighbor_hex:
                neighbors.append(neighbor_hex)
        
        return neighbors
    
    def _cube_to_hex(self, cube):
        """Convert cube coordinates back to hex coordinate string."""
        try:
            q, r, s = cube
            
            # Convert cube to offset coordinates
            col = q
            row = r + (q - (q & 1)) // 2
            
            # Convert to hex string coordinate
            letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            
            if col >= 26:
                # Double letter columns: AA=26, BB=27, etc.
                if col <= 31:  # Only handle AA-FF
                    col_str = letters[col - 26] + letters[col - 26]
                else:
                    return None  # Outside valid range
            else:
                # Single letter columns: A=0, B=1, etc.
                col_str = letters[col]
            
            # Calculate row number in hex notation
            num_rows = 21 if col % 2 == 0 else 20
            row_num = num_rows - row
            
            if row_num < 1 or row_num > num_rows:
                return None  # Outside valid range
            
            return f"{col_str}{row_num}"
        except:
            return None
    
    def highlight_command_post_range(self, ax, game_state, player_id, range_distance=8):
        """Highlight the outer perimeter of range_distance from player's command posts."""
        if not hasattr(game_state, 'command_posts'):
            return
        
        # Get player color
        player = game_state.get_player_by_id(player_id)
        if not player:
            return
        
        player_color = self.player_colors.get(player.name, '#808080')
        
        # Find all command post locations for this player
        command_post_hexes = []
        for location, player_ids in game_state.command_posts.items():
            if player_id in player_ids:
                command_post_hexes.append(location)
        
        if not command_post_hexes:
            return
        
        # Get all hexes within range_distance from any command post
        all_reachable_hexes = set()
        for command_post in command_post_hexes:
            for distance in range(range_distance + 1):  # 0 to range_distance inclusive
                hexes_at_distance = self._get_hexes_at_distance(command_post, distance)
                all_reachable_hexes.update(hexes_at_distance)
        
        # Find perimeter hexes and draw their farthest edge from command posts
        perimeter_hexes_processed = set()
        
        for command_post in command_post_hexes:
            hexes_at_max_range = self._get_hexes_at_distance(command_post, range_distance)
            for hex_coord in hexes_at_max_range:
                if hex_coord in perimeter_hexes_processed:
                    continue  # Already processed this hex from another command post
                    
                # Find the edge that is farthest from the nearest command post
                farthest_edge = self._find_farthest_edge_from_command_posts(hex_coord, command_post_hexes)
                
                if farthest_edge is not None:
                    self._draw_hex_edges(ax, hex_coord, [farthest_edge], player_color)
                    perimeter_hexes_processed.add(hex_coord)
    
    def _find_farthest_edge_from_command_posts(self, hex_coord, command_post_hexes):
        """Find the edge index (0-5) that is farthest from all command posts."""
        try:
            x, y = self.hex_coordinate_to_matplotlib(hex_coord)
            hex_vertices = get_hex_vertices(x, y, self.hex_radius)
            
            max_min_distance = -1
            farthest_edge_idx = None
            
            # Check each of the 6 edges
            for edge_idx in range(6):
                # Get the midpoint of this edge
                v1 = hex_vertices[edge_idx]
                v2 = hex_vertices[(edge_idx + 1) % 6]
                edge_midpoint = ((v1[0] + v2[0]) / 2, (v1[1] + v2[1]) / 2)
                
                # Find minimum distance from this edge midpoint to any command post
                min_distance_to_command_post = float('inf')
                for command_post in command_post_hexes:
                    cp_x, cp_y = self.hex_coordinate_to_matplotlib(command_post)
                    distance = ((edge_midpoint[0] - cp_x) ** 2 + (edge_midpoint[1] - cp_y) ** 2) ** 0.5
                    min_distance_to_command_post = min(min_distance_to_command_post, distance)
                
                # Keep track of the edge with maximum minimum distance to command posts
                if min_distance_to_command_post > max_min_distance:
                    max_min_distance = min_distance_to_command_post
                    farthest_edge_idx = edge_idx
            
            return farthest_edge_idx
        except:
            return None
    
    def _draw_hex_edges(self, ax, hex_coord, edge_indices, color):
        """Draw specific edges of a hex given edge indices (0-5)."""
        try:
            x, y = self.hex_coordinate_to_matplotlib(hex_coord)
            hex_vertices = get_hex_vertices(x, y, self.hex_radius)
            
            # Draw each specified edge
            for edge_idx in edge_indices:
                # Get the two vertices that form this edge
                v1 = hex_vertices[edge_idx]
                v2 = hex_vertices[(edge_idx + 1) % 6]  # Next vertex (wrapping around)
                
                # Draw line segment for this edge
                ax.plot([v1[0], v2[0]], [v1[1], v2[1]], 
                       color=color, linewidth=3, alpha=0.9, zorder=2)
                
        except:
            # Skip if coordinate conversion fails
            pass
    
    def highlight_all_players_ranges(self, ax, game_state, range_distance=8):
        """Highlight command post ranges for all players."""
        for player in game_state.players:
            self.highlight_command_post_range(ax, game_state, player.player_id, range_distance)
    
    def add_task_forces(self, fig, ax, game_state, turn_number: int):
        """Add task force positions and information to the map."""
        
        # Add task force path lines first (so they appear under markers)
        self.add_task_force_paths(ax, game_state)
        
        # Group task forces by location to handle multiple TFs on same hex
        location_groups = {}
        
        # First pass: collect all task forces by location
        for player_idx, player in enumerate(game_state.players):
            color = self.player_colors.get(player.name, '#333333')
            
            for group_index, group in enumerate(player.ship_groups):
                location = group.location
                
                # Group ships by actual task force IDs
                tf_ships = {}
                for ship in group.ships:
                    tf_id = ship.task_force_id
                    ship_type = ship.ship_type
                    count = ship.count
                    
                    if tf_id not in tf_ships:
                        tf_ships[tf_id] = {}
                    if ship_type not in tf_ships[tf_id]:
                        tf_ships[tf_id][ship_type] = 0
                    tf_ships[tf_id][ship_type] += count
                
                for tf_id, ships in tf_ships.items():
                    # Add each actual task force to the location groups
                    if location not in location_groups:
                        location_groups[location] = []
                    
                    location_groups[location].append({
                        'player': player,
                        'color': color,
                        'tf_number': tf_id,  # Use actual task force ID
                        'group': group,
                        'ships': ships  # Store the ship composition for this specific TF
                    })
        
        # Second pass: draw task forces with positioning for multiple TFs
        for location, task_forces in location_groups.items():
            # Get matplotlib coordinates for this hex
            try:
                center_x, center_y = self.hex_coordinate_to_matplotlib(location)
            except:
                continue  # Skip if coordinate conversion fails
            
            num_tfs = len(task_forces)
            
            if num_tfs == 1:
                # Single task force - use normal size and center position
                tf_data = task_forces[0]
                self._draw_single_task_force(ax, center_x, center_y, tf_data, game_state)
            else:
                # Multiple task forces - use smaller symbols arranged around the hex
                self._draw_multiple_task_forces(ax, center_x, center_y, task_forces, game_state)
    
    def _draw_single_task_force(self, ax, x, y, tf_data, game_state):
        """Draw a single task force at full size."""
        player = tf_data['player']
        color = tf_data['color']
        tf_number = tf_data['tf_number']
        group = tf_data['group']
        
        # Draw task force circle at normal size
        tf_circle = plt.Circle((x, y), self.circle_radius * 1.2,
                             facecolor=color, edgecolor='white',
                             alpha=0.8, zorder=10, linewidth=2)
        ax.add_patch(tf_circle)
        
        # Add task force symbol
        symbol = self.task_force_symbols.get(tf_number, str(tf_number))
        ax.text(x, y, symbol, ha='center', va='center', 
               fontsize=10, color='white', fontweight='bold', zorder=11)
        
        # Add ship composition and destination info
        # For TF1, position label outside the hex area near entry point
        if tf_number == 1:
            self._add_tf1_info_near_entry(ax, x, y, tf_data, game_state)
        else:
            self._add_task_force_info(ax, x, y, tf_data, game_state)
    
    def _draw_multiple_task_forces(self, ax, center_x, center_y, task_forces, game_state):
        """Draw multiple task forces arranged around a hex with smaller symbols."""
        import math
        
        num_tfs = len(task_forces)
        # Reduce circle size for multiple task forces
        small_radius = self.circle_radius * 0.6
        # Arrange in a circle around the hex center
        arrangement_radius = self.circle_radius * 0.8
        
        # Multiple task forces on same hex - no central label needed
        
        for i, tf_data in enumerate(task_forces):
            # Calculate position around the hex
            angle = 2 * math.pi * i / num_tfs
            tf_x = center_x + arrangement_radius * math.cos(angle)
            tf_y = center_y + arrangement_radius * math.sin(angle)
            
            color = tf_data['color']
            tf_number = tf_data['tf_number']
            player_name = tf_data['player'].name
            
            # Draw smaller task force circle
            tf_circle = plt.Circle((tf_x, tf_y), small_radius,
                                 facecolor=color, edgecolor='white',
                                 alpha=0.8, zorder=10, linewidth=1)
            ax.add_patch(tf_circle)
            
            # Add task force symbol (smaller font)
            symbol = self.task_force_symbols.get(tf_number, str(tf_number))
            ax.text(tf_x, tf_y, symbol, ha='center', va='center', 
                   fontsize=7, color='white', fontweight='bold', zorder=11)
            
            # Skip the extra player identification boxes when multiple TFs on same hex
            
            # Add ship composition info (positioned to avoid overlap)
            # Calculate offset based on position around circle to prevent label overlap
            label_offset_x = 0.5 * math.cos(angle)
            label_offset_y = 0.5 * math.sin(angle)
            self._add_task_force_info(ax, tf_x, tf_y, tf_data, game_state, small=True, 
                                    extra_offset_x=label_offset_x, extra_offset_y=label_offset_y)
    
    def _add_task_force_info(self, ax, x, y, tf_data, game_state, small=False, extra_offset_x=0, extra_offset_y=0):
        """Add ship composition and destination info for a task force."""
        player = tf_data['player']
        color = tf_data['color']
        tf_number = tf_data['tf_number']
        group = tf_data['group']
        
        # Get ship composition
        ship_counts = group.get_ship_counts()
        ship_summary = []
        for ship_type, count in ship_counts.items():
            if count > 0:
                abbrev = self.ship_abbrev.get(ship_type, '?')
                ship_summary.append(f"{count}{abbrev}")
        
        # Get destination from movement plans
        destination_text = ""
        if hasattr(game_state, 'movement_plans') and game_state.movement_plans:
            player_plans = game_state.movement_plans.get(player.player_id, {})
            plan = player_plans.get(tf_number, {})
            if 'final_destination' in plan:
                destination_text = f" → {plan['final_destination']}"
        
        # Add ship composition and destination as small text near task force
        if ship_summary:
            composition_text = ','.join(ship_summary) + destination_text
            
            # Calculate smart offset to avoid overlapping with other task force icons
            offset_x, offset_y = self._calculate_smart_label_offset(ax, x, y, game_state, tf_data, small, extra_offset_x, extra_offset_y)
            
            # Adjust font size based on task force size
            fontsize = 5 if small else 6
            
            ax.text(x + offset_x, y + offset_y, composition_text, 
                   ha='left', va='bottom', fontsize=fontsize, 
                   color=color, fontweight='bold', zorder=12,
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
    
    def _calculate_smart_label_offset(self, ax, x, y, game_state, tf_data, small=False, extra_offset_x=0, extra_offset_y=0):
        """Calculate label offset that avoids overlapping with other task force icons."""
        current_location = tf_data['group'].location
        
        # Count task forces at this location to determine if it's a dense hex
        tf_count_at_location = 0
        for player in game_state.players:
            for group in player.ship_groups:
                if group.location == current_location:
                    tf_count_at_location += 1
        
        # Special handling for dense hexes (4+ task forces)
        if tf_count_at_location >= 4:
            # Use radial positioning for dense hexes
            tf_index = 0
            for player in game_state.players:
                for group in player.ship_groups:
                    if group.location == current_location:
                        if group == tf_data['group']:
                            break
                        tf_index += 1
            
            # Calculate radial position
            import math
            angle = (tf_index * 2 * math.pi) / tf_count_at_location
            radius = 0.7 if not small else 0.5
            offset_x = radius * math.cos(angle)
            offset_y = radius * math.sin(angle)
            return offset_x, offset_y
        
        # Base offset values for non-dense hexes
        if small:
            base_offset_x, base_offset_y = 0.3, 0.2
        else:
            base_offset_x, base_offset_y = 0.4, 0.3
        
        # Apply any extra offset passed in
        base_offset_x += extra_offset_x
        base_offset_y += extra_offset_y
        
        # Define potential offset positions in order of preference
        # Each tuple is (offset_x, offset_y, description)
        potential_offsets = [
            (base_offset_x, base_offset_y, "top-right"),           # Default
            (base_offset_x, -base_offset_y, "bottom-right"),       # Move down
            (-base_offset_x, base_offset_y, "top-left"),           # Move left  
            (-base_offset_x, -base_offset_y, "bottom-left"),       # Move down-left
            (0, base_offset_y + 0.2, "top-center"),               # Move up
            (0, -base_offset_y - 0.2, "bottom-center"),           # Move further down
            (base_offset_x + 0.3, 0, "center-right"),             # Move further right
            (-base_offset_x - 0.3, 0, "center-left"),             # Move further left
        ]
        
        # Get all task force positions to check for conflicts
        all_tf_positions = self._get_all_task_force_positions(game_state)
        current_tf_location = tf_data['group'].location
        
        # Try each offset position and pick the first one that doesn't conflict
        for offset_x, offset_y, description in potential_offsets:
            label_x = x + offset_x
            label_y = y + offset_y
            
            # Check if this label position would overlap with any task force icon
            has_conflict = False
            for tf_location, tf_pos in all_tf_positions.items():
                if tf_location == current_tf_location:
                    continue  # Skip self
                
                tf_x, tf_y = tf_pos
                # Calculate distance between label position and task force icon
                distance = ((label_x - tf_x) ** 2 + (label_y - tf_y) ** 2) ** 0.5
                
                # If label would be too close to another task force icon, it's a conflict
                min_distance = 0.6  # Minimum distance to avoid visual overlap
                if distance < min_distance:
                    has_conflict = True
                    break
            
            # If no conflict found, use this offset
            if not has_conflict:
                return offset_x, offset_y
        
        # If all positions have conflicts, use the default with a larger offset
        return base_offset_x + 0.5, base_offset_y + 0.5
    
    def _get_all_task_force_positions(self, game_state):
        """Get positions of all task forces for conflict detection."""
        positions = {}
        
        for player in game_state.players:
            for tf_index, group in enumerate(player.ship_groups):
                location = group.location
                try:
                    x, y = self.hex_coordinate_to_matplotlib(location)
                    positions[location] = (x, y)
                except:
                    pass  # Skip if coordinate conversion fails
        
        return positions
        
    def _add_tf1_info_near_entry(self, ax, x, y, tf_data, game_state):
        """Add TF1 ship composition info positioned outside hex area near entry point."""
        player = tf_data['player']
        color = tf_data['color']
        group = tf_data['group']
        
        # Get ship composition
        ship_counts = group.get_ship_counts()
        ship_summary = []
        for ship_type, count in ship_counts.items():
            if count > 0:
                abbrev = self.ship_abbrev.get(ship_type, '?')
                ship_summary.append(f"{count}{abbrev}")
        
        if ship_summary:
            composition_text = f"TF1: {','.join(ship_summary)}"
            
            # Position TF1 label outside the hex grid based on entry point
            entry_hex = player.entry_hex
            
            # Position TF1 labels closer to the edge of entry hex
            if entry_hex.startswith('A1') or entry_hex.startswith('B1') or entry_hex.startswith('C1') or entry_hex == 'FF1':  # Top row entries
                offset_x, offset_y = 0, 0.7  # Above entry hex
                va_align = 'bottom'
            elif entry_hex.startswith('A2') or entry_hex.startswith('B2') or entry_hex == 'FF20':  # Bottom row entries  
                offset_x, offset_y = 0, -0.7  # Below entry hex
                va_align = 'top'
            else:  # Side entries
                if entry_hex.startswith('A'):  # Left side
                    offset_x, offset_y = -0.7, 0
                    va_align = 'center'
                else:  # Right side or other
                    offset_x, offset_y = 0.7, 0
                    va_align = 'center'
            
            ax.text(x + offset_x, y + offset_y, composition_text, 
                   ha='center', va=va_align, fontsize=7, 
                   color=color, fontweight='bold', zorder=12,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
    
    def add_task_force_paths(self, ax, game_state):
        """Add white path lines showing task force movement plans."""
        # Check if we have movement plans stored on the game state
        if hasattr(game_state, 'movement_plans') and game_state.movement_plans:
            for player_id, player_plans in game_state.movement_plans.items():
                for tf_id, plan in player_plans.items():
                    try:
                        if 'planned_path' in plan and 'path_index' in plan:
                            # New path structure - draw next turn's movement only
                            planned_path = plan['planned_path']
                            path_index = plan.get('path_index', 0)
                            
                            # Get player to determine movement speed
                            player = None
                            for p in game_state.players:
                                if p.player_id == player_id:
                                    player = p
                                    break
                            
                            if player and path_index < len(planned_path) - 1:
                                # Calculate how far the task force will move next turn using gas cloud rules
                                effective_speed = player.current_ship_speed
                                # Note: Turn 1 penalty is handled in movement execution, not here
                                
                                # Determine end position for next turn's movement considering gas clouds
                                next_turn_end_index = self._calculate_next_turn_end_position(
                                    planned_path, path_index, effective_speed)
                                
                                # Draw solid white line from current position to next turn's end position
                                if next_turn_end_index > path_index:
                                    # Draw the path segments for next turn's movement (solid line)
                                    for i in range(path_index, next_turn_end_index):
                                        if i + 1 < len(planned_path):
                                            x1, y1 = self.hex_coordinate_to_matplotlib(planned_path[i])
                                            x2, y2 = self.hex_coordinate_to_matplotlib(planned_path[i + 1])
                                            
                                            ax.plot([x1, x2], [y1, y2], color='white', 
                                                   linewidth=4, alpha=0.9, zorder=5)
                                
                                # Draw dashed white line for remaining path to final destination
                                if next_turn_end_index < len(planned_path) - 1:
                                    # Draw the remaining path segments (dashed line)
                                    for i in range(next_turn_end_index, len(planned_path) - 1):
                                        x1, y1 = self.hex_coordinate_to_matplotlib(planned_path[i])
                                        x2, y2 = self.hex_coordinate_to_matplotlib(planned_path[i + 1])
                                        
                                        ax.plot([x1, x2], [y1, y2], color='white', 
                                               linewidth=3, alpha=0.7, linestyle='--', zorder=4)
                        
                        elif 'current_location' in plan and 'next_hex' in plan and 'final_destination' in plan:
                            # Legacy path structure - for backward compatibility
                            x1, y1 = self.hex_coordinate_to_matplotlib(plan['current_location'])
                            x2, y2 = self.hex_coordinate_to_matplotlib(plan['next_hex'])
                            ax.plot([x1, x2], [y1, y2], color='white', 
                                   linewidth=4, alpha=0.9, zorder=5)
                            
                            # Draw dotted path from next hex to final destination
                            if plan['next_hex'] != plan['final_destination']:
                                x3, y3 = self.hex_coordinate_to_matplotlib(plan['final_destination'])
                                ax.plot([x2, x3], [y2, y3], color='white', 
                                       linewidth=3, alpha=0.7, linestyle='--', zorder=5)
                    except Exception as e:
                        pass
    
    def _calculate_next_turn_end_position(self, planned_path, current_path_index, ship_speed):
        """
        Calculate where a task force will end up after one turn of movement,
        considering gas cloud movement restrictions.
        """
        from stellar_conquest.core.constants import GAS_CLOUD_HEXES
        gas_cloud_hexes = set(GAS_CLOUD_HEXES)
        
        movement_this_turn = 0
        position_index = current_path_index
        current_hex = planned_path[position_index] if position_index < len(planned_path) else planned_path[-1]
        is_starting_in_gas_cloud = current_hex in gas_cloud_hexes
        
        # Apply gas cloud movement rules
        if is_starting_in_gas_cloud:
            # Starting in gas cloud - can move full speed when leaving
            while (movement_this_turn < ship_speed and 
                   position_index + 1 < len(planned_path)):
                
                next_hex = planned_path[position_index + 1]
                position_index += 1
                movement_this_turn += 1
                
                # If entering another gas cloud, movement ends
                if next_hex in gas_cloud_hexes:
                    break
        else:
            # Starting in normal space
            while (movement_this_turn < ship_speed and 
                   position_index + 1 < len(planned_path)):
                
                next_hex = planned_path[position_index + 1]
                
                # Check if entering gas cloud
                if next_hex in gas_cloud_hexes:
                    # Entering gas cloud ends turn
                    position_index += 1
                    movement_this_turn = ship_speed  # End turn
                    break
                else:
                    # Normal movement
                    position_index += 1
                    movement_this_turn += 1
        
        # Ensure we don't go past the end of the path
        return min(position_index, len(planned_path) - 1)

    def add_movement_trails(self, fig, ax, movement_history: Dict):
        """Add movement trails showing where task forces have moved."""
        # This would require tracking movement history between turns
        # For now, we'll add a placeholder for future enhancement
        pass
    
    def create_turn_map(self, game_state, turn_number: int, 
                       movement_history: Dict = None, 
                       save_path: str = None) -> str:
        """Create a complete map for a specific turn."""
        
        # Create base map
        fig, ax = self.create_base_map(game_state, turn_number)
        
        # Add range highlighting for all players (appears under other elements)
        self.highlight_all_players_ranges(ax, game_state, range_distance=8)
        
        # Add task forces and game information
        self.add_task_forces(fig, ax, game_state, turn_number)
        
        # Add movement trails if available
        if movement_history:
            self.add_movement_trails(fig, ax, movement_history)
        
        # Save the map
        if save_path is None:
            # Ensure output directory exists
            os.makedirs('output/maps', exist_ok=True)
            save_path = f"output/maps/enhanced_turn_{turn_number}_map.svg"
        else:
            # Ensure we're using .svg extension
            save_path = save_path.replace('.png', '.svg')

        # Suppress tight layout warnings when using bbox_inches='tight'
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*tight layout.*')
            try:
                # Save only as SVG for scalability
                fig.savefig(save_path, format='svg', bbox_inches='tight',
                           facecolor='#f8f9fa', transparent=False)

                print(f"📊 Enhanced map saved: {save_path}")
            except Exception as e:
                print(f"Warning: Error saving map {save_path}: {str(e)}")
            finally:
                plt.close(fig)  # Always close to free memory
        return save_path
    
    def create_player_range_map(self, game_state, turn_number: int, player_id: int,
                               movement_history: Dict = None, 
                               save_path: str = None) -> str:
        """Create a map showing a player's command post range (8 hex radius)."""
        
        # Create base map
        fig, ax = self.create_base_map(game_state, turn_number)
        
        # Add range highlighting first (so it appears under other elements)
        self.highlight_command_post_range(ax, game_state, player_id, range_distance=8)
        
        # Add task forces and game information
        self.add_task_forces(fig, ax, game_state, turn_number)
        
        # Add movement trails if available
        if movement_history:
            self.add_movement_trails(fig, ax, movement_history)
        
        # Get player name for filename
        player = game_state.get_player_by_id(player_id)
        player_name = player.name.replace(' ', '_') if player else f"player_{player_id}"
        
        # Save the map
        if save_path is None:
            # Ensure output directory exists
            os.makedirs('output/maps', exist_ok=True)
            save_path = f"output/maps/enhanced_turn_{turn_number}_{player_name}_range.svg"
        else:
            # Ensure we're using .svg extension
            save_path = save_path.replace('.png', '.svg')

        # Suppress tight layout warnings when using bbox_inches='tight'
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*tight layout.*')
            try:
                # Save only as SVG for scalability
                fig.savefig(save_path, format='svg', bbox_inches='tight',
                           facecolor='#f8f9fa', transparent=False)

                print(f"📊 Player range map saved: {save_path}")
            except Exception as e:
                print(f"Warning: Error saving range map {save_path}: {str(e)}")
            finally:
                plt.close(fig)  # Always close to free memory
        return save_path

def test_enhanced_generator():
    """Test the enhanced map generator with sample data."""
    print("🧪 Testing Enhanced Map Generator...")
    
    # Create sample game state
    sys.path.insert(0, os.path.dirname(__file__))
    from stellar_conquest.game.game_state import create_game, GameSettings
    from stellar_conquest.core.enums import PlayStyle
    
    game_state = create_game(GameSettings())
    game_state.add_player("Admiral Nova", PlayStyle.EXPANSIONIST, "A1")
    game_state.add_player("General Vega", PlayStyle.WARLORD, "A21") 
    game_state.add_player("Captain Rex", PlayStyle.BALANCED, "FF1")
    game_state.start_game()
    
    # Create enhanced map
    generator = EnhancedMapGenerator()
    map_path = generator.create_turn_map(game_state, 0, save_path="output/maps/test_enhanced_map.svg")
    
    print(f"✅ Test map created: {map_path}")
    print("🖼️  Open the PNG or SVG file to view the enhanced map!")

if __name__ == "__main__":
    test_enhanced_generator()