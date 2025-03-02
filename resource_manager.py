import asyncio
from typing import Callable, List

class ResourceManager:
    """Manejador de recursos y callbacks para inicialización diferida"""
    def __init__(self):
        self._resource_callbacks: List[Callable] = []
        self.resources_loaded = asyncio.Event()

    def add_resource_callback(self, callback: Callable):
        """
        Registra un callback para ser ejecutado cuando los recursos estén listos.
        
        Args:
            callback (Callable): Función a ejecutar cuando los recursos se carguen.
        """
        if callable(callback):
            self._resource_callbacks.append(callback)
        else:
            raise TypeError("El callback debe ser una función o método invocable.")

    def execute_callbacks(self):
        """
        Ejecuta todos los callbacks registrados.
        Se llama cuando los recursos han sido cargados correctamente.
        """
        for callback in self._resource_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error ejecutando callback: {e}")

    def clear_callbacks(self):
        """Limpia todos los callbacks registrados."""
        self._resource_callbacks.clear()

    def are_resources_loaded(self) -> bool:
        """
        Verifica si los recursos han sido cargados.
        
        Returns:
            bool: True si los recursos están listos, False en caso contrario.
        """
        return self.resources_loaded.is_set()

    def set_resources_loaded(self):
        """Marca los recursos como cargados y notifica a los suscriptores."""
        self.resources_loaded.set()

    async def wait_for_resources(self):
        """Espera hasta que los recursos estén cargados."""
        await self.resources_loaded.wait()