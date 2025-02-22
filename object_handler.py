import threading
import asyncio
import queue
import pygame as pg
import os
from sprite_object import *
from npc import *
from random import choices, randrange

class ObjectHandler:
    def __init__(self, game):
        self.game = game
        self.sprite_list = []
        self.npc_list = []
        self.npc_positions = {}
        self.running = False
        self.event_queue = queue.Queue()  # Cola para manejar eventos

        # Rutas de sprites
        self.npc_sprite_path = 'resources/sprites/npc/'
        self.static_sprite_path = 'resources/sprites/static_sprites/'
        self.anim_sprite_path = 'resources/sprites/animated_sprites/'

        # Agregar sprites iniciales
        self.add_sprite(AnimatedSprite(game))
        self._spawn_npc()

        # Mapa de sprites estáticos y animados
        self._add_static_sprites()

    def start(self):
        """Inicia el hilo de actualización."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def run(self):
        """Hilo independiente que maneja la actualización de NPCs y sprites."""
        asyncio.run(self.update_loop())

    async def update_loop(self):
        """Bucle de actualización usando asyncio."""
        while self.running:
            await self.update()
            await asyncio.sleep(0.016)  # 60 FPS (1000 / 60 ≈ 16 ms)

    def stop(self):
        """Detiene el hilo cuando se cierra el juego."""
        self.running = False
        if hasattr(self, "thread"):
            self.thread.join()

    def _spawn_npc(self):
        """Genera NPCs en posiciones aleatorias sin sobreponerse con el mapa."""
        self.enemies = 300  # Número de NPCs
        self.npc_types = [SoldierNPC, CyberDemonNPC]
        self.weights = [70, 10]
        self.restricted_area = {(i, j) for i in range(10) for j in range(10)}

        for _ in range(self.enemies):
            npc_class = choices(self.npc_types, self.weights)[0]
            pos = x, y = randrange(self.game.map.cols), randrange(self.game.map.rows)

            while pos in self.game.map.world_map or pos in self.restricted_area:
                pos = x, y = randrange(self.game.map.cols), randrange(self.game.map.rows)

            self.add_npc(npc_class(self.game, pos=(x + 0.5, y + 0.5)))

    def _add_static_sprites(self):
        """Agrega sprites estáticos y animados al juego."""
        animated_positions = [
            (1.5, 1.5), (1.5, 7.5), (5.5, 3.25), (5.5, 4.75),
            (7.5, 2.5), (7.5, 5.5), (14.5, 1.5), (14.5, 4.5),
            (14.5, 24.5), (14.5, 30.5), (1.5, 30.5), (1.5, 24.5)
        ]
        red_light_positions = [
            (14.5, 5.5), (14.5, 7.5), (12.5, 7.5), (9.5, 7.5),
            (14.5, 12.5), (9.5, 20.5), (10.5, 20.5), (3.5, 14.5), (3.5, 18.5)
        ]
        
        for pos in animated_positions:
            self.add_sprite(AnimatedSprite(self.game, pos=pos))

        for pos in red_light_positions:
            self.add_sprite(AnimatedSprite(self.game, path=self.anim_sprite_path + 'red_light/0.png', pos=pos))

    async def check_win(self):
        """Verifica si quedan NPCs vivos. Si no hay, reinicia el juego."""
        if not self.npc_positions:
            self.game.object_renderer.win()
            pg.display.flip()
            await asyncio.sleep(1.5)  # Espera 1.5 segundos
            self.game.new_game()

    async def update(self):
        """Actualiza la lista de NPCs y sprites en el juego."""
        self.npc_positions = {npc.map_pos for npc in self.npc_list if npc.alive}

        # Actualiza sprites
        for sprite in self.sprite_list:
            sprite.update()

        # Actualiza NPCs
        for npc in self.npc_list:
            npc.update()

        # Verifica si el jugador ha ganado
        await self.check_win()

    def add_npc(self, npc):
        """Agrega un NPC a la lista."""
        self.npc_list.append(npc)

    def add_sprite(self, sprite):
        """Agrega un sprite a la lista."""
        self.sprite_list.append(sprite)

    @staticmethod
    def get_texture(path, res=(64, 64)):
        """Carga y redimensiona una imagen con Pygame."""
        texture = pg.image.load(path).convert_alpha()
        return pg.transform.smoothscale(texture, res)

    def load_animated_sprite(self, path, res=(64, 64)):
        """Carga los frames de una animación."""
        frames = []
        for file_name in sorted(os.listdir(path)):
            full_path = os.path.join(path, file_name)
            frames.append(self.get_texture(full_path, res))
        return frames