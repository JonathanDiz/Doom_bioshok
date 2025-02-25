import asyncio
from concurrent.futures import ThreadPoolExecutor

class ExecutionEngine:
    """Manejador del motor asíncrono y ejecución en segundo plano."""
    def __init__(self, core):
        self.core = core
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.loop = asyncio.get_event_loop()

    async def run_in_executor(self, func, *args):
        """Ejecuta una función en el executor."""
        return await self.loop.run_in_executor(self.executor, func, *args)

    def shutdown(self):
        """Apaga el executor."""
        self.executor.shutdown(wait=False)