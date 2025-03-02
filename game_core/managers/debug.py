import time
import logging
import platform
import traceback
import pygame as pg
from collections import deque
from typing import Any, Dict

class DebugManager:
    """Gestor avanzado de diagnóstico y profiling para el juego"""
    
    __slots__ = (
        'core', 'logger', 'metrics', '_fps_buffer',
        '_start_time', '_current_errors'
    )
    
    def __init__(self, core):
        self.core = core  # Referencia al núcleo del juego
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metrics = {
            'frame_times': deque(maxlen=60),
            'memory_usage': deque(maxlen=60)
        }
        self._fps_buffer = deque(maxlen=60)
        self._start_time = time.monotonic()
        self._current_errors = []
        
        self._log_system_info()
        
    def _log_system_info(self):
        """Registra información del sistema al inicializar"""
        sys_info = {
            'OS': platform.platform(),
            'Processor': platform.processor(),
            'Python': platform.python_version(),
            'Pygame': pg.version.ver,
            'SDL': pg.get_sdl_version()
        }
        
        self.logger.info("System Information:\n%s",
            '\n'.join(f"{k}: {v}" for k, v in sys_info.items())
        )
    
    def track_performance(self, metric_name: str, duration: float):
        """Registra métricas de rendimiento con precisión"""
        self.metrics['frame_times'].append(duration)
        if duration > 0.016:  # 60 FPS threshold
            self.logger.warning(f"Slow operation: {metric_name} took {duration:.4f}s")
    
    def log_error(self, context: str, error: Exception):
        """Registra errores con stack trace completo"""
        error_info = {
            'timestamp': time.time(),
            'context': context,
            'error_type': type(error).__name__,
            'message': str(error),
            'stack_trace': traceback.format_exc()
        }
        self._current_errors.append(error_info)
        self.logger.critical(
            f"CRITICAL ERROR in {context}",
            extra={'error_data': error_info}
        )
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Genera reporte de diagnóstico en tiempo real"""
        return {
            'fps': self.current_fps,
            'avg_frame_time': sum(self.metrics['frame_times']) / len(self.metrics['frame_times']) if self.metrics['frame_times'] else 0,
            'recent_errors': self._current_errors[-5:]
        }
    
    @property
    def current_fps(self) -> float:
        """Calcula los FPS actuales suavizados"""
        return len(self._fps_buffer) / sum(self._fps_buffer) if self._fps_buffer else 0

    def update_frame(self):
        """Debe llamarse cada frame para actualizar métricas"""
        frame_time = time.monotonic() - self._start_time
        self._fps_buffer.append(frame_time)
        self._start_time = time.monotonic()