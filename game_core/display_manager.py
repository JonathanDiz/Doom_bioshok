import pygame as pg
import logging
from typing import Tuple, Optional
from enum import Enum, auto

logger = logging.getLogger(__name__)

class ScalingMode(Enum):
    LETTERBOX = auto()
    STRETCH = auto()
    INTEGER_SCALE = auto()
    ASPECT_RATIO = auto()

class DisplayManager:
    """Gestión avanzada de pantalla con soporte multi-resolución, escalado y HDR"""
    
    __slots__ = (
        'core', '_real_screen', '_safe_zone', '_scaling_mode',
        '_target_res', '_aspect_ratio', '_hdr_enabled', '_vsync',
        '_debug_overlay'
    )

    def __init__(self, core):
        self.core = core
        self._real_screen: Optional[pg.Surface] = None
        self._safe_zone: Optional[pg.Surface] = None
        self._scaling_mode: ScalingMode = ScalingMode.LETTERBOX
        self._target_res: Tuple[int, int] = (1920, 1080)  # Resolución lógica del juego
        self._aspect_ratio: float = 16 / 9
        self._hdr_enabled: bool = False
        self._vsync: bool = True
        self._debug_overlay: bool = False

        self._init_display()

    def _init_display(self):
        """Inicialización segura del subsistema gráfico"""
        try:
            # Detectar capacidades HDR
            display_info = pg.display.Info()
            self._hdr_enabled = self._check_hdr_support()

            flags = pg.HWSURFACE | pg.DOUBLEBUF | pg.OPENGL
            if self._vsync:
                flags |= pg.DOUBLEBUF  # VSync implícito en algunos sistemas

            if self._hdr_enabled:
                flags |= pg.HWPALETTE
                pg.display.gl_set_attribute(pg.GL_COLORSPACE, pg.GL_COLORSPACE_SCRGB)
                logger.info("HDR enabled")

            self._real_screen = pg.display.set_mode(
                (0, 0), 
                flags=flags | pg.FULLSCREEN,
                vsync=self._vsync
            )
            
            self._create_safe_zone()
            self._update_projection()
            
        except pg.error as e:
            logger.critical(f"Error inicializando display: {e}")
            self._fallback_to_windowed()

    def _check_hdr_support(self) -> bool:
        """Verifica soporte HDR/wide color gamut"""
        try:
            return pg.display.is_hdr_capable()
        except AttributeError:
            return False

    def _create_safe_zone(self):
        """Crea superficie de renderizado seguro con gestión de color"""
        self._safe_zone = pg.Surface(
            self._target_res, 
            flags=pg.SRCALPHA | (pg.HWSURFACE if self._hdr_enabled else 0)
        ).convert_alpha()

    def _fallback_to_windowed(self):
        """Modo de emergencia para sistemas problemáticos"""
        logger.warning("Falling back to windowed mode")
        self._real_screen = pg.display.set_mode(
            (1280, 720), 
            flags=pg.SHOWN
        )
        self._create_safe_zone()

    def set_resolution(self, width: int, height: int):
        """Cambia la resolución objetivo dinámicamente"""
        self._target_res = (width, height)
        self._aspect_ratio = width / height
        self._create_safe_zone()
        self._update_projection()

    def set_scaling_mode(self, mode: ScalingMode):
        """Configura el modo de escalado"""
        self._scaling_mode = mode
        self._update_projection()

    def _update_projection(self):
        """Actualiza matriz de proyección para renderizado escalado"""
        # Lógica para shaders/transformaciones de cámara
        pass

    def clear(self, color: Tuple[int, int, int] = (0, 0, 0)):
        """Limpia pantalla con color específico"""
        self._safe_zone.fill(color)

    def update(self):
        """Renderiza el contenido escalado en la pantalla real"""
        scaled_surface = self._apply_scaling()
        self._real_screen.blit(scaled_surface, self._calculate_position(scaled_surface))
        
        if self._debug_overlay:
            self._draw_debug_info()
            
        pg.display.flip()

    def _apply_scaling(self) -> pg.Surface:
        """Aplica el modo de escalado configurado"""
        target_size = self._real_screen.get_size()
        
        if self._scaling_mode == ScalingMode.STRETCH:
            return pg.transform.smoothscale(self._safe_zone, target_size)
            
        elif self._scaling_mode == ScalingMode.INTEGER_SCALE:
            scale = min(target_size[0] // self._target_res[0],
                        target_size[1] // self._target_res[1])
            return pg.transform.scale_by(self._safe_zone, scale)
            
        elif self._scaling_mode == ScalingMode.ASPECT_RATIO:
            ratio = min(target_size[0]/self._target_res[0],
                        target_size[1]/self._target_res[1])
            return pg.transform.smoothscale(self._safe_zone, 
                (int(self._target_res[0] * ratio), int(self._target_res[1] * ratio)))

        # Modo Letterbox por defecto
        ratio = min(target_size[0]/self._target_res[0],
                    target_size[1]/self._target_res[1])
        scaled_size = (int(self._target_res[0] * ratio), 
                       int(self._target_res[1] * ratio))
        return pg.transform.smoothscale(self._safe_zone, scaled_size)

    def _calculate_position(self, surface: pg.Surface) -> Tuple[int, int]:
        """Calcula posición para modos con barras"""
        if self._scaling_mode in (ScalingMode.LETTERBOX, ScalingMode.ASPECT_RATIO):
            return (
                (self._real_screen.get_width() - surface.get_width()) // 2,
                (self._real_screen.get_height() - surface.get_height()) // 2
            )
        return (0, 0)

    def _draw_debug_info(self):
        """Muestra información de depuración en pantalla"""
        debug_font = pg.font.SysFont('Arial', 20)
        info = [
            f"Resolución: {self._real_screen.get_size()}",
            f"Modo escalado: {self._scaling_mode.name}",
            f"FPS: {self.core.clock.get_fps():.1f}",
            f"HDR: {'Sí' if self._hdr_enabled else 'No'}"
        ]
        
        y_offset = 10
        for line in info:
            text_surf = debug_font.render(line, True, (255, 255, 255))
            self._real_screen.blit(text_surf, (10, y_offset))
            y_offset += 25

    @property
    def screen(self) -> pg.Surface:
        """Acceso seguro a la zona de renderizado seguro"""
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
        """Alterna la información de depuración"""
        self._debug_overlay = not self._debug_overlay

    def cleanup(self):
        """Libera recursos del display"""
        if self._safe_zone:
            self._safe_zone = None
        pg.display.quit()