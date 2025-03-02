import pygame as pg
import asyncio
import logging
from enum import Enum, IntEnum, auto
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
        '_priority_queue', '_metrics', '_signal_handlers', '_filter_rules'
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

        self._register_core_events()

    def _register_core_events(self):
        """Registra manejadores para eventos críticos del sistema"""
        self.register_handler(EventType.SYSTEM, self._handle_system_events, EventPriority.CRITICAL)
        self.register_handler(EventType.INPUT, self._handle_input_events, EventPriority.HIGH)

    def register_handler(self, 
                       event_type: EventType, 
                       handler: Callable, 
                       priority: EventPriority = EventPriority.NORMAL):
        """Registra un nuevo manejador de eventos con prioridad"""
        self._event_handlers[event_type].append((handler, priority))

    def register_signal(self, signal: str, handler: Callable):
        """Registra un manejador para señales del sistema"""
        self._signal_handlers[signal].append(handler)

    def add_filter(self, event_type: EventType, condition: Callable):
        """Añade un filtro para eventos específicos"""
        self._filter_rules[event_type].append(condition)

    async def process_events(self):
        """Procesamiento principal de eventos con pipeline optimizado"""
        start_time = pg.time.get_ticks()
        
        # Fase 1: Recolección de eventos
        raw_events = await self._collect_events()
        
        # Fase 2: Clasificación y filtrado
        processed_events = await self._process_event_batch(raw_events)
        
        # Fase 3: Ejecución de manejadores
        await self._dispatch_events(processed_events)
        
        # Métricas
        self._metrics['process_time'] = pg.time.get_ticks() - start_time
        self._metrics['events_processed'] += len(processed_events)

    async def _collect_events(self) -> List[pg.event.Event]:
        """Recolección de eventos no bloqueante"""
        return await asyncio.get_event_loop().run_in_executor(
            self._executor,
            pg.event.get
        )

    async def _process_event_batch(self, events: List[pg.event.Event]) -> List[EventWrapper]:
        """Procesamiento paralelo de eventos con filtrado"""
        loop = asyncio.get_event_loop()
        tasks = []
        
        for event in events:
            task = loop.run_in_executor(
                self._executor,
                self._wrap_event,
                event
            )
            tasks.append(task)
            
        wrapped_events = await asyncio.gather(*tasks)
        return [e for e in wrapped_events if self._filter_event(e)]

    def _wrap_event(self, event: pg.event.Event) -> EventWrapper:
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
        if event.type == pg.QUIT:
            return EventType.SYSTEM
        elif event.type in (pg.KEYDOWN, pg.KEYUP, pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP):
            return EventType.INPUT
        elif event.type >= pg.USEREVENT:
            return EventType.CUSTOM
        return EventType.SYSTEM

    def _filter_event(self, event: EventWrapper) -> bool:
        """Aplica filtros registrados al evento"""
        for rule in self._filter_rules.get(event.type, []):
            if not rule(event):
                return False
        return True

    async def _dispatch_events(self, events: List[EventWrapper]):
        """Envía eventos a los manejadores correspondientes por prioridad"""
        for event in sorted(events, key=lambda e: e.priority):
            await self._execute_handlers(event)

    async def _execute_handlers(self, event: EventWrapper):
        """Ejecuta los manejadores para el evento"""
        handlers = self._event_handlers.get(event.type, [])
        for handler, priority in handlers:
            if priority <= event.priority:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        await asyncio.get_event_loop().run_in_executor(
                            self._executor,
                            handler,
                            event
                        )
                except Exception as e:
                    logger.error(f"Error en manejador de eventos: {e}")
                    self._emit_signal('event_error', {'event': event, 'error': e})

    def _handle_system_events(self, event: EventWrapper):
        """Manejador crítico para eventos del sistema"""
        if event.event.type == pg.QUIT:
            self._emit_signal('system_shutdown')
        elif event.event.type == pg.VIDEORESIZE:
            self._emit_signal('window_resize', event.event.size)

    def _handle_input_events(self, event: EventWrapper):
        """Manejador de alto rendimiento para entrada"""
        self.core.input_system.queue_event(event.event)

    def _emit_signal(self, signal: str, data: Optional[Any] = None):
        """Propaga señales del sistema a los suscriptores"""
        for handler in self._signal_handlers.get(signal, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error en manejador de señal {signal}: {e}")

    def get_metrics(self) -> Dict[str, float]:
        """Devuelve métricas de rendimiento del sistema"""
        return self._metrics.copy()

    def _get_event_priority(self, event_type: EventType, event: pg.event.Event) -> EventPriority:
        """Determina la prioridad del evento"""
        priorities = {
            EventType.SYSTEM: EventPriority.CRITICAL,
            EventType.INPUT: EventPriority.HIGH,
            EventType.NETWORK: EventPriority.NORMAL,
            EventType.CUSTOM: EventPriority.LOW
        }
        return priorities.get(event_type, EventPriority.NORMAL)

    def _get_event_source(self, event: pg.event.Event) -> Optional[str]:
        """Identifica la fuente del evento para depuración"""
        if event.type in (pg.KEYDOWN, pg.KEYUP):
            return 'keyboard'
        elif event.type in (pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP, pg.MOUSEMOTION):
            return 'mouse'
        elif event.type >= pg.USEREVENT:
            return 'custom'
        return None