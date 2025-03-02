import pygame as pg
import asyncio
import concurrent.futures
from typing import Callable, Any
from math import sin, cos, pi

from player import Player

class AnimationSystem:
    def __init__(self, max_workers=4):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers)
        self.loop = asyncio.get_event_loop()
        self.tasks = []
        self.animations = {}
        self.easing_functions = {
            'linear': lambda t: t,
            'ease_in': lambda t: t**2,
            'ease_out': lambda t: 1 - (1 - t)**2,
            'ease_in_out': lambda t: 0.5 * (1 - cos(pi * t))
        }
    
    async def _async_animation_wrapper(
        self,
        target: Any,
        duration: float,
        update_callback: Callable,
        easing: str = 'linear'
    ):
        """Wrapper principal para animaciones asíncronas"""
        start_time = pg.time.get_ticks()
        ease_fn = self.easing_functions.get(easing, self.easing_functions['linear'])
        
        while (elapsed := pg.time.get_ticks() - start_time) < duration:
            progress = ease_fn(elapsed / duration)
            await self.loop.run_in_executor(
                self.executor,
                self._apply_animation_update,
                target,
                progress,
                update_callback
            )
            await asyncio.sleep(0)
            
        update_callback(target, 1.0)  # Asegurar estado final
    
    def _apply_animation_update(self, target, progress, callback):
        """Aplica actualizaciones de animación de manera thread-safe"""
        callback(target, progress)
    
    def add_animation(
        self,
        target: Any,
        duration: float,
        update_callback: Callable,
        easing: str = 'linear',
        group: str = 'default'
    ):
        """Registra una nueva animación"""
        task = self.loop.create_task(
            self._async_animation_wrapper(target, duration, update_callback, easing)
        )
        self.animations.setdefault(group, []).append(task)
    
    async def parallel_animations(self, *animations):
        """Ejecuta múltiples animaciones en paralelo"""
        await asyncio.gather(*[a[0](*a[1:]) for a in animations])
    
    def cancel_group(self, group: str):
        """Cancela todas las animaciones de un grupo"""
        for task in self.animations.get(group, []):
            task.cancel()
        self.animations.pop(group, None)
    
    async def stop_all(self):
        """Detiene todas las animaciones activas"""
        for group in list(self.animations.keys()):
            self.cancel_group(group)

class AnimationPresets:
    @staticmethod
    def move_linear(target, start_pos, end_pos, duration=1.0, easing='linear'):
        """Animación de movimiento entre dos puntos"""
        def update(obj, progress):
            obj.x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
            obj.y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
        return (update, target, duration, easing)
    
    @staticmethod
    def scale_transition(target, start_scale, end_scale, duration=0.5, easing='ease_in_out'):
        """Animación de escalado suave"""
        def update(obj, progress):
            obj.scale = start_scale + (end_scale - start_scale) * progress
        return (update, target, duration, easing)
    
    @staticmethod
    def rotate(target, start_angle, end_angle, duration=1.0, easing='ease_out'):
        """Animación de rotación angular"""
        def update(obj, progress):
            obj.angle = start_angle + (end_angle - start_angle) * progress
        return (update, target, duration, easing)
    
    @staticmethod
    def particle_fade(surface, start_alpha, end_alpha, duration=0.7, easing='ease_out'):
        """Efecto de desvanecimiento para partículas"""
        def update(surf, progress):
            alpha = start_alpha + (end_alpha - start_alpha) * progress
            surf.set_alpha(int(alpha))
        return (update, surface, duration, easing)

# Uso recomendado en el juego
async def main_game_loop():
    anim_system = AnimationSystem()
    player = Player()  # Suponiendo una clase Player con atributos x, y
    
    # Ejemplo: Animación combinada
    anim_system.add_animation(
        *AnimationPresets.move_linear(
            player, 
            (100, 100), 
            (400, 300), 
            duration=1.5, 
            easing='ease_in_out'
        ),
        group='player_movement'
    )
    
    anim_system.add_animation(
        *AnimationPresets.rotate(
            player,
            0,
            360,
            duration=1.5,
            easing='ease_out'
        ),
        group='player_rotation'
    )
    
    # Ejecutar animaciones en paralelo
    await anim_system.parallel_animations(
        anim_system.animations['player_movement'],
        anim_system.animations['player_rotation']
    )

if __name__ == '__main__':
    asyncio.run(main_game_loop())