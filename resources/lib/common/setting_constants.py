# -*- coding: utf-8 -*-

from enum import Enum
try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from common import *

from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from common.messages import Message, Messages


class BaseSettingsConstants:

    settings_map: Dict[int, Message] = {}

    @classmethod
    def get_label(cls, setting_id: int) -> str:
        msg_handle = cls.settings_map.get(setting_id, setting_id)
        label = Messages.get_msg(msg_handle)
        return label

    @classmethod
    def get_msg_handle(cls, setting_id: int) -> Message:
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
    RECITE_ID: Final[str] = Services.RECITE_ID
    RESPONSIVE_VOICE_ID: Final[str] = Services.RESPONSIVE_VOICE_ID
    GOOGLE_ID: Final[str] = Services.GOOGLE_ID
    SPEECH_DISPATCHER_ID: Final[str] = Services.SPEECH_DISPATCHER_ID
    EXPERIMENTAL_ENGINE_ID: Final[str] = Services.EXPERIMENTAL_ENGINE_ID
    SAPI_ID: Final[str] = Services.SAPI_ID

    ALL_ENGINE_IDS: List[str] = [
        AUTO_ID,
        ESPEAK_ID,
        EXPERIMENTAL_ENGINE_ID,
        FESTIVAL_ID,
        FLITE_ID,
        GOOGLE_ID,
        INTERNAL_ID,
        LOG_ONLY_ID,
        PICO_TO_WAVE_ID,
        RECITE_ID,
        RESPONSIVE_VOICE_ID,
        SAPI_ID,
        SPEECH_DISPATCHER_ID
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
        GOOGLE_ID             : 'goo'
    }


class Languages(BaseSettingsConstants):

    LOCALE_AF: Final[str] = 'af'
    LOCALE_AF_ZA: Final[str] = 'af-ZA'
    LOCALE_AR_SA: Final[str] = 'ar-SA'
    LOCALE_BS: Final[str] = 'bs'
    LOCALE_CA: Final[str] = 'ca'
    LOCALE_CA_ES: Final[str] = 'ca-ES'
    LOCALE_CS: Final[str] = 'cs'
    LOCALE_CY: Final[str] = 'cy'
    LOCALE_DA_DK: Final[str] = 'da-DK'
    LOCALE_DE_DE: Final[str] = 'de-DE'
    LOCALE_EL_GR: Final[str] = 'el-GR'
    LOCALE_EN_AU: Final[str] = 'en-AU'
    LOCALE_EN_GB: Final[str] = 'en-GB'
    LOCALE_EN_IE: Final[str] = 'en-IE'
    LOCALE_EN_IN: Final[str] = 'en-IN'
    LOCALE_EN_US: Final[str] = 'en-US'
    LOCALE_EN_ZA: Final[str] = 'en-ZA'
    LOCALE_EO: Final[str] = 'eo'
    LOCALE_ES_ES: Final[str] = 'es-ES'
    LOCALE_ES: Final[str] = 'es'
    LOCALE_ES_MX: Final[str] = 'es-MX'
    LOCALE_ES_US: Final[str] = 'es-US'
    LOCALE_FI_FI: Final[str] = 'fi-FI'
    LOCALE_FR_BE: Final[str] = 'fr-BE'
    LOCALE_FR_FR: Final[str] = 'fr-FR'
    LOCALE_FR_CA: Final[str] = 'fr-CA'
    LOCALE_FR: Final[str] = 'fr'
    LOCALE_HI: Final[str] = 'hi'
    LOCALE_HI_IN: Final[str] = 'hi-IN'
    LOCALE_HR_HR: Final[str] = 'hr-HR'
    LOCALE_HU_HU: Final[str] = 'hu-HU'
    LOCALE_HY_AM: Final[str] = 'hy-AM'
    LOCALE_ID_ID: Final[str] = 'id-ID'
    LOCALE_IS_IS: Final[str] = 'is-IS'
    LOCALE_IT_IT: Final[str] = 'it-IT'
    LOCALE_JA_JP: Final[str] = 'ja-JP'
    LOCALE_KO_KR: Final[str] = 'ko-KR'
    LOCALE_LA: Final[str] = 'la'
    LOCALE_LV_LV: Final[str] = 'lv-LV'
    LOCALE_NB_NO: Final[str] = 'nb-NO'
    LOCALE_NL_BE: Final[str] = 'nl-BE'
    LOCALE_NL_NL: Final[str] = 'nl-NL'
    LOCALE_NO_NO: Final[str] = 'no-NO'
    LOCALE_PL_PL: Final[str] = 'pl-PL'
    LOCALE_PT_BR: Final[str] = 'pt-BR'
    LOCALE_PT_PT: Final[str] = 'pt-PT'
    LOCALE_RO_RO: Final[str] = 'ro-RO'
    LOCALE_RU_RU: Final[str] = 'ru-RU'
    LOCALE_SK_SK: Final[str] = 'sk-SK'
    LOCALE_SQ_AL: Final[str] = 'sq-AL'
    LOCAL_SR_ME: Final[str] = 'sr-ME'
    LOCALE_SR_RS: Final[str] = 'sr-RS'
    LOCALE_SW_KE: Final[str] = 'sw-KE'
    LOCALE_TA: Final[str] = 'ta'
    LOCALE_TH_TH: Final[str] = 'th-TH'
    LOCALE_TR_TR: Final[str] = 'tr-TR'
    LOCALE_VI_VN: Final[str] = 'vi-VN'
    LOCALE_ZH_CN: Final[str] = 'zh-CN'
    LOCALE_ZH_HK: Final[str] = 'zh-HK'
    LOCALE_ZH_TW: Final[str] = 'zh-TW'

    settings_map = {
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
        LOCAL_SR_ME : Messages.LOCAL_SR_ME,
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
        MPG321      : Messages.PLAYER_MPG321,
        MPG123      : Messages.PLAYER_MPG123,
        MPG321_OE_PI: Messages.PLAYER_MPG321_OE_PI,
        INTERNAL    : Messages.PLAYER_INTERNAL
    }


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


class GenderSettingsMap(BaseSettingsConstants):
    settings_map = {
        Genders.MALE   : Messages.GENDER_MALE,
        Genders.FEMALE : Messages.GENDER_FEMALE,
        Genders.UNKNOWN: Messages.GENDER_UNKNOWN
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
