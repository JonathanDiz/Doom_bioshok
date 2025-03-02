import time
import logging
import platform
import traceback
import pygame as pg
from collections import deque
from typing import Any, Dict, List
from contextlib import contextmanager

class DebugManager:
    """Sistema avanzado de diagnóstico y profiling para el motor del juego"""
    
    __slots__ = (
        'core', 'logger', 'metrics', '_fps_buffer',
        '_start_time', '_current_errors', '_perf_stack'
    )
    
    def __init__(self, core):
        self.core = core
        self.logger = logging.getLogger('GameDebug')
        self.metrics = {
            'frame_times': deque(maxlen=300),  # 5 segundos a 60 FPS
            'memory_usage': deque(maxlen=60),
            'custom': {}
        }
        self._fps_buffer = deque(maxlen=60)
        self._start_time = time.monotonic()
        self._current_errors: List[Dict] = []
        self._perf_stack = []

        self._log_system_info()
        
    def _log_system_info(self):
        """Registra información detallada del sistema al inicializar"""
        sys_info = [
            f"Sistema Operativo: {platform.platform()}",
            f"Procesador: {platform.processor() or 'Desconocido'}",
            f"Versión Python: {platform.python_version()}",
            f"Versión Pygame: {pg.version.ver}",
            f"Versión SDL: {'.'.join(map(str, pg.get_sdl_version()))}"
        ]
        
        self.logger.info("Información del sistema:\n%s", '\n'.join(sys_info))
    
    @contextmanager
    def track_performance(self, metric_name: str):
        """Context manager para medición precisa de rendimiento"""
        start_time = time.monotonic()
        self._perf_stack.append(metric_name)
        try:
            yield
        finally:
            duration = time.monotonic() - start_time
            self._perf_stack.pop()
            self._record_performance(metric_name, duration)
    
    def _record_performance(self, name: str, duration: float):
        """Registra métricas de rendimiento con análisis de bottlenecks"""
        self.metrics['frame_times'].append(duration)
        
        # Umbrales de advertencia dinámicos
        warning_threshold = 1.0 / self.core.display.target_fps * 1.5
        if duration > warning_threshold:
            context = ' > '.join(self._perf_stack)
            self.logger.warning(
                f"Lentitud en {name} ({context}): {duration*1000:.1f}ms"
            )
    
    def log_error(self, context: str, error: Exception):
        """Registra errores con información estructurada para debugging"""
        error_info = {
            'timestamp': time.time(),
            'context': context,
            'type': error.__class__.__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'game_state': self._capture_game_state()
        }
        self._current_errors.append(error_info)
        self.logger.critical(
            f"Error crítico en {context}: {error}",
            extra={'debug_info': error_info}
        )
    
    def _capture_game_state(self) -> Dict[str, Any]:
        """Captura estado relevante del juego para diagnóstico"""
        return {
            'fps': self.current_fps,
            'scene': getattr(self.core, 'current_scene', 'Desconocido'),
            'entities': len(getattr(self.core, 'entities', [])),
            'resolution': self.core.display.logical_resolution
        }
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Genera reporte de diagnóstico en tiempo real"""
        frame_times = self.metrics['frame_times']
        return {
            'fps': self.current_fps,
            'frame_time': {
                'current': frame_times[-1] if frame_times else 0,
                'avg': sum(frame_times)/len(frame_times) if frame_times else 0,
                'max': max(frame_times, default=0)
            },
            'recent_errors': self._current_errors[-3:],
            'memory': {
                'texturas': len(self.core.resource_manager._cache),
                'entidades_activas': self._count_active_entities()
            }
        }
    
    def _count_active_entities(self) -> int:
        """Helper para contar entidades activas"""
        return sum(1 for e in getattr(self.core, 'entities', []) if e.active)
    
    def update_frame_metrics(self):
        """Actualiza métricas de frame, debe llamarse una vez por frame"""
        frame_time = time.monotonic() - self._start_time
        self._fps_buffer.append(frame_time)
        self._start_time = time.monotonic()
    
    @property
    def current_fps(self) -> float:
        """Calcula FPS suavizados con media móvil"""
        if not self._fps_buffer:
            return 0.0
        return len(self._fps_buffer) / sum(self._fps_buffer)
    
    def reset_metrics(self):
        """Reinicia todas las métricas de rendimiento"""
        self.metrics['frame_times'].clear()
        self._fps_buffer.clear()
        self._current_errors.clear()