import pygame as pg
import numpy as np
from edge_detection import detect_geometric_patterns
from luminance import LuminanceAnalyzer
from blending_weights import calculate_distance_weights

class MultiPassSMAA:
    def __init__(self, screen, passes=2):
        self.screen = screen
        self.passes = passes
        self.luma_analyzer = LuminanceAnalyzer()
        
        # Buffers para múltiples pasadas
        self.pass_buffers = [
            pg.Surface(screen.get_size(), pg.SRCALPHA)
            for _ in range(passes)
        ]
        
        # Parámetros de calidad
        self.edge_threshold = 0.08
        self.blend_strength = 0.65

    def execute_passes(self):
        current_buffer = pg.surfarray.array3d(self.screen)
        
        for pass_num in range(self.passes):
            # 1. Cálculo de luminancia adaptativa
            luma = self.luma_analyzer.calculate_adaptive_luma(current_buffer)
            
            # 2. Detección de bordes con patrones geométricos
            edges = (luma > self.edge_threshold).astype(np.uint8) * 255
            patterns = detect_geometric_patterns(edges)
            
            # 3. Cálculo de pesos de blending
            weights = calculate_distance_weights(edges)
            
            # 4. Aplicar mezcla
            blended = self._apply_blending(current_buffer, patterns, weights)
            
            # Actualizar buffer para la siguiente pasada
            pg.surfarray.blit_array(self.pass_buffers[pass_num], blended)
            current_buffer = blended
        
        # Aplicar el resultado final
        self.screen.blit(self.pass_buffers[-1], (0, 0))

    def _apply_blending(self, color_buffer, patterns, weights):
        blended = np.copy(color_buffer)
        height, width, _ = blended.shape
        
        for y in range(1, height-1):
            for x in range(1, width-1):
                if weights[y, x] > 0:
                    # Mezcla basada en patrones y pesos
                    h_pattern, v_pattern = patterns[y, x]
                    blend_factor = self.blend_strength * weights[y, x]
                    
                    # Mezcla horizontal
                    blended[y, x] = (color_buffer[y, x] * (1 - blend_factor) +
                                    color_buffer[y, x + 1] * blend_factor * h_pattern)
                    
                    # Mezcla vertical
                    blended[y, x] = (blended[y, x] * (1 - blend_factor) +
                                    color_buffer[y + 1, x] * blend_factor * v_pattern)
        
        return blended