import time
import sys
import os
import pygame as pg
import asyncio
import traceback
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict

from game_core import GameCore
import game_core
from game_core.managers import initialize_core_managers
from game_core.utils.async_tools import AsyncLoader, run_parallel 
from game_core import core
from game_core.core import GameCore
from game_core.managers.audio import AudioCategory, AudioManager
from game_core.managers.input import InputAction, InputManager
from npc import Game
import player
# Importación estándar
from game_core.managers import InputManager, DisplayManager

from game_core.utils.type_aliases import Coordinate, ColorValue

def draw_particle(pos: Coordinate, color: ColorValue) -> None:
    # Implementación de renderizado
    pass

# Creación rápida de managers básicos
from game_core.managers import initialize_core_managers

input_mgr, display_mgr, resource_mgr, debug_mgr = initialize_core_managers(game_core)

# Inicialización
audio_manager = AudioManager(core)

# Carga de recursos
audio_manager.load_sound('jump', 'sfx/jump.wav', AudioCategory.SFX)
audio_manager.load_music('main_theme', 'music/main.ogg')

# Importación de múltiples utilidades
from game_core.utils import (
    AsyncLoader,
    Coordinate,
    debug_timer,
    validate_resolution
)

# Uso del temporizador
with debug_timer() as timer:
    # Código a medir
    pass

print(f"Operación completada en {timer.duration:.2f}s")

# Validación de resolución
best_res = validate_resolution((3840, 2160))

# Reproducción
audio_manager.play_sound('jump', player.position)
audio_manager.play_music('main_theme', fade_duration=2000)

# Control de volumen
audio_manager.set_volume(AudioCategory.SFX, 0.8)

# Configuración inicial de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_debug.log'),
        logging.StreamHandler()
    ]
)

