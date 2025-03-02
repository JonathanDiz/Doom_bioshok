import asyncio
import pygame as pg
import logging
import platform
import sys
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from typing import Optional, Dict, Any, Tuple, Callable

logger = logging.getLogger(__name__)

class Subsystem(IntEnum):
    """Subsistemas principales del motor"""
    VIDEO = auto()
    AUDIO = auto()
    INPUT = auto()
    EVENTS = auto()
    PHYSICS = auto()
    NETWORKING = auto()
    GUI = auto()

class ConfigPreset(Enum):
    """Configuraciones predefinidas para distintos entornos"""
    DESKTOP = auto()
    MOBILE = auto()
    SERVER = auto()
    DEBUG = auto()
    VR = auto()

@dataclass
class SystemConfig:
    """Configuración completa del sistema"""
    enabled_subsystems: Dict[Subsystem, bool]
    window_title: str = "NextGen Engine"
    resolution: Tuple[int, int] = (1280, 720)
    vsync: bool = True
    opengl_version: Tuple[int, int] = (4, 1)
    audio_settings: Dict[str, Any] = None
    cursor_visible: bool = False
    event_grab: bool = True
    physics_fps: int = 60
    network_port: int = 8080
    fullscreen: bool = False

class Initialization:
    """Sistema profesional de inicialización del motor con soporte multiplataforma"""
    
    __slots__ = (
        'config', '_initialized_subsystems', '_timers', 
        '_window', '_gl_context', '_performance_stats'
    )
    
    def __init__(self, config: SystemConfig = None):
        self.config = config or self._default_config()
        self._initialized_subsystems = set()
        self._timers = {}
        self._window = None
        self._gl_context = None
        self._performance_stats = {
            'init_time': 0.0,
            'subsystems': {}
        }

        self._configure_logging()
        self._log_system_info()
        
    def _default_config(self) -> SystemConfig:
        """Configuración óptima para escritorio moderno"""
        return SystemConfig(
            enabled_subsystems={
                Subsystem.VIDEO: True,
                Subsystem.AUDIO: True,
                Subsystem.INPUT: True,
                Subsystem.EVENTS: True,
                Subsystem.PHYSICS: False,
                Subsystem.GUI: True
            },
            audio_settings={
                'frequency': 48000,
                'channels': 6,
                'buffersize': 4096,
                'allowed_changes': pg.AUDIO_ALLOW_FREQUENCY_CHANGE
            }
        )

    async def async_initialize(self, systems: list) -> list:
        """Inicialización asíncrona con gestión de dependencias
        
        Args:
            systems (list): Lista de funciones/corutinas de inicialización
            
        Returns:
            list: Resultados de cada sistema inicializado
            
        Raises:
            RuntimeError: Si ocurre un error crítico durante la inicialización
        """
        try:
            results = await asyncio.gather(*[
                self._track_performance(system) 
                for system in systems
            ])
            
            logger.info("Sistemas inicializados asíncronamente")
            self._log_performance_stats()
            return results
        except Exception as e:
            self._emergency_shutdown()
            raise RuntimeError("Error en inicialización asíncrona") from e

    async def _track_performance(self, system: Callable) -> Any:
        """Mide y registra el tiempo de ejecución de un sistema
        
        Args:
            system (Callable): Función o corutina a medir
            
        Returns:
            Any: Resultado de la ejecución del sistema
        """
        start_time = pg.time.get_ticks()
        result = await system() if asyncio.iscoroutinefunction(system) else system()
        duration = pg.time.get_ticks() - start_time
        self._performance_stats['subsystems'][system.__name__] = duration
        return result

    def initialize(self) -> None:
        """Inicialización tradicional síncrona con control de errores
        
        Raises:
            RuntimeError: Si ocurre un error durante la inicialización
        """
        try:
            start_time = pg.time.get_ticks()
            
            self._init_foundations()
            self._init_video()
            self._init_audio()
            self._init_input()
            self._init_physics()
            self._init_network()
            self._init_gui()
            
            self._performance_stats['init_time'] = pg.time.get_ticks() - start_time
            self._log_performance_stats()
            
        except Exception as e:
            self._emergency_shutdown()
            raise RuntimeError("Error crítico en inicialización") from e

    def _init_foundations(self) -> None:
        """Inicialización básica del core del motor"""
        if not pg.get_init():
            pg.init()
            self._mark_initialized(Subsystem.VIDEO)
            logger.info("Core del motor inicializado")

    def _init_video(self) -> None:
        """Configuración avanzada del subsistema gráfico"""
        if not self.config.enabled_subsystems.get(Subsystem.VIDEO):
            return

        try:
            self._create_gl_context()
            self._configure_window()
            self._enable_hardware_features()
            logger.info("Subsistema gráfico listo")
        except pg.error as e:
            logger.error("Error en subsistema gráfico: %s", e)
            if self.config.enabled_subsystems[Subsystem.VIDEO]:
                raise

    def _create_gl_context(self) -> None:
        """Crea contexto gráfico con parámetros específicos"""
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, self.config.opengl_version[0])
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, self.config.opengl_version[1])
        
        self._window = pg.display.set_mode(
            self.config.resolution,
            flags=pg.OPENGL | pg.DOUBLEBUF | (pg.FULLSCREEN if self.config.fullscreen else 0),
            vsync=self.config.vsync
        )
        self._gl_context = pg.display.get_window()

    def _configure_window(self) -> None:
        """Configura propiedades de la ventana principal"""
        pg.display.set_caption(self.config.window_title)
        pg.mouse.set_visible(self.config.cursor_visible)
        pg.event.set_grab(self.config.event_grab)

    def _enable_hardware_features(self) -> None:
        """Habilita características avanzadas de hardware"""
        if self._gl_context:
            pg.glEnable(pg.GL_MULTISAMPLE)
            pg.glEnable(pg.GL_DEPTH_TEST)
            pg.glEnable(pg.GL_BLEND)
            pg.glBlendFunc(pg.GL_SRC_ALPHA, pg.GL_ONE_MINUS_SRC_ALPHA)

    def _init_audio(self) -> None:
        """Inicialización del subsistema de audio"""
        if self.config.enabled_subsystems.get(Subsystem.AUDIO):
            try:
                pg.mixer.init(**self.config.audio_settings)
                self._mark_initialized(Subsystem.AUDIO)
                logger.info("Subsistema de audio listo")
            except pg.error as e:
                logger.error("Error en audio: %s", e)

    def _init_input(self) -> None:
        """Configuración de dispositivos de entrada"""
        if self.config.enabled_subsystems.get(Subsystem.INPUT):
            pg.joystick.init()
            self._mark_initialized(Subsystem.INPUT)
            logger.info("Dispositivos de entrada detectados: %d", pg.joystick.get_count())

    def _init_physics(self) -> None:
        """Inicialización del motor físico"""
        if self.config.enabled_subsystems.get(Subsystem.PHYSICS):
            pg.physics.init()
            pg.physics.set_fps(self.config.physics_fps)
            self._mark_initialized(Subsystem.PHYSICS)
            logger.info("Motor físico configurado a %d FPS", self.config.physics_fps)

    def _init_network(self) -> None:
        """Configuración inicial de red"""
        if self.config.enabled_subsystems.get(Subsystem.NETWORKING):
            pg.network.init()
            logger.info("Subsistema de red listo en puerto %d", self.config.network_port)

    def _init_gui(self) -> None:
        """Inicialización del sistema GUI"""
        if self.config.enabled_subsystems.get(Subsystem.GUI):
            pg.gui.init()
            self._mark_initialized(Subsystem.GUI)
            logger.info("Sistema GUI inicializado")

    def shutdown(self) -> None:
        """Apagado controlado de todos los subsistemas"""
        logger.info("Iniciando apagado controlado...")
        self._release_subsystems()
        pg.quit()
        logger.info("Motor apagado correctamente")

    def _emergency_shutdown(self) -> None:
        """Procedimiento de emergencia para fallos críticos"""
        logger.critical("APAGADO DE EMERGENCIA!")
        pg.quit()
        sys.exit(1)

    def _release_subsystems(self) -> None:
        """Liberación ordenada de recursos por subsistema"""
        release_order = [
            Subsystem.GUI,
            Subsystem.PHYSICS,
            Subsystem.NETWORKING,
            Subsystem.AUDIO,
            Subsystem.INPUT,
            Subsystem.VIDEO
        ]
        
        for subsystem in release_order:
            if subsystem in self._initialized_subsystems:
                getattr(self, f"_release_{subsystem.name.lower()}")()
                logger.debug("Subsistema %s liberado", subsystem.name)

    def _release_video(self) -> None:
        """Libera recursos gráficos"""
        if self._gl_context:
            pg.display.quit()

    def _release_audio(self) -> None:
        """Libera recursos de audio"""
        pg.mixer.quit()

    def _release_input(self) -> None:
        """Libera dispositivos de entrada"""
        pg.joystick.quit()

    def _mark_initialized(self, subsystem: Subsystem) -> None:
        """Registro de subsistemas inicializados"""
        self._initialized_subsystems.add(subsystem)
        logger.debug("Subsistema %s marcado como listo", subsystem.name)

    def _configure_logging(self) -> None:
        """Configuración avanzada del sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('engine.log'),
                logging.StreamHandler()
            ]
        )

    def _log_system_info(self) -> None:
        """Registro de información técnica del sistema"""
        logger.info("\n".join([
            "=== INFORMACIÓN DEL SISTEMA ===",
            f"Sistema Operativo: {platform.platform()}",
            f"Arquitectura: {platform.machine()}",
            f"Procesador: {platform.processor()}",
            f"Python: {platform.python_version()}",
            f"PyGame: {pg.version.ver}",
            f"OpenGL: {self.config.opengl_version}",
            "==============================="
        ]))

    def _log_performance_stats(self) -> None:
        """Muestra estadísticas de rendimiento de inicialización"""
        logger.info("\n".join([
            "=== ESTADÍSTICAS DE RENDIMIENTO ===",
            f"Tiempo total de inicialización: {self._performance_stats['init_time']}ms",
            "Tiempos por subsistema:",
            *[f"- {name}: {time}ms" for name, time in self._performance_stats['subsystems'].items()],
            "==================================="
        ]))

    @classmethod
    def create_preset(cls, preset: ConfigPreset) -> 'Initialization':
        """Factoría para configuraciones predefinidas
        
        Args:
            preset (ConfigPreset): Presección deseada
            
        Returns:
            Initialization: Instancia configurada
        """
        configs = {
            ConfigPreset.DESKTOP: SystemConfig(
                enabled_subsystems={s: True for s in Subsystem},
                opengl_version=(4, 6),
                resolution=(1920, 1080),
                vsync=True
            ),
            ConfigPreset.MOBILE: SystemConfig(
                enabled_subsystems={Subsystem.VIDEO: True, Subsystem.INPUT: True},
                opengl_version=(3, 1),
                resolution=(1280, 720),
                vsync=False
            ),
            ConfigPreset.SERVER: SystemConfig(
                enabled_subsystems={Subsystem.NETWORKING: True},
                vsync=False
            ),
            ConfigPreset.DEBUG: SystemConfig(
                enabled_subsystems={s: True for s in Subsystem},
                cursor_visible=True,
                event_grab=False
            ),
            ConfigPreset.VR: SystemConfig(
                enabled_subsystems={Subsystem.VIDEO: True, Subsystem.INPUT: True},
                opengl_version=(4, 5),
                resolution=(2160, 1200),
                vsync=True
            )
        }
        return cls(configs[preset])