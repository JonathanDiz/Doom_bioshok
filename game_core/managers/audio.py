import math
import pygame as pg
import asyncio
import logging
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Optional, Tuple, Set, List
from collections import defaultdict
from ..utils.async_tools import AsyncLoader

logger = logging.getLogger(__name__)

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
    """Gestor avanzado de audio con soporte espacial 3D y gestión dinámica de canales"""
    
    __slots__ = (
        'core', '_sounds', '_music', '_channels', '_channel_allocations',
        '_listener_pos', '_volume_settings', '_music_volume'
    )

    def __init__(self, core):
        self.core = core
        self._sounds: Dict[str, SoundData] = {}
        self._music: Optional[str] = None
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
        self._music_volume: float = 1.0
        self._init_audio_system()

    def _init_audio_system(self):
        """Inicialización robusta del sistema de audio"""
        try:
            pg.mixer.init(
                frequency=48000,
                size=-32,
                channels=2,
                buffer=4096,
                allowedchanges=pg.AUDIO_ALLOW_FREQUENCY_CHANGE | pg.AUDIO_ALLOW_CHANNELS_CHANGE
            )
            self._allocate_channels(64)
            logger.info(f"Sistema de audio inicializado con {len(self._channels)} canales")
        except pg.error as e:
            logger.critical(f"Error al inicializar audio: {e}")
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
            self._channel_allocations[category].update(range(index, index + count))
            index += count

    async def load_sound(self, name: str, path: Path, category: AudioCategory,
                       volume: float = 1.0, spatial: bool = False,
                       max_distance: float = 1000.0):
        """Carga asíncrona de sonidos con gestión de errores"""
        if not self.core.resource_manager.audio_enabled:
            return

        try:
            sound = await AsyncLoader.run_io_task(pg.mixer.Sound, path)
            self._sounds[name] = SoundData(
                sound=sound,
                category=category,
                volume=volume,
                spatial=spatial,
                max_distance=max_distance
            )
            logger.debug(f"Sonido cargado: {name}")
        except (FileNotFoundError, pg.error) as e:
            logger.error(f"Error cargando sonido {name}: {e}")

    async def load_music(self, path: Path):
        """Carga de música con actualización de volumen"""
        if not self.core.resource_manager.audio_enabled:
            return

        try:
            await AsyncLoader.run_io_task(pg.mixer.music.load, path)
            self._update_music_volume()
        except pg.error as e:
            logger.error(f"Error cargando música: {e}")

    def play_music(self, loops: int = -1):
        """Reproduce la música cargada"""
        if self.core.resource_manager.audio_enabled:
            pg.mixer.music.play(loops)

    def play_sound(self, name: str, position: Optional[Tuple[float, float]] = None):
        """Reproduce un sonido con posicionamiento espacial opcional"""
        if name not in self._sounds:
            logger.warning(f"Sonido no encontrado: {name}")
            return

        sound_data = self._sounds[name]
        channel = self._get_available_channel(sound_data.category)
        
        if not channel:
            logger.debug("No hay canales disponibles")
            return

        if sound_data.spatial and position:
            self._apply_spatial_effects(channel, sound_data, position)
            
        final_volume = self._calculate_final_volume(sound_data)
        channel.set_volume(final_volume)
        channel.play(sound_data.sound, loops=sound_data.loops)

    def _apply_spatial_effects(self, channel: pg.mixer.Channel,
                             sound_data: SoundData, position: Tuple[float, float]):
        """Aplica efectos espaciales con atenuación logarítmica"""
        dx = position[0] - self._listener_pos[0]
        dy = position[1] - self._listener_pos[1]
        distance = math.hypot(dx, dy)
        
        # Atenuación no lineal y posicionamiento estéreo
        volume = math.pow(max(0, 1 - (distance / sound_data.max_distance)), 2)
        pan = max(-1.0, min(1.0, dx / sound_data.max_distance))
        
        channel.set_volume(volume * self._volume_settings['master'])
        channel.set_pan(pan)

    def _calculate_final_volume(self, sound_data: SoundData) -> float:
        """Calcula el volumen final con límites"""
        base_volume = sound_data.volume * self._volume_settings['master']
        category_volume = self._volume_settings[sound_data.category]
        return max(0.0, min(1.0, base_volume * category_volume))

    def _get_available_channel(self, category: AudioCategory) -> Optional[pg.mixer.Channel]:
        """Obtiene un canal disponible con sistema de fallback"""
        # Prioridad a canales asignados
        for index in self._channel_allocations[category]:
            if not self._channels[index].get_busy():
                return self._channels[index]
        
        # Fallback a canales no críticos
        for index, channel in enumerate(self._channels):
            if not channel.get_busy() and index not in self._channel_allocations[AudioCategory.UI]:
                return channel
        return None

    def set_listener_position(self, position: Tuple[float, float]):
        """Actualiza la posición del oyente con suavizado"""
        self._listener_pos = (
            self._listener_pos[0] * 0.3 + position[0] * 0.7,
            self._listener_pos[1] * 0.3 + position[1] * 0.7
        )

    def set_volume(self, category: AudioCategory, volume: float):
        """Configura volúmenes con actualización en tiempo real"""
        self._volume_settings[category] = max(0.0, min(1.0, volume))
        if category == AudioCategory.MUSIC:
            self._update_music_volume()

    def _update_music_volume(self):
        """Sincroniza el volumen de la música"""
        pg.mixer.music.set_volume(
            self._volume_settings['master'] * 
            self._volume_settings[AudioCategory.MUSIC]
        )

    def fadeout_music(self, duration: int = 2000):
        """Detiene la música con fadeout"""
        pg.mixer.music.fadeout(duration)

class MusicTrack:
    """Gestor de pistas musicales con transiciones fluidas"""
    
    __slots__ = ('audio', 'current_track', 'fade_duration', '_transition_task')
    
    def __init__(self, audio_manager: AudioManager):
        self.audio = audio_manager
        self.current_track: Optional[str] = None
        self.fade_duration: int = 2000  # ms
        self._transition_task: Optional[asyncio.Task] = None

    async def crossfade(self, new_track: str):
        """Transición suave entre pistas con gestión de tareas"""
        if self._transition_task and not self._transition_task.done():
            self._transition_task.cancel()
            try:
                await self._transition_task
            except asyncio.CancelledError:
                logger.debug("Transición anterior cancelada")

        self._transition_task = asyncio.create_task(self._perform_crossfade(new_track))

    async def _perform_crossfade(self, new_track: str):
        """Lógica interna de transición con fadeout/fadein"""
        if self.current_track:
            await self.audio.fadeout_music(self.fade_duration)
        
        await self.audio.load_music(new_track)
        self.audio.play_music()
        self.current_track = new_track

    def update_volume(self):
        """Actualiza el volumen según la configuración actual"""
        self.audio._update_music_volume()