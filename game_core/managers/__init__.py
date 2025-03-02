"""
Módulo principal para sistemas de gestión del juego

Exporta los componentes principales para un acceso simplificado:
from game_core.managers import InputManager, DisplayManager, ResourceManager
"""

from .input import InputManager
from .display import DisplayManager
from .resource import ResourceManager
from .debug import DebugManager

print("\nIniciando carga de managers...")

try:
    print("Intentando importar InputManager")
    from .input import InputManager
    print("InputManager importado correctamente")
    
    print("Intentando importar DebugManager")
    from .debug import DebugManager
    print("DebugManager importado correctamente")
    
except Exception as e:
    print("\nError durante importación:")
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensaje: {str(e)}")
    print("Traceback completo:")
    import traceback
    traceback.print_exc()

def initialize_core_managers(core) -> tuple:
    print("\nCreando instancias de managers...")
    try:
        input_mgr = InputManager(core)
        print("InputManager instanciado")
        
        debug_mgr = DebugManager(core)
        print("DebugManager instanciado")
        
        return (input_mgr, debug_mgr)
        
    except Exception as e:
        print("Error al crear instancias:")
        print(f"Tipo: {type(e).__name__}")
        print(f"Mensaje: {str(e)}")
        raise

__all__ = [
    'InputManager',
    'DisplayManager',
    'ResourceManager',
    'DebugManager',
    'initialize_core_managers'
]