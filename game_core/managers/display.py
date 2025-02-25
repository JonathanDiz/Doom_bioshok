import pygame as pg
import asyncio
from typing import Tuple, Optional, Dict
from pathlib import Path
from ..utils.async_tools import AsyncLoader

class DisplayManager:
    """Gestor avanzado de pantalla y renderizado con soporte multi-resolución"""
    
    def __init__(self, core):
        self.core = core
        self._init_display()
        self._window = None
        self._render_surface = None
        self._display_info = None
        self._vsync_enabled = False
        self._resolution = (1280, 720)
        self._scaling_mode = 'letterbox'
        self._shaders: Dict[str, any] = {}
        self._gl_context_created = False

    def _init_display(self):
        # Configura la pantalla usando self.core si es necesario
        self.core.screen = pg.display.set_mode((800, 600))

    async def initialize_async(self):
        """Inicialización asíncrona del subsistema de visualización"""
        await self._detect_display_info()
        await self._create_initial_window()
        await self._load_default_shaders()

    async def _detect_display_info(self):
        """Detecta capacidades del monitor en segundo plano"""
        await asyncio.sleep(0)  # Yield para el event loop
        self._display_info = {
            'modes': pg.display.list_modes(),
            'current': pg.display.Info(),
            'gl': {
                'version': pg.display.gl_get_attribute(pg.GL_CONTEXT_MAJOR_VERSION),
                'vendor': pg.display.gl_get_attribute(pg.GL_VENDOR)
            }
        }

    async def _create_initial_window(self):
        """Crea ventana inicial con configuración óptima"""
        best_mode = self._find_best_display_mode()
        flags = self._get_initial_flags()
        
        # Creación asíncrona del contexto GL
        await AsyncLoader().run_tasks([
            self._create_gl_context(best_mode, flags)
        ])
        
        self._apply_default_settings()

    def _find_best_display_mode(self) -> Tuple[int, int]:
        """Selecciona la mejor resolución compatible"""
        if not self._display_info['modes']:
            return self._resolution
        
        # Priorizar resoluciones 16:9
        for mode in reversed(self._display_info['modes']):
            if (mode[0]/mode[1]) >= 1.77:
                return mode
        return self._display_info['modes'][-1]

    def _get_initial_flags(self) -> int:
        """Genera flags iniciales para la ventana"""
        flags = pg.OPENGL | pg.DOUBLEBUF
        if self._display_info['current'].hw:
            flags |= pg.FULLSCREEN | pg.HWSURFACE
        return flags

    async def _create_gl_context(self, resolution: Tuple[int, int], flags: int):
        """Crea contexto GL de forma asíncrona"""
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 3)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)
        
        self._window = pg.display.set_mode(resolution, flags)
        self._gl_context_created = True

    def _apply_default_settings(self):
        """Configuración inicial de renderizado"""
        self.set_vsync(True)
        self.set_scaling_mode('letterbox')
        self.set_resolution(self._resolution)

    async def set_resolution(self, resolution: Tuple[int, int]):
        """Cambia resolución de renderizado con recálculo asíncrono"""
        if not self._gl_context_created:
            return
            
        self._resolution = resolution
        self._render_surface = pg.Surface(resolution, pg.SRCALPHA)
        
        # Recargar shaders si es necesario
        await self._reload_shaders()

    def set_vsync(self, enabled: bool):
        """Habilita/deshabilita VSync"""
        self._vsync_enabled = enabled
        pg.display.gl_set_attribute(pg.GL_SWAP_CONTROL, 1 if enabled else 0)

    def set_scaling_mode(self, mode: str):
        """Configura modo de escalado de pantalla"""
        valid_modes = ['stretch', 'letterbox', 'integer']
        self._scaling_mode = mode if mode in valid_modes else 'letterbox'

    async def _load_default_shaders(self):
        """Carga shaders básicos en segundo plano"""
        shader_path = Path('assets/shaders')
        await AsyncLoader().run_tasks([
            self._load_shader('basic', shader_path/'basic.vert', shader_path/'basic.frag'),
            self._load_shader('ui', shader_path/'ui.vert', shader_path/'ui.frag')
        ])

    async def _load_shader(self, name: str, vert_path: Path, frag_path: Path):
        """Carga y compila shaders GLSL de forma asíncrona"""
        if not self._gl_context_created:
            return

        # Implementación real usando OpenGL aquí
        # (Ejemplo simplificado para demostración)
        self._shaders[name] = {
            'vertex': vert_path.read_text(),
            'fragment': frag_path.read_text()
        }

    async def _reload_shaders(self):
        """Recarga shaders al cambiar resolución"""
        if self._shaders:
            await self._load_default_shaders()

    def begin_frame(self):
        """Prepara el frame para renderizado"""
        if self._render_surface:
            self._render_surface.fill((0, 0, 0, 0))

    def end_frame(self):
        """Finaliza y muestra el frame"""
        scaled_surface = self._apply_scaling(self._render_surface)
        self._window.blit(scaled_surface, (0, 0))
        pg.display.flip()

    def _apply_scaling(self, surface: pg.Surface) -> pg.Surface:
        """Aplica el modo de escalado configurado"""
        target_size = self._window.get_size()
        
        if self._scaling_mode == 'stretch':
            return pg.transform.smoothscale(surface, target_size)
            
        elif self._scaling_mode == 'integer':
            scale = min(target_size[0] // surface.get_width(),
                        target_size[1] // surface.get_height())
            scaled = pg.transform.scale_by(surface, scale)
            return scaled
            
        # Modo letterbox por defecto
        ratio = min(target_size[0]/surface.get_width(),
                    target_size[1]/surface.get_height())
        scaled_size = (int(surface.get_width() * ratio),
                        int(surface.get_height() * ratio))
        scaled = pg.transform.smoothscale(surface, scaled_size)
        final = pg.Surface(target_size, pg.SRCALPHA)
        final.blit(scaled, ((target_size[0] - scaled_size[0]) // 2,
                            (target_size[1] - scaled_size[1]) // 2))
        return final

    @property
    def current_resolution(self) -> Tuple[int, int]:
        """Devuelve la resolución activa de renderizado"""
        return self._resolution

    @property
    def window_size(self) -> Tuple[int, int]:
        """Tamaño real de la ventana"""
        return self._window.get_size() if self._window else (0, 0)