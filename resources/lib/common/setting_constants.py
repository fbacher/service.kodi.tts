# -*- coding: utf-8 -*-

from common.messages import Messages
from common.settings import Settings


class BaseSettingsConstants:

    settings_map = {}

    @classmethod
    def get_label(cls, setting_id):
        msg_handle = cls.settings_map.get(setting_id, None)
        label = Messages.get_msg(msg_handle)
        return label

    @classmethod
    def get_msg_handle(cls, setting_id):
        return cls.settings_map.get(setting_id, None)


class Backends(BaseSettingsConstants):
    AUTO_ID = 'auto'
    ESPEAK_ID = 'eSpeak'
    FESTIVAL_ID = 'Festival'
    FLITE_ID = 'Flite'
    PICO_TO_WAVE_ID ='pico2wave'
    RECITE_ID = 'recite'
    RESPONSIVE_VOICE_ID = 'ResponsiveVoice'
    SPEECH_DISPATCHER_ID = 'Speech-Dispatcher'

    settings_map = {
        AUTO_ID: Messages.AUTO,
        ESPEAK_ID: Messages.BACKEND_ESPEAK,
        FESTIVAL_ID: Messages.BACKEND_FESTIVAL,
        FLITE_ID: Messages.BACKEND_FLITE,
        RESPONSIVE_VOICE_ID: Messages.BACKEND_RESPONSIVE_VOICE,
    }


class Languages(BaseSettingsConstants):

    LOCALE_AF = 'af'
    LOCALE_AF_ZA = 'af-ZA'
    LOCALE_AR_SA = 'ar-SA'
    LOCALE_BS = 'bs'
    LOCALE_CA = 'ca'
    LOCALE_CA_ES = 'ca-ES'
    LOCALE_CS = 'cs'
    LOCALE_CY = 'cy'
    LOCALE_DA_DK = 'da-DK'
    LOCALE_DE_DE = 'de-DE'
    LOCALE_EL_GR = 'el-GR'
    LOCALE_EN_AU = 'en-AU'
    LOCALE_EN_GB = 'en-GB'
    LOCALE_EN_IE = 'en-IE'
    LOCALE_EN_IN = 'en-IN'
    LOCALE_EN_US = 'en-US'
    LOCALE_EN_ZA = 'en-ZA'
    LOCALE_EO = 'eo'
    LOCALE_ES_ES = 'es-ES'
    LOCALE_ES = 'es'
    LOCALE_ES_MX = 'es-MX'
    LOCALE_ES_US = 'es-US'
    LOCALE_FI_FI = 'fi-FI'
    LOCALE_FR_BE = 'fr-BE'
    LOCALE_FR_FR = 'fr-FR'
    LOCALE_FR_CA = 'fr-CA'
    LOCALE_FR = 'fr'
    LOCALE_HI = 'hi'
    LOCALE_HI_IN = 'hi-IN'
    LOCALE_HR_HR = 'hr-HR'
    LOCALE_HU_HU = 'hu-HU'
    LOCALE_HY_AM = 'hy-AM'
    LOCALE_ID_ID = 'id-ID'
    LOCALE_IS_IS = 'is-IS'
    LOCALE_IT_IT = 'it-IT'
    LOCALE_JA_JP = 'ja-JP'
    LOCALE_KO_KR = 'ko-KR'
    LOCALE_LA = 'la'
    LOCALE_LV_LV = 'lv-LV'
    LOCALE_NB_NO = 'nb-NO'
    LOCALE_NL_BE = 'nl-BE'
    LOCALE_NL_NL = 'nl-NL'
    LOCALE_NO_NO = 'no-NO'
    LOCALE_PL_PL = 'pl-PL'
    LOCALE_PT_BR = 'pt-BR'
    LOCALE_PT_PT = 'pt-PT'
    LOCALE_RO_RO = 'ro-RO'
    LOCALE_RU_RU = 'ru-RU'
    LOCALE_SK_SK = 'sk-SK'
    LOCALE_SQ_AL = 'sq-AL'
    LOCAL_SR_ME = 'sr-ME'
    LOCALE_SR_RS = 'sr-RS'
    LOCALE_SW_KE = 'sw-KE'
    LOCALE_TA = 'ta'
    LOCALE_TH_TH = 'th-TH'
    LOCALE_TR_TR = 'tr-TR'
    LOCALE_VI_VN = 'vi-VN'
    LOCALE_ZH_CN = 'zh-CN'
    LOCALE_ZH_HK = 'zh-HK'
    LOCALE_ZH_TW = 'zh-TW'

    settings_map = {
        LOCALE_AF: Messages.LOCALE_AF,
        LOCALE_AF_ZA: Messages.LOCALE_AF_ZA,
        LOCALE_AR_SA: Messages.LOCALE_AR_SA,
        LOCALE_BS: Messages.LOCALE_BS,
        LOCALE_CA: Messages.LOCALE_CA,
        LOCALE_CA_ES: Messages.LOCALE_CA_ES,
        LOCALE_CS: Messages.LOCALE_CS,
        LOCALE_CY: Messages.LOCALE_CY,
        LOCALE_DA_DK: Messages.LOCALE_DA_DK,
        LOCALE_DE_DE: Messages.LOCALE_DE_DE,
        LOCALE_EL_GR: Messages.LOCALE_EL_GR,
        LOCALE_EN_AU: Messages.LOCALE_EN_AU,
        LOCALE_EN_GB: Messages.LOCALE_EN_GB,
        LOCALE_EN_IE: Messages.LOCALE_EN_IE,
        LOCALE_EN_IN: Messages.LOCALE_EN_IN,
        LOCALE_EN_US: Messages.LOCALE_EN_US,
        LOCALE_EN_ZA: Messages.LOCALE_EN_ZA,
        LOCALE_EO: Messages.LOCALE_EO,
        LOCALE_ES_ES: Messages.LOCALE_ES_ES,
        LOCALE_ES: Messages.LOCALE_ES,
        LOCALE_ES_MX: Messages.LOCALE_ES_MX,
        LOCALE_ES_US: Messages.LOCALE_ES_US,
        LOCALE_FI_FI: Messages.LOCALE_FI_FI,
        LOCALE_FR_BE: Messages.LOCALE_FR_BE,
        LOCALE_FR_FR: Messages.LOCALE_FR_FR,
        LOCALE_FR_CA: Messages.LOCALE_FR_CA,
        LOCALE_FR: Messages.LOCALE_FR,
        LOCALE_HI: Messages.LOCALE_HI,
        LOCALE_HI_IN: Messages.LOCALE_HI_IN,
        LOCALE_HR_HR: Messages.LOCALE_HR_HR,
        LOCALE_HU_HU: Messages.LOCALE_HU_HU,
        LOCALE_HY_AM: Messages.LOCALE_HY_AM,
        LOCALE_ID_ID: Messages.LOCALE_ID_ID,
        LOCALE_IS_IS: Messages.LOCALE_IS_IS,
        LOCALE_IT_IT: Messages.LOCALE_IT_IT,
        LOCALE_JA_JP: Messages.LOCALE_JA_JP,
        LOCALE_KO_KR: Messages.LOCALE_KO_KR,
        LOCALE_LA: Messages.LOCALE_LA,
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
        LOCAL_SR_ME: Messages.LOCAL_SR_ME,
        LOCALE_SR_RS: Messages.LOCALE_SR_RS,
        LOCALE_SW_KE: Messages.LOCALE_SW_KE,
        LOCALE_TA: Messages.LOCALE_TA,
        LOCALE_TH_TH: Messages.LOCALE_TH_TH,
        LOCALE_TR_TR: Messages.LOCALE_TR_TR,
        LOCALE_VI_VN: Messages.LOCALE_VI_VN,
        LOCALE_ZH_CN: Messages.LOCALE_ZH_CN,
        LOCALE_ZH_HK: Messages.LOCALE_ZH_HK,
        LOCALE_ZH_TW: Messages.LOCALE_ZH_TW
    }


