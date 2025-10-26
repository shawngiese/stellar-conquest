"""Input validation utilities for Stellar Conquest simulator."""

import re
from typing import Any, List, Dict, Union, Optional, Type, Callable
from ..core.enums import ShipType, PlanetType, Technology, PlayStyle, StarColor, TurnPhase
from ..core.exceptions import (
    ValidationError, InvalidInputError, RangeValidationError, 
    TypeValidationError, ConstraintViolationError
)
from ..core.constants import (
    MAX_PLAYERS, MIN_PLAYER_COUNT, MAX_TURNS, MAX_GAME_NAME_LENGTH,
    MAX_PLAYER_NAME_LENGTH, VALID_HEX_PATTERN, STARTING_FLEET
)


class Validator:
    """Base validator class with common validation methods."""
    
    @staticmethod
    def validate_type(value: Any, expected_type: Type, field_name: str = "value") -> None:
        """Validate that value is of expected type."""
        if not isinstance(value, expected_type):
            raise TypeValidationError(
                f"{field_name} must be of type {expected_type.__name__}, got {type(value).__name__}",
                error_code="TYPE_MISMATCH",
                context={"field": field_name, "expected": expected_type.__name__, "actual": type(value).__name__}
            )
    
    @staticmethod
    def validate_range(value: Union[int, float], min_val: Union[int, float], 
                      max_val: Union[int, float], field_name: str = "value") -> None:
        """Validate that value is within specified range."""
        if not min_val <= value <= max_val:
            raise RangeValidationError(
                f"{field_name} must be between {min_val} and {max_val}, got {value}",
                error_code="OUT_OF_RANGE",
                context={"field": field_name, "value": value, "min": min_val, "max": max_val}
            )
    
    @staticmethod
    def validate_positive(value: Union[int, float], field_name: str = "value") -> None:
        """Validate that value is positive."""
        if value <= 0:
            raise RangeValidationError(
                f"{field_name} must be positive, got {value}",
                error_code="NOT_POSITIVE",
                context={"field": field_name, "value": value}
            )
    
    @staticmethod
    def validate_non_negative(value: Union[int, float], field_name: str = "value") -> None:
        """Validate that value is non-negative."""
        if value < 0:
            raise RangeValidationError(
                f"{field_name} must be non-negative, got {value}",
                error_code="NEGATIVE",
                context={"field": field_name, "value": value}
            )
    
    @staticmethod
    def validate_enum(value: Any, enum_class: Type, field_name: str = "value") -> None:
        """Validate that value is a valid enum member."""
        if not isinstance(value, enum_class):
            valid_values = [e.value for e in enum_class]
            raise InvalidInputError(
                f"{field_name} must be one of {valid_values}, got {value}",
                error_code="INVALID_ENUM",
                context={"field": field_name, "value": value, "valid_values": valid_values}
            )
    
    @staticmethod
    def validate_string_length(value: str, max_length: int, min_length: int = 0, 
                              field_name: str = "value") -> None:
        """Validate string length."""
        if not min_length <= len(value) <= max_length:
            raise RangeValidationError(
                f"{field_name} length must be between {min_length} and {max_length}, got {len(value)}",
                error_code="INVALID_LENGTH",
                context={"field": field_name, "length": len(value), "min": min_length, "max": max_length}
            )
    
    @staticmethod
    def validate_pattern(value: str, pattern: str, field_name: str = "value") -> None:
        """Validate string matches pattern."""
        if not re.match(pattern, value):
            raise InvalidInputError(
                f"{field_name} does not match required pattern {pattern}: {value}",
                error_code="PATTERN_MISMATCH",
                context={"field": field_name, "value": value, "pattern": pattern}
            )
    
    @staticmethod
    def validate_list_length(value: List, min_length: int = 0, max_length: int = None,
                            field_name: str = "list") -> None:
        """Validate list length."""
        if len(value) < min_length:
            raise RangeValidationError(
                f"{field_name} must have at least {min_length} items, got {len(value)}",
                error_code="LIST_TOO_SHORT",
                context={"field": field_name, "length": len(value), "min": min_length}
            )
        
        if max_length is not None and len(value) > max_length:
            raise RangeValidationError(
                f"{field_name} must have at most {max_length} items, got {len(value)}",
                error_code="LIST_TOO_LONG",
                context={"field": field_name, "length": len(value), "max": max_length}
            )
    
    @staticmethod
    def validate_unique_list(value: List, field_name: str = "list") -> None:
        """Validate that list contains unique items."""
        if len(value) != len(set(value)):
            raise ConstraintViolationError(
                f"{field_name} must contain unique items",
                error_code="DUPLICATE_ITEMS",
                context={"field": field_name, "length": len(value), "unique_count": len(set(value))}
            )


