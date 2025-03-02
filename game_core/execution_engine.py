import asyncio
import logging
import os
import time
import concurrent.futures
from enum import IntEnum, auto
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial
from heapq import heappush, heappop

logger = logging.getLogger(__name__)
T = TypeVar('T')

class TaskPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

class ExecutionMode(IntEnum):
    THREAD = auto()
    PROCESS = auto()
    ASYNC = auto()

@dataclass(order=True)
class Task:
    priority: TaskPriority
    timestamp: float
    task_id: int
    func: Callable = None
    args: Tuple = ()
    kwargs: Dict[str, Any] = None
    callback: Optional[Callable] = None
    retries: int = 0
    mode: ExecutionMode = ExecutionMode.THREAD

class ExecutionEngine:
    """Motor de ejecución avanzado con gestión de recursos, prioridades y métricas"""
    
    __instance = None
    __slots__ = (
        '_loop', '_io_executor', '_cpu_executor', '_task_queue',
        '_metrics', '_running_tasks', '_next_task_id', '_shutdown_flag'
    )

    def __new__(cls, core=None):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance._init_engine()
        return cls.__instance

    def _init_engine(self):
        """Inicialización privada del motor"""
        self._loop = asyncio.get_event_loop()
        self._io_executor = ThreadPoolExecutor(
            max_workers=self._calculate_optimal_workers('io'),
            thread_name_prefix='IO-Worker'
        )
        self._cpu_executor = ProcessPoolExecutor(
            max_workers=self._calculate_optimal_workers('cpu')
        )
        self._task_queue = []
        self._metrics = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'avg_exec_time': 0.0,
            'queue_size': 0,
            'active_workers': 0
        }
        self._running_tasks = set()
        self._next_task_id = 0
        self._shutdown_flag = False

    def _calculate_optimal_workers(self, pool_type: str) -> int:
        """Calcula workers óptimos basado en hardware"""
        cores = os.cpu_count() or 4
        return {
            'io': min(32, (cores * 4)),
            'cpu': cores
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
        if self._shutdown_flag:
            raise RuntimeError("Engine en proceso de apagado")

        task = Task(
            priority=priority,
            timestamp=time.monotonic(),
            task_id=self._next_task_id,
            func=func,
            args=args,
            kwargs=kwargs or {},
            retries=retries,
            mode=mode
        )
        self._next_task_id += 1
        
        heappush(self._task_queue, task)
        self._metrics['queue_size'] += 1
        
        return await self._process_task(task)

    async def _process_task(self, task: Task) -> Any:
        """Ejecuta la tarea con el executor apropiado"""
        self._metrics['queue_size'] -= 1
        self._metrics['active_workers'] += 1
        
        try:
            start_time = time.monotonic()
            
            if task.mode == ExecutionMode.PROCESS:
                result = await self._loop.run_in_executor(
                    self._cpu_executor,
                    partial(self._execute_with_retries, task)
                )
            else:
                result = await self._loop.run_in_executor(
                    self._io_executor,
                    partial(self._execute_with_retries, task)
                )
                
            exec_time = time.monotonic() - start_time
            self._update_metrics(success=True, exec_time=exec_time)
            
            return result
        except Exception as e:
            self._update_metrics(success=False)
            logger.error(f"Task failed: {task.func.__name__} - {e}")
            raise
        finally:
            self._metrics['active_workers'] -= 1
            self._running_tasks.discard(task.task_id)

    def _execute_with_retries(self, task: Task):
        """Ejecuta la tarea con reintentos y manejo de errores"""
        for attempt in range(task.retries + 1):
            try:
                return task.func(*task.args, **task.kwargs)
            except Exception as e:
                if attempt == task.retries:
                    raise
                logger.warning(f"Retrying {task.func.__name__} (attempt {attempt+1})")
                time.sleep(2 ** attempt)  # Backoff exponencial

    def _update_metrics(self, success: bool, exec_time: float = 0.0):
        """Actualiza las métricas de rendimiento"""
        self._metrics['tasks_completed' if success else 'tasks_failed'] += 1
        if exec_time > 0:
            total = self._metrics['tasks_completed']
            self._metrics['avg_exec_time'] = (
                (self._metrics['avg_exec_time'] * (total - 1) + exec_time) / total
            )

    async def shutdown(self, timeout: float = 5.0):
        """Apagado seguro con limpieza de recursos"""
        self._shutdown_flag = True
        logger.info("Iniciando apagado del motor...")
        
        # Cancelar tareas pendientes
        while self._task_queue:
            heappop(self._task_queue)
        
        # Esperar finalización de tareas activas
        await asyncio.wait_for(
            self._wait_for_running_tasks(),
            timeout=timeout
        )
        
        # Cerrar executors
        self._io_executor.shutdown(wait=False)
        self._cpu_executor.shutdown(wait=False)
        logger.info("Motor apagado correctamente")

    async def _wait_for_running_tasks(self):
        """Espera a que las tareas en ejecución finalicen"""
        while self._metrics['active_workers'] > 0:
            await asyncio.sleep(0.1)

    def get_metrics(self) -> Dict[str, float]:
        """Devuelve métricas de rendimiento actualizadas"""
        return self._metrics.copy()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """Acceso al event loop principal"""
        return self._loop

    @property
    def is_running(self) -> bool:
        """Estado del motor"""
        return not self._shutdown_flag