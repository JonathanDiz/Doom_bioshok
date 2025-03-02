import math
import pygame as pg

# Configuración principal del juego
GAME_CONFIG = {
    'resolution': (1280, 720),
    'max_fps': 60,
    'window_title': "FPS Game",
    'asset_paths': {
        'textures': 'assets/textures',
        'sounds': 'assets/audio',
        'fonts': 'assets/fonts',
        'models': 'assets/models'
    },
    'debug': {
        'show_fps': True,
        'log_level': 'DEBUG'
    },
    'input': {
        'mouse_sensitivity': 1.5,
        'invert_y_axis': False
    }
}

# Configuración específica de renderizado
RESOLUTION = GAME_CONFIG['resolution']
FPS = GAME_CONFIG['max_fps']

# Configuración del jugador
PLAYER_CONFIG = {
    'move_speed': 4.5,
    'jump_force': 8.0,
    'max_health': 100
}

# Resolución
RESOLUTION = (1280, 720)
HALF_WIDTH = RESOLUTION[0] // 2
HALF_HEIGHT = RESOLUTION[1] // 2
WIDTH = 100  # Ajustar según necesidades de renderizado

# Jugador
PLAYER_POS = (1.5, 1.5)
PLAYER_ANGLE = 0
PLAYER_MAX_HEALTH = 100
PLAYER_SPEED = 0.004
PLAYER_SIZE_SCALE = 0.2

# Mouse
MOUSE_BORDER_LEFT = 100
MOUSE_BORDER_RIGHT = RESOLUTION[0] - 100
MOUSE_MAX_REL = 40
MOUSE_SENSITIVITY = 0.0002

# game settings
RES = WIDTH, HEIGHT = 1600, 900
# RES = WIDTH, HEIGHT = 1920, 1080
HALF_WIDTH = RESOLUTION[0] // 2
HALF_HEIGHT = RESOLUTION[1] // 2
FPS = 0
FONT_PATH = r"fonts\Teko-Regular.ttf"
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FLOOR_COLOR = (150, 150, 150)

PLAYER_POS = 1.5, 5  # mini_map
PLAYER_ANGLE = 0
PLAYER_SPEED = 0.004
PLAYER_ROT_SPEED = 0.002
PLAYER_SIZE_SCALE = 60
PLAYER_MAX_HEALTH = 100

MOUSE_SENSITIVITY = 0.0003
MOUSE_MAX_REL = 40
MOUSE_BORDER_LEFT = 100
MOUSE_BORDER_RIGHT = WIDTH - MOUSE_BORDER_LEFT

FLOOR_COLOR = (30, 30, 30)

FOV = math.pi / 3
HALF_FOV = FOV / 2
NUM_RAYS = WIDTH // 2
HALF_NUM_RAYS = NUM_RAYS // 2
DELTA_ANGLE = FOV / NUM_RAYS
MAX_DEPTH = 20

SCREEN_DIST = HALF_WIDTH / math.tan(HALF_FOV)
SCALE = WIDTH // NUM_RAYS

TEXTURE_SIZE = 256
TILE_SIZE = 60
HALF_TEXTURE_SIZE = TEXTURE_SIZE // 2
MUSIC_ON = True
MUSIC_PATH= 'resources/sound/theme.mp3'