class GameValidator(Validator):
    """Validator for game-specific inputs."""
    
    @staticmethod
    def validate_player_id(player_id: int, max_players: int = MAX_PLAYERS) -> None:
        """Validate player ID."""
        GameValidator.validate_type(player_id, int, "player_id")
        GameValidator.validate_range(player_id, 1, max_players, "player_id")
    
    @staticmethod
    def validate_player_count(count: int) -> None:
        """Validate player count."""
        GameValidator.validate_type(count, int, "player_count")
        GameValidator.validate_range(count, MIN_PLAYER_COUNT, MAX_PLAYERS, "player_count")
    
    @staticmethod
    def validate_turn_number(turn: int) -> None:
        """Validate turn number."""
        GameValidator.validate_type(turn, int, "turn")
        GameValidator.validate_range(turn, 1, MAX_TURNS, "turn")
    
    @staticmethod
    def validate_hex_coordinate(hex_coord: str) -> None:
        """Validate hex coordinate format."""
        GameValidator.validate_type(hex_coord, str, "hex_coordinate")
        GameValidator.validate_pattern(hex_coord, VALID_HEX_PATTERN, "hex_coordinate")
        
        # Additional validation for valid board positions
        match = re.match(r'^([A-Z]{1,2})(\d+)$', hex_coord)
        if match:
            col_str, row_str = match.groups()
            row = int(row_str)
            
            # Check if column is valid
            if len(col_str) == 1:
                col_num = ord(col_str) - ord('A') + 1
                max_row = 21 if col_num % 2 == 1 else 20
            elif len(col_str) == 2 and col_str[0] == col_str[1]:
                if col_str not in ['AA', 'BB', 'CC', 'DD', 'EE', 'FF']:
                    raise InvalidInputError(f"Invalid column: {col_str}")
                col_num = ord(col_str[0]) - ord('A') + 27
                max_row = 21 if col_num % 2 == 1 else 20
            else:
                raise InvalidInputError(f"Invalid hex format: {hex_coord}")
            
            if not 1 <= row <= max_row:
                raise InvalidInputError(
                    f"Invalid row {row} for column {col_str}, max is {max_row}"
                )
    
    @staticmethod
    def validate_ship_count(count: int, ship_type: ShipType) -> None:
        """Validate ship count."""
        GameValidator.validate_type(count, int, "ship_count")
        GameValidator.validate_positive(count, "ship_count")
        
        # Additional validation based on ship type
        max_reasonable = 1000  # Reasonable upper limit
        GameValidator.validate_range(count, 1, max_reasonable, "ship_count")
    
    @staticmethod
    def validate_population(population: int) -> None:
        """Validate population amount (in millions)."""
        GameValidator.validate_type(population, int, "population")
        GameValidator.validate_non_negative(population, "population")
        
        # Maximum reasonable population
        max_population = 10000  # 10 billion (10,000 million)
        GameValidator.validate_range(population, 0, max_population, "population")
    
    @staticmethod
    def validate_industrial_points(ip: int) -> None:
        """Validate industrial points amount."""
        GameValidator.validate_type(ip, int, "industrial_points")
        GameValidator.validate_non_negative(ip, "industrial_points")
        
        # Maximum reasonable IP
        max_ip = 100000
        GameValidator.validate_range(ip, 0, max_ip, "industrial_points")
    
    @staticmethod
    def validate_planet_capacity(capacity: int, planet_type: PlanetType) -> None:
        """Validate planet population capacity."""
        GameValidator.validate_type(capacity, int, "planet_capacity")
        GameValidator.validate_positive(capacity, "planet_capacity")
        
        # Validate capacity makes sense for planet type
        if planet_type == PlanetType.BARREN and capacity > 20:
            raise ConstraintViolationError(
                f"Barren planets typically have capacity <= 20, got {capacity}"
            )
        elif planet_type == PlanetType.MINIMAL_TERRAN and capacity > 40:
            raise ConstraintViolationError(
                f"Minimal-Terran planets typically have capacity <= 40, got {capacity}"
            )
        elif planet_type == PlanetType.TERRAN and capacity > 80:
            raise ConstraintViolationError(
                f"Terran planets typically have capacity <= 80, got {capacity}"
            )
    
    @staticmethod
    def validate_game_name(name: str) -> None:
        """Validate game name."""
        GameValidator.validate_type(name, str, "game_name")
        GameValidator.validate_string_length(name, MAX_GAME_NAME_LENGTH, 1, "game_name")
        
        # Check for invalid characters
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', name):
            raise InvalidInputError(
                "Game name can only contain letters, numbers, spaces, underscores, and hyphens"
            )
    
    @staticmethod
    def validate_player_name(name: str) -> None:
        """Validate player name."""
        GameValidator.validate_type(name, str, "player_name")
        GameValidator.validate_string_length(name, MAX_PLAYER_NAME_LENGTH, 1, "player_name")
        
        # Check for invalid characters
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', name):
            raise InvalidInputError(
                "Player name can only contain letters, numbers, spaces, underscores, and hyphens"
            )


