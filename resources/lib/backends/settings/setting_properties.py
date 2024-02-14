from __future__ import annotations  # For union operator |

from enum import Enum

import xbmcvfs

from common import *

from backends.settings.service_types import Services


class SettingType(Enum):
    BOOLEAN_TYPE = 'BOOLEAN_TYPE'
    BOOLEAN_LIST_TYPE = 'BOOLEAN_LIST_TYPE'
    FLOAT_TYPE = 'FLOAT_TYPE'
    FLOAT_LIST_TYPE = 'FLOAT_LIST_TYPE'
    INTEGER_TYPE = 'INTEGER_TYPE'
    INTEGER_LIST_TYPE = 'INTEGER_LIST_TYPE'
    STRING_TYPE = 'STRING_TYPE'
    STRING_LIST_TYPE = 'STRING_LIST_TYPE'


class SettingsProperties:  # (ISettings):
    # Must list these engines in preference order. Or at least the first few
    # should be in this order.
    AUTO_ID: Final[str] = Services.AUTO_ENGINE_ID
    ESPEAK_ID: Final[str] = Services.ESPEAK_ID
    FESTIVAL_ID: Final[str] = Services.FESTIVAL_ID
    FLITE_ID: Final[str] = Services.FLITE_ID
    INTERNAL_ID: Final[str] = Services.INTERNAL_PLAYER_ID
    PICO_TO_WAVE_ID: Final[str] = Services.PICO_TO_WAVE_ID
    RECITE_ID: Final[str] = Services.RECITE_ID
    RESPONSIVE_VOICE_ID: Final[str] = Services.RESPONSIVE_VOICE_ID
    SPEECH_DISPATCHER_ID: Final[str] = Services.SPEECH_DISPATCHER_ID
    EXPERIMENTAL_ENGINE_ID: Final[str] = Services.EXPERIMENTAL_ENGINE_ID

    ADDONS_MD5: Final[str] = 'addons_MD5'
    API_KEY: Final[str] = 'api_key'
    AUTO_ITEM_EXTRA: Final[str] = 'auto_item_extra'

    # int seconds Time to wait before saying something extra in seconds

    AUTO_ITEM_EXTRA_DELAY: Final[str] = 'auto_item_extra_delay'
    ENGINE: Final[str] = 'engine'
    ENGINE_DEFAULT: Final[str] = AUTO_ID
    BACKGROUND_PROGRESS_INTERVAL: Final[str] = 'background_progress_interval'
    CACHE_PATH: Final[str] = 'cache_path'
    CACHE_EXPIRATION_DAYS: Final[str] = 'cache_expiration_days'
    CACHE_SPEECH: Final[str] = 'cache_speech'
    CACHE_VOICE_FILES: Final[str] = 'cache_voice_files'
    CAPITAL_RECOGNITION: Final[str] = 'capital_recognition'
    CONVERTER: Final[str] = 'converter'
    DEBUG_LOG_LEVEL: Final[str] = 'debug_log_level'
    DELAY_VOICING: Final[str] = 'delay_voicing'
    DISABLE_BROKEN_SERVICES: Final[str] = 'disable_broken_services'
    # TODO: Change settings like output_via_espeak to be output <string value>
    # ENGINE_SPEAKS: Final[str] = 'engine_speak'  # Voicing engine also speaks
    GENDER: Final[str] = 'gender'
    GENDER_VISIBLE: Final[str] = 'gender_visible'
    GUI: Final[str] = 'gui'
    LANGUAGE: Final[str] = 'language'
    MODULE: Final[str] = 'module'
    OUTPUT_VIA: Final[str] = 'output_via'
    OUTPUT_VISIBLE: Final[str] = 'output_visible'
    OVERRIDE_POLL_INTERVAL: Final[str] = 'override_poll_interval'
    PIPE: Final[str] = 'pipe'  # Engine to pipe speech to a player
    PITCH: Final[str] = 'pitch'
    PLAYER: Final[str] = 'player'  # Specifies the player
    PLAYER_VOLUME: Final[str] = 'player_volume'
    PLAYER_PITCH: Final[str] = 'player_pitch'
    PLAYER_SLAVE: Final[str] = 'player_slave'
    PLAYER_SPEED: Final[str] = 'player_speed'
    POLL_INTERVAL: Final[str] = 'poll_interval'
    PUNCTUATION: Final[str] = 'punctuation'
    READER_ON: Final[str] = 'reader_on'
    REMOTE_PITCH: Final[str] = 'remote_pitch'
    REMOTE_SERVER: Final[str] = 'remote_server'
    REMOTE_SPEED: Final[str] = 'remote_speed'
    REMOTE_VOLUME: Final[str] = 'remote_volume'
    SETTINGS_BEING_CONFIGURED: Final[str] = 'settings_being_configured'
    SETTINGS_DIGEST: Final[str] = 'settings_digest'
    # SETTINGS_LAST_CHANGED: Final[str] = 'settings_last_changed'
    SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: Final[
        str] = 'speak_background_progress_during_media'
    SPEAK_BACKGROUND_PROGRESS: Final[str] = 'speak_background_progress'
    SPEAK_LIST_COUNT: Final[str] = 'speak_list_count'
    SPEAK_ON_SERVER: Final[str] = 'speak_on_server'
    SPEAK_VIA_KODI: Final[str] = 'speak_via_kodi'
    SPEECH_DISPATCHER: Final[str] = 'Speech-Dispatcher'
    SPEED: Final[str] = 'speed'
    SPEED_ENABLED: Final[str] = 'speed_enabled'
    SPEED_VISIBLE: Final[str] = 'speed_visible'
    SPELLING: Final[str] = 'spelling'
    SERVICE_ID: Final[str] = 'id'
    TTS_SERVICE: Final[str] = 'tts'
    TTSD_HOST: Final[str] = 'ttsd_host'
    TTSD_PORT: Final[str] = 'ttsd_port'
    USE_AOSS: Final[str] = 'use_aoss'
    USE_TEMPFS: Final[str] = 'use_tmpfs'
    VERSION: Final[str] = 'version'
    VOICE: Final[str] = 'voice'
    VOICE_TTSD: Final[str] = 'voice_ttsd'
    VOICE_VISIBLE: Final[str] = 'voice_visible'
    VOLUME: Final[str] = 'volume'
    VOLUME_VISIBLE: Final[str] = 'volume_visible'

    API_KEY_DEFAULT: Final[str] = ''
    CACHE_PATH_DEFAULT: Final[str] = xbmcvfs.translatePath(
        'special://userdata/addon_data/service.kodi.tts/cache')
    CACHE_EXPIRATION_DEFAULT: Final[int] = 365
    CACHE_SPEECH_DEFAULT: Final[bool] = False
    ENGINE_SPEEK_DEFAULT = None
    GENDER_DEFAULT: Final[str] = 'none'
    LANGUAGE_DEFAULT: Final[str] = 'none'
    PIPE_DEFAULT = None
    PITCH_DEFAULT = None
    SPEED_DEFAULT = None
    VOICE_DEFAULT: Final[str] = 'none'
    VOLUME_DEFAULT = None

    TOP_LEVEL_SETTINGS: List[str] = [
        ENGINE,
        TTS_SERVICE
    ]

    TTS_SETTINGS: List[str] = [
        AUTO_ITEM_EXTRA,
        AUTO_ITEM_EXTRA_DELAY,
        BACKGROUND_PROGRESS_INTERVAL,
        DISABLE_BROKEN_SERVICES,
        SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
        SPEAK_BACKGROUND_PROGRESS,
        CACHE_PATH,   # Move to engine specific
        CACHE_EXPIRATION_DAYS,  # Move to engine specific
        CACHE_VOICE_FILES,
        ADDONS_MD5,
        # DEBUG_LOGGING,  # Boolean needed to toggle visibility
        DEBUG_LOG_LEVEL,  # Merge into Logging, get rid of verbose_logging, etc
        GENDER_VISIBLE,
        GUI,
        #  SPEECH_DISPATCHER,
        OUTPUT_VIA,
        OUTPUT_VISIBLE,
        OVERRIDE_POLL_INTERVAL,
        PLAYER_SLAVE, # Probably not global (.tts)
        POLL_INTERVAL,
        READER_ON,
        SETTINGS_BEING_CONFIGURED,
        SETTINGS_DIGEST,
        # SETTINGS_LAST_CHANGED,
        SPEAK_LIST_COUNT,
        SPEAK_VIA_KODI,
        SPEED_VISIBLE,
        TTSD_HOST,
        TTSD_PORT,
        USE_TEMPFS,
        VERSION,
        VOICE_VISIBLE,
        VOLUME_VISIBLE
    ]

    # Logically, ENGINE_SPEAK and PIPE should be combined into an enum of
    # three values instructing the engine what to do with speech that it produces:
    #   WRITE_TO_FILE, SPEAK (engine itself speaks), PIPE (to some other player).
    #
    # However, we have two settings: ENGINE_SPEAK and PIPE. ENGINE_SPEAK takes
    # precedence. If PIPE is set to 'pipe', then it is considered True, else
    # the engine is to write to file.

    UNKNOWN_VALUE = 'unknown'

    # Most settings are associated with a player or a voice engine. Such
    # settings have the player or engine name appended to the setting name.
    #
    # Some settings are not associated with a player or engine. The setting
    # names are not modified. Such settings are referred to here as
    # 'top_level_settings'

    ALL_SETTINGS: List[str] = [
        ENGINE,  # Leave this as the FIRST setting
        ADDONS_MD5,
        API_KEY,
        AUTO_ITEM_EXTRA,
        # int seconds Time to wait before saying something extra in seconds
        AUTO_ITEM_EXTRA_DELAY,
        BACKGROUND_PROGRESS_INTERVAL,
        CACHE_PATH,
        CACHE_EXPIRATION_DAYS,
        CACHE_SPEECH,
        CACHE_VOICE_FILES,
        CAPITAL_RECOGNITION,
        CONVERTER,
        # DEBUG_LOGGING,
        DEBUG_LOG_LEVEL,
        DELAY_VOICING,
        DISABLE_BROKEN_SERVICES,
        GENDER,
        GENDER_VISIBLE,
        GUI,
        LANGUAGE,
        MODULE,
        OUTPUT_VIA,
        OUTPUT_VISIBLE,
        OVERRIDE_POLL_INTERVAL,
        PIPE,
        PITCH,
        PLAYER,
        PLAYER_VOLUME,
        PLAYER_PITCH,
        PLAYER_SLAVE,
        PLAYER_SPEED,
        POLL_INTERVAL,
        PUNCTUATION,
        READER_ON,
        REMOTE_PITCH,
        REMOTE_SPEED,
        REMOTE_VOLUME,
        SETTINGS_DIGEST,
        SETTINGS_BEING_CONFIGURED,
        # SETTINGS_LAST_CHANGED,
        SPEECH_DISPATCHER,
        SERVICE_ID,
        SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
        SPEAK_BACKGROUND_PROGRESS,
        SPEAK_LIST_COUNT,
        SPEAK_ON_SERVER,
        SPEAK_VIA_KODI,
        SPEED,
        SPEED_ENABLED,
        SPEED_VISIBLE,
        SPELLING,
        TTS_SERVICE,
        TTSD_HOST,
        TTSD_PORT,
        USE_AOSS,
        USE_TEMPFS,
        VERSION,
        VOICE,
        VOICE_VISIBLE,
        VOLUME
    ]

    SettingTypes: Dict[str, SettingType] = {}

    @classmethod
    def init(cls):
        cls.SettingTypes = {
            cls.ADDONS_MD5                            : SettingType.STRING_TYPE,
            cls.API_KEY                               : SettingType.STRING_TYPE,
            cls.AUTO_ITEM_EXTRA                       : SettingType.BOOLEAN_TYPE,
            cls.AUTO_ITEM_EXTRA_DELAY                 : SettingType.INTEGER_TYPE,
            cls.ENGINE                                : SettingType.STRING_TYPE,
            cls.BACKGROUND_PROGRESS_INTERVAL          : SettingType.INTEGER_TYPE,
            cls.CACHE_PATH                            : SettingType.STRING_TYPE,
            cls.CACHE_EXPIRATION_DAYS                 : SettingType.INTEGER_TYPE,
            cls.CACHE_SPEECH                          : SettingType.BOOLEAN_TYPE,
            cls.CACHE_VOICE_FILES                     : SettingType.BOOLEAN_TYPE,
            cls.CAPITAL_RECOGNITION                   : SettingType.BOOLEAN_TYPE,
            cls.CONVERTER                             : SettingType.STRING_TYPE,
            cls.DEBUG_LOG_LEVEL                       : SettingType.INTEGER_TYPE,
            cls.DELAY_VOICING                         : SettingType.BOOLEAN_TYPE,
            cls.DISABLE_BROKEN_SERVICES               : SettingType.BOOLEAN_TYPE,
            cls.GENDER                                : SettingType.STRING_TYPE,
            cls.GENDER_VISIBLE                        : SettingType.BOOLEAN_TYPE,
            cls.GUI                                   : SettingType.BOOLEAN_TYPE,
            cls.LANGUAGE                              : SettingType.STRING_TYPE,
            cls.MODULE                                : SettingType.STRING_TYPE,
            cls.OUTPUT_VIA                            : SettingType.STRING_TYPE,
            cls.OUTPUT_VISIBLE                        : SettingType.BOOLEAN_TYPE,
            cls.OVERRIDE_POLL_INTERVAL                : SettingType.BOOLEAN_TYPE,
            cls.PIPE                                  : SettingType.BOOLEAN_TYPE,
            cls.PITCH                                 : SettingType.INTEGER_TYPE,
            cls.PLAYER                                : SettingType.STRING_TYPE,
            cls.PLAYER_VOLUME                         : SettingType.INTEGER_TYPE,
            cls.PLAYER_PITCH                          : SettingType.INTEGER_TYPE,
            cls.PLAYER_SLAVE                          : SettingType.BOOLEAN_TYPE,
            cls.PLAYER_SPEED                          : SettingType.INTEGER_TYPE,
            cls.POLL_INTERVAL                         : SettingType.INTEGER_TYPE,
            cls.READER_ON                             : SettingType.BOOLEAN_TYPE,
            cls.REMOTE_PITCH                          : SettingType.INTEGER_TYPE,
            # Replaces engine.ttsd, etc.
            cls.REMOTE_SERVER                         : SettingType.STRING_TYPE,
            cls.REMOTE_SPEED                          : SettingType.INTEGER_TYPE,
            cls.REMOTE_VOLUME                         : SettingType.INTEGER_TYPE,
            cls.SERVICE_ID                            : SettingType.STRING_TYPE,
            cls.SETTINGS_BEING_CONFIGURED             : SettingType.BOOLEAN_TYPE,
            cls.SETTINGS_DIGEST                       : SettingType.STRING_TYPE,
            # cls.SETTINGS_LAST_CHANGED                 : SettingType.INTEGER_TYPE,
            cls.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: SettingType.BOOLEAN_TYPE,
            cls.SPEAK_BACKGROUND_PROGRESS             : SettingType.BOOLEAN_TYPE,
            cls.SPEAK_LIST_COUNT                      : SettingType.BOOLEAN_TYPE,
            cls.SPEAK_ON_SERVER                       : SettingType.BOOLEAN_TYPE,
            cls.SPEAK_VIA_KODI                        : SettingType.BOOLEAN_TYPE,
            cls.SPEECH_DISPATCHER                     : SettingType.STRING_TYPE,
            cls.SPEED                                 : SettingType.INTEGER_TYPE,
            cls.SPEED_ENABLED                         : SettingType.BOOLEAN_TYPE,
            cls.SPEED_VISIBLE                         : SettingType.BOOLEAN_TYPE,
            cls.TTSD_HOST                             : SettingType.STRING_TYPE,
            cls.TTSD_PORT                             : SettingType.INTEGER_TYPE,
            cls.USE_AOSS                              : SettingType.BOOLEAN_TYPE,
            cls.USE_TEMPFS                            : SettingType.BOOLEAN_TYPE,
            cls.VERSION                               : SettingType.STRING_TYPE,
            cls.VOICE                                 : SettingType.STRING_TYPE,
            cls.VOICE_VISIBLE                         : SettingType.BOOLEAN_TYPE,
            cls.VOLUME                                : SettingType.INTEGER_TYPE,
            cls.VOLUME_VISIBLE                        : SettingType.STRING_TYPE
        }


SettingsProperties.init()
