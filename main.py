import pygame as pg
import asyncio
import concurrent.futures
from animation_system import AnimationPresets, AnimationSystem
from settings import *
from map import *
from player import Player
from raycasting import RayCasting
from object_renderer import ObjectRenderer
from sprite_object import *
from object_handler import ObjectHandler
from weapon import Weapon
from sound import Sound
from pathfinding_module import PathFinder, PathFinding
from menu import Menu
from stats import GameStats
from adaptive_display import initialize_adaptive_display
from safe_zone_renderer import SafeZoneRenderer
from pixel_renderer import PixelRenderer
from smaa_advanced import AdvancedSMAA

class Game:
    def __init__(self):
        pg.init()
        # Configuración de pantalla
        self.real_screen, self.real_width, self.real_height = initialize_adaptive_display(fullscreen=True)
        self.safe_zone = pg.Surface((WIDTH, HEIGHT))
        self.screen = self.safe_zone
        self.screen_width = WIDTH
        self.screen_height = HEIGHT
        
        self.animation_system = AnimationSystem()
        self.particles = []

        # Inicialización
        pathfinder = PathFinder(Game)

        # Sistema de renderizado
        self.clock = pg.time.Clock()
        self.delta_time = 1
        self.running = True
        self.global_trigger = False
        self.global_event = pg.USEREVENT + 0
        pg.time.set_timer(self.global_event, 40)
        
        # Componentes esenciales
        self.stats = GameStats()
        self.player = Player(self)
        self.map = Map(self)
        self.object_renderer = ObjectRenderer(self)
        self.raycasting = RayCasting(self)
        self.pixel_renderer = PixelRenderer(WIDTH, HEIGHT)
        self.smaa = AdvancedSMAA(self.safe_zone, passes=2)

        # Sistema de threads
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.loop = asyncio.get_event_loop()
        
        # Inicialización diferida
        self.lazy_initialization()
        
        # Configuración de pygame
        pg.mouse.set_visible(False)
        pg.event.set_grab(True)

    def lazy_initialization(self):
        """Inicializa componentes no críticos en segundo plano"""
        self.loop.run_in_executor(
            self.thread_pool, 
            self._init_background_components
        )

    async def animate_attack(self):
        await self.animation_system.parallel_animations(
            AnimationPresets.move_linear(...),
            AnimationPresets.scale_transition(...)
        )
    
    def update(self):
        self.animation_system.update()  # Si necesitas actualización manual

    def _init_background_components(self):
        """Componentes que no requieren el main thread"""
        self.pathfinding = PathFinding(self)
        self.sound = Sound(self)
        self.object_handler = ObjectHandler(self)

    def new_game(self):
        """Reinicia el estado del juego"""
        self.running = True
        self.player = Player(self)
        self.map = Map(self)
        self.object_renderer = ObjectRenderer(self)
        self.raycasting = RayCasting(self)
        self.object_handler = ObjectHandler(self)
        self.weapon = Weapon(self)
        self.stats.reset()
        
        if pg.mixer.get_init():
            pg.mixer.music.play(-1)

    async def async_update(self):
        """Actualización paralela de componentes"""
        tasks = [
            self.loop.run_in_executor(self.thread_pool, self.player.update),
            self.loop.run_in_executor(self.thread_pool, self.raycasting.update),
            self.loop.run_in_executor(self.thread_pool, self.object_handler.update),
            self.weapon.update_async()
        ]
        await asyncio.gather(*tasks)

    def sync_update(self):
        """Actualización síncrona requerida por Pygame"""
        self.check_events()
        self.delta_time = self.clock.tick(FPS)
        pg.display.flip()

    async def game_loop(self):
        asyncio.create_task(PathFinder.dynamic_obstacle_update())
        """Bucle principal del juego optimizado"""
        while self.running:
            await self.async_update()
            self.draw()
            await self.smaa.apply_async()
            self.sync_update()
            await asyncio.sleep(0)

    def draw(self):
        font = pg.font.SysFont('Arial', 24)
    
        # Renderizar texto de estadísticas
        death_surface = font.render(f"Muertes: {self.deaths}", True, (255, 255, 255))
        win_surface = font.render(f"Victorias: {self.wins}", True, (255, 255, 255))
    
        # Posicionamiento
        self.safe_zone_renderer.surface.blit(death_surface, (50, 100))
        self.safe_zone_renderer.surface.blit(win_surface, (50, 150))
        """Pipeline de renderizado optimizado"""
        self.safe_zone.fill(FLOOR_COLOR)
        self.object_renderer.draw()
        self.weapon.draw()
        self.pixel_renderer.render(self.safe_zone)


    # Uso async en update()
    async def npc_update(self):
        path = await self.pathfinder.find_path_async((self.x, self.y), target_pos)
        self.follow_path(path)


    def check_events(self):
        """Manejo de eventos eficiente"""
        for event in pg.event.get():
            if event.type in (pg.QUIT, pg.KEYDOWN) and event.key == pg.K_ESCAPE:
                self.running = False
            elif event.type == self.global_event:
                self.global_trigger = True
            self.player.single_fire_event(event)

class AsyncWeapon(Weapon):
    async def update_async(self):
        """Actualización asíncrona de animaciones complejas"""
        await self.game.loop.run_in_executor(
            self.game.thread_pool, 
            self.process_advanced_animations
        )

    def process_advanced_animations(self):
        """Lógica de animaciones optimizada para CPU"""
        # Implementación real de animaciones aquí
        pass

class GameStats:
    def __init__(self):
        self.deaths = 0
        self.wins = 0
    
    def reset(self):
        self.deaths = 0
        self.wins = 0

async def main():
    game = Game()

    # 1. Crear el renderizador de la zona segura del menú
    menu_safe_renderer = SafeZoneRenderer(
        width=WIDTH,
        height=HEIGHT,
        real_screen=game.real_screen,
        game=game
    )

    menu = Menu(game, safe_zone_renderer=menu_safe_renderer)
    menu.set_stats(game.stats.deaths, game.stats.wins)
    
    choice = await menu.run()
    if choice == "restart":
        game.new_game()
        await game.game_loop()
    
    pg.quit()

if __name__ == '__main__':
    asyncio.run(main())