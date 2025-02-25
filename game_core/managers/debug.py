import logging
import time
from contextlib import contextmanager

class DebugManager:
    """Monitorización en tiempo real sin overhead en release"""
    def __init__(self, core):
        self.core = core
        self._logger = logging.getLogger('GameCore')
        self._start_time: float = 0.0
        
    @contextmanager
    def track_performance(self, task_name: str):
        """Context manager para medir tiempos"""
        start = time.monotonic()
        try:
            yield
        finally:
            elapsed = time.monotonic() - start
            if elapsed > 0.1:
                self._logger.warning(f"Lentitud en {task_name}: {elapsed:.2f}s")
                
    def log_quickboot(self):
        """Registro de métricas de arranque"""
        self._logger.info(
            f"Arranque completado en {time.time() - self._start_time:.2f}s\n"
            f"Recursos cargados: {len(self.core.resource._cache)}"
        )