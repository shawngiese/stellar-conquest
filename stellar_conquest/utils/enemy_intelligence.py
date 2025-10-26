#!/usr/bin/env python3
"""
Enemy Intelligence System for Stellar Conquest

This module implements enemy activity logging and star system monitoring
to provide strategic intelligence for warfare decisions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum

class ActivityType(Enum):
    """Types of enemy activities that can be logged."""
    ENEMY_COLONY_DISCOVERED = "enemy_colony_discovered"
    ENEMY_SHIPS_DISCOVERED = "enemy_ships_discovered"
    ENEMY_SHIPS_PASSING = "enemy_ships_passing"
    ENEMY_COLONY_ATTACKED = "enemy_colony_attacked"
    ENEMY_SHIPS_ENGAGED = "enemy_ships_engaged"
    DETAILED_COMBAT_REPORT = "detailed_combat_report"
    MOVEMENT_ENCOUNTER = "movement_encounter"
    RETREAT_RECORDED = "retreat_recorded"

@dataclass
class EnemyActivityEntry:
    """Single entry in the enemy activity log."""
    turn: int
    location: str
    activity_type: ActivityType
    enemy_player: str
    details: str
    threat_level: int = 1  # 1-5 scale
    verified: bool = True
    
    def __str__(self):
        return f"Turn {self.turn}: {self.details} at {self.location}"

@dataclass
class StarSystemMonitorEntry:
    """Single entry in the star system monitoring log."""
    turn: int
    location: str
    enemy_player: str
    ship_types: List[str]
    ship_count: int
    movement_direction: Optional[str] = None
    hostile_action: bool = False
    
    def __str__(self):
        ships_desc = f"{self.ship_count} ships ({', '.join(self.ship_types)})"
        action = " (HOSTILE)" if self.hostile_action else ""
        return f"Turn {self.turn}: {self.enemy_player} - {ships_desc} passed through {self.location}{action}"

class EnemyIntelligenceSystem:
    """Manages enemy activity logging and strategic intelligence for players."""
    
    def __init__(self):
        # Player-specific activity logs
        self.enemy_activity_logs: Dict[str, List[EnemyActivityEntry]] = {}
        self.star_monitoring_logs: Dict[str, List[StarSystemMonitorEntry]] = {}
        
        # Strategic target recommendations
        self.priority_targets: Dict[str, List[str]] = {}
        
    def initialize_player_logs(self, player_name: str):
        """Initialize logging for a new player."""
        self.enemy_activity_logs[player_name] = []
        self.star_monitoring_logs[player_name] = []
        self.priority_targets[player_name] = []
        
    def log_enemy_activity(self, observer_player: str, turn: int, location: str, 
                          activity_type: ActivityType, enemy_player: str, 
                          details: str, threat_level: int = 1):
        """Log enemy activity discovered by a player."""
        if observer_player not in self.enemy_activity_logs:
            self.initialize_player_logs(observer_player)
            
        entry = EnemyActivityEntry(
            turn=turn,
            location=location,
            activity_type=activity_type,
            enemy_player=enemy_player,
            details=details,
            threat_level=threat_level
        )
        
        self.enemy_activity_logs[observer_player].append(entry)
        
        # Update priority targets if it's a significant threat
        if threat_level >= 3:
            if location not in self.priority_targets[observer_player]:
                self.priority_targets[observer_player].append(location)
                
    def log_star_system_monitoring(self, observer_player: str, turn: int, 
                                 location: str, enemy_player: str, 
                                 ship_types: List[str], ship_count: int,
                                 movement_direction: str = None, hostile_action: bool = False):
        """Log enemy ships passing through player-controlled star systems."""
        if observer_player not in self.star_monitoring_logs:
            self.initialize_player_logs(observer_player)
            
        entry = StarSystemMonitorEntry(
            turn=turn,
            location=location,
            enemy_player=enemy_player,
            ship_types=ship_types,
            ship_count=ship_count,
            movement_direction=movement_direction,
            hostile_action=hostile_action
        )
        
        self.star_monitoring_logs[observer_player].append(entry)
        
        # If hostile action, mark location as priority target
        if hostile_action:
            if location not in self.priority_targets[observer_player]:
                self.priority_targets[observer_player].append(location)
    
    def get_enemy_activity_report(self, player_name: str, recent_turns: int = 5) -> str:
        """Generate enemy activity report for a player."""
        if player_name not in self.enemy_activity_logs:
            return f"📊 {player_name}'s Enemy Activity Log: No activity recorded"
            
        activities = self.enemy_activity_logs[player_name]
        if not activities:
            return f"📊 {player_name}'s Enemy Activity Log: No enemy activity detected"
            
        # Filter recent activities
        latest_turn = max(entry.turn for entry in activities)
        recent_activities = [entry for entry in activities 
                           if entry.turn >= (latest_turn - recent_turns + 1)]
        
        if not recent_activities:
            return f"📊 {player_name}'s Enemy Activity Log: No recent enemy activity"
            
        report = [f"\n📊 {player_name}'s Enemy Activity Log (Last {recent_turns} turns):"]
        
        # Group by enemy player
        by_enemy = {}
        for entry in recent_activities:
            if entry.enemy_player not in by_enemy:
                by_enemy[entry.enemy_player] = []
            by_enemy[entry.enemy_player].append(entry)
            
        for enemy, entries in by_enemy.items():
            report.append(f"\n   🎯 Intelligence on {enemy}:")
            for entry in sorted(entries, key=lambda x: x.turn):
                threat_indicator = "🔥" * entry.threat_level
                report.append(f"     Turn {entry.turn}: {entry.details} at {entry.location} {threat_indicator}")
                
        return "\n".join(report)
    
    def get_star_monitoring_report(self, player_name: str, recent_turns: int = 5) -> str:
        """Generate star system monitoring report for a player."""
        if player_name not in self.star_monitoring_logs:
            return f"🛡️ {player_name}'s Star System Security: No monitoring data"
            
        monitors = self.star_monitoring_logs[player_name]
        if not monitors:
            return f"🛡️ {player_name}'s Star System Security: No enemy incursions detected"
            
        # Filter recent monitoring
        latest_turn = max(entry.turn for entry in monitors)
        recent_monitors = [entry for entry in monitors 
                          if entry.turn >= (latest_turn - recent_turns + 1)]
        
        if not recent_monitors:
            return f"🛡️ {player_name}'s Star System Security: No recent incursions"
            
        report = [f"\n🛡️ {player_name}'s Star System Security Log (Last {recent_turns} turns):"]
        
        # Group by location
        by_location = {}
        for entry in recent_monitors:
            if entry.location not in by_location:
                by_location[entry.location] = []
            by_location[entry.location].append(entry)
            
        for location, entries in by_location.items():
            report.append(f"\n   📍 {location} Activity:")
            for entry in sorted(entries, key=lambda x: x.turn):
                hostile_marker = " ⚠️ HOSTILE" if entry.hostile_action else ""
                report.append(f"     {entry}{hostile_marker}")
                
        return "\n".join(report)
    
    def get_priority_targets(self, player_name: str) -> List[str]:
        """Get list of priority target locations for strategic planning."""
        if player_name not in self.priority_targets:
            return []
        return list(self.priority_targets[player_name])
    
    def get_strategic_recommendations(self, player_name: str) -> str:
        """Generate strategic recommendations based on intelligence."""
        if player_name not in self.enemy_activity_logs:
            return f"🎯 {player_name}'s Strategic Intelligence: No data available"
            
        activities = self.enemy_activity_logs[player_name]
        monitors = self.star_monitoring_logs.get(player_name, [])
        priorities = self.priority_targets.get(player_name, [])
        
        if not activities and not monitors:
            return f"🎯 {player_name}'s Strategic Intelligence: Galaxy appears peaceful"
            
        report = [f"\n🎯 {player_name}'s Strategic Intelligence Summary:"]
        
        if priorities:
            report.append(f"\n   🚨 Priority Targets for Military Action:")
            for target in priorities[:5]:  # Top 5 priorities
                threat_count = len([a for a in activities if a.location == target and a.threat_level >= 3])
                report.append(f"     • {target} - Threat Level: {threat_count}")
        
        # Count enemy presence by player
        enemy_presence = {}
        for entry in activities:
            enemy_presence[entry.enemy_player] = enemy_presence.get(entry.enemy_player, 0) + 1
            
        if enemy_presence:
            report.append(f"\n   📊 Enemy Activity Summary:")
            for enemy, count in sorted(enemy_presence.items(), key=lambda x: x[1], reverse=True):
                report.append(f"     • {enemy}: {count} recorded activities")
                
        return "\n".join(report)

# Global intelligence system instance
intelligence_system = EnemyIntelligenceSystem()