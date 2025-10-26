"""Core enumerations for Stellar Conquest simulator."""

from enum import Enum, IntEnum, auto


class ShipType(Enum):
    """Types of ships in Stellar Conquest."""
    SCOUT = "scout"
    COLONY_TRANSPORT = "colony_transport"
    CORVETTE = "corvette"
    FIGHTER = "fighter"
    DEATH_STAR = "death_star"


class PlanetType(Enum):
    """Types of planets that can be colonized."""
    TERRAN = "terran"
    SUB_TERRAN = "sub_terran"
    MINIMAL_TERRAN = "minimal_terran"
    BARREN = "barren"


class StarColor(Enum):
    """Star colors corresponding to spectral classes."""
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


class PlayStyle(Enum):
    """Different AI play styles."""
    EXPANSIONIST = "expansionist"
    WARLORD = "warlord"
    TECHNOPHILE = "technophile"
    BALANCED = "balanced"


class Technology(Enum):
    """Available technologies in the game."""
    # Ship Speed Technologies
    SPEED_3_HEX = "speed_3_hex"
    SPEED_4_HEX = "speed_4_hex"
    SPEED_5_HEX = "speed_5_hex"
    SPEED_6_HEX = "speed_6_hex"
    SPEED_7_HEX = "speed_7_hex"
    SPEED_8_HEX = "speed_8_hex"
    
    # Weapons Technologies
    MISSILE_BASE = "missile_base"
    FIGHTER_SHIP = "fighter_ship"
    ADVANCED_MISSILE_BASE = "advanced_missile_base"
    DEATH_STAR = "death_star"
    IMPROVED_SHIP_WEAPONRY = "improved_ship_weaponry"
    PLANET_SHIELD = "planet_shield"
    
    # General Technologies
    CONTROLLED_ENVIRONMENT_TECH = "controlled_environment_tech"
    INDUSTRIAL_TECHNOLOGY = "industrial_technology"
    IMPROVED_INDUSTRIAL_TECH = "improved_industrial_tech"
    UNLIMITED_SHIP_RANGE = "unlimited_ship_range"
    UNLIMITED_SHIP_COMMUNICATION = "unlimited_ship_communication"
    ROBOTIC_INDUSTRY = "robotic_industry"


class TechnologyLevel(IntEnum):
    """Technology research levels."""
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


class GamePhase(Enum):
    """Game phases including setup and turn phases."""
    SETUP = "setup"
    MOVEMENT = "movement"
    EXPLORATION = "exploration"
    COLONIZATION = "colonization"
    COMBAT = "combat"
    PRODUCTION = "production"


class TurnPhase(Enum):
    """Different phases within a single turn."""
    MOVEMENT = "movement"
    EXPLORATION = "exploration"
    COMBAT = "combat"
    COLONIZATION = "colonization"
    PRODUCTION = "production"


