# coding=utf-8
from __future__ import annotations  # For union operator |

from common.logger import BasicLogger
from enum import Enum
try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from common import *
from common.message_ids import MessageId

# Support for running with NO ENGINE nor PLAYER using limited pre-generated
# cache. The intent is to provide enough TTS so the user can cfg
# to use an engine and player_key.
GENERATE_BACKUP_SPEECH: bool = False
MY_LOGGER = BasicLogger.get_logger(__name__)


class Services(StrEnum):
    TTS_SERVICE = 'tts'
    AFPLAY_ID = 'afplay'
    APLAY_ID = 'aplay'
    PLAYER_SERVICE = 'player'  # Generic player_key
    CURRENT_ENGINE_ID = 'current_engine'
    #  AUTO_ENGINE_ID = 'auto'
    CACHE_WRITER_ID = 'cache_writer'
    CACHE_READER_ID = 'cache_reader'
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

    # player's id.

    WavAudioPlayerHandler = 'wave_handler'
    MP3AudioPlayerHandler = 'mp3_handler'
    BuiltInAudioPlayerHandler = 'internal_handler'
    BUILT_IN_PLAYER_ID: str = 'built_in_player'

    @property
    def translated_name(self) -> str:
        clz = type(self)
        msg_id_lookup: Dict[str, MessageId] = {
            # TTS :
            #  clz.AUTO_ENGINE_ID        : MessageId.ENGINE_AUTO,
            clz.ESPEAK_ID             : MessageId.ENGINE_ESPEAK,
            clz.FESTIVAL_ID           : MessageId.ENGINE_FESTIVAL,
            clz.FLITE_ID              : MessageId.ENGINE_FLITE,
            clz.EXPERIMENTAL_ENGINE_ID: MessageId.ENGINE_EXPERIMENTAL,
            clz.GOOGLE_ID             : MessageId.ENGINE_GOOGLE,
            clz.POWERSHELL_ID         : MessageId.ENGINE_POWERSHELL,
            clz.RECITE_ID             : MessageId.ENGINE_RECITE,
            clz.RESPONSIVE_VOICE_ID   : MessageId.ENGINE_RESPONSIVE_VOICE,
            clz.SAPI_ID               : MessageId.ENGINE_SAPI,
            clz.SPEECH_DISPATCHER_ID  : MessageId.ENGINE_SPEECH_DISPATCHER,
            clz.BUILT_IN_PLAYER_ID    : MessageId.ENGINE_INTERNAL,
            clz.LOG_ONLY_ID           : MessageId.ENGINE_LOG_ONLY,
            clz.PICO_TO_WAVE_ID       : MessageId.CONVERT_PICO_TO_WAV,
            clz.PIPER_ID              : MessageId.ENGINE_PIPER
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


'''
class MyStrEnum(StrEnum):

    def __new__(cls, *args) -> object:
        str_value: str = args[0]
        MY_LOGGER.debug(f'ServiceType value: {str_value} args: {args}')
        obj = str.__new__(cls)
        obj._value_ = str_value
        return obj


class OrdStrEnum(MyStrEnum):
    def __init__(self, ordinal: int) -> None:
        MY_LOGGER.debug(f'ordinal: {ordinal}')
        self.ordinal = ordinal

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal >= other.ordinal
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal > other.ordinal
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal <= other.ordinal
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal < other.ordinal
        return NotImplemented
'''


class LabeledType(StrEnum):
    """
        A StrEnum that also includes an ordinal value (for preference
        comparision) as well as messageId and a method to get the
        translated label for the value.
    """
    def __new__(cls, value: str, ord_value: int, label_id: MessageId):
        member = str.__new__(cls, value)
        member._value_ = value
        member.ordinal = ord_value
        member.label_id = label_id
        #  MY_LOGGER.debug(f'ord_value: {ord_value}')
        return member

    # def __init__(self, ordinal: int) -> None:
    #     MY_LOGGER.debug(f'ordinal: {ordinal}')
    #     self.ordinal = ordinal

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal >= other.ordinal
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal > other.ordinal
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal <= other.ordinal
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal < other.ordinal
        return NotImplemented

    @property
    def label(self) -> str:
        clz = LabeledType
        message_id: MessageId = self.label_id
        msg: str = message_id[self].get_msg()
        return msg


class MyType(StrEnum):
    """
        Indicates which services are provided
    """
    def __new__(cls, value, ord_value):
        member = str.__new__(cls, value)
        member._value_ = value
        member.ordinal = ord_value
        #  MY_LOGGER.debug(f'ord_value: {ord_value}')
        return member

    # def __init__(self, ordinal: int) -> None:
    #     MY_LOGGER.debug(f'ordinal: {ordinal}')
    #     self.ordinal = ordinal

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal >= other.ordinal
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal > other.ordinal
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal <= other.ordinal
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal < other.ordinal
        return NotImplemented


class ServiceType(MyType):
    """
    Uses a StrEnum but with an extra attribute indicating preference, in
    decreasing order
    """
    ALL = 'all', 1
    # Produces Audio
    ENGINE = 'engine', 2
    # Services are external to Kodi ex. Speech Dispatcher
    EXTERNAL_SERVICE = 'external_service', 3
    # Provides caching service
    CACHE_READER = 'cache_reader', 4
    CACHE_WRITER = 'cache_writer', 5
    # Converts audio formats
    TRANSCODER = 'transcoder', 6
    # Provides PIPE for services that can't
    PIPE_ADAPTER = 'pipe_adapter', 7
    # Plays Audio
    PLAYER = 'player', 8
    ENGINE_SETTINGS = 'engine_settings', 9
    TTS = 'TTS', 10
    INTERNAL_PLAYER = 'internal_player', 11
    LAST_SERVICE_TYPE = 'internal_player', 11

    UNKNOWN = 'UNKNOWN', 12  # TODO: Eliminate, from old_style settings


class ENGINE_SETTINGS:
    CACHE_SUFFIX: Final[str] = 'cache_suffix'


class TTS_Type(StrEnum):
    ADDONS_MD5 = 'addons_MD5'
    AUTO_ITEM_EXTRA = 'auto_item_extra'
    AUTO_ITEM_EXTRA_DELAY = 'auto_item_extra_delay'
    BACKGROUND_PROGRESS_INTERVAL = 'background_progress_interval'
    CACHE_PATH = 'cache_path'
    CACHE_EXPIRATION_DAYS = 'cache_expiration_days'
    CURRENT_ENGINE = 'current_engine'
    CONFIGURE_ON_STARTUP = 'configure_on_startup'
    DISABLE_BROKEN_SERVICES = 'disable_broken_services'
    SERVICE_ID = 'id'
    SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA = 'speak_background_progress_during_media'
    SPEAK_BACKGROUND_PROGRESS = 'speak_background_progress'
    SPEAK_ON_SERVER = 'speak_on_server'
    #  CACHE_VOICE_FILES=
    # DEBUG_LOGGING=     #  Boolean needed to toggle visibility
    DEBUG_LOG_LEVEL = 'debug_log_level'
    # Merge into Logging=  get rid of verbose_logging=  etc
    EXTENDED_HELP_ON_STARTUP = 'extended_help_on_startup'
    # GUI=
    HINT_TEXT_ON_STARTUP = 'hint_text_on_startup'
    HELP_CONFIG_ON_STARTUP = 'help_config_on_startup'
    INITIAL_RUN = 'initial_run'
    INTRODUCTION_ON_STARTUP = 'introduction_on_startup'
    # OUTPUT_VIA=
    #  OUTPUT_VISIBLE=
    OVERRIDE_POLL_INTERVAL = 'override_poll_interval'
    PITCH = 'pitch'
    POLL_INTERVAL = 'poll_interval'
    READER_ON = 'reader_on'
    #  SETTINGS_DIGEST = 'settings_digest'
    #  SETTINGS_LAST_CHANGED=
    SPEAK_LIST_COUNT = 'speak_list_count'
    SPEAK_VIA_KODI = 'speak_via_kodi'
    SERVICE_NAME = 'name'
    #  SPEED_VISIBLE=
    #  TTSD_HOST=
    #  TTSD_PORT=
    USE_TMPFS = 'use_tmpfs'
    VERSION = 'version'
    SPEED = 'speed'
    VOLUME = 'volume'


DEFAULT_MESSAGE_ID = MessageId.ENGINE_ESPEAK


class EngineType(LabeledType):
    # Engines with an ordinal, with lower values for most desired engine.
    #
    #  AUTO_ENGINE = Services.AUTO_ENGINE_ID, 0, MessageId.ENGINE_AUTO
    # EXPERIMENTAL_ENGINE = Services.EXPERIMENTAL_ENGINE_ID
    GOOGLE = Services.GOOGLE_ID, 1, MessageId.ENGINE_GOOGLE
    POWERSHELL = Services.POWERSHELL_ID, 2, MessageId.ENGINE_POWERSHELL
    # FESTIVAL = Services.FESTIVAL_ID = -1, MessageId.ENGINE_FESTIVAL
    # FLITE = Services.FLITE_ID = -1, MessageId.FLITE
    ESPEAK = Services.ESPEAK_ID, 3, MessageId.ENGINE_ESPEAK
    # LOG_ONLY = Services.LOG_ONLY_ID, 100, MessageId.ENGINE_LOG_ONLY
    # SPEECH_DISPATCHER = Services.SPEECH_DISPATCHER_ID
    NO_ENGINE = Services.NO_ENGINE_ID, 99, MessageId.ENGINE_NO_ENGINE
    # RECITE = Services.RECITE_ID
    # SAPI_ID = 'sapi'
    DEFAULT = Services.DEFAULT_ENGINE_ID, 0, DEFAULT_MESSAGE_ID


DUMMY_ENGINES: List[EngineType] = [# EngineType.AUTO_ENGINE,
                                   EngineType.DEFAULT]
ALL_ENGINES: List[EngineType] = list(EngineType)
#  ALL_ENGINES.remove(EngineType.AUTO_ENGINE)


class BasePlayerType(StrEnum):
    """
        Indicates which services are provided
    """
    def __new__(cls, value: str, supports_cache: bool, ord_value: int):
        member = str.__new__(cls, value)
        member._value_ = value
        member.supports_cache = supports_cache
        member.ordinal = ord_value
        #  MY_LOGGER.debug(f'ord_value: {ord_value}')
        return member

    # def __init__(self, ordinal: int) -> None:
    #     MY_LOGGER.debug(f'ordinal: {ordinal}')
    #     self.ordinal = ordinal

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal >= other.ordinal
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal > other.ordinal
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal <= other.ordinal
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal < other.ordinal
        return NotImplemented

    def supports_cache(self) -> bool:
        # Indicates whether this player supports a cache
        return self.supports_cache


class PlayerType(BasePlayerType):
    """
      Uses a StrEnum but with an extra attribute indicating preference, in
      decreasing order

      TODO: Review order and rational. Add more properties, such
            as PLAYER_MODEs. (get rid of some stupid validators)
      """
    # MPV is big, but very capable. Great for caching.
    MPV = Services.MPV_ID.value, True, 0
    # Windows is WAVE, but built-in
    WINDOWS = Services.WINDOWS_ID.value, True, 10
    PAPLAY = Services.PAPLAY_ID.value, True, 13
    AFPLAY = Services.AFPLAY_ID.value, True, 14
    # MPLAYER is not the best at using cache. Slave mode
    # not so great.
    MPLAYER = Services.MPLAYER_ID.value, True, 15
    SOX = Services.SOX_ID.value, True, 20
    MPG321 = Services.MPG321_ID.value, True, 40
    MPG123 = Services.MPG123_ID.value, True, 41
    MPG321_OE_PI = Services.MPG321_OE_PI_ID.value, True, 42
    APLAY = Services.APLAY_ID.value, True, 70
    # Engine's built-in player
    SFX = Services.SFX_ID.value, True, 90  # Kodi built-in, WAVE
    BUILT_IN_PLAYER = Services.BUILT_IN_PLAYER_ID.value, False, 100


    @property
    def label(self) -> str:
        clz = PlayerType
        msg_id_lookup: Dict[str, MessageId] = {
            PlayerType.SFX            : MessageId.PLAYER_SFX,
            PlayerType.WINDOWS        : MessageId.PLAYER_WINDOWS,
            PlayerType.APLAY          : MessageId.PLAYER_APLAY,
            PlayerType.PAPLAY         : MessageId.PLAYER_PAPLAY,
            PlayerType.AFPLAY         : MessageId.PLAYER_AFPLAY,
            PlayerType.SOX            : MessageId.PLAYER_SOX,
            PlayerType.MPLAYER        : MessageId.PLAYER_MPLAYER,
            PlayerType.MPV            : MessageId.PLAYER_MPV,
            PlayerType.MPG321         : MessageId.PLAYER_MPG321,
            PlayerType.MPG123         : MessageId.PLAYER_MPG123,
            PlayerType.MPG321_OE_PI: MessageId.PLAYER_MPG321_OE_PI,
            PlayerType.BUILT_IN_PLAYER: MessageId.PLAYER_BUILT_IN
        }
        msg: str = msg_id_lookup[self].get_msg()
        return msg


ALL_PLAYERS: List[PlayerType] = list(PlayerType)

SERVICES_BY_TYPE: Final[Dict[ServiceType, List[StrEnum]]] = {
    ServiceType.ENGINE: ALL_ENGINES,
    ServiceType.PLAYER: ALL_PLAYERS,
    ServiceType.TRANSCODER: ALL_TRANSCODERS
}


class ServiceID:
    """
    Encapsulates a fully qualified setting. There is an extra top-level node,
    ServiceType that the settings stored in settings.xml. This node allows
    settings which are not part of settings.xml to be managed the same way as
    those from settings.xml.

    Structure of internal settings tree:
    <ServiceType>.<Service>.<Service_property_name>
    Structure of settings in settings.xml omits some nodes when they are not
    needed. Settings.xml only has two levels. There are only two Services in
    settings.xml: Engine and other. Information about the other services (Player)
    such as player_key voice, is actually a property of the engine that is using
    the player_key. The reason for there to be a Player (and other) ServiceTypes is
    to help with configuration. 'Other' settings, such as debugging_enabled
    or the global speed are generally kept in the 'TTS' ServiceType. There are
    a small number of top-level nodes, such as 'engine' which contains the id
    of the current engine.

    The job of this class is to contain and manage the tree structure
    for settings.
    """

    def __init__(self, service_type: ServiceType,
                 service_id: str | StrEnum | None = None,
                 setting_id: str | StrEnum | None = None) -> None:
        """
        Defines the 'path' to a setting. A path can have the nodes:
        <ServiceType>.<service_name>.<setting_name>
        Ex: ENGINE.google.player_key.

        Or 'TTS.TTS.debug' Yes, the second TTS is redundant, but keeps the
        structure the same.

        :param service_type: Required ServiceType.ENGINE, etc.
        :param service_id:   Required setting_id, ex. 'google'
        :param setting_id:   Optional when the node is used to operate on all
                             settings of a service: ex Load all ENGINE google settings
        """
        if service_type is None or not isinstance(service_type, ServiceType):
            raise ValueError('service_type is NOT type ServiceType, rather it is '
                             f'{type(service_type)} {service_type}')
        self._service_type: ServiceType = service_type
        if service_id is not None and not isinstance(service_id, str):
            raise ValueError(f'service_id should be str, NOT {type(service_id)} '
                             f'{service_id}')
        # StrEnums are also considered strs, but we want real str (for now)
        if isinstance(service_id, StrEnum):
            service_id: str = service_id.value
        self._service_id: str = service_id
        if setting_id is not None and not isinstance(setting_id, str):
            raise ValueError(f'setting_id should be str, NOT {type(setting_id)} '
                             f'{setting_id}')
        if isinstance(setting_id, StrEnum):
            setting_id = setting_id.value
        self._setting_id: str | None = setting_id

        # key to identify the service: See @property service_key
        self._service_key: str | None = None

        # key to identify the service FOR settings. see @property short_service_key
        self._short_service_key: str | None = None

        # key to identify the full ServiceID: see @property key
        self._key: str | None = None
        # key to identify the full ServiceID: see @property short_key
        self._short_key: str | None = None

    def with_prop(self, setting_id: str | StrEnum) -> ForwardRef('ServiceID'):
        return ServiceID(service_type=self.service_type,
                         service_id=self.service_id,
                         setting_id=setting_id)

    def from_full_setting_id(self, full_setting_id: str) -> ForwardRef('ServiceID'):
        tmp_id: List[str] = full_setting_id.split(sep=".", maxsplit=2)
        setting_id: str | None = None
        service_id: str = tmp_id[-1]
        if len(tmp_id) == 2:
            setting_id = tmp_id[0]
        return ServiceID(service_type=ServiceType.UNKNOWN, service_id=service_id,
                         setting_id=setting_id)

    def __str__(self) -> str:
        #  MY_LOGGER.debug(f'key: {self._key}')
        return self.key

    def __repr__(self) -> str:
        return f'{self}'

    @property
    def service_type(self) -> ServiceType:
        return self._service_type

    @property
    def service_id(self) -> str:
        return self._service_id

    @property
    def setting_id(self) -> Any:
        return self._setting_id

    @property
    def key(self) -> str:
        """
        Gets the key for the setting. Used by SettingsMap (and likely others) to
        access a map of a list of settings.

        :return:
        """
        if self._key is None:
            if self._setting_id is not None and self._setting_id != '':
                self._key = (f'{self.service_type.value}.{self.service_id}.'
                             f'{self.setting_id}')
            else:
                self._key = (f'{self.service_type.value}.{self.service_id}.'
                             f'{TTS_Type.SERVICE_ID}')
            MY_LOGGER.debug(f'key: {self._key}')
        return self._key

    @property
    def short_key(self) -> str:
        """
        Gets a path usable for settings stored in Settings.xml.
        Does NOT validate the path.
        :return:
        """
        if self._short_key is None:
            if self._setting_id is None:
                # raise ValueError('Missing setting_id')
                return self.service_key
            self._short_key = f'{str(self.setting_id)}.{str(self.service_id)}'
            MY_LOGGER.debug(f'short_key: {self._short_key}')
        return self._short_key

    @property
    def service_key(self) -> str:
        """
        Gets the key for the service itself. Used by SettingsMap (and likely others) to
        access a map of a list of settings. The key consists of:
        ServiceType.service_id.id_property. Example: 'engine.google.id'. The
        value of the service_key is the same as the service_id.

        Does NOT validate the path.
        :return:
        """
        if self._service_key is None:
            self._service_key: str = (f'{self.service_type.value}.{str(self.service_id)}.'
                                      f'{TTS_Type.SERVICE_ID}')
            MY_LOGGER.debug(f'service_type.service_id.id: {self._service_key}'
                            f' service_key: {self.key}')
        return self._service_key

    @property
    def short_service_key(self) -> str:
        """
        Gets the key for the service itself. Used by SettingsMap (and likely others) to
        access a map of a list of settings. The key consists of:
        id_property.service_id. Example: 'id.google'. The
        value of the service_key is the same as the service_id.

        Does NOT validate the path.
        :return:
        """
        if self._short_service_key is None:
            self._short_service_key: str = (f'{TTS_Type.SERVICE_ID}.'
                                            f'{str(self.service_id)}')
            MY_LOGGER.debug(f'id.service_id: {self._short_service_key}'
                            f' key: {self}')
        return self._short_service_key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ServiceID):
            if not isinstance(other, str):
                raise ValueError(f'Expected {type(self)} or str type not: {type(other)}')
            else:
                return self.key == other
        other: ServiceID
        return self.key == other.key

    def __hash__(self):
        return hash(self.key)


class ServiceKey:
    ENGINE_KEY: ServiceID = ServiceID(ServiceType.ENGINE)
    PLAYER_KEY: ServiceID = ServiceID(ServiceType.PLAYER)
    TTS_KEY: ServiceID = ServiceID(ServiceType.TTS,
                                   Services.TTS_SERVICE, TTS_Type.SERVICE_ID)
    #  EXPERIMENTAL_ENGINE = Services.EXPERIMENTAL_ENGINE_ID
    #  AUTO_KEY: ServiceID = ServiceID(ServiceType.ENGINE, Services.AUTO_ENGINE_ID,
    #                                  None)
    GOOGLE_KEY: ServiceID = ServiceID(ServiceType.ENGINE,
                                      Services.GOOGLE_ID, TTS_Type.SERVICE_ID)
    #  FESTIVAL = Services.FESTIVAL_ID
    #  FLITE = Services.FLITE_ID
    ESPEAK_KEY: ServiceID = ServiceID(ServiceType.ENGINE,
                                      Services.ESPEAK_ID, TTS_Type.SERVICE_ID)
    #  LOG_ONLY = Services.LOG_ONLY_ID
    #  SPEECH_DISPATCHER = Services.SPEECH_DISPATCHER_ID
    NO_ENGINE_KEY: ServiceID = ServiceID(ServiceType.ENGINE,
                                         Services.NO_ENGINE_ID, TTS_Type.SERVICE_ID)
    POWERSHELL_KEY: ServiceID = ServiceID(ServiceType.ENGINE,
                                          Services.POWERSHELL_ID, TTS_Type.SERVICE_ID)
    # TODO: REWORK to be dynamic. Need shared safe place to update in
    # bootstrap or config and use here
    DEFAULT_KEY: ServiceID = ServiceID(ServiceType.ENGINE, EngineType.DEFAULT,
                                       TTS_Type.SERVICE_ID)

    MPV_KEY: ServiceID = ServiceID(ServiceType.PLAYER, PlayerType.MPV,
                                   TTS_Type.SERVICE_ID)
    MPLAYER_KEY: ServiceID = ServiceID(ServiceType.PLAYER, PlayerType.MPLAYER,
                                       TTS_Type.SERVICE_ID)
    SFX_KEY: ServiceID = ServiceID(ServiceType.PLAYER, PlayerType.SFX,
                                   TTS_Type.SERVICE_ID)
    BUILT_IN_KEY: ServiceID = ServiceID(ServiceType.PLAYER, PlayerType.BUILT_IN_PLAYER,
                                        TTS_Type.SERVICE_ID)
    #  RECITE = Services.RECITE_ID
    #  SAPI_ID = 'sapi'
    #  DEFAULT = Services.DEFAULT_ENGINE_ID

    #  ------------------ TTS (top_level)
    ADDONS_MD5: ServiceID  #
    ADDONS_MD5 = TTS_KEY.with_prop(TTS_Type.ADDONS_MD5)
    AUTO_ITEM_EXTRA: ServiceID
    AUTO_ITEM_EXTRA = TTS_KEY.with_prop(TTS_Type.AUTO_ITEM_EXTRA)
    AUTO_ITEM_EXTRA_DELAY: ServiceID  #
    AUTO_ITEM_EXTRA_DELAY = TTS_KEY.with_prop(TTS_Type.AUTO_ITEM_EXTRA_DELAY)
    BACKGROUND_PROGRESS_INTERVAL: ServiceID  #
    BACKGROUND_PROGRESS_INTERVAL = TTS_KEY.with_prop(TTS_Type.BACKGROUND_PROGRESS_INTERVAL)
    CACHE_EXPIRATION_DAYS: ServiceID  #
    CACHE_EXPIRATION_DAYS = TTS_KEY.with_prop(TTS_Type.CACHE_EXPIRATION_DAYS)
    # CACHE_PATH: ServiceID  #
    # CACHE_PATH = TTS_KEY.with_prop(TTS_Type.CACHE_PATH)
    CURRENT_ENGINE_KEY: ServiceID
    CURRENT_ENGINE_KEY = TTS_KEY.with_prop(TTS_Type.CURRENT_ENGINE)
    DEBUG_LOG_LEVEL: ServiceID  #
    DEBUG_LOG_LEVEL = TTS_KEY.with_prop(TTS_Type.DEBUG_LOG_LEVEL)
    DISABLE_BROKEN_SERVICES: ServiceID  #
    DISABLE_BROKEN_SERVICES = TTS_KEY.with_prop(TTS_Type.DISABLE_BROKEN_SERVICES)
    EXTENDED_HELP_ON_STARTUP: ServiceID  #
    EXTENDED_HELP_ON_STARTUP = TTS_KEY.with_prop(TTS_Type.EXTENDED_HELP_ON_STARTUP)
    HINT_TEXT_ON_STARTUP: ServiceID  #
    HINT_TEXT_ON_STARTUP = TTS_KEY.with_prop(TTS_Type.HINT_TEXT_ON_STARTUP)
    INITIAL_RUN: ServiceID
    INITIAL_RUN = TTS_KEY.with_prop(TTS_Type.INITIAL_RUN)
    INTRODUCTION_ON_STARTUP: ServiceID
    INTRODUCTION_ON_STARTUP = TTS_KEY.with_prop(TTS_Type.INTRODUCTION_ON_STARTUP)
    OVERRIDE_POLL_INTERVAL: ServiceID  #
    OVERRIDE_POLL_INTERVAL = TTS_KEY.with_prop(TTS_Type.OVERRIDE_POLL_INTERVAL)
    PITCH: ServiceID
    PITCH = TTS_KEY.with_prop(TTS_Type.PITCH)
    POLL_INTERVAL: ServiceID  #
    POLL_INTERVAL = TTS_KEY.with_prop(TTS_Type.POLL_INTERVAL)
    READER_ON: ServiceID  #
    READER_ON = TTS_KEY.with_prop(TTS_Type.READER_ON)
    #  SETTINGS_DIGEST: ServiceID  #
    #  SETTINGS_DIGEST = TTS_KEY.with_prop(TTS_Type.SETTINGS_DIGEST)
    SPEAK_BACKGROUND_PROGRESS: ServiceID  #
    SPEAK_BACKGROUND_PROGRESS = TTS_KEY.with_prop(TTS_Type.SPEAK_BACKGROUND_PROGRESS)
    SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: ServiceID  #
    SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA = TTS_KEY.with_prop(
            TTS_Type.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA)
    SPEAK_LIST_COUNT: ServiceID  #
    SPEAK_LIST_COUNT = TTS_KEY.with_prop(TTS_Type.SPEAK_LIST_COUNT)
    SPEAK_ON_SERVER: ServiceID
    SPEAK_ON_SERVER = TTS_KEY.with_prop(TTS_Type.SPEAK_ON_SERVER)
    SPEAK_VIA_KODI: ServiceID  #
    SPEAK_VIA_KODI = TTS_KEY.with_prop(TTS_Type.SPEAK_VIA_KODI)
    SPEED: ServiceID
    SPEED = TTS_KEY.with_prop(TTS_Type.SPEED)
    USE_TMPFS: ServiceID    #
    USE_TMPFS = TTS_KEY.with_prop(TTS_Type.USE_TMPFS)
    VERSION: ServiceID    #
    VERSION = TTS_KEY.with_prop(TTS_Type.VERSION)
    VOLUME: ServiceID    #
    VOLUME = TTS_KEY.with_prop(TTS_Type.VOLUME)

    #  Services for Engines.