class Debugger:
    """Sistema centralizado de debugging y registro de errores"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_debugger()
        return cls._instance
    
    def _init_debugger(self):
        """Inicializa los componentes del debugger"""
        self.error_count = 0
        self.warning_count = 0
        self.performance_data = []
        self.start_time = time.time()
        self.frame_counter = 0
        
        # Configurar dumps de estado
        self.state_snapshots = []
        self.snapshot_interval = 5  # segundos
        
    @staticmethod
    def log_exception(context: str, exception: Exception, extra: Dict[str, Any] = None):
        """Registra excepciones con traza completa y contexto"""
        logger = logging.getLogger(__name__)
        exc_info = (type(exception), exception, exception.__traceback__)
        log_data = {
            'context': context,
            'exception_type': str(type(exception)),
            'message': str(exception),
            'timestamp': datetime.now().isoformat(),
            'extra': extra or {}
        }
        
        logger.error(
            "Error en %s: %s\n%s",
            context,
            exception,
            traceback.format_exc(),
            extra={'debug_data': log_data}
        )
        
        Debugger._instance.error_count += 1
        
    @staticmethod
    def performance_monitor(func):
        """Decorador para monitorizar rendimiento de funciones"""
        async def async_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.monotonic() - start
                Debugger._instance.performance_data.append(
                    (func.__name__, duration)
                )
                if duration > 0.1:  # Límite de advertencia de rendimiento
                    logging.warning(f"Función lenta: {func.__name__} ({duration:.2f}s)")
                    
        def sync_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.monotonic() - start
                Debugger._instance.performance_data.append(
                    (func.__name__, duration)
                )
                
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    @staticmethod
    def game_state_snapshot(game):
        """Captura estado actual del juego para debugging"""
        snapshot = {
            'timestamp': time.time(),
            'resources_loaded': hasattr(game, 'resource_manager') and game.resource_manager.are_resources_ready(),
            'entities_count': len(game.object_handler.npc) if hasattr(game, 'object_handler') else 0,
            'player_position': getattr(game.player, 'pos', (0, 0)),
            'fps': game.clock.get_fps() if hasattr(game, 'clock') else 0
        }
        Debugger._instance.state_snapshots.append(snapshot)
        
    @staticmethod
    def generate_report():
        """Genera reporte completo de debugging"""
        report = [
            f"Debug Report - {datetime.now().isoformat()}",
            f"Tiempo ejecución: {time.time() - Debugger._instance.start_time:.1f}s",
            f"Errores totales: {Debugger._instance.error_count}",
            f"Advertencias: {Debugger._instance.warning_count}",
            "\nPerformance:"
        ]
        
        # Análisis de rendimiento
        func_stats = {}
        for func_name, duration in Debugger._instance.performance_data:
            func_stats.setdefault(func_name, []).append(duration)
            
        for func, times in func_stats.items():
            avg = sum(times) / len(times)
            report.append(
                f"- {func}: {len(times)} ejecuciones, "
                f"avg: {avg:.3f}s, max: {max(times):.3f}s"
            )
            
        # Últimos snapshots
        report.append("\nÚltimos estados del juego:")
        for snap in Debugger._instance.state_snapshots[-3:]:
            report.append(
                f"[{datetime.fromtimestamp(snap['timestamp'])}] "
                f"Posición: {snap['player_position']} FPS: {snap['fps']:.1f}"
            )
            
        return "\n".join(report)

class DebugGameCore:
    """Wrapper de debugging para GameCore"""
    
    def __init__(self, game):
        self.game = game
        self.debugger = Debugger()
        
    def __getattr__(self, name):
        return getattr(self.game, name)
    
    async def run(self):
        """Bucle principal con monitorización"""
        try:
            while self.game.running:
                self.debugger.game_state_snapshot(self.game)
                await self.game._process_events()
                await asyncio.sleep(0)
                
                # Log de rendimiento periódico
                if time.time() - self.debugger.start_time > self.debugger.snapshot_interval:
                    logging.info(Debugger.generate_report())
                    
        except Exception as e:
            self.debugger.log_exception("Bucle principal", e, {
                'last_state': self.debugger.state_snapshots[-1] if self.debugger.state_snapshots else None
            })
            raise
        finally:
            await self.game.shutdown()

# Aplicar decoradores de debugging a las funciones críticas
GameCore.load_heavy_resources = Debugger.performance_monitor(GameCore.load_heavy_resources)
Game._process_game_updates = Debugger.performance_monitor(Game._process_game_updates)
Game._handle_rendering = Debugger.performance_monitor(Game._handle_rendering)

async def main():
    # 1. Arranque en menos de 1 segundo
    core = GameCore()
    await core.quick_boot()
    
    input_mgr, display_mgr, resource_mgr, debug_mgr = initialize_core_managers(game_core)
    await game_core.run()
    # 2. Loop principal con recursos cargando en segundo plano
    while core.running:
        # Lógica mínima jugable mientras carga
        for event in pg.event.get():
            if event.type == pg.QUIT:
                core.running = False
        
        # En el bucle principal
        InputManager.update()

        if InputManager.get_action_down(InputAction.JUMP):
            player.jump()

        mouse_pos = InputManager.get_mouse_position()

        # Renderizar pantalla de carga
        core.display.fill((0, 0, 0))
        pg.display.flip()
        await asyncio.sleep(0)
    """Punto de entrada principal con manejo de errores mejorado"""
    debugger = Debugger()
    try:
        game = DebugGameCore(GameCore())
        
        # Carga inicial de recursos con monitorización
        await debugger.performance_monitor(game.load_heavy_resources)()
        
        # Ejecución del juego con wrapper de debugging
        await game.run()
        
        # Generar reporte final
        logging.info("\n" + Debugger.generate_report())
        
    except Exception as e:
        debugger.log_exception("Main", e, {
            'system': os.uname(),
            'pygame_version': pg.version.ver,
            'python_version': sys.version
        })
        raise
    finally:
        if pg.get_init():
            pg.quit()

if __name__ == '__main__':
    asyncio.run(main())