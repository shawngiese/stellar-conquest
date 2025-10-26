"""Fleet entity for managing groups of ships."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .ship import Ship, ShipType


@dataclass
class Fleet:
    """Represents a collection of ships at a specific location."""
    
    player_id: int
    location: str  # Hex coordinate like "A1"
    ships: List[Ship] = field(default_factory=list)
    is_task_force: bool = False
    task_force_id: Optional[int] = None
    
    @property
    def total_ships(self) -> int:
        """Total number of individual ships in this fleet."""
        return sum(ship.count for ship in self.ships)
    
    @property
    def ship_counts(self) -> Dict[ShipType, int]:
        """Count of each ship type in the fleet."""
        counts = {ship_type: 0 for ship_type in ShipType}
        for ship in self.ships:
            counts[ship.ship_type] += ship.count
        return counts
    
    @property
    def has_warships(self) -> bool:
        """Check if fleet contains any warships."""
        return any(ship.is_warship for ship in self.ships)
    
    @property
    def has_unarmed_ships(self) -> bool:
        """Check if fleet contains scouts or colony transports."""
        return any(ship.is_unarmed for ship in self.ships)
    
    def add_ships(self, ship_type: ShipType, count: int, destination: Optional[str] = None) -> None:
        """Add ships to the fleet."""
        # Try to merge with existing ships of same type and destination
        for ship in self.ships:
            if ship.ship_type == ship_type and ship.destination == destination:
                ship.count += count
                return
        
        # Create new ship group
        self.ships.append(Ship(ship_type, count, destination))
    
    def remove_ships(self, ship_type: ShipType, count: int) -> int:
        """Remove ships from fleet, returning actual count removed."""
        removed = 0
        ships_to_remove = []
        
        for i, ship in enumerate(self.ships):
            if ship.ship_type == ship_type and removed < count:
                needed = count - removed
                if ship.count <= needed:
                    # Remove entire ship group
                    removed += ship.count
                    ships_to_remove.append(i)
                else:
                    # Split ship group
                    ship.count -= needed
                    removed += needed
                    break
        
        # Remove empty ship groups (in reverse order to maintain indices)
        for i in reversed(ships_to_remove):
            self.ships.pop(i)
        
        return removed
    
    def get_ships_by_type(self, ship_type: ShipType) -> List[Ship]:
        """Get all ship groups of a specific type."""
        return [ship for ship in self.ships if ship.ship_type == ship_type]
    
    def split_fleet(self, ship_selections: Dict[ShipType, int]) -> "Fleet":
        """Split off ships to create a new fleet."""
        new_fleet = Fleet(self.player_id, self.location)
        
        for ship_type, count in ship_selections.items():
            removed = self.remove_ships(ship_type, count)
            if removed > 0:
                new_fleet.add_ships(ship_type, removed)
        
        return new_fleet
    
    def merge_fleet(self, other: "Fleet") -> None:
        """Merge another fleet into this one."""
        if other.location != self.location:
            raise ValueError(f"Cannot merge fleets at different locations: {self.location} vs {other.location}")
        
        for ship in other.ships:
            self.add_ships(ship.ship_type, ship.count, ship.destination)
        
        other.ships.clear()
    
    def get_warships(self) -> List[Ship]:
        """Get all warships in the fleet."""
        return [ship for ship in self.ships if ship.is_warship]
    
    def get_colony_transports(self) -> List[Ship]:
        """Get all colony transports in the fleet."""
        return [ship for ship in self.ships if ship.ship_type == ShipType.COLONY_TRANSPORT]