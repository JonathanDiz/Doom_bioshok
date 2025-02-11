import os
from PIL import Image, ImageCms
import pygame as pg
from settings import *

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ['SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR'] = '0'
os.environ['PYGAME_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR'] = '0'

class ObjectRenderer:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.update_resolution_dependent_attributes()
        self.wall_textures = self.load_wall_textures()
        self.blood_screen = self.get_texture_with_antialiasing('resources/textures/blood_screen.png', (self.screen_width, self.screen_height))
        self.digit_size = 90  # Puedes ajustar este tamaño según sea necesario
        self.digit_images = [self.get_texture_with_antialiasing(f'resources/textures/digits/{i}.png', [self.digit_size] * 2)
                            for i in range(11)]
        self.digits = dict(zip(map(str, range(11)), self.digit_images))
        self.game_over_image = self.get_texture_with_antialiasing('resources/textures/game_over.png', (self.screen_width, self.screen_height))
        self.win_image = self.get_texture_with_antialiasing('resources/textures/win.png', (self.screen_width, self.screen_height))

    def update_resolution_dependent_attributes(self):
        self.screen_width = self.game.screen_width
        self.screen_height = self.game.screen_height
        self.half_height = self.screen_height // 2
        self.sky_image = self.get_texture_with_antialiasing('resources/textures/sky.png', (self.screen_width, self.half_height))
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
        health = str(self.game.player.health)
        for i, char in enumerate(health):
            self.screen.blit(self.digits[char], (i * self.digit_size, 0))
        self.screen.blit(self.digits['10'], ((i + 1) * self.digit_size, 0))

    def player_damage(self):
        self.screen.blit(self.blood_screen, (0, 0))

    def draw_background(self):
        self.sky_offset = (self.sky_offset + 4.5 * self.game.player.rel) % self.screen_width
        self.screen.blit(self.sky_image, (-self.sky_offset, 0))
        self.screen.blit(self.sky_image, (-self.sky_offset + self.screen_width, 0))
        # floor
        pg.draw.rect(self.screen, FLOOR_COLOR, (0, self.half_height, self.screen_width, self.screen_height))

    def render_game_objects(self):
        list_objects = sorted(self.game.raycasting.objects_to_render, key=lambda t: t[0], reverse=True)
        for depth, image, pos in list_objects:
            self.screen.blit(image, pos)

    @staticmethod
    def correct_image_color_profile(path):
        # Abre la imagen con Pillow
        image = Image.open(path)
        
        # Verifica si la imagen tiene un canal alfa (transparencia)
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            alpha = image.split()[-1] if image.mode in ('RGBA', 'LA') else image.convert('RGBA').split()[-1]
            image = image.convert('RGB').convert('RGBA')
            image.putalpha(alpha)
        else:
            image = image.convert('RGB')
        
        # Guarda la imagen en un nuevo archivo temporal
        corrected_path = f"{path}_corrected.png"
        image.save(corrected_path, format='PNG')
        
        return corrected_path

    @staticmethod
    def get_texture_with_antialiasing(path, res=(TEXTURE_SIZE, TEXTURE_SIZE)):
        # Corrige el perfil de color de la imagen
        corrected_path = ObjectRenderer.correct_image_color_profile(path)
        
        # Carga la imagen corregida con Pygame
        texture = pg.image.load(corrected_path).convert_alpha()
        os.remove(corrected_path)  # Elimina el archivo temporal
        
        return pg.transform.smoothscale(texture, res)

    def load_wall_textures(self):
        return {
            1: self.get_texture_with_antialiasing('resources/textures/1.png'),
            2: self.get_texture_with_antialiasing('resources/textures/2.png'),
            3: self.get_texture_with_antialiasing('resources/textures/3.png'),
            4: self.get_texture_with_antialiasing('resources/textures/4.png'),
            5: self.get_texture_with_antialiasing('resources/textures/5.png'),
        }

    def update(self):
        self.draw()
        pg.display.update()
