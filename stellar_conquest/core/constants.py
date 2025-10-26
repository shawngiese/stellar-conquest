"""Game constants for Stellar Conquest simulator."""

from .enums import ShipType, Technology, PlanetType, StarColor


# Game Configuration Constants
MAX_PLAYERS = 4
MIN_PLAYERS = 2
MAX_TURNS = 44
STARTING_VICTORY_POINTS_TARGET = 100
PRODUCTION_TURN_INTERVAL = 4  # Production occurs every 4th turn
HEX_DISTANCE_UNIT = 0.125  # Light-years per hex (from rules)

# Starting Fleet Composition
STARTING_FLEET = {
    ShipType.SCOUT: 4,
    ShipType.CORVETTE: 4,
    ShipType.COLONY_TRANSPORT: 35
}

# Starting Bonus Industrial Points
STARTING_BONUS_IP = 25

# Ship Movement and Range
DEFAULT_SHIP_SPEED = 2  # Hexes per turn
COMMAND_POST_RANGE = 8  # Maximum distance from command post
GAS_CLOUD_SPEED = 1     # Speed through gas clouds

# Population and Growth
TERRAN_GROWTH_RATE = 5     # 1 growth per 5 million population
SUB_TERRAN_GROWTH_RATE = 10 # 1 growth per 10 million population
POPULATION_UNIT = 1_000_000 # Population counted in millions

# Industrial Production
IP_PER_POPULATION = 1      # Industrial points per million population
IP_PER_FACTORY = 1         # Industrial points per factory
MINERAL_RICH_MULTIPLIER = 2 # Production multiplier for mineral-rich planets

# Population Bonus Calculations
BONUS_BASE = 3_000_000     # Base 3 million for bonus calculation
BONUS_RATIO = 3            # 3 emigrants = 1 bonus population

# Ship Costs (Industrial Points)
SHIP_COSTS = {
    ShipType.COLONY_TRANSPORT: 1,
    ShipType.SCOUT: 3,
    ShipType.CORVETTE: 8,
    ShipType.FIGHTER: 20,
    ShipType.DEATH_STAR: 40
}

# Building Costs (Industrial Points)
BUILDING_COSTS = {
    "factory": 4,
    "robotic_factory": 3,
    "missile_base": 4,
    "advanced_missile_base": 10,
    "planet_shield": 30
}

# Technology Costs (Industrial Points)
TECHNOLOGY_COSTS = {
    # Ship Speed Technologies
    Technology.SPEED_3_HEX: 15,
    Technology.SPEED_4_HEX: 40,
    Technology.SPEED_5_HEX: 55,
    Technology.SPEED_6_HEX: 65,
    Technology.SPEED_7_HEX: 75,
    Technology.SPEED_8_HEX: 80,
    
    # Weapons Technologies
    Technology.MISSILE_BASE: 25,
    Technology.FIGHTER_SHIP: 35,
    Technology.ADVANCED_MISSILE_BASE: 55,
    Technology.DEATH_STAR: 90,
    Technology.IMPROVED_SHIP_WEAPONRY: 100,
    Technology.PLANET_SHIELD: 130,
    
    # General Technologies
    Technology.CONTROLLED_ENVIRONMENT_TECH: 25,
    Technology.INDUSTRIAL_TECHNOLOGY: 25,
    Technology.IMPROVED_INDUSTRIAL_TECH: 55,
    Technology.UNLIMITED_SHIP_RANGE: 60,
    Technology.UNLIMITED_SHIP_COMMUNICATION: 70,
    Technology.ROBOTIC_INDUSTRY: 100
}

