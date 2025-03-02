import math
import pygame as pg

# Configuración centralizada del juego
GAME_CONFIG = {
    'core': {
        'resolution': (1280, 720),
        'max_fps': 60,
        'window_title': "FPS Game",
        'font_path': r"fonts\Teko-Regular.ttf",
        'music': {
            'enabled': True,
            'theme_path': 'resources/sound/theme.mp3'
        }
    },
    
    'player': {
        'position': (1.5, 5),  # Posición en el mini mapa
        'angle': 0,
        'move_speed': 4.5,
        'rotation_speed': 0.002,
        'jump_force': 8.0,
        'size_scale': 60,
        'max_health': 100,
        'fov': math.pi / 3,
        'max_depth': 20
    },
    
    'render': {
        'floor_color': (30, 30, 30),
        'texture_size': 256,
        'tile_size': 60,
        'num_rays': None,  # Se calcula dinámicamente
        'scale': None,      # Se calcula dinámicamente
        'screen_dist': None # Se calcula dinámicamente
    },
    
    'controls': {
        'mouse': {
            'sensitivity': 0.0003,
            'max_rel': 40,
            'border_left': 100,
            'border_right': None  # Se calcula dinámicamente
        },
        'invert_y_axis': False
    },
    
    'assets': {
        'textures': 'assets/textures',
        'sounds': 'assets/audio',
        'fonts': 'assets/fonts',
        'models': 'assets/models'
    },
    
    'debug': {
        'show_fps': True,
        'log_level': 'DEBUG',
        'colors': {
            'white': (255, 255, 255),
            'black': (0, 0, 0)
        }
    }
}

PLAYER_POS = [100, 100]
PLAYER_ANGLE = 0
PLAYER_MAX_HEALTH = 100
PLAYER_SPEED = 5
PLAYER_SIZE_SCALE = 1.5
MOUSE_SENSITIVITY = 0.5

# Cálculos dinámicos basados en configuración
RESOLUTION = GAME_CONFIG['core']['resolution']
GAME_CONFIG['render']['num_rays'] = RESOLUTION[0] // 2
GAME_CONFIG['render']['scale'] = RESOLUTION[0] // GAME_CONFIG['render']['num_rays']
GAME_CONFIG['render']['screen_dist'] = (RESOLUTION[0] // 2) / math.tan(GAME_CONFIG['player']['fov'] / 2)
GAME_CONFIG['controls']['mouse']['border_right'] = RESOLUTION[0] - GAME_CONFIG['controls']['mouse']['border_left']

# Accesos rápidos
CORE = GAME_CONFIG['core']
PLAYER = GAME_CONFIG['player']
RENDER = GAME_CONFIG['render']
CONTROLS = GAME_CONFIG['controls']
ASSETS = GAME_CONFIG['assets']
DEBUG = GAME_CONFIG['debug']

# Constantes derivadas
HALF_RES = (RESOLUTION[0] // 2, RESOLUTION[1] // 2)
HALF_FOV = PLAYER['fov'] / 2
DELTA_ANGLE = PLAYER['fov'] / RENDER['num_rays']
HALF_TEXTURE_SIZE = RENDER['texture_size'] // 2

# Variables de estado del juego (deberían estar en otro módulo)
current_fps = 0
player_health = PLAYER['max_health']