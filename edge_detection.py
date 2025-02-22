# edge_detection.py (optimizado sin Numba)
import numpy as np
import pygame as pg

def detect_geometric_patterns(edges_array, max_search_steps=32):
    height, width = edges_array.shape
    patterns = np.zeros((height, width, 2), dtype=np.float32)
    
    # Vectorización NumPy para mejor rendimiento
    edges_padded = np.pad(edges_array, 1, mode='constant')
    
    # Búsqueda horizontal
    horizontal = np.minimum(
        np.argmax(edges_padded[1:-1, 2:] == 0, axis=1),
        max_search_steps
    )
    
    # Búsqueda vertical
    vertical = np.minimum(
        np.argmax(edges_padded[2:, 1:-1] == 0, axis=0),
        max_search_steps
    )
    
    patterns[1:-1, 1:-1, 0] = horizontal / max_search_steps
    patterns[1:-1, 1:-1, 1] = vertical / max_search_steps
    
    return patterns