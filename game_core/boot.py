import asyncio
import logging
from enum import Enum, auto
from typing import Dict, List, Awaitable, Optional, Callable
from pygame import mixer
from pathlib import Path
from dataclasses import dataclass

class BootStage(Enum):
    PRE_INIT = auto()
    ESSENTIAL = auto()
    BACKGROUND = auto()
    POST_INIT = auto()

@dataclass
class BootTask:
    name: str
    coroutine: Callable
    dependencies: List[str]
    retries: int = 3
    critical: bool = True

class BootManager:
    """Sistema de arranque modular con gestión de dependencias y recuperación de errores"""
    
    __slots__ = (
        'core', '_stages', '_progress', '_total_tasks', 
        '_current_stage', '_task_registry', '_progress_callback'
    )

    def __init__(self, core):
        self.core = core
        self._stages: Dict[BootStage, List[BootTask]] = {
            BootStage.PRE_INIT: [],
            BootStage.ESSENTIAL: [],
            BootStage.BACKGROUND: [],
            BootStage.POST_INIT: []
        }
        self._progress: Dict[str, float] = {}
        self._total_tasks = 0
        self._current_stage: BootStage = BootStage.PRE_INIT
        self._task_registry: Dict[str, BootTask] = {}
        self._progress_callback: Optional[Callable[[float], None]] = None

    def register_task(self, task: BootTask, stage: BootStage):
        """Registra una tarea de inicialización con metadatos"""
        self._stages[stage].append(task)
        self._task_registry[task.name] = task
        self._total_tasks += 1

    def set_progress_callback(self, callback: Callable[[float], None]):
        """Configura callback para reportar progreso"""
        self._progress_callback = callback

    async def cold_start(self):
        """Secuencia completa de arranque con gestión de errores"""
        try:
            await self._execute_stage(BootStage.PRE_INIT)
            await self._execute_stage(BootStage.ESSENTIAL)
            await self._execute_stage(BootStage.BACKGROUND)
            await self._execute_stage(BootStage.POST_INIT)
        except CriticalBootError as e:
            await self._cleanup_failed_startup()
            raise

    async def _execute_stage(self, stage: BootStage):
        """Ejecuta todas las tareas de una etapa con dependencias"""
        self._current_stage = stage
        tasks = self._resolve_dependencies(self._stages[stage])
        
        for task in tasks:
            await self._run_task_with_retry(task)
            self._update_progress()

    def _resolve_dependencies(self, tasks: List[BootTask]) -> List[BootTask]:
        """Ordena tareas según dependencias usando topological sort"""
        # Implementación de ordenación topológica aquí
        return tasks

    async def _run_task_with_retry(self, task: BootTask):
        """Ejecuta una tarea con reintentos y manejo de errores"""
        for attempt in range(task.retries):
            try:
                result = await task.coroutine()
                self._progress[task.name] = 1.0
                return result
            except Exception as e:
                logging.error(f"Boot task failed: {task.name} (attempt {attempt+1})")
                if attempt == task.retries - 1:
                    if task.critical:
                        raise CriticalBootError(f"Critical task failed: {task.name}") from e
                    else:
                        logging.warning(f"Non-critical task {task.name} failed")

    def _update_progress(self):
        """Actualiza el callback de progreso general"""
        if self._progress_callback:
            completed = sum(self._progress.values())
            self._progress_callback(completed / self._total_tasks)

    async def _cleanup_failed_startup(self):
        """Limpieza de recursos en caso de fallo crítico"""
        logging.critical("Performing emergency shutdown...")
        
        cleanup_tasks = [
            self._shutdown_display(),
            self._release_input_devices(),
            self._unload_audio()
        ]
        
        await asyncio.gather(*cleanup_tasks)
        self.core.reset_state()

    async def _shutdown_display(self):
        """Apagado seguro del subsistema gráfico"""
        if hasattr(self.core, 'display'):
            await self.core.display.cleanup()

    async def _release_input_devices(self):
        """Liberación de dispositivos de entrada"""
        if hasattr(self.core, 'input'):
            self.input.release_all()

    async def _unload_audio(self):
        """Descarga de recursos de audio"""
        if hasattr(self.core, 'audio'):
            self.audio.stop_all()

class CriticalBootError(Exception):
    """Excepción para errores críticos durante el arranque"""
    pass

# Tareas predefinidas para el sistema core
def core_boot_tasks(boot_manager: BootManager):
    """Registra las tareas esenciales del sistema"""
    boot_manager.register_task(
        BootTask(
            name='init_display',
            coroutine=_init_display,
            dependencies=[],
            critical=True
        ),
        BootStage.PRE_INIT
    )
    
    boot_manager.register_task(
        BootTask(
            name='load_input_profiles',
            coroutine=_load_input_profiles,
            dependencies=['init_display'],
            critical=True
        ),
        BootStage.ESSENTIAL
    )
    
    boot_manager.register_task(
        BootTask(
            name='init_audio_subsystem',
            coroutine=_init_audio,
            dependencies=[],
            critical=False
        ),
        BootStage.ESSENTIAL
    )

    async def _init_display(self):
        """Inicialización asíncrona del subsistema gráfico"""
        from .managers.display import DisplayManager
        try:
            self.core.display = DisplayManager(self.core)
            await self.core.display.initialize()
            self.core.display.set_vsync(True)
        except Exception as e:
            logging.critical("Failed to initialize display subsystem")
            raise

    async def _load_input_profiles(self):
        """Carga de configuraciones de entrada"""
        from .managers.input import InputManager
        try:
            self.core.input = InputManager(self.core)
            await self.core.input.load_profile('default')
        except Exception as e:
            logging.critical("Input system initialization failed")
            raise

    async def _init_audio(self):
        """Inicialización no crítica del subsistema de audio"""
        from .managers.audio import AudioManager
        try:
            self.core.audio = AudioManager(self.core)
            await self.core.audio.initialize()
        except Exception as e:
            logging.warning("Audio subsystem initialization failed")

def core_boot_tasks(boot_manager: BootManager):
    """Registra las tareas esenciales del sistema"""
    boot_manager.register_task(
        BootTask(
            name='init_display',
            coroutine=boot_manager._init_display,
            dependencies=[],
            critical=True
        ),
        BootStage.PRE_INIT
    )
    
    boot_manager.register_task(
        BootTask(
            name='load_input_profiles',
            coroutine=boot_manager._load_input_profiles,
            dependencies=['init_display'],
            critical=True
        ),
        BootStage.ESSENTIAL
    )
    
    boot_manager.register_task(
        BootTask(
            name='init_audio_subsystem',
            coroutine=boot_manager._init_audio,
            dependencies=[],
            critical=False
        ),
        BootStage.ESSENTIAL
    )