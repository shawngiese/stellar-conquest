"""Base entity classes for Stellar Conquest domain objects."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
import uuid

from ..core.exceptions import ValidationError
from ..utils.validation import Validator


@dataclass
class BaseEntity(ABC):
    """Base class for all game entities with common functionality."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        self.validate()
        self._register_entity()
    
    @abstractmethod
    def validate(self) -> None:
        """Validate entity state. Must be implemented by subclasses."""
        pass
    
    def _register_entity(self) -> None:
        """Register entity in global registry for debugging/tracking."""
        # This could be used for debugging or game state tracking
        pass
    
    def update_modified_time(self) -> None:
        """Update the last modified timestamp."""
        self.last_modified = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary representation."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            elif isinstance(value, (list, set)):
                result[key] = [
                    item.to_dict() if hasattr(item, 'to_dict') else item 
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEntity":
        """Create entity from dictionary representation."""
        # This would be implemented by subclasses for proper deserialization
        raise NotImplementedError("Subclasses must implement from_dict")
    
    def copy(self) -> "BaseEntity":
        """Create a deep copy of this entity with new ID."""
        import copy
        new_entity = copy.deepcopy(self)
        new_entity.id = str(uuid.uuid4())
        new_entity.created_at = datetime.now()
        new_entity.last_modified = datetime.now()
        return new_entity
    
    def __eq__(self, other) -> bool:
        """Equality based on ID."""
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)


@dataclass
class GameEntity(BaseEntity):
    """Base class for entities that belong to a specific game."""
    
    game_id: str = ""
    
    def validate(self) -> None:
        """Validate game entity."""
        Validator.validate_type(self.game_id, str, "game_id")


@dataclass
class PlayerOwnedEntity(GameEntity):
    """Base class for entities owned by a player."""
    
    player_id: int = 0
    
    def validate(self) -> None:
        """Validate player-owned entity."""
        super().validate()
        from ..utils.validation import GameValidator
        GameValidator.validate_player_id(self.player_id)
    
    def is_owned_by(self, player_id: int) -> bool:
        """Check if entity is owned by specified player."""
        return self.player_id == player_id


@dataclass
class LocationEntity(GameEntity):
    """Base class for entities that exist at a specific location."""
    
    location: str = ""
    
    def validate(self) -> None:
        """Validate location entity."""
        super().validate()
        from ..utils.validation import GameValidator
        if self.location:
            GameValidator.validate_hex_coordinate(self.location)
    
    def is_at_location(self, location: str) -> bool:
        """Check if entity is at specified location."""
        return self.location == location
    
    def move_to_location(self, new_location: str) -> None:
        """Move entity to new location."""
        from ..utils.validation import GameValidator
        GameValidator.validate_hex_coordinate(new_location)
        self.location = new_location
        self.update_modified_time()


@dataclass
class CombatEntity(PlayerOwnedEntity):
    """Base class for entities that can participate in combat."""
    
    combat_strength: int = 0
    can_attack: bool = False
    is_destroyed: bool = False
    
    def validate(self) -> None:
        """Validate combat entity."""
        super().validate()
        Validator.validate_non_negative(self.combat_strength, "combat_strength")
        Validator.validate_type(self.can_attack, bool, "can_attack")
        Validator.validate_type(self.is_destroyed, bool, "is_destroyed")
    
    def destroy(self) -> None:
        """Mark entity as destroyed."""
        self.is_destroyed = True
        self.update_modified_time()
    
    def is_active(self) -> bool:
        """Check if entity is active (not destroyed)."""
        return not self.is_destroyed
    
    def can_participate_in_combat(self) -> bool:
        """Check if entity can participate in combat."""
        return self.is_active() and (self.can_attack or self.combat_strength > 0)


@dataclass
class ProductiveEntity(PlayerOwnedEntity):
    """Base class for entities that can produce industrial points."""
    
    industrial_output: int = 0
    
    def validate(self) -> None:
        """Validate productive entity."""
        super().validate()
        Validator.validate_non_negative(self.industrial_output, "industrial_output")
    
    def calculate_production(self) -> int:
        """Calculate industrial points produced. Override in subclasses."""
        return self.industrial_output
    
    def set_production(self, output: int) -> None:
        """Set industrial output."""
        Validator.validate_non_negative(output, "industrial_output")
        self.industrial_output = output
        self.update_modified_time()


@dataclass
class ResearchableEntity(PlayerOwnedEntity):
    """Base class for entities that can conduct research."""
    
    research_points: int = 0
    
    def validate(self) -> None:
        """Validate researchable entity."""
        super().validate()
        Validator.validate_non_negative(self.research_points, "research_points")
    
    def contribute_research(self, points: int) -> None:
        """Add research points."""
        Validator.validate_non_negative(points, "research_points")
        self.research_points += points
        self.update_modified_time()
    
    def get_research_contribution(self) -> int:
        """Get research points available."""
        return self.research_points


