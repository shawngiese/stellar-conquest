#!/usr/bin/env python3
"""
Stellar Conquest Taskforce Movement Audit Log Generator

This script analyzes Stellar Conquest output files and creates detailed movement
audit logs for each player's taskforces, tracking their activities turn by turn.

Usage:
    python3 audit_taskforce.py <input_file> [output_directory]
    python3 audit_taskforce.py --help
    python3 audit_taskforce.py --list

Examples:
    python3 audit_taskforce.py output/output_stats28.txt
    python3 audit_taskforce.py output/output_stats28.txt audit_logs/
"""

import re
import sys
import os
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class TaskForceEvent:
    """Represents a single taskforce event."""
    turn: int
    event_type: str  # 'created', 'moved', 'explored', 'combat', 'disbanded', 'colonized', etc.
    location: str
    details: str
    raw_line: str = ""


@dataclass
class TaskForce:
    """Represents a taskforce and its history."""
    tf_id: int
    player_name: str
    created_turn: Optional[int] = None
    initial_composition: str = ""
    target_destination: str = ""
    target_name: str = ""
    current_location: str = ""
    status: str = "active"  # active, disbanded, destroyed, arrived
    events: List[TaskForceEvent] = field(default_factory=list)
    
    def add_event(self, event: TaskForceEvent):
        """Add an event to this taskforce's history."""
        self.events.append(event)
        # Update current location if this is a movement event
        if event.event_type in ['moved', 'created'] and event.location:
            self.current_location = event.location


