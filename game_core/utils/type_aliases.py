"""
Definiciones centralizadas de tipos para el motor del juego

Proporciona alias de tipos y estructuras comunes usadas en múltiples módulos
"""

from typing import (
    TypeAlias, 
    Any,
    Tuple,
    Callable,
    Union,
    Optional,
    Protocol,
    runtime_checkable
)
from pathlib import Path
import pygame as pg

#region Coordenadas y Geometría
Coordinate: TypeAlias = Union[Tuple[float, float], Tuple[float, float, float]]
"""Representa coordenadas 2D/3D (x, y) o (x, y, z)"""

ScreenCoordinate: TypeAlias = Tuple[int, int]
"""Coordenadas de pantalla en píxeles enteros (x, y)"""

RectPosition: TypeAlias = Union[Coordinate, pg.Rect]
"""Posición representada como coordenadas o rectángulo de Pygame"""

RotationAngle: TypeAlias = float
"""Ángulo de rotación en grados (0-360)"""
#endregion

#region Gráficos y Color
ColorValue: TypeAlias = Union[
    Tuple[int, int, int], 
    Tuple[int, int, int, int], 
    str,
    pg.Color
]
"""Representación de color en RGB/RGBA, hex string o Color de Pygame"""

AlphaValue: TypeAlias = int
"""Valor de transparencia alpha (0-255)"""

SurfaceType: TypeAlias = pg.Surface
"""Alias para superficies de Pygame"""

TextureID: TypeAlias = str
"""Identificador único de textura"""
#endregion

#region Sistema de Entidades
EntityID: TypeAlias = int
"""Identificador único de entidad"""

ComponentID: TypeAlias = str
"""Identificador de componente en formato 'type:subtype'"""

EntityQuery: TypeAlias = set[ComponentID]
"""Conjunto de componentes requeridos para consultar entidades"""
#endregion

#region Sistema de Eventos
EventCallback: TypeAlias = Callable[[Any], Optional[bool]]
"""Firma para callbacks de eventos (return True para consumir evento)"""

EventType: TypeAlias = Union[int, str]
"""Tipo de evento (pg.EventType o nombre personalizado)"""

EventData: TypeAlias = dict[str, Any]
"""Estructura de datos para información de eventos"""
#endregion

#region Sistema de Recursos
AssetPath: TypeAlias = Union[Path, str]
"""Ruta a recursos del juego (absoluta o relativa)"""

ResourceTag: TypeAlias = str
"""Etiqueta para agrupar recursos relacionados"""

LoaderFunction: TypeAlias = Callable[[AssetPath], Any]
"""Firma para funciones de carga de recursos"""
#endregion

#region Física y Movimiento
Velocity: TypeAlias = Tuple[float, float]
"""Vector de velocidad en 2D (dx, dy)"""

Direction: TypeAlias = Tuple[float, float]
"""Vector de dirección normalizado (x, y)"""

Force: TypeAlias = float
"""Magnitud de fuerza aplicada"""
#endregion

#region Interfaces del Sistema
class SupportsRendering(Protocol):
    """Protocolo para objetos renderizables"""
    def render(self, surface: SurfaceType, offset: Coordinate) -> None:
        ...
        
class SupportsUpdate(Protocol):
    """Protocolo para objetos actualizables"""
    def update(self, delta_time: float) -> None:
        ...

@runtime_checkable
class GameSystem(Protocol):
    """Protocolo para sistemas del juego"""
    def initialize(self) -> None: ...
    def update(self, delta_time: float) -> None: ...
    def shutdown(self) -> None: ...
#endregion

#region Configuraciones
DisplaySettings: TypeAlias = dict[str, Union[int, bool, str]]
"""Configuración de pantalla: resolución, fullscreen, vsync, etc."""

InputBindings: TypeAlias = dict[str, list[dict[str, Any]]]
"""Configuraciones de controles desde archivo JSON"""

GameSettings: TypeAlias = dict[str, Union[DisplaySettings, InputBindings]]
"""Configuración completa del juego"""
#endregion