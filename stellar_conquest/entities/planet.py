"""Planet entity for Stellar Conquest."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

from ..core.enums import PlanetType, StarColor
from ..core.exceptions import ValidationError, ConstraintViolationError
from ..core.constants import VICTORY_POINTS
from ..data import get_planets_by_star_color
from ..utils.validation import GameValidator, Validator
from .base import BaseEntity, LocationEntity


@dataclass
class Planet(LocationEntity):
    """Represents a planet that can be colonized."""
    
    planet_type: PlanetType = PlanetType.TERRAN
    max_population: int = 40
    is_mineral_rich: bool = False
    orbit: int = 1
    star_color: Optional[StarColor] = None
    
    def validate(self) -> None:
        """Validate planet state."""
        super().validate()
        
        Validator.validate_enum(self.planet_type, PlanetType, "planet_type")
        GameValidator.validate_planet_capacity(self.max_population, self.planet_type)
        Validator.validate_type(self.is_mineral_rich, bool, "is_mineral_rich")
        Validator.validate_range(self.orbit, 1, 7, "orbit")
        
        if self.star_color:
            Validator.validate_enum(self.star_color, StarColor, "star_color")
    
    @property
    def can_support_growth(self) -> bool:
        """Check if this planet type supports population growth."""
        return self.planet_type in [PlanetType.TERRAN, PlanetType.SUB_TERRAN]
    
    @property
    def growth_rate(self) -> Optional[int]:
        """Population needed for 1 million growth per production turn."""
        if self.planet_type == PlanetType.TERRAN:
            return 5  # 1 per 5 million
        elif self.planet_type == PlanetType.SUB_TERRAN:
            return 10  # 1 per 10 million
        else:
            return None  # No growth on minimal-terran or barren
    
    @property
    def victory_points(self) -> int:
        """Victory points awarded for controlling this planet."""
        return VICTORY_POINTS.get(self.planet_type, 0)
    
    @property
    def is_habitable(self) -> bool:
        """Check if planet can be colonized normally."""
        return self.planet_type in [
            PlanetType.TERRAN, 
            PlanetType.SUB_TERRAN, 
            PlanetType.MINIMAL_TERRAN
        ]
    
    @property
    def requires_cet(self) -> bool:
        """Check if planet requires Controlled Environment Technology to colonize."""
        return self.planet_type == PlanetType.BARREN
    
    @property
    def industrial_multiplier(self) -> float:
        """Get industrial production multiplier."""
        return 2.0 if self.is_mineral_rich else 1.0
    
    def can_be_colonized(self, has_cet: bool = False) -> bool:
        """Check if planet can be colonized with current technology."""
        if self.requires_cet:
            return has_cet
        return self.is_habitable
    
    def calculate_growth(self, current_population: int) -> int:
        """Calculate population growth for this planet."""
        if not self.can_support_growth or current_population <= 0:
            return 0
        
        growth_rate = self.growth_rate
        if growth_rate is None:
            return 0
        
        base_growth = current_population // growth_rate
        
        # Cap growth at planet capacity
        max_growth = self.max_population - current_population
        return min(base_growth, max_growth)
    
    def can_support_population(self, population: int) -> bool:
        """Check if planet can support given population."""
        return population <= self.max_population
    
    def get_excess_population(self, population: int) -> int:
        """Get population that exceeds planet capacity."""
        return max(0, population - self.max_population)
    
    def calculate_base_production(self, population: int) -> int:
        """Calculate base industrial production before multipliers."""
        return min(population, self.max_population)  # IP per million population
    
    def calculate_total_production(self, population: int, factories: int) -> int:
        """Calculate total industrial production including factories."""
        base_production = self.calculate_base_production(population)
        factory_production = factories
        
        total = base_production + factory_production
        
        # Apply mineral-rich multiplier
        return int(total * self.industrial_multiplier)
    
    def get_strategic_value(self) -> float:
        """Calculate strategic value for AI decision making."""
        base_value = 0.0
        
        # Value based on planet type
        type_values = {
            PlanetType.TERRAN: 10.0,
            PlanetType.SUB_TERRAN: 6.0,
            PlanetType.MINIMAL_TERRAN: 3.0,
            PlanetType.BARREN: 1.0
        }
        base_value += type_values.get(self.planet_type, 0.0)
        
        # Population capacity bonus
        base_value += self.max_population * 0.1
        
        # Mineral-rich bonus
        if self.is_mineral_rich:
            base_value *= 1.5
        
        # Victory points bonus
        base_value += self.victory_points * 2.0
        
        return base_value
    
    def get_colonization_priority(self, player_has_cet: bool = False) -> float:
        """Get colonization priority score for AI."""
        if not self.can_be_colonized(player_has_cet):
            return 0.0
        
        priority = self.get_strategic_value()
        
        # Prefer planets that support growth
        if self.can_support_growth:
            priority *= 1.5
        
        # Bonus for high-capacity planets
        if self.max_population >= 60:
            priority *= 1.2
        
        return priority
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert planet to dictionary representation."""
        data = super().to_dict()
        data.update({
            "planet_type": self.planet_type.value,
            "max_population": self.max_population,
            "is_mineral_rich": self.is_mineral_rich,
            "orbit": self.orbit,
            "star_color": self.star_color.value if self.star_color else None,
            "victory_points": self.victory_points,
            "can_support_growth": self.can_support_growth,
            "requires_cet": self.requires_cet,
            "strategic_value": self.get_strategic_value()
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Planet":
        """Create planet from dictionary representation."""
        planet_type = PlanetType(data["planet_type"])
        star_color = StarColor(data["star_color"]) if data.get("star_color") else None
        
        return cls(
            id=data.get("id", ""),
            location=data.get("location", ""),
            planet_type=planet_type,
            max_population=data["max_population"],
            is_mineral_rich=data["is_mineral_rich"],
            orbit=data["orbit"],
            star_color=star_color,
            game_id=data.get("game_id", "")
        )
    
    def __str__(self) -> str:
        """String representation of planet."""
        mineral_str = " (mineral-rich)" if self.is_mineral_rich else ""
        location_str = f" at {self.location}" if self.location else ""
        
        return (f"{self.planet_type.value.title()} planet (orbit {self.orbit}, "
                f"max {self.max_population}M){mineral_str}{location_str}")


class StarSystem(LocationEntity):
    """Represents a star system containing planets."""
    
    def __init__(self, location: str, star_color: StarColor, name: Optional[str] = None):
        self.star_color = star_color
        self.name = name
        self.planets: List[Planet] = []
        self.explored_by: set = set()  # Player IDs who have explored
        self.star_card_number: Optional[int] = None
        super().__init__(location=location)
    
    def validate(self) -> None:
        """Validate star system."""
        super().validate()
        Validator.validate_enum(self.star_color, StarColor, "star_color")
        
        if self.name:
            Validator.validate_type(self.name, str, "name")
        
        if len(self.planets) > 3:
            raise ConstraintViolationError(
                f"Star system cannot have more than 3 planets: {len(self.planets)}"
            )
        
        # Validate each planet
        for planet in self.planets:
            planet.validate()
            if planet.location != self.location:
                raise ValidationError(
                    f"Planet location {planet.location} doesn't match system {self.location}"
                )
    
    def add_planet(self, planet: Planet) -> None:
        """Add a planet to this star system."""
        if len(self.planets) >= 3:
            raise ConstraintViolationError("Star system cannot have more than 3 planets")
        
        # Set planet location to match system
        planet.location = self.location
        planet.star_color = self.star_color
        
        # Check for duplicate orbits
        if any(p.orbit == planet.orbit for p in self.planets):
            raise ConstraintViolationError(f"Orbit {planet.orbit} already occupied")
        
        self.planets.append(planet)
        self.update_modified_time()
    
    def get_planet_by_orbit(self, orbit: int) -> Optional[Planet]:
        """Get planet at specific orbit."""
        for planet in self.planets:
            if planet.orbit == orbit:
                return planet
        return None
    
    def get_habitable_planets(self) -> List[Planet]:
        """Get all habitable planets in the system."""
        return [p for p in self.planets if p.is_habitable]
    
    def get_mineral_rich_planets(self) -> List[Planet]:
        """Get all mineral-rich planets in the system."""
        return [p for p in self.planets if p.is_mineral_rich]
    
    def get_colonizable_planets(self, has_cet: bool = False) -> List[Planet]:
        """Get all planets that can be colonized."""
        return [p for p in self.planets if p.can_be_colonized(has_cet)]
    
    def is_explored_by(self, player_id: int) -> bool:
        """Check if system has been explored by player."""
        return player_id in self.explored_by
    
    def explore(self, player_id: int, star_card_number: int) -> None:
        """Mark system as explored by player."""
        GameValidator.validate_player_id(player_id)
        self.explored_by.add(player_id)
        
        if self.star_card_number is None:
            self.star_card_number = star_card_number
        
        self.update_modified_time()
    
    def get_total_victory_points(self) -> int:
        """Get total victory points from all planets."""
        return sum(p.victory_points for p in self.planets)
    
    def get_strategic_value(self) -> float:
        """Calculate strategic value for AI decision making."""
        if not self.planets:
            return 0.0
        
        return sum(p.get_strategic_value() for p in self.planets)
    
    def get_exploration_value(self, star_color_preferences: Dict[StarColor, float] = None) -> float:
        """Get value for exploration targeting."""
        if star_color_preferences is None:
            # Default preferences based on game rules
            star_color_preferences = {
                StarColor.YELLOW: 2.0,  # More likely to have Terran planets
                StarColor.BLUE: 1.5,    # More likely to have mineral-rich
                StarColor.GREEN: 1.2,
                StarColor.ORANGE: 1.0,
                StarColor.RED: 0.8
            }
        
        return star_color_preferences.get(self.star_color, 1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert star system to dictionary representation."""
        data = super().to_dict()
        data.update({
            "star_color": self.star_color.value,
            "name": self.name,
            "planets": [p.to_dict() for p in self.planets],
            "explored_by": list(self.explored_by),
            "star_card_number": self.star_card_number,
            "total_victory_points": self.get_total_victory_points(),
            "strategic_value": self.get_strategic_value()
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StarSystem":
        """Create star system from dictionary representation."""
        star_color = StarColor(data["star_color"])
        
        system = cls(
            location=data["location"],
            star_color=star_color,
            name=data.get("name")
        )
        
        system.id = data.get("id", "")
        system.game_id = data.get("game_id", "")
        system.explored_by = set(data.get("explored_by", []))
        system.star_card_number = data.get("star_card_number")
        
        # Add planets
        for planet_data in data.get("planets", []):
            planet = Planet.from_dict(planet_data)
            system.planets.append(planet)
        
        return system
    
    def __str__(self) -> str:
        """String representation of star system."""
        name_str = f" ({self.name})" if self.name else ""
        planet_count = len(self.planets)
        explored_str = f", explored by {len(self.explored_by)} players" if self.explored_by else ""
        
        return (f"{self.star_color.value.title()} star at {self.location}{name_str} "
                f"with {planet_count} planet{'s' if planet_count != 1 else ''}{explored_str}")


# Utility functions for planet operations
def create_planet_from_star_card(star_card_data, orbit: int) -> Planet:
    """Create planet from star card data."""
    from ..data import get_star_card
    
    # This would use the star card data to create appropriate planet
    # For now, create a basic planet
    return Planet(
        planet_type=PlanetType.TERRAN,
        max_population=40,
        orbit=orbit
    )


def get_planets_by_type(planets: List[Planet], planet_type: PlanetType) -> List[Planet]:
    """Filter planets by type."""
    return [p for p in planets if p.planet_type == planet_type]


def get_most_valuable_planet(planets: List[Planet]) -> Optional[Planet]:
    """Get planet with highest strategic value."""
    if not planets:
        return None
    
    return max(planets, key=lambda p: p.get_strategic_value())


def calculate_system_production_potential(system: StarSystem, has_cet: bool = False) -> int:
    """Calculate maximum production potential of a star system."""
    total_potential = 0
    
    for planet in system.get_colonizable_planets(has_cet):
        # Assume maximum population and reasonable factory count
        max_population = planet.max_population
        estimated_factories = min(max_population, 20)  # Conservative factory estimate
        
        potential = planet.calculate_total_production(max_population, estimated_factories)
        total_potential += potential
    
    return total_potential


def find_best_colonization_targets(systems: List[StarSystem], 
                                 has_cet: bool = False, 
                                 limit: int = 5) -> List[Planet]:
    """Find best planets for colonization across multiple systems."""
    all_planets = []
    
    for system in systems:
        all_planets.extend(system.get_colonizable_planets(has_cet))
    
    # Sort by colonization priority
    sorted_planets = sorted(all_planets, 
                           key=lambda p: p.get_colonization_priority(has_cet), 
                           reverse=True)
    
    return sorted_planets[:limit]