class TaskForceAuditor:
    """Main class for parsing and auditing taskforce movements."""
    
    def __init__(self):
        self.taskforces: Dict[str, Dict[int, TaskForce]] = defaultdict(lambda: {})  # player -> tf_id -> TaskForce
        self.current_turn = 0
        self.current_player = ""
        
    def extract_player_name(self, turn_header: str) -> Tuple[Optional[int], Optional[str]]:
        """Extract turn number and player name from turn header."""
        match = re.match(r'TURN (\d+) - (.+?)\'S TURN', turn_header.strip())
        if match:
            turn_num = int(match.group(1))
            player_name = match.group(2)
            return turn_num, player_name
        return None, None
    
    def parse_tf_creation(self, line: str) -> Optional[Tuple[int, str, str, str]]:
        """Parse taskforce creation line."""
        # Pattern: Creating TF2: 1 scout + 1 corvette → target Indi at D4
        creation_match = re.search(r'Creating TF(\d+): (.+?) → target (.+?) at ([A-Z]{1,2}\d+)', line)
        if creation_match:
            tf_id = int(creation_match.group(1))
            composition = creation_match.group(2)
            target_name = creation_match.group(3)
            target_location = creation_match.group(4)
            return tf_id, composition, target_name, target_location
        
        # Alternative pattern: Creating TF10: 35 colony transports + 4 corvette escorts → colonize Canis at G5
        alt_match = re.search(r'Creating TF(\d+): (.+?) → (.+?) at ([A-Z]{1,2}\d+)', line)
        if alt_match:
            tf_id = int(alt_match.group(1))
            composition = alt_match.group(2)
            action_target = alt_match.group(3)
            target_location = alt_match.group(4)
            return tf_id, composition, action_target, target_location
            
        return None
    
    def parse_tf_movement(self, line: str) -> Optional[Tuple[int, str, str]]:
        """Parse taskforce movement line."""
        # Pattern: ✅ TF2 advanced from A1 to B2 or ✅ TF6 advanced from CC2 to AA3
        movement_match = re.search(r'✅ TF(\d+) advanced from ([A-Z]{1,2}\d+) to ([A-Z]{1,2}\d+)', line)
        if movement_match:
            tf_id = int(movement_match.group(1))
            from_loc = movement_match.group(2)
            to_loc = movement_match.group(3)
            return tf_id, from_loc, to_loc
        return None
    
    def parse_tf_destination_reached(self, line: str) -> Optional[Tuple[int, str, str]]:
        """Parse taskforce destination reached events."""
        # Pattern: 🏁 TF2 has reached destination Indi!
        reached_match = re.search(r'🏁 TF(\d+) has reached destination (.+?)!', line)
        if reached_match:
            tf_id = int(reached_match.group(1))
            destination_name = reached_match.group(2)
            return tf_id, "", f"Reached destination {destination_name}"
        return None
    
    def parse_tf_status(self, line: str) -> Optional[Tuple[int, str, str]]:
        """Parse taskforce status line."""
        # Pattern: 🚀 TF2 at B2: or 🚀 TF6 at CC2:
        status_match = re.search(r'🚀 TF(\d+) at ([A-Z]{1,2}\d+):', line)
        if status_match:
            tf_id = int(status_match.group(1))
            location = status_match.group(2)
            return tf_id, location, "status_report"
        return None
    
    def parse_ship_composition(self, line: str) -> Optional[str]:
        """Parse ship composition from 'Ships:' lines."""
        if line.strip().startswith('Ships:'):
            return line.strip()[6:].strip()  # Remove 'Ships:' prefix
        return None
    
    def parse_declared_path(self, line: str) -> Optional[str]:
        """Parse declared path from taskforce status sections."""
        # Pattern: 📋 Declared path: A1 → B1 → B2 → C3 → C4 → D4
        if line.strip().startswith('📋 Declared path:'):
            return line.strip()[17:].strip()  # Remove '📋 Declared path:' prefix
        return None
    
    def parse_exploration(self, line: str) -> Optional[Tuple[int, str, str]]:
        """Parse exploration events."""
        # Look for exploration-related lines mentioning TF
        if 'TF' in line and ('explore' in line.lower() or 'discovered' in line.lower() or 'scouting' in line.lower()):
            tf_match = re.search(r'TF(\d+)', line)
            if tf_match:
                tf_id = int(tf_match.group(1))
                return tf_id, "", line.strip()
        return None
    
    def parse_combat(self, line: str) -> Optional[Tuple[int, str]]:
        """Parse combat events involving taskforces."""
        if 'TF' in line and ('combat' in line.lower() or 'battle' in line.lower() or 'attack' in line.lower()):
            tf_match = re.search(r'TF(\d+)', line)
            if tf_match:
                tf_id = int(tf_match.group(1))
                return tf_id, line.strip()
        return None
    
    def parse_file(self, input_file: str):
        """Parse the input file and extract taskforce information."""
        
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        print(f"📖 Parsing {input_file} for taskforce movements...")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_tf_being_processed = None
        current_tf_ship_composition = None
        current_tf_declared_path = None
        
        for line_num, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check for turn header
            turn_info = self.extract_player_name(line_stripped)
            if turn_info[0] is not None:
                self.current_turn, self.current_player = turn_info
                continue
            
            if not self.current_player:
                continue
                
            # Parse taskforce creation
            creation_info = self.parse_tf_creation(line_stripped)
            if creation_info:
                tf_id, composition, target_name, target_location = creation_info
                
                if tf_id not in self.taskforces[self.current_player]:
                    self.taskforces[self.current_player][tf_id] = TaskForce(
                        tf_id=tf_id,
                        player_name=self.current_player,
                        created_turn=self.current_turn,
                        initial_composition=composition,
                        target_destination=target_location,
                        target_name=target_name
                    )
                
                event = TaskForceEvent(
                    turn=self.current_turn,
                    event_type='created',
                    location="A1",  # Most taskforces start at entry hex
                    details=f"Created with {composition} targeting {target_name} at {target_location}",
                    raw_line=line_stripped
                )
                self.taskforces[self.current_player][tf_id].add_event(event)
                continue
            
            # Parse taskforce movement
            movement_info = self.parse_tf_movement(line_stripped)
            if movement_info:
                tf_id, from_loc, to_loc = movement_info
                
                # Create taskforce if it doesn't exist (defensive programming)
                if self.current_player not in self.taskforces or tf_id not in self.taskforces[self.current_player]:
                    if self.current_player not in self.taskforces:
                        self.taskforces[self.current_player] = {}
                    self.taskforces[self.current_player][tf_id] = TaskForce(
                        tf_id=tf_id,
                        player_name=self.current_player,
                        current_location=from_loc
                    )
                
                event = TaskForceEvent(
                    turn=self.current_turn,
                    event_type='moved',
                    location=to_loc,
                    details=f"Advanced from {from_loc} to {to_loc}",
                    raw_line=line_stripped
                )
                self.taskforces[self.current_player][tf_id].add_event(event)
                continue
                
            # Parse taskforce destination reached events
            destination_info = self.parse_tf_destination_reached(line_stripped)
            if destination_info:
                tf_id, location, details = destination_info
                
                # Create taskforce if it doesn't exist (defensive programming)
                if self.current_player not in self.taskforces or tf_id not in self.taskforces[self.current_player]:
                    if self.current_player not in self.taskforces:
                        self.taskforces[self.current_player] = {}
                    self.taskforces[self.current_player][tf_id] = TaskForce(
                        tf_id=tf_id,
                        player_name=self.current_player
                    )
                
                event = TaskForceEvent(
                    turn=self.current_turn,
                    event_type='arrived',
                    location=self.taskforces[self.current_player][tf_id].current_location or "Unknown",
                    details=details,
                    raw_line=line_stripped
                )
                self.taskforces[self.current_player][tf_id].add_event(event)
                continue
            
            # Parse taskforce status
            status_info = self.parse_tf_status(line_stripped)
            if status_info:
                tf_id, location, status_type = status_info
                current_tf_being_processed = tf_id
                current_tf_ship_composition = None
                current_tf_declared_path = None
                
                # Create taskforce if it doesn't exist
                if self.current_player not in self.taskforces:
                    self.taskforces[self.current_player] = {}
                if tf_id not in self.taskforces[self.current_player]:
                    self.taskforces[self.current_player][tf_id] = TaskForce(
                        tf_id=tf_id,
                        player_name=self.current_player,
                        current_location=location
                    )
                
                # Look ahead for ship composition and declared path
                ship_details = ""
                path_details = ""
                for i in range(1, min(5, len(lines) - line_num)):  # Look ahead up to 4 lines
                    next_line = lines[line_num + i].strip()
                    
                    # Check for ship composition
                    if not current_tf_ship_composition:
                        ship_comp = self.parse_ship_composition(next_line)
                        if ship_comp:
                            ship_details = f"Ships: {ship_comp}"
                            current_tf_ship_composition = ship_comp
                            
                            # Update taskforce composition if not set
                            tf = self.taskforces[self.current_player][tf_id]
                            if not tf.initial_composition and ship_comp:
                                tf.initial_composition = ship_comp
                    
                    # Check for declared path
                    if not current_tf_declared_path:
                        declared_path = self.parse_declared_path(next_line)
                        if declared_path:
                            path_details = f"Path: {declared_path}"
                            current_tf_declared_path = declared_path
                    
                    # Stop if we hit another TF or phase boundary
                    if ('🚀 TF' in next_line or 'PHASE' in next_line or '====' in next_line):
                        break
                
                # Build detailed status message
                details_parts = [f"At {location}"]
                if ship_details:
                    details_parts.append(ship_details)
                if path_details:
                    details_parts.append(path_details)
                
                # Always record status to track every turn's position
                tf = self.taskforces[self.current_player][tf_id]
                event = TaskForceEvent(
                    turn=self.current_turn,
                    event_type='status_update',
                    location=location,
                    details=" - ".join(details_parts),
                    raw_line=line_stripped
                )
                tf.add_event(event)
                continue
            
            # Check for ship composition or declared path lines following status (fallback handling)
            ship_comp = self.parse_ship_composition(line_stripped)
            declared_path = self.parse_declared_path(line_stripped)
            
            if (ship_comp or declared_path) and current_tf_being_processed:
                # Update the most recent status event with additional details
                tf = self.taskforces[self.current_player][current_tf_being_processed]
                if tf.events and tf.events[-1].event_type == 'status_update':
                    last_event = tf.events[-1]
                    if ship_comp and "Ships:" not in last_event.details:
                        last_event.details += f" - Ships: {ship_comp}"
                    if declared_path and "Path:" not in last_event.details:
                        last_event.details += f" - Path: {declared_path}"
                continue
            
            # Parse exploration events
            exploration_info = self.parse_exploration(line_stripped)
            if exploration_info:
                tf_id, location, details = exploration_info
                if self.current_player in self.taskforces and tf_id in self.taskforces[self.current_player]:
                    event = TaskForceEvent(
                        turn=self.current_turn,
                        event_type='exploration',
                        location=location,
                        details=details,
                        raw_line=line_stripped
                    )
                    self.taskforces[self.current_player][tf_id].add_event(event)
                continue
            
            # Parse combat events
            combat_info = self.parse_combat(line_stripped)
            if combat_info:
                tf_id, details = combat_info
                if self.current_player in self.taskforces and tf_id in self.taskforces[self.current_player]:
                    event = TaskForceEvent(
                        turn=self.current_turn,
                        event_type='combat',
                        location=self.taskforces[self.current_player][tf_id].current_location,
                        details=details,
                        raw_line=line_stripped
                    )
                    self.taskforces[self.current_player][tf_id].add_event(event)
                continue
            
            # Reset current TF processing on phase boundaries or non-related lines
            if ('PHASE' in line_stripped or '====' in line_stripped or 
                '----' in line_stripped or not line_stripped):
                current_tf_being_processed = None
                current_tf_ship_composition = None
                current_tf_declared_path = None
    
    def normalize_player_name(self, player_name: str) -> str:
        """Convert player name to safe filename format."""
        safe_name = re.sub(r'[^\w\s-]', '', player_name.lower())
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        return safe_name
    
    def generate_audit_report(self, output_dir: str, input_filename: str):
        """Generate audit reports for all players."""
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        base_name = Path(input_filename).stem
        created_files = []
        
        for player_name, player_taskforces in self.taskforces.items():
            if not player_taskforces:
                continue
                
            safe_name = self.normalize_player_name(player_name)
            audit_file = os.path.join(output_dir, f"{base_name}_{safe_name}_audit_taskforce.txt")
            created_files.append(audit_file)
            
            print(f"📋 Writing taskforce audit for {player_name} to {audit_file}")
            
            with open(audit_file, 'w', encoding='utf-8') as f:
                # Write header
                f.write("=" * 80 + "\n")
                f.write(f"  {player_name.upper()}'S TASKFORCE MOVEMENT AUDIT\n")
                f.write(f"  Generated from: {os.path.basename(input_filename)}\n")
                f.write("=" * 80 + "\n\n")
                
                # Write summary
                f.write("📊 TASKFORCE SUMMARY\n")
                f.write("-" * 40 + "\n")
                f.write(f"Player: {player_name}\n")
                f.write(f"Total Taskforces: {len(player_taskforces)}\n")
                
                # List all taskforces with basic info
                for tf_id in sorted(player_taskforces.keys()):
                    tf = player_taskforces[tf_id]
                    event_count = len(tf.events)
                    status = tf.status
                    if tf.events:
                        last_location = tf.current_location or "Unknown"
                        created_turn = tf.created_turn or "Unknown"
                        f.write(f"  TF{tf_id}: Created Turn {created_turn}, {event_count} events, last at {last_location}\n")
                    else:
                        f.write(f"  TF{tf_id}: No recorded events\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("  DETAILED TASKFORCE HISTORIES\n")
                f.write("=" * 80 + "\n\n")
                
                # Write detailed history for each taskforce
                for tf_id in sorted(player_taskforces.keys()):
                    tf = player_taskforces[tf_id]
                    
                    f.write(f"{'╔' + '═' * 78 + '╗'}\n")
                    f.write(f"║ TASKFORCE {tf_id:<68} ║\n")
                    f.write(f"{'╚' + '═' * 78 + '╝'}\n\n")
                    
                    # Basic info
                    if tf.initial_composition:
                        f.write(f"Initial Composition: {tf.initial_composition}\n")
                    if tf.target_name:
                        f.write(f"Primary Target: {tf.target_name} at {tf.target_destination}\n")
                    if tf.created_turn:
                        f.write(f"Created: Turn {tf.created_turn}\n")
                    f.write(f"Status: {tf.status}\n")
                    f.write(f"Total Events: {len(tf.events)}\n\n")
                    
                    if not tf.events:
                        f.write("⚠️  No events recorded for this taskforce\n\n")
                        continue
                    
                    # Event history - show ALL turns (1-44) with status
                    f.write("COMPLETE MOVEMENT HISTORY (ALL TURNS):\n")
                    f.write("-" * 60 + "\n")
                    
                    # Create a turn-by-turn view
                    turn_events = {}
                    for event in tf.events:
                        if event.turn not in turn_events:
                            turn_events[event.turn] = []
                        turn_events[event.turn].append(event)
                    
                    # Sort events within each turn by type priority
                    def event_priority(event):
                        priorities = {'created': 1, 'status_update': 2, 'moved': 3, 'arrived': 4, 'exploration': 5, 'combat': 6}
                        return priorities.get(event.event_type, 7)
                    
                    for turn in sorted(turn_events.keys()):
                        turn_events[turn].sort(key=event_priority)
                    
                    # Show events for all recorded turns
                    for turn in sorted(turn_events.keys()):
                        f.write(f"\nTurn {turn:2d}:\n")
                        
                        for event in turn_events[turn]:
                            # Format event based on type
                            if event.event_type == 'created':
                                f.write(f"   🏗️  CREATED - {event.details}\n")
                            elif event.event_type == 'moved':
                                f.write(f"   🚀 MOVED - {event.details}\n")
                            elif event.event_type == 'arrived':
                                f.write(f"   🏁 ARRIVED - {event.details}\n")
                            elif event.event_type == 'exploration':
                                f.write(f"   🔍 EXPLORATION - {event.details}\n")
                            elif event.event_type == 'combat':
                                f.write(f"   ⚔️  COMBAT - {event.details}\n")
                            elif event.event_type == 'status_update':
                                # Only show status if it's the only event or includes ship details
                                if len(turn_events[turn]) == 1 or "Ships:" in event.details:
                                    f.write(f"   📍 POSITION - {event.details}\n")
                            else:
                                f.write(f"   📝 {event.event_type.upper()} - {event.details}\n")
                    
                    # Show summary of missing turns if any
                    all_turns = set(range(1, 45))  # Turns 1-44
                    recorded_turns = set(turn_events.keys())
                    missing_turns = all_turns - recorded_turns
                    
                    if missing_turns:
                        f.write(f"\n⚠️  No activity recorded for turns: {', '.join(map(str, sorted(missing_turns)))}\n")
                    
                    f.write("\n" + "─" * 80 + "\n\n")
        
        return created_files
    
    def get_statistics(self) -> Dict[str, any]:
        """Get statistics about parsed taskforces."""
        stats = {
            'total_players': len(self.taskforces),
            'player_stats': {}
        }
        
        for player_name, player_taskforces in self.taskforces.items():
            player_stats = {
                'total_taskforces': len(player_taskforces),
                'total_events': sum(len(tf.events) for tf in player_taskforces.values()),
                'active_taskforces': sum(1 for tf in player_taskforces.values() if tf.status == 'active'),
                'taskforce_types': {}
            }
            
            # Analyze taskforce compositions
            for tf in player_taskforces.values():
                composition = tf.initial_composition.lower() if tf.initial_composition else 'unknown'
                if 'scout' in composition and 'corvette' in composition:
                    tf_type = 'mixed_exploration'
                elif 'scout' in composition:
                    tf_type = 'pure_scout'
                elif 'colony' in composition:
                    tf_type = 'colonization'
                elif 'corvette' in composition or 'fighter' in composition:
                    tf_type = 'military'
                else:
                    tf_type = 'other'
                
                player_stats['taskforce_types'][tf_type] = player_stats['taskforce_types'].get(tf_type, 0) + 1
            
            stats['player_stats'][player_name] = player_stats
        
        return stats


def find_output_files() -> List[str]:
    """Find available output files."""
    patterns = ["output/output_stats*.txt", "output_stats*.txt", "output/*.txt"]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    return sorted(list(set(files)))


def show_help():
    """Show help information."""
    print("""
🚀 Stellar Conquest Taskforce Movement Audit
============================================

Creates detailed movement audit logs for each player's taskforces,
tracking their activities turn by turn for audit purposes.

USAGE:
    python3 audit_taskforce.py <input_file> [output_directory]
    python3 audit_taskforce.py --help
    python3 audit_taskforce.py --list

ARGUMENTS:
    input_file         Path to the output file to analyze
    output_directory   Directory for audit files (default: audit_taskforce)

OPTIONS:
    --help, -h        Show this help message
    --list, -l        List available output files

EXAMPLES:
    python3 audit_taskforce.py output/output_stats28.txt
    python3 audit_taskforce.py output/output_stats28.txt my_audits/

OUTPUT FILES:
    Creates detailed audit files for each player:
    - output_stats28_admiral_nova_audit_taskforce.txt
    - output_stats28_general_vega_audit_taskforce.txt
    - etc.

AUDIT CONTENTS:
    For each player's taskforces:
    • Creation details (composition, target, turn)
    • Turn-by-turn movement history
    • Exploration activities
    • Combat involvement
    • Current status and location

FEATURES:
    • Complete taskforce lifecycle tracking
    • Movement validation and audit trail
    • Event categorization and organization
    • Statistical summaries per player
    • Chronological event ordering
""")


def list_available_files():
    """List available output files."""
    print("🚀 Stellar Conquest Taskforce Audit")
    print("===================================\n")
    
    files = find_output_files()
    
    if not files:
        print("❌ No output files found.")
        return
    
    print(f"📁 Found {len(files)} output files:\n")
    for i, file in enumerate(files, 1):
        try:
            size = os.path.getsize(file)
            size_str = f"({size:,} bytes)"
        except:
            size_str = "(size unknown)"
        
        print(f"  {i:2d}. {file} {size_str}")
    
    print(f"\nUSAGE:")
    print(f"  python3 audit_taskforce.py <filename>")


def main():
    """Main function."""
    
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ['--help', '-h']):
        show_help()
        return
    
    if len(sys.argv) == 2 and sys.argv[1] in ['--list', '-l']:
        list_available_files()
        return
    
    if len(sys.argv) < 2:
        print("❌ Error: Input file required.")
        print("Use --help for usage information.")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "audit_taskforce"
    
    try:
        print("🚀 Stellar Conquest Taskforce Movement Audit")
        print("=" * 50)
        
        if not os.path.exists(input_file):
            print(f"❌ Error: Input file '{input_file}' not found.")
            files = find_output_files()
            if files:
                print(f"\n💡 Available files:")
                for file in files[:5]:
                    print(f"   - {file}")
            sys.exit(1)
        
        # Create auditor and parse file
        auditor = TaskForceAuditor()
        auditor.parse_file(input_file)
        
        if not auditor.taskforces:
            print("❌ No taskforce data found in the input file!")
            sys.exit(1)
        
        # Show statistics
        stats = auditor.get_statistics()
        print(f"\n📊 Parsing Results:")
        print(f"   Players analyzed: {stats['total_players']}")
        for player, player_stats in stats['player_stats'].items():
            print(f"   - {player}: {player_stats['total_taskforces']} taskforces, {player_stats['total_events']} total events")
        
        # Generate audit reports
        print(f"\n📋 Generating audit reports...")
        created_files = auditor.generate_audit_report(output_dir, input_file)
        
        print(f"\n✅ Created {len(created_files)} audit files in {output_dir}/")
        print(f"\n📋 Generated files:")
        for file in created_files:
            print(f"   - {os.path.basename(file)}")
        
        print(f"\n💡 Review commands:")
        print(f"   ls {output_dir}/                    # List audit files")
        print(f"   less {output_dir}/*audit.txt        # Browse audit reports")
        print(f"   grep 'MOVED' {output_dir}/*audit.txt    # Find all movements")
        print(f"   grep 'TF.*CREATED' {output_dir}/*audit.txt  # Find taskforce creations")
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()