import asyncio
import pygame as pg
import math
from settings import *

class RayCasting:
    def __init__(self, game):
        self.game = game
        self.ray_casting_result = []
        self.objects_to_render = []
        self.textures = self.game.object_renderer.wall_textures

    def get_objects_to_render(self):
        """Prepara los objetos para renderizar."""
        self.objects_to_render.clear()
        textures = self.textures  # Referencia local

        for ray, (depth, proj_height, texture, offset) in enumerate(self.ray_casting_result):
            texture_surface = textures[texture]
            texture_width = texture_surface.get_width()
            subsurface_x = int(offset * (texture_width - SCALE))

            if proj_height < HEIGHT:
                wall_column = texture_surface.subsurface(
                    (subsurface_x, 0, SCALE, TEXTURE_SIZE)
                )
                wall_column = pg.transform.scale(wall_column, (SCALE, proj_height))
                wall_pos = (ray * SCALE, HALF_HEIGHT - proj_height // 2)
            else:
                texture_height = TEXTURE_SIZE * HEIGHT / proj_height
                wall_column = texture_surface.subsurface(
                    (subsurface_x, HALF_TEXTURE_SIZE - texture_height // 2, SCALE, texture_height)
                )
                wall_column = pg.transform.scale(wall_column, (SCALE, HEIGHT))
                wall_pos = (ray * SCALE, 0)

            self.objects_to_render.append((depth, wall_column, wall_pos))

    def draw(self):
        """Dibuja los objetos en la pantalla."""
        screen_blit = self.game.screen.blit  # Optimización
        for depth, wall_column, wall_pos in sorted(self.objects_to_render, key=lambda x: x[0], reverse=True):
            screen_blit(wall_column, wall_pos)

    def ray_cast(self):
        """Realiza el cálculo de raycasting simplificado."""
        self.ray_casting_result.clear()
        world_map = self.game.map.world_map  # Referencia local
        player = self.game.player  # Referencia local

        ox, oy = player.pos
        x_map, y_map = player.map_pos
        ray_angle = player.angle - HALF_FOV + 0.0001
        
        for ray in range(NUM_RAYS):
            sin_a, cos_a = math.sin(ray_angle), math.cos(ray_angle)

            # Cálculo de intersección con paredes
            depth = 0
            while depth < MAX_DEPTH:
                x = ox + depth * cos_a
                y = oy + depth * sin_a
                tile = int(x), int(y)
                if tile in world_map:
                    texture = world_map[tile]
                    break
                depth += 0.1  # Incremento de profundidad

            # Corrección de efecto fish-eye
            depth *= math.cos(player.angle - ray_angle)

            # Proyección
            proj_height = SCREEN_DIST / (depth + 1e-6)
            offset = (x % 1) if sin_a > 0 else (y % 1)  # Offset basado en la posición del rayo
            self.ray_casting_result.append((depth, proj_height, texture, offset))
            ray_angle += DELTA_ANGLE

    def ray_cast_player_npc(self, npc_x, npc_y):
        """Verifica si el NPC puede ver al jugador mediante raycasting."""
        ox, oy = self.game.player.pos
        ray_angle = math.atan2(npc_y - oy, npc_x - ox)
        sin_a, cos_a = math.sin(ray_angle), math.cos(ray_angle)
        
        x, y = ox, oy
        for _ in range(MAX_DEPTH):
            x += cos_a * 0.1
            y += sin_a * 0.1
            if (int(x), int(y)) in self.game.map.world_map:
                return False  # Bloqueado por una pared
            if int(x) == int(npc_x) and int(y) == int(npc_y):
                return True  # Hay línea de visión directa
        return False

    def update(self):
        """Actualiza el raycasting."""
        self.ray_cast()
        self.get_objects_to_render()
        asyncio.sleep(0)  # Cede el control al bucle de eventos