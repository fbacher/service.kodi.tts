# -*- coding: utf-8 -*-

from enum import Enum

from common.logger import BasicLogger
from common.message_ids import MessageId

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from common import *

from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from common.messages import Message, Messages

MY_LOGGER = BasicLogger.get_logger(__name__)


class BaseSettingsConstants:

    settings_map: Dict[str, Message] = {}

    @classmethod
    def get_label(cls, setting_id: str) -> str:
        msg_handle = cls.settings_map.get(setting_id, setting_id)
        label = Messages.get_msg(msg_handle)
        return label

    @classmethod
    def get_msg_handle(cls, setting_id: str) -> Message:
        return cls.settings_map.get(setting_id, None)


class Backends(BaseSettingsConstants):
    AUTO_ID: Final[str] = Services.AUTO_ENGINE_ID
    DEFAULT_ENGINE_ID: Final[str] = Services.DEFAULT_ENGINE_ID
    ESPEAK_ID: Final[str] = Services.ESPEAK_ID
    FESTIVAL_ID: Final[str] = Services.FESTIVAL_ID
    FLITE_ID: Final[str] = Services.FLITE_ID
    INTERNAL_ID: Final[str] = Services.INTERNAL_PLAYER_ID
    LOG_ONLY_ID: Final[str] = Services.LOG_ONLY_ID
    NO_ENGINE_ID = Services.NO_ENGINE_ID
    PICO_TO_WAVE_ID: Final[str] = Services.PICO_TO_WAVE_ID
    PIPER_ID: Final[str] = Services.PIPER_ID
    POWERSHELL_ID: Final[str] = Services.POWERSHELL_ID
    RECITE_ID: Final[str] = Services.RECITE_ID
    RESPONSIVE_VOICE_ID: Final[str] = Services.RESPONSIVE_VOICE_ID
    GOOGLE_ID: Final[str] = Services.GOOGLE_ID
    SPEECH_DISPATCHER_ID: Final[str] = Services.SPEECH_DISPATCHER_ID
    EXPERIMENTAL_ENGINE_ID: Final[str] = Services.EXPERIMENTAL_ENGINE_ID
    SAPI_ID: Final[str] = Services.SAPI_ID

    ALL_ENGINE_IDS: List[str] = [
        AUTO_ID,
        ESPEAK_ID,
        # EXPERIMENTAL_ENGINE_ID,
        # FESTIVAL_ID,
        # FLITE_ID,
        GOOGLE_ID,
        # INTERNAL_ID,
        # LOG_ONLY_ID,
        # PICO_TO_WAVE_ID,
        # PIPER_ID,
        POWERSHELL_ID,
        # RECITE_ID,
        # RESPONSIVE_VOICE_ID,
        # SAPI_ID,
        # SPEECH_DISPATCHER_ID
    ]

    settings_map: Dict[str, Message] = {
        AUTO_ID             : MessageId.ENGINE_AUTO,
        ESPEAK_ID           : MessageId.ENGINE_ESPEAK,
        FESTIVAL_ID         : MessageId.ENGINE_FESTIVAL,
        FLITE_ID            : MessageId.ENGINE_FLITE,
        GOOGLE_ID           : MessageId.ENGINE_GOOGLE,
        INTERNAL_ID         : MessageId.ENGINE_INTERNAL,
        LOG_ONLY_ID         : MessageId.ENGINE_LOG_ONLY,
        PICO_TO_WAVE_ID     : MessageId.CONVERT_PICO_TO_WAV,
        PIPER_ID            : MessageId.ENGINE_PIPER,
        POWERSHELL_ID       : MessageId.ENGINE_POWERSHELL,
        RECITE_ID           : MessageId.ENGINE_RECITE,
        RESPONSIVE_VOICE_ID : MessageId.ENGINE_RESPONSIVE_VOICE,
        SAPI_ID             : MessageId.ENGINE_SAPI,
        SPEECH_DISPATCHER_ID: MessageId.ENGINE_SPEECH_DISPATCHER
    }

    # Separate cache for each engine. Short code that is a directory
    # below the CACHE_PATH

    ENGINE_CACHE_CODE: Dict[str, str] = {
        ESPEAK_ID             : 'espeak',
        FESTIVAL_ID           : 'fest',
        FLITE_ID              : 'flite',
        RESPONSIVE_VOICE_ID   : 'rv',
        SPEECH_DISPATCHER_ID  : 'speechDisp',
        EXPERIMENTAL_ENGINE_ID: 'ex',
        GOOGLE_ID             : 'goo',
        PIPER_ID              : 'piper'
    }


