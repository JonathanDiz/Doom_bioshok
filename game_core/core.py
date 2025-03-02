import pygame as pg
import asyncio
import logging
import platform
import time
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass
from pygame.locals import *

from display_manager import DisplayManager
from settings import GAME_CONFIG
from .managers.resource import ResourceManager
from .initialization import PyGameInitialization

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .managers import InputManager, AudioManager
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
    """Núcleo principal del juego con gestión avanzada de subsistemas"""
    
    __slots__ = (
        'running', 'clock', 'resource', 'boot', 'display',
        'input', 'audio', '_delta_time', '_system_info',
        '_frame_times', '_target_fps', '_vsync', '_initialized'
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
            
        # Configuración inicial
        self.initializer = PyGameInitialization(config=GAME_CONFIG)
        self.initializer.configure(
            window_title="Mi Juego",
            vsync=True,
            gl_version=(3, 3))
        
        # Estado del sistema
        self.running = False
        self._delta_time: float = 0.0
        self._frame_times: list = []
        self._target_fps: int = GAME_CONFIG['render']['target_fps']
        self._vsync: bool = GAME_CONFIG['render']['vsync']
        
        # Subsistemas
        self.clock: pg.time.Clock = None
        self.resource: ResourceManager = ResourceManager(self)
        self.boot: Optional['BootManager'] = None
        self.display: DisplayManager = None
        self.input: Optional['InputManager'] = None
        self.audio: Optional['AudioManager'] = None
        
        # Información del sistema
        self._system_info: Optional[SystemInfo] = None
        
        self._initialized = True

    async def initialize(self):
        """Inicialización asíncrona del núcleo"""
        try:
            await self._initialize_pygame()
            self._initialize_subsystems()
            self._log_system_info()
            self.running = True
        except Exception as e:
            logger.critical("Fallo en inicialización", exc_info=True)
            await self.emergency_shutdown()
            raise GameCoreError("Error crítico durante inicialización") from e

    async def _initialize_pygame(self):
        """Inicialización segura de Pygame con capacidades extendidas"""
        await self.initializer.async_initialize(
            subsystems=[
                'display',
                'audio',
                'input'
            ]
        )
        self._system_info = SystemInfo(
            pygame_version=pg.version.ver,
            python_version=platform.python_version(),
            platform=platform.platform(),
            renderer=pg.display.get_driver(),
            opengl_version=pg.display.gl_get_attribute(pg.GL_VERSION) or "N/A"
        )

    def _initialize_subsystems(self):
        """Configuración de subsistemas principales"""
        self.clock = pg.time.Clock()
        self.display = DisplayManager(self)
        
        if GAME_CONFIG['audio']['enabled']:
            self._initialize_audio_subsystem()
            
        if GAME_CONFIG['input']['enabled']:
            self._initialize_input_subsystem()

    def _initialize_audio_subsystem(self):
        """Configuración avanzada del sistema de audio"""
        from .managers.audio import AudioManager
        self.audio = AudioManager(self)
        self.audio.configure(**GAME_CONFIG['audio'])

    def _initialize_input_subsystem(self):
        """Configuración de dispositivos de entrada"""
        from .managers.input import InputManager
        self.input = InputManager(self)
        self.input.configure(**GAME_CONFIG['controls'])

    def _log_system_info(self):
        """Registro de información técnica del sistema"""
        logger.info("\n".join([
            "=== Sistema Info ===",
            f"PyGame: {self._system_info.pygame_version}",
            f"Python: {self._system_info.python_version}",
            f"Plataforma: {self._system_info.platform}",
            f"Renderizador: {self._system_info.renderer}",
            f"OpenGL: {self._system_info.opengl_version}",
            "===================="
        ]))

    async def quick_boot(self):
        """Secuencia de arranque rápido optimizada"""
        try:
            from .boot import BootManager
            self.boot = BootManager(self)
            await self.boot.cold_start()
            logger.info("Arranque completado exitosamente")
        except Exception as e:
            logger.critical(f"Fallo en arranque: {e}")
            await self.emergency_shutdown()
            raise

    async def emergency_shutdown(self):
        """Apagado de emergencia controlado"""
        logger.error("Iniciando apagado de emergencia...")
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
        self._frame_times.append(time.perf_counter())
        if len(self._frame_times) > 120:
            self._frame_times.pop(0)

    def end_frame(self):
        """Finaliza el frame y sincroniza"""
        self._delta_time = time.perf_counter() - self._frame_times[-1]
        if self._vsync:
            pg.display.flip()

    @property
    def delta_time(self) -> float:
        """Tiempo transcurrido desde el último frame en segundos"""
        return self._delta_time

    @property
    def fps(self) -> float:
        """FPS actuales suavizados (media móvil de 60 frames)"""
        if len(self._frame_times) < 2:
            return 0.0
        return 60 / sum(self._frame_times[-60:] - self._frame_times[-61:-1])

    def set_target_fps(self, fps: int):
        """Configura el objetivo de FPS (0 para ilimitado)"""
        self._target_fps = max(0, fps)
        logger.info(f"Objetivo de FPS configurado a {self._target_fps}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        pg.quit()