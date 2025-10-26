"""
Stellar Conquest - A comprehensive board game simulator.

This package provides a complete implementation of the Stellar Conquest board game
with support for AI players, scenario analysis, and Monte Carlo simulation.
"""

__version__ = "0.1.0"
__author__ = "Stellar Conquest Simulator Team"

from .game.game_state import GameState
from .entities.player import Player
from .simulation.simulator import StellarConquestSimulator

__all__ = ["GameState", "Player", "StellarConquestSimulator"]