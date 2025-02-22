import os
import pygame as pg
from settings import *

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ['SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR'] = '0'

class ObjectRenderer:
    def __init__(self, game):
        self.game = game
        # Configuración inicial de pantalla y resolución
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        self.screen_width = WIDTH
        self.screen_height = HEIGHT
        self.update_resolution_dependent_attributes()

        # Cargar texturas de paredes, overlays y HUD
        self.wall_textures = self.load_wall_textures()
        self.blood_screen = self.load_texture('resources/textures/blood_screen.png', (self.screen_width, self.screen_height))
        self.digit_size = 90  
        self.digits = {str(i): self.load_texture(f'resources/textures/digits/{i}.png', (self.digit_size, self.digit_size))
                       for i in range(11)}
        self.game_over_image = self.load_texture('resources/textures/game_over.png', (self.screen_width, self.screen_height))
        self.win_image = self.load_texture('resources/textures/win.png', (self.screen_width, self.screen_height))

    def update_resolution_dependent_attributes(self):
        # Actualiza atributos según la resolución actual
        self.screen_width = self.game.screen_width
        self.screen_height = self.game.screen_height
        self.half_height = self.screen_height // 2
        self.sky_image = self.load_texture('resources/textures/sky.png', (self.screen_width, self.half_height))
        self.sky_offset = 0

    def draw(self):
        self.draw_background()
        self.render_game_objects()
        self.draw_player_health()

    def win(self):
        self.screen.blit(self.win_image, (0, 0))

    def game_over(self):
        self.screen.blit(self.game_over_image, (0, 0))

    def draw_player_health(self):
        # Dibuja la salud del jugador usando dígitos precargados
        health_str = str(self.game.player.health)
        for i, digit in enumerate(health_str):
            self.screen.blit(self.digits[digit], (i * self.digit_size, 0))
        # Se dibuja "10" al final si es necesario (según tu lógica de HUD)
        self.screen.blit(self.digits['10'], ((len(health_str)) * self.digit_size, 0))

    def player_damage(self):
        self.screen.blit(self.blood_screen, (0, 0))

    def draw_background(self):
        # Actualiza el desplazamiento del cielo y dibuja el fondo
        self.sky_offset = (self.sky_offset + 4.5 * self.game.player.rel) % self.screen_width
        self.screen.blit(self.sky_image, (-self.sky_offset, 0))
        self.screen.blit(self.sky_image, (-self.sky_offset + self.screen_width, 0))
        pg.draw.rect(self.screen, FLOOR_COLOR, (0, self.half_height, self.screen_width, self.screen_height))

    def render_game_objects(self):
        # Dibuja los objetos del juego ordenados por profundidad (de más lejanos a más cercanos)
        objects = sorted(self.game.raycasting.objects_to_render, key=lambda t: t[0], reverse=True)
        for _, image, pos in objects:
            self.screen.blit(image, pos)

    @staticmethod
    def load_texture(path, res=(TEXTURE_SIZE, TEXTURE_SIZE)):
        # Carga la textura y la escala suavemente a la resolución especificada
        texture = pg.image.load(path).convert_alpha()
        return pg.transform.smoothscale(texture, res)

    def load_wall_textures(self):
        # Carga texturas de paredes (asumiendo que están numeradas del 1 al 5)
        return {i: self.load_texture(f'resources/textures/{i}.png') for i in range(1, 6)}

    def update(self):
        # Dibuja y actualiza la pantalla completa
        self.draw()
        pg.display.flip()
