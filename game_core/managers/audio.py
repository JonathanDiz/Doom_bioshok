from enum import Enum, auto
import pygame as pg
import asyncio
import logging
import math
from pathlib import Path
from typing import Dict, Optional, Tuple, Set, List
from collections import defaultdict
from ..utils.async_tools import AsyncLoader

class AudioCategory(Enum):
    SFX = auto()
    MUSIC = auto()
    AMBIENT = auto()
    UI = auto()

class SoundData:
    __slots__ = ('sound', 'volume', 'category', 'loops', 'max_distance', 'spatial')
    
    def __init__(self, sound: pg.mixer.Sound, category: AudioCategory, 
                 volume: float = 1.0, loops: int = 0, 
                 max_distance: float = 1000.0, spatial: bool = False):
        self.sound = sound
        self.category = category
        self.volume = volume
        self.loops = loops
        self.max_distance = max_distance
        self.spatial = spatial

class AudioManager:
    """Gestor de audio optimizado con soporte para spatial 3D avanzado y gestión dinámica de canales"""
    
    def __init__(self, core):
        self.core = core
        self._sounds: Dict[str, SoundData] = {}
        self._music: Optional[pg.mixer.music] = None
        self._channels: List[pg.mixer.Channel] = []
        self._channel_allocations: Dict[AudioCategory, Set[int]] = defaultdict(set)
        self._listener_pos: Tuple[float, float] = (0.0, 0.0)
        self._volume_settings = {
            'master': 1.0,
            AudioCategory.SFX: 0.8,
            AudioCategory.MUSIC: 0.7,
            AudioCategory.AMBIENT: 0.6,
            AudioCategory.UI: 1.0
        }
        self._init_audio_system()

    def _init_audio_system(self):
        """Configuración robusta del sistema de audio"""
        try:
            pg.mixer.init(
                frequency=48000,
                size=-32,
                channels=2,
                buffer=4096,
                allowedchanges=pg.AUDIO_ALLOW_FREQUENCY_CHANGE | pg.AUDIO_ALLOW_CHANNELS_CHANGE
            )
            self._allocate_channels(64)  # Total de canales
            logging.info(f"Audio system initialized with {pg.mixer.get_num_channels()} channels")
        except pg.error as e:
            logging.critical(f"Failed to initialize audio: {e}")
            self.core.resource_manager.audio_enabled = False

    def _allocate_channels(self, total_channels: int):
        """Distribución dinámica de canales por categoría"""
        self._channels = [pg.mixer.Channel(i) for i in range(total_channels)]
        allocations = {
            AudioCategory.SFX: int(total_channels * 0.5),
            AudioCategory.UI: int(total_channels * 0.2),
            AudioCategory.AMBIENT: int(total_channels * 0.2),
            AudioCategory.MUSIC: int(total_channels * 0.1)
        }
        
        index = 0
        for category, count in allocations.items():
            for _ in range(count):
                self._channel_allocations[category].add(index)
                index += 1

    async def load_sound(self, name: str, path: Path, category: AudioCategory, 
                       volume: float = 1.0, spatial: bool = False, 
                       max_distance: float = 1000.0):
        """Carga asíncrona optimizada con gestión de errores"""
        if not self.core.resource_manager.audio_enabled:
            return

        try:
            sound = await AsyncLoader().run_io_task(pg.mixer.Sound, path)
            self._sounds[name] = SoundData(
                sound=sound,
                category=category,
                volume=volume,
                spatial=spatial,
                max_distance=max_distance
            )
            logging.debug(f"Loaded sound: {name}")
        except (FileNotFoundError, pg.error) as e:
            logging.error(f"Error loading sound {name}: {e}")

    async def load_music(self, path: Path):
        """Carga de música con verificación de formatos"""
        if not self.core.resource_manager.audio_enabled:
            return

        try:
            await AsyncLoader().run_io_task(pg.mixer.music.load, path)
            self._update_music_volume()
        except pg.error as e:
            logging.error(f"Music load error: {e}")

    def play_sound(self, name: str, position: Optional[Tuple[float, float]] = None):
        """Reproducción optimizada con gestión espacial avanzada"""
        if name not in self._sounds:
            logging.warning(f"Sound {name} not found")
            return

        sound_data = self._sounds[name]
        channel = self._get_available_channel(sound_data.category)
        
        if not channel:
            logging.debug(f"No available channels for {name}")
            return

        if sound_data.spatial and position:
            self._apply_spatial_effects(channel, sound_data, position)
            
        final_volume = self._calculate_final_volume(sound_data)
        channel.set_volume(final_volume)
        channel.play(sound_data.sound, loops=sound_data.loops)

    def _apply_spatial_effects(self, channel: pg.mixer.Channel, 
                             sound_data: SoundData, position: Tuple[float, float]):
        """Cálculos espaciales precisos con atenuación logarítmica"""
        dx = position[0] - self._listener_pos[0]
        dy = position[1] - self._listener_pos[1]
        distance = math.hypot(dx, dy)
        
        # Atenuación no lineal para mayor realismo
        volume = math.pow(max(0, 1 - (distance / sound_data.max_distance)), 2)
        pan = dx / sound_data.max_distance  # Stereo positioning
        
        channel.set_volume(volume * self._volume_settings['master'])
        channel.set_pan(max(-1.0, min(1.0, pan)))

    def _calculate_final_volume(self, sound_data: SoundData) -> float:
        """Cálculo de volumen multi-nivel con clamping"""
        return max(0.0, min(1.0, 
            sound_data.volume * 
            self._volume_settings['master'] * 
            self._volume_settings[sound_data.category]
        ))

    def _get_available_channel(self, category: AudioCategory) -> Optional[pg.mixer.Channel]:
        """Obtención inteligente de canales con fallback"""
        # Primero intentar canales asignados
        for index in self._channel_allocations[category]:
            if not self._channels[index].get_busy():
                return self._channels[index]
        
        # Fallback a canales no utilizados de otras categorías
        for index, channel in enumerate(self._channels):
            if not channel.get_busy() and index not in self._channel_allocations[AudioCategory.UI]:
                return channel
        return None

    def set_listener_position(self, position: Tuple[float, float]):
        """Actualización de la posición del oyente con suavizado"""
        self._listener_pos = (
            self._listener_pos[0] * 0.3 + position[0] * 0.7,
            self._listener_pos[1] * 0.3 + position[1] * 0.7
        )

    def _update_music_volume(self):
        """Actualización sincronizada del volumen musical"""
        pg.mixer.music.set_volume(
            self._volume_settings['master'] * 
            self._volume_settings[AudioCategory.MUSIC]
        )

class MusicTrack:
    """Gestor avanzado de pistas musicales con transiciones fluidas"""
    
    def __init__(self, audio_manager: AudioManager):
        self.audio = audio_manager
        self.current_track: Optional[str] = None
        self.fade_duration: int = 2000  # ms
        self._transition_task: Optional[asyncio.Task] = None

    async def crossfade(self, new_track: str):
        """Transición suave entre pistas con cancelación segura"""
        if self._transition_task and not self._transition_task.done():
            self._transition_task.cancel()
            try:
                await self._transition_task
            except asyncio.CancelledError:
                pass

        self._transition_task = asyncio.create_task(self._perform_crossfade(new_track))

    async def _perform_crossfade(self, new_track: str):
        """Lógica interna de transición"""
        if self.current_track:
            await self.audio.fadeout_music(self.fade_duration)
        
        await self.audio.load_music(new_track)
        self.audio.play_music()
        self.current_track = new_track

    def update_volume(self):
        """Actualización reactiva del volumen"""
        self.audio._update_music_volume()