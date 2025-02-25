import pygame as pg
import asyncio
import json
from pathlib import Path
from enum import Enum, auto
from collections import defaultdict
from typing import Dict, Tuple, Optional, Set

class InputType(Enum):
    KEYBOARD = auto()
    MOUSE = auto()
    GAMEPAD = auto()
    TOUCH = auto()

class InputAction(Enum):
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    JUMP = auto()
    ATTACK = auto()
    MENU = auto()

class InputManager:
    """Sistema avanzado de gestión de input con soporte para rebind y multi-dispositivo"""
    
    def __init__(self, core):
        self.core = core
        self._keybindings: Dict[InputAction, Set[Tuple[InputType, int]]] = defaultdict(set)
        self._input_state: Dict[Tuple[InputType, int], bool] = defaultdict(bool)
        self._last_input_state: Dict[Tuple[InputType, int], bool] = defaultdict(bool)
        self._gamepads: Dict[int, pg.joystick.Joystick] = {}
        self._deadzones = {'left_stick': 0.1, 'right_stick': 0.15, 'triggers': 0.05}
        self._input_context: str = 'gameplay'
        self._buffer = InputBuffer()
        self._mouse_pos = (0, 0)
        self._mouse_rel = (0, 0)
        self._config_loaded = False

    async def load_keybindings(self, profile: str = 'default'):
        """Carga asíncrona de configuraciones desde archivo"""
        config_path = Path(f'config/controls/{profile}.json')
        try:
            async with asyncio.to_thread(open, config_path, 'r') as f:
                data = json.loads(await f.read())
                await self._parse_bindings(data)
        except FileNotFoundError:
            await self._load_default_bindings()
        finally:
            self._config_loaded = True

    async def _parse_bindings(self, data: dict):
        """Procesa la configuración de controles"""
        for action, bindings in data.items():
            try:
                input_action = InputAction[action.upper()]
                for binding in bindings:
                    input_type = InputType[binding['type'].upper()]
                    code = self._get_input_code(input_type, binding['value'])
                    self._keybindings[input_action].add((input_type, code))
            except KeyError:
                continue

    def _get_input_code(self, input_type: InputType, value: str) -> int:
        """Convierte configuraciones a códigos de Pygame"""
        match input_type:
            case InputType.KEYBOARD:
                return getattr(pg, f'K_{value.lower()}')
            case InputType.MOUSE:
                return getattr(pg, f'BUTTON_{value.upper()}')
            case InputType.GAMEPAD:
                parts = value.split('_')
                return (getattr(pg, f'JOY{parts[0].upper()}'), 
                        getattr(pg, f'JOYBUTTON_{parts[1].upper()}'))
            case _:
                raise ValueError(f"Tipo de input no soportado: {input_type}")

    async def _load_default_bindings(self):
        """Carga bindings por defecto si no hay archivo"""
        default_bindings = {
            'MOVE_UP': [{'type': 'keyboard', 'value': 'w'}],
            'MOVE_DOWN': [{'type': 'keyboard', 'value': 's'}],
            'MOVE_LEFT': [{'type': 'keyboard', 'value': 'a'}],
            'MOVE_RIGHT': [{'type': 'keyboard', 'value': 'd'}],
            'JUMP': [{'type': 'keyboard', 'value': 'space'}],
            'ATTACK': [{'type': 'mouse', 'value': 'left'}]
        }
        await self._parse_bindings(default_bindings)

    def handle_event(self, event: pg.event.Event):
        """Procesa eventos de input y actualiza estados"""
        match event.type:
            case pg.KEYDOWN | pg.KEYUP:
                self._handle_keyboard(event)
            case pg.MOUSEBUTTONDOWN | pg.MOUSEBUTTONUP:
                self._handle_mouse_button(event)
            case pg.MOUSEMOTION:
                self._handle_mouse_motion(event)
            case pg.JOYDEVICEADDED:
                self._add_gamepad(event.device_index)
            case pg.JOYDEVICEREMOVED:
                self._remove_gamepad(event.instance_id)
            case pg.JOYBUTTONDOWN | pg.JOYBUTTONUP:
                self._handle_gamepad_button(event)
            case pg.JOYAXISMOTION:
                self._handle_gamepad_axis(event)

    def _handle_keyboard(self, event: pg.event.Event):
        key = event.key
        state = event.type == pg.KEYDOWN
        self._input_state[(InputType.KEYBOARD, key)] = state

    def _handle_mouse_button(self, event: pg.event.Event):
        button = event.button
        state = event.type == pg.MOUSEBUTTONDOWN
        self._input_state[(InputType.MOUSE, button)] = state

    def _handle_mouse_motion(self, event: pg.event.Event):
        self._mouse_pos = event.pos
        self._mouse_rel = event.rel

    def _add_gamepad(self, device_id: int):
        if device_id not in self._gamepads:
            joystick = pg.joystick.Joystick(device_id)
            joystick.init()
            self._gamepads[device_id] = joystick

    def _remove_gamepad(self, instance_id: int):
        for device_id, joystick in list(self._gamepads.items()):
            if joystick.get_instance_id() == instance_id:
                joystick.quit()
                del self._gamepads[device_id]

    def _handle_gamepad_button(self, event: pg.event.Event):
        device = event.instance_id
        button = event.button
        state = event.type == pg.JOYBUTTONDOWN
        self._input_state[(InputType.GAMEPAD, (device, button))] = state

    def _handle_gamepad_axis(self, event: pg.event.Event):
        device = event.instance_id
        axis = event.axis
        value = event.value
        # Implementar lógica para deadzones y conversión a digital

    def update(self):
        """Actualiza estados para el nuevo frame"""
        self._last_input_state = self._input_state.copy()
        self._buffer.update()
        self._mouse_rel = (0, 0)

    def get_action(self, action: InputAction) -> bool:
        """Verifica si una acción está siendo presionada"""
        return any(self._input_state[binding] for binding in self._keybindings[action])

    def get_action_down(self, action: InputAction) -> bool:
        """Verifica si una acción acaba de ser presionada"""
        return any(
            self._input_state[binding] and not self._last_input_state[binding]
            for binding in self._keybindings[action]
        )

    def get_action_up(self, action: InputAction) -> bool:
        """Verifica si una acción acaba de ser liberada"""
        return any(
            not self._input_state[binding] and self._last_input_state[binding]
            for binding in self._keybindings[action]
        )

    def get_mouse_position(self) -> Tuple[int, int]:
        """Devuelve la posición absoluta del mouse"""
        return self._mouse_pos

    def get_mouse_delta(self) -> Tuple[int, int]:
        """Devuelve el movimiento relativo del mouse"""
        return self._mouse_rel

    def set_input_context(self, context: str):
        """Cambia el contexto de input (ej: 'menu', 'gameplay')"""
        self._input_context = context
        self._buffer.clear()

class InputBuffer:
    """Sistema de buffer de inputs para técnicas como input leniency"""
    def __init__(self, buffer_time: float = 0.2):
        self._buffer: Dict[InputAction, float] = {}
        self._buffer_time = buffer_time

    def update(self):
        """Actualiza el buffer y elimina entradas expiradas"""
        current_time = pg.time.get_ticks() / 1000
        self._buffer = {
            action: timestamp
            for action, timestamp in self._buffer.items()
            if current_time - timestamp < self._buffer_time
        }

    def add_input(self, action: InputAction):
        """Añade una entrada al buffer"""
        self._buffer[action] = pg.time.get_ticks() / 1000

    def check_buffered(self, action: InputAction) -> bool:
        """Verifica si una acción está en el buffer"""
        return action in self._buffer

    def clear(self):
        """Limpia el buffer completamente"""
        self._buffer.clear()