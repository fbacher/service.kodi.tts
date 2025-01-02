# coding=utf-8
from __future__ import annotations  # For union operator |
from enum import Enum
try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from common import *
from common.message_ids import MessageId

# Support for running with NO ENGINE nor PLAYER using limited pre-generated
# cache. The intent is to provide enough TTS so the user can configure
# to use an engine and player.
GENERATE_BACKUP_SPEECH: bool = False


class Services(StrEnum):
    TTS_SERVICE = 'tts'
    AFPLAY_ID = 'afplay'
    APLAY_ID = 'aplay'
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
    MPG321_OE_PI_ID = 'mpg321_OE_Pi'
    NO_ENGINE_ID = 'no_engine'
    PAPLAY_ID = 'paplay'
    PICO_TO_WAVE_ID = 'pico2wave'
    PIPER_ID = 'piper'
    POWERSHELL_ID = 'powershell'
    RECITE_ID = 'Recite'
    SAPI_ID = 'sapi'
    SERVICE_ID = 'id'  # Specifies the service's id (FLite is the current
    SFX_ID = 'sfx'
    SOX_ID = 'sox'
    LAME_ID = 'lame'
    WINDOWS_ID = 'windows'
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


ALL_TRANSCODERS: List[TranscoderType] = list(TranscoderType)


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


class EngineType(StrEnum):
    AUTO_ENGINE = Services.AUTO_ENGINE_ID
    EXPERIMENTAL_ENGINE = Services.EXPERIMENTAL_ENGINE_ID
    GOOGLE = Services.GOOGLE_ID
    FESTIVAL = Services.FESTIVAL_ID
    FLITE = Services.FLITE_ID
    ESPEAK = Services.ESPEAK_ID
    LOG_ONLY = Services.LOG_ONLY_ID
    SPEECH_DISPATCHER = Services.SPEECH_DISPATCHER_ID
    NO_ENGINE = Services.NO_ENGINE_ID
    RECITE = Services.RECITE_ID
    # SAPI_ID = 'sapi'
    DEFAULT = Services.DEFAULT_ENGINE_ID


ALL_ENGINES: List[EngineType] = list(EngineType)


class PlayerType(StrEnum):
    NONE = Services.NONE_ID
    SFX = Services.SFX_ID  # Kodi built-in, WAVE
    WINDOWS = Services.WINDOWS_ID
    APLAY = Services.APLAY_ID
    PAPLAY = Services.PAPLAY_ID
    AFPLAY = Services.AFPLAY_ID
    SOX = Services.SOX_ID
    MPLAYER = Services.MPLAYER_ID
    MPV = Services.MPV_ID
    MPG321 = Services.MPG321_ID
    MPG123 = Services.MPG123_ID
    MPG321_OE_PI = Services.MPG321_OE_PI_ID

    # Engine's built-in player

    INTERNAL = Services.INTERNAL_PLAYER_ID

    @property
    def label(self) -> str:
        clz = PlayerType
        msg_id_lookup: Dict[str, MessageId] = {
            PlayerType.NONE        : MessageId.PLAYER_NONE,
            PlayerType.SFX         : MessageId.PLAYER_SFX,
            PlayerType.WINDOWS     : MessageId.PLAYER_WINDOWS,
            PlayerType.APLAY       : MessageId.PLAYER_APLAY,
            PlayerType.PAPLAY      : MessageId.PLAYER_PAPLAY,
            PlayerType.AFPLAY      : MessageId.PLAYER_AFPLAY,
            PlayerType.SOX         : MessageId.PLAYER_SOX,
            PlayerType.MPLAYER     : MessageId.PLAYER_MPLAYER,
            PlayerType.MPV         : MessageId.PLAYER_MPV,
            PlayerType.MPG321      : MessageId.PLAYER_MPG321,
            PlayerType.MPG123      : MessageId.PLAYER_MPG123,
            PlayerType.MPG321_OE_PI: MessageId.PLAYER_MPG321_OE_PI,
            PlayerType.INTERNAL    : MessageId.PLAYER_INTERNAL
        }
        msg: str = msg_id_lookup[self].get_msg()
        return msg


ALL_PLAYERS: List[StrEnum] = list(PlayerType)

SERVICES_BY_TYPE: Final[Dict[ServiceType, List[StrEnum]]] = {
    ServiceType.ENGINE: ALL_ENGINES,
    ServiceType.PLAYER: ALL_PLAYERS,
    ServiceType.TRANSCODER: ALL_TRANSCODERS
}
