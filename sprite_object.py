import pygame as pg
from settings import *
import os
import math
from collections import deque


class SpriteObject:
    def __init__(self, game, path='resources/sprites/static_sprites/candlebra.png',
                 pos=(10.5, 3.5), scale=0.7, shift=0.27):
        self.game = game
        self.player = game.player
        self.x, self.y = pos
        self.image = pg.image.load(path).convert_alpha()
        self.image_width = self.image.get_width()
        self.image_half_width = self.image_width // 2
        self.image_ratio = self.image_width / self.image.get_height()
        self.dx, self.dy, self.theta, self.screen_x, self.dist, self.norm_dist = 0, 0, 0, 0, 1, 1
        self.sprite_half_width = 0
        self.sprite_scale = scale
        self.sprite_height_shift = shift

    def get_sprite_projection(self):
        proj = SCREEN_DIST / self.norm_dist * self.sprite_scale
        proj_width = int(proj * self.image_ratio)
        proj_height = int(proj)

        if (proj_width, proj_height) != self.image.get_size():
            image = pg.transform.scale(self.image, (proj_width, proj_height))
        else:
            image = self.image

        self.sprite_half_width = proj_width // 2
        height_shift = proj_height * self.sprite_height_shift
        pos = (self.screen_x - self.sprite_half_width, 
               HALF_HEIGHT - proj_height // 2 + height_shift)

        self.game.raycasting.objects_to_render.append((self.norm_dist, image, pos))

    def get_sprite(self):
        self.dx, self.dy = self.x - self.player.x, self.y - self.player.y
        self.theta = math.atan2(self.dy, self.dx)

        delta = math.fmod(self.theta - self.player.angle, math.tau)

        delta_rays = delta / DELTA_ANGLE
        self.screen_x = (HALF_NUM_RAYS + delta_rays) * SCALE

        self.dist = math.hypot(self.dx, self.dy)
        self.norm_dist = self.dist * math.cos(delta)

        if -self.image_half_width < self.screen_x < (WIDTH + self.image_half_width) and self.norm_dist > 0.5:
            self.get_sprite_projection()

    def update(self):
        self.get_sprite()


class AnimatedSprite(SpriteObject):
    def __init__(self, game, path='resources/sprites/animated_sprites/green_light/0.png',
                 pos=(11.5, 3.5), scale=0.8, shift=0.16, animation_time=120):
        super().__init__(game, path, pos, scale, shift)
        self.animation_time = animation_time
        self.path = os.path.dirname(path)
        self.images = self.get_images(self.path)
        self.animation_time_prev = pg.time.get_ticks()
        self.animation_trigger = False

    def update(self):
        super().update()
        self.check_animation_time()
        if self.animation_trigger:
            self.animate()

    def animate(self):
        self.images.rotate(-1)
        self.image = self.images[0]

    def check_animation_time(self):
        time_now = pg.time.get_ticks()
        if time_now - self.animation_time_prev >= self.animation_time:
            self.animation_time_prev = time_now
            self.animation_trigger = True

    def get_images(self, path):
        images = deque()
        for file_name in sorted(os.listdir(path)):
            file_path = os.path.join(path, file_name)
            if os.path.isfile(file_path):
                images.append(pg.image.load(file_path).convert_alpha())
        return images
