"""
Módulo principal para sistemas de gestión del juego

Exporta los componentes principales para un acceso simplificado:
from game_core.managers import InputManager, DisplayManager, ResourceManager
"""

from .input import InputManager
from .display import DisplayManager
from .resource import ResourceManager
from .debug import DebugManager
from .audio import AudioManager

# Interface pública del módulo
__all__ = [
    'InputManager',
    'DisplayManager', 
    'ResourceManager',
    'DebugManager',
    'AudioManager'
]

# Versión del sistema de gestión
__version__ = '1.0.0'

# Inicialización de subsistemas comunes
def initialize_core_managers(core) -> tuple:
    """Crea instancias básicas preconfiguradas de los managers principales"""
    return (
        InputManager(core),
        DisplayManager(core),
        ResourceManager(core),
        DebugManager(core)
    )