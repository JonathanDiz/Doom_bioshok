import asyncio
import logging
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

class BootStage(Enum):
    """Etapas del proceso de arranque"""
    PRE_INIT = auto()
    ESSENTIAL = auto()
    BACKGROUND = auto()
    POST_INIT = auto()

@dataclass
class BootTask:
    """Estructura para gestionar tareas de inicialización"""
    name: str
    coroutine: Callable[[], Awaitable[None]]
    dependencies: List[str]
    stage: BootStage
    retries: int = 3
    critical: bool = True
    weight: float = 1.0

class CriticalBootError(Exception):
    """Excepción para errores críticos durante el arranque"""
    pass

class BootManager:
    """Sistema avanzado de arranque con gestión de dependencias y recuperación de errores"""
    
    __slots__ = (
        'core', '_tasks', '_progress', '_total_weight',
        '_current_stage', '_task_dependencies', '_progress_callback'
    )

    def __init__(self, core):
        self.core = core
        self._tasks: Dict[BootStage, List[BootTask]] = defaultdict(list)
        self._progress: Dict[str, float] = {}
        self._total_weight: float = 0.0
        self._current_stage: Optional[BootStage] = None
        self._task_dependencies: Dict[str, List[str]] = {}
        self._progress_callback: Optional[Callable[[float], None]] = None

        self._register_core_tasks()

    def _register_core_tasks(self):
        """Registra tareas esenciales del sistema"""
        self.add_task(
            BootTask(
                name='init_display',
                coroutine=self._init_display,
                dependencies=[],
                stage=BootStage.PRE_INIT,
                critical=True
            )
        )
        
        self.add_task(
            BootTask(
                name='load_input_profiles',
                coroutine=self._load_input_profiles,
                dependencies=['init_display'],
                stage=BootStage.ESSENTIAL,
                critical=True
            )
        )
        
        self.add_task(
            BootTask(
                name='init_audio_subsystem',
                coroutine=self._init_audio,
                dependencies=[],
                stage=BootStage.ESSENTIAL,
                critical=False
            )
        )

    def add_task(self, task: BootTask):
        """Añade una nueva tarea de inicialización"""
        self._tasks[task.stage].append(task)
        self._task_dependencies[task.name] = task.dependencies
        self._total_weight += task.weight

    def set_progress_callback(self, callback: Callable[[float], None]):
        """Configura callback para reportar progreso"""
        self._progress_callback = callback

    async def cold_start(self):
        """Ejecuta la secuencia completa de arranque"""
        try:
            for stage in BootStage:
                await self._execute_stage(stage)
        except CriticalBootError as e:
            await self._emergency_shutdown()
            raise

    async def _execute_stage(self, stage: BootStage):
        """Ejecuta todas las tareas de una etapa"""
        logger.info(f"Iniciando etapa de arranque: {stage.name}")
        self._current_stage = stage
        
        tasks = self._topological_sort(self._tasks[stage])
        for task in tasks:
            await self._execute_task_with_retry(task)
            self._update_progress(task)

    def _topological_sort(self, tasks: List[BootTask]) -> List[BootTask]:
        """Ordena tareas basado en dependencias usando Kahn's algorithm"""
        task_map = {task.name: task for task in tasks}
        in_degree = {task.name: 0 for task in tasks}
        graph = defaultdict(list)
        queue = []

        # Construir grafo de dependencias
        for task in tasks:
            for dep in self._task_dependencies.get(task.name, []):
                if dep in task_map:
                    graph[dep].append(task.name)
                    in_degree[task.name] += 1

        # Inicializar cola con nodos sin dependencias
        for task in tasks:
            if in_degree[task.name] == 0:
                queue.append(task.name)

        result = []
        while queue:
            current = queue.pop(0)
            result.append(task_map[current])
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Verificar ciclos
        if len(result) != len(tasks):
            raise CriticalBootError("Dependencias cíclicas detectadas")
            
        return result

    async def _execute_task_with_retry(self, task: BootTask):
        """Ejecuta una tarea con reintentos y manejo de errores"""
        for attempt in range(1, task.retries + 1):
            try:
                logger.debug(f"Ejecutando tarea: {task.name} (intento {attempt})")
                await task.coroutine()
                return
            except Exception as e:
                if attempt == task.retries:
                    logger.error(f"Fallo en tarea: {task.name}")
                    if task.critical:
                        raise CriticalBootError(f"Tarea crítica fallida: {task.name}") from e
                    logger.warning(f"Tarea no crítica {task.name} falló")

    def _update_progress(self, task: BootTask):
        """Actualiza el progreso y notifica"""
        self._progress[task.name] = 1.0
        if self._progress_callback:
            completed = sum(self._progress.values())
            self._progress_callback(completed / self._total_weight)

    async def _init_display(self):
        """Inicializa el subsistema gráfico"""
        from .managers.display import DisplayManager
        try:
            self.core.display = DisplayManager(self.core)
            await self.core.display.initialize()
            logger.info("Subsistema gráfico inicializado")
        except Exception as e:
            logger.critical("Error inicializando display: %s", e)
            raise

    async def _load_input_profiles(self):
        """Carga configuraciones de entrada"""
        from .managers.input import InputManager
        try:
            self.core.input = InputManager(self.core)
            await self.core.input.load_profile('default')
            logger.info("Perfiles de entrada cargados")
        except Exception as e:
            logger.critical("Error cargando perfiles: %s", e)
            raise

    async def _init_audio(self):
        """Inicializa el subsistema de audio"""
        from .managers.audio import AudioManager
        try:
            self.core.audio = AudioManager(self.core)
            await self.core.audio.initialize()
            logger.info("Subsistema de audio inicializado")
        except Exception as e:
            logger.warning("Error no crítico en audio: %s", e)

    async def _emergency_shutdown(self):
        """Apagado de emergencia controlado"""
        logger.critical("Realizando limpieza de emergencia...")
        shutdown_tasks = []
        
        if hasattr(self.core, 'display'):
            shutdown_tasks.append(self.core.display.cleanup())
        if hasattr(self.core, 'audio'):
            shutdown_tasks.append(self.core.audio.stop_all())
        
        await asyncio.gather(*shutdown_tasks)
        logger.info("Recursos liberados exitosamente")