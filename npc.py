import asyncio
import os
import math
import pygame as pg
from random import randint, random
from sprite_object import AnimatedSprite


class NPC(AnimatedSprite):
    def __init__(self, game, path='resources/sprites/npc/soldier/0.png', pos=(10.5, 5.5),
                 scale=0.6, shift=0.38, animation_time=180):
        super().__init__(game, path, pos, scale, shift, animation_time)
        self.attack_images = []
        self.death_images = []
        self.idle_images = []
        self.pain_images = []
        self.walk_images = []

        self.attack_dist = randint(3, 6)
        self.speed = 0.03
        self.size = 20
        self.health = 100
        self.attack_damage = 10
        self.accuracy = 0.15
        self.alive = True
        self.pain = False
        self.ray_cast_value = False
        self.frame_counter = 0
        self.player_search_trigger = False

    async def load_images(self):
        self.attack_images = await self.get_images_async(os.path.join(self.path, 'attack'))
        self.death_images = await self.get_images_async(os.path.join(self.path, 'death'))
        self.idle_images = await self.get_images_async(os.path.join(self.path, 'idle'))
        self.pain_images = await self.get_images_async(os.path.join(self.path, 'pain'))
        self.walk_images = await self.get_images_async(os.path.join(self.path, 'walk'))

    async def get_images_async(self, folder_path):
        images = []
        for img_name in os.listdir(folder_path):
            img_path = os.path.join(folder_path, img_name)
            image = pg.image.load(img_path).convert_alpha()
            images.append(image)
        return images

    def update(self):
        self.check_animation_time()
        self.get_sprite()
        self.run_logic()

    def movement(self):
        next_pos = self.game.pathfinding.get_path(self.map_pos, self.game.player.map_pos)
        if next_pos not in self.game.object_handler.npc_positions:
            angle = math.atan2(next_pos[1] + 0.5 - self.y, next_pos[0] + 0.5 - self.x)
            dx = math.cos(angle) * self.speed
            dy = math.sin(angle) * self.speed
            self.check_wall_collision(dx, dy)

    def attack(self):
        if self.animation_trigger:
            self.game.sound.npc_shot.play()
            if random() < self.accuracy:
                self.game.player.get_damage(self.attack_damage)

    def check_hit_in_npc(self):
        if self.ray_cast_value and self.game.player.shot:
            if self.screen_x - self.sprite_half_width < self.game.player.screen_x < self.screen_x + self.sprite_half_width:
                self.game.sound.npc_pain.play()
                self.game.player.shot = False
                self.pain = True
                self.health -= self.game.weapon.damage
                self.check_health()

    def check_health(self):
        if self.health <= 0:
            self.alive = False
            self.game.sound.npc_death.play()

    def run_logic(self):
        if self.alive:
            self.ray_cast_value = self.ray_cast_player_npc()
            self.check_hit_in_npc()
            if self.pain:
                self.animate(self.pain_images)
                if self.animation_trigger:
                    self.pain = False
            elif self.ray_cast_value:
                self.player_search_trigger = True
                if self.dist < self.attack_dist:
                    self.animate(self.attack_images)
                    self.attack()
                else:
                    self.animate(self.walk_images)
                    self.movement()
            elif self.player_search_trigger:
                self.animate(self.walk_images)
                self.movement()
            else:
                self.animate(self.idle_images)
        else:
            self.animate(self.death_images)

    @property
    def map_pos(self):
        return int(self.x), int(self.y)


class SoldierNPC(NPC):
    def __init__(self, game, path='resources/sprites/npc/soldier/0.png', pos=(10.5, 5.5),
                 scale=0.6, shift=0.38, animation_time=180):
        super().__init__(game, path, pos, scale, shift, animation_time)


class CyberDemonNPC(NPC):
    def __init__(self, game, path='resources/sprites/npc/cyber_demon/0.png', pos=(11.5, 6.0),
                 scale=1.0, shift=0.04, animation_time=210):
        super().__init__(game, path, pos, scale, shift, animation_time)
        self.attack_dist = 6
        self.health = 150
        self.attack_damage = 15
        self.speed = 0.055
        self.accuracy = 0.25


async def main():
    pg.init()
    game = None  # Aquí deberías inicializar tu objeto de juego principal
    npc = SoldierNPC(game)
    await npc.load_images()
    cyber_demon = CyberDemonNPC(game)
    await cyber_demon.load_images()
    
    running = True
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

        npc.update()
        cyber_demon.update()
        
        # Renderización aquí (dependerá de tu estructura de juego)

        await asyncio.sleep(0)  # Permite a pygbag manejar el bucle de eventos

    pg.quit()

if __name__ == "__main__":
    asyncio.run(main())