class ActionResult(Enum):
    """Result types for action execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    INVALID = "invalid"
    PARTIAL = "partial"


class SimulationMode(Enum):
    """Different simulation execution modes."""
    STEP_BY_STEP = "step_by_step"
    AUTOMATED = "automated"
    DEBUG = "debug"
    MONTE_CARLO = "monte_carlo"


class ScenarioType(Enum):
    """Types of scenarios that can be run."""
    COMBAT_SIMULATION = "combat_simulation"
    PRODUCTION_ANALYSIS = "production_analysis"
    EXPANSION_RACE = "expansion_race"
    STRATEGIC_DECISION = "strategic_decision"
    FULL_GAME_FORK = "full_game_fork"


class Priority(IntEnum):
    """Priority levels for different objectives."""
    MINIMAL = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


class CombatResult(Enum):
    """Results of combat resolution."""
    ATTACKER_VICTORY = "attacker_victory"
    DEFENDER_VICTORY = "defender_victory"
    MUTUAL_DESTRUCTION = "mutual_destruction"
    ATTACKER_RETREAT = "attacker_retreat"
    DEFENDER_RETREAT = "defender_retreat"


class ColonyStatus(Enum):
    """Status of a colony."""
    ACTIVE = "active"
    CONQUERED = "conquered"
    BESIEGED = "besieged"
    ABANDONED = "abandoned"


class FleetStatus(Enum):
    """Status of a fleet."""
    ACTIVE = "active"
    IN_TRANSIT = "in_transit"
    IN_COMBAT = "in_combat"
    TASK_FORCE = "task_force"


class ExplorationRisk(Enum):
    """Types of exploration risks."""
    NONE = "none"
    SHIP_DESTRUCTION = "ship_destruction"
    NAVIGATION_HAZARD = "navigation_hazard"


class ResourceType(Enum):
    """Types of resources in the game."""
    POPULATION = "population"
    INDUSTRIAL_POINTS = "industrial_points"
    RESEARCH_POINTS = "research_points"


class VictoryCondition(Enum):
    """Types of victory conditions."""
    TURN_LIMIT = "turn_limit"
    TOTAL_CONQUEST = "total_conquest"
    ELIMINATION = "elimination"


class LogLevel(Enum):
    """Logging levels for game events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PlayerAction(Enum):
    """Types of player actions."""
    MOVE_SHIPS = "move_ships"
    EXPLORE_SYSTEM = "explore_system"
    ATTACK_SHIPS = "attack_ships"
    ATTACK_COLONY = "attack_colony"
    COLONIZE_PLANET = "colonize_planet"
    BUILD_SHIPS = "build_ships"
    BUILD_DEFENSES = "build_defenses"
    RESEARCH_TECHNOLOGY = "research_technology"
    TRANSFER_POPULATION = "transfer_population"


class TerrainType(Enum):
    """Types of terrain on the game board."""
    EMPTY_SPACE = "empty_space"
    STAR_SYSTEM = "star_system"
    GAS_CLOUD = "gas_cloud"
    ENTRY_HEX = "entry_hex"


class DifficultyLevel(Enum):
    """AI difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class GameSpeed(Enum):
    """Game execution speed settings."""
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"
    INSTANT = "instant"


class AnalysisType(Enum):
    """Types of game analysis."""
    WIN_RATE = "win_rate"
    STRATEGY_EFFECTIVENESS = "strategy_effectiveness"
    OPTIMAL_OPENING = "optimal_opening"
    DECISION_TREE = "decision_tree"
    STATISTICAL_SUMMARY = "statistical_summary"


class ExportFormat(Enum):
    """Export formats for game data."""
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    PDF = "pdf"
    XML = "xml"


# Utility functions for enum operations
def get_ship_combat_types():
    """Get ship types that can participate in combat."""
    return [ShipType.CORVETTE, ShipType.FIGHTER, ShipType.DEATH_STAR]


def get_unarmed_ship_types():
    """Get ship types vulnerable to exploration risks."""
    return [ShipType.SCOUT, ShipType.COLONY_TRANSPORT]


def get_habitable_planet_types():
    """Get planet types that can support colonies."""
    return [PlanetType.TERRAN, PlanetType.SUB_TERRAN, PlanetType.MINIMAL_TERRAN]


def get_growth_supporting_planets():
    """Get planet types that support population growth."""
    return [PlanetType.TERRAN, PlanetType.SUB_TERRAN]


def get_speed_technologies():
    """Get all ship speed technologies in order."""
    return [
        Technology.SPEED_3_HEX,
        Technology.SPEED_4_HEX,
        Technology.SPEED_5_HEX,
        Technology.SPEED_6_HEX,
        Technology.SPEED_7_HEX,
        Technology.SPEED_8_HEX
    ]


def get_weapon_technologies():
    """Get all weapon-related technologies."""
    return [
        Technology.MISSILE_BASE,
        Technology.FIGHTER_SHIP,
        Technology.ADVANCED_MISSILE_BASE,
        Technology.DEATH_STAR,
        Technology.IMPROVED_SHIP_WEAPONRY,
        Technology.PLANET_SHIELD
    ]


def get_industrial_technologies():
    """Get all industrial/economic technologies."""
    return [
        Technology.CONTROLLED_ENVIRONMENT_TECH,
        Technology.INDUSTRIAL_TECHNOLOGY,
        Technology.IMPROVED_INDUSTRIAL_TECH,
        Technology.UNLIMITED_SHIP_RANGE,
        Technology.UNLIMITED_SHIP_COMMUNICATION,
        Technology.ROBOTIC_INDUSTRY
    ]