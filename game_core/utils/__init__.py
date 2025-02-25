"""
Módulo utilitario central para funcionalidades transversales del motor de juego

Exporta:
- Herramientas asíncronas: AsyncLoader, run_parallel
- Tipos comunes: Coordinate, ColorValue, GameSystem, etc.
- Funciones helper: debug_timer, validate_resolution
"""

from .async_tools import AsyncLoader, run_parallel
from .type_aliases import (
    Coordinate,
    ScreenCoordinate,
    ColorValue,
    SurfaceType,
    EntityID,
    EventCallback,
    AssetPath,
    Velocity,
    GameSystem,
    DisplaySettings
)

# Interface pública del módulo
__all__ = [
    # Async Tools
    'AsyncLoader',
    'run_parallel',
    
    # Type Aliases
    'Coordinate',
    'ScreenCoordinate',
    'ColorValue',
    'SurfaceType',
    'EntityID', 
    'EventCallback',
    'AssetPath',
    'Velocity',
    'GameSystem',
    'DisplaySettings',
    
    # Helper Functions
    'debug_timer',
    'validate_resolution'
]

# Versión del módulo utilitario
__version__ = '1.3.0'

# Funciones helper adicionales
def debug_timer():
    """Context manager para medir tiempos de ejecución"""
    from time import perf_counter
    class Timer:
        def __enter__(self):
            self.start = perf_counter()
            return self
        def __exit__(self, *args):
            self.end = perf_counter()
            self.duration = self.end - self.start
            print(f"Tiempo ejecución: {self.duration:.4f} segundos")
    return Timer()

def validate_resolution(resolution: tuple):
    """Normaliza y valida una resolución de pantalla"""
    from pygame import display
    valid_modes = display.list_modes()
    return (
        min(max(resolution[0], 640), 7680),
        min(max(resolution[1], 480), 4320)
    ) if valid_modes else (1280, 720)