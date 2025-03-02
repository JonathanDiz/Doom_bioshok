"""
Módulo principal de sistemas de gestión del juego

Provee una interfaz unificada para todos los managers principales:
from game_core.managers import (
    InputManager,
    DisplayManager,
    ResourceManager,
    DebugManager,
    AudioManager,
    initialize_core_managers
)
"""

import logging
from typing import Tuple

# Configuración de logging
logger = logging.getLogger(__name__)

try:
    from .input import InputManager
    from .display import DisplayManager
    from .resource import ResourceManager
    from .debug import DebugManager
    from .audio import AudioManager
except ImportError as e:
    logger.critical("Error crítico al importar módulos de gestión: %s", e)
    raise

__all__ = [
    'InputManager',
    'DisplayManager',
    'ResourceManager',
    'DebugManager',
    'AudioManager',
    'initialize_core_managers'
]

__version__ = '2.2.0'

def initialize_core_managers(core) -> Tuple:
    """
    Inicializa los sistemas principales con gestión robusta de errores
    
    Returns:
        Tuple: Instancias de (DisplayManager, ResourceManager, InputManager, 
               DebugManager, AudioManager)
    """
    managers = []
    
    try:
        logger.info("Inicializando subsistemas principales...")
        
        logger.debug("Creando DisplayManager...")
        display = DisplayManager(core)
        managers.append(display)
        
        logger.debug("Creando ResourceManager...")
        resource = ResourceManager(core)
        managers.append(resource)
        
        logger.debug("Creando InputManager...")
        input_mgr = InputManager(core)
        managers.append(input_mgr)
        
        logger.debug("Creando DebugManager...")
        debug = DebugManager(core)
        managers.append(debug)
        
        logger.debug("Creando AudioManager...")
        audio = AudioManager(core)
        managers.append(audio)
        
        logger.info("Subsistemas principales inicializados correctamente")

    except Exception as e:
        logger.critical("Fallo en inicialización de subsistemas: %s", e, exc_info=True)
        raise
    
    return tuple(managers)