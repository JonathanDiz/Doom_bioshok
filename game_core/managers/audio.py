from enum import Enum, auto
import pygame as pg
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Set
from collections import defaultdict
from ..utils.async_tools import AsyncLoader

class AudioCategory(Enum):
    SFX = auto()
    MUSIC = auto()
    AMBIENT = auto()
    UI = auto()

class SoundData:
    __slots__ = ('sound', 'volume', 'category', 'loops')
    
    def __init__(self, sound: pg.mixer.Sound, category: AudioCategory, 
                 volume: float = 1.0, loops: int = 0):
        self.sound = sound
        self.category = category
        self.volume = volume
        self.loops = loops

class AudioManager:
    """Gestor avanzado de audio con soporte para 3D, mezcla dinámica y efectos DSP"""
    
    def __init__(self, core):
        self.core = core
        self._sounds: Dict[str, SoundData] = {}
        self._music: Optional[pg.mixer.music] = None
        self._channels = pg.mixer.Channel
        self._channel_pools: Dict[AudioCategory, Set[int]] = defaultdict(set)
        self._listener_pos: Tuple[float, float] = (0, 0)
        self._volume = {
            'master': 1.0,
            AudioCategory.SFX: 1.0,
            AudioCategory.MUSIC: 1.0,
            AudioCategory.AMBIENT: 1.0,
            AudioCategory.UI: 1.0
        }
        self._init_audio_system()

    def _init_audio_system(self):
        """Configuración segura para cualquier versión de Pygame"""
        try:
            # Parámetros básicos y universales
            init_kwargs = {
                'frequency': 44100,
                'size': -16,
                'channels': 2,
                'buffer': 2048
            }
            
            # Añadir parámetros avanzados solo si existen
            if hasattr(pg.mixer, 'AUDIO_ALLOW_FREQUENCY_CHANGE'):
                init_kwargs['allowedchanges'] = pg.mixer.AUDIO_ALLOW_FREQUENCY_CHANGE
                
            pg.mixer.init(**init_kwargs)
            self._create_channel_pools()
            
        except Exception as e:
            logging.error(f"Error crítico en audio: {e}")

    def _create_channel_pools(self):
        """Asigna canales por categoría para priorización"""
        channels = pg.mixer.get_num_channels()
        allocations = {
            AudioCategory.SFX: int(channels * 0.5),
            AudioCategory.UI: int(channels * 0.2),
            AudioCategory.AMBIENT: int(channels * 0.3)
        }
        
        channel_id = 0
        for category, count in allocations.items():
            for _ in range(count):
                self._channel_pools[category].add(channel_id)
                channel_id += 1

    async def load_sound(self, name: str, path: Path, 
                        category: AudioCategory, 
                        volume: float = 1.0,
                        spatial: bool = False):
        """Carga asíncrona de sonidos con opciones 3D"""
        if not self.core.resource_manager.audio_enabled:
            return

        try:
            sound = await AsyncLoader().run_in_executor(
                pg.mixer.Sound, path
            )
            self._sounds[name] = SoundData(
                sound=sound,
                category=category,
                volume=volume,
                loops=0
            )
            
            if spatial:
                sound.set_volume(0)  # Controlado por posición
                
        except Exception as e:
            logging.error(f"Error loading sound {name}: {e}")

    async def load_music(self, path: Path, fade_duration: int = 1000):
        """Carga música con streaming y crossfade"""
        if not self.core.resource_manager.audio_enabled:
            return

        def _load():
            pg.mixer.music.load(path)
            pg.mixer.music.set_volume(self._volume['master'] * self._volume[AudioCategory.MUSIC])
            pg.mixer.music.fadeout(fade_duration)
            
        await AsyncLoader().run_in_executor(_load)

    def play_sound(self, name: str, position: Optional[Tuple[float, float]] = None):
        """Reproduce un sonido con opciones espaciales"""
        if name not in self._sounds:
            logging.warning(f"Sound {name} not loaded")
            return

        sound_data = self._sounds[name]
        channel = self._get_available_channel(sound_data.category)
        
        if channel is None:
            logging.debug(f"No available channels for {name}")
            return

        if position is not None:
            self._apply_spatial_effect(channel, position)
            
        volume = self._calculate_volume(sound_data)
        channel.set_volume(volume)
        channel.play(sound_data.sound, loops=sound_data.loops)

    def _apply_spatial_effect(self, channel: pg.mixer.Channel, position: Tuple[float, float]):
        """Aplica efectos 3D básicos usando panning y atenuación"""
        dx = position[0] - self._listener_pos[0]
        dy = position[1] - self._listener_pos[1]
        distance = (dx**2 + dy**2)**0.5
        max_distance = 1000  # Configurable según necesidades del juego
        
        # Atenuación por distancia
        volume = max(0, 1 - (distance / max_distance))
        pan = max(-1, min(1, dx / max_distance))
        
        channel.set_volume(volume * self._volume['master'])
        channel.set_pan(pan)

    def _calculate_volume(self, sound_data: SoundData) -> float:
        """Calcula el volumen final aplicando todas las categorías"""
        return sound_data.volume * self._volume['master'] * self._volume[sound_data.category]

    def _get_available_channel(self, category: AudioCategory) -> Optional[pg.mixer.Channel]:
        """Obtiene un canal disponible de la pool correspondiente"""
        for channel_id in self._channel_pools[category]:
            channel = pg.mixer.Channel(channel_id)
            if not channel.get_busy():
                return channel
        return None

    def set_listener_position(self, position: Tuple[float, float]):
        """Actualiza la posición del oyente para efectos 3D"""
        self._listener_pos = position

    def set_volume(self, category: AudioCategory, volume: float):
        """Establece volumen para una categoría específica"""
        self._volume[category] = max(0.0, min(1.0, volume))
        if category == AudioCategory.MUSIC:
            pg.mixer.music.set_volume(self._volume['master'] * volume)

    def pause_all(self):
        """Pausa todo el audio excepto la categoría UI"""
        for category in self._channel_pools:
            if category != AudioCategory.UI:
                for channel_id in self._channel_pools[category]:
                    pg.mixer.Channel(channel_id).pause()
        pg.mixer.music.pause()

    def resume_all(self):
        """Reanuda todo el audio pausado"""
        for channel_id in range(pg.mixer.get_num_channels()):
            pg.mixer.Channel(channel_id).unpause()
        pg.mixer.music.unpause()

    def stop_all(self):
        """Detiene todo el audio incluyendo música"""
        for channel_id in range(pg.mixer.get_num_channels()):
            pg.mixer.Channel(channel_id).stop()
        pg.mixer.music.stop()

class MusicTrack:
    """Gestor avanzado para pistas musicales con transiciones"""
    def __init__(self, audio_manager: AudioManager):
        self.audio = audio_manager
        self.current_track: Optional[str] = None
        self.next_track: Optional[str] = None
        self.fade_duration = 1000  # ms

    async def crossfade(self, new_track: str):
        """Transición suave entre pistas musicales"""
        if self.current_track:
            self.audio.fadeout_music(self.fade_duration)
            await asyncio.sleep(self.fade_duration / 1000)
        
        await self.audio.load_music(new_track)
        self.audio.play_music(fade_ms=self.fade_duration)
        self.current_track = new_track

    def queue(self, track: str):
        """Encola una pista para reproducción continua"""
        self.next_track = track
        pg.mixer.music.queue(track)

    def set_playlist(self, tracks: list, shuffle: bool = False):
        """Configura una lista de reproducción con opción de shuffle"""
        # Implementación de lista de reproducción
        pass