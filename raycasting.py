import asyncio
import pygame as pg
import math
from settings import *

import pygame as pg
import math
from settings import *

class RayCasting:
    def __init__(self, game):
        self.game = game
        self.textures_ready = False  # Bandera de estado
        self.ray_casting_result = []
        self.objects_to_render = []
        self._init_dependencies()

    def _init_dependencies(self):
        """Registra callback para inicialización diferida"""
        self.game.add_resource_callback(self._on_resources_loaded)

    def _on_resources_loaded(self):
        """Callback cuando los recursos están listos"""
        self.textures = self.game.object_renderer.wall_textures
        self.textures_ready = True

    def update(self):
        """Actualización segura con verificación de estado"""
        if not self.textures_ready:
            return  # Salir temprano si no hay recursos
        
        self.ray_cast()
        self.get_objects_to_render()

    def init_textures(self):
        """Sincroniza las texturas cuando están disponibles"""
        if self.game.object_renderer:
            self.textures = self.game.object_renderer.wall_textures

    def update(self):
        """Actualización síncrona para ejecución en hilos"""
        # Verificación de texturas en cada frame
        if not self.textures and hasattr(self.game, 'object_renderer'):
            self.init_textures()
        
        # Ejecutar lógica principal solo si tenemos texturas
        if self.textures:
            self.ray_cast()
            self.get_objects_to_render()

    def get_objects_to_render(self):
        """Prepara los objetos para renderizar."""
        self.objects_to_render.clear()
        
        for ray, (depth, proj_height, texture, offset) in enumerate(self.ray_casting_result):
            texture_surface = self.textures[texture]
            texture_width = texture_surface.get_width()
            
            # Cálculo de coordenadas de textura
            subsurface_x = int(offset * (texture_width - SCALE))
            if proj_height < HEIGHT:
                texture_rect = (subsurface_x, 0, SCALE, TEXTURE_SIZE)
                wall_pos = (ray * SCALE, HALF_HEIGHT - proj_height // 2)
            else:
                texture_height = TEXTURE_SIZE * HEIGHT / proj_height
                texture_rect = (
                    subsurface_x,
                    HALF_TEXTURE_SIZE - texture_height // 2,
                    SCALE,
                    texture_height
                )
                wall_pos = (ray * SCALE, 0)
            
            # Escalado y preparación de la columna
            wall_column = texture_surface.subsurface(texture_rect)
            wall_column = pg.transform.scale(wall_column, (SCALE, HEIGHT if proj_height >= HEIGHT else proj_height))
            self.objects_to_render.append((depth, wall_column, wall_pos))

    def draw(self):
        """Renderiza las columnas en orden de profundidad."""
        for depth, image, pos in sorted(self.objects_to_render, key=lambda x: -x[0]):
            self.game.screen.blit(image, pos)

    def ray_cast(self):
        """Cálculo principal de raycasting."""
        self.ray_casting_result.clear()
        ox, oy = self.game.player.pos
        x_map, y_map = self.game.player.map_pos
        ray_angle = self.game.player.angle - HALF_FOV + 0.0001

        for ray in range(NUM_RAYS):
            sin_a = math.sin(ray_angle)
            cos_a = math.cos(ray_angle)
            
            depth = 0
            while depth < MAX_DEPTH:
                x = ox + depth * cos_a
                y = oy + depth * sin_a
                if (int(x), int(y)) in self.game.map.world_map:
                    texture = self.game.map.world_map[(int(x), int(y))]
                    break
                depth += 0.1

            # Proyección y corrección fish-eye
            depth *= math.cos(self.game.player.angle - ray_angle)
            proj_height = SCREEN_DIST / (depth + 1e-6)
            offset = (x % 1) if sin_a > 0 else (y % 1)
            
            self.ray_casting_result.append((depth, proj_height, texture, offset))
            ray_angle += DELTA_ANGLE

    def ray_cast_player_npc(self, npc_x, npc_y):
        """Verifica línea de visión entre NPC y jugador."""
        ox, oy = self.game.player.pos
        ray_angle = math.atan2(npc_y - oy, npc_x - ox)
        sin_a, cos_a = math.sin(ray_angle), math.cos(ray_angle)
        
        x, y = ox, oy
        for _ in range(MAX_DEPTH):
            x += cos_a * 0.1
            y += sin_a * 0.1
            if (int(x), int(y)) in self.game.map.world_map:
                return False
            if int(x) == int(npc_x) and int(y) == int(npc_y):
                return True
        return False