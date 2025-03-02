import pygame as pg
import asyncio
import logging
import platform
import time
from typing import Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
from pygame.locals import *

from game_core.managers.resource import ResourceManager
from game_core import PyGameInitialization
from settings import GAME_CONFIG

# Configuración inicial de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('GameCore')

if TYPE_CHECKING:
    from .managers import DisplayManager, InputManager, AudioManager
    from .boot import BootManager

@dataclass
class SystemInfo:
    pygame_version: str
    python_version: str
    platform: str
    renderer: str
    opengl_version: str

class GameCoreError(Exception):
    """Excepción base para errores críticos del núcleo"""
    pass

class GameCore:
    """Motor central del juego con gestión de subsistemas y recursos"""
    
    __slots__ = (
        'running', '_display', 'clock', 'resource', 
        'boot', 'display', 'input', 'audio', '_delta_time',
        '_system_info', '_frame_times', '_target_fps', '_vsync'
    )
    
    _instance: Optional['GameCore'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Configuración de inicialización
        self.initializer = PyGameInitialization(
            config=self._load_config()
        )
        
        # Usando el inicializador
        self.initializer.configure({
            'window_title': "Mi Juego",
            'vsync': True
        })

        self.initialization = PyGameInitialization(config=GAME_CONFIG)  # ✅ Usa la clase
        self.initialization.initialize()
        
    async def quick_boot(self):
        """Usando Initialization para el proceso de arranque"""
        await self.initialization.async_initialize(
            systems=[self._init_pygame, self._init_display]
        )

        # Estado del sistema
        self.running = True
        self._delta_time: float = 0.0
        self._frame_times: list = []
        self._target_fps: int = 144
        self._vsync: bool = True
        
        # Subsistemas
        self.resource: ResourceManager = ResourceManager(self)
        self.boot: Optional['BootManager'] = None
        self.display: Optional['DisplayManager'] = None
        self.input: Optional['InputManager'] = None
        self.audio: Optional['AudioManager'] = None
        
        # Información del sistema
        self._system_info: Optional[SystemInfo] = None
        
        self._init_pygame()
        self._init_subsystems()
        self._log_system_info()
        
        self._initialized = True

    def _init_pygame(self):
        """Inicialización segura de Pygame con fallbacks"""
        try:
            pg.init()
            pg.mixer.pre_init(44100, -16, 2, 4096)
            pg.display.init()
            pg.joystick.init()
            self._check_opengl_support()
        except pg.error as e:
            logger.critical(f"Error inicializando Pygame: {e}")
            raise GameCoreError("Fallo crítico en inicialización de Pygame") from e

    def _check_opengl_support(self):
        """Verifica capacidades OpenGL mínimas"""
        gl_version = (3, 3)
        try:
            pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
            pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, gl_version[0])
            pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, gl_version[1])
        except pg.error as e:
            logger.warning(f"OpenGL {gl_version} no soportado: {e}")
            self._vsync = False

    def _init_subsystems(self):
        """Inicialización diferida de subsistemas no críticos"""
        self.clock = pg.time.Clock()
        self._system_info = SystemInfo(
            pygame_version=pg.version.ver,
            python_version=platform.python_version(),
            platform=platform.platform(),
            renderer=pg.display.get_driver(),
            opengl_version=pg.display.gl_get_attribute(pg.GL_VERSION) or "N/A"
        )

    def _log_system_info(self):
        """Registro detallado de información del sistema"""
        logger.info("\n".join([
            "=== System Info ===",
            f"PyGame: {self._system_info.pygame_version}",
            f"Python: {self._system_info.python_version}",
            f"Platform: {self._system_info.platform}",
            f"Renderer: {self._system_info.renderer}",
            f"OpenGL: {self._system_info.opengl_version}",
            "==================="
        ]))

    async def quick_boot(self, config_path: Optional[str] = None):
        """Arranque rápido con inicialización paralela de subsistemas"""
        from .boot import BootManager
        try:
            self.boot = BootManager(self)
            await self.boot.cold_start()
            logger.info("Boot sequence completed successfully")
        except Exception as e:
            logger.critical(f"Boot failed: {e}")
            await self.emergency_shutdown()
            raise

    async def emergency_shutdown(self):
        """Apagado de emergencia controlado"""
        logger.error("Initiating emergency shutdown...")
        self.running = False
        
        shutdown_tasks = []
        if self.display:
            shutdown_tasks.append(self.display.cleanup())
        if self.audio:
            shutdown_tasks.append(self.audio.stop_all())
        
        await asyncio.gather(*shutdown_tasks)
        pg.quit()

    def begin_frame(self):
        """Prepara el nuevo frame de renderizado"""
        self.clock.tick(self._target_fps)
        start_time = time.perf_counter()
        
        # Actualización de delta time con media móvil
        if len(self._frame_times) >= 60:
            self._frame_times.pop(0)
        self._frame_times.append(start_time)

    def end_frame(self):
        """Finaliza el frame y sincroniza"""
        end_time = time.perf_counter()
        self._delta_time = end_time - self._frame_times[-1]
        if self._vsync:
            pg.display.flip()

    @property
    def delta_time(self) -> float:
        """Tiempo transcurrido desde el último frame en segundos"""
        return self._delta_time

    @property
    def fps(self) -> float:
        """FPS actuales suavizados"""
        if len(self._frame_times) < 2:
            return 0.0
        return 1.0 / (sum(self._frame_times[-10:]) / len(self._frame_times[-10:]))

    def set_target_fps(self, fps: int):
        """Configura el objetivo de FPS (0 para ilimitado)"""
        self._target_fps = max(0, fps)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        pg.quit()