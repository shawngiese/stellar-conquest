"""Colony entity for Stellar Conquest."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

from ..core.enums import ColonyStatus, Technology
from ..core.exceptions import ValidationError, ConstraintViolationError, InsufficientResourcesError
from ..core.constants import BUILDING_COSTS, IP_PER_POPULATION, IP_PER_FACTORY, MINERAL_RICH_MULTIPLIER
from ..utils.validation import GameValidator, Validator
from .base import ProductiveEntity, ResearchableEntity
from .planet import Planet


@dataclass
class Colony(ProductiveEntity, ResearchableEntity):
    """Represents a player's colony on a planet."""
    
    planet: Planet = field(default_factory=lambda: Planet())
    population: int = 0
    factories: int = 0
    missile_bases: int = 0
    advanced_missile_bases: int = 0
    has_planet_shield: bool = False
    status: ColonyStatus = ColonyStatus.ACTIVE
    original_owner: Optional[int] = None
    turns_under_control: int = 0
    
    def __post_init__(self):
        """Initialize colony with validation."""
        # Set location to match planet
        if self.planet.location:
            self.location = self.planet.location
        
        super().__post_init__()
    
    def validate(self) -> None:
        """Validate colony state."""
        super().validate()
        
        self.planet.validate()
        GameValidator.validate_population(self.population)
        Validator.validate_non_negative(self.factories, "factories")
        Validator.validate_non_negative(self.missile_bases, "missile_bases")
        Validator.validate_non_negative(self.advanced_missile_bases, "advanced_missile_bases")
        Validator.validate_type(self.has_planet_shield, bool, "has_planet_shield")
        Validator.validate_enum(self.status, ColonyStatus, "status")
        
        if self.original_owner is not None:
            GameValidator.validate_player_id(self.original_owner)
        
        # Validate population doesn't exceed planet capacity
        if self.population > self.planet.max_population:
            raise ConstraintViolationError(
                f"Population {self.population} exceeds planet capacity {self.planet.max_population}"
            )
        
        # Validate location matches planet
        if self.location != self.planet.location:
            raise ValidationError(
                f"Colony location {self.location} doesn't match planet location {self.planet.location}"
            )
    
    @property
    def effective_owner(self) -> int:
        """The player who currently controls this colony."""
        return self.player_id
    
    @property
    def is_conquered(self) -> bool:
        """Check if colony is conquered by another player."""
        return self.status == ColonyStatus.CONQUERED
    
    @property
    def is_besieged(self) -> bool:
        """Check if colony is under siege."""
        return self.status == ColonyStatus.BESIEGED
    
    @property
    def is_active(self) -> bool:
        """Check if colony is actively producing."""
        return self.status == ColonyStatus.ACTIVE
    
    @property
    def can_grow(self) -> bool:
        """Check if this colony can grow population."""
        return (self.is_active and 
                self.planet.can_support_growth and
                self.population < self.planet.max_population)
    
    @property
    def can_produce(self) -> bool:
        """Check if colony can produce industrial points."""
        # Conquered colonies can't produce in first turn after conquest
        if self.is_conquered and self.turns_under_control < 1:
            return False
        
        return self.status in [ColonyStatus.ACTIVE, ColonyStatus.CONQUERED]
    
    @property
    def can_build_ships(self) -> bool:
        """Check if colony can build ships."""
        return self.can_produce and not self.is_besieged
    
    @property
    def can_build_defenses(self) -> bool:
        """Check if colony can build defensive structures."""
        if self.is_conquered:
            return False  # Conquered colonies can't build defenses
        
        return self.status in [ColonyStatus.ACTIVE, ColonyStatus.BESIEGED]
    
    @property
    def total_defenses(self) -> int:
        """Get total defensive strength."""
        total = self.missile_bases + (self.advanced_missile_bases * 2)
        return total
    
    @property
    def is_defended(self) -> bool:
        """Check if colony has any defenses."""
        return self.total_defenses > 0 or self.has_planet_shield
    
    @property
    def is_invulnerable(self) -> bool:
        """Check if colony cannot be attacked (planet shield)."""
        return self.has_planet_shield
    
    def calculate_growth(self) -> int:
        """Calculate population growth for this production turn."""
        if not self.can_grow:
            return 0
        
        return self.planet.calculate_growth(self.population)
    
    def calculate_industrial_points(self) -> int:
        """Calculate industrial points produced this turn."""
        if not self.can_produce:
            return 0
        
        # Base production: population + factories
        base_ip = (self.population * IP_PER_POPULATION + 
                  self.factories * IP_PER_FACTORY)
        
        # Apply mineral-rich multiplier
        if self.planet.is_mineral_rich:
            base_ip = int(base_ip * MINERAL_RICH_MULTIPLIER)
        
        return base_ip
    
    def add_population(self, amount: int) -> int:
        """Add population, returning excess that couldn't fit."""
        if amount <= 0:
            return 0
        
        available_space = self.planet.max_population - self.population
        actual_added = min(amount, available_space)
        self.population += actual_added
        self.update_modified_time()
        
        return amount - actual_added
    
    def remove_population(self, amount: int) -> int:
        """Remove population, returning actual amount removed."""
        if amount <= 0:
            return 0
        
        actual_removed = min(amount, self.population)
        self.population -= actual_removed
        self.update_modified_time()
        
        # Check if colony is abandoned
        if self.population <= 0:
            self.abandon()
        
        return actual_removed
    
    def grow_population(self) -> int:
        """Execute population growth, returning growth amount."""
        if not self.can_grow:
            return 0
        
        growth = self.calculate_growth()
        self.population += growth
        self.update_modified_time()
        
        return growth
    
    def add_factories(self, count: int, factory_limit: Optional[int] = None) -> int:
        """Add factories, respecting population limits. Returns excess."""
        if count <= 0:
            return 0
        
        # Check factory limits based on technology
        if factory_limit is not None:
            max_factories = self.population * factory_limit
            available_slots = max(0, max_factories - self.factories)
            actual_added = min(count, available_slots)
        else:
            # Robotic industry - no limit
            actual_added = count
        
        self.factories += actual_added
        self.update_modified_time()
        
        return count - actual_added
    
    def remove_factories(self, count: int) -> int:
        """Remove factories, returning actual count removed."""
        if count <= 0:
            return 0
        
        actual_removed = min(count, self.factories)
        self.factories -= actual_removed
        self.update_modified_time()
        
        return actual_removed
    
    def add_missile_bases(self, count: int) -> None:
        """Add missile bases."""
        if count > 0:
            self.missile_bases += count
            self.update_modified_time()
    
    def add_advanced_missile_bases(self, count: int) -> None:
        """Add advanced missile bases."""
        if count > 0:
            self.advanced_missile_bases += count
            self.update_modified_time()
    
    def install_planet_shield(self) -> None:
        """Install planet shield defense."""
        self.has_planet_shield = True
        self.update_modified_time()
    
    def destroy_defenses(self, missile_bases: int = 0, advanced_bases: int = 0) -> Dict[str, int]:
        """Destroy defensive structures. Returns actual amounts destroyed."""
        destroyed = {"missile_bases": 0, "advanced_missile_bases": 0}
        
        if missile_bases > 0:
            destroyed["missile_bases"] = min(missile_bases, self.missile_bases)
            self.missile_bases -= destroyed["missile_bases"]
        
        if advanced_bases > 0:
            destroyed["advanced_missile_bases"] = min(advanced_bases, self.advanced_missile_bases)
            self.advanced_missile_bases -= destroyed["advanced_missile_bases"]
        
        if destroyed["missile_bases"] > 0 or destroyed["advanced_missile_bases"] > 0:
            self.update_modified_time()
        
        return destroyed
    
    def conquer(self, new_owner: int) -> None:
        """Mark colony as conquered by new owner."""
        GameValidator.validate_player_id(new_owner)
        
        # Store original owner if this is first conquest
        if self.original_owner is None:
            self.original_owner = self.player_id
        
        self.player_id = new_owner
        self.status = ColonyStatus.CONQUERED
        self.turns_under_control = 0
        self.update_modified_time()
    
    def liberate(self) -> None:
        """Return colony to original owner."""
        if self.original_owner is not None:
            self.player_id = self.original_owner
            self.original_owner = None
        
        self.status = ColonyStatus.ACTIVE
        self.turns_under_control = 0
        self.update_modified_time()
    
    def besiege(self) -> None:
        """Mark colony as under siege."""
        if self.status == ColonyStatus.ACTIVE:
            self.status = ColonyStatus.BESIEGED
            self.update_modified_time()
    
    def relieve_siege(self) -> None:
        """Remove siege status."""
        if self.status == ColonyStatus.BESIEGED:
            self.status = ColonyStatus.ACTIVE
            self.update_modified_time()
    
    def abandon(self) -> None:
        """Abandon the colony."""
        self.status = ColonyStatus.ABANDONED
        self.population = 0
        self.factories = 0  # Factories destroyed when abandoned
        self.update_modified_time()
    
    def advance_turn(self) -> None:
        """Advance colony by one turn."""
        if self.is_conquered or self.status != ColonyStatus.ABANDONED:
            self.turns_under_control += 1
    
    def calculate_emigration_bonus(self, emigrants: int) -> int:
        """Calculate population bonus from emigration."""
        if emigrants <= 0:
            return 0
        
        # Population bonus: 1 million for every 3 million emigrants
        # up to bonus limit (growth + 3 million)
        base_growth = self.calculate_growth()
        bonus_limit = base_growth + 3
        
        eligible_emigrants = min(emigrants, bonus_limit)
        bonus = eligible_emigrants // 3
        
        return bonus
    
    def spend_industrial_points(self, spending_plan: Dict[str, int], 
                               available_technologies: set) -> Dict[str, Any]:
        """Execute industrial spending plan. Returns results."""
        total_ip = self.calculate_industrial_points()
        total_spending = sum(spending_plan.values())
        
        if total_spending > total_ip:
            raise InsufficientResourcesError(
                f"Spending {total_spending} exceeds available IP {total_ip}"
            )
        
        results = {
            "total_ip": total_ip,
            "spent": 0,
            "purchases": {},
            "research": {},
            "remaining": total_ip
        }
        
        # Process purchases
        for item, amount in spending_plan.items():
            if amount <= 0:
                continue
            
            if item in BUILDING_COSTS:
                # Building purchase
                cost_per_unit = BUILDING_COSTS[item]
                units = amount // cost_per_unit
                
                if item == "factory":
                    excess = self.add_factories(units, 1)  # Normal factory limit
                    results["purchases"]["factories"] = units - excess
                elif item == "robotic_factory":
                    if Technology.ROBOTIC_INDUSTRY in available_technologies:
                        excess = self.add_factories(units, None)  # No limit
                        results["purchases"]["robotic_factories"] = units - excess
                elif item == "missile_base":
                    if Technology.MISSILE_BASE in available_technologies:
                        self.add_missile_bases(units)
                        results["purchases"]["missile_bases"] = units
                elif item == "advanced_missile_base":
                    if Technology.ADVANCED_MISSILE_BASE in available_technologies:
                        self.add_advanced_missile_bases(units)
                        results["purchases"]["advanced_missile_bases"] = units
                elif item == "planet_shield":
                    if (Technology.PLANET_SHIELD in available_technologies and 
                        not self.has_planet_shield):
                        self.install_planet_shield()
                        results["purchases"]["planet_shield"] = 1
                
                results["spent"] += units * cost_per_unit
            
            else:
                # Research or other spending
                results["research"][item] = amount
                results["spent"] += amount
        
        results["remaining"] = total_ip - results["spent"]
        return results
    
    def get_strategic_value(self) -> float:
        """Calculate strategic value for AI decision making."""
        value = self.planet.get_strategic_value()
        
        # Add value for existing infrastructure
        value += self.population * 0.1
        value += self.factories * 2.0
        value += self.total_defenses * 1.5
        
        # Bonus for active status
        if self.is_active:
            value *= 1.2
        elif self.is_conquered:
            value *= 0.8
        elif self.is_besieged:
            value *= 0.6
        
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert colony to dictionary representation."""
        data = super().to_dict()
        data.update({
            "planet": self.planet.to_dict(),
            "population": self.population,
            "factories": self.factories,
            "missile_bases": self.missile_bases,
            "advanced_missile_bases": self.advanced_missile_bases,
            "has_planet_shield": self.has_planet_shield,
            "status": self.status.value,
            "original_owner": self.original_owner,
            "turns_under_control": self.turns_under_control,
            "industrial_output": self.calculate_industrial_points(),
            "total_defenses": self.total_defenses,
            "strategic_value": self.get_strategic_value()
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Colony":
        """Create colony from dictionary representation."""
        planet = Planet.from_dict(data["planet"])
        status = ColonyStatus(data["status"])
        
        return cls(
            id=data.get("id", ""),
            planet=planet,
            population=data["population"],
            factories=data["factories"],
            missile_bases=data["missile_bases"],
            advanced_missile_bases=data["advanced_missile_bases"],
            has_planet_shield=data["has_planet_shield"],
            status=status,
            original_owner=data.get("original_owner"),
            turns_under_control=data["turns_under_control"],
            player_id=data.get("player_id", 0),
            game_id=data.get("game_id", "")
        )
    
    def __str__(self) -> str:
        """String representation of colony."""
        status_str = f" ({self.status.value})" if self.status != ColonyStatus.ACTIVE else ""
        defense_str = f", {self.total_defenses} defenses" if self.is_defended else ""
        shield_str = ", shielded" if self.has_planet_shield else ""
        
        return (f"Colony of {self.population}M on {self.planet.planet_type.value} "
                f"planet at {self.location} with {self.factories} factories"
                f"{defense_str}{shield_str}{status_str}")


# Utility functions for colony operations
def create_starting_colony(planet: Planet, player_id: int, population: int = 1) -> Colony:
    """Create a new colony for a player."""
    colony = Colony(
        planet=planet,
        population=population,
        player_id=player_id,
        game_id=""  # Will be set by game
    )
    return colony


def calculate_colony_maintenance_cost(colony: Colony) -> int:
    """Calculate maintenance cost for a colony (if any)."""
    # Stellar Conquest doesn't have maintenance costs, but this could be extended
    return 0


def get_colonies_by_status(colonies: List[Colony], status: ColonyStatus) -> List[Colony]:
    """Filter colonies by status."""
    return [c for c in colonies if c.status == status]


def get_most_productive_colony(colonies: List[Colony]) -> Optional[Colony]:
    """Get colony with highest industrial output."""
    if not colonies:
        return None
    
    return max(colonies, key=lambda c: c.calculate_industrial_points())


def calculate_total_production(colonies: List[Colony]) -> int:
    """Calculate total industrial production across all colonies."""
    return sum(c.calculate_industrial_points() for c in colonies if c.can_produce)


def find_vulnerable_colonies(colonies: List[Colony]) -> List[Colony]:
    """Find colonies that are vulnerable to attack."""
    return [c for c in colonies if not c.is_defended and c.is_active]


def optimize_factory_distribution(colonies: List[Colony], 
                                 available_ip: int, 
                                 factory_limit_per_population: int = 1) -> Dict[str, int]:
    """Optimize factory distribution across colonies."""
    # Simple optimization: prioritize mineral-rich planets
    mineral_rich_colonies = [c for c in colonies if c.planet.is_mineral_rich and c.can_produce]
    
    factory_cost = BUILDING_COSTS["factory"]
    factories_to_build = available_ip // factory_cost
    
    distribution = {}
    
    # Prioritize mineral-rich colonies
    for colony in mineral_rich_colonies:
        if factories_to_build <= 0:
            break
        
        max_additional = (colony.population * factory_limit_per_population) - colony.factories
        to_add = min(factories_to_build, max_additional)
        
        if to_add > 0:
            distribution[colony.id] = to_add
            factories_to_build -= to_add
    
    # Then other colonies
    for colony in colonies:
        if factories_to_build <= 0:
            break
        
        if colony.id in distribution:
            continue  # Already handled
        
        max_additional = (colony.population * factory_limit_per_population) - colony.factories
        to_add = min(factories_to_build, max_additional)
        
        if to_add > 0:
            distribution[colony.id] = to_add
            factories_to_build -= to_add
    
    return distribution