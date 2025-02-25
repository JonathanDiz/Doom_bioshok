import asyncio

class ResourceManager:
    """Gestor de recursos vinculado al GameCore"""
    def __init__(self, game_core):
        self.game_core = game_core  # Referencia obligatoria
        self.resources_loaded = asyncio.Event()
        
    async def load_resources(self):
        """Carga simulada de recursos"""
        await asyncio.sleep(0.1)  # Simula operación asíncrona
        self.resources_loaded.set()
        print("Recursos cargados exitosamente!")