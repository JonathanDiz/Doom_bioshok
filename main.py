import sys
import os
import pygame as pg
import asyncio
import logging
from settings import GAME_CONFIG
from player import Player
from game_core import GameCore as BaseGameCore, Initialization
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
        self.input, self.display, self.resources, self.debug = initialize_core_managers(self)
        self._configure_managers()
        self.initializer = Initialization(config=GAME_CONFIG)
        
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

    def _handle_system_quit(self):
        """Manejo centralizado de la salida del juego"""
        self.execution.stop()
        self.running = False

    async def process_input(self):
        """Procesamiento avanzado de entradas con gestión de estados"""
        input_state = self.input.process()
        
        if input_state.quit_triggered:
            self.events.dispatch('quit', {'source': 'user'})
            
        if input_state.actions.get('shoot'):
            self.events.dispatch('shoot', {
                'position': input_state.mouse_position,
                'time': self.execution.current_frame_time
            })

    async def game_loop(self):
        """Bucle principal optimizado con gestión de tiempo real"""
        try:
            while self.execution.is_running:
                await self._process_frame()
        except Exception as e:
            self.debug.log_exception("GameLoopFailure", e)
        finally:
            await self._safe_shutdown()

    async def _process_frame(self):
        """Procesamiento completo de un frame del juego"""
        with self.debug.track_performance("FrameProcessing"):
            await self.process_input()
            await self._update_world_state()
            self._render_frame()
            self._maintain_fps()

    async def _update_world_state(self):
        """Actualización del estado del juego con interpolación"""
        self.player.update(
            self.input.mouse_delta,
            self.execution.delta_time
        )

    def _render_frame(self):
        """Renderizado optimizado con doble buffer"""
        self.display.clear()
        self.player.draw(self.display.buffer)
        self.display.flip()

    def _maintain_fps(self):
        """Control de tasa de refresco con ajuste dinámico"""
        self.clock.tick(GAME_CONFIG['render']['max_fps'])
        self.debug.track_fps()

    async def _safe_shutdown(self):
        """Apagado controlado de todos los sistemas"""
        with self.debug.track_performance("ShutdownSequence"):
            await self.display.cleanup()
            await self.resources.release_all_assets()
            pg.quit()
            self.debug.generate_performance_report()

async def main():
    """Punto de entrada principal del juego"""
    game = DebugGameCore()
    
    try:
        with game.debug.track_performance("FullRuntime"):
            await game.boot()
            await game.execution.run(
                main_systems=[game.game_loop],
                background_systems=[game.resources.background_loading]
            )
    except Exception as e:
        game.debug.log_exception("CriticalFailure", e, critical=True)
    finally:
        if game.execution.is_running:
            await game._safe_shutdown()

if __name__ == '__main__':
    asyncio.run(main())