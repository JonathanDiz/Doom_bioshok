"""
Módulo principal que expone la API pública del paquete de utilidades del juego.
Controla las exportaciones principales y la configuración inicial del paquete.
"""

import logging
from typing import List

# Configuración inicial de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Versión del paquete
__version__ = "1.3.0"

# Exportaciones públicas de los subsistemas principales
from .display_manager import DisplayManager
from .event_manager import EventManager
from .execution_engine import ExecutionEngine
from .resource_manager import ResourceManager
from .initialization import Initialization
from .core import GameCore, GameCoreError
from .boot import BootManager, BootStage, CriticalBootError

__all__: List[str] = [
    'DisplayManager',
    'EventManager',
    'ExecutionEngine',
    'ResourceManager',
    'Initialization',
    'GameCore',
    'GameCoreError',
    'BootManager',
    'BootStage',
    'CriticalBootError',
    '__version__'
]

logger.info(f"Game Utilities v{__version__} inicializado correctamente")
logger.debug("Módulos disponibles: %s", __all__)