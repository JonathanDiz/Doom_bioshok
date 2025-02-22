import asyncio
import pygame as pg
from settings import FONT_PATH

class Menu:
    def __init__(self, game, safe_zone_renderer):
        self.game = game
        self.renderer = safe_zone_renderer
        self.stats = {'deaths': 0, 'wins': 0}
        self.running = False
        self.selected_choice = None
        self.font = pg.font.Font(FONT_PATH, 24)
        self.ui_elements = {}
        
        # Inicializar elementos del menú
        self._init_menu_ui()

        try:
            self.font = pg.font.Font(r'fonts/Teko-Regular.ttf', 32)  # Ruta absoluta recomendada
        except FileNotFoundError:
            self.font = pg.font.SysFont('Arial', 32, bold=True)  # Fallback a fuente del sistema

    def _init_menu_ui(self):
        """Configura los elementos visuales del menú"""
        # Botones principales
        self.ui_elements['play_button'] = {
            'rect': pg.Rect(300, 200, 200, 40),
            'text': "Nueva Partida",
            'action': "restart"
        }
        
        self.ui_elements['exit_button'] = {
            'rect': pg.Rect(300, 260, 200, 40),
            'text': "Salir del Juego",
            'action': "exit"
        }

        # Texto de estadísticas
        self.ui_elements['stats_text'] = {
            'position': (50, 400),
            'color': (200, 200, 200)
        }

    def set_stats(self, deaths, wins):
        """Actualiza y muestra las estadísticas en el menú"""
        self.stats = {'deaths': deaths, 'wins': wins}
        self._update_stats_surface()

    def _update_stats_surface(self):
        """Genera la superficie de texto de estadísticas"""
        stats_content = [
            f"Partidas Ganadas: {self.stats['wins']}",
            f"Muertes Totales: {self.stats['deaths']}"
        ]
        self.stats_surface = pg.Surface((400, 60), pg.SRCALPHA)
        y_offset = 0
        for line in stats_content:
            text_surf = self.font.render(line, True, self.ui_elements['stats_text']['color'])
            self.stats_surface.blit(text_surf, (0, y_offset))
            y_offset += 25

    async def run(self):
        """Bucle principal asíncrono del menú"""
        self.running = True
        self.selected_choice = None
        self.renderer.set_mode('menu')
        
        while self.running:
            await self._process_frame()
            
        return self.selected_choice

    async def _process_frame(self):
        """Procesa un frame completo del menú"""
        # Manejo de eventos
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.selected_choice = "exit"
                self.running = False
            else:
                self._handle_input(event)

        # Actualización y renderizado
        self._update_ui_state()
        self._draw_ui()
        self.renderer.render()
        
        await asyncio.sleep(0)  # Ceder control

    def _handle_input(self, event):
        """Procesa los eventos de entrada"""
        # Manejo de teclado
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_RETURN:  # Enter
                self.selected_choice = "restart"
                self.running = False
            elif event.key == pg.K_ESCAPE:  # Escape
                self.selected_choice = "exit"
                self.running = False
        elif event.type == pg.MOUSEBUTTONDOWN:
                
        # Manejo de ratón
            if event.type == pg.MOUSEBUTTONDOWN:
                mouse_pos = self.renderer._scale_mouse_position(pg.mouse.get_pos())
                for element in self.ui_elements.values():
                    if 'rect' in element and element['rect'].collidepoint(mouse_pos):
                        self.selected_choice = element.get('action')
                        self.running = False

    def _update_ui_state(self):
        """Actualiza el estado visual de los elementos UI"""
        mouse_pos = self.renderer._scale_mouse_position(pg.mouse.get_pos())
        for element in self.ui_elements.values():
            if 'rect' in element:
                element['hover'] = element['rect'].collidepoint(mouse_pos)

    def _draw_ui(self):
        """Renderiza todos los elementos del menú"""
        # Fondo
        self.renderer.safe_zone.fill((30, 30, 30))
    
        # Botones interactivos
        mouse_pos = self.renderer._scale_mouse_position(pg.mouse.get_pos())
        for element in self.ui_elements.values():
            if 'rect' in element:
                color = (100, 150, 200) if element['rect'].collidepoint(mouse_pos) else (50, 100, 150)
                self._draw_button(element['rect'], color, element['text'])
    
        # Estadísticas
        if hasattr(self, 'stats_surface'):
            self.renderer.safe_zone.blit(
                self.stats_surface,
                self.ui_elements['stats_text']['position']
            )
    
        # Actualizar solo una vez por frame
        pg.display.update()

    def _draw_button(self, rect, color, text):
        # Crear superficie con canal alpha
        text_surface = self.font.render(text, True, (255, 255, 255)).convert_alpha()
    
        # Fondo del botón con transparencia
        button_surface = pg.Surface(rect.size, pg.SRCALPHA)
        pg.draw.rect(button_surface, (*color, 128), (0, 0, *rect.size), border_radius=5)  # 128 = 50% opacidad
    
        # Combinar superficies
        button_surface.blit(text_surface, text_surface.get_rect(center=button_surface.get_rect().center))
    
        # Dibujar en la safe zone
        self.renderer.safe_zone.blit(button_surface, rect.topleft)