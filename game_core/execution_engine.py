import asyncio
import logging
import os
import time
import concurrent.futures
from enum import IntEnum, auto
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial
from heapq import heappush, heappop

logger = logging.getLogger(__name__)
T = TypeVar('T')

class TaskPriority(IntEnum):
    """Prioridades de ejecución para gestión de recursos"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

class ExecutionMode(IntEnum):
    """Modos de ejecución disponibles"""
    THREAD = auto()
    PROCESS = auto()
    ASYNC = auto()

@dataclass(order=True)
class Task:
    """Estructura para gestión de tareas con prioridad"""
    priority: TaskPriority
    timestamp: float = field(compare=False)
    task_id: int = field(compare=False)
    func: Callable = field(compare=False)
    args: Tuple = field(default_factory=tuple, compare=False)
    kwargs: Dict[str, Any] = field(default_factory=dict, compare=False)
    callback: Optional[Callable] = field(default=None, compare=False)
    retries: int = field(default=3, compare=False)
    mode: ExecutionMode = field(default=ExecutionMode.THREAD, compare=False)

class ExecutionEngine:
    """Motor de ejecución avanzado con gestión de recursos y prioridades"""
    
    _instance = None
    __slots__ = (
        '_loop', '_io_executor', '_cpu_executor', '_task_queue',
        '_metrics', '_running_tasks', '_next_task_id', '_shutdown_flag',
        '_lock'
    )

    def __new__(cls):
        """Implementación singleton thread-safe"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__()
        return cls._instance

    def __init__(self):
        """Inicialización privada del motor"""
        self._loop = asyncio.get_event_loop()
        self._io_executor = ThreadPoolExecutor(
            max_workers=self._calculate_optimal_workers('io'),
            thread_name_prefix='IO-Worker-'
        )
        self._cpu_executor = ProcessPoolExecutor(
            max_workers=self._calculate_optimal_workers('cpu')
        )
        self._task_queue = []
        self._metrics = self._init_metrics()
        self._running_tasks = set()
        self._next_task_id = 0
        self._shutdown_flag = False
        self._lock = asyncio.Lock()

    def _init_metrics(self) -> Dict[str, Any]:
        """Inicializa el sistema de métricas"""
        return {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'avg_exec_time': 0.0,
            'max_exec_time': 0.0,
            'min_exec_time': float('inf'),
            'queue_size': 0,
            'active_workers': 0,
            'total_retries': 0
        }

    def _calculate_optimal_workers(self, pool_type: str) -> int:
        """Calcula la configuración óptima de workers"""
        cores = os.cpu_count() or 4
        return {
            'io': min(32, (cores * 4)),
            'cpu': max(1, cores - 1)
        }[pool_type]

    async def submit(
        self,
        func: Callable[..., T],
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        retries: int = 3,
        mode: ExecutionMode = ExecutionMode.THREAD,
        **kwargs
    ) -> T:
        """Envía una tarea para ejecución con gestión de prioridades"""
        async with self._lock:
            if self._shutdown_flag:
                raise RuntimeError("Motor en proceso de apagado")

            task = Task(
                priority=priority,
                timestamp=time.monotonic(),
                task_id=self._next_task_id,
                func=func,
                args=args,
                kwargs=kwargs,
                retries=retries,
                mode=mode
            )
            self._next_task_id += 1
            
            heappush(self._task_queue, task)
            self._metrics['queue_size'] += 1
            
        return await self._process_task(task)

    async def _process_task(self, task: Task) -> Any:
        """Ejecuta la tarea con el executor apropiado"""
        async with self._lock:
            self._metrics['queue_size'] -= 1
            self._metrics['active_workers'] += 1
            self._running_tasks.add(task.task_id)

        try:
            start_time = time.monotonic()
            executor = self._select_executor(task.mode)
            
            result = await self._loop.run_in_executor(
                executor,
                partial(self._execute_with_retries, task)
            )
            
            exec_time = time.monotonic() - start_time
            self._update_metrics(success=True, exec_time=exec_time)
            
            return result
        except Exception as e:
            self._update_metrics(success=False)
            logger.error(f"Task failed: {task.func.__name__} - {str(e)}")
            raise
        finally:
            async with self._lock:
                self._metrics['active_workers'] -= 1
                self._running_tasks.discard(task.task_id)

    def _select_executor(self, mode: ExecutionMode):
        """Selecciona el executor apropiado según el modo"""
        return {
            ExecutionMode.THREAD: self._io_executor,
            ExecutionMode.PROCESS: self._cpu_executor,
            ExecutionMode.ASYNC: None
        }[mode]

    async def _execute_with_retries(self, task: Task):
        """Ejecuta la tarea con reintentos y manejo de errores"""
        for attempt in range(task.retries + 1):
            try:
                return task.func(*task.args, **task.kwargs)
            except Exception as e:
                if attempt == task.retries:
                    raise
                logger.warning(f"Reintentando {task.func.__name__} (intento {attempt+1})")
                async with self._lock:
                    self._metrics['total_retries'] += 1
                time.sleep(2 ** attempt)  # Backoff exponencial

    async def _update_metrics(self, success: bool, exec_time: float = 0.0):
        """Actualiza las métricas de rendimiento"""
        async with self._lock:
            key = 'tasks_completed' if success else 'tasks_failed'
            self._metrics[key] += 1
            
            if exec_time > 0:
                self._metrics['max_exec_time'] = max(self._metrics['max_exec_time'], exec_time)
                self._metrics['min_exec_time'] = min(self._metrics['min_exec_time'], exec_time)
                
                total = self._metrics['tasks_completed']
                self._metrics['avg_exec_time'] = (
                    (self._metrics['avg_exec_time'] * (total - 1) + exec_time) / total
                )

    async def shutdown(self, timeout: float = 5.0):
        """Apagado seguro con limpieza de recursos"""
        async with self._lock:
            self._shutdown_flag = True
            logger.info("Iniciando apagado del motor...")

            # Limpiar cola de tareas
            while self._task_queue:
                heappop(self._task_queue)

        # Esperar finalización de tareas activas
        try:
            await asyncio.wait_for(
                self._wait_for_running_tasks(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Tiempo de espera agotado para finalizar tareas")

        # Cerrar executors
        self._io_executor.shutdown(wait=False)
        self._cpu_executor.shutdown(wait=False)
        logger.info("Motor apagado correctamente")

    async def _wait_for_running_tasks(self):
        """Espera a que las tareas en ejecución finalicen"""
        while self._metrics['active_workers'] > 0:
            await asyncio.sleep(0.1)

    async def get_metrics(self) -> Dict[str, float]:
        """Devuelve métricas de rendimiento actualizadas"""
        async with self._lock:
            return self._metrics.copy()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """Acceso al event loop principal"""
        return self._loop

    @property
    def is_running(self) -> bool:
        """Estado del motor"""
        return not self._shutdown_flag

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()