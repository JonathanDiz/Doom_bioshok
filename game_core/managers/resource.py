from enum import Enum, auto
import pygame as pg
import asyncio
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Callable
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor

class LoadPriority(Enum):
    CRITICAL = auto()  # Recursos necesarios para el primer frame
    HIGH = auto()      # Assets esenciales del nivel actual
    MEDIUM = auto()    # Recursos del siguiente nivel/área
    LOW = auto()       # Elementos opcionales/background

class AssetType(Enum):
    TEXTURE = auto()
    SOUND = auto()
    FONT = auto()
    DATA = auto()
    SHADER = auto()

@dataclass
class ResourceData:
    asset: Any
    size: int          # En bytes
    dependencies: Set[str]
    last_access: float
    load_count: int = 0

class ResourceManager:
    """Gestor avanzado de recursos con caché inteligente, dependencias y gestión de memoria"""
    
    __slots__ = (
        'core', '_cache', '_load_queue', '_dependency_graph',
        '_memory_limit', '_total_loaded', '_executor', '_semaphore',
        '_progress_callback', '_loaded_assets', '_total_to_load'
    )

    def __init__(self, core, memory_limit_mb: int = 1024):
        self.core = core
        self._cache: OrderedDict[str, ResourceData] = OrderedDict()
        self._load_queue: Dict[LoadPriority, List[tuple]] = {p: [] for p in LoadPriority}
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._memory_limit = memory_limit_mb * 1024 * 1024  # Convertir a bytes
        self._total_loaded = 0
        self._executor = ThreadPoolExecutor(max_workers=os.cpu_count())
        self._semaphore = asyncio.Semaphore(os.cpu_count() * 2)
        self._progress_callback: Optional[Callable[[float], None]] = None
        self._loaded_assets = 0
        self._total_to_load = 0

    def set_progress_callback(self, callback: Callable[[float], None]):
        """Configura un callback para reportar progreso de carga"""
        self._progress_callback = callback

    def preload_manifest(self, manifest_path: Path):
        """Carga un manifiesto de recursos con metadatos"""
        # Implementar parser de JSON con dependencias y prioridades
        pass

    def register_dependency(self, asset_path: str, depends_on: List[str]):
        """Registra dependencias entre recursos"""
        self._dependency_graph[asset_path] = set(depends_on)

    async def load_queued(self):
        """Carga recursiva con resolución de dependencias y gestión de memoria"""
        self._total_to_load = sum(len(q) for q in self._load_queue.values())
        
        for priority in LoadPriority:
            while self._load_queue[priority]:
                tasks = []
                current_batch = self._load_queue[priority].copy()
                self._load_queue[priority].clear()
                
                for asset_type, path in current_batch:
                    if not self._check_dependencies(path):
                        self._requeue_with_dependencies(priority, asset_type, path)
                        continue
                    
                    tasks.append(self._load_asset(asset_type, path, priority))
                
                await asyncio.gather(*tasks)
                self._report_progress()

    def _check_dependencies(self, path: str) -> bool:
        """Verifica si todas las dependencias están cargadas"""
        return all(dep in self._cache for dep in self._dependency_graph[path])

    def _requeue_with_dependencies(self, priority: LoadPriority, asset_type: AssetType, path: str):
        """Reagenda la carga hasta que se cumplan las dependencias"""
        self._load_queue[priority].append((asset_type, path))
        for dep in self._dependency_graph[path]:
            if dep not in self._cache and not any(dep in q for q in self._load_queue.values()):
                self.preload(AssetType.TEXTURE, dep, LoadPriority.CRITICAL)

    async def _load_asset(self, asset_type: AssetType, path: str, priority: LoadPriority):
        """Carga asíncrona con gestión de errores y caché"""
        async with self._semaphore:
            try:
                if path in self._cache:
                    self._cache.move_to_end(path)
                    return

                asset, size = await self._execute_loader(asset_type, path)
                self._add_to_cache(path, asset, size, asset_type)
                self._loaded_assets += 1

            except Exception as e:
                logging.error(f"Error loading {path}: {e}")
                raise AssetLoadError(f"Failed to load {path}") from e

    async def _execute_loader(self, asset_type: AssetType, path: str):
        """Ejecuta el loader adecuado con reintentos"""
        loop = asyncio.get_running_loop()
        for attempt in range(3):
            try:
                if asset_type == AssetType.TEXTURE:
                    return await loop.run_in_executor(
                        self._executor,
                        self._load_texture, path
                    )
                elif asset_type == AssetType.SOUND:
                    return await loop.run_in_executor(
                        self._executor,
                        self._load_sound, path
                    )
                # Implementar otros tipos
            except pg.error as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(0.1 * attempt)

    def _load_texture(self, path: str) -> tuple:
        """Carga optimizada de texturas con gestión de VRAM"""
        surface = pg.image.load(path)
        optimized = surface.convert_alpha() if surface.get_flags() & pg.SRCALPHA else surface.convert()
        return optimized, surface.get_bytesize()

    def _load_sound(self, path: str) -> tuple:
        """Carga de sonido con ajuste de volumen global"""
        sound = pg.mixer.Sound(path)
        sound.set_volume(self.core.config.sound_volume)
        return sound, os.path.getsize(path)

    def _add_to_cache(self, path: str, asset: Any, size: int, asset_type: AssetType):
        """Añade a la caché con gestión de memoria"""
        while self._total_loaded + size > self._memory_limit and self._cache:
            self._evict_oldest()
        
        self._cache[path] = ResourceData(
            asset=asset,
            size=size,
            dependencies=self._dependency_graph[path],
            last_access=time.time()
        )
        self._total_loaded += size

    def _evict_oldest(self):
        """Elimina el recurso menos usado siguiendo política LRU"""
        oldest = next(iter(self._cache))
        self._total_loaded -= self._cache[oldest].size
        del self._cache[oldest]

    def get(self, path: str) -> Any:
        """Obtiene un recurso con actualización de acceso"""
        if path not in self._cache:
            raise AssetNotLoadedError(f"Asset {path} not loaded")
        
        data = self._cache[path]
        data.last_access = time.time()
        data.load_count += 1
        self._cache.move_to_end(path)
        return data.asset

    def _report_progress(self):
        """Actualiza el callback de progreso"""
        if self._progress_callback and self._total_to_load > 0:
            progress = self._loaded_assets / self._total_to_load
            self._progress_callback(min(progress, 1.0))

class AssetLoadError(Exception):
    """Excepción para errores de carga de recursos"""
    pass

class AssetNotLoadedError(Exception):
    """Excepción para accesos a recursos no cargados"""
    pass