# Technology Prerequisites and Reduced Costs
TECHNOLOGY_PREREQUISITES = {
    Technology.SPEED_4_HEX: (Technology.SPEED_3_HEX, 30),
    Technology.SPEED_5_HEX: (Technology.SPEED_4_HEX, 40),
    Technology.SPEED_6_HEX: (Technology.SPEED_5_HEX, 50),
    Technology.SPEED_7_HEX: (Technology.SPEED_6_HEX, 60),
    Technology.SPEED_8_HEX: (Technology.SPEED_7_HEX, 70),
    Technology.ADVANCED_MISSILE_BASE: (Technology.MISSILE_BASE, 40),
    Technology.DEATH_STAR: (Technology.FIGHTER_SHIP, 75),
    Technology.IMPROVED_INDUSTRIAL_TECH: (Technology.INDUSTRIAL_TECHNOLOGY, 40),
    Technology.UNLIMITED_SHIP_RANGE: (Technology.SPEED_5_HEX, 40),  # Requires 5+ hex speed
    Technology.ROBOTIC_INDUSTRY: (Technology.INDUSTRIAL_TECHNOLOGY, 85)
}

# Victory Points
VICTORY_POINTS = {
    PlanetType.TERRAN: 3,
    PlanetType.SUB_TERRAN: 1,
    PlanetType.MINIMAL_TERRAN: 0,
    PlanetType.BARREN: 0
}

# Combat Values and Attack Tables
COMBAT_VALUES = {
    "scout": {"combat_strength": 0, "can_attack": False},
    "colony_transport": {"combat_strength": 0, "can_attack": False},
    "corvette": {"combat_strength": 1, "can_attack": True},
    "fighter": {"combat_strength": 2, "can_attack": True},
    "death_star": {"combat_strength": 4, "can_attack": True},
    "missile_base": {"combat_strength": 1, "can_attack": True},
    "advanced_missile_base": {"combat_strength": 2, "can_attack": True}
}

# Attack Table (attacker vs defender, die roll needed for kill)
ATTACK_TABLE = {
    # Format: (attacker, defender): (dice_count, success_range)
    ("corvette", "scout"): (1, [1, 2, 3, 4]),
    ("corvette", "colony_transport"): (1, [1, 2, 3, 4]),
    ("corvette", "corvette"): (1, [1]),
    ("corvette", "missile_base"): (1, [1]),
    ("corvette", "fighter"): (2, [10]),
    ("corvette", "advanced_missile_base"): (2, [10]),
    ("corvette", "death_star"): (1, []),  # No effect
    
    ("fighter", "scout"): (1, [1, 2, 3, 4, 5]),
    ("fighter", "colony_transport"): (1, [1, 2, 3, 4, 5]),
    ("fighter", "corvette"): (1, [1, 2]),
    ("fighter", "missile_base"): (1, [1, 2]),
    ("fighter", "fighter"): (1, [1]),
    ("fighter", "advanced_missile_base"): (1, [1]),
    ("fighter", "death_star"): (2, [10]),
    
    ("death_star", "scout"): (1, [1, 2, 3, 4, 5, 6]),  # Automatic
    ("death_star", "colony_transport"): (1, [1, 2, 3, 4, 5, 6]),  # Automatic
    ("death_star", "corvette"): (1, [1, 2, 3, 4]),
    ("death_star", "missile_base"): (1, [1, 2, 3, 4]),
    ("death_star", "fighter"): (1, [1, 2, 3]),
    ("death_star", "advanced_missile_base"): (1, [1, 2, 3]),
    ("death_star", "death_star"): (1, [1, 2])
}

# Colony Destruction Rates (population destroyed per turn per ship)
DESTRUCTION_RATES = {
    ShipType.CORVETTE: 1_000_000,  # 1 million per turn
    ShipType.FIGHTER: 3_000_000,   # 3 million per turn
    ShipType.DEATH_STAR: 5_000_000 # 5 million per turn
}

# Exploration Risk
EXPLORATION_RISK_CHANCE = 1/6  # 1 in 6 chance of ship destruction

# Map Board Configuration  
BOARD_SIZE = 14  # 14x14 hex grid (simplified)
HEX_GRID_SIZE = 14
BOARD_DIMENSIONS = {
    "columns": 32,  # A through Z, then AA through FF
    "odd_column_rows": 21,    # A, C, E, G, I, K, M, O, Q, S, U, W, Y, AA, CC, EE
    "even_column_rows": 20,   # B, D, F, H, J, L, N, P, R, T, V, X, Z, BB, DD, FF
}

