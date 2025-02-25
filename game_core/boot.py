import asyncio
from typing import List, Awaitable

from game_core.utils.async_tools import AsyncLoader
from .managers.resource import LoadPriority
import pygame as pg

class BootManager:
    """Sistema de arranque por etapas con carga en paralelo"""
    def __init__(self, core):
        self.core = core
        self._load_tasks: List[Awaitable] = []
        
    async def start_async_load(self):
        """Carga no bloqueante de recursos esenciales"""
        self._queue_essential_tasks()
        await self._execute_parallel_load()
        
    def _queue_essential_tasks(self):
        """Encola tareas críticas de inicialización"""
        self._load_tasks.extend([
            self._load_display_subsystem(),
            self._load_input_system(),
            self._init_audio()
        ])
    
    async def _execute_parallel_load(self):
        """Ejecuta carga paralela con prioridades"""
        loader = AsyncLoader(max_workers=4)
        await loader.run_tasks(self._load_tasks)
    
    async def _load_display_subsystem(self):
        """Carga diferida del subsistema de renderizado"""
        from .managers.display import DisplayManager
        self.core.display_manager = DisplayManager(self.core)
        await self.core.display_manager.initialize_async()
    
    async def _load_input_system(self):
        """Inicializa controles en segundo plano"""
        from .managers.input import InputManager
        self.core.input = InputManager()
        await self.core.input.load_keybindings()
    
    async def _init_audio(self):
        """Carga mínima de audio para feedback inmediato"""
        pg.mixer.init()
        self.core.resource.load_sound('ui_click', 'assets/audio/click.wav', LoadPriority.HIGH)