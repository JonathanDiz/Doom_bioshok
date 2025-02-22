import numpy as np
import pygame as pg

def rgb_to_luminance(color_array):
    """Conversión RGB a luminancia usando coeficientes BT.709 optimizados"""
    return np.dot(color_array[..., :3], [0.2126, 0.7152, 0.0722][..., np.newaxis]).squeeze()

class LuminanceAnalyzer:
    def __init__(self, decay_rate=0.2):
        self.decay_rate = np.clip(decay_rate, 0.01, 0.99)
        self.history = None
        self.epsilon = 1e-6  # Para estabilidad numérica

    def calculate_adaptive_luma(self, screen_array):
        """Cálculo adaptativo con suavizado temporal vectorizado"""
        current_luma = rgb_to_luminance(screen_array)
        
        if self.history is None:
            self.history = current_luma.copy()
        else:
            # Actualización exponencialmente ponderada
            np.subtract(current_luma, self.history, out=current_luma)
            np.multiply(current_luma, self.decay_rate, out=current_luma)
            np.add(self.history, current_luma, out=self.history)
        
        # Normalización y estabilización
        luma_min = self.history.min() - self.epsilon
        luma_max = self.history.max() + self.epsilon
        return np.clip((self.history - luma_min) / (luma_max - luma_min), 0.0, 1.0)