"""
Módulo principal del núcleo del juego

Exporta la interfaz pública principal:
from game_core import GameCore, ResourceManager, initialize_managers
"""

from .core import GameCore
from .initialization import PyGameInitialization
from .execution_engine import ExecutionEngine
from .event_manager import EventManager
from .managers import (
    ResourceManager,
    DisplayManager,
    DebugManager,
    initialize_core_managers
)

__all__ = [
    # Core del sistema
    "GameCore",
    "Initialization",
    "ExecutionEngine",
    
    # Managers
    "ResourceManager",
    "DisplayManager", 
    "EventManager",
    "DebugManager",
    
    # Factory methods
    "initialize_core_managers"
]

# Configuración de acceso rápido
__version__ = "1.3.0"
__author__ = "Jonathan Joao Diaz Olivares <jonathanfullstack@gmail.com>"
__license__ = "GPL-3.0 license"