class Languages(BaseSettingsConstants):
    _logger: BasicLogger = None

    # Msg for generic locale display
    # Msg 32425 in strings.po is: "{0} ({1})"
    # {0} is for Language
    # {1} is for Country/region
    # Example "English (United States)"
    LOCALE_GENERIC: Final[int] = 32425


    LOCALE_AF: Final[str] = 'af'
    LOCALE_AF_ZA: Final[str] = 'af-za'
    LOCALE_AR_SA: Final[str] = 'ar-sa'
    LOCALE_BS: Final[str] = 'bs'
    LOCALE_CA: Final[str] = 'ca'
    LOCALE_CA_ES: Final[str] = 'ca-es'
    LOCALE_CS: Final[str] = 'cs'
    LOCALE_CY: Final[str] = 'cy'
    LOCALE_DA_DK: Final[str] = 'da-dk'
    LOCALE_DE_DE: Final[str] = 'de-de'
    LOCALE_EL_GR: Final[str] = 'el-gr'
    LOCALE_EN_AU: Final[str] = 'en-au'
    LOCALE_EN_GB: Final[str] = 'en-gb'
    LOCALE_EN_IE: Final[str] = 'en-ie'
    LOCALE_EN_IN: Final[str] = 'en-in'
    LOCALE_EN_US: Final[str] = 'en-us'
    LOCALE_EN_ZA: Final[str] = 'en-za'
    LOCALE_EO: Final[str] = 'eo'
    LOCALE_ES_ES: Final[str] = 'es-es'
    LOCALE_ES: Final[str] = 'es'
    LOCALE_ES_MX: Final[str] = 'es-mx'
    LOCALE_ES_US: Final[str] = 'es-us'
    LOCALE_FI_FI: Final[str] = 'fi-fi'
    LOCALE_FR_BE: Final[str] = 'fr-be'
    LOCALE_FR_FR: Final[str] = 'fr-fr'
    LOCALE_FR_CA: Final[str] = 'fr-ca'
    LOCALE_FR: Final[str] = 'fr'
    LOCALE_HI: Final[str] = 'hi'
    LOCALE_HI_IN: Final[str] = 'hi-in'
    LOCALE_HR_HR: Final[str] = 'hr-hr'
    LOCALE_HU_HU: Final[str] = 'hu-hu'
    LOCALE_HY_AM: Final[str] = 'hy-am'
    LOCALE_ID_ID: Final[str] = 'id-id'
    LOCALE_IS_IS: Final[str] = 'is-is'
    LOCALE_IT_IT: Final[str] = 'it-it'
    LOCALE_JA_JP: Final[str] = 'ja-jp'
    LOCALE_KO_KR: Final[str] = 'ko-kr'
    LOCALE_LA: Final[str] = 'la'
    LOCALE_LV_LV: Final[str] = 'lv-lv'
    LOCALE_NB_NO: Final[str] = 'nb-no'
    LOCALE_NL_BE: Final[str] = 'nl-be'
    LOCALE_NL_NL: Final[str] = 'nl-nl'
    LOCALE_NO_NO: Final[str] = 'no-no'
    LOCALE_PL_PL: Final[str] = 'pl-pl'
    LOCALE_PT_BR: Final[str] = 'pt-br'
    LOCALE_PT_PT: Final[str] = 'pt-pt'
    LOCALE_RO_RO: Final[str] = 'ro-ro'
    LOCALE_RU_RU: Final[str] = 'ru-ru'
    LOCALE_SK_SK: Final[str] = 'sk-sk'
    LOCALE_SQ_AL: Final[str] = 'sq-al'
    LOCAL_SR_ME: Final[str] = 'sr-me'
    LOCALE_SR_RS: Final[str] = 'sr-rs'
    LOCALE_SW_KE: Final[str] = 'sw-ke'
    LOCALE_TA: Final[str] = 'ta'
    LOCALE_TH_TH: Final[str] = 'th-th'
    LOCALE_TR_TR: Final[str] = 'tr-tr'
    LOCALE_VI_VN: Final[str] = 'vi-vn'
    LOCALE_ZH_CN: Final[str] = 'zh-cn'
    LOCALE_ZH_HK: Final[str] = 'zh-hk'
    LOCALE_ZH_TW: Final[str] = 'zh-tw'

    COUNTRY_AL: Final[str] = 'al'
    COUNTRY_AM: Final[str] = 'am'
    COUNTRY_AU: Final[str] = 'au'
    COUNTRY_BE: Final[str] = 'be'
    COUNTRY_BR: Final[str] = 'br'
    COUNTRY_CA: Final[str] = 'ca'
    COUNTRY_CN: Final[str] = 'cn'
    COUNTRY_DE: Final[str] = 'de'
    COUNTRY_DK: Final[str] = 'dk'
    COUNTRY_EO: Final[str] = 'eo'
    COUNTRY_ES: Final[str] = 'es'
    COUNTRY_FI: Final[str] = 'fi'
    COUNTRY_FR: Final[str] = 'fr'
    COUNTRY_GB: Final[str] = 'gb'
    COUNTRY_GR: Final[str] = 'gr'
    COUNTRY_HK: Final[str] = 'hk'
    COUNTRY_HR: Final[str] = 'hr'
    COUNTRY_HU: Final[str] = 'hu'
    COUNTRY_ID: Final[str] = 'id'
    COUNTRY_IE: Final[str] = 'ie'
    COUNTRY_IN: Final[str] = 'in'
    COUNTRY_IS: Final[str] = 'is'
    COUNTRY_IT: Final[str] = 'it'
    COUNTRY_JA: Final[str] = 'ja'
    COUNTRY_KE: Final[str] = 'ke'
    COUNTRY_KR: Final[str] = 'kr'
    COUNTRY_LV: Final[str] = 'lv'
    COUNTRY_ME: Final[str] = 'me'
    COUNTRY_MX: Final[str] = 'mx'
    COUNTRY_NL: Final[str] = 'nl'
    COUNTRY_NO: Final[str] = 'no'
    COUNTRY_PL: Final[str] = 'pl'
    COUNTRY_PT: Final[str] = 'pt'
    COUNTRY_RO: Final[str] = 'ro'
    COUNTRY_RS: Final[str] = 'rs'
    COUNTRY_RU: Final[str] = 'ru'
    COUNTRY_SA: Final[str] = 'sa'
    COUNTRY_SK: Final[str] = 'sk'
    COUNTRY_TA: Final[str] = 'ta'
    COUNTRY_TH: Final[str] = 'th'
    COUNTRY_TR: Final[str] = 'tr'
    COUNTRY_TW: Final[str] = 'tw'
    COUNTRY_US: Final[str] = 'us'
    COUNTRY_VN: Final[str] = 'vn'
    COUNTRY_ZA: Final[str] = 'za'

    LANG_AF: Final[str] = 'af'
    LANG_AR: Final[str] = 'ar'
    LANG_BS: Final[str] = 'bo'
    LANG_CA: Final[str] = 'ca'
    LANG_CS: Final[str] = 'cz'
    LANG_CY: Final[str] = 'we'
    LANG_DA: Final[str] = 'da'
    LANG_DE: Final[str] = 'de'
    LANG_EL: Final[str] = 'gr'
    LANG_EN: Final[str] = 'en'
    LANG_EO: Final[str] = 'es'
    LANG_ES: Final[str] = 'sp'
    LANG_FI: Final[str] = 'fi'
    LANG_FR: Final[str] = 'fr'
    LANG_HI: Final[str] = 'hi'
    LANG_HR: Final[str] = 'cr'
    LANG_HU: Final[str] = 'hu'
    LANG_HY: Final[str] = 'ar'
    LANG_ID: Final[str] = 'in'
    LANG_IS: Final[str] = 'ic'
    LANG_IT: Final[str] = 'it'
    LANG_JA: Final[str] = 'ja'
    LANG_KO: Final[str] = 'ko'
    LANG_LA: Final[str] = 'la'
    LANG_LV: Final[str] = 'la'
    LANG_NB: Final[str] = 'no'
    LANG_NL: Final[str] = 'du'
    LANG_NO: Final[str] = 'no'
    LANG_PL: Final[str] = 'po'
    LANG_PT: Final[str] = 'po'
    LANG_RO: Final[str] = 'ro'
    LANG_RU: Final[str] = 'ru'
    LANG_SK: Final[str] = 'sl'
    LANG_SQ: Final[str] = 'al'
    LANG_SR: Final[str] = 'se'
    LANG_SW: Final[str] = 'sw'
    LANG_TA: Final[str] = 'ta'
    LANG_TH: Final[str] = 'th'
    LANG_TR: Final[str] = 'tu'
    LANG_VI: Final[str] = 'vi'
    LANG_ZH: Final[str] = 'ch'


