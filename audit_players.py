#!/usr/bin/env python3
"""
Stellar Conquest Player Log Splitter

This script takes an output file (like output_stats28.txt) and creates separate
files for each player containing only their relevant turn information.

Usage:
    python3 audit_players.py <input_file> [output_directory]
    python3 audit_players.py --help
    python3 audit_players.py --list

Examples:
    python3 audit_players.py output/output_stats28.txt
    python3 audit_players.py output/output_stats28.txt my_game_logs/
"""

import re
import sys
import os
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def extract_player_name(turn_header: str) -> Tuple[Optional[int], Optional[str]]:
    """Extract turn number and player name from turn header."""
    match = re.match(r'TURN (\d+) - (.+?)\'S TURN', turn_header.strip())
    if match:
        turn_num = int(match.group(1))
        player_name = match.group(2)
        return turn_num, player_name
    return None, None


def normalize_player_name(player_name: str) -> str:
    """Convert player name to safe filename format."""
    safe_name = re.sub(r'[^\w\s-]', '', player_name.lower())
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    return safe_name


def find_output_files() -> List[str]:
    """Find available output files in the output directory."""
    patterns = [
        "output/output_stats*.txt",
        "output_stats*.txt",
        "output/*.txt"
    ]
    
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    
    return sorted(list(set(files)))


