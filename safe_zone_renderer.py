import pygame as pg
from settings import *
import os

class SafeZoneRenderer:
    def __init__(self, width, height, real_screen, game):
        self.real_screen = real_screen
        self.game = game
        self.current_mode = 'game'  # 'game' o 'menu'
        self.last_aspect_ratio = (width, height)
        
        # Configuración inicial
        self._create_safe_zone(width, height)
        self._load_menu_assets()
        
    def _create_safe_zone(self, width, height):
        """Crea/actualiza la superficie de la zona segura"""
        self.safe_zone = pg.Surface((width, height), pg.SRCALPHA)
        self.safe_zone_rect = self.safe_zone.get_rect()
        
    def _load_menu_assets(self):
        """Carga recursos específicos del menú"""
        # Usar os.path para rutas multiplataforma
        self.menu_bg = pg.image.load(os.path.join('assets', 'menu_bg.jpg')).convert_alpha()
        self.font = pg.font.Font(os.path.join('fonts', 'Teko-Regular.ttf'), 24)
        
        # Botones del menú
        self.buttons = {
            'play': {'rect': pg.Rect(350, 200, 100, 40), 'text': "Jugar"},
            'exit': {'rect': pg.Rect(350, 260, 100, 40), 'text': "Salir"}
        }

    def set_mode(self, mode):
        """Cambia entre modos de renderizado"""
        self.current_mode = mode
        if mode == 'menu':
            self._create_menu_surface()

    def _create_menu_surface(self):
        """Prepara la superficie específica del menú"""
        self.menu_surface = pg.Surface(self.safe_zone.get_size(), pg.SRCALPHA)
        self.menu_surface.blit(self.menu_bg, (0, 0))
        
        # Renderizar botones
        for btn in self.buttons.values():
            text_surf = self.font.render(btn['text'], True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=btn['rect'].center)
            pg.draw.rect(self.menu_surface, (30, 30, 30), btn['rect'])
            self.menu_surface.blit(text_surf, text_rect)

    def handle_input(self, event):
        """Procesa eventos de entrada para el menú"""
        if self.current_mode == 'menu':
            if event.type == pg.MOUSEBUTTONDOWN:
                mouse_pos = self._scale_mouse_position(pg.mouse.get_pos())
                for btn_name, btn in self.buttons.items():
                    if btn['rect'].collidepoint(mouse_pos):
                        return btn_name
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    return 'resume'
        return None

    def render(self):
        """Renderiza el contenido según el modo actual"""
        self.safe_zone.fill((0, 0, 0, 0))
        
        if self.current_mode == 'game':
            self._render_game()
        else:
            self._render_menu()
            
        self._scale_and_present()

    def _render_game(self):
        """Renderiza elementos del juego"""
        if self.game.map: self.game.map.draw()
        if self.game.raycasting: self.game.raycasting.draw()
        if self.game.object_renderer: self.game.object_renderer.draw()
        if self.game.weapon: self.game.weapon.draw()
        if self.game.pixel_renderer: self.game.pixel_renderer.render(self.safe_zone)

    def _render_menu(self):
        """Renderiza elementos del menú"""
        self.safe_zone.blit(self.menu_surface, (0, 0))
        # Actualizar elementos interactivos
        mouse_pos = self._scale_mouse_position(pg.mouse.get_pos())
        for btn in self.buttons.values():
            color = (80, 80, 80) if btn['rect'].collidepoint(mouse_pos) else (30, 30, 30)
            pg.draw.rect(self.safe_zone, color, btn['rect'])

    def _scale_mouse_position(self, pos):
        """Ajusta la posición del mouse a las coordenadas de la safe zone"""
        real_w, real_h = self.real_screen.get_size()
        scale_x = self.last_aspect_ratio[0] / real_w
        scale_y = self.last_aspect_ratio[1] / real_h
        return (int(pos[0] * scale_x), int(pos[1] * scale_y))

    def _scale_and_present(self):
        """Escala y muestra el contenido en pantalla real"""
        scaled = pg.transform.scale(self.safe_zone, self.real_screen.get_size())
        self.real_screen.blit(scaled, (0, 0))
        pg.display.flip()

    def update_dimensions(self, new_width, new_height):
        """Actualiza dimensiones al cambiar tamaño de ventana"""
        self._create_safe_zone(new_width, new_height)
        self.last_aspect_ratio = (new_width, new_height)
        if self.current_mode == 'menu':
            self._create_menu_surface()