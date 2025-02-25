import pygame as pg

class EventManager:
    """Manejador de eventos de entrada."""
    def __init__(self, core):
        self.core = core

    async def process_events(self):
        """Procesa los eventos de entrada."""
        events = await self.core.execution_engine.run_in_executor(self._fetch_events)
        for event in events:
            await self._process_single_event(event)

    def _fetch_events(self):
        """Obtiene los eventos de Pygame."""
        return list(pg.event.get())

    async def _process_single_event(self, event):
        """Procesa un evento individual."""
        if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
            await self.core.shutdown()
        elif event.type == pg.USEREVENT + 0:
            self.core.global_trigger = True
        await self.core.execution_engine.run_in_executor(
            self.core.player.handle_event, event
        )