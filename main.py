import sys
import os
import pygame as pg
import asyncio
import logging
from settings import GAME_CONFIG
from player import Player
from game_core import GameCore as BaseGameCore, PyGameInitialization
from game_core.managers import initialize_core_managers

# Configuración de rutas de importación
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuración centralizada de logging
logging.basicConfig(
    level=GAME_CONFIG['debug']['log_level'],
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_debug.log'),
        logging.StreamHandler()
    ]
)

class GameCore(BaseGameCore):
    """Núcleo principal del juego con gestión mejorada de sistemas"""
    
    def __init__(self):
        super().__init__()
        self.initializer = PyGameInitialization(config=GAME_CONFIG)
        self.input, self.display, self.resources, self.debug = initialize_core_managers(self)
        self._configure_managers()
        
    def _configure_managers(self):
        """Configuración inicial integrada de subsistemas"""
        self.debug.configure(**GAME_CONFIG['debug'])
        self.input.configure(
            mouse_sensitivity=GAME_CONFIG['controls']['mouse_sensitivity'],
            key_bindings=GAME_CONFIG['controls']['key_bindings']
        )
        
    async def boot(self):
        """Inicialización paralela de sistemas principales"""
        await self.initializer.async_initialize(
            systems=[
                self._init_essential_systems,
                self._load_critical_assets
            ]
        )
        
    async def _init_essential_systems(self):
        """Inicialización de sistemas básicos"""
        await asyncio.gather(
            self.display.initialize(
                resolution=GAME_CONFIG['render']['resolution'],
                window_title=GAME_CONFIG['window_title'],
                vsync=GAME_CONFIG['render']['vsync']
            ),
            self._init_pygame()
        )
        
    async def _load_critical_assets(self):
        """Carga de recursos esenciales"""
        await self.resources.load_critical(
            GAME_CONFIG['asset_paths']['textures'],
            GAME_CONFIG['asset_paths']['sounds']
        )

class DebugGameCore(GameCore):
    """Implementación extendida con capacidades de depuración avanzadas"""
    
    def __init__(self):
        super().__init__()
        self.player = Player(self)
        self._register_event_handlers()
        
    def _register_event_handlers(self):
        """Configuración de manejadores de eventos globales"""
        self.debug.logger.info("Registrando manejadores de eventos...")
        self.events.subscribe('quit', self._handle_system_quit)
        self.events.subscribe('shoot', self.player.handle_shoot)
        self.input.register_event(pg.QUIT, self._trigger_quit_event)
        
    async def run_game_loop(self):
        """Ejecución principal del bucle del juego"""
        try:
            while self.execution.is_running:
                await self._process_frame()
                self.debug.track_performance_metrics()
        except Exception as e:
            self.debug.log_exception("GameLoop", e, critical=True)
        finally:
            await self._safe_shutdown()

async def main():
    """Punto de entrada principal de la aplicación"""
    game = DebugGameCore()
    
    try:
        with game.debug.track_performance("FullExecution"):
            await game.boot()
            await game.execution.run(
                main_systems=[game.run_game_loop],
                background_systems=[game.resources.background_loading]
            )
    except Exception as e:
        game.debug.log_exception("MainProcess", e, critical=True)
    finally:
        if game.execution.is_running:
            await game._safe_shutdown()

if __name__ == '__main__':
    asyncio.run(main())