class EntityCollection:
    """Generic collection for managing entities with common operations."""
    
    def __init__(self, entity_type: type = BaseEntity):
        self.entity_type = entity_type
        self._entities: Dict[str, BaseEntity] = {}
    
    def add(self, entity: BaseEntity) -> None:
        """Add entity to collection."""
        if not isinstance(entity, self.entity_type):
            raise ValidationError(f"Entity must be of type {self.entity_type}")
        self._entities[entity.id] = entity
    
    def remove(self, entity_id: str) -> Optional[BaseEntity]:
        """Remove and return entity from collection."""
        return self._entities.pop(entity_id, None)
    
    def get(self, entity_id: str) -> Optional[BaseEntity]:
        """Get entity by ID."""
        return self._entities.get(entity_id)
    
    def get_all(self) -> List[BaseEntity]:
        """Get all entities in collection."""
        return list(self._entities.values())
    
    def filter_by_player(self, player_id: int) -> List[BaseEntity]:
        """Get entities owned by specific player."""
        return [
            entity for entity in self._entities.values()
            if hasattr(entity, 'player_id') and entity.player_id == player_id
        ]
    
    def filter_by_location(self, location: str) -> List[BaseEntity]:
        """Get entities at specific location."""
        return [
            entity for entity in self._entities.values()
            if hasattr(entity, 'location') and entity.location == location
        ]
    
    def filter_active(self) -> List[BaseEntity]:
        """Get active (non-destroyed) entities."""
        return [
            entity for entity in self._entities.values()
            if not hasattr(entity, 'is_destroyed') or not entity.is_destroyed
        ]
    
    def count(self) -> int:
        """Get count of entities in collection."""
        return len(self._entities)
    
    def clear(self) -> None:
        """Remove all entities from collection."""
        self._entities.clear()
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists in collection."""
        return entity_id in self._entities
    
    def find_by_criteria(self, criteria_func) -> List[BaseEntity]:
        """Find entities matching criteria function."""
        return [
            entity for entity in self._entities.values()
            if criteria_func(entity)
        ]


class EntityManager:
    """Manager for all entity collections in a game."""
    
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.collections: Dict[str, EntityCollection] = {}
    
    def register_collection(self, name: str, entity_type: type) -> EntityCollection:
        """Register a new entity collection."""
        collection = EntityCollection(entity_type)
        self.collections[name] = collection
        return collection
    
    def get_collection(self, name: str) -> Optional[EntityCollection]:
        """Get entity collection by name."""
        return self.collections.get(name)
    
    def get_all_entities(self) -> List[BaseEntity]:
        """Get all entities across all collections."""
        all_entities = []
        for collection in self.collections.values():
            all_entities.extend(collection.get_all())
        return all_entities
    
    def get_entities_by_player(self, player_id: int) -> List[BaseEntity]:
        """Get all entities owned by a player."""
        player_entities = []
        for collection in self.collections.values():
            player_entities.extend(collection.filter_by_player(player_id))
        return player_entities
    
    def get_entities_at_location(self, location: str) -> List[BaseEntity]:
        """Get all entities at a location."""
        location_entities = []
        for collection in self.collections.values():
            location_entities.extend(collection.filter_by_location(location))
        return location_entities
    
    def cleanup_destroyed_entities(self) -> int:
        """Remove all destroyed entities and return count removed."""
        removed_count = 0
        for collection in self.collections.values():
            destroyed_ids = [
                entity.id for entity in collection.get_all()
                if hasattr(entity, 'is_destroyed') and entity.is_destroyed
            ]
            for entity_id in destroyed_ids:
                collection.remove(entity_id)
                removed_count += 1
        return removed_count
    
    def validate_all_entities(self) -> List[str]:
        """Validate all entities and return list of validation errors."""
        errors = []
        for collection_name, collection in self.collections.items():
            for entity in collection.get_all():
                try:
                    entity.validate()
                except ValidationError as e:
                    errors.append(f"{collection_name}.{entity.id}: {str(e)}")
        return errors
    
    def export_game_state(self) -> Dict[str, Any]:
        """Export all entities to serializable format."""
        state = {
            "game_id": self.game_id,
            "collections": {}
        }
        
        for name, collection in self.collections.items():
            state["collections"][name] = [
                entity.to_dict() for entity in collection.get_all()
            ]
        
        return state


# Utility functions for entity operations
def create_entity_id(prefix: str = "") -> str:
    """Create a unique entity ID with optional prefix."""
    entity_id = str(uuid.uuid4())
    return f"{prefix}_{entity_id}" if prefix else entity_id


def validate_entity_reference(entity_id: str, collection: EntityCollection) -> bool:
    """Validate that an entity reference exists in collection."""
    return collection.exists(entity_id)


def transfer_entity_ownership(entity: PlayerOwnedEntity, new_owner: int) -> None:
    """Transfer entity ownership to new player."""
    from ..utils.validation import GameValidator
    GameValidator.validate_player_id(new_owner)
    
    old_owner = entity.player_id
    entity.player_id = new_owner
    entity.update_modified_time()
    
    # Could trigger events here for ownership change
    

def merge_entities(primary: BaseEntity, secondary: BaseEntity) -> BaseEntity:
    """Merge two entities, keeping primary and adding mergeable attributes from secondary."""
    # This would be implemented based on specific entity merge rules
    # For now, just return primary
    primary.update_modified_time()
    return primary


def clone_entity_for_scenario(entity: BaseEntity, scenario_id: str) -> BaseEntity:
    """Clone entity for scenario testing with new IDs."""
    cloned = entity.copy()
    if hasattr(cloned, 'game_id'):
        cloned.game_id = scenario_id
    return cloned