# Most settings are stored using TTS-defined values. Each user
# of the settings use a validator & constraints to translate to and
# from TTS values. This is done to make it easier to share values
# between engines, players, etc.


# TODO: Change to ENUM
class Players(BaseSettingsConstants):
    TTS: Final[str] = 'tts'
    NONE: Final[str] = 'Unknown Player'
    SFX: Final[str] = 'sfx'
    WINDOWS: Final[str] = 'Windows'
    APLAY: Final[str] = 'aplay'
    PAPLAY: Final[str] = 'paplay'
    AFPLAY: Final[str] = 'afplay'
    SOX: Final[str] = 'sox'
    MPLAYER: Final[str] = 'mplayer'
    MPV: Final[str] = 'mpv'
    MPG321: Final[str] = 'mpg321'
    MPG123: Final[str] = 'mpg123'
    MPG321_OE_PI: Final[str] = 'mpg321_OE_Pi'

    # Engine's built-in player

    INTERNAL: Final[str] = 'internal'

    # HANDLERS

    WavAudioPlayerHandler = 'wave_handler'
    MP3AudioPlayerHandler = 'mp3_handler'
    BuiltInAudioPlayerHandler = 'internal_handler'

    settings_map = {
        NONE        : MessageId.PLAYER_NONE,
        SFX         : MessageId.PLAYER_SFX,
        WINDOWS     : MessageId.PLAYER_WINDOWS,
        APLAY       : MessageId.PLAYER_APLAY,
        PAPLAY      : MessageId.PLAYER_PAPLAY,
        AFPLAY      : MessageId.PLAYER_AFPLAY,
        SOX         : MessageId.PLAYER_SOX,
        MPLAYER     : MessageId.PLAYER_MPLAYER,
        MPV         : MessageId.PLAYER_MPV,
        MPG321      : MessageId.PLAYER_MPG321,
        MPG123      : MessageId.PLAYER_MPG123,
        MPG321_OE_PI: MessageId.PLAYER_MPG321_OE_PI,
        INTERNAL    : MessageId.PLAYER_INTERNAL
    }

    @classmethod
    def get_msg(cls, player: str) -> str:
        return Players.settings_map[player].get_msg()


    ALL_PLAYER_IDS: List[str] = [
            Services.MPV_ID,
            Services.MPLAYER_ID,
            Services.SFX_ID,
            # WINDOWS,
            # APLAY,
            # PAPLAY,
            # AFPLAY,
            # SOX,
            # MPG321,
            # MPG123,
            # MPG321_OE_PI,
            # INTERNAL,
            # NONE,
            # WavAudioPlayerHandler,
            # MP3AudioPlayerHandler,
            # BuiltInAudioPlayerHandler
    ]


