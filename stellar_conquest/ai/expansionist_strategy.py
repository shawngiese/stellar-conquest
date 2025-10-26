"""Expansionist AI strategy focused on rapid colonization and growth."""

from typing import List, Dict, Any
from dataclasses import dataclass

from .base_strategy import BaseStrategy, StrategyWeights, GamePhase, Priority
from ..game.game_state import GameState
from ..entities.player import Player, Technology
from ..entities.ship import ShipType
from ..actions.base_action import BaseAction
from ..actions.movement_action import MovementAction, MovementOrder
from ..actions.exploration_action import ExplorationAction
from ..actions.colonization_action import ColonizationAction


class ExpansionistStrategy(BaseStrategy):
    """AI strategy focused on rapid expansion and colonization."""
    
    def __init__(self):
        weights = StrategyWeights(
            exploration=1.5,    # High exploration to find colonies
            colonization=2.0,   # Highest priority on colonization
            military=0.7,       # Lower military until threatened
            research=1.2,       # Focus on economic/expansion tech
            economy=1.3         # Strong economic focus
        )
        super().__init__("Expansionist", weights)
    
    def decide_turn_actions(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Decide actions prioritizing exploration and colonization."""
        actions = []
        game_phase = self.get_game_phase(game_state)
        
        # Phase-specific action priorities
        if game_phase == GamePhase.EARLY_EXPLORATION:
            actions.extend(self._early_exploration_actions(player, game_state))
        elif game_phase == GamePhase.MID_EXPANSION:
            actions.extend(self._mid_expansion_actions(player, game_state))
        else:  # LATE_MILITARY
            actions.extend(self._late_military_actions(player, game_state))
        
        return actions
    
    def _early_exploration_actions(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Actions for early game: aggressive exploration and initial colonization."""
        actions = []
        
        # 1. Split oversized scout task forces first
        scout_splitting_actions = self.split_oversized_scout_task_forces(player, game_state)
        actions.extend(scout_splitting_actions)
        
        # 2. Spread scouts for maximum exploration
        scout_exploration = self._plan_scout_exploration(player, game_state)
        if scout_exploration:
            actions.append(scout_exploration)
        
        # 3. Move colony transports toward promising systems
        colonization_moves = self._plan_colonization_movements(player, game_state)
        actions.extend(colonization_moves)
        
        # 4. Explore reachable star systems
        exploration_targets = self.evaluate_exploration_targets(player, game_state)[:3]  # Top 3
        if exploration_targets:
            targets = [target[0] for target in exploration_targets]
            actions.append(ExplorationAction(player.player_id, targets))
        
        # 5. Colonize best available planets
        colonization_action = self._plan_colonization(player, game_state)
        if colonization_action:
            actions.append(colonization_action)
        
        return actions
    
    def _mid_expansion_actions(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Actions for mid-game: continued expansion with some defense."""
        actions = []
        
        # 1. Split oversized scout task forces for continued exploration
        scout_splitting_actions = self.split_oversized_scout_task_forces(player, game_state)
        actions.extend(scout_splitting_actions)
        
        # 2. Continue exploration but more selective
        exploration_targets = self.evaluate_exploration_targets(player, game_state)[:2]
        if exploration_targets:
            targets = [target[0] for target in exploration_targets]
            actions.append(ExplorationAction(player.player_id, targets))
        
        # 3. Aggressive colonization of remaining good planets
        colonization_action = self._plan_colonization(player, game_state)
        if colonization_action:
            actions.append(colonization_action)
        
        # 4. Start building some military for defense
        defensive_moves = self._plan_defensive_positioning(player, game_state)
        actions.extend(defensive_moves)
        
        return actions
    
    def _late_military_actions(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Actions for late game: defend colonies, opportunistic expansion, victory point control."""
        actions = []
        
        # Priority 1: Split oversized scout task forces for victory point positioning
        scout_splitting_actions = self.split_oversized_scout_task_forces(player, game_state)
        actions.extend(scout_splitting_actions)
        
        # Priority 2: Defend valuable colonies under threat
        defensive_actions = self._plan_enhanced_colony_defense(player, game_state)
        actions.extend(defensive_actions)
        
        # Priority 3: Review security log and plan colony attacks
        colony_attack_actions = self._plan_colony_attacks(player, game_state)
        actions.extend(colony_attack_actions)
        
        # Priority 4: Position scouts for victory point control (Rule C)
        victory_point_actions = self._plan_victory_point_control(player, game_state)
        actions.extend(victory_point_actions)
        
        # Priority 5: Continue limited exploration for strategic advantage
        exploration_targets = self.evaluate_exploration_targets(player, game_state)[:1]
        if exploration_targets:
            targets = [target[0] for target in exploration_targets]
            actions.append(ExplorationAction(player.player_id, targets))
        
        return actions
    
    def _plan_scout_exploration(self, player: Player, game_state: GameState) -> MovementAction:
        """Plan scout movements for maximum exploration coverage."""
        scout_orders = []
        
        # Find scouts and send them to different unexplored systems
        for ship_group in player.ship_groups:
            scouts = [ship for ship in ship_group.ships if ship.ship_type.value == "scout" and ship.count > 0]
            if scouts:
                # Find best unexplored target for scout distribution
                exploration_targets = self.evaluate_exploration_targets(player, game_state)
                
                for scout_ship in scouts:
                    scouts_available = scout_ship.count
                    location = ship_group.location
                    
                    # Only use existing scouts for exploration (splitting handled separately)
                    # Send small groups to maximize exploration coverage
                    if scouts_available > 0 and exploration_targets:
                        # Determine how many to send based on available targets
                        available_targets = min(len(exploration_targets), scouts_available)
                        scouts_per_target = max(1, scouts_available // max(1, available_targets))
                        
                        targets_used = 0
                        for target_location, _ in exploration_targets:
                            if targets_used >= available_targets or scouts_available <= 0:
                                break
                                
                            scouts_to_send = min(scouts_per_target, scouts_available)
                            if scouts_to_send > 0:
                                scout_orders.append(MovementOrder(
                                    location, ShipType.SCOUT, scouts_to_send, target_location
                                ))
                                scouts_available -= scouts_to_send
                                targets_used += 1
        
        return MovementAction(player.player_id, scout_orders) if scout_orders else None
    
    def _plan_colonization_movements(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Move colony transports toward promising colonization targets."""
        actions = []
        
        # Identify best colonization targets
        colonization_targets = self.evaluate_colonization_targets(player, game_state)[:3]
        
        if not colonization_targets:
            return actions
        
        # Move colony transports toward these targets
        transport_orders = []
        
        for fleet in player.fleets:
            transports = fleet.get_ships_by_type(ShipType.COLONY_TRANSPORT)
            if transports and colonization_targets:
                # Move transports toward best target
                target_location = colonization_targets[0][0]
                transport_count = sum(t.count for t in transports)
                
                transport_orders.append(MovementOrder(
                    fleet.location, ShipType.COLONY_TRANSPORT, 
                    min(5, transport_count), target_location
                ))
        
        if transport_orders:
            actions.append(MovementAction(player.player_id, transport_orders))
        
        return actions
    
    def _plan_colonization(self, player: Player, game_state: GameState) -> ColonizationAction:
        """Plan colonization of available planets."""
        # This would be implemented with a ColonizationAction class
        # For now, return None as placeholder
        return None
    
    def _plan_defensive_positioning(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Position military ships to defend key colonies."""
        actions = []
        
        # Identify most valuable colonies that need protection
        vulnerable_colonies = self._identify_vulnerable_colonies(player, game_state)
        
        # Move available warships to defend them
        for colony_location in vulnerable_colonies[:2]:  # Top 2 most vulnerable
            defensive_orders = self._create_defensive_orders(colony_location, player, game_state)
            if defensive_orders:
                actions.append(MovementAction(player.player_id, defensive_orders))
        
        return actions
    
    def _plan_colony_defense(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Plan comprehensive colony defense for late game."""
        # Similar to defensive positioning but more comprehensive
        return []
    
    def _plan_opportunistic_attacks(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Look for weak enemy positions to attack."""
        actions = []
        
        # Find enemy colonies that are weakly defended
        military_targets = self.evaluate_military_targets(player, game_state)
        
        for target_location, score in military_targets[:1]:  # Only take best opportunity
            if score > 2.0:  # Only if favorable odds
                attack_orders = self._create_attack_orders(target_location, player, game_state)
                if attack_orders:
                    actions.append(MovementAction(player.player_id, attack_orders))
        
        return actions
    
    def decide_production_spending(self, player: Player, game_state: GameState, 
                                 available_ip: int) -> Dict[str, int]:
        """Decide production spending with expansionist priorities."""
        spending = {}
        remaining_ip = available_ip
        game_phase = self.get_game_phase(game_state)
        
        # Expansionist priorities:
        # 1. Colony transports for expansion
        # 2. Scouts for exploration  
        # 3. Factories for economic growth
        # 4. Speed research for faster expansion
        # 5. Military only when necessary
        
        if game_phase == GamePhase.EARLY_EXPLORATION:
            # Early game: maximize exploration and colonization capability
            
            # Colony transports (high priority)
            transport_need = self._calculate_transport_need(player, game_state)
            transport_cost = min(transport_need, remaining_ip)
            spending["colony_transports"] = transport_cost
            remaining_ip -= transport_cost
            
            # Scouts for exploration
            scout_cost = min(6, remaining_ip)  # 2 scouts at 3 IP each
            spending["scouts"] = scout_cost
            remaining_ip -= scout_cost
            
            # Speed research for faster expansion
            if remaining_ip >= 15 and Technology.SPEED_3_HEX not in player.completed_technologies:
                spending["research_speed_3"] = 15
                remaining_ip -= 15
            
        elif game_phase == GamePhase.MID_EXPANSION:
            # Mid game: balance expansion with economic development
            
            # Factories for economic growth
            factory_investment = min(remaining_ip // 2, 20)
            spending["factories"] = factory_investment  
            remaining_ip -= factory_investment
            
            # More colony transports
            transport_cost = min(remaining_ip // 3, 10)
            spending["colony_transports"] = transport_cost
            remaining_ip -= transport_cost
            
            # Some military for defense
            if remaining_ip >= 8:
                spending["corvettes"] = 8  # 1 corvette
                remaining_ip -= 8
            
        else:  # LATE_MILITARY
            # Late game: prepare for final military push while maintaining economy
            
            # Assess colony defense needs for production prioritization
            defense_needs = self.evaluate_colony_defense_needs(player, game_state)
            high_threat_colonies = len([d for d in defense_needs if d[1]['threat_level'] >= 3])
            
            # Adjust military budget based on threat level
            base_military_budget = remaining_ip // 2
            if high_threat_colonies > 0:
                # Increase military budget when under threat
                military_budget = min(remaining_ip * 2 // 3, base_military_budget + (high_threat_colonies * 10))
            else:
                military_budget = base_military_budget
            
            # Military buildup - prioritize based on what's available and effective
            if player.can_build_ship_type(ShipType.FIGHTER):
                fighter_count = military_budget // 20
                spending["fighters"] = fighter_count * 20
                remaining_ip -= fighter_count * 20
            else:
                corvette_count = military_budget // 8
                spending["corvettes"] = corvette_count * 8
                remaining_ip -= corvette_count * 8
            
            # Build missile bases for threatened colonies
            if high_threat_colonies > 0 and player.can_build_ship_type(ShipType.CORVETTE):
                missile_base_budget = min(remaining_ip // 3, high_threat_colonies * 4)  # 4 IP per missile base
                spending["missile_bases"] = missile_base_budget
                remaining_ip -= missile_base_budget
            
            # Continue factory building (but less if under threat)
            factory_budget = min(remaining_ip, 12 if high_threat_colonies == 0 else 8)
            spending["factories"] = factory_budget
            remaining_ip -= factory_budget
        
        # Invest any remaining IP in research
        if remaining_ip > 0:
            spending["research_misc"] = remaining_ip
        
        self.log_decision("production_spending", {
            "game_phase": game_phase.value,
            "total_ip": available_ip,
            "spending": spending
        })
        
        return spending
    
    def _calculate_transport_need(self, player: Player, game_state: GameState) -> int:
        """Calculate how many colony transports are needed."""
        # Count available transports
        current_transports = 0
        for fleet in player.fleets:
            current_transports += sum(
                s.count for s in fleet.ships if s.ship_type == ShipType.COLONY_TRANSPORT
            )
        
        # Estimate need based on colonies and population
        total_population = sum(c.population for c in player.colonies)
        
        # Want enough transports to move about 10% of population
        desired_transports = max(5, total_population // 10)
        
        return max(0, desired_transports - current_transports)
    
    def _identify_vulnerable_colonies(self, player: Player, game_state: GameState) -> List[str]:
        """Identify colonies that are most vulnerable to attack."""
        vulnerable = []
        
        for colony in player.colonies:
            # Check for nearby enemy presence
            colony_location = "placeholder"  # Would get actual location
            enemy_threat = self._assess_enemy_threat_to_location(colony_location, player, game_state)
            
            if enemy_threat > 0:
                vulnerable.append(colony_location)
        
        return vulnerable
    
    def _assess_enemy_threat_to_location(self, location: str, player: Player, game_state: GameState) -> float:
        """Assess enemy military threat to a specific location."""
        threat_level = 0.0
        
        # Check adjacent hexes for enemy fleets
        adjacent_hexes = game_state.galaxy.get_adjacent_hexes(location)
        
        for hex_coord in adjacent_hexes:
            enemy_strength = self._assess_enemy_strength(hex_coord, player, game_state)
            threat_level += enemy_strength.get("total_strength", 0) * 0.5  # Adjacent threat discount
        
        # Check same hex
        direct_threat = self._assess_enemy_strength(location, player, game_state)
        threat_level += direct_threat.get("total_strength", 0)
        
        return threat_level
    
    def _create_defensive_orders(self, location: str, player: Player, game_state: GameState) -> List[MovementOrder]:
        """Create movement orders to defend a location."""
        orders = []
        
        # Find available warships and move them to defend
        for fleet in player.fleets:
            warships = fleet.get_warships()
            if warships and fleet.location != location:
                # Move some warships to defend
                for ship_group in warships[:1]:  # Move first available warship group
                    orders.append(MovementOrder(
                        fleet.location, ship_group.ship_type, 
                        min(2, ship_group.count), location
                    ))
                    break
        
        return orders
    
    def _create_attack_orders(self, target_location: str, player: Player, game_state: GameState) -> List[MovementOrder]:
        """Create movement orders to attack a target."""
        orders = []
        
        # Gather available military forces for attack
        available_warships = []
        for fleet in player.fleets:
            warships = fleet.get_warships()
            available_warships.extend([(fleet.location, ship) for ship in warships])
        
        # Move sufficient force to attack
        if available_warships:
            source_location, ship_group = available_warships[0]
            attack_force = min(3, ship_group.count)  # Send moderate force
            
            orders.append(MovementOrder(
                source_location, ship_group.ship_type, 
                attack_force, target_location
            ))
        
        return orders
    
    def _plan_victory_point_control(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Position scouts and other ships to control systems for Rule C victory points."""
        actions = []
        
        # Evaluate systems that could give victory points via Rule C
        vp_targets = self.evaluate_victory_point_positions(player, game_state)[:10]  # Top 10 targets
        
        if not vp_targets:
            return actions
        
        # Distribute scouts (max 1 per system for VP control)
        scout_orders = []
        available_scouts = []
        
        # Collect available scouts from all ship groups, limiting groups to 5 scouts max
        for ship_group in player.ship_groups:
            scouts = [ship for ship in ship_group.ships if ship.ship_type.value == "scout" and ship.count > 0]
            if scouts:
                for scout_ship in scouts:
                    # If more than 5 scouts in one location, distribute them
                    scouts_here = scout_ship.count
                    location = ship_group.location
                    
                    # Keep max 5 scouts per task force, distribute the rest
                    if scouts_here > 5:
                        scouts_to_distribute = scouts_here - 5
                        available_scouts.extend([(location, scouts_to_distribute)])
                    
                    # Also consider scouts from groups with <= 5 for redeployment
                    elif scouts_here <= 5:
                        # Only redeploy if this location doesn't need VP control
                        location_needs_vp_control = any(target[0] == location for target in vp_targets)
                        if not location_needs_vp_control:
                            available_scouts.extend([(location, min(2, scouts_here))])  # Keep some scouts
        
        # Assign scouts to VP control targets
        scouts_assigned = 0
        for target_location, score in vp_targets:
            if scouts_assigned >= len(available_scouts):
                break
                
            # Check if we already have ships at target
            has_ships = player.get_ship_group_at_location(target_location) is not None
            if not has_ships and available_scouts:
                source_location, available_count = available_scouts[scouts_assigned]
                scouts_to_send = min(1, available_count)  # Send only 1 scout per VP target
                
                scout_orders.append(MovementOrder(
                    source_location, ShipType.SCOUT, scouts_to_send, target_location
                ))
                scouts_assigned += 1
        
        if scout_orders:
            actions.append(MovementAction(player.player_id, scout_orders))
            
            self.log_decision("victory_point_control", {
                "targets": [target[0] for target in vp_targets[:len(scout_orders)]],
                "scouts_deployed": len(scout_orders)
            })
        
        return actions
    
    def _plan_colony_attacks(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Review discovered enemy colonies and plan attacks according to 4.2 rules."""
        actions = []
        
        # Get all potential colony attack targets
        attack_targets = self.evaluate_colony_attack_targets(player, game_state)
        
        if not attack_targets:
            return actions
        
        # Log security review decision
        self.log_decision("security_review", {
            "targets_found": len(attack_targets),
            "top_targets": [target[1]['enemy_player'] + " at " + target[0] for target in attack_targets[:3]]
        })
        
        # Select best targets for attack (limit to 2 per turn to avoid overextension)
        for location, target_info in attack_targets[:2]:
            # Check if we have sufficient warships available
            available_warships = self._get_available_warships_for_attack(player, location, game_state)
            
            if available_warships:
                # Calculate required force based on target defenses
                defense_strength = target_info['defense_strength']
                required_warships = max(2, defense_strength + 1)  # Need superiority
                
                if len(available_warships) >= required_warships:
                    # Plan attack
                    attack_orders = self._create_colony_attack_orders(
                        location, target_info, available_warships[:required_warships], player, game_state
                    )
                    
                    if attack_orders:
                        actions.append(MovementAction(player.player_id, attack_orders))
                        
                        self.log_decision("colony_attack_planned", {
                            "target": target_info['enemy_player'] + " colony at " + location,
                            "target_value": target_info['value_score'],
                            "defense_strength": defense_strength,
                            "warships_sent": len(attack_orders),
                            "colony_details": f"{target_info['population']}M pop, {target_info['factories']} factories"
                        })
        
        return actions
    
    def _plan_enhanced_colony_defense(self, player: Player, game_state: GameState) -> List[BaseAction]:
        """Plan colony defense based on threat assessment and colony value."""
        actions = []
        
        # Get colonies that need defense
        defense_needs = self.evaluate_colony_defense_needs(player, game_state)
        
        if not defense_needs:
            return actions
        
        # Prioritize defense for most valuable/threatened colonies
        for location, defense_info in defense_needs[:3]:  # Top 3 threatened colonies
            if defense_info['needs_warships'] and not defense_info['has_warships']:
                # Send warships to defend
                defensive_orders = self._create_enhanced_defensive_orders(location, defense_info, player, game_state)
                if defensive_orders:
                    actions.append(MovementAction(player.player_id, defensive_orders))
                    
                    self.log_decision("colony_defense_reinforcement", {
                        "location": location,
                        "threat_level": defense_info['threat_level'],
                        "colony_value": defense_info['colony_value'],
                        "warships_sent": len(defensive_orders),
                        "colony_details": f"{defense_info['population']}M pop, {defense_info['factories']} factories on {defense_info['planet_type']}"
                    })
        
        return actions

    def _get_available_warships_for_attack(self, player: Player, target_location: str, game_state: GameState) -> List[Tuple[str, Any]]:
        """Find available warships that can be used for colony attacks."""
        available_warships = []
        
        for ship_group in player.ship_groups:
            warships = [ship for ship in ship_group.ships if ship.is_warship and ship.count > 0]
            if warships:
                # Check if these warships are not critically needed for defense
                location = ship_group.location
                is_defending_critical_colony = self._is_location_critical_defense(location, player, game_state)
                
                if not is_defending_critical_colony:
                    for warship in warships:
                        # Keep some warships for local defense, send others for attack
                        available_for_attack = max(0, warship.count - 1)  # Keep at least 1 if possible
                        if available_for_attack > 0:
                            available_warships.append((location, warship))
        
        return available_warships

    def _create_colony_attack_orders(self, target_location: str, target_info: Dict, 
                                   available_warships: List, player: Player, 
                                   game_state: GameState) -> List[MovementOrder]:
        """Create movement orders for attacking an enemy colony."""
        orders = []
        
        for source_location, warship in available_warships:
            # Send appropriate force - more ships for better defended colonies
            ships_to_send = 1
            if target_info['defense_strength'] > 2:
                ships_to_send = 2
            if target_info['defense_strength'] > 5:
                ships_to_send = min(3, warship.count)
            
            orders.append(MovementOrder(
                source_location, warship.ship_type, 
                min(ships_to_send, warship.count), target_location
            ))
        
        return orders

    def _create_enhanced_defensive_orders(self, location: str, defense_info: Dict, 
                                        player: Player, game_state: GameState) -> List[MovementOrder]:
        """Create movement orders to defend a threatened colony."""
        orders = []
        
        # Find nearest available warships
        available_warships = []
        from ..utils.hex_utils import calculate_hex_distance
        
        for ship_group in player.ship_groups:
            warships = [ship for ship in ship_group.ships if ship.is_warship and ship.count > 0]
            if warships and ship_group.location != location:
                distance = calculate_hex_distance(ship_group.location, location)
                for warship in warships:
                    available_warships.append((ship_group.location, warship, distance))
        
        # Sort by distance (closest first)
        available_warships.sort(key=lambda x: x[2])
        
        # Send appropriate number of warships based on threat
        warships_needed = 1
        if defense_info['threat_level'] >= 4:
            warships_needed = 3
        elif defense_info['threat_level'] >= 3:
            warships_needed = 2
        
        warships_sent = 0
        for source_location, warship, distance in available_warships:
            if warships_sent >= warships_needed:
                break
                
            ships_to_send = min(2, warship.count)  # Send up to 2 ships per group
            orders.append(MovementOrder(
                source_location, warship.ship_type, 
                ships_to_send, location
            ))
            warships_sent += ships_to_send
        
        return orders

    def _is_location_critical_defense(self, location: str, player: Player, game_state: GameState) -> bool:
        """Check if a location is critical for defense and shouldn't have warships moved away."""
        # Check if this location has a valuable colony
        colonies_here = player.get_colonies_at_location(location)
        if colonies_here:
            for colony in colonies_here:
                colony_value = self._get_colony_value(colony)
                if colony_value > 10:  # High value colony
                    return True
        
        # Check for immediate enemy threats
        for other_player in game_state.players:
            if other_player.player_id == player.player_id:
                continue
            
            enemy_ship_group = other_player.get_ship_group_at_location(location)
            if enemy_ship_group and enemy_ship_group.get_total_ships() > 0:
                return True  # Under immediate threat
        
        return False