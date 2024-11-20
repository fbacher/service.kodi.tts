# coding=utf-8
from __future__ import annotations  # For union operator |
from enum import Enum
try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from common import *
from common.message_ids import MessageId


class Services(StrEnum):
    TTS_SERVICE = 'tts'
    PLAYER_SERVICE = 'player'  # Generic player
    AUTO_ENGINE_ID = 'auto'
    CACHE_WRITER_ID = 'cache_writer'
    CACHE_READER_ID = 'cache_reader'
    INTERNAL_PLAYER_ID = 'internal'
    EXPERIMENTAL_ENGINE_ID = 'experimental'
    GOOGLE_ID = 'google'
    RESPONSIVE_VOICE_ID = 'ResponsiveVoice'
    FESTIVAL_ID = 'Festival'
    FLITE_ID = 'Flite'
    ESPEAK_ID = 'eSpeak'
    LOG_ONLY_ID = 'LogOnly'
    SPEECH_DISPATCHER_ID = 'Speech-Dispatcher'
    MPLAYER_ID = 'mplayer'
    MPV_ID = 'mpv'
    MPG123_ID = 'mpg123'
    MPG321_ID = 'mpg321'
    NO_ENGINE_ID = 'no_engine'
    PICO_TO_WAVE_ID = 'pico2wave'
    PIPER_ID = 'piper'
    POWERSHELL_ID = 'powershell'
    RECITE_ID = 'Recite'
    SAPI_ID = 'sapi'
    SERVICE_ID = 'id'  # Specifies the service's id (FLite is the current
    SFX_ID = 'sfx'
    LAME_ID = 'lame'
    DEFAULT_ENGINE_ID = ESPEAK_ID

    # engine's id.

    WavAudioPlayerHandler = 'wave_handler'
    MP3AudioPlayerHandler = 'mp3_handler'
    BuiltInAudioPlayerHandler = 'internal_handler'
    NONE_ID: str = 'none'

    @property
    def translated_name(self) -> str:
        clz = type(self)
        msg_id_lookup: Dict[str, MessageId] = {
            # TTS :
            clz.AUTO_ENGINE_ID        : MessageId.ENGINE_AUTO,
            clz.ESPEAK_ID             : MessageId.ENGINE_ESPEAK,
            clz.FESTIVAL_ID           : MessageId.ENGINE_FESTIVAL,
            clz.FLITE_ID              : MessageId.ENGINE_FLITE,
            clz.EXPERIMENTAL_ENGINE_ID: MessageId.ENGINE_EXPERIMENTAL,
            clz.GOOGLE_ID             : MessageId.ENGINE_GOOGLE,
            clz.RECITE_ID             : MessageId.ENGINE_RECITE,
            clz.RESPONSIVE_VOICE_ID   : MessageId.ENGINE_RESPONSIVE_VOICE,
            clz.SAPI_ID               : MessageId.ENGINE_SAPI,
            clz.SPEECH_DISPATCHER_ID  : MessageId.ENGINE_SPEECH_DISPATCHER,
            clz.INTERNAL_PLAYER_ID    : MessageId.ENGINE_INTERNAL,
            clz.LOG_ONLY_ID           : MessageId.ENGINE_LOG_ONLY,
            clz.PICO_TO_WAVE_ID       : MessageId.CONVERT_PICO_TO_WAV,
            clz.PIPER_ID              : MessageId.ENGINE_PIPER,
        }
        msg: str = msg_id_lookup[self].get_msg()
        return msg


class TranscoderType(StrEnum):
    LAME = 'lame'
    MPLAYER = 'mencoder'
    FFMPEG = 'ffmpeg'


class WaveToMpg3Transcoder(StrEnum):
    LAME = TranscoderType.LAME.value
    MPLAYER = TranscoderType.MPLAYER.value
    FFMPEG = TranscoderType.FFMPEG.value


class Mpg3ToWaveTranscoder(StrEnum):
    LAME = TranscoderType.LAME.value
    # MPLAYER = TranscoderType.MPLAYER.value
    # FFMPEG = TranscoderType.FFMPEG.value


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
    TRANSCODER = 5
    # Provides PIPE for services that can't
    PIPE_ADAPTER = 6
    # Plays Audio
    PLAYER = 7
    ENGINE_SETTINGS = 8
    TTS = 9
    INTERNAL_PLAYER = 10
    LAST_SERVICE_TYPE = 10
