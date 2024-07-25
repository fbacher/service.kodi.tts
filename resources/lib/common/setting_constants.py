# -*- coding: utf-8 -*-

from enum import Enum

from common.logger import BasicLogger

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from common import *

from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from common.messages import Message, Messages

module_logger = BasicLogger.get_module_logger(module_path=__file__)


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
    PICO_TO_WAVE_ID: Final[str] = Services.PICO_TO_WAVE_ID
    PIPER_ID: Final[str] = Services.PIPER_ID
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
        LOG_ONLY_ID,
        # PICO_TO_WAVE_ID,
        # PIPER_ID,
        # RECITE_ID,
        # RESPONSIVE_VOICE_ID,
        # SAPI_ID,
        # SPEECH_DISPATCHER_ID
    ]
    settings_map: Dict[str, Message] = {
        AUTO_ID             : Messages.AUTO,
        ESPEAK_ID           : Messages.BACKEND_ESPEAK,
        FESTIVAL_ID         : Messages.BACKEND_FESTIVAL,
        FLITE_ID            : Messages.BACKEND_FLITE,
        GOOGLE_ID           : Messages.BACKEND_GOOGLE,
        INTERNAL_ID         : Messages.BACKEND_INTERNAL,
        LOG_ONLY_ID         : Messages.BACKEND_LOG_ONLY,
        PICO_TO_WAVE_ID     : Messages.CONVERT_PICO_TO_WAV,
        PIPER_ID            : Messages.BACKEND_PIPER,
        RECITE_ID           : Messages.BACKEND_RECITE,
        RESPONSIVE_VOICE_ID : Messages.BACKEND_RESPONSIVE_VOICE,
        SAPI_ID             : Messages.BACKEND_SAPI,
        SPEECH_DISPATCHER_ID: Messages.BACKEND_SPEECH_DISPATCHER
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

    locale_msg_map = {
        LOCALE_AF   : Messages.LOCALE_AF,
        LOCALE_AF_ZA: Messages.LOCALE_AF_ZA,
        LOCALE_AR_SA: Messages.LOCALE_AR_SA,
        LOCALE_BS   : Messages.LOCALE_BS,
        LOCALE_CA   : Messages.LOCALE_CA,
        LOCALE_CA_ES: Messages.LOCALE_CA_ES,
        LOCALE_CS   : Messages.LOCALE_CS,
        LOCALE_CY   : Messages.LOCALE_CY,
        LOCALE_DA_DK: Messages.LOCALE_DA_DK,
        LOCALE_DE_DE: Messages.LOCALE_DE_DE,
        LOCALE_EL_GR: Messages.LOCALE_EL_GR,
        LOCALE_EN_AU: Messages.LOCALE_EN_AU,
        LOCALE_EN_GB: Messages.LOCALE_EN_GB,
        LOCALE_EN_IE: Messages.LOCALE_EN_IE,
        LOCALE_EN_IN: Messages.LOCALE_EN_IN,
        LOCALE_EN_US: Messages.LOCALE_EN_US,
        LOCALE_EN_ZA: Messages.LOCALE_EN_ZA,
        LOCALE_EO   : Messages.LOCALE_EO,
        LOCALE_ES_ES: Messages.LOCALE_ES_ES,
        LOCALE_ES   : Messages.LOCALE_ES,
        LOCALE_ES_MX: Messages.LOCALE_ES_MX,
        LOCALE_ES_US: Messages.LOCALE_ES_US,
        LOCALE_FI_FI: Messages.LOCALE_FI_FI,
        LOCALE_FR_BE: Messages.LOCALE_FR_BE,
        LOCALE_FR_FR: Messages.LOCALE_FR_FR,
        LOCALE_FR_CA: Messages.LOCALE_FR_CA,
        LOCALE_FR   : Messages.LOCALE_FR,
        LOCALE_HI   : Messages.LOCALE_HI,
        LOCALE_HI_IN: Messages.LOCALE_HI_IN,
        LOCALE_HR_HR: Messages.LOCALE_HR_HR,
        LOCALE_HU_HU: Messages.LOCALE_HU_HU,
        LOCALE_HY_AM: Messages.LOCALE_HY_AM,
        LOCALE_ID_ID: Messages.LOCALE_ID_ID,
        LOCALE_IS_IS: Messages.LOCALE_IS_IS,
        LOCALE_IT_IT: Messages.LOCALE_IT_IT,
        LOCALE_JA_JP: Messages.LOCALE_JA_JP,
        LOCALE_KO_KR: Messages.LOCALE_KO_KR,
        LOCALE_LA   : Messages.LOCALE_LA,
        LOCALE_LV_LV: Messages.LOCALE_LV_LV,
        LOCALE_NB_NO: Messages.LOCALE_NB_NO,
        LOCALE_NL_BE: Messages.LOCALE_NL_BE,
        LOCALE_NL_NL: Messages.LOCALE_NL_NL,
        LOCALE_NO_NO: Messages.LOCALE_NO_NO,
        LOCALE_PL_PL: Messages.LOCALE_PL_PL,
        LOCALE_PT_BR: Messages.LOCALE_PT_BR,
        LOCALE_PT_PT: Messages.LOCALE_PT_PT,
        LOCALE_RO_RO: Messages.LOCALE_RO_RO,
        LOCALE_RU_RU: Messages.LOCALE_RU_RU,
        LOCALE_SK_SK: Messages.LOCALE_SK_SK,
        LOCALE_SQ_AL: Messages.LOCALE_SQ_AL,
        LOCAL_SR_ME : Messages.LOCALE_SR_ME,
        LOCALE_SR_RS: Messages.LOCALE_SR_RS,
        LOCALE_SW_KE: Messages.LOCALE_SW_KE,
        LOCALE_TA   : Messages.LOCALE_TA,
        LOCALE_TH_TH: Messages.LOCALE_TH_TH,
        LOCALE_TR_TR: Messages.LOCALE_TR_TR,
        LOCALE_VI_VN: Messages.LOCALE_VI_VN,
        LOCALE_ZH_CN: Messages.LOCALE_ZH_CN,
        LOCALE_ZH_HK: Messages.LOCALE_ZH_HK,
        LOCALE_ZH_TW: Messages.LOCALE_ZH_TW
    }

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

    country_msg_map: Dict[str, int] = {
        COUNTRY_AL: 32340,
        COUNTRY_AM: 32341,
        COUNTRY_AU: 32342,
        COUNTRY_BE: 32343,
        COUNTRY_BR: 32344,
        COUNTRY_CA: 32345,
        COUNTRY_CN: 32346,
        COUNTRY_DE: 32347,
        COUNTRY_DK: 32348,
        COUNTRY_EO: 32349,
        COUNTRY_ES: 32350,
        COUNTRY_FI: 32351,
        COUNTRY_FR: 32352,
        COUNTRY_GB: 32353,
        COUNTRY_GR: 32354,
        COUNTRY_HK: 32355,
        COUNTRY_HR: 32356,
        COUNTRY_HU: 32357,
        COUNTRY_ID: 32358,
        COUNTRY_IE: 32359,
        COUNTRY_IN: 32360,
        COUNTRY_IS: 32361,
        COUNTRY_IT: 32362,
        COUNTRY_JA: 32363,
        COUNTRY_KE: 32364,
        COUNTRY_KR: 32365,
        COUNTRY_LV: 32366,
        COUNTRY_ME: 32367,
        COUNTRY_MX: 32368,
        COUNTRY_NL: 32369,
        COUNTRY_NO: 32370,
        COUNTRY_PL: 32371,
        COUNTRY_PT: 32372,
        COUNTRY_RO: 32373,
        COUNTRY_RS: 32374,
        COUNTRY_RU: 32375,
        COUNTRY_SA: 32376,
        COUNTRY_SK: 32377,
        COUNTRY_TA: 32378,
        COUNTRY_TH: 32379,
        COUNTRY_TR: 32380,
        COUNTRY_US: 32381,
        COUNTRY_VN: 32382,
        COUNTRY_ZA: 32383
    }

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

    lang_msg_map: Dict[str, int] = {
        LANG_AF: 32384,
        LANG_AR: 32385,
        LANG_BS: 32386,
        LANG_CA: 32387,
        LANG_CS: 32388,
        LANG_CY: 32389,
        LANG_DA: 32390,
        LANG_DE: 32391,
        LANG_EL: 32392,
        LANG_EN: 32393,
        LANG_EO: 32394,
        LANG_ES: 32395,
        LANG_FI: 32396,
        LANG_FR: 32397,
        LANG_HI: 32398,
        LANG_HR: 32399,
        LANG_HU: 32400,
        LANG_HY: 32401,
        LANG_ID: 32402,
        LANG_IS: 32403,
        LANG_IT: 32404,
        LANG_JA: 32405,
        LANG_KO: 32406,
        LANG_LA: 32407,
        LANG_LV: 32408,
        LANG_NB: 32409,
        LANG_NL: 32410,
        LANG_NO: 32411,
        LANG_PL: 32412,
        LANG_PT: 32413,
        LANG_RO: 32414,
        LANG_RU: 32415,
        LANG_SK: 32416,
        LANG_SQ: 32417,
        LANG_SR: 32418,
        LANG_SW: 32419,
        LANG_TA: 32420,
        LANG_TH: 32421,
        LANG_TR: 32422,
        LANG_VI: 32423,
        LANG_ZH: 32424
    }


# Most settings are stored using TTS-defined values. Each user
# of the settings use a validator & constraints to translate to and
# from TTS values. This is done to make it easier to share values
# between engines, players, etc.

class Players(BaseSettingsConstants):
    TTS: Final[str] = 'tts'
    NONE: Final[str] = 'Unknown Player'
    SFX: Final[str] = 'PlaySFX'
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
        NONE        : Messages.PLAYER_NONE,
        SFX         : Messages.PLAYER_SFX,
        WINDOWS     : Messages.PLAYER_WINDOWS,
        APLAY       : Messages.PLAYER_APLAY,
        PAPLAY      : Messages.PLAYER_PAPLAY,
        AFPLAY      : Messages.PLAYER_AFPLAY,
        SOX         : Messages.PLAYER_SOX,
        MPLAYER     : Messages.PLAYER_MPLAYER,
        MPV         : Messages.PLAYER_MPV,
        MPG321      : Messages.PLAYER_MPG321,
        MPG123      : Messages.PLAYER_MPG123,
        MPG321_OE_PI: Messages.PLAYER_MPG321_OE_PI,
        INTERNAL    : Messages.PLAYER_INTERNAL
    }


class PlayerMode(StrEnum):
    SLAVE_FILE = 'slave_file'
    SLAVE_PIPE = 'slave_pipe'
    FILE = 'file'
    PIPE = 'pipe'
    ENGINE_SPEAK = 'engine_speak'


class Converters(BaseSettingsConstants):
    NONE: Final[str] = 'Unknown Player'
    WINDOWS: Final[str] = 'Windows'
    SOX: Final[str] = 'sox'
    MPLAYER: Final[str] = 'mplayer'
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
