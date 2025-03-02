import asyncio
import pygame as pg
import logging
import platform
import sys
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class Subsystem(IntEnum):
    VIDEO = auto()
    AUDIO = auto()
    INPUT = auto()
    EVENTS = auto()
    JOYSTICK = auto()
    GUI = auto()

class ConfigPreset(Enum):
    DESKTOP = auto()
    EMBEDDED = auto()
    SERVER = auto()
    DEBUG = auto()

@dataclass
class SystemConfig:
    enabled_subsystems: Dict[Subsystem, bool]
    window_title: str = "PyGame Application"
    vsync: bool = True
    opengl_version: Tuple[int, int] = (3, 3)
    audio_settings: Dict[str, Any] = None
    cursor_visible: bool = False
    event_grab: bool = True
    timer_events: Dict[int, int] = None

class PyGameInitialization:
    """Sistema profesional de inicialización de Pygame con gestión de subsistemas"""
    
    def __init__(self, config: SystemConfig = None):
        self.config = config or self._default_config()
        self._initialized_subsystems = set()
        self._timers = {}
        self._window = None
        self._gl_context_created = False

        self._configure_logging()
        self._log_system_info()
        
    def _default_config(self) -> SystemConfig:
        """Configuración predeterminada para entornos de escritorio"""
        return SystemConfig(
            enabled_subsystems={
                Subsystem.VIDEO: True,
                Subsystem.AUDIO: True,
                Subsystem.INPUT: True,
                Subsystem.EVENTS: True,
                Subsystem.JOYSTICK: False,
                Subsystem.GUI: False
            },
            audio_settings={
                'frequency': 44100,
                'size': -16,
                'channels': 2,
                'buffer': 4096
            }
        )

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    async def async_initialize(self, systems: list):
        """Versión asíncrona para inicialización moderna"""
        await asyncio.gather(*[system() for system in systems])
        logger.info("Sistemas inicializados asíncronamente")

    def initialize(self):
        """Inicialización completa del sistema con gestión de errores"""
        try:
            self._init_foundations()
            self._init_video()
            self._init_audio()
            self._init_input()
            self._init_custom_timers()
            self._finalize_setup()
        except Exception as e:
            self._emergency_shutdown()
            raise RuntimeError("Initialization failed") from e

    def _init_foundations(self):
        """Inicialización básica de Pygame"""
        if not pg.get_init():
            pg.init()
            self._mark_initialized(Subsystem.VIDEO)
            logger.info("Pygame core initialized")

    def _init_video(self):
        """Configuración avanzada del subsistema de video"""
        if not self.config.enabled_subsystems.get(Subsystem.VIDEO, False):
            return

        try:
            self._create_gl_context()
            self._set_window_properties()
            self._apply_hardware_acceleration()
            logger.info("Video subsystem initialized")
        except pg.error as e:
            logger.error("Failed to initialize video subsystem")
            if self.config.enabled_subsystems[Subsystem.VIDEO]:
                raise

    def _create_gl_context(self):
        """Crea contexto OpenGL con versión específica"""
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, self.config.opengl_version[0])
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, self.config.opengl_version[1])
        
        self._window = pg.display.set_mode(
            (1280, 720), 
            flags=pg.OPENGL | pg.DOUBLEBUF,
            vsync=self.config.vsync
        )
        self._gl_context_created = True

    def _set_window_properties(self):
        """Configura propiedades de la ventana"""
        pg.display.set_caption(self.config.window_title)
        pg.mouse.set_visible(self.config.cursor_visible)
        pg.event.set_grab(self.config.event_grab)

    def _apply_hardware_acceleration(self):
        """Habilita características avanzadas de hardware"""
        if self._gl_context_created:
            pg.glEnable(pg.GL_MULTISAMPLE)
            pg.glEnable(pg.GL_DEPTH_TEST)

    def _init_audio(self):
        """Inicialización del subsistema de audio"""
        if self.config.enabled_subsystems.get(Subsystem.AUDIO, False):
            try:
                pg.mixer.init(**self.config.audio_settings)
                self._mark_initialized(Subsystem.AUDIO)
                logger.info("Audio subsystem initialized")
            except pg.error as e:
                logger.warning(f"Audio initialization failed: {e}")

    def _init_input(self):
        """Configuración de dispositivos de entrada"""
        if self.config.enabled_subsystems.get(Subsystem.INPUT, False):
            pg.joystick.init()
            self._mark_initialized(Subsystem.INPUT)
            logger.info(f"Input devices detected: {pg.joystick.get_count()}")

    def _init_custom_timers(self):
        """Configuración de eventos temporizados personalizados"""
        if self.config.timer_events:
            for event_id, interval in self.config.timer_events.items():
                pg.time.set_timer(event_id, interval)
                self._timers[event_id] = interval
                logger.debug(f"Timer configured: {event_id} every {interval}ms")

    def _finalize_setup(self):
        """Pasos finales de configuración"""
        if self.config.enabled_subsystems.get(Subsystem.GUI, False):
            self._init_gui_subsystem()

    def _init_gui_subsystem(self):
        """Inicialización de componentes GUI avanzados"""
        # Implementación específica del framework GUI
        pass

    def shutdown(self):
        """Apagado controlado de todos los subsistemas"""
        logger.info("Initiating controlled shutdown...")
        self._release_subsystems()
        pg.quit()
        logger.info("System shutdown completed")

    def _emergency_shutdown(self):
        """Procedimiento de emergencia para fallos críticos"""
        logger.critical("Performing emergency shutdown!")
        pg.quit()
        sys.exit(1)

    def _release_subsystems(self):
        """Liberación ordenada de recursos"""
        if Subsystem.AUDIO in self._initialized_subsystems:
            pg.mixer.quit()
        if Subsystem.INPUT in self._initialized_subsystems:
            pg.joystick.quit()

    def _mark_initialized(self, subsystem: Subsystem):
        """Registro de subsistemas inicializados"""
        self._initialized_subsystems.add(subsystem)

    def _configure_logging(self):
        """Configuración del sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _log_system_info(self):
        """Registro de información del sistema"""
        logger.info("\n".join([
            "=== System Information ===",
            f"OS: {platform.platform()}",
            f"Python: {platform.python_version()}",
            f"Pygame: {pg.version.ver}",
            f"OpenGL: {self.config.opengl_version}",
            "=========================="
        ]))

    @staticmethod
    def create_preset(preset: ConfigPreset) -> 'PyGameInitialization':
        """Factory method para configuraciones predefinidas"""
        configs = {
            ConfigPreset.DESKTOP: SystemConfig(
                enabled_subsystems={s: True for s in Subsystem},
                opengl_version=(4, 1),
                audio_settings={'frequency': 48000, 'channels': 6}
            ),
            ConfigPreset.EMBEDDED: SystemConfig(
                enabled_subsystems={Subsystem.VIDEO: True, Subsystem.INPUT: True},
                opengl_version=(2, 1),
                cursor_visible=True,
                event_grab=False
            ),
            ConfigPreset.SERVER: SystemConfig(
                enabled_subsystems={Subsystem.VIDEO: False, Subsystem.EVENTS: True},
                cursor_visible=True
            ),
            ConfigPreset.DEBUG: SystemConfig(
                enabled_subsystems={s: True for s in Subsystem},
                cursor_visible=True,
                event_grab=False,
                timer_events={pg.USEREVENT: 1000}
            )
        }
        return PyGameInitialization(configs[preset])