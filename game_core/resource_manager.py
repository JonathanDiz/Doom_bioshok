import asyncio
import logging
from enum import Enum, auto
from typing import Optional, Callable, Awaitable, Dict, List, Any
from collections import defaultdict, deque

class LoadState(Enum):
    """Estados del ciclo de vida de la carga de recursos"""
    PENDING = auto()
    LOADING = auto()
    SUCCESS = auto()
    FAILED = auto()

class ResourceManager:
    """Sistema profesional de gestión de recursos con carga asíncrona y seguimiento de dependencias"""
    
    __slots__ = (
        'game_core', 'resources_loaded', '_state',
        '_loaders', '_dependencies', '_last_error', 'logger'
    )

    def __init__(self, game_core=None):
        self.game_core = game_core
        self.resources_loaded = asyncio.Event()
        self._state = LoadState.PENDING
        self._loaders: Dict[str, Callable[[], Awaitable[None]]] = {}
        self._dependencies: Dict[str, List[str]] = defaultdict(list)
        self._last_error: Optional[Exception] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_loader(
        self, 
        loader_id: str, 
        loader: Callable[[], Awaitable[None]], 
        dependencies: List[str] = None
    ) -> None:
        """Registra un nuevo cargador con gestión de dependencias
        
        Args:
            loader_id (str): Identificador único del cargador
            loader (Callable[[], Awaitable[None]]): Función de carga asíncrona
            dependencies (List[str], optional): Lista de IDs de dependencias
        """
        if loader_id in self._loaders:
            self.logger.warning(f"Loader '{loader_id}' ya registrado")
            return
            
        self._loaders[loader_id] = loader
        self._dependencies[loader_id] = dependencies or []
        self.logger.debug(f"Loader registrado: {loader_id}")

    async def load_resources(self) -> None:
        """Ejecuta la carga de recursos con paralelismo controlado y gestión de dependencias"""
        if self._state == LoadState.LOADING:
            self.logger.warning("Carga de recursos ya en progreso")
            return

        self._state = LoadState.LOADING
        self.resources_loaded.clear()
        self.logger.info("Iniciando carga de recursos...")

        try:
            execution_order = self._resolve_dependencies()
            await self._execute_loaders(execution_order)
            self._state = LoadState.SUCCESS
            self.logger.info("Carga completada exitosamente")
        except Exception as e:
            self._handle_load_error(e)
        finally:
            self.resources_loaded.set()

    def _resolve_dependencies(self) -> List[List[str]]:
        """Resuelve dependencias usando topological sort
        
        Returns:
            List[List[str]]: Orden de ejecución por niveles de dependencia
            
        Raises:
            ValueError: Si se detectan dependencias circulares
        """
        in_degree = defaultdict(int)
        graph = defaultdict(list)
        nodes = set(self._loaders.keys())

        # Construir grafo de dependencias
        for loader, deps in self._dependencies.items():
            for dep in deps:
                graph[dep].append(loader)
                in_degree[loader] += 1
                nodes.add(dep)

        # Inicializar cola con nodos sin dependencias
        queue = deque([node for node in nodes if in_degree[node] == 0])
        result = []
        
        while queue:
            current_level = []
            for _ in range(len(queue)):
                node = queue.popleft()
                if node in self._loaders:
                    current_level.append(node)
                
                for neighbor in graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            
            if current_level:
                result.append(current_level)

        # Verificar ciclos
        if any(in_degree[node] > 0 for node in nodes):
            raise ValueError("Dependencias circulares detectadas")
        
        return result

    async def _execute_loaders(self, execution_order: List[List[str]]) -> None:
        """Ejecuta cargadores en paralelo por etapas de dependencias
        
        Args:
            execution_order (List[List[str]]): Orden de ejecución generado
        """
        for stage in execution_order:
            self.logger.info(f"Ejecutando etapa con {len(stage)} cargadores")
            tasks = [self._run_loader(loader_id) for loader_id in stage]
            await asyncio.gather(*tasks)

    async def _run_loader(self, loader_id: str) -> None:
        """Ejecuta un loader individual con manejo de errores
        
        Args:
            loader_id (str): ID del cargador a ejecutar
        """
        try:
            self.logger.debug(f"Ejecutando loader: {loader_id}")
            await self._loaders[loader_id]()
        except Exception as e:
            self.logger.error(f"Fallo en loader {loader_id}: {str(e)}")
            raise

    def _handle_load_error(self, error: Exception) -> None:
        """Gestiona errores de carga y genera reportes
        
        Args:
            error (Exception): Excepción capturada durante la carga
        """
        self._state = LoadState.FAILED
        self._last_error = error
        self.logger.critical(
            "Error crítico cargando recursos", 
            exc_info=True,
            extra={
                "load_state": self._state.name,
                "active_loaders": list(self._loaders.keys())
            }
        )

    def get_loader_status(self, loader_id: str) -> Dict[str, Any]:
        """Obtiene el estado detallado de un loader específico
        
        Args:
            loader_id (str): ID del cargador a consultar
            
        Returns:
            Dict[str, Any]: Estado del cargador y metadatos
        """
        return {
            "registered": loader_id in self._loaders,
            "dependencies": self._dependencies.get(loader_id, []),
            "last_error": str(self._last_error) if self._last_error else None
        }

    @property
    def state(self) -> LoadState:
        """Estado actual del proceso de carga"""
        return self._state

    @property
    def last_error(self) -> Optional[Exception]:
        """Último error registrado durante la carga"""
        return self._last_error

    @property
    def ready(self) -> bool:
        """Indica si los recursos están listos para su uso"""
        return self._state == LoadState.SUCCESS

    @property
    def progress(self) -> float:
        """Progreso de carga estimado (0.0 a 1.0)"""
        if self._state == LoadState.SUCCESS:
            return 1.0
        total = len(self._loaders)
        completed = sum(1 for loader in self._loaders if loader not in self._dependencies)
        return completed / total if total > 0 else 0.0