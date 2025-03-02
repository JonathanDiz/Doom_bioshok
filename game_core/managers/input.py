import math
import pygame as pg
import asyncio
import json
import logging
from enum import Enum, auto
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional, Set, List
from dataclasses import dataclass

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
    """Sistema avanzado de input con soporte para múltiples dispositivos, perfiles y feedback háptico"""
    
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
        self._haptic_effects: Dict[int, HapticEffect] = {}
        self._touch_inputs: List[Dict] = []

    async def load_profile(self, profile: str = 'default'):
        """Carga asíncrona de configuraciones con fallback a valores por defecto"""
        config_path = Path(f'config/controls/{profile}.json')
        default_path = Path('config/controls/default.json')
        
        try:
            await self._load_config(config_path)
        except FileNotFoundError:
            logging.warning(f"Profile {profile} not found, loading defaults")
            await self._load_config(default_path)
        except json.JSONDecodeError as e:
            logging.error(f"Invalid config: {e}")
            await self._load_defaults()

    async def _load_config(self, path: Path):
        """Carga y analiza configuración con validación"""
        async with open(path, 'r') as f:
            data = json.loads(await f.read())
            await self._parse_bindings(data.get('bindings', {}))
            self._deadzones.update(data.get('deadzones', {}))
            self._contexts.update(data.get('contexts', {}))

    async def _parse_bindings(self, bindings: dict):
        """Procesamiento paralelo de bindings complejos"""
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
        """Mapeo avanzado de códigos de entrada"""
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
                raise ValueError(f"Unsupported input type: {input_type}")

    def handle_event(self, event: pg.event.Event):
        """Router de eventos con manejo específico por tipo"""
        handlers = {
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
        }
        
        if event.type in handlers:
            handlers[event.type](event)

    def _handle_key(self, event: pg.event.Event):
        """Procesamiento optimizado de teclado"""
        state = event.type == pg.KEYDOWN
        self._input_state[(InputType.KEYBOARD, event.key)] = 1.0 if state else 0.0

    def _handle_mouse_button(self, event: pg.event.Event):
        """Estado de botones del mouse con detección de presión"""
        self._mouse_state['buttons'][event.button-1] = event.type == pg.MOUSEBUTTONDOWN

    def _handle_mouse_motion(self, event: pg.event.Event):
        """Actualización de posición y delta del mouse"""
        self._mouse_state['pos'] = event.pos
        self._mouse_state['rel'] = event.rel

    def _handle_joystick_added(self, event: pg.event.Event):
        """Registro completo de gamepads con soporte háptico"""
        joystick = pg.joystick.Joystick(event.device_index)
        joystick.init()
        if joystick.get_init():
            self._gamepads[event.device_index] = joystick
            if joystick.get_numhats() > 0:
                self._enable_haptic(joystick)

    def _enable_haptic(self, joystick: pg.joystick.Joystick):
        """Configuración de efectos hápticos"""
        if joystick.get_numhats() > 0 and pg.version.SDL_VERSION >= (2,0,9):
            haptic_device = pg.haptic.SDL_HapticOpenFromJoystick(joystick)
            if haptic_device:
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
                    magnitude=0x4000,
                    envelope=pg.haptic.HAPTIC_ENVELOPE
                )
                self._haptic_effects[joystick.get_instance_id()] = effect

    def _handle_gamepad_button(self, event: pg.event.Event):
        """Estado de botones de gamepad"""
        state = event.type == pg.JOYBUTTONDOWN
        key = (InputType.GAMEPAD_BUTTON, (event.instance_id, event.button))
        self._input_state[key] = 1.0 if state else 0.0

    def _handle_gamepad_axis(self, event: pg.event.Event):
        """Procesamiento de ejes analógicos con deadzones"""
        axis = event.axis
        value = self._apply_deadzone(event.value, self._deadzones['left_stick'])
        key = (InputType.GAMEPAD_AXIS, (event.instance_id, axis))
        self._input_state[key] = value

    def _apply_deadzone(self, value: float, deadzone: float) -> float:
        """Aplicación no lineal de deadzone para mejor control"""
        abs_value = abs(value)
        if abs_value < deadzone:
            return 0.0
        return math.copysign((abs_value - deadzone) / (1 - deadzone), value)

    def _handle_touch(self, event: pg.event.Event):
        """Gestión de input táctil multi-point"""
        touch = {
            'id': event.finger_id,
            'pos': (event.x * self.core.display.window_size[0],
                    event.y * self.core.display.window_size[1]),
            'pressure': event.pressure,
            'type': event.type
        }
        self._touch_inputs.append(touch)

    def update(self):
        """Actualización de estados y efectos hápticos"""
        self._last_state = self._input_state.copy()
        self._buffer.update()
        self._mouse_state['rel'] = (0, 0)
        self._update_haptics()

    def _update_haptics(self):
        """Actualización de efectos hápticos activos"""
        for effect in list(self._haptic_effects.values()):
            if effect.get_status() == pg.HAPTIC_STOPPED:
                effect.destroy()
                del self._haptic_effects[effect.id]

    def get_action(self, action: InputAction) -> float:
        """Obtiene la intensidad del input (analógica o digital)"""
        if action not in self._keybindings or not self._context_active(action):
            return 0.0
        
        return max(
            self._input_state[binding] 
            for binding in self._keybindings[action]
            if binding in self._input_state
        )

    def get_action_down(self, action: InputAction) -> bool:
        """Detección precisa de presión inicial"""
        return any(
            self._input_state[binding] > 0 and self._last_state.get(binding, 0) <= 0
            for binding in self._keybindings[action]
            if self._context_active(action)
        )

    def set_context(self, context: str, inherit: bool = True):
        """Cambio de contexto con herencia opcional"""
        self._current_context = context
        self._buffer.set_active_actions(self._contexts.get(context, set()))

    def _context_active(self, action: InputAction) -> bool:
        """Verifica si la acción está permitida en el contexto actual"""
        return action in self._contexts.get(self._current_context, set())

class InputBuffer:
    """Buffer de inputs avanzado con soporte para prioridades y combos"""
    
    __slots__ = ('_buffer', '_max_time', '_priority')
    
    def __init__(self, buffer_time: float = 0.2, priority: List[InputAction] = None):
        self._buffer: deque[InputEvent] = deque(maxlen=10)
        self._max_time = buffer_time
        self._priority = priority or []

    def update(self):
        """Limpia entradas expiradas manteniendo el orden de prioridad"""
        current_time = pg.time.get_ticks() / 1000
        self._buffer = deque(
            [e for e in self._buffer if current_time - e.timestamp <= self._max_time],
            maxlen=10
        )

    def add(self, event: InputEvent):
        """Añade un evento con prioridad"""
        event.timestamp = pg.time.get_ticks() / 1000
        self._buffer.appendleft(event)
        self._buffer = deque(
            sorted(self._buffer, key=lambda x: self._priority.index(x.action)),
            maxlen=10
        )

    def check(self, action: InputAction, window: float = 0.1) -> bool:
        """Verifica si la acción ocurrió en el tiempo especificado"""
        current_time = pg.time.get_ticks() / 1000
        return any(
            e.action == action and (current_time - e.timestamp) <= window
            for e in self._buffer
        )

    def get_strength(self, action: InputAction) -> float:
        """Devuelve la intensidad máxima registrada para la acción"""
        return max(
            (e.strength for e in self._buffer if e.action == action),
            default=0.0
        )