class ActionValidator(Validator):
    """Validator for game action inputs."""
    
    @staticmethod
    def validate_movement_distance(distance: int, max_speed: int) -> None:
        """Validate movement distance."""
        GameValidator.validate_type(distance, int, "movement_distance")
        GameValidator.validate_range(distance, 1, max_speed, "movement_distance")
    
    @staticmethod
    def validate_fleet_composition(fleet_data: Dict[ShipType, int]) -> None:
        """Validate fleet composition."""
        GameValidator.validate_type(fleet_data, dict, "fleet_composition")
        
        if not fleet_data:
            raise ConstraintViolationError("Fleet cannot be empty")
        
        total_ships = 0
        for ship_type, count in fleet_data.items():
            GameValidator.validate_enum(ship_type, ShipType, "ship_type")
            GameValidator.validate_ship_count(count, ship_type)
            total_ships += count
        
        if total_ships == 0:
            raise ConstraintViolationError("Fleet must contain at least one ship")
        
        # Reasonable fleet size limit
        max_fleet_size = 1000
        if total_ships > max_fleet_size:
            raise ConstraintViolationError(
                f"Fleet size {total_ships} exceeds maximum {max_fleet_size}"
            )
    
    @staticmethod
    def validate_technology_purchase(technology: Technology, cost: int, available_ip: int) -> None:
        """Validate technology purchase."""
        GameValidator.validate_enum(technology, Technology, "technology")
        GameValidator.validate_positive(cost, "technology_cost")
        GameValidator.validate_non_negative(available_ip, "available_ip")
        
        if cost > available_ip:
            raise ConstraintViolationError(
                f"Insufficient IP for {technology.value}: need {cost}, have {available_ip}"
            )
    
    @staticmethod
    def validate_production_spending(spending_plan: Dict[str, int], total_ip: int) -> None:
        """Validate production spending plan."""
        GameValidator.validate_type(spending_plan, dict, "spending_plan")
        GameValidator.validate_non_negative(total_ip, "total_ip")
        
        total_spent = sum(spending_plan.values())
        if total_spent > total_ip:
            raise ConstraintViolationError(
                f"Total spending {total_spent} exceeds available IP {total_ip}"
            )
        
        for item, amount in spending_plan.items():
            GameValidator.validate_type(item, str, "spending_item")
            GameValidator.validate_non_negative(amount, f"spending_amount_{item}")


