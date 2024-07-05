from __future__ import annotations  # For union operator |

from enum import Enum

from common import *


class Services:
    TTS_SERVICE: Final[str] = 'tts'
    PLAYER_SERVICE: Final[str] = 'player'  # Generic player
    AUTO_ENGINE_ID: Final[str] = 'auto'
    CACHE_WRITER_ID: Final[str] = 'cache_writer'
    CACHE_READER_ID: Final[str] = 'cache_reader'
    INTERNAL_PLAYER_ID: Final[str] = 'internal'
    EXPERIMENTAL_ENGINE_ID: Final[str] = 'experimental'
    GOOGLE_ID: Final[str] = 'google'
    RESPONSIVE_VOICE_ID: Final[str] = 'ResponsiveVoice'
    FESTIVAL_ID: Final[str] = 'Festival'
    FLITE_ID: Final[str] = 'Flite'
    ESPEAK_ID: Final[str] = 'eSpeak'
    LOG_ONLY_ID: Final[str] = 'LogOnly'
    SPEECH_DISPATCHER_ID: Final[str] = 'Speech-Dispatcher'
    MPLAYER_ID: Final[str] = 'mplayer'
    MPV_ID: Final[str] = 'mpv'
    MPG123_ID: Final[str] = 'mpg123'
    MPG321_ID: Final[str] = 'mpg321'
    PICO_TO_WAVE_ID: Final[str] = 'pico2wave'
    PIPER_ID: Final[str] = 'piper'
    RECITE_ID: Final[str] = 'Recite'
    SAPI_ID: Final[str] = 'sapi'
    SERVICE_ID: Final[str] = 'id'  # Specifies the service's id (FLite is the current
    LAME_ID: Final[str] = 'lame'
    DEFAULT_ENGINE_ID: Final[str] = ESPEAK_ID

    # engine's id.

    WavAudioPlayerHandler = 'wave_handler'
    MP3AudioPlayerHandler = 'mp3_handler'
    BuiltInAudioPlayerHandler = 'internal_handler'
    NONE_ID: 'none'


class ServiceType(Enum):
    """
        Indicates which services are provided
    """
    ALL = 0
    # Produces Audio
    ENGINE = 1
    # Services are external to Kodi (ex. Speech Dispatcher)
    EXTERNAL_SERVICE = 2
    # Provides caching service
    CACHE_READER = 3
    CACHE_WRITER = 4
    # Converts audio formats
    CONVERTER = 5
    # Provides PIPE for services that can't
    PIPE_ADAPTER = 6
    # Plays Audio
    PLAYER = 7
    ENGINE_SETTINGS = 8
    INTERNAL_PLAYER = 9
    LAST_SERVICE_TYPE = 9
