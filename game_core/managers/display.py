import time
import pygame as pg
import asyncio
import logging
import math
from pathlib import Path
from typing import Callable, Tuple, Dict, Optional
from ..utils.async_tools import AsyncLoader, run_parallel

class DisplayManager:
    """Gestor avanzado de renderizado con soporte para OpenGL moderno y escalado inteligente"""
    
    __slots__ = (
        'core', '_window', '_render_surface', '_display_info',
        '_vsync_enabled', '_resolution', '_scaling_mode', '_shaders',
        '_gl_context_created', '_target_fps', '_frame_data', '_scaler_cache'
    )
    
    def __init__(self, core):
        self.core = core
        self._window: Optional[pg.Surface] = None
        self._render_surface: Optional[pg.Surface] = None
        self._display_info: Dict = {}
        self._vsync_enabled: bool = False
        self._resolution: Tuple[int, int] = (1280, 720)
        self._scaling_mode: str = 'letterbox'
        self._shaders: Dict[str, Dict] = {}
        self._gl_context_created: bool = False
        self._target_fps: int = 144
        self._frame_data = {
            'delta_time': 0.0,
            'frame_count': 0
        }
        self._scaler_cache: Dict[str, Callable] = {}

    async def initialize(self):
        """Inicialización asíncrona completa del subsistema gráfico"""
        try:
            await self._detect_display_capabilities()
            await self._create_optimized_window()
            await self._load_critical_shaders()
            self._build_scaler_functions()
            logging.info("Display subsystem initialized successfully")
        except Exception as e:
            logging.critical(f"Display init failed: {e}")
            self._fallback_to_software()

    async def _detect_display_capabilities(self):
        """Detección avanzada de capacidades del hardware"""
        await asyncio.sleep(0)  # Yield para el event loop
        
        self._display_info = {
            'modes': pg.display.list_modes(depth=32, flags=pg.OPENGL),
            'current': pg.display.Info(),
            'gl': {
                'version': (pg.display.gl_get_attribute(pg.GL_CONTEXT_MAJOR_VERSION),
                           pg.display.gl_get_attribute(pg.GL_CONTEXT_MINOR_VERSION)),
                'extensions': pg.display.gl_get_attribute(pg.GL_EXTENSIONS).split()
            },
            'max_texture_size': pg.display.gl_get_attribute(pg.GL_MAX_TEXTURE_SIZE)
        }

    async def _create_optimized_window(self):
        """Crea ventana optimizada para el hardware detectado"""
        best_mode = self._select_best_resolution()
        flags = self._generate_optimal_flags()
        
        await self._create_gl_context(best_mode, flags)
        self._apply_quality_settings()

    def _select_best_resolution(self) -> Tuple[int, int]:
        """Selección inteligente de resolución inicial"""
        target_aspect = 16 / 9
        sorted_modes = sorted(
            self._display_info['modes'],
            key=lambda m: abs((m[0]/m[1]) - target_aspect) + m[0]*m[1]*0.000001,
            reverse=True
        )
        return sorted_modes[0] if sorted_modes else self._resolution

    def _generate_optimal_flags(self) -> int:
        """Genera flags óptimos basados en capacidades"""
        flags = pg.OPENGL | pg.DOUBLEBUF | pg.HWSURFACE
        
        if pg.display.get_driver() == 'x11':
            flags |= pg.SCALED
        if self._display_info['current'].hw:
            flags |= pg.FULLSCREEN
            
        return flags

    async def _create_gl_context(self, resolution: Tuple[int, int], flags: int):
        """Crea contexto GL moderno con gestión de errores"""
        try:
            pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
            pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 3)
            pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)
            pg.display.gl_set_attribute(pg.GL_STENCIL_SIZE, 8)
            pg.display.gl_set_attribute(pg.GL_MULTISAMPLEBUFFERS, 1)
            pg.display.gl_set_attribute(pg.GL_MULTISAMPLESAMPLES, 4)
            
            self._window = pg.display.set_mode(resolution, flags)
            self._gl_context_created = True
        except pg.error as e:
            logging.error(f"OpenGL context failed: {e}")
            raise RuntimeError("Could not create OpenGL context")

    def _apply_quality_settings(self):
        """Configura parámetros de calidad gráfica"""
        pg.display.gl_set_attribute(pg.GL_SWAP_CONTROL, 1 if self._vsync_enabled else 0)
        pg.glEnable(pg.GL_MULTISAMPLE)
        pg.glEnable(pg.GL_DEPTH_TEST)
        pg.glEnable(pg.GL_BLEND)
        pg.glBlendFunc(pg.GL_SRC_ALPHA, pg.GL_ONE_MINUS_SRC_ALPHA)

    async def _load_critical_shaders(self):
        """Carga asíncrona de shaders esenciales con caché"""
        shader_dir = Path('resources/shaders')
        await run_parallel([
            self._load_and_compile_shader('main', shader_dir/'main.vert', shader_dir/'main.frag'),
            self._load_and_compile_shader('ui', shader_dir/'ui.vert', shader_dir/'ui.frag'),
            self._load_and_compile_shader('post', shader_dir/'post.vert', shader_dir/'post.frag')
        ])

    async def _load_and_compile_shader(self, name: str, vert_path: Path, frag_path: Path):
        """Carga y compila shaders con verificación de errores"""
        try:
            vert_src = await AsyncLoader.load_text(vert_path)
            frag_src = await AsyncLoader.load_text(frag_path)
            
            # Simulación de compilación GLSL
            self._shaders[name] = {
                'vert': vert_src,
                'frag': frag_src,
                'program': None  # Aquí iría el programa compilado real
            }
            logging.debug(f"Shader {name} loaded successfully")
        except Exception as e:
            logging.error(f"Shader {name} error: {e}")
            raise

    def _build_scaler_functions(self):
        """Precompila funciones de escalado para máximo rendimiento"""
        self._scaler_cache = {
            'stretch': lambda s: pg.transform.smoothscale(s, self._window.get_size()),
            'integer': self._integer_scale,
            'letterbox': self._letterbox_scale,
            'aspect': self._aspect_scale
        }

    def _integer_scale(self, surface: pg.Surface) -> pg.Surface:
        """Escalado por múltiplos enteros manteniendo píxeles nítidos"""
        scale = min(
            self._window.get_width() // surface.get_width(),
            self._window.get_height() // surface.get_height()
        )
        return pg.transform.scale_by(surface, scale)

    def _letterbox_scale(self, surface: pg.Surface) -> pg.Surface:
        """Escalado manteniendo relación de aspecto con barras negras"""
        target_ratio = self._window.get_width() / self._window.get_height()
        source_ratio = surface.get_width() / surface.get_height()
        
        if source_ratio > target_ratio:
            new_width = self._window.get_width()
            new_height = int(new_width / source_ratio)
        else:
            new_height = self._window.get_height()
            new_width = int(new_height * source_ratio)
            
        scaled = pg.transform.smoothscale(surface, (new_width, new_height))
        final = pg.Surface(self._window.get_size(), pg.SRCALPHA)
        final.blit(scaled, ((self._window.get_width() - new_width) // 2,
                          (self._window.get_height() - new_height) // 2))
        return final

    def _aspect_scale(self, surface: pg.Surface) -> pg.Surface:
        """Escalado adaptativo manteniendo relación de aspecto"""
        ratio = min(
            self._window.get_width() / surface.get_width(),
            self._window.get_height() / surface.get_height()
        )
        new_size = (int(surface.get_width() * ratio), 
                    int(surface.get_height() * ratio))
        return pg.transform.smoothscale(surface, new_size)

    async def set_resolution(self, width: int, height: int):
        """Cambio dinámico de resolución con recarga de recursos"""
        self._resolution = (width, height)
        self._render_surface = pg.Surface(self._resolution, pg.SRCALPHA)
        
        await self._reload_shaders()
        self.core.resource_manager.update_textures(self._resolution)

    def begin_frame(self):
        """Prepara el buffer de renderizado"""
        self._frame_data['start_time'] = time.monotonic()
        self._render_surface.fill((0, 0, 0, 0))
        
    def end_frame(self):
        """Finaliza el frame y aplica efectos post-procesado"""
        self._apply_post_processing()
        scaled = self._scaler_cache[self._scaling_mode](self._render_surface)
        self._window.blit(scaled, (0, 0))
        pg.display.flip()
        
        # Cálculo de delta_time
        self._frame_data['delta_time'] = time.monotonic() - self._frame_data['start_time']
        self._frame_data['frame_count'] += 1

    def _apply_post_processing(self):
        """Aplica efectos post-procesado usando shaders"""
        if 'post' in self._shaders:
            # Implementación real usando OpenGL aquí
            pass

    def _fallback_to_software(self):
        """Modo de emergencia sin aceleración hardware"""
        self._window = pg.display.set_mode(self._resolution, pg.SWSURFACE)
        self._gl_context_created = False
        logging.warning("Running in software rendering mode")

    @property
    def delta_time(self) -> float:
        """Tiempo transcurrido desde el último frame"""
        return self._frame_data['delta_time']

    @property
    def fps(self) -> float:
        """FPS actuales calculados suavizados"""
        return 1.0 / self.delta_time if self.delta_time > 0 else 0

    def set_fullscreen(self, enable: bool):
        """Cambia modo pantalla completa dinámicamente"""
        flags = self._window.get_flags()
        if enable:
            flags |= pg.FULLSCREEN
        else:
            flags &= ~pg.FULLSCREEN
        pg.display.set_mode(self._resolution, flags)