# Entry Hexes (corner positions for player starting locations)
ENTRY_HEXES = {
    1: "A1",    # Top-left
    2: "A21",   # Bottom-left  
    3: "FF1",   # Top-right
    4: "FF20"   # Bottom-right
}

# Gas Cloud Hexes (obstacles on the board) - from rules.txt
GAS_CLOUD_HEXES = {
    'A10', 'A11', 'A12', 'A13', 'B10', 'B11', 'B12', 'C11', 
    'I7', 'I8', 'I13', 'I14', 'J6', 'J7', 'J8', 'J12', 'J13', 'J14', 
    'K6', 'K7', 'K14', 'K15', 'K16', 'L5', 'L15', 'O1', 'O20', 
    'P1', 'P19', 'P20', 'Q1', 'Q2', 'Q20', 'R1', 'R2', 'R19', 
    'U6', 'V5', 'V6', 'V14', 'V15', 'W6', 'W7', 'W15', 
    'X6', 'X7', 'X8', 'X13', 'X14', 'Y12', 'Y13', 'Y14',
    'DD7', 'EE8', 'EE9', 'EE11', 'FF8', 'FF9', 'FF10', 'FF11'
}

# Fixed Star Locations (from rules.txt)
FIXED_STAR_LOCATIONS = {
    "AA19": {"color": "yellow", "starname": "Scorpii"},
    "B18": {"color": "red", "starname": "Lalande"},
    "E17": {"color": "yellow", "starname": "Ceti"},
    "H18": {"color": "red", "starname": "Mira"},
    "I16": {"color": "orange", "starname": "Rastaban"},
    "D13": {"color": "red", "starname": "Luyten"},
    "L18": {"color": "yellow", "starname": "Alcor"},
    "J15": {"color": "blue", "starname": "Pherda"},
    "H12": {"color": "lime", "starname": "Eridani"},
    "B11": {"color": "blue", "starname": "Sirius"},
    "F9": {"color": "yellow", "starname": "Diphda"},
    "E7": {"color": "red", "starname": "Kapetyn"},
    "D4": {"color": "orange", "starname": "Indi"},
    "G5": {"color": "yellow", "starname": "Canis"},
    "H2": {"color": "red", "starname": "Ophiuchi"},
    "I10": {"color": "red", "starname": "Ross"},
    "I8": {"color": "blue", "starname": "Deneb"},
    "L3": {"color": "red", "starname": "Cephei"},
    "L6": {"color": "lime", "starname": "Mirfak"},
    "L10": {"color": "orange", "starname": "Alphard"},
    "L13": {"color": "yellow", "starname": "Lyrae"},
    "P18": {"color": "orange", "starname": "Hydrae"},
    "Q20": {"color": "blue", "starname": "Zosca"},
    "O16": {"color": "lime", "starname": "Sadir"},
    "O13": {"color": "red", "starname": "Lacalle"},
    "N8": {"color": "yellow", "starname": "Capella"},
    "N6": {"color": "orange", "starname": "Kochab"},
    "O4": {"color": "yellow", "starname": "Schedar"},
    "Q2": {"color": "blue", "starname": "Mizar"},
    "R6": {"color": "lime", "starname": "Caph"},
    "Q8": {"color": "red", "starname": "Crucis"},
    "P10": {"color": "lime", "starname": "Canopus"},
    "Q11": {"color": "yellow", "starname": "Draconis"},
    "R14": {"color": "orange", "starname": "Lupi"},
    "T16": {"color": "yellow", "starname": "Aurigae"},
    "T12": {"color": "red", "starname": "Scheat"},
    "S10": {"color": "orange", "starname": "Almach"},
    "T4": {"color": "red", "starname": "Antares"},
    "V2": {"color": "yellow", "starname": "Tauri"},
    "U8": {"color": "yellow", "starname": "Spica"},
    "Y3": {"color": "red", "starname": "Wolf"},
    "X5": {"color": "orange", "starname": "Arcturus"},
    "X8": {"color": "blue", "starname": "Vega"},
    "W11": {"color": "red", "starname": "Mirach"},
    "W13": {"color": "yellow", "starname": "Cygni"},
    "V19": {"color": "lime", "starname": "Procyon"},
    "X16": {"color": "red", "starname": "Kruger"},
    "CC17": {"color": "red", "starname": "Barnard"},
    "Y14": {"color": "blue", "starname": "Altair"},
    "AA15": {"color": "orange", "starname": "Hamal"},
    "CC12": {"color": "yellow", "starname": "Dubhe"},
    "AA9": {"color": "lime", "starname": "Wezen"},
    "BB5": {"color": "yellow", "starname": "Bootis"},
    "EE10": {"color": "lime", "starname": "Polaris"}
}

