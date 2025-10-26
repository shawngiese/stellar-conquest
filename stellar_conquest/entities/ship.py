"""Ship entity for Stellar Conquest."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

from ..core.enums import ShipType
from ..core.exceptions import ValidationError, InvalidActionError
from ..core.constants import SHIP_COSTS, DESTRUCTION_RATES
from ..data import SHIP_DATA, get_ship_data
from ..utils.validation import GameValidator, Validator
from .base import CombatEntity, LocationEntity


@dataclass
class Ship(CombatEntity, LocationEntity):
    """Represents a single ship or group of ships of the same type."""
    
    ship_type: ShipType = ShipType.SCOUT
    count: int = 1
    destination: Optional[str] = None
    carried_population: int = 0  # For colony transports
    task_force_id: Optional[int] = None  # Task force identity to prevent unwanted merging
    
    def __post_init__(self):
        """Initialize ship with data from ship database."""
        # Get ship data and set properties
        ship_data = get_ship_data(self.ship_type)
        self.combat_strength = ship_data.combat_strength
        self.can_attack = ship_data.can_attack
        
        super().__post_init__()
    
    def validate(self) -> None:
        """Validate ship state."""
        super().validate()
        
        Validator.validate_enum(self.ship_type, ShipType, "ship_type")
        GameValidator.validate_ship_count(self.count, self.ship_type)
        
        if self.destination:
            GameValidator.validate_hex_coordinate(self.destination)
        
        if self.carried_population > 0:
            if not self.carries_population:
                raise ValidationError("Only colony transports can carry population")
            GameValidator.validate_population(self.carried_population)
            
            # Each colony transport carries exactly 1 million population
            if self.ship_type == ShipType.COLONY_TRANSPORT:
                expected_population = self.count * 1  # 1 million per transport
                if self.carried_population != expected_population:
                    raise ValidationError(
                        f"Colony transports must carry 1M each: "
                        f"expected {expected_population}, got {self.carried_population}"
                    )
    
    @property
    def is_warship(self) -> bool:
        """Check if this ship type can participate in combat."""
        return self.ship_type in [ShipType.CORVETTE, ShipType.FIGHTER, ShipType.DEATH_STAR]
    
    @property
    def is_unarmed(self) -> bool:
        """Check if this ship type is vulnerable to exploration risks."""
        return self.ship_type in [ShipType.SCOUT, ShipType.COLONY_TRANSPORT]
    
    @property
    def carries_population(self) -> bool:
        """Check if this ship type can carry population."""
        return self.ship_type == ShipType.COLONY_TRANSPORT
    
    @property
    def total_cost(self) -> int:
        """Get total industrial point cost for all ships."""
        return SHIP_COSTS[self.ship_type] * self.count
    
    @property
    def total_combat_strength(self) -> int:
        """Get total combat strength for all ships."""
        return self.combat_strength * self.count if self.is_active() else 0
    
    @property
    def destruction_rate(self) -> int:
        """Get population destruction rate per turn (for warships)."""
        if self.ship_type in DESTRUCTION_RATES:
            return DESTRUCTION_RATES[self.ship_type] * self.count
        return 0
    
    def split(self, count: int) -> "Ship":
        """Split off a number of ships into a new Ship object."""
        if count >= self.count:
            raise InvalidActionError(
                f"Cannot split {count} ships from group of {self.count}"
            )
        
        if count <= 0:
            raise InvalidActionError("Split count must be positive")
        
        # Calculate population for colony transports
        split_population = 0
        if self.carries_population and self.carried_population > 0:
            population_per_ship = self.carried_population // self.count
            split_population = population_per_ship * count
        
        # Create new ship group
        new_ship = Ship(
            ship_type=self.ship_type,
            count=count,
            location=self.location,
            destination=self.destination,
            carried_population=split_population,
            player_id=self.player_id,
            game_id=self.game_id
        )
        
        # Update this ship group
        self.count -= count
        if self.carries_population:
            self.carried_population -= split_population
        self.update_modified_time()
        
        return new_ship
    
    def merge(self, other: "Ship") -> None:
        """Merge another ship group into this one."""
        if self.ship_type != other.ship_type:
            raise InvalidActionError(
                f"Cannot merge {self.ship_type.value} with {other.ship_type.value}"
            )
        
        if self.player_id != other.player_id:
            raise InvalidActionError("Cannot merge ships from different players")
        
        if self.location != other.location:
            raise InvalidActionError(
                f"Cannot merge ships at different locations: {self.location} vs {other.location}"
            )
        
        # Prevent merging between different task forces (allow cars on freeway model)
        if self.task_force_id != other.task_force_id:
            raise InvalidActionError(
                f"Cannot merge ships from different task forces: TF{self.task_force_id} vs TF{other.task_force_id}"
            )
        
        # Merge counts and population
        self.count += other.count
        if self.carries_population:
            self.carried_population += other.carried_population
        
        self.update_modified_time()
        
        # Mark other ship as destroyed (will be cleaned up)
        other.destroy()
    
    def remove_ships(self, count: int) -> int:
        """Remove ships from this group, returning actual count removed."""
        if count <= 0:
            return 0
        
        removed = min(count, self.count)
        self.count -= removed
        
        # Remove proportional population for colony transports
        if self.carries_population and self.carried_population > 0:
            population_per_ship = self.carried_population // (self.count + removed)
            self.carried_population -= population_per_ship * removed
        
        # If no ships left, mark as destroyed
        if self.count <= 0:
            self.destroy()
        
        self.update_modified_time()
        return removed
    
    def set_destination(self, destination: str) -> None:
        """Set ship destination for movement."""
        GameValidator.validate_hex_coordinate(destination)
        self.destination = destination
        self.update_modified_time()
    
    def clear_destination(self) -> None:
        """Clear ship destination."""
        self.destination = None
        self.update_modified_time()
    
    def load_population(self, population: int) -> int:
        """Load population onto colony transports. Returns excess that couldn't fit."""
        if not self.carries_population:
            raise InvalidActionError("Only colony transports can carry population")
        
        if population <= 0:
            return 0
        
        # Each transport carries exactly 1 million
        max_capacity = self.count * 1_000_000
        current_capacity = max_capacity - self.carried_population
        
        actual_loaded = min(population, current_capacity)
        self.carried_population += actual_loaded
        self.update_modified_time()
        
        return population - actual_loaded
    
    def unload_population(self, amount: Optional[int] = None) -> int:
        """Unload population from colony transports. Returns amount unloaded."""
        if not self.carries_population:
            raise InvalidActionError("Only colony transports can carry population")
        
        if amount is None:
            amount = self.carried_population
        
        actual_unloaded = min(amount, self.carried_population)
        self.carried_population -= actual_unloaded
        self.update_modified_time()
        
        return actual_unloaded
    
    def move_to_location(self, new_location: str) -> None:
        """Move ship to new location."""
        super().move_to_location(new_location)
        # Clear destination when ship reaches a location
        if self.destination == new_location:
            self.destination = None
    
    def calculate_combat_value(self) -> float:
        """Calculate relative combat value for AI decision making."""
        if not self.is_active():
            return 0.0
        
        base_values = {
            ShipType.SCOUT: 0.0,
            ShipType.COLONY_TRANSPORT: 0.0,
            ShipType.CORVETTE: 1.0,
            ShipType.FIGHTER: 2.5,
            ShipType.DEATH_STAR: 6.0
        }
        
        return base_values.get(self.ship_type, 0.0) * self.count
    
    def can_explore_safely(self, has_warship_escort: bool) -> bool:
        """Check if ship can explore without risk."""
        if self.is_warship:
            return True  # Warships have no exploration risk
        
        return has_warship_escort  # Unarmed ships need escort
    
    def get_movement_cost(self) -> int:
        """Get industrial point cost to build replacement ships."""
        return self.total_cost
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ship to dictionary representation."""
        data = super().to_dict()
        data.update({
            "ship_type": self.ship_type.value,
            "count": self.count,
            "destination": self.destination,
            "carried_population": self.carried_population,
            "total_cost": self.total_cost,
            "total_combat_strength": self.total_combat_strength,
            "is_warship": self.is_warship,
            "is_unarmed": self.is_unarmed
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ship":
        """Create ship from dictionary representation."""
        # Convert ship_type string back to enum
        ship_type = ShipType(data["ship_type"])
        
        return cls(
            id=data.get("id", ""),
            ship_type=ship_type,
            count=data["count"],
            location=data.get("location", ""),
            destination=data.get("destination"),
            carried_population=data.get("carried_population", 0),
            player_id=data.get("player_id", 0),
            game_id=data.get("game_id", "")
        )
    
    def __str__(self) -> str:
        """String representation of ship."""
        location_str = f" at {self.location}" if self.location else ""
        dest_str = f" -> {self.destination}" if self.destination else ""
        pop_str = f" (carrying {self.carried_population}M)" if self.carried_population > 0 else ""
        
        return f"{self.count} {self.ship_type.value.title()}{location_str}{dest_str}{pop_str}"


class ShipGroup:
    """Collection of ships at the same location, similar to original Fleet concept."""
    
    def __init__(self, location: str, player_id: int):
        self.location = location
        self.player_id = player_id
        self.ships: List[Ship] = []
    
    def add_ships(self, ship: Ship) -> None:
        """Add ships to the group."""
        if ship.location != self.location:
            raise InvalidActionError(f"Ship location {ship.location} doesn't match group location {self.location}")
        
        if ship.player_id != self.player_id:
            raise InvalidActionError(f"Ship owner {ship.player_id} doesn't match group owner {self.player_id}")
        
        # Try to merge with existing ships of same type and task force
        for existing_ship in self.ships:
            if (existing_ship.ship_type == ship.ship_type and 
                existing_ship.destination == ship.destination and
                existing_ship.task_force_id == ship.task_force_id):
                existing_ship.merge(ship)
                return
        
        # Add as new ship group
        self.ships.append(ship)
    
    def remove_ships(self, ship_type: ShipType, count: int) -> int:
        """Remove ships from group, returning actual count removed."""
        removed = 0
        ships_to_remove = []
        
        for i, ship in enumerate(self.ships):
            if ship.ship_type == ship_type and removed < count:
                needed = count - removed
                actual_removed = ship.remove_ships(needed)
                removed += actual_removed
                
                if ship.count <= 0:
                    ships_to_remove.append(i)
                
                if removed >= count:
                    break
        
        # Remove destroyed ships
        for i in reversed(ships_to_remove):
            self.ships.pop(i)
        
        return removed
    
    def get_ship_counts(self) -> Dict[ShipType, int]:
        """Get count of each ship type in the group."""
        counts = {}
        for ship in self.ships:
            if ship.is_active():
                counts[ship.ship_type] = counts.get(ship.ship_type, 0) + ship.count
        return counts
    
    def get_total_ships(self) -> int:
        """Get total number of ships in the group."""
        return sum(ship.count for ship in self.ships if ship.is_active())
    
    def get_warships(self) -> List[Ship]:
        """Get all warships in the group."""
        return [ship for ship in self.ships if ship.is_warship and ship.is_active()]
    
    def get_unarmed_ships(self) -> List[Ship]:
        """Get all unarmed ships in the group."""
        return [ship for ship in self.ships if ship.is_unarmed and ship.is_active()]
    
    def has_warships(self) -> bool:
        """Check if group contains any warships."""
        return len(self.get_warships()) > 0
    
    def get_total_combat_strength(self) -> int:
        """Get total combat strength of all ships."""
        return sum(ship.total_combat_strength for ship in self.ships if ship.is_active())
    
    def get_ships_by_type(self, ship_type: ShipType) -> List[Ship]:
        """Get all ship groups of a specific type."""
        return [ship for ship in self.ships if ship.ship_type == ship_type and ship.is_active()]
    
    def cleanup_destroyed_ships(self) -> int:
        """Remove destroyed ships and return count removed."""
        initial_count = len(self.ships)
        self.ships = [ship for ship in self.ships if ship.is_active()]
        return initial_count - len(self.ships)
    
    def is_empty(self) -> bool:
        """Check if group has no active ships."""
        return self.get_total_ships() == 0