import pygame as pg
from settings import FLOOR_COLOR, WIDTH, HEIGHT

class DisplayManager:
    """Manejador de la pantalla y renderizado."""
    def __init__(self, core):
        self.core = core
        self.real_screen = None
        self.safe_zone = None
        self.screen = None
        self._init_display()

    def _init_display(self):
        """Configura la pantalla principal."""
        self.real_screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
        self.safe_zone = pg.Surface((WIDTH, HEIGHT))
        self.screen = self.safe_zone

    def clear_screen(self):
        """Limpia la pantalla."""
        self.safe_zone.fill(FLOOR_COLOR)

    def flip_display(self):
        """Actualiza la pantalla."""
        pg.display.flip()