# Star System Counts
TOTAL_STAR_SYSTEMS = len(FIXED_STAR_LOCATIONS)
STAR_COLOR_DISTRIBUTION = {
    StarColor.BLUE: 8,    # blue stars in fixed locations
    StarColor.GREEN: 9,   # lime stars (green equivalent)
    StarColor.YELLOW: 18, # yellow stars
    StarColor.ORANGE: 9,  # orange stars  
    StarColor.RED: 18     # red stars
}

# Color mapping from rules.txt to StarColor enum
RULES_COLOR_TO_STARCOLOR = {
    "blue": StarColor.BLUE,
    "lime": StarColor.GREEN,  # lime maps to green
    "yellow": StarColor.YELLOW,
    "orange": StarColor.ORANGE,
    "red": StarColor.RED
}

# Planet Distribution Tendencies by Star Color
PLANET_TENDENCIES = {
    StarColor.YELLOW: {
        "terran_chance": 0.7,
        "mineral_rich_chance": 0.2
    },
    StarColor.BLUE: {
        "terran_chance": 0.2,
        "mineral_rich_chance": 0.8
    },
    StarColor.GREEN: {
        "terran_chance": 0.4,
        "mineral_rich_chance": 0.3
    },
    StarColor.ORANGE: {
        "terran_chance": 0.3,
        "mineral_rich_chance": 0.4
    },
    StarColor.RED: {
        "terran_chance": 0.2,
        "mineral_rich_chance": 0.3
    }
}

# Gas Cloud Movement Rules
GAS_CLOUD_ENTRY_RESTRICTION = True  # Must start adjacent to enter
GAS_CLOUD_MOVEMENT_LIMIT = 1        # Only 1 hex per turn in clouds

# Factory Limits
FACTORY_LIMITS = {
    "normal": 1,        # 1 factory per million population (Industrial Technology)
    "improved": 2,      # 2 factories per million population (Improved Industrial)
    "robotic": None     # No limit (Robotic Industry)
}

# Task Force Limits
MAX_TASK_FORCES_PER_PLAYER = 15

# Command Post Rules
COMMAND_POST_REQUIRED_FOR_SHIPS = [
    ShipType.CORVETTE,
    ShipType.FIGHTER,
    ShipType.DEATH_STAR,
    ShipType.COLONY_TRANSPORT
]  # Scouts exempt from command post range

# AI Strategy Weights (default values)
DEFAULT_STRATEGY_WEIGHTS = {
    "expansionist": {
        "exploration": 1.5,
        "colonization": 2.0,
        "military": 0.7,
        "research": 1.2,
        "economy": 1.3
    },
    "warlord": {
        "exploration": 1.0,
        "colonization": 1.2,
        "military": 2.0,
        "research": 0.8,
        "economy": 1.0
    },
    "technophile": {
        "exploration": 1.2,
        "colonization": 1.0,
        "military": 0.8,
        "research": 2.0,
        "economy": 1.5
    },
    "balanced": {
        "exploration": 1.0,
        "colonization": 1.0,
        "military": 1.0,
        "research": 1.0,
        "economy": 1.0
    }
}

# Simulation Configuration
DEFAULT_SIMULATION_CONFIG = {
    "max_turns": MAX_TURNS,
    "debug_logging": False,
    "save_snapshots": True,
    "monte_carlo_iterations": 1000,
    "random_seed": None
}

