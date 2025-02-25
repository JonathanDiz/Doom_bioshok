import pygame as pg

class Initialization:
    """Manejador de la inicialización de Pygame y componentes esenciales."""
    def __init__(self, core):
        self.core = core
        self._init_pygame()

    def _init_pygame(self):
        """Inicializa Pygame y configura parámetros básicos."""
        pg.init()
        pg.mouse.set_visible(False)
        pg.event.set_grab(True)
        pg.time.set_timer(pg.USEREVENT + 0, 40)