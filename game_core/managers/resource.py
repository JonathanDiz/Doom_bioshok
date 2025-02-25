from enum import Enum, auto
from typing import Dict, Any, Optional
import pygame as pg
import asyncio

class LoadPriority(Enum):
    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()

class ResourceManager:
    """Gestor de recursos con carga priorizada y caché"""
    def __init__(self, core):
        self.core = core
        self._cache: Dict[str, Any] = {}
        self._load_queue: Dict[LoadPriority, list] = {
            LoadPriority.CRITICAL: [],
            LoadPriority.HIGH: [],
            LoadPriority.MEDIUM: [],
            LoadPriority.LOW: []
        }
        
    def preload(self, asset_type: str, path: str, priority: LoadPriority):
        """Registra recurso para carga diferida"""
        self._load_queue[priority].append((asset_type, path))
        
    async def load_queued(self):
        """Carga recursos en paralelo según prioridad"""
        for priority in LoadPriority:
            await self._process_priority_level(priority)
    
    async def _process_priority_level(self, priority: LoadPriority):
        """Procesa un nivel de prioridad"""
        tasks = []
        for asset_type, path in self._load_queue[priority]:
            tasks.append(asyncio.create_task(
                self._load_asset(asset_type, path)
            ))
        await asyncio.gather(*tasks)
    
    async def _load_asset(self, asset_type: str, path: str):
        """Carga asíncrona con caché integrado"""
        if path in self._cache:
            return
            
        if asset_type == 'texture':
            self._cache[path] = await self._load_texture(path)
        elif asset_type == 'sound':
            self._cache[path] = await self._load_sound(path)
            
    async def _load_texture(self, path: str) -> pg.Surface:
        """Carga texturas optimizadas para GPU"""
        # Implementación con SDL_image o similar
        return pg.image.load(path).convert_alpha()
    
    async def _load_sound(self, path: str) -> pg.mixer.Sound:
        """Carga de sonido con streaming"""
        return pg.mixer.Sound(path)