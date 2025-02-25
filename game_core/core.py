import pygame as pg
from typing import Optional, TYPE_CHECKING
from .managers.resource import ResourceManager
from .utils.async_tools import AsyncLoader

if TYPE_CHECKING:
    from .boot import BootManager

class GameCore:
    """Núcleo mínimo para inicio ultrarrápido"""
    __slots__ = ('running', 'clock', 'resource', 'boot', '_display')
    
    def __init__(self):
        # Estado esencial
        self.running = True
        self.screen = None
        self.clock: pg.time.Clock = pg.time.Clock()
        
        # Subsistemas principales
        self.resource: ResourceManager = ResourceManager(self)
        self.boot: Optional['BootManager'] = None
        self._display: Optional[pg.Surface] = None
        
        # Configuración inicial crítica
        self._init_essentials()
    
    def _init_essentials(self):
        """Configuración mínima para mostrar pantalla"""
        pg.init()
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        self._display = pg.display.set_mode((1024, 768), pg.OPENGL | pg.DOUBLEBUF)
    
    @property
    def display(self) -> pg.Surface:
        """Acceso seguro a la superficie de display"""
        if self._display is None:
            raise RuntimeError("Display no inicializado")
        return self._display
    
    async def quick_boot(self):
        """Arranque rápido con carga en segundo plano"""
        from .boot import BootManager
        self.boot = BootManager(self)
        await self.boot.start_async_load()