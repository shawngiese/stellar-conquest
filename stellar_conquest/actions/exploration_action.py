"""Star exploration actions."""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import random

from .base_action import BaseAction, ActionResult, ActionOutcome
from ..game.game_state import GameState
from ..entities.ship import ShipType
from ..entities.colony import Planet, PlanetType


@dataclass
class ExplorationResult:
    """Result of exploring a star system."""
    location: str
    star_card_drawn: Optional[int] = None
    planets_discovered: List[Planet] = None
    colonies_revealed: List[Dict] = None
    ships_revealed: List[Dict] = None
    exploration_losses: List[Dict] = None  # Ships lost to exploration risks


class ExplorationAction(BaseAction):
    """Handle star exploration with risk resolution and discovery."""
    
    def __init__(self, player_id: int, exploration_targets: List[str]):
        super().__init__(player_id, "exploration")
        self.exploration_targets = exploration_targets  # Hex coordinates
        self.results: List[ExplorationResult] = []
    
    def validate(self, game_state: GameState) -> bool:
        """Validate exploration targets."""
        player = game_state.players.get(self.player_id)
        if not player:
            return False
        
        for target in self.exploration_targets:
            # Must have ships at the target location
            fleet = player.get_fleet_at_location(target)
            if not fleet or fleet.total_ships == 0:
                return False
            
            # Target must be a star system
            star_system = game_state.galaxy.get_star_system(target)
            if not star_system:
                return False
        
        return True
    
    def execute(self, game_state: GameState) -> ActionOutcome:
        """Execute exploration for all targets."""
        if not self.validate(game_state):
            return ActionOutcome(ActionResult.INVALID, "Exploration validation failed")
        
        player = game_state.players[self.player_id]
        self.results = []
        
        for target in self.exploration_targets:
            result = self._explore_single_system(target, player, game_state)
            self.results.append(result)
        
        # Summarize results
        total_losses = sum(len(r.exploration_losses or []) for r in self.results)
        total_discoveries = sum(len(r.planets_discovered or []) for r in self.results)
        
        message = f"Explored {len(self.exploration_targets)} systems"
        if total_losses > 0:
            message += f", lost {total_losses} ships to exploration risks"
        if total_discoveries > 0:
            message += f", discovered {total_discoveries} planets"
        
        self.executed = True
        self.outcome = ActionOutcome(
            ActionResult.SUCCESS, message,
            {
                "systems_explored": len(self.exploration_targets),
                "ships_lost": total_losses,
                "planets_discovered": total_discoveries,
                "results": [self._serialize_result(r) for r in self.results]
            }
        )
        
        self.log_execution(game_state, self.outcome)
        return self.outcome
    
    def _explore_single_system(self, location: str, player, game_state: GameState) -> ExplorationResult:
        """Explore a single star system."""
        fleet = player.get_fleet_at_location(location)
        star_system = game_state.galaxy.get_star_system(location)
        
        result = ExplorationResult(location)
        
        # Step 1: Resolve exploration risks for unarmed ships
        result.exploration_losses = self._resolve_exploration_risks(fleet, star_system, player, game_state)
        
        # Step 2: Discover planets (if system not already explored)
        if player.player_id not in star_system.explored_by:
            result.planets_discovered, result.star_card_drawn = self._discover_planets(star_system, game_state)
            star_system.explored_by.add(player.player_id)
        
        # Step 3: Reveal enemy colonies and ships
        result.colonies_revealed = self._reveal_enemy_colonies(location, player, game_state)
        result.ships_revealed = self._reveal_enemy_ships(location, player, game_state)
        
        return result
    
    def _resolve_exploration_risks(self, fleet, star_system, player, game_state: GameState) -> List[Dict]:
        """Resolve exploration risks for unarmed ships."""
        losses = []
        
        # Only unarmed ships face risks in unexplored systems
        if player.player_id in star_system.explored_by:
            return losses  # No risk for already explored systems
        
        # Check if fleet has warships for protection
        has_warship_protection = fleet.has_warships
        
        if has_warship_protection:
            return losses  # Warships protect from exploration risks
        
        # Roll for each unarmed ship group
        unarmed_ships = [ship for ship in fleet.ships if ship.is_unarmed]
        
        for ship_group in unarmed_ships:
            for _ in range(ship_group.count):
                # Roll 1d6, destroyed on roll of 1
                if random.randint(1, 6) == 1:
                    losses.append({
                        "ship_type": ship_group.ship_type.value,
                        "location": fleet.location
                    })
                    
                    # Remove ship from fleet
                    fleet.remove_ships(ship_group.ship_type, 1)
        
        return losses
    
    def _discover_planets(self, star_system, game_state: GameState) -> tuple[List[Planet], int]:
        """Discover planets by drawing a star card."""
        # This would normally draw from star card deck based on star color
        # For now, use simplified random generation based on star color probabilities
        
        planets = []
        star_card_number = self._draw_star_card(star_system.color)
        
        # Generate planets based on star color tendencies from rules
        planet_data = self._get_star_card_data(star_card_number, star_system.color)
        
        for planet_info in planet_data:
            planet = Planet(
                planet_type=planet_info["type"],
                max_population=planet_info["max_pop"],
                is_mineral_rich=planet_info["mineral_rich"],
                orbit=planet_info["orbit"]
            )
            planets.append(planet)
        
        # Add planets to star system
        star_system.planets.extend(planets)
        star_system.star_card_number = star_card_number
        
        return planets, star_card_number
    
    def _draw_star_card(self, star_color) -> int:
        """Draw a star card number (simplified)."""
        # In real implementation, this would draw from appropriate deck
        return random.randint(1, 20)  # Placeholder
    
    def _get_star_card_data(self, card_number: int, star_color) -> List[Dict]:
        """Get planet data from star card (simplified)."""
        # This would lookup actual star card data from game files
        # Yellow stars more likely to have Terran planets, blue more likely mineral-rich, etc.
        
        if star_color.value == "yellow":
            # Yellow stars favor habitable planets
            return [
                {
                    "type": PlanetType.TERRAN,
                    "max_pop": random.choice([40, 60, 80]),
                    "mineral_rich": False,
                    "orbit": 3
                }
            ]
        elif star_color.value == "blue":
            # Blue stars favor mineral-rich planets
            return [
                {
                    "type": PlanetType.MINIMAL_TERRAN,
                    "max_pop": random.choice([10, 20, 40]),
                    "mineral_rich": True,
                    "orbit": 4
                }
            ]
        else:
            # Other colors have mixed results
            return [
                {
                    "type": random.choice(list(PlanetType)),
                    "max_pop": random.choice([10, 20, 40, 60]),
                    "mineral_rich": random.choice([True, False]),
                    "orbit": random.randint(1, 6)
                }
            ]
    
    def _reveal_enemy_colonies(self, location: str, player, game_state: GameState) -> List[Dict]:
        """Reveal enemy colonies at the location."""
        revealed = []
        
        for other_player_id, other_player in game_state.players.items():
            if other_player_id == player.player_id:
                continue
            
            colonies = other_player.get_colony_at_location(location)
            for colony in colonies:
                # Reveal colony existence and some details (not all defenses)
                colony_info = {
                    "player_id": other_player_id,
                    "population": colony.population,
                    "factories": colony.factories,
                    "has_planet_shield": colony.has_planet_shield,
                    "planet_type": colony.planet.planet_type.value
                }
                revealed.append(colony_info)
        
        return revealed
    
    def _reveal_enemy_ships(self, location: str, player, game_state: GameState) -> List[Dict]:
        """Reveal enemy ships at the location."""
        revealed = []
        
        for other_player_id, other_player in game_state.players.items():
            if other_player_id == player.player_id:
                continue
            
            enemy_fleet = other_player.get_fleet_at_location(location)
            if enemy_fleet:
                # Reveal ship counts
                ship_info = {
                    "player_id": other_player_id,
                    "ship_counts": enemy_fleet.ship_counts,
                    "total_ships": enemy_fleet.total_ships
                }
                revealed.append(ship_info)
        
        return revealed
    
    def _serialize_result(self, result: ExplorationResult) -> Dict[str, Any]:
        """Serialize exploration result for logging."""
        return {
            "location": result.location,
            "star_card": result.star_card_drawn,
            "planets_found": len(result.planets_discovered or []),
            "colonies_revealed": len(result.colonies_revealed or []),
            "ships_revealed": len(result.ships_revealed or []),
            "ships_lost": len(result.exploration_losses or [])
        }