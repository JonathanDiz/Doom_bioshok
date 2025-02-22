import threading
import pygame as pg
import math
import asyncio
import queue
from settings import *

class Player:
    def __init__(self, game):
        self.game = game
        self.x, self.y = PLAYER_POS
        self.angle = PLAYER_ANGLE
        self.shot = False  # Indica si el jugador ha disparado
        self.health = PLAYER_MAX_HEALTH
        self.rel = 0
        self.health_recovery_delay = 1000  # en milisegundos
        self.time_prev = pg.time.get_ticks()
        self.diag_move_corr = 1 / math.sqrt(2)
        self.rotation = 0
        self.running = False  # No inicia el hilo inmediatamente
        self.event_queue = queue.Queue()  # Cola para manejar eventos

    def start(self):
        """ Se llama cuando la pantalla ya está inicializada """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def run(self):
        """ Hilo independiente que maneja la actualización del jugador """
        asyncio.run(self.update_loop())

    async def update_loop(self):
        """ Bucle de actualización del jugador usando asyncio """
        while self.running:
            await self.update()
            await asyncio.sleep(0.016)  # 60 FPS (1000 / 60 ≈ 16 ms)

    def stop(self):
        """ Detiene el hilo cuando se cierra el juego """
        self.running = False
        if hasattr(self, "thread"):
            self.thread.join()

    async def recover_health(self):
        """ Recupera la salud del jugador con un retraso """
        time_now = pg.time.get_ticks()
        if time_now - self.time_prev > self.health_recovery_delay and self.health < PLAYER_MAX_HEALTH:
            self.health += 1
            self.time_prev = time_now

    def check_game_over(self):
        """ Verifica si el jugador ha perdido """
        if self.health < 1:
            self.game.object_renderer.game_over()
            pg.display.flip()
            pg.time.delay(1500)
            self.game.new_game()

    def get_damage(self, damage):
        """ Reduce la salud del jugador y verifica si ha perdido """
        self.health -= damage
        self.game.object_renderer.player_damage()
        self.game.sound.player_pain.play()
        self.check_game_over()

    async def movement(self):
        """ Maneja el movimiento del jugador """
        sin_a, cos_a = math.sin(self.angle), math.cos(self.angle)
        dx, dy = 0, 0
        speed = PLAYER_SPEED * self.game.delta_time
        keys = pg.key.get_pressed()
        num_key_pressed = 0
        if keys[pg.K_w]:
            num_key_pressed += 1
            dx += speed * cos_a
            dy += speed * sin_a
        if keys[pg.K_s]:
            num_key_pressed += 1
            dx -= speed * cos_a
            dy -= speed * sin_a
        if keys[pg.K_a]:
            num_key_pressed += 1
            dx += speed * sin_a
            dy -= speed * cos_a
        if keys[pg.K_d]:
            num_key_pressed += 1
            dx -= speed * sin_a
            dy += speed * cos_a

        # Corrección de movimiento diagonal
        if num_key_pressed > 1:
            dx *= self.diag_move_corr
            dy *= self.diag_move_corr

        self.check_wall_collision(dx, dy)
        self.angle %= math.tau

    def check_wall(self, x, y):
        """ Verifica si hay una pared en la posición (x, y) """
        return (x, y) not in self.game.map.world_map

    def check_wall_collision(self, dx, dy):
        """ Maneja las colisiones con las paredes """
        scale = PLAYER_SIZE_SCALE / self.game.delta_time
        if self.check_wall(int(self.x + dx * scale), int(self.y)):
            self.x += dx
        if self.check_wall(int(self.x), int(self.y + dy * scale)):
            self.y += dy

    def draw(self):
        """ Dibuja al jugador en la pantalla """
        if self.game.screen:  # Asegura que la pantalla esté inicializada
            pg.draw.line(self.game.screen, 'yellow', (self.x * 100, self.y * 100),
                         (self.x * 100 + WIDTH * math.cos(self.angle),
                          self.y * 100 + WIDTH * math.sin(self.angle)), 2)
            pg.draw.circle(self.game.screen, 'green', (self.x * 100, self.y * 100), 15)

    async def mouse_control(self):
        """ Maneja el control del mouse para rotar al jugador """
        if not pg.get_init():  # Asegura que Pygame esté corriendo antes de usar el mouse
            return 0
        
        mx, _ = pg.mouse.get_pos()
        if mx < MOUSE_BORDER_LEFT or mx > MOUSE_BORDER_RIGHT:
            pg.mouse.set_pos([HALF_WIDTH, HALF_HEIGHT])
        rel = pg.mouse.get_rel()[0]
        rel = max(-MOUSE_MAX_REL, min(MOUSE_MAX_REL, rel))
        self.angle += rel * MOUSE_SENSITIVITY * self.game.delta_time
        return rel

    def single_fire_event(self, event):
        """ Maneja el evento de disparo único """
        if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:  # Disparar con la barra espaciadora
            self.event_queue.put("shoot")  # Encola el evento de disparo

    async def handle_shoot(self):
        """ Maneja el disparo del jugador """
        if not self.shot:  # Evita múltiples disparos simultáneos
            self.shot = True
            print("¡Disparando!")  # Depuración
            self.game.sound.shotgun.play()  # Reproduce un sonido de disparo
            await asyncio.sleep(0.3)  # Retraso de 300 ms
            self.shot = False

    async def update(self):
        """ Lógica de actualización del jugador """
        await self.movement()
        await self.mouse_control()
        await self.recover_health()

        # Maneja eventos en la cola
        while not self.event_queue.empty():
            event = self.event_queue.get()
            if event == "shoot":
                await self.handle_shoot()

    @property
    def pos(self):
        return self.x, self.y

    @property
    def map_pos(self):
        return int(self.x), int(self.y)