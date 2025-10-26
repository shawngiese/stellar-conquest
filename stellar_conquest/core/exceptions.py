"""Custom exceptions for Stellar Conquest simulator."""


class StellarConquestError(Exception):
    """Base exception for all Stellar Conquest simulator errors."""
    
    def __init__(self, message: str, error_code: str = None, context: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self):
        base_msg = self.message
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_msg = f"{base_msg} (Context: {context_str})"
        return base_msg


# Game State Exceptions
class GameStateError(StellarConquestError):
    """Errors related to game state management."""
    pass


class InvalidGameStateError(GameStateError):
    """Game state is in an invalid condition."""
    pass


class GameAlreadyEndedError(GameStateError):
    """Attempted action on a game that has already ended."""
    pass


class InvalidTurnError(GameStateError):
    """Invalid turn or turn sequence operation."""
    pass


class InvalidPhaseError(GameStateError):
    """Action attempted in wrong turn phase."""
    pass


# Player Exceptions
class PlayerError(StellarConquestError):
    """Errors related to player operations."""
    pass


class InvalidPlayerError(PlayerError):
    """Invalid player ID or player state."""
    pass


class InsufficientResourcesError(PlayerError):
    """Player lacks required resources for action."""
    pass


class TechnologyNotAvailableError(PlayerError):
    """Required technology not researched."""
    pass


class PlayerNotActiveError(PlayerError):
    """Action attempted by non-active player."""
    pass


# Action Exceptions
class ActionError(StellarConquestError):
    """Errors related to action execution."""
    pass


class InvalidActionError(ActionError):
    """Action is invalid for current game state."""
    pass


class ActionValidationError(ActionError):
    """Action failed validation checks."""
    pass


class ActionExecutionError(ActionError):
    """Error during action execution."""
    pass


class ActionSequenceError(ActionError):
    """Invalid sequence of actions."""
    pass


# Movement Exceptions
class MovementError(ActionError):
    """Errors related to ship movement."""
    pass


class InvalidDestinationError(MovementError):
    """Invalid movement destination."""
    pass


class RangeExceededError(MovementError):
    """Movement exceeds ship range."""
    pass


class PathBlockedError(MovementError):
    """Movement path is blocked."""
    pass


class CommandPostRangeError(MovementError):
    """Ship moved beyond command post range."""
    pass


class CommunicationRangeError(MovementError):
    """Ship communication beyond range."""
    pass


# Combat Exceptions
class CombatError(StellarConquestError):
    """Errors related to combat resolution."""
    pass


class InvalidCombatError(CombatError):
    """Combat cannot be initiated."""
    pass


class CombatResolutionError(CombatError):
    """Error during combat resolution."""
    pass


class InvalidTargetError(CombatError):
    """Invalid combat target."""
    pass


class NoWarshipsError(CombatError):
    """No warships available for combat."""
    pass


# Exploration Exceptions
class ExplorationError(StellarConquestError):
    """Errors related to exploration."""
    pass


class InvalidExplorationTargetError(ExplorationError):
    """Invalid exploration target."""
    pass


class ExplorationRiskError(ExplorationError):
    """Error during exploration risk resolution."""
    pass


class StarCardError(ExplorationError):
    """Error with star card operations."""
    pass


class SystemAlreadyExploredError(ExplorationError):
    """System has already been explored."""
    pass


# Colonization Exceptions
class ColonizationError(StellarConquestError):
    """Errors related to colonization."""
    pass


class InvalidColonizationError(ColonizationError):
    """Colonization is not possible."""
    pass


class PlanetCapacityExceededError(ColonizationError):
    """Planet population capacity exceeded."""
    pass


class PlanetAlreadyColonizedError(ColonizationError):
    """Planet already has a colony."""
    pass


class InsufficientTransportsError(ColonizationError):
    """Not enough colony transports available."""
    pass


class BarrenPlanetError(ColonizationError):
    """Cannot colonize barren planet without CET."""
    pass


# Production Exceptions
class ProductionError(StellarConquestError):
    """Errors related to production."""
    pass


class InvalidProductionError(ProductionError):
    """Production action is invalid."""
    pass


class InsufficientIndustrialPointsError(ProductionError):
    """Not enough industrial points for purchase."""
    pass


class ProductionCapacityError(ProductionError):
    """Production capacity exceeded."""
    pass


class InvalidPurchaseError(ProductionError):
    """Invalid item purchase."""
    pass


# Galaxy/Map Exceptions
class GalaxyError(StellarConquestError):
    """Errors related to galaxy/map operations."""
    pass


class InvalidHexError(GalaxyError):
    """Invalid hex coordinate."""
    pass


class InvalidStarSystemError(GalaxyError):
    """Invalid star system."""
    pass


class PathfindingError(GalaxyError):
    """Error in pathfinding algorithm."""
    pass


class InvalidDistanceError(GalaxyError):
    """Invalid distance calculation."""
    pass


# Fleet/Ship Exceptions
class FleetError(StellarConquestError):
    """Errors related to fleet operations."""
    pass


class InvalidFleetError(FleetError):
    """Invalid fleet configuration."""
    pass


class EmptyFleetError(FleetError):
    """Fleet has no ships."""
    pass


