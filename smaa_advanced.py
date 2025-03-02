import concurrent.futures
import asyncio
from multi_pass_smaa import MultiPassSMAA

class AdvancedSMAA(MultiPassSMAA):
    def __init__(self, screen, passes=2):
        super().__init__(screen, passes)
        
        # Configurar el sistema de threads
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.loop = asyncio.get_event_loop()

    async def apply_async(self):
        """Versión asíncrona para pygbag"""
        task = self.loop.run_in_executor(
            self.executor,
            self.execute_passes
        )
        await task

    def apply(self):
        """Versión síncrona"""
        self.execute_passes()