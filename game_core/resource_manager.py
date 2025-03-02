import asyncio
import logging
from enum import Enum, auto
from typing import Optional, Callable, Awaitable, List


class LoadState(Enum):
    """Estado actual del proceso de carga de recursos"""
    PENDING = auto()
    LOADING = auto()
    SUCCESS = auto()
    FAILED = auto()


class ResourceManager:
    """Gestor modular de recursos con soporte para carga asíncrona y manejo de errores

    Attributes:
        resources_loaded (asyncio.Event): Evento que se activa al completar la carga
    """

    def __init__(self, game_core=None):
        """Inicializa el gestor de recursos

        Args:
            game_core (Optional[GameCore]): Referencia al núcleo del juego
        """
        self.game_core = game_core
        self.resources_loaded = asyncio.Event()
        self._state = LoadState.PENDING
        self._loaders: List[Callable[[], Awaitable[None]]] = []
        self._last_error: Optional[Exception] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_loader(self, loader: Callable[[], Awaitable[None]]):
        """Registra un nuevo cargador de recursos

        Args:
            loader (Callable[[], Awaitable[None]]): Función asíncrona para cargar recursos
        """
        self._loaders.append(loader)
        self.logger.debug(f"Nuevo cargador registrado: {loader.__name__}")

    async def load_resources(self) -> None:
        """Ejecuta todos los cargadores registrados de forma concurrente"""
        if self._state == LoadState.LOADING:
            self.logger.warning("La carga de recursos ya está en progreso")
            return

        self._state = LoadState.LOADING
        self.resources_loaded.clear()
        self.logger.info("Iniciando carga de recursos...")

        try:
            await asyncio.gather(*(loader() for loader in self._loaders))
            self._state = LoadState.SUCCESS
            self.logger.info("Carga de recursos completada exitosamente")
        except Exception as e:
            self._state = LoadState.FAILED
            self._last_error = e
            self.logger.error(f"Error cargando recursos: {str(e)}", exc_info=True)
        finally:
            self.resources_loaded.set()

    @property
    def state(self) -> LoadState:
        """Estado actual de la carga de recursos"""
        return self._state

    @property
    def last_error(self) -> Optional[Exception]:
        """Último error registrado durante la carga"""
        return self._last_error

    @property
    def ready(self) -> bool:
        """Indica si los recursos están listos para su uso"""
        return self._state == LoadState.SUCCESS