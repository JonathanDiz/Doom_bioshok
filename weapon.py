import threading
import asyncio
import queue
import pygame as pg
from collections import deque
from sprite_object import *

class Weapon(AnimatedSprite):
    def __init__(self, game, path='resources/sprites/weapon/shotgun/0.png', scale=0.4, animation_time=90):
        super().__init__(game, path=path, scale=scale, animation_time=animation_time)
        # Calcular el tamaño escalado una sola vez
        base_width = self.image.get_width()
        base_height = self.image.get_height()
        scaled_size = (int(base_width * scale), int(base_height * scale))
        # Escalar todas las imágenes de la animación de forma simultánea
        self.images = deque([pg.transform.smoothscale(img, scaled_size) for img in self.images])
        # Calcular la posición para centrar el arma en la pantalla
        self.weapon_pos = (HALF_WIDTH - self.images[0].get_width() // 2, HEIGHT - self.images[0].get_height())
        self.reloading = False
        self.num_images = len(self.images)
        self.frame_counter = 0
        self.damage = 50
        self.running = False
        self.event_queue = queue.Queue()  # Cola para manejar eventos

    def start(self):
        """Inicia el hilo de actualización."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def run(self):
        """Hilo independiente que maneja la animación del arma."""
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

    async def animate_shot(self):
        """Maneja la animación del disparo."""
        if self.reloading and self.animation_trigger:
            # Al disparar, el jugador ya no queda en modo "shot"
            self.game.player.shot = False
            # Rotar el deque para cambiar el frame de la animación
            self.images.rotate(-1)
            self.frame_counter += 1
            if self.frame_counter >= self.num_images:
                self.reloading = False
                self.frame_counter = 0
            # Actualizar la imagen mostrada
            self.image = self.images[0]

    def draw(self):
        """Dibuja el arma en la pantalla."""
        self.game.screen.blit(self.images[0], self.weapon_pos)

    async def update(self):
        """Actualiza la lógica del arma."""
        self.check_animation_time()
        await self.animate_shot()

    def fire(self):
        """Dispara el arma."""
        if not self.reloading:
            self.reloading = True
            self.event_queue.put("fire")  # Encola el evento de disparo

    async def handle_fire(self):
        """Maneja el evento de disparo."""
        if not self.reloading:
            self.reloading = True
            await self.animate_shot()