class ConfigValidator(Validator):
    """Validator for configuration and settings."""
    
    @staticmethod
    def validate_simulation_config(config: Dict[str, Any]) -> None:
        """Validate simulation configuration."""
        required_fields = ["mode", "debug_logging", "save_snapshots"]
        for field in required_fields:
            if field not in config:
                raise InvalidInputError(f"Missing required config field: {field}")
        
        # Validate specific fields
        if "max_turns" in config:
            GameValidator.validate_range(config["max_turns"], 1, 200, "max_turns")
        
        if "iterations" in config:
            GameValidator.validate_range(config["iterations"], 1, 100000, "iterations")
        
        if "random_seed" in config and config["random_seed"] is not None:
            GameValidator.validate_type(config["random_seed"], int, "random_seed")
    
    @staticmethod
    def validate_strategy_assignment(assignments: Dict[int, str]) -> None:
        """Validate AI strategy assignments."""
        GameValidator.validate_type(assignments, dict, "strategy_assignments")
        
        valid_strategies = ["expansionist", "warlord", "technophile", "balanced"]
        
        for player_id, strategy in assignments.items():
            GameValidator.validate_player_id(player_id)
            if strategy not in valid_strategies:
                raise InvalidInputError(
                    f"Invalid strategy '{strategy}' for player {player_id}. "
                    f"Valid strategies: {valid_strategies}"
                )


class ScenarioValidator(Validator):
    """Validator for scenario configurations."""
    
    @staticmethod
    def validate_combat_scenario(params: Dict[str, Any]) -> None:
        """Validate combat scenario parameters."""
        required = ["location", "attacker_id", "defender_id"]
        for field in required:
            if field not in params:
                raise InvalidInputError(f"Combat scenario missing required field: {field}")
        
        GameValidator.validate_hex_coordinate(params["location"])
        GameValidator.validate_player_id(params["attacker_id"])
        GameValidator.validate_player_id(params["defender_id"])
        
        if params["attacker_id"] == params["defender_id"]:
            raise ConstraintViolationError("Attacker and defender must be different players")
    
    @staticmethod
    def validate_production_scenario(params: Dict[str, Any]) -> None:
        """Validate production scenario parameters."""
        required = ["player_id"]
        for field in required:
            if field not in params:
                raise InvalidInputError(f"Production scenario missing required field: {field}")
        
        GameValidator.validate_player_id(params["player_id"])
        
        if "spending_strategy" in params:
            ActionValidator.validate_production_spending(
                params["spending_strategy"], 
                params.get("available_ip", 1000)  # Default for validation
            )
        
        if "turns" in params:
            GameValidator.validate_range(params["turns"], 1, 44, "scenario_turns")


# Convenience functions for common validations
def validate_game_setup(player_count: int, player_names: List[str], 
                       strategies: List[str], game_name: str = "Game") -> None:
    """Validate complete game setup."""
    GameValidator.validate_player_count(player_count)
    GameValidator.validate_game_name(game_name)
    
    if len(player_names) != player_count:
        raise ConstraintViolationError(
            f"Number of player names ({len(player_names)}) must match player count ({player_count})"
        )
    
    if len(strategies) != player_count:
        raise ConstraintViolationError(
            f"Number of strategies ({len(strategies)}) must match player count ({player_count})"
        )
    
    for name in player_names:
        GameValidator.validate_player_name(name)
    
    valid_strategies = ["expansionist", "warlord", "technophile", "balanced"]
    for strategy in strategies:
        if strategy not in valid_strategies:
            raise InvalidInputError(f"Invalid strategy: {strategy}")


def validate_starting_fleet(fleet: Dict[ShipType, int]) -> None:
    """Validate starting fleet composition."""
    ActionValidator.validate_fleet_composition(fleet)
    
    # Validate against expected starting fleet
    for ship_type, expected_count in STARTING_FLEET.items():
        if fleet.get(ship_type, 0) != expected_count:
            raise ConstraintViolationError(
                f"Starting fleet {ship_type.value} count should be {expected_count}, "
                f"got {fleet.get(ship_type, 0)}"
            )


def validate_file_path(file_path: str, must_exist: bool = False) -> None:
    """Validate file path."""
    Validator.validate_type(file_path, str, "file_path")
    
    if not file_path.strip():
        raise InvalidInputError("File path cannot be empty")
    
    # Basic path validation
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    if any(char in file_path for char in invalid_chars):
        raise InvalidInputError(f"File path contains invalid characters: {file_path}")
    
    if must_exist:
        import os
        if not os.path.exists(file_path):
            raise InvalidInputError(f"File does not exist: {file_path}")


def safe_validate(validator_func: Callable, *args, **kwargs) -> bool:
    """Safely run validation, returning True if valid, False if not."""
    try:
        validator_func(*args, **kwargs)
        return True
    except ValidationError:
        return False