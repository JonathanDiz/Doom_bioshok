import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

def calculate_distance_weights(edges_array, max_distance=32):
    """
    Calcula pesos de blending basados en distancia a bordes usando operaciones vectorizadas.
    Compatible con Python 3.13 y pygbag.
    """
    height, width = edges_array.shape
    max_sq = max_distance ** 2
    
    # 1. Precomputar matriz de distancias para vecindario 5x5
    y, x = np.ogrid[-2:3, -2:3]
    dist_matrix = (x**2 + y**2).astype(np.float32)

    # 2. Crear ventanas deslizantes 5x5 con padding
    padded = np.pad(edges_array, 2, mode='constant', constant_values=1)
    windows = sliding_window_view(padded, (5, 5))

    # 3. Encontrar mínima distancia a borde en cada ventana
    edge_mask = (windows == 0)
    valid_dists = np.where(edge_mask, dist_matrix, np.inf)
    min_dists = np.sqrt(np.min(valid_dists, axis=(2, 3)))

    # 4. Calcular pesos y normalizar
    weights = np.clip(1.0 - (min_dists / max_distance), 0.0, 1.0)
    
    # 5. Aplicar máscara de bordes originales
    return np.where(edges_array > 0, weights, 0).astype(np.float32)