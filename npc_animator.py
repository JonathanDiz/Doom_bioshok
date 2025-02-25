import pygame as pg
import asyncio
import concurrent.futures
from math import sin, cos, pi
from game_navigation import GamePathFinder

from map import TILE_SIZE

class NPCAnimator:
    def __init__(self, game, max_workers=2):
        self.game = game
        self.pathfinder = GamePathFinder(game)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers)
        self.loop = asyncio.get_event_loop()
        self.animation_tasks = {}
        self.easing = {
            'move': lambda t: t**2 if t < 0.5 else 1 - (1 - t)**2,
            'attack': lambda t: 0.5 * (1 - cos(pi * t)),
            'damage': lambda t: sin(pi * t)
        }
        
    async def _animate_property(self, npc, duration, properties, easing_type='move'):
        """Animación genérica de propiedades con easing"""
        start_time = pg.time.get_ticks()
        initial_values = {k: getattr(npc, k) for k in properties}
        
        while (elapsed := pg.time.get_ticks() - start_time) < duration:
            progress = self.easing[easing_type](elapsed / duration)
            await self._apply_changes(npc, properties, initial_values, progress)
            await asyncio.sleep(0)
            
        await self._apply_changes(npc, properties, initial_values, 1.0)

    async def _apply_changes(self, npc, properties, initial, progress):
        """Aplica cambios de animación de forma thread-safe"""
        await self.loop.run_in_executor(
            self.executor,
            self._thread_safe_update,
            npc,
            properties,
            initial,
            progress
        )
    
    def _thread_safe_update(self, npc, properties, initial, progress):
        """Actualización segura para threads de propiedades del NPC"""
        for prop, (start, end) in properties.items():
            current = start + (end - start) * progress
            setattr(npc, prop, current)

    async def patrol_path(self, npc, path, speed=100):
        """Animación de patrullaje con pathfinding"""
        for point in path:
            if not npc.is_active: return  # Verificar estado
            
            dx = point.x * TILE_SIZE - npc.x
            dy = point.y * TILE_SIZE - npc.y
            distance = (dx**2 + dy**2)**0.5
            duration = distance / speed
            
            await self._animate_property(
                npc,
                duration,
                {
                    'x': (npc.x, point.x * TILE_SIZE),
                    'y': (npc.y, point.y * TILE_SIZE)
                },
                'move'
            )

    async def attack_movement(self, npc, target, power=30):
        """Animación de ataque con retroceso"""
        if not target.is_alive: return
        
        # Movimiento hacia adelante
        await self._animate_property(
            npc,
            0.15,
            {'attack_offset': (0, power)},
            'attack'
        )
        
        # Retroceso
        await self._animate_property(
            npc,
            0.3,
            {'attack_offset': (power, 0)},
            'damage'
        )

    async def damage_reaction(self, npc, intensity=50):
        """Animación de reacción al daño"""
        await self._animate_property(
            npc,
            0.4,
            {
                'damage_offset_x': (0, intensity * cos(npc.angle)),
                'damage_offset_y': (0, intensity * sin(npc.angle))
            },
            'damage'
        )

    async def smooth_rotate(self, npc, target_angle, duration=0.8):
        """Rotación suave con corrección angular"""
        start_angle = npc.angle % 360
        target_angle %= 360
        
        # Calcula la dirección de rotación más corta
        diff = (target_angle - start_angle + 180) % 360 - 180
        end_angle = start_angle + diff
        
        await self._animate_property(
            npc,
            duration,
            {'angle': (start_angle, end_angle)},
            'move'
        )

    async def dynamic_pathfinding(self, npc, target_pos):
        """Ejemplo de uso con el pathfinder actualizado"""
        start = (
            npc.x // self.game.map.tile_size, 
            npc.y // self.game.map.tile_size
        )
        goal = (
            target_pos[0] // self.game.map.tile_size,
            target_pos[1] // self.game.map.tile_size
        )
        
        path = await self.pathfinder.find_path(start, goal)
        if path:
            npc.target_x = path[0][0] * self.game.map.tile_size
            npc.target_y = path[0][1] * self.game.map.tile_size

    def create_animation_task(self, npc_id, coroutine):
        """Registra y maneja una tarea de animación"""
        if npc_id in self.animation_tasks:
            self.animation_tasks[npc_id].cancel()
            
        task = self.loop.create_task(coroutine)
        self.animation_tasks[npc_id] = task
        task.add_done_callback(lambda _: self.animation_tasks.pop(npc_id, None))

    async def stop_all_animations(self):
        """Detiene todas las animaciones activas"""
        for task in self.animation_tasks.values():
            task.cancel()
        self.animation_tasks.clear()

# Uso en el juego ---------------------------------------------------------------
class NPC:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = 0
        self.attack_offset = 0
        self.damage_offset_x = 0
        self.damage_offset_y = 0
        self.is_active = True
        self.is_alive = True

async def main():
    pg.init()
    screen = pg.display.set_mode((800, 600))
    
    # Configuración inicial
    npc = NPC(100, 100)
    animator = NPCAnimator(None)
    grid_matrix = [[1] * 20 for _ in range(20)]  # Mapa de ejemplo
    
    # Ejecutar animaciones combinadas
    animator.create_animation_task(
        1,
        asyncio.gather(
            animator.dynamic_pathfinding(npc, (500, 300), grid_matrix),
            animator.smooth_rotate(npc, 45)
        )
    )
    
    # Bucle principal
    running = True
    while running:
        screen.fill((30, 30, 30))
        
        # Dibujar NPC (implementar lógica real)
        pg.draw.circle(screen, (200, 50, 50), (int(npc.x), int(npc.y)), 15)
        
        pg.display.flip()
        await asyncio.sleep(0)
        
    pg.quit()

if __name__ == '__main__':
    asyncio.run(main())