class ShipNotFoundError(FleetError):
    """Ship type not found in fleet."""
    pass


class FleetSplitError(FleetError):
    """Error splitting fleet."""
    pass


class TaskForceError(FleetError):
    """Error with task force operations."""
    pass


# AI/Strategy Exceptions
class AIError(StellarConquestError):
    """Errors related to AI decision making."""
    pass


class InvalidStrategyError(AIError):
    """Invalid AI strategy."""
    pass


class StrategyExecutionError(AIError):
    """Error executing AI strategy."""
    pass


class DecisionEngineError(AIError):
    """Error in decision engine."""
    pass


# Simulation Exceptions
class SimulationError(StellarConquestError):
    """Errors related to simulation execution."""
    pass


class SimulationConfigError(SimulationError):
    """Invalid simulation configuration."""
    pass


class SimulationExecutionError(SimulationError):
    """Error during simulation execution."""
    pass


class MonteCarloError(SimulationError):
    """Error in Monte Carlo simulation."""
    pass


# Scenario Exceptions
class ScenarioError(StellarConquestError):
    """Errors related to scenario analysis."""
    pass


class InvalidScenarioError(ScenarioError):
    """Invalid scenario configuration."""
    pass


class ScenarioExecutionError(ScenarioError):
    """Error executing scenario."""
    pass


class ScenarioDataError(ScenarioError):
    """Error with scenario data."""
    pass


# Data/Configuration Exceptions
class DataError(StellarConquestError):
    """Errors related to game data."""
    pass


class InvalidConfigurationError(DataError):
    """Invalid configuration data."""
    pass


class DataLoadingError(DataError):
    """Error loading game data."""
    pass


class DataValidationError(DataError):
    """Game data validation failed."""
    pass


class StarCardDataError(DataError):
    """Error with star card data."""
    pass


class TechnologyDataError(DataError):
    """Error with technology data."""
    pass


# File I/O Exceptions
class FileOperationError(StellarConquestError):
    """Errors related to file operations."""
    pass


class SaveGameError(FileOperationError):
    """Error saving game state."""
    pass


class LoadGameError(FileOperationError):
    """Error loading game state."""
    pass


class InvalidFileFormatError(FileOperationError):
    """Invalid file format."""
    pass


class FileNotFoundError(FileOperationError):
    """Game file not found."""
    pass


# Validation Exceptions
class ValidationError(StellarConquestError):
    """Errors related to input validation."""
    pass


class InvalidInputError(ValidationError):
    """Invalid input provided."""
    pass


class RangeValidationError(ValidationError):
    """Value outside valid range."""
    pass


class TypeValidationError(ValidationError):
    """Invalid type provided."""
    pass


class ConstraintViolationError(ValidationError):
    """Input violates constraints."""
    pass


# Analysis Exceptions
class AnalysisError(StellarConquestError):
    """Errors related to game analysis."""
    pass


class StatisticalAnalysisError(AnalysisError):
    """Error in statistical analysis."""
    pass


class ReportGenerationError(AnalysisError):
    """Error generating analysis report."""
    pass


class DataExportError(AnalysisError):
    """Error exporting analysis data."""
    pass


# Utility functions for exception handling
def raise_if_invalid_player(player_id: int, valid_players: list, context: str = ""):
    """Raise InvalidPlayerError if player ID is not valid."""
    if player_id not in valid_players:
        raise InvalidPlayerError(
            f"Player {player_id} is not valid",
            error_code="INVALID_PLAYER",
            context={"player_id": player_id, "valid_players": valid_players, "context": context}
        )


def raise_if_game_ended(game_state, action_name: str = "action"):
    """Raise GameAlreadyEndedError if game has ended."""
    if game_state.is_game_over:
        raise GameAlreadyEndedError(
            f"Cannot perform {action_name} - game has already ended",
            error_code="GAME_ENDED",
            context={"action": action_name, "winner": game_state.winner_id}
        )


def raise_if_insufficient_resources(required: int, available: int, resource_type: str):
    """Raise InsufficientResourcesError if not enough resources."""
    if available < required:
        raise InsufficientResourcesError(
            f"Insufficient {resource_type}: need {required}, have {available}",
            error_code="INSUFFICIENT_RESOURCES",
            context={"required": required, "available": available, "resource_type": resource_type}
        )


def raise_if_invalid_hex(hex_coord: str, valid_pattern: str = r'^[A-Z]+\d+$'):
    """Raise InvalidHexError if hex coordinate is invalid."""
    import re
    if not re.match(valid_pattern, hex_coord):
        raise InvalidHexError(
            f"Invalid hex coordinate: {hex_coord}",
            error_code="INVALID_HEX",
            context={"hex_coord": hex_coord, "pattern": valid_pattern}
        )


def raise_if_wrong_phase(current_phase: str, required_phase: str, action_name: str):
    """Raise InvalidPhaseError if in wrong turn phase."""
    if current_phase != required_phase:
        raise InvalidPhaseError(
            f"Cannot perform {action_name} in {current_phase} phase, requires {required_phase}",
            error_code="WRONG_PHASE",
            context={"current_phase": current_phase, "required_phase": required_phase, "action": action_name}
        )