import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Awaitable, Any

class AsyncLoader:
    """Ejecuta tareas en paralelo con control de workers"""
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers)
        
    async def run_tasks(self, tasks: List[Awaitable]):
        """Ejecuta lista de corrutinas en paralelo"""
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(self.executor, task)
            for task in tasks
        ]
        await asyncio.gather(*futures)

# Añade esta nueva función
async def run_parallel(*tasks: Awaitable[Any]) -> list:
    """
    Ejecuta múltiples tareas asíncronas en paralelo
    Ejemplo de uso:
    results = await run_parallel(task1(), task2(), task3())
    """
    return await asyncio.gather(*tasks)