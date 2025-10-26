"""Game data structures and constants for Stellar Conquest."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
from ..core.enums import StarColor, PlanetType, ShipType, Technology


@dataclass(frozen=True)
class StarCardData:
    """Data structure for star card information."""
    card_number: int
    star_color: StarColor
    planets: List['PlanetData']
    
    def __post_init__(self):
        """Validate star card data."""
        if not 1 <= self.card_number <= 78:
            raise ValueError(f"Invalid star card number: {self.card_number}")
        if len(self.planets) > 3:
            raise ValueError(f"Star card cannot have more than 3 planets: {len(self.planets)}")


@dataclass(frozen=True)
class PlanetData:
    """Data structure for planet information."""
    orbit: int
    planet_type: PlanetType
    max_population: int
    is_mineral_rich: bool = False
    
    def __post_init__(self):
        """Validate planet data."""
        if not 1 <= self.orbit <= 7:
            raise ValueError(f"Invalid orbit number: {self.orbit}")
        if self.max_population <= 0:
            raise ValueError(f"Invalid max population: {self.max_population}")


@dataclass(frozen=True)
class TechnologyData:
    """Data structure for technology information."""
    technology: Technology
    name: str
    description: str
    cost: int
    prerequisite: Optional[Technology] = None
    reduced_cost: Optional[int] = None
    level: int = 1
    
    def __post_init__(self):
        """Validate technology data."""
        if self.cost <= 0:
            raise ValueError(f"Invalid technology cost: {self.cost}")
        if self.reduced_cost is not None and self.reduced_cost >= self.cost:
            raise ValueError(f"Reduced cost must be less than base cost: {self.reduced_cost} >= {self.cost}")
        if not 1 <= self.level <= 3:
            raise ValueError(f"Invalid technology level: {self.level}")


@dataclass(frozen=True)
class ShipData:
    """Data structure for ship type information."""
    ship_type: ShipType
    name: str
    cost: int
    combat_strength: int
    can_attack: bool
    vulnerable_to_exploration: bool
    carries_population: bool = False
    
    def __post_init__(self):
        """Validate ship data."""
        if self.cost < 0:
            raise ValueError(f"Invalid ship cost: {self.cost}")
        if self.combat_strength < 0:
            raise ValueError(f"Invalid combat strength: {self.combat_strength}")


@dataclass(frozen=True)
class CombatRollData:
    """Data structure for combat roll requirements."""
    attacker: str
    defender: str
    dice_count: int
    success_values: List[int]
    
    def __post_init__(self):
        """Validate combat roll data."""
        if self.dice_count not in [1, 2]:
            raise ValueError(f"Invalid dice count: {self.dice_count}")
        if not all(1 <= val <= (6 if self.dice_count == 1 else 12) for val in self.success_values):
            raise ValueError(f"Invalid success values: {self.success_values}")


@dataclass(frozen=True)
class StarSystemData:
    """Data structure for star system information."""
    location: str
    star_color: StarColor
    name: Optional[str] = None
    
    def __post_init__(self):
        """Validate star system data."""
        import re
        if not re.match(r'^[A-Z]{1,2}\d{1,2}$', self.location):
            raise ValueError(f"Invalid hex location: {self.location}")


@dataclass(frozen=True)
class BuildingData:
    """Data structure for building information."""
    name: str
    cost: int
    prerequisite_tech: Optional[Technology] = None
    description: str = ""
    
    def __post_init__(self):
        """Validate building data."""
        if self.cost <= 0:
            raise ValueError(f"Invalid building cost: {self.cost}")


# Game Data Collections
STAR_CARDS: Dict[int, StarCardData] = {
    # Blue star cards (1-11)
    1: StarCardData(1, StarColor.BLUE, []),
    2: StarCardData(2, StarColor.BLUE, []),
    3: StarCardData(3, StarColor.BLUE, [
        PlanetData(3, PlanetType.BARREN, 10, True),
        PlanetData(4, PlanetType.SUB_TERRAN, 20, False)
    ]),
    4: StarCardData(4, StarColor.BLUE, [
        PlanetData(5, PlanetType.SUB_TERRAN, 20, False)
    ]),
    5: StarCardData(5, StarColor.BLUE, [
        PlanetData(3, PlanetType.MINIMAL_TERRAN, 10, False),
        PlanetData(5, PlanetType.BARREN, 10, True)
    ]),
    6: StarCardData(6, StarColor.BLUE, [
        PlanetData(4, PlanetType.BARREN, 10, True),
        PlanetData(6, PlanetType.MINIMAL_TERRAN, 40, False)
    ]),
    7: StarCardData(7, StarColor.BLUE, [
        PlanetData(4, PlanetType.MINIMAL_TERRAN, 20, False),
        PlanetData(5, PlanetType.BARREN, 20, True)
    ]),
    8: StarCardData(8, StarColor.BLUE, [
        PlanetData(3, PlanetType.BARREN, 10, False),
        PlanetData(5, PlanetType.MINIMAL_TERRAN, 20, True)
    ]),
    9: StarCardData(9, StarColor.BLUE, [
        PlanetData(4, PlanetType.MINIMAL_TERRAN, 10, False),
        PlanetData(5, PlanetType.MINIMAL_TERRAN, 40, True)
    ]),
    10: StarCardData(10, StarColor.BLUE, [
        PlanetData(3, PlanetType.BARREN, 20, True)
    ]),
    11: StarCardData(11, StarColor.BLUE, [
        PlanetData(6, PlanetType.BARREN, 20, True),
        PlanetData(7, PlanetType.BARREN, 10, True)
    ]),
    
    # Green star cards (12-23)
    12: StarCardData(12, StarColor.GREEN, [
        PlanetData(4, PlanetType.TERRAN, 60, False),
        PlanetData(5, PlanetType.MINIMAL_TERRAN, 10, False),
        PlanetData(6, PlanetType.BARREN, 20, False)
    ]),
    13: StarCardData(13, StarColor.GREEN, []),
    14: StarCardData(14, StarColor.GREEN, []),
    15: StarCardData(15, StarColor.GREEN, [
        PlanetData(4, PlanetType.SUB_TERRAN, 20, False),
        PlanetData(5, PlanetType.TERRAN, 40, False)
    ]),
    16: StarCardData(16, StarColor.GREEN, [
        PlanetData(3, PlanetType.BARREN, 10, True),
        PlanetData(4, PlanetType.TERRAN, 60, False)
    ]),
    17: StarCardData(17, StarColor.GREEN, [
        PlanetData(4, PlanetType.SUB_TERRAN, 40, False),
        PlanetData(5, PlanetType.BARREN, 20, False)
    ]),
    18: StarCardData(18, StarColor.GREEN, [
        PlanetData(4, PlanetType.BARREN, 10, True),
        PlanetData(5, PlanetType.SUB_TERRAN, 60, False)
    ]),
    19: StarCardData(19, StarColor.GREEN, [
        PlanetData(3, PlanetType.BARREN, 20, True)
    ]),
    20: StarCardData(20, StarColor.GREEN, [
        PlanetData(2, PlanetType.BARREN, 10, False),
        PlanetData(3, PlanetType.SUB_TERRAN, 40, True)
    ]),
    21: StarCardData(21, StarColor.GREEN, [
        PlanetData(3, PlanetType.MINIMAL_TERRAN, 20, False),
        PlanetData(6, PlanetType.BARREN, 10, True)
    ]),
    22: StarCardData(22, StarColor.GREEN, [
        PlanetData(5, PlanetType.MINIMAL_TERRAN, 40, False)
    ]),
    23: StarCardData(23, StarColor.GREEN, [
        PlanetData(4, PlanetType.BARREN, 20, False)
    ]),
    
    # Yellow star cards (24-43) - High Terran planet probability
    24: StarCardData(24, StarColor.YELLOW, [
        PlanetData(3, PlanetType.TERRAN, 80, False),
        PlanetData(4, PlanetType.SUB_TERRAN, 40, False)
    ]),
    25: StarCardData(25, StarColor.YELLOW, [
        PlanetData(3, PlanetType.TERRAN, 80, False)
    ]),
    26: StarCardData(26, StarColor.YELLOW, [
        PlanetData(5, PlanetType.TERRAN, 60, False)
    ]),
    27: StarCardData(27, StarColor.YELLOW, [
        PlanetData(3, PlanetType.MINIMAL_TERRAN, 40, False),
        PlanetData(4, PlanetType.BARREN, 20, True)
    ]),
    28: StarCardData(28, StarColor.YELLOW, [
        PlanetData(3, PlanetType.TERRAN, 80, False)
    ]),
    29: StarCardData(29, StarColor.YELLOW, [
        PlanetData(3, PlanetType.TERRAN, 60, False)
    ]),
    30: StarCardData(30, StarColor.YELLOW, [
        PlanetData(5, PlanetType.TERRAN, 60, False)
    ]),
    # ... Continue with remaining yellow cards
    
    # Sample red star cards (57-78) - Lower Terran probability
    57: StarCardData(57, StarColor.RED, [
        PlanetData(3, PlanetType.TERRAN, 40, False)
    ]),
    58: StarCardData(58, StarColor.RED, [
        PlanetData(1, PlanetType.SUB_TERRAN, 40, False)
    ]),
    # ... Continue with remaining red cards
}


SHIP_DATA: Dict[ShipType, ShipData] = {
    ShipType.SCOUT: ShipData(
        ShipType.SCOUT, "Scout", 3, 0, False, True
    ),
    ShipType.COLONY_TRANSPORT: ShipData(
        ShipType.COLONY_TRANSPORT, "Colony Transport", 1, 0, False, True, True
    ),
    ShipType.CORVETTE: ShipData(
        ShipType.CORVETTE, "Corvette", 8, 1, True, False
    ),
    ShipType.FIGHTER: ShipData(
        ShipType.FIGHTER, "Fighter", 20, 2, True, False
    ),
    ShipType.DEATH_STAR: ShipData(
        ShipType.DEATH_STAR, "Death Star", 40, 4, True, False
    )
}


TECHNOLOGY_DATA: Dict[Technology, TechnologyData] = {
    # Ship Speed Technologies
    Technology.SPEED_3_HEX: TechnologyData(
        Technology.SPEED_3_HEX, "3 Hex Speed", 
        "Every ship may move up to 3 hexes per turn", 15, level=1
    ),
    Technology.SPEED_4_HEX: TechnologyData(
        Technology.SPEED_4_HEX, "4 Hex Speed",
        "Every ship may move up to 4 hexes per turn", 40, 
        Technology.SPEED_3_HEX, 30, level=1
    ),
    Technology.SPEED_5_HEX: TechnologyData(
        Technology.SPEED_5_HEX, "5 Hex Speed",
        "Every ship may move up to 5 hexes per turn", 55,
        Technology.SPEED_4_HEX, 40, level=2
    ),
    Technology.SPEED_6_HEX: TechnologyData(
        Technology.SPEED_6_HEX, "6 Hex Speed",
        "Every ship may move up to 6 hexes per turn", 65,
        Technology.SPEED_5_HEX, 50, level=2
    ),
    Technology.SPEED_7_HEX: TechnologyData(
        Technology.SPEED_7_HEX, "7 Hex Speed",
        "Every ship may move up to 7 hexes per turn", 75,
        Technology.SPEED_6_HEX, 60, level=3
    ),
    Technology.SPEED_8_HEX: TechnologyData(
        Technology.SPEED_8_HEX, "8 Hex Speed",
        "Every ship may move up to 8 hexes per turn", 80,
        Technology.SPEED_7_HEX, 70, level=3
    ),
    
    # Weapons Technologies
    Technology.MISSILE_BASE: TechnologyData(
        Technology.MISSILE_BASE, "Missile Base",
        "Equivalent in strength to corvette. Cost 4 IP per base", 25, level=1
    ),
    Technology.FIGHTER_SHIP: TechnologyData(
        Technology.FIGHTER_SHIP, "Fighter Ship",
        "More powerful warship. Cost 20 IP per fighter", 35, level=1
    ),
    Technology.ADVANCED_MISSILE_BASE: TechnologyData(
        Technology.ADVANCED_MISSILE_BASE, "Advanced Missile Base",
        "Equivalent in strength to fighter. Cost 10 IP per base", 55,
        Technology.MISSILE_BASE, 40, level=2
    ),
    Technology.DEATH_STAR: TechnologyData(
        Technology.DEATH_STAR, "Death Star",
        "Most powerful warship. Cost 40 IP per death star", 90,
        Technology.FIGHTER_SHIP, 75, level=2
    ),
    Technology.IMPROVED_SHIP_WEAPONRY: TechnologyData(
        Technology.IMPROVED_SHIP_WEAPONRY, "Improved Ship Weaponry",
        "Warships fire twice per attack on misses", 100, level=3
    ),
    Technology.PLANET_SHIELD: TechnologyData(
        Technology.PLANET_SHIELD, "Planet Shield",
        "Protects planet from all attacks. Cost 30 IP per shield", 130, level=3
    ),
    
    # General Technologies
    Technology.CONTROLLED_ENVIRONMENT_TECH: TechnologyData(
        Technology.CONTROLLED_ENVIRONMENT_TECH, "Controlled Environment Technology",
        "Permits colonization of barren planets", 25, level=1
    ),
    Technology.INDUSTRIAL_TECHNOLOGY: TechnologyData(
        Technology.INDUSTRIAL_TECHNOLOGY, "Industrial Technology",
        "Allows factory construction. Cost 4 IP per factory", 25, level=1
    ),
    Technology.IMPROVED_INDUSTRIAL_TECH: TechnologyData(
        Technology.IMPROVED_INDUSTRIAL_TECH, "Improved Industrial Technology",
        "Allows 2 factories per million population", 55,
        Technology.INDUSTRIAL_TECHNOLOGY, 40, level=2
    ),
    Technology.UNLIMITED_SHIP_RANGE: TechnologyData(
        Technology.UNLIMITED_SHIP_RANGE, "Unlimited Ship Range",
        "Ships can move anywhere without command post limit", 60,
        Technology.SPEED_5_HEX, 40, level=2
    ),
    Technology.UNLIMITED_SHIP_COMMUNICATION: TechnologyData(
        Technology.UNLIMITED_SHIP_COMMUNICATION, "Unlimited Ship Communication",
        "Ships can be directed from any hex", 70, level=3
    ),
    Technology.ROBOTIC_INDUSTRY: TechnologyData(
        Technology.ROBOTIC_INDUSTRY, "Robotic Industry",
        "Unlimited factories per planet. Cost 3 IP per factory", 100,
        Technology.INDUSTRIAL_TECHNOLOGY, 85, level=3
    )
}


BUILDING_DATA: Dict[str, BuildingData] = {
    "factory": BuildingData(
        "Factory", 4, Technology.INDUSTRIAL_TECHNOLOGY,
        "Produces 1 IP per turn"
    ),
    "robotic_factory": BuildingData(
        "Robotic Factory", 3, Technology.ROBOTIC_INDUSTRY,
        "Produces 1 IP per turn, no population limit"
    ),
    "missile_base": BuildingData(
        "Missile Base", 4, Technology.MISSILE_BASE,
        "Defensive structure equivalent to corvette"
    ),
    "advanced_missile_base": BuildingData(
        "Advanced Missile Base", 10, Technology.ADVANCED_MISSILE_BASE,
        "Defensive structure equivalent to fighter"
    ),
    "planet_shield": BuildingData(
        "Planet Shield", 30, Technology.PLANET_SHIELD,
        "Protects planet from all attacks"
    )
}


COMBAT_TABLE: Dict[tuple, CombatRollData] = {
    # Corvette attacks
    ("corvette", "scout"): CombatRollData("corvette", "scout", 1, [1, 2, 3, 4]),
    ("corvette", "colony_transport"): CombatRollData("corvette", "colony_transport", 1, [1, 2, 3, 4]),
    ("corvette", "corvette"): CombatRollData("corvette", "corvette", 1, [1]),
    ("corvette", "missile_base"): CombatRollData("corvette", "missile_base", 1, [1]),
    ("corvette", "fighter"): CombatRollData("corvette", "fighter", 2, [10]),
    ("corvette", "advanced_missile_base"): CombatRollData("corvette", "advanced_missile_base", 2, [10]),
    ("corvette", "death_star"): CombatRollData("corvette", "death_star", 1, []),
    
    # Fighter attacks
    ("fighter", "scout"): CombatRollData("fighter", "scout", 1, [1, 2, 3, 4, 5]),
    ("fighter", "colony_transport"): CombatRollData("fighter", "colony_transport", 1, [1, 2, 3, 4, 5]),
    ("fighter", "corvette"): CombatRollData("fighter", "corvette", 1, [1, 2]),
    ("fighter", "missile_base"): CombatRollData("fighter", "missile_base", 1, [1, 2]),
    ("fighter", "fighter"): CombatRollData("fighter", "fighter", 1, [1]),
    ("fighter", "advanced_missile_base"): CombatRollData("fighter", "advanced_missile_base", 1, [1]),
    ("fighter", "death_star"): CombatRollData("fighter", "death_star", 2, [10]),
    
    # Death Star attacks
    ("death_star", "scout"): CombatRollData("death_star", "scout", 1, [1, 2, 3, 4, 5, 6]),
    ("death_star", "colony_transport"): CombatRollData("death_star", "colony_transport", 1, [1, 2, 3, 4, 5, 6]),
    ("death_star", "corvette"): CombatRollData("death_star", "corvette", 1, [1, 2, 3, 4]),
    ("death_star", "missile_base"): CombatRollData("death_star", "missile_base", 1, [1, 2, 3, 4]),
    ("death_star", "fighter"): CombatRollData("death_star", "fighter", 1, [1, 2, 3]),
    ("death_star", "advanced_missile_base"): CombatRollData("death_star", "advanced_missile_base", 1, [1, 2, 3]),
    ("death_star", "death_star"): CombatRollData("death_star", "death_star", 1, [1, 2]),
    
    # Missile Base attacks (same as corvette)
    ("missile_base", "scout"): CombatRollData("missile_base", "scout", 1, [1, 2, 3, 4]),
    ("missile_base", "colony_transport"): CombatRollData("missile_base", "colony_transport", 1, [1, 2, 3, 4]),
    ("missile_base", "corvette"): CombatRollData("missile_base", "corvette", 1, [1]),
    ("missile_base", "missile_base"): CombatRollData("missile_base", "missile_base", 1, [1]),
    ("missile_base", "fighter"): CombatRollData("missile_base", "fighter", 2, [10]),
    ("missile_base", "advanced_missile_base"): CombatRollData("missile_base", "advanced_missile_base", 2, [10]),
    ("missile_base", "death_star"): CombatRollData("missile_base", "death_star", 1, []),
    
    # Advanced Missile Base attacks (same as fighter)
    ("advanced_missile_base", "scout"): CombatRollData("advanced_missile_base", "scout", 1, [1, 2, 3, 4, 5]),
    ("advanced_missile_base", "colony_transport"): CombatRollData("advanced_missile_base", "colony_transport", 1, [1, 2, 3, 4, 5]),
    ("advanced_missile_base", "corvette"): CombatRollData("advanced_missile_base", "corvette", 1, [1, 2]),
    ("advanced_missile_base", "missile_base"): CombatRollData("advanced_missile_base", "missile_base", 1, [1, 2]),
    ("advanced_missile_base", "fighter"): CombatRollData("advanced_missile_base", "fighter", 1, [1]),
    ("advanced_missile_base", "advanced_missile_base"): CombatRollData("advanced_missile_base", "advanced_missile_base", 1, [1]),
    ("advanced_missile_base", "death_star"): CombatRollData("advanced_missile_base", "death_star", 2, [10])
}


STAR_SYSTEMS: Dict[str, StarSystemData] = {
    "AA15": StarSystemData("AA15", StarColor.ORANGE, "Hamal"),
    "AA19": StarSystemData("AA19", StarColor.YELLOW, "Scorpii"),
    "AA9": StarSystemData("AA9", StarColor.GREEN, "Wezen"),
    "B11": StarSystemData("B11", StarColor.BLUE, "Sirius"),
    "B18": StarSystemData("B18", StarColor.RED, "Lalande"),
    "BB5": StarSystemData("BB5", StarColor.YELLOW, "Bootis"),
    "CC12": StarSystemData("CC12", StarColor.YELLOW, "Dubhe"),
    "CC17": StarSystemData("CC17", StarColor.RED, "Barnard"),
    "D13": StarSystemData("D13", StarColor.RED, "Luyten"),
    "D4": StarSystemData("D4", StarColor.ORANGE, "Indi"),
    "E17": StarSystemData("E17", StarColor.YELLOW, "Ceti"),
    "E7": StarSystemData("E7", StarColor.RED, "Kapetyn"),
    "EE10": StarSystemData("EE10", StarColor.GREEN, "Polaris"),
    "F9": StarSystemData("F9", StarColor.YELLOW, "Diphda"),
    "G5": StarSystemData("G5", StarColor.YELLOW, "Canis"),
    "H12": StarSystemData("H12", StarColor.GREEN, "Eridani"),
    "H18": StarSystemData("H18", StarColor.RED, "Mira"),
    "H2": StarSystemData("H2", StarColor.RED, "Ophiuchi"),
    "I10": StarSystemData("I10", StarColor.RED, "Ross"),
    "I16": StarSystemData("I16", StarColor.ORANGE, "Rastaban"),
    "I8": StarSystemData("I8", StarColor.BLUE, "Deneb"),
    "J15": StarSystemData("J15", StarColor.BLUE, "Pherda"),
    # ... Continue with all 54 star systems from the rules
}


# Gas cloud hex locations
GAS_CLOUD_HEXES: List[str] = [
    # Cloud 1
    "A10", "A11", "A12", "A13", "B10", "B11", "B12", "C11",
    # Cloud 2
    "I7", "I8", "I13", "I14", "J6", "J7", "J8", "J12", "J13", "J14",
    "K6", "K7", "K14", "K15", "K16", "L5", "L15",
    # Cloud 3
    "O1", "O20", "P1", "P19", "P20", "Q1", "Q2", "Q20", "R1", "R2", "R19",
    # Cloud 4
    "U6", "V5", "V6", "V14", "V15", "W6", "W7", "W15", 
    "X6", "X7", "X8", "X13", "X14", "Y12", "Y13", "Y14",
    # Additional cloud hexes would be added based on complete map data
]


# Utility functions for data access
def get_star_card(card_number: int) -> Optional[StarCardData]:
    """Get star card data by number."""
    return STAR_CARDS.get(card_number)


def get_ship_data(ship_type: ShipType) -> ShipData:
    """Get ship data by type."""
    return SHIP_DATA[ship_type]


def get_technology_data(technology: Technology) -> TechnologyData:
    """Get technology data."""
    return TECHNOLOGY_DATA[technology]


def get_combat_data(attacker: str, defender: str) -> Optional[CombatRollData]:
    """Get combat roll data for attacker vs defender."""
    return COMBAT_TABLE.get((attacker, defender))


def get_star_system(location: str) -> Optional[StarSystemData]:
    """Get star system data by location."""
    return STAR_SYSTEMS.get(location)


def is_gas_cloud_hex(location: str) -> bool:
    """Check if location is a gas cloud hex."""
    return location in GAS_CLOUD_HEXES


def get_planets_by_star_color(star_color: StarColor) -> List[StarCardData]:
    """Get all star cards of a specific color."""
    return [card for card in STAR_CARDS.values() if card.star_color == star_color]


def get_technologies_by_level(level: int) -> List[TechnologyData]:
    """Get all technologies of a specific level."""
    return [tech for tech in TECHNOLOGY_DATA.values() if tech.level == level]