def parse_output_file(input_file: str) -> Dict[str, List[Tuple[int, List[str]]]]:
    """
    Parse the output file and organize content by player.
    
    Returns:
        Dict mapping player names to list of (turn_number, content_lines) tuples
    """
    
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    players_data = {}
    current_player = None
    current_turn = None
    current_lines = []
    header_lines = []
    in_header = True
    
    print(f"📖 Parsing {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Check if this is a turn header
        if 'TURN' in line and "'S TURN" in line:
            in_header = False
            
            # Save previous player's turn data if exists
            if current_player and current_lines:
                if current_player not in players_data:
                    players_data[current_player] = []
                players_data[current_player].append((current_turn, current_lines.copy()))
            
            # Start new player turn
            turn_num, player_name = extract_player_name(line_stripped)
            if turn_num is not None and player_name is not None:
                current_player = player_name
                current_turn = turn_num
                current_lines = [line]
                continue
        
        # Collect header information (before first turn)
        if in_header:
            header_lines.append(line)
            continue
        
        # Add line to current player's turn
        if current_player:
            current_lines.append(line)
    
    # Don't forget the last player's turn
    if current_player and current_lines:
        if current_player not in players_data:
            players_data[current_player] = []
        players_data[current_player].append((current_turn, current_lines.copy()))
    
    # Store header for later use
    parse_output_file._header_lines = header_lines
    return players_data


def write_player_files(players_data: Dict[str, List[Tuple[int, List[str]]]], 
                      output_dir: str, input_filename: str):
    """Write separate files for each player."""
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get the base name of input file for naming output files
    base_name = Path(input_filename).stem
    
    # Get header lines if available
    header_lines = getattr(parse_output_file, '_header_lines', [])
    
    created_files = []
    
    for player_name, turns_data in players_data.items():
        safe_name = normalize_player_name(player_name)
        output_file = os.path.join(output_dir, f"{base_name}_{safe_name}.txt")
        created_files.append(output_file)
        
        print(f"✍️  Writing {len(turns_data)} turns for {player_name} to {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header information
            if header_lines:
                f.write("=" * 70 + "\n")
                f.write(f"  {player_name.upper()}'S GAME LOG\n")
                f.write(f"  Extracted from: {os.path.basename(input_filename)}\n") 
                f.write("=" * 70 + "\n\n")
                
                # Write original header but modify title
                for line in header_lines:
                    if "STELLAR CONQUEST AUTO DEMO" in line:
                        f.write(line.replace("AUTO DEMO", f"PLAYER LOG - {player_name.upper()}"))
                    elif line.strip() and not line.startswith('🗺️') and not line.startswith('📊'):
                        f.write(line)
                
                f.write("\n" + "=" * 70 + "\n")
                f.write(f"  {player_name.upper()}'S TURNS\n")
                f.write("=" * 70 + "\n\n")
            
            # Write all turns for this player in chronological order
            turns_data.sort(key=lambda x: x[0])
            
            for turn_num, lines in turns_data:
                # Write turn separator
                f.write(f"\n{'═' * 70}\n")
                f.write(f"  TURN {turn_num}\n")
                f.write(f"{'═' * 70}\n")
                
                # Write turn content, skipping the original turn header
                for line in lines[1:]:
                    f.write(line)
                
                f.write("\n")
    
    print(f"✅ Created {len(players_data)} player files in {output_dir}/")
    return created_files


def get_game_summary(players_data: Dict[str, List[Tuple[int, List[str]]]]) -> str:
    """Generate a summary of the game data."""
    
    summary = []
    summary.append("📊 Game Summary:")
    summary.append(f"   Players found: {len(players_data)}")
    
    for player_name, turns_data in players_data.items():
        max_turn = max(turn_num for turn_num, _ in turns_data) if turns_data else 0
        summary.append(f"   - {player_name}: {len(turns_data)} turns (max turn {max_turn})")
    
    return "\n".join(summary)


def show_help():
    """Show help information."""
    print("""
🚀 Stellar Conquest Player Log Splitter
========================================

Splits Stellar Conquest output files into separate files for each player.

USAGE:
    python3 audit_players.py <input_file> [output_directory]
    python3 audit_players.py --help
    python3 audit_players.py --list

ARGUMENTS:
    input_file         Path to the output file to split (e.g., output/output_stats28.txt)
    output_directory   Directory to create player files (default: audit_players)

OPTIONS:
    --help, -h        Show this help message
    --list, -l        List available output files

EXAMPLES:
    python3 audit_players.py output/output_stats28.txt
    python3 audit_players.py output/output_stats28.txt my_analysis/
    python3 audit_players.py --list

OUTPUT:
    Creates separate files for each player:
    - output_stats28_admiral_nova.txt
    - output_stats28_general_vega.txt
    - output_stats28_captain_rex.txt
    - output_stats28_commander_luna.txt

FEATURES:
    • Preserves all original formatting and content
    • Creates clean, readable turn-by-turn organization
    • Safe filename generation from player names
    • Comprehensive game summary and statistics
    • Error handling with helpful messages

Use the individual player files to analyze strategies, review decisions,
and understand each player's gameplay patterns.
""")


def list_available_files():
    """List available output files."""
    print("🚀 Stellar Conquest Player Log Splitter")
    print("========================================\n")
    
    files = find_output_files()
    
    if not files:
        print("❌ No output files found.")
        print("\nLooked in:")
        print("  - output/output_stats*.txt")
        print("  - output_stats*.txt")
        print("  - output/*.txt")
        return
    
    print(f"📁 Found {len(files)} output files:\n")
    for i, file in enumerate(files, 1):
        # Get file size for display
        try:
            size = os.path.getsize(file)
            size_str = f"({size:,} bytes)" if size > 0 else "(empty)"
        except:
            size_str = "(size unknown)"
        
        print(f"  {i:2d}. {file} {size_str}")
    
    print(f"\nUSAGE:")
    print(f"  python3 audit_players.py <filename>")
    print(f"\nEXAMPLE:")
    if files:
        print(f"  python3 audit_players.py {files[0]}")


def print_success_info(created_files: List[str], output_dir: str):
    """Print success information and helpful commands."""
    print(f"\n🎉 Success! Player logs have been created in: {output_dir}/\n")
    
    print("📋 Created files:")
    for file in created_files:
        filename = os.path.basename(file)
        print(f"   - {filename}")
    
    print(f"\n💡 Quick access commands:")
    print(f"   ls {output_dir}/                     # List all created files")
    print(f"   head -50 {output_dir}/*.txt          # Preview all player files")
    print(f"   less {output_dir}/*.txt              # Browse individual files")
    
    # Extract base name for specific commands
    if created_files:
        first_file = os.path.basename(created_files[0])
        base_pattern = first_file.split('_')[0] + "_" + first_file.split('_')[1]  # e.g., "output_stats28"
        print(f"   grep \"COMBAT\" {output_dir}/{base_pattern}_*.txt  # Find combat events")
        print(f"   grep \"TF.*created\" {output_dir}/{base_pattern}_*.txt  # Find task force creations")


def main():
    """Main function."""
    
    # Handle special arguments
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ['--help', '-h']):
        show_help()
        return
    
    if len(sys.argv) == 2 and sys.argv[1] in ['--list', '-l']:
        list_available_files()
        return
    
    # Regular usage
    if len(sys.argv) < 2:
        print("❌ Error: Input file required.")
        print("Use --help for usage information.")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "audit_players"
    
    try:
        print("🚀 Stellar Conquest Player Log Splitter")
        print("=" * 50)
        
        # Check if input file exists
        if not os.path.exists(input_file):
            print(f"❌ Error: Input file '{input_file}' not found.")
            
            # Suggest available files
            files = find_output_files()
            if files:
                print(f"\n💡 Available files:")
                for file in files[:5]:  # Show first 5
                    print(f"   - {file}")
                if len(files) > 5:
                    print(f"   ... and {len(files) - 5} more (use --list to see all)")
            sys.exit(1)
        
        # Parse the input file
        players_data = parse_output_file(input_file)
        
        if not players_data:
            print("❌ No player data found in the input file!")
            print("\n💡 Make sure the file contains turn headers like:")
            print("   'TURN 1 - ADMIRAL NOVA'S TURN'")
            sys.exit(1)
        
        # Show summary
        print(get_game_summary(players_data))
        print()
        
        # Write player files
        created_files = write_player_files(players_data, output_dir, input_file)
        
        # Show success information
        print("\n" + "=" * 50)
        print_success_info(created_files, output_dir)
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()