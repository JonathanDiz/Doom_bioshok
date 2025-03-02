import asyncio
import os
import math
import threading
import queue
import pygame as pg
from random import randint, random
from npc_animator import NPCAnimator
from sprite_object import AnimatedSprite

# En tu clase NPC
class NPC:
    def __init__(self, id, x, y):
        self.id = id
        self.x = x
        self.y = y
        self.animator = NPCAnimator(Game)
        
    async def patrol(self):
        await self.animator.dynamic_pathfinding(
            self, 
            target_pos=(500, 300),
            grid_matrix=Game.map.grid_matrix
        )
        
    async def attack(self, target):
        await self.animator.attack_movement(self, target)
        
    async def take_damage(self):
        await self.animator.damage_reaction(self)
        await self.animator.smooth_rotate(self, self.angle + 45)

# Definición de las clases auxiliares
class Pathfinding:
    def get_path(self, start, end):
        # Implementa la lógica de búsqueda de ruta
        return [(1, 1), (2, 2)]  # Ejemplo de ruta

class Player:
    def __init__(self):
        self.map_pos = (0, 0)  # Posición del jugador en el mapa
        self.screen_x = 400    # Posición X del jugador en la pantalla
        self.shot = False      # Indica si el jugador ha disparado

    def get_damage(self, damage):
        # Implementa la lógica para recibir daño
        print(f"Player recibe {damage} de daño")

class ObjectHandler:
    def __init__(self):
        self.npc_positions = []  # Lista de posiciones de NPCs

class SoundManager:
    def __init__(self):
        self.npc_shot = pg.mixer.Sound("resources/sound/shotgun.wav")  # Sonido de disparo
        self.npc_pain = pg.mixer.Sound("resources/sound/npc_pain.wav")  # Sonido de dolor
        self.npc_death = pg.mixer.Sound("resources/sound/npc_death.wav")  # Sonido de muerte

class Weapon:
    def __init__(self):
        self.damage = 10  # Daño del arma

# Definición de la clase Game
class Game:
    def __init__(self):
        self.pathfinding = Pathfinding()
        self.player = Player()
        self.object_handler = ObjectHandler()
        self.sound = SoundManager()
        self.weapon = Weapon()

# Definición de la clase NPC
class NPC(AnimatedSprite):
    def __init__(self, game, path='resources/sprites/npc/soldier/0.png', pos=(10.5, 5.5), scale=0.6, shift=0.38, animation_time=180):
        super().__init__(game, path, pos, scale, shift, animation_time)
        self.attack_images = []
        self.death_images = []
        self.idle_images = []
        self.pain_images = []
        self.walk_images = []
        self.attack_dist = randint(3, 6)
        self.speed = 0.03
        self.health = 100
        self.attack_damage = 10
        self.accuracy = 0.15
        self.alive = True
        self.pain = False
        self.ray_cast_value = False
        self.player_search_trigger = False
        self.event_queue = queue.Queue()  # Cola para manejar eventos

    async def load_images(self):
        """Carga todas las imágenes de forma asíncrona."""
        paths = ['attack', 'death', 'idle', 'pain', 'walk']
        self.attack_images, self.death_images, self.idle_images, self.pain_images, self.walk_images = \
            await asyncio.gather(*(self.get_images_async(os.path.join(self.path, p)) for p in paths))

    async def get_images_async(self, folder_path):
        """Carga imágenes de un directorio de forma asíncrona."""
        images = []
        if os.path.exists(folder_path):
            for img_name in sorted(os.listdir(folder_path)):
                img_path = os.path.join(folder_path, img_name)
                images.append(pg.image.load(img_path).convert_alpha())
        return images

    def update(self):
        """Actualiza la lógica del NPC."""
        self.check_animation_time()
        self.get_sprite()
        self.run_logic()

    def movement(self):
        """Maneja el movimiento del NPC."""
        next_pos = self.game.pathfinding.get_path(self.map_pos, self.game.player.map_pos)
        if next_pos and next_pos not in self.game.object_handler.npc_positions:
            angle = math.atan2(next_pos[1] + 0.5 - self.y, next_pos[0] + 0.5 - self.x)
            dx, dy = math.cos(angle) * self.speed, math.sin(angle) * self.speed
            self.check_wall_collision(dx, dy)

    def ray_cast_player_npc(self):
        """Implementación del raycast."""
        return True  # O un valor adecuado según tu lógica

    def attack(self):
        """Maneja el ataque del NPC."""
        if self.animation_trigger:
            self.game.sound.npc_shot.play()
        if random() < self.accuracy:
            self.game.player.get_damage(self.attack_damage)

    def check_hit_in_npc(self):
        """Verifica si el NPC ha sido golpeado."""
        if self.ray_cast_value and self.game.player.shot and \
           self.screen_x - self.sprite_half_width < self.game.player.screen_x < self.screen_x + self.sprite_half_width:
            self.game.sound.npc_pain.play()
            self.game.player.shot = False
            self.pain = True
            self.health -= self.game.weapon.damage
            self.check_health()

    def check_health(self):
        """Verifica la salud del NPC."""
        if self.health <= 0:
            self.alive = False
            self.game.sound.npc_death.play()

    async def run_logic(self):
        """Ejecuta la lógica del NPC."""
        if not self.alive:
            self.animate(self.death_images)
            return

        self.ray_cast_value = self.ray_cast_player_npc()
        self.check_hit_in_npc()

        if self.pain:
            self.animate(self.pain_images)
        elif self.ray_cast_value:
            self.player_search_trigger = True
            if self.dist < self.attack_dist:
                self.animate(self.attack_images)
                self.attack()
        else:
            self.animate(self.walk_images)

    @property
    def map_pos(self):
        return int(self.x), int(self.y)

class SoldierNPC(NPC):
    def __init__(self, game, pos=(10.5, 5.5)):
        super().__init__(game, path='resources/sprites/npc/soldier/0.png', pos=pos)

class CyberDemonNPC(NPC):
    def __init__(self, game, pos=(11.5, 6.0)):
        super().__init__(game, path='resources/sprites/npc/cyber_demon/0.png', pos=pos, scale=1.0, shift=0.04, animation_time=210)
        self.attack_dist = 6
        self.health = 150
        self.attack_damage = 15
        self.speed = 0.055
        self.accuracy = 0.25

async def main():
    pg.init()
    game = Game()  # Inicializa la clase Game
    soldier_npc = SoldierNPC(game)
    cyber_demon = CyberDemonNPC(game)

    await asyncio.gather(soldier_npc.load_images(), cyber_demon.load_images())

    running = True
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
        await soldier_npc.update()
        await cyber_demon.update()
        await asyncio.sleep(0)  # Optimización para Pygbag

    pg.quit()

if __name__ == "__main__":
    asyncio.run(main())