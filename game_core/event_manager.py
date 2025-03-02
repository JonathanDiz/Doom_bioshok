from functools import partial
import pygame as pg
import asyncio
import logging
from enum import IntEnum, auto
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class EventType(IntEnum):
    SYSTEM = auto()
    INPUT = auto()
    CUSTOM = auto()
    NETWORK = auto()
    DEBUG = auto()

class EventPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

@dataclass
class EventWrapper:
    event: pg.event.Event
    type: EventType
    priority: EventPriority
    timestamp: float
    source: Optional[Any] = None

class EventManager:
    """Sistema avanzado de gestión de eventos con prioridades, filtrado y métricas"""
    
    __slots__ = (
        'core', '_executor', '_event_handlers', '_event_queue',
        '_priority_queue', '_metrics', '_signal_handlers', '_filter_rules',
        '_lock'
    )

    def __init__(self, core):
        self.core = core
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._event_queue: List[EventWrapper] = []
        self._priority_queue: Dict[EventPriority, List[EventWrapper]] = defaultdict(list)
        self._metrics: Dict[str, float] = defaultdict(float)
        self._signal_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._filter_rules: Dict[EventType, List[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()

        self._register_core_events()
        self._setup_core_handlers()

    def _register_core_events(self):
        """Registra manejadores para eventos críticos del sistema"""
        self.register_handler(EventType.SYSTEM, self._handle_system_events, EventPriority.CRITICAL)
        self.register_handler(EventType.INPUT, self._handle_input_events, EventPriority.HIGH)
        self.register_handler(EventType.CUSTOM, self._handle_custom_events, EventPriority.NORMAL)

    def _setup_core_handlers(self):
        """Configura manejadores esenciales del sistema"""
        self.register_signal('system_shutdown', self.core.shutdown)
        self.register_signal('event_error', self._log_event_error)

    async def register_handler(
        self, 
        event_type: EventType, 
        handler: Callable, 
        priority: EventPriority = EventPriority.NORMAL
    ):
        """Registra un nuevo manejador de eventos con prioridad"""
        async with self._lock:
            self._event_handlers[event_type].append((handler, priority))

    async def register_signal(self, signal: str, handler: Callable):
        """Registra un manejador para señales del sistema"""
        async with self._lock:
            self._signal_handlers[signal].append(handler)

    async def add_filter(self, event_type: EventType, condition: Callable):
        """Añade un filtro para eventos específicos"""
        async with self._lock:
            self._filter_rules[event_type].append(condition)

    async def process_events(self):
        """Procesamiento principal de eventos con pipeline optimizado"""
        start_time = pg.time.get_ticks()
        
        async with self._lock:
            raw_events = await self._collect_events()
            processed_events = await self._process_event_batch(raw_events)
            await self._dispatch_events(processed_events)
            
            # Actualización de métricas
            self._metrics['process_time'] = pg.time.get_ticks() - start_time
            self._metrics['events_processed'] += len(processed_events)
            self._metrics['queue_size'] = len(self._event_queue)

    async def _collect_events(self) -> List[pg.event.Event]:
        """Recolección de eventos no bloqueante"""
        return await asyncio.get_event_loop().run_in_executor(
            self._executor,
            pg.event.get
        )

    async def _process_event_batch(self, events: List[pg.event.Event]) -> List[EventWrapper]:
        """Procesamiento paralelo de eventos con filtrado"""
        tasks = [self._wrap_event(event) for event in events]
        wrapped_events = await asyncio.gather(*tasks)
        return [e for e in wrapped_events if await self._filter_event(e)]

    async def _wrap_event(self, event: pg.event.Event) -> EventWrapper:
        """Clasificación inicial de eventos"""
        event_type = self._determine_event_type(event)
        return EventWrapper(
            event=event,
            type=event_type,
            priority=self._get_event_priority(event_type, event),
            timestamp=pg.time.get_ticks(),
            source=self._get_event_source(event)
        )

    def _determine_event_type(self, event: pg.event.Event) -> EventType:
        """Determina el tipo de evento basado en su naturaleza"""
        match event.type:
            case pg.QUIT | pg.VIDEORESIZE:
                return EventType.SYSTEM
            case pg.KEYDOWN | pg.KEYUP | pg.MOUSEBUTTONDOWN | pg.MOUSEBUTTONUP | pg.MOUSEMOTION:
                return EventType.INPUT
            case _ if event.type >= pg.USEREVENT:
                return EventType.CUSTOM
            case _:
                return EventType.SYSTEM

    async def _filter_event(self, event: EventWrapper) -> bool:
        """Aplica filtros registrados al evento"""
        for rule in self._filter_rules.get(event.type, []):
            if not await self._execute_filter_rule(rule, event):
                return False
        return True

    async def _execute_filter_rule(self, rule: Callable, event: EventWrapper) -> bool:
        """Ejecuta una regla de filtrado con manejo de errores"""
        try:
            return rule(event)
        except Exception as e:
            logger.error(f"Error en filtro de eventos: {str(e)}")
            self._emit_signal('event_error', {'event': event, 'error': e})
            return False

    async def _dispatch_events(self, events: List[EventWrapper]):
        """Envía eventos a los manejadores correspondientes por prioridad"""
        dispatch_tasks = [self._execute_handlers(event) for event in sorted(
            events, 
            key=lambda e: e.priority
        )]
        await asyncio.gather(*dispatch_tasks)

    async def _execute_handlers(self, event: EventWrapper):
        """Ejecuta los manejadores para el evento"""
        handlers = self._event_handlers.get(event.type, [])
        for handler, priority in handlers:
            if priority <= event.priority:
                await self._run_handler(handler, event)

    async def _run_handler(self, handler: Callable, event: EventWrapper):
        """Ejecuta un manejador individual con gestión de errores"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    partial(handler, event)
                )
        except Exception as e:
            logger.error(f"Error en manejador de eventos: {str(e)}")
            self._emit_signal('event_error', {'event': event, 'error': e})

    def _handle_system_events(self, event: EventWrapper):
        """Manejador crítico para eventos del sistema"""
        match event.event.type:
            case pg.QUIT:
                self._emit_signal('system_shutdown')
            case pg.KEYDOWN if event.event.key == pg.K_ESCAPE:
                self._emit_signal('system_shutdown')
            case pg.VIDEORESIZE:
                self._emit_signal('window_resize', event.event.size)

    def _handle_input_events(self, event: EventWrapper):
        """Manejador de alto rendimiento para entrada"""
        self.core.input_system.queue_event(event.event)
        asyncio.create_task(
            self.core.execution_engine.run_in_executor(
                self.core.player.handle_event,
                event.event
            )
        )

    def _handle_custom_events(self, event: EventWrapper):
        """Manejador para eventos personalizados"""
        if event.event.type == pg.USEREVENT + 0:
            self.core.global_trigger = True

    def _emit_signal(self, signal: str, data: Optional[Any] = None):
        """Propaga señales del sistema a los suscriptores"""
        for handler in self._signal_handlers.get(signal, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(data))
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error en manejador de señal {signal}: {str(e)}")

    def get_metrics(self) -> Dict[str, float]:
        """Devuelve métricas de rendimiento del sistema"""
        return self._metrics.copy()

    def _get_event_priority(self, event_type: EventType, event: pg.event.Event) -> EventPriority:
        """Determina la prioridad del evento"""
        priority_map = {
            EventType.SYSTEM: EventPriority.CRITICAL,
            EventType.INPUT: EventPriority.HIGH,
            EventType.NETWORK: EventPriority.NORMAL,
            EventType.CUSTOM: EventPriority.LOW
        }
        return priority_map.get(event_type, EventPriority.NORMAL)

    def _get_event_source(self, event: pg.event.Event) -> Optional[str]:
        """Identifica la fuente del evento para depuración"""
        source_map = {
            pg.KEYDOWN: 'keyboard',
            pg.KEYUP: 'keyboard',
            pg.MOUSEBUTTONDOWN: 'mouse',
            pg.MOUSEBUTTONUP: 'mouse',
            pg.MOUSEMOTION: 'mouse'
        }
        return source_map.get(event.type, 
            'custom' if event.type >= pg.USEREVENT else None)

    def _log_event_error(self, data: Dict[str, Any]):
        """Registro centralizado de errores de eventos"""
        logger.error(
            "Error en evento %s: %s",
            data['event'].type.name,
            str(data['error']),
            exc_info=True
        )

    async def shutdown(self):
        """Apagado seguro del sistema de eventos"""
        await self._executor.shutdown(wait=True)
        async with self._lock:
            self._event_handlers.clear()
            self._signal_handlers.clear()
            self._filter_rules.clear()
            self._event_queue.clear()