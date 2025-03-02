import pygame as pg
import logging
from typing import Optional, Tuple
from enum import Enum, auto
from settings import FLOOR_COLOR

logger = logging.getLogger(__name__)

class ScalingMode(Enum):
    LETTERBOX = auto()
    STRETCH = auto()
    INTEGER_SCALE = auto()
    ASPECT_RATIO = auto()

class DisplayManager:
    """Sistema avanzado de gestión de pantalla con múltiples modos de escalado y HDR"""
    
    __slots__ = (
        'core', '_real_screen', '_safe_zone', '_scaling_mode',
        '_target_res', '_aspect_ratio', '_hdr_enabled', '_vsync',
        '_debug_overlay', '_color_profile'
    )

    def __init__(self, core):
        self.core = core
        self._real_screen: Optional[pg.Surface] = None
        self._safe_zone: Optional[pg.Surface] = None
        self._scaling_mode: ScalingMode = ScalingMode.LETTERBOX
        self._target_res: Tuple[int, int] = (1280, 720)
        self._aspect_ratio: float = 16 / 9
        self._hdr_enabled: bool = False
        self._vsync: bool = True
        self._debug_overlay: bool = False
        self._color_profile: str = 'sRGB'

        self._init_display()
        self._setup_defaults()

    def _init_display(self):
        """Inicialización segura del subsistema gráfico con fallback automático"""
        try:
            self._detect_display_capabilities()
            flags = self._get_display_flags()
            
            self._real_screen = pg.display.set_mode(
                (0, 0), 
                flags=flags | pg.FULLSCREEN,
                vsync=self._vsync
            )
            
            self._create_safe_zone()
            self._apply_color_profile()
            
        except pg.error as e:
            logger.critical(f"Error inicializando display: {e}")
            self._fallback_to_windowed()

    def _setup_defaults(self):
        """Configuración inicial de parámetros de renderizado"""
        pg.display.set_caption("Mi Juego")
        pg.display.set_icon(pg.image.load('assets/icon.png'))

    def _detect_display_capabilities(self):
        """Detecta capacidades avanzadas del monitor"""
        self._hdr_enabled = self._check_hdr_support()
        self._color_profile = 'HDR' if self._hdr_enabled else 'sRGB'

    def _get_display_flags(self):
        """Genera flags apropiados para la configuración actual"""
        flags = pg.HWSURFACE | pg.DOUBLEBUF
        if self._hdr_enabled:
            flags |= pg.OPENGL
            pg.display.gl_set_attribute(pg.GL_COLORSPACE, pg.GL_COLORSPACE_SCRGB)
        return flags

    def _check_hdr_support(self) -> bool:
        """Verifica soporte HDR/wide color gamut"""
        try:
            return pg.display.is_hdr_capable()
        except AttributeError:
            return False

    def _create_safe_zone(self):
        """Crea superficie de renderizado principal con gestión de color"""
        self._safe_zone = pg.Surface(
            self._target_res, 
            flags=pg.SRCALPHA | (pg.HWSURFACE if self._hdr_enabled else 0)
        ).convert_alpha()

    def _apply_color_profile(self):
        """Configura el perfil de color según las capacidades del sistema"""
        if self._hdr_enabled:
            self._safe_zone.set_colorspace('SCRGB')
            logger.info("Color profile: HDR/SCRGB")
        else:
            self._safe_zone.set_colorspace('sRGB')

    def _fallback_to_windowed(self):
        """Modo de emergencia para sistemas problemáticos"""
        logger.warning("Usando modo ventana de emergencia")
        self._real_screen = pg.display.set_mode(
            self._target_res, 
            flags=pg.SHOWN
        )
        self._create_safe_zone()

    def set_resolution(self, width: int, height: int):
        """Cambia dinámicamente la resolución objetivo"""
        self._target_res = (width, height)
        self._aspect_ratio = width / height
        self._create_safe_zone()
        self._update_viewport()

    def set_scaling_mode(self, mode: ScalingMode):
        """Configura el modo de escalado de imagen"""
        self._scaling_mode = mode
        self._update_viewport()

    def _update_viewport(self):
        """Actualiza los parámetros de la vista de cámara"""
        # Lógica para shaders de escalado
        pass

    def clear(self):
        """Limpia la pantalla con el color base"""
        self._safe_zone.fill(FLOOR_COLOR)

    def update(self):
        """Renderiza el contenido final en pantalla"""
        self._apply_scaling()
        self._handle_debug()
        pg.display.flip()

    def _apply_scaling(self):
        """Aplica el modo de escalado configurado"""
        scaled_surface = self._get_scaled_surface()
        position = self._calculate_position(scaled_surface)
        self._real_screen.blit(scaled_surface, position)

    def _get_scaled_surface(self) -> pg.Surface:
        """Genera la superficie escalada según el modo actual"""
        screen_w, screen_h = self._real_screen.get_size()
        target_w, target_h = self._target_res

        if self._scaling_mode == ScalingMode.STRETCH:
            return pg.transform.smoothscale(self._safe_zone, (screen_w, screen_h))

        if self._scaling_mode == ScalingMode.INTEGER_SCALE:
            scale = min(screen_w // target_w, screen_h // target_h)
            return pg.transform.scale_by(self._safe_zone, scale)

        if self._scaling_mode == ScalingMode.ASPECT_RATIO:
            ratio = min(screen_w/target_w, screen_h/target_h)
            return pg.transform.smoothscale(self._safe_zone, 
                (int(target_w * ratio), int(target_h * ratio)))

        # Modo Letterbox por defecto
        ratio = min(screen_w/target_w, screen_h/target_h)
        scaled_size = (int(target_w * ratio), int(target_h * ratio))
        return pg.transform.smoothscale(self._safe_zone, scaled_size)

    def _calculate_position(self, surface: pg.Surface) -> Tuple[int, int]:
        """Calcula posición para modos con barras laterales/superiores"""
        if self._scaling_mode in (ScalingMode.LETTERBOX, ScalingMode.ASPECT_RATIO):
            return (
                (self._real_screen.get_width() - surface.get_width()) // 2,
                (self._real_screen.get_height() - surface.get_height()) // 2
            )
        return (0, 0)

    def _handle_debug(self):
        """Muestra información de depuración si está habilitada"""
        if self._debug_overlay:
            self._draw_debug_info()

    def _draw_debug_info(self):
        """Renderiza overlay con información técnica"""
        debug_font = pg.font.SysFont('Consolas', 20)
        lines = [
            f"Resolución: {self.current_resolution}",
            f"Escalado: {self._scaling_mode.name}",
            f"FPS: {self.core.clock.get_fps():.1f}",
            f"Color: {self._color_profile}",
            f"VSync: {'On' if self._vsync else 'Off'}"
        ]
        
        y = 10
        for line in lines:
            text_surf = debug_font.render(line, True, (255, 255, 0), (0, 0, 128))
            self._real_screen.blit(text_surf, (10, y))
            y += text_surf.get_height() + 2

    @property
    def screen(self) -> pg.Surface:
        """Acceso seguro a la superficie de renderizado principal"""
        return self._safe_zone

    @property
    def current_resolution(self) -> Tuple[int, int]:
        """Devuelve la resolución física actual"""
        return self._real_screen.get_size() if self._real_screen else (0, 0)

    @property
    def logical_resolution(self) -> Tuple[int, int]:
        """Devuelve la resolución lógica del juego"""
        return self._target_res

    def toggle_debug_overlay(self):
        """Alterna la visualización de información de depuración"""
        self._debug_overlay = not self._debug_overlay

    def toggle_vsync(self):
        """Alterna la sincronización vertical"""
        self._vsync = not self._vsync
        self._init_display()

    def cleanup(self):
        """Libera recursos gráficos"""
        if self._safe_zone:
            self._safe_zone = None
        pg.display.quit()