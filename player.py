import threading
import pygame as pg
import math
import asyncio
import queue
from settings import *

class Player:
    __slots__ = (
        'game', 'x', 'y', 'rect', 'angle', 'shot', 
        'health', 'rel', 'health_recovery_delay',
        'time_prev', 'diag_move_corr', 'rotation',
        'running', 'event_queue', 'input_queue', 'health_lock'
    )

    def __init__(self, game):
        # Inicialización de atributos principales
        self.game = game
        self.x, self.y = PLAYER_POS
        self.rect = pg.Rect(
            int(self.x * 100),
            int(self.y * 100),
            32, 32
        )
        
        # Configuración de estado inicial
        self.angle = PLAYER_ANGLE
        self.shot = False
        self.health = PLAYER_MAX_HEALTH
        self.rel = 0
        self.health_recovery_delay = 1000
        self.time_prev = pg.time.get_ticks()
        self.diag_move_corr = 1 / math.sqrt(2)
        self.rotation = 0
        self.running = False
        
        # Sistema de colas y bloqueos
        self.event_queue = queue.Queue()
        self.input_queue = queue.Queue()
        self.health_lock = threading.Lock()

    def start(self):
        """Inicia el hilo de actualización del jugador"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def run(self):
        """Punto de entrada del hilo de ejecución"""
        asyncio.run(self.update_loop())

    async def update_loop(self):
        """Bucle principal de actualización asíncrona"""
        while self.running:
            await self.update()
            await asyncio.sleep(0.016)  # ≈60 FPS

    def stop(self):
        """Detiene el hilo de ejecución de forma segura"""
        self.running = False
        if hasattr(self, "thread"):
            self.thread.join()

    async def recover_health(self):
        """Recuperación gradual de salud con bloqueo thread-safe"""
        time_now = pg.time.get_ticks()
        with self.health_lock:
            if (time_now - self.time_prev > self.health_recovery_delay and 
                self.health < PLAYER_MAX_HEALTH):
                self.health += 1
                self.time_prev = time_now

    def check_game_over(self):
        """Verifica y maneja el estado de game over"""
        with self.health_lock:
            if self.health < 1:
                self.game.object_renderer.game_over()
                pg.display.flip()
                pg.time.delay(1500)
                self.game.new_game()

    def get_damage(self, damage):
        """Aplica daño al jugador con protección contra race conditions"""
        with self.health_lock:
            self.health -= damage
        self.game.object_renderer.player_damage()
        self.game.sound.player_pain.play()
        self.check_game_over()

    async def movement(self, keys_state, delta_time):
        """Sistema de movimiento optimizado con física mejorada"""
        sin_a = math.sin(self.angle)
        cos_a = math.cos(self.angle)
        speed = PLAYER_SPEED * delta_time
        dx, dy = 0.0, 0.0
        
        # Cálculo vectorial optimizado
        dx += (keys_state[pg.K_w] - keys_state[pg.K_s]) * cos_a * speed
        dy += (keys_state[pg.K_w] - keys_state[pg.K_s]) * sin_a * speed
        dx += (keys_state[pg.K_a] - keys_state[pg.K_d]) * sin_a * speed
        dy -= (keys_state[pg.K_a] - keys_state[pg.K_d]) * cos_a * speed

        # Corrección de movimiento diagonal
        if sum(keys_state[key] for key in [pg.K_w, pg.K_s, pg.K_a, pg.K_d]) > 1:
            dx *= self.diag_move_corr
            dy *= self.diag_move_corr
        
        self.check_wall_collision(dx, dy, delta_time)
        self.angle %= math.tau

    def check_wall_collision(self, dx, dy, delta_time):
        """Detección de colisiones con optimización de rendimiento"""
        scale = PLAYER_SIZE_SCALE / delta_time
        next_x = self.x + dx * scale
        next_y = self.y + dy * scale
        
        if (int(next_x), int(self.y)) not in self.game.map.world_map:
            self.x += dx
            
        if (int(self.x), int(next_y)) not in self.game.map.world_map:
            self.y += dy

    def draw(self):
        """Renderizado optimizado con pre-cálculo de valores"""
        if self.game.screen:
            x = int(self.x * 100)
            y = int(self.y * 100)
            end_x = x + int(50 * math.cos(self.angle))
            end_y = y + int(50 * math.sin(self.angle))
            
            pg.draw.line(self.game.screen, (255, 255, 0), (x, y), (end_x, end_y), 2)
            pg.draw.circle(self.game.screen, (0, 255, 0), (x, y), 15)

    async def mouse_control(self, rel, delta_time):
        """Manejo de entrada de ratón con suavizado"""
        if rel != 0:
            self.angle += rel * MOUSE_SENSITIVITY * delta_time
            self.angle %= math.tau

    def single_fire_event(self, event):
        """Manejo de eventos de disparo"""
        if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
            self.event_queue.put("shoot")

    async def handle_shoot(self):
        """Lógica de disparo con control de tiempo"""
        if not self.shot:
            self.shot = True
            self.game.sound.shotgun.play()
            await asyncio.sleep(0.3)
            self.shot = False

    async def update(self):
        """Actualización principal con gestión de inputs"""
        keys_state = None
        mouse_rel = 0
        delta_time = self.game.delta_time

        # Procesamiento de cola de inputs
        while not self.input_queue.empty():
            try:
                keys, rel, dt = self.input_queue.get_nowait()
                keys_state = keys
                mouse_rel += rel
                delta_time = dt
            except queue.Empty:
                break

        await self.movement(keys_state, delta_time)
        await self.mouse_control(mouse_rel, delta_time)
        await self.recover_health()

        # Procesamiento de eventos de disparo
        while not self.event_queue.empty():
            event = self.event_queue.get()
            if event == "shoot":
                await self.handle_shoot()

    @property
    def map_pos(self):
        """Posición actual en coordenadas del mapa"""
        return int(self.x), int(self.y)

    @property
    def pos(self):
        """Posición precisa en coordenadas del mundo"""
        return self.x, self.y