# Analysis Constants
STATISTICAL_SIGNIFICANCE_THRESHOLD = 0.05
MIN_MONTE_CARLO_ITERATIONS = 100
RECOMMENDED_MONTE_CARLO_ITERATIONS = 1000

# File Format Constants
SAVE_GAME_VERSION = "1.0"
SUPPORTED_EXPORT_FORMATS = ["json", "csv", "html", "pdf"]

# Logging Configuration
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Performance Constants
MAX_PATHFINDING_ITERATIONS = 1000
COMBAT_RESOLUTION_TIMEOUT = 30  # seconds
ACTION_EXECUTION_TIMEOUT = 10   # seconds

# Validation Constants
MIN_PLAYER_COUNT = 2
MAX_GAME_NAME_LENGTH = 50
MAX_PLAYER_NAME_LENGTH = 30
VALID_HEX_PATTERN = r'^([A-Z]{1,2})(\d{1,2})$'

# Star Card System
STAR_CARD_RANGES = {
    StarColor.BLUE: (1, 11),     # Blue stars: cards 1-11
    StarColor.GREEN: (12, 23),   # Green stars: cards 12-23  
    StarColor.YELLOW: (24, 43),  # Yellow stars: cards 24-43
    StarColor.ORANGE: (44, 56),  # Orange stars: cards 44-56
    StarColor.RED: (57, 78)      # Red stars: cards 57-78
}

