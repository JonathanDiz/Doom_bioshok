import math
import pygame as pg
import asyncio
import json
import logging
from enum import Enum, auto
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional, Set, List

logger = logging.getLogger(__name__)

class InputType(Enum):
    KEYBOARD = auto()
    MOUSE = auto()
    GAMEPAD_BUTTON = auto()
    GAMEPAD_AXIS = auto()
    TOUCH = auto()

class InputAction(Enum):
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    JUMP = auto()
    ATTACK = auto()
    MENU = auto()

@dataclass
class InputEvent:
    action: InputAction
    strength: float = 1.0
    timestamp: float = 0.0

class InputManager:
    """Sistema avanzado de gestión de input con soporte multi-dispositivo y háptico"""
    
    __slots__ = (
        'core', '_keybindings', '_input_state', '_last_state',
        '_gamepads', '_deadzones', '_contexts', '_current_context',
        '_buffer', '_mouse_state', '_haptic_effects', '_touch_inputs'
    )

    def __init__(self, core):
        self.core = core
        self._keybindings: Dict[InputAction, Set[Tuple[InputType, int]]] = defaultdict(set)
        self._input_state: Dict[Tuple[InputType, int], float] = defaultdict(float)
        self._last_state: Dict[Tuple[InputType, int], float] = defaultdict(float)
        self._gamepads: Dict[int, pg.joystick.Joystick] = {}
        self._deadzones = {'left_stick': 0.15, 'right_stick': 0.15, 'triggers': 0.05}
        self._contexts: Dict[str, Set[InputAction]] = defaultdict(set)
        self._current_context: str = 'global'
        self._buffer = InputBuffer()
        self._mouse_state = {'pos': (0, 0), 'rel': (0, 0), 'buttons': [False]*5}
        self._haptic_effects: Dict[int, pg.haptic.Haptic] = {}
        self._touch_inputs: List[Dict] = []

    async def load_profile(self, profile: str = 'default'):
        """Carga asíncrona de configuración de controles"""
        config_path = Path(f'config/controls/{profile}.json')
        default_path = Path('config/controls/default.json')
        
        try:
            await self._load_config(config_path)
        except FileNotFoundError:
            logger.warning(f"Perfil {profile} no encontrado, cargando valores por defecto")
            await self._load_default_bindings()

    async def _load_config(self, path: Path):
        """Carga y procesa el archivo de configuración"""
        async with open(path, 'r') as f:
            data = json.loads(await f.read())
            await self._parse_bindings(data.get('bindings', {}))
            self._deadzones.update(data.get('deadzones', {}))
            self._contexts.update(data.get('contexts', {}))

    async def _parse_bindings(self, bindings: dict):
        """Procesamiento paralelo de bindings"""
        tasks = []
        for action, inputs in bindings.items():
            try:
                input_action = InputAction[action.upper()]
                tasks.append(self._process_binding(input_action, inputs))
            except KeyError:
                continue
        await asyncio.gather(*tasks)

    async def _process_binding(self, action: InputAction, inputs: list):
        """Procesa cada binding individualmente"""
        for entry in inputs:
            input_type = InputType[entry['type'].upper()]
            code = self._map_input_code(input_type, entry['value'])
            self._keybindings[action].add((input_type, code))

    def _map_input_code(self, input_type: InputType, value: str) -> int:
        """Mapea configuraciones a códigos de Pygame"""
        match input_type:
            case InputType.KEYBOARD:
                return getattr(pg, f'K_{value.upper()}')
            case InputType.MOUSE:
                return getattr(pg, f'BUTTON_{value.upper()}')
            case InputType.GAMEPAD_BUTTON:
                parts = value.split('_')
                return (int(parts[0]), getattr(pg, f'JOYBUTTON_{parts[1].upper()}'))
            case InputType.GAMEPAD_AXIS:
                parts = value.split('_')
                return (int(parts[0]), getattr(pg, f'JOYAXIS_{parts[1].upper()}'))
            case _:
                raise ValueError(f"Tipo de input no soportado: {input_type}")

    def handle_event(self, event: pg.event.Event):
        """Distribuidor de eventos con manejo específico"""
        handler = {
            pg.KEYDOWN: self._handle_key,
            pg.KEYUP: self._handle_key,
            pg.MOUSEBUTTONDOWN: self._handle_mouse_button,
            pg.MOUSEBUTTONUP: self._handle_mouse_button,
            pg.MOUSEMOTION: self._handle_mouse_motion,
            pg.JOYDEVICEADDED: self._handle_joystick_added,
            pg.JOYDEVICEREMOVED: self._handle_joystick_removed,
            pg.JOYBUTTONDOWN: self._handle_gamepad_button,
            pg.JOYBUTTONUP: self._handle_gamepad_button,
            pg.JOYAXISMOTION: self._handle_gamepad_axis,
            pg.FINGERDOWN: self._handle_touch,
            pg.FINGERUP: self._handle_touch,
            pg.FINGERMOTION: self._handle_touch
        }.get(event.type)
        
        if handler:
            handler(event)

    def _handle_key(self, event: pg.event.Event):
        """Procesa eventos de teclado"""
        state = 1.0 if event.type == pg.KEYDOWN else 0.0
        self._input_state[(InputType.KEYBOARD, event.key)] = state

    def _handle_mouse_button(self, event: pg.event.Event):
        """Actualiza estado de botones del mouse"""
        self._mouse_state['buttons'][event.button-1] = event.type == pg.MOUSEBUTTONDOWN

    def _handle_mouse_motion(self, event: pg.event.Event):
        """Actualiza posición y movimiento del mouse"""
        self._mouse_state['pos'] = event.pos
        self._mouse_state['rel'] = event.rel

    def _handle_joystick_added(self, event: pg.event.Event):
        """Configura nuevos gamepads con soporte háptico"""
        joystick = pg.joystick.Joystick(event.device_index)
        joystick.init()
        if joystick.get_init():
            self._gamepads[event.device_index] = joystick
            self._enable_haptic_feedback(joystick)

    def _enable_haptic_feedback(self, joystick: pg.joystick.Joystick):
        """Habilita efectos hápticos si está soportado"""
        if pg.version.SDL_VERSION >= (2, 0, 18) and joystick.get_numhats() > 0:
            try:
                haptic = pg.haptic.Haptic(joystick)
                haptic.init()
                effect = pg.haptic.HapticEffect(
                    type=pg.haptic.CONSTANT,
                    direction=pg.haptic.POLAR,
                    length=1000,
                    delay=0,
                    button=0,
                    attack_length=100,
                    attack_level=0,
                    fade_length=100,
                    fade_level=0,
                    magnitude=0x4000
                )
                haptic.upload_effect(effect)
                self._haptic_effects[joystick.get_instance_id()] = haptic
            except pg.error:
                logger.warning("Dispositivo no soporta háptica")

    def _handle_gamepad_button(self, event: pg.event.Event):
        """Procesa botones de gamepad"""
        state = 1.0 if event.type == pg.JOYBUTTONDOWN else 0.0
        key = (InputType.GAMEPAD_BUTTON, (event.instance_id, event.button))
        self._input_state[key] = state

    def _handle_gamepad_axis(self, event: pg.event.Event):
        """Procesa ejes analógicos con deadzone"""
        value = self._apply_deadzone(event.value, self._deadzones['left_stick'])
        key = (InputType.GAMEPAD_AXIS, (event.instance_id, event.axis))
        self._input_state[key] = value

    def _apply_deadzone(self, value: float, deadzone: float) -> float:
        """Aplica deadzone no lineal para mejor precisión"""
        abs_value = abs(value)
        if abs_value < deadzone:
            return 0.0
        return math.copysign((abs_value - deadzone) / (1 - deadzone), value)

    def _handle_touch(self, event: pg.event.Event):
        """Procesa eventos táctiles multi-punto"""
        touch = {
            'id': event.finger_id,
            'pos': (event.x * self.core.display.logical_resolution[0],
                    event.y * self.core.display.logical_resolution[1]),
            'pressure': event.pressure,
            'type': event.type
        }
        self._touch_inputs.append(touch)

    def update(self):
        """Actualiza estados y efectos para el nuevo frame"""
        self._last_state = self._input_state.copy()
        self._buffer.update()
        self._mouse_state['rel'] = (0, 0)
        self._touch_inputs.clear()

    def get_action(self, action: InputAction) -> float:
        """Obtiene intensidad del input (0.0 a 1.0)"""
        if not self._context_active(action):
            return 0.0
        return max(
            self._input_state[binding] 
            for binding in self._keybindings.get(action, [])
        )

    def get_action_down(self, action: InputAction) -> bool:
        """Verifica si la acción fue iniciada este frame"""
        return any(
            self._input_state[binding] > 0 and self._last_state.get(binding, 0) <= 0
            for binding in self._keybindings.get(action, [])
        )

    def set_context(self, context: str):
        """Cambia el contexto de input activo"""
        self._current_context = context
        self._buffer.clear()

    def _context_active(self, action: InputAction) -> bool:
        """Verifica si la acción está permitida en el contexto actual"""
        return action in self._contexts.get(self._current_context, set())

class InputBuffer:
    """Buffer de inputs para combos y técnicas avanzadas"""
    
    __slots__ = ('_events', '_max_duration')
    
    def __init__(self, max_duration: float = 0.2):
        self._events: deque[InputEvent] = deque(maxlen=10)
        self._max_duration = max_duration

    def update(self):
        """Elimina eventos expirados"""
        current_time = pg.time.get_ticks() / 1000
        self._events = deque(
            [e for e in self._events if current_time - e.timestamp <= self._max_duration],
            maxlen=10
        )

    def add(self, event: InputEvent):
        """Añade un nuevo evento con timestamp"""
        event.timestamp = pg.time.get_ticks() / 1000
        self._events.appendleft(event)

    def check(self, action: InputAction, window: float = 0.1) -> bool:
        """Verifica si la acción ocurrió en el periodo especificado"""
        current_time = pg.time.get_ticks() / 1000
        return any(
            e.action == action and (current_time - e.timestamp) <= window
            for e in self._events
        )

    def clear(self):
        """Limpia el buffer completamente"""
        self._events.clear()