class PlayerMode(StrEnum):
    SLAVE_FILE = 'slave_file'
    SLAVE_PIPE = 'slave_pipe'
    FILE = 'file'
    PIPE = 'pipe'
    ENGINE_SPEAK = 'engine_speak'

    @property
    def name(self) -> str:
        return self.value

    @property
    def translated_name(self) -> str:
        clz = type(self)
        msg_look_up: Dict[ForwardRef('PlayerMode'), str] = {
            clz.SLAVE_FILE: MessageId.PLAYER_MODE_SLAVE_FILE.get_msg(),
            clz.SLAVE_PIPE: MessageId.PLAYER_MODE_SLAVE_PIPE.get_msg(),
            clz.FILE: MessageId.PLAYER_MODE_FILE.get_msg(),
            clz.PIPE: MessageId.PLAYER_MODE_PIPE.get_msg(),
            clz.ENGINE_SPEAK: MessageId.PLAYER_MODE_ENGINE_SPEAK.get_msg()
            }
        player_name: str = ''
        try:
            player_name = msg_look_up.get(self)
        except:
            MY_LOGGER.exception('')
        return player_name

    @classmethod
    def get_rank(cls, player_mode: ForwardRef('PlayerMode')) -> int:
        ranking: Dict[ForwardRef('PlayerMode'), int] = {
            cls.SLAVE_FILE  : 0,
            cls.SLAVE_PIPE  : 1,
            cls.FILE        : 2,
            cls.PIPE        : 3,
            cls.ENGINE_SPEAK: 4
        }
        rank: int = ranking[player_mode]
        return rank

    @classmethod
    def normalize(cls,
                  modes: List[ForwardRef('PlayerMode')]
                  ) -> List[List[Any]]:
        """
        Build a ranked list of every possible PlayerModes, but with a bool indicating
        whether the element was present in the input list or not.

        :param modes:
        :return: A List[List[PlayerMode, PlayerMode_rank, present]
        """
        marked_list: List[List[Any]] = [
            [cls.SLAVE_FILE, 0, False],
            [cls.SLAVE_PIPE, 1, False],
            [cls.FILE, 2, False],
            [cls.PIPE, 3, False],
            [cls.ENGINE_SPEAK, 4, False]
        ]
        for mode in modes:
            mode: ForwardRef('PlayerMode')
            MY_LOGGER.debug(f'mode: {mode} type: {type(mode)}')
            rank: int = cls.get_rank(mode)
            MY_LOGGER.debug(f'rank: {rank}')
            marked_mode: List[Any]
            marked_list[rank][2] = True
            MY_LOGGER.debug(f'marked_list[rank]: {marked_list[rank]}')
        return marked_list

    @classmethod
    def intersection(cls,
                     modes_1: List[ForwardRef('PlayerMode')],
                     modes_2: List[ForwardRef('PlayerMode')]
                     ) -> List[ForwardRef('PlayerMode')]:
        normalized_1: List[List[Any]]
        normalized_1 = cls.normalize(modes_1)
        normalized_2: List[List[Any]]
        normalized_2 = cls.normalize(modes_2)

        # Since both lists have all the possible PlayerMode values in order,
        # simply walk both lists at the same time looking for when
        # both lists are marked as having that PlayerMode from the
        # input lists.

        intersection: List[ForwardRef('PlayerMode')] = []
        for norm_1, norm_2 in zip(normalized_1, normalized_2):
            if norm_1[2] and norm_2[2]:
                intersection.append(norm_1[0])
        return intersection