# Star Cards Database (from rules.txt STAR CARDS TABLE)
STAR_CARDS = {
    # Blue stars (1-11)
    1: {"color": "blue", "planets": []},  # Empty system
    2: {"color": "blue", "planets": []},  # Empty system
    3: {"color": "blue", "planets": [
        {"orbit": 3, "type": "barren", "max_pop": 10, "mineral_rich": True},
        {"orbit": 4, "type": "sub_terran", "max_pop": 20, "mineral_rich": False}
    ]},
    4: {"color": "blue", "planets": [
        {"orbit": 5, "type": "sub_terran", "max_pop": 20, "mineral_rich": False}
    ]},
    5: {"color": "blue", "planets": [
        {"orbit": 3, "type": "minimal_terran", "max_pop": 10, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 10, "mineral_rich": True}
    ]},
    6: {"color": "blue", "planets": [
        {"orbit": 4, "type": "barren", "max_pop": 10, "mineral_rich": True},
        {"orbit": 6, "type": "minimal_terran", "max_pop": 40, "mineral_rich": False}
    ]},
    7: {"color": "blue", "planets": [
        {"orbit": 4, "type": "minimal_terran", "max_pop": 20, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 20, "mineral_rich": True}
    ]},
    8: {"color": "blue", "planets": [
        {"orbit": 3, "type": "barren", "max_pop": 10, "mineral_rich": False},
        {"orbit": 5, "type": "minimal_terran", "max_pop": 20, "mineral_rich": True}
    ]},
    9: {"color": "blue", "planets": [
        {"orbit": 4, "type": "minimal_terran", "max_pop": 10, "mineral_rich": False},
        {"orbit": 5, "type": "minimal_terran", "max_pop": 40, "mineral_rich": True}
    ]},
    10: {"color": "blue", "planets": [
        {"orbit": 3, "type": "barren", "max_pop": 20, "mineral_rich": True}
    ]},
    11: {"color": "blue", "planets": [
        {"orbit": 6, "type": "barren", "max_pop": 20, "mineral_rich": True},
        {"orbit": 7, "type": "barren", "max_pop": 10, "mineral_rich": True}
    ]},
    
    # Green stars (12-23)
    12: {"color": "green", "planets": [
        {"orbit": 4, "type": "terran", "max_pop": 60, "mineral_rich": False},
        {"orbit": 5, "type": "minimal_terran", "max_pop": 10, "mineral_rich": False},
        {"orbit": 6, "type": "barren", "max_pop": 20, "mineral_rich": False}
    ]},
    13: {"color": "green", "planets": []},  # Empty system
    14: {"color": "green", "planets": []},  # Empty system
    15: {"color": "green", "planets": [
        {"orbit": 4, "type": "sub_terran", "max_pop": 20, "mineral_rich": False},
        {"orbit": 5, "type": "terran", "max_pop": 40, "mineral_rich": False}
    ]},
    16: {"color": "green", "planets": [
        {"orbit": 3, "type": "barren", "max_pop": 10, "mineral_rich": True},
        {"orbit": 4, "type": "terran", "max_pop": 60, "mineral_rich": False}
    ]},
    17: {"color": "green", "planets": [
        {"orbit": 4, "type": "sub_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 20, "mineral_rich": False}  # BR assumed to be barren
    ]},
    18: {"color": "green", "planets": [
        {"orbit": 4, "type": "barren", "max_pop": 10, "mineral_rich": True},
        {"orbit": 5, "type": "sub_terran", "max_pop": 60, "mineral_rich": False}
    ]},
    19: {"color": "green", "planets": [
        {"orbit": 3, "type": "barren", "max_pop": 20, "mineral_rich": True}
    ]},
    20: {"color": "green", "planets": [
        {"orbit": 2, "type": "barren", "max_pop": 10, "mineral_rich": False},
        {"orbit": 3, "type": "sub_terran", "max_pop": 40, "mineral_rich": True}
    ]},
    21: {"color": "green", "planets": [
        {"orbit": 3, "type": "minimal_terran", "max_pop": 20, "mineral_rich": False},
        {"orbit": 6, "type": "barren", "max_pop": 10, "mineral_rich": True}
    ]},
    22: {"color": "green", "planets": [
        {"orbit": 5, "type": "minimal_terran", "max_pop": 40, "mineral_rich": False}
    ]},
    23: {"color": "green", "planets": [
        {"orbit": 4, "type": "barren", "max_pop": 20, "mineral_rich": False}
    ]},
    
    # Yellow stars (24-43)
    24: {"color": "yellow", "planets": [
        {"orbit": 3, "type": "terran", "max_pop": 80, "mineral_rich": False},
        {"orbit": 4, "type": "sub_terran", "max_pop": 40, "mineral_rich": False}
    ]},
    25: {"color": "yellow", "planets": [
        {"orbit": 3, "type": "terran", "max_pop": 80, "mineral_rich": False}
    ]},
    26: {"color": "yellow", "planets": [
        {"orbit": 5, "type": "terran", "max_pop": 60, "mineral_rich": False}
    ]},
    27: {"color": "yellow", "planets": [
        {"orbit": 3, "type": "minimal_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 4, "type": "barren", "max_pop": 20, "mineral_rich": True}
    ]},
    28: {"color": "yellow", "planets": [
        {"orbit": 3, "type": "terran", "max_pop": 80, "mineral_rich": False}
    ]},
    29: {"color": "yellow", "planets": [
        {"orbit": 3, "type": "terran", "max_pop": 60, "mineral_rich": False}
    ]},
    30: {"color": "yellow", "planets": [
        {"orbit": 5, "type": "terran", "max_pop": 60, "mineral_rich": False}
    ]},
    31: {"color": "yellow", "planets": [
        {"orbit": 2, "type": "minimal_terran", "max_pop": 40, "mineral_rich": False}
    ]},
    32: {"color": "yellow", "planets": [
        {"orbit": 4, "type": "terran", "max_pop": 80, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 10, "mineral_rich": False}
    ]},
    33: {"color": "yellow", "planets": [
        {"orbit": 3, "type": "terran", "max_pop": 60, "mineral_rich": False}
    ]},
    34: {"color": "yellow", "planets": [
        {"orbit": 5, "type": "terran", "max_pop": 40, "mineral_rich": False}
    ]},
    35: {"color": "yellow", "planets": [
        {"orbit": 3, "type": "barren", "max_pop": 20, "mineral_rich": False}
    ]},
    36: {"color": "yellow", "planets": [
        {"orbit": 4, "type": "terran", "max_pop": 80, "mineral_rich": False}
    ]},
    37: {"color": "yellow", "planets": [
        {"orbit": 3, "type": "barren", "max_pop": 20, "mineral_rich": False},
        {"orbit": 4, "type": "terran", "max_pop": 60, "mineral_rich": False}
    ]},
    38: {"color": "yellow", "planets": [
        {"orbit": 3, "type": "sub_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 4, "type": "minimal_terran", "max_pop": 20, "mineral_rich": False}
    ]},
    39: {"color": "yellow", "planets": [
        {"orbit": 4, "type": "minimal_terran", "max_pop": 20, "mineral_rich": False},
        {"orbit": 5, "type": "terran", "max_pop": 60, "mineral_rich": False}
    ]},
    40: {"color": "yellow", "planets": [
        {"orbit": 4, "type": "terran", "max_pop": 80, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 10, "mineral_rich": False}
    ]},
    41: {"color": "yellow", "planets": [
        {"orbit": 4, "type": "sub_terran", "max_pop": 60, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 10, "mineral_rich": True}
    ]},
    42: {"color": "yellow", "planets": [
        {"orbit": 5, "type": "terran", "max_pop": 60, "mineral_rich": False}
    ]},
    43: {"color": "yellow", "planets": [
        {"orbit": 4, "type": "terran", "max_pop": 80, "mineral_rich": False}
    ]},
    
    # Orange stars (44-56)
    44: {"color": "orange", "planets": [
        {"orbit": 2, "type": "sub_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 3, "type": "sub_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 10, "mineral_rich": False}
    ]},
    45: {"color": "orange", "planets": [
        {"orbit": 2, "type": "terran", "max_pop": 60, "mineral_rich": False},
        {"orbit": 3, "type": "sub_terran", "max_pop": 20, "mineral_rich": False}
    ]},
    46: {"color": "orange", "planets": [
        {"orbit": 3, "type": "terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 4, "type": "minimal_terran", "max_pop": 10, "mineral_rich": False}
    ]},
    47: {"color": "orange", "planets": [
        {"orbit": 2, "type": "sub_terran", "max_pop": 60, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 10, "mineral_rich": True}
    ]},
    48: {"color": "orange", "planets": [
        {"orbit": 3, "type": "sub_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 4, "type": "minimal_terran", "max_pop": 10, "mineral_rich": True}
    ]},
    49: {"color": "orange", "planets": [
        {"orbit": 2, "type": "barren", "max_pop": 10, "mineral_rich": False},
        {"orbit": 3, "type": "sub_terran", "max_pop": 40, "mineral_rich": False}
    ]},
    50: {"color": "orange", "planets": [
        {"orbit": 3, "type": "minimal_terran", "max_pop": 20, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 20, "mineral_rich": False}
    ]},
    51: {"color": "orange", "planets": []},  # Empty system
    52: {"color": "orange", "planets": [
        {"orbit": 4, "type": "sub_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 10, "mineral_rich": False}
    ]},
    53: {"color": "orange", "planets": [
        {"orbit": 4, "type": "sub_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 10, "mineral_rich": False}
    ]},
    54: {"color": "orange", "planets": [
        {"orbit": 4, "type": "minimal_terran", "max_pop": 20, "mineral_rich": True},
        {"orbit": 6, "type": "barren", "max_pop": 20, "mineral_rich": False}
    ]},
    55: {"color": "orange", "planets": []},  # Empty system
    56: {"color": "orange", "planets": [
        {"orbit": 5, "type": "minimal_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 6, "type": "barren", "max_pop": 20, "mineral_rich": True}
    ]},
    
    # Red stars (57-78)
    57: {"color": "red", "planets": [
        {"orbit": 3, "type": "terran", "max_pop": 40, "mineral_rich": False}
    ]},
    58: {"color": "red", "planets": [
        {"orbit": 1, "type": "sub_terran", "max_pop": 40, "mineral_rich": False}
    ]},
    59: {"color": "red", "planets": [
        {"orbit": 1, "type": "barren", "max_pop": 10, "mineral_rich": True},
        {"orbit": 4, "type": "minimal_terran", "max_pop": 40, "mineral_rich": False}
    ]},
    60: {"color": "red", "planets": [
        {"orbit": 1, "type": "minimal_terran", "max_pop": 10, "mineral_rich": False},
        {"orbit": 3, "type": "barren", "max_pop": 10, "mineral_rich": False}
    ]},
    61: {"color": "red", "planets": [
        {"orbit": 2, "type": "sub_terran", "max_pop": 20, "mineral_rich": False},
        {"orbit": 3, "type": "barren", "max_pop": 20, "mineral_rich": False}
    ]},
    62: {"color": "red", "planets": [
        {"orbit": 2, "type": "sub_terran", "max_pop": 60, "mineral_rich": False},
        {"orbit": 4, "type": "barren", "max_pop": 20, "mineral_rich": False}
    ]},
    63: {"color": "red", "planets": [
        {"orbit": 1, "type": "minimal_terran", "max_pop": 20, "mineral_rich": False},
        {"orbit": 3, "type": "barren", "max_pop": 10, "mineral_rich": False}
    ]},
    64: {"color": "red", "planets": [
        {"orbit": 2, "type": "minimal_terran", "max_pop": 10, "mineral_rich": False},
        {"orbit": 4, "type": "barren", "max_pop": 20, "mineral_rich": False}
    ]},
    65: {"color": "red", "planets": [
        {"orbit": 3, "type": "sub_terran", "max_pop": 40, "mineral_rich": False}
    ]},
    66: {"color": "red", "planets": [
        {"orbit": 3, "type": "sub_terran", "max_pop": 60, "mineral_rich": False}
    ]},
    67: {"color": "red", "planets": [
        {"orbit": 2, "type": "minimal_terran", "max_pop": 20, "mineral_rich": False}
    ]},
    68: {"color": "red", "planets": [
        {"orbit": 3, "type": "minimal_terran", "max_pop": 10, "mineral_rich": False}
    ]},
    69: {"color": "red", "planets": [
        {"orbit": 1, "type": "barren", "max_pop": 10, "mineral_rich": False},
        {"orbit": 4, "type": "sub_terran", "max_pop": 40, "mineral_rich": False}
    ]},
    70: {"color": "red", "planets": [
        {"orbit": 1, "type": "minimal_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 3, "type": "barren", "max_pop": 20, "mineral_rich": False}
    ]},
    71: {"color": "red", "planets": [
        {"orbit": 3, "type": "minimal_terran", "max_pop": 20, "mineral_rich": False},
        {"orbit": 4, "type": "barren", "max_pop": 10, "mineral_rich": False}
    ]},
    72: {"color": "red", "planets": [
        {"orbit": 2, "type": "barren", "max_pop": 10, "mineral_rich": False},
        {"orbit": 4, "type": "minimal_terran", "max_pop": 10, "mineral_rich": False}
    ]},
    73: {"color": "red", "planets": [
        {"orbit": 1, "type": "sub_terran", "max_pop": 40, "mineral_rich": False}
    ]},
    74: {"color": "red", "planets": [
        {"orbit": 2, "type": "minimal_terran", "max_pop": 40, "mineral_rich": True}
    ]},
    75: {"color": "red", "planets": [
        {"orbit": 4, "type": "minimal_terran", "max_pop": 10, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 20, "mineral_rich": False}
    ]},
    76: {"color": "red", "planets": []},  # Empty system
    77: {"color": "red", "planets": [
        {"orbit": 2, "type": "sub_terran", "max_pop": 40, "mineral_rich": False},
        {"orbit": 5, "type": "barren", "max_pop": 20, "mineral_rich": True}
    ]},
    78: {"color": "red", "planets": [
        {"orbit": 1, "type": "barren", "max_pop": 10, "mineral_rich": False},
        {"orbit": 3, "type": "minimal_terran", "max_pop": 40, "mineral_rich": False}
    ]},
}

# Error Codes
ERROR_CODES = {
    "INVALID_PLAYER": "E001",
    "GAME_ENDED": "E002",
    "INSUFFICIENT_RESOURCES": "E003",
    "INVALID_HEX": "E004",
    "WRONG_PHASE": "E005",
    "INVALID_ACTION": "E006",
    "VALIDATION_FAILED": "E007",
    "EXECUTION_FAILED": "E008"
}