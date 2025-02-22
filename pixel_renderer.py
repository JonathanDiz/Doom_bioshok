import pygame as pg
import numpy as np

class PixelRenderer:
    def __init__(self, width, height):
        """
        Inicializa el renderizador de píxeles.
        Crea un buffer de píxeles (array NumPy) con tamaño width x height y 3 canales (RGB).
        """
        self.width = width
        self.height = height
        # Creamos un buffer de píxeles inicializado en negro (0,0,0)
        self.buffer = np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def clear(self, color=(0, 0, 0)):
        """
        Limpia el buffer con el color dado (por defecto, negro).
        color: Tuple (R, G, B)
        """
        self.buffer[:, :] = color

    def set_pixel(self, x, y, color):
        """
        Establece el color de un píxel en la posición (x, y).
        Solo actualiza si (x, y) se encuentra dentro de los límites del buffer.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y, x] = color

    def draw_rect(self, x, y, w, h, color):
        """
        Dibuja un rectángulo en el buffer.
        x, y: Coordenadas superiores izquierdas
        w, h: Ancho y alto del rectángulo
        color: Tuple (R, G, B)
        """
        x_end = min(x + w, self.width)
        y_end = min(y + h, self.height)
        self.buffer[y:y_end, x:x_end] = color

    def draw_line(self, x0, y0, x1, y1, color):
        """
        Dibuja una línea utilizando el algoritmo de Bresenham.
        x0, y0: Coordenadas de inicio
        x1, y1: Coordenadas de fin
        color: Tuple (R, G, B)
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        if dx > dy:
            err = dx / 2.0
            while x != x1:
                self.set_pixel(x, y, color)
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
            self.set_pixel(x, y, color)
        else:
            err = dy / 2.0
            while y != y1:
                self.set_pixel(x, y, color)
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
            self.set_pixel(x, y, color)

    def render(self, screen):
        """
        Crea una superficie a partir del buffer y la dibuja en la pantalla.
        Este método se llama en el loop principal de tu juego.
        """
        # La función swapaxes es necesaria para que la superficie tenga las dimensiones correctas.
        surface = pg.surfarray.make_surface(self.buffer.swapaxes(0, 1))
        screen.blit(surface, (0, 0))