class AudioType(StrEnum):
    MP3 = 'mp3'
    WAV = 'wav'


class Converters(BaseSettingsConstants):
    NONE: Final[str] = 'Unknown Player'
    WINDOWS: Final[str] = 'Windows'
    SOX: Final[str] = 'sox'
    MPLAYER: Final[str] = 'mencoder'
    MPG123: Final[str] = 'mpg123'  # Can convert from mpg to wave, not too useful
    MPG321_OE_PI: Final[str] = 'mpg321_OE_Pi'
    MPG321: Final[str] = 'mpg321'  # near clone of mpg123, can convert mpg to wave
    LAME: Final[str] = 'lame'  # can be accessed directly via lame command (linux)
    # or via ffmpeg

    # Built-in players

    INTERNAL: Final[str] = 'internal'

    # TODO: Review to see if messages need to be unique to the converter job

    settings_map = {
        NONE        : Messages.PLAYER_NONE,
        WINDOWS     : Messages.PLAYER_WINDOWS,
        SOX         : Messages.PLAYER_SOX,
        MPLAYER     : Messages.PLAYER_MPLAYER,
        MPG321      : Messages.PLAYER_MPG321,
        MPG123      : Messages.PLAYER_MPG123,
        MPG321_OE_PI: Messages.PLAYER_MPG321_OE_PI,
        INTERNAL    : Messages.PLAYER_INTERNAL,
    }


class Genders(StrEnum):
    MALE = 'male'
    FEMALE = 'female'
    UNKNOWN = 'unknown'

    def get_label(self) -> str:
        msg_id: Message = GenderSettingsMap[self]
        label: str = Messages.get_msg(msg_id)
        return label


class GenderSettingsMap(BaseSettingsConstants):
    settings_map: Dict[Genders, Message] = {
        Genders.MALE   : Messages.GENDER_MALE,
        Genders.FEMALE : Messages.GENDER_FEMALE,
        Genders.UNKNOWN: Messages.GENDER_UNKNOWN
    }


class Channels(StrEnum):
    # Note the # channels effects perceived volume.
    NO_PREF = 'no_pref'
    MONO = 'mono'
    STEREO = 'stereo'


class ChannelSettingsMap(BaseSettingsConstants):
    settings_map = {
        Channels.NO_PREF: Messages.CHANNEL_NO_PREF,
        Channels.MONO   : Messages.CHANNEL_MONO,
        Channels.STEREO : Messages.CHANNEL_STEREO
    }


class Misc(BaseSettingsConstants):
    PITCH: Final[str] = SettingsProperties.PITCH

    settings_map = {
        PITCH: Messages.MISC_PITCH
    }


class Mode(Enum):
    FILEOUT = 0
    ENGINESPEAK = 1
    PIPE = 2