class Players(BaseSettingsConstants):
    NONE = 'Unknown Player'
    SFX = 'PlaySFX'
    WINDOWS = 'Windows'
    APLAY = 'aplay'
    PAPLAY = 'paplay'
    AFPLAY = 'afplay'
    SOX = 'sox'
    MPLAYER = 'mplayer'
    MPG321 = 'mpg321'
    MPG123 = 'mpg123'
    MPG321_OE_PI = 'mpg321_OE_Pi'

    # Built-in players

    INTERNAL = 'internal'

    settings_map = {
        NONE: Messages.PLAYER_NONE,
        SFX: Messages.PLAYER_SFX,
        WINDOWS: Messages.PLAYER_WINDOWS,
        APLAY: Messages.PLAYER_APLAY,
        PAPLAY: Messages.PLAYER_PAPLAY,
        AFPLAY: Messages.PLAYER_AFPLAY,
        SOX: Messages.PLAYER_SOX,
        MPLAYER: Messages.PLAYER_MPLAYER,
        MPG321: Messages.PLAYER_MPG321,
        MPG123: Messages.PLAYER_MPG123,
        MPG321_OE_PI: Messages.PLAYER_MPG321_OE_PI,
        INTERNAL: Messages.PLAYER_INTERNAL,
    }


class Genders(BaseSettingsConstants):
    MALE = 'male'
    FEMALE = 'female'
    UNKNOWN = 'unknown'

    settings_map = {
        MALE: Messages.GENDER_MALE,
        FEMALE: Messages.GENDER_FEMALE,
        UNKNOWN: Messages.GENDER_UNKNOWN
    }

class Misc(BaseSettingsConstants):
    PITCH = Settings.PITCH

    settings_map = {
        PITCH: Messages.MISC_PITCH
    }
