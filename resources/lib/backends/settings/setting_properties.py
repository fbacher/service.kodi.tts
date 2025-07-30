# coding=utf-8
from __future__ import annotations  # For union operator |

from enum import Enum

import xbmcvfs

from common import *

from backends.settings.service_types import Services, ServiceType, TTS_Type


class SettingType(Enum):
    BOOLEAN_TYPE = 'BOOLEAN_TYPE'
    BOOLEAN_LIST_TYPE = 'BOOLEAN_LIST_TYPE'
    FLOAT_TYPE = 'FLOAT_TYPE'
    FLOAT_LIST_TYPE = 'FLOAT_LIST_TYPE'
    INTEGER_TYPE = 'INTEGER_TYPE'
    INTEGER_LIST_TYPE = 'INTEGER_LIST_TYPE'
    STRING_TYPE = 'STRING_TYPE'
    STRING_LIST_TYPE = 'STRING_LIST_TYPE'


class SettingProp:  # (ISettings):
    # Must list these engines in preference order. Or at least the first few
    # should be in this order.
    #  AUTO_ID: Final[str] = Services.DEFAULT_ENGINE_ID.value
    ESPEAK_ID: Final[str] = Services.ESPEAK_ID.value
    FESTIVAL_ID: Final[str] = Services.FESTIVAL_ID.value
    FLITE_ID: Final[str] = Services.FLITE_ID.value
    INTERNAL_ID: Final[str] = Services.BUILT_IN_PLAYER_ID.value
    NO_ENGINE_ID: Final[str] = Services.NO_ENGINE_ID.value
    PICO_TO_WAVE_ID: Final[str] = Services.PICO_TO_WAVE_ID.value
    RECITE_ID: Final[str] = Services.RECITE_ID.value
    RESPONSIVE_VOICE_ID: Final[str] = Services.RESPONSIVE_VOICE_ID.value
    SPEECH_DISPATCHER_ID: Final[str] = Services.SPEECH_DISPATCHER_ID.value
    EXPERIMENTAL_ENGINE_ID: Final[str] = Services.EXPERIMENTAL_ENGINE_ID.value

    API_KEY: Final[str] = 'api_key'
    AVAILABILITY: Final[str] = 'availability'

    ENGINE: Final[str] = 'engine'
    #  ENGINE_DEFAULT: Final[str] = AUTO_ID
    CACHE_SPEECH: Final[str] = 'cache_speech'
    CACHE_SUFFIX: Final[str] = 'cache_suffix'
    CACHE_TOP: Final[str] = 'cache_top'
    #  CACHE_VOICE_FILES: Final[str] = 'cache_voice_files'
    CAPITAL_RECOGNITION: Final[str] = 'capital_recognition'
    COMMAND: Final[str] = 'command'
    COMMAND_PATH: Final[str] = 'command_path'
    CHANNELS: Final[str] = TTS_Type.CHANNELS.value
    TRANSCODER: Final[str] = 'transcoder'
    DELAY_VOICING: Final[str] = 'delay_voicing'
    # TODO: Change settings like output_via_espeak to be output <string value>
    # ENGINE_SPEAKS: Final[str] = 'engine_speak'  # Voicing engine also speaks
    GENDER: Final[str] = 'gender'
    GENDER_VISIBLE: Final[str] = 'gender_visible'
    #  GUI: Final[str] = 'gui'
    LANGUAGE: Final[str] = 'language'
    MODULE: Final[str] = 'module'
    # OUTPUT_VIA: Final[str] = 'output_via'
    #  OUTPUT_VISIBLE: Final[str] = 'output_visible'
    # PIPE: Final[str] = 'pipe'  # Engine to pipe speech to a player_key
    PLAYER_MODE: Final[str] = 'player_mode'  # How the engine communicates with player_key
    PITCH: Final[str] = 'pitch'
    PLAYER: Final[str] = 'player'  # Specifies the player_key
    PLAYER_VOLUME: Final[str] = 'player_volume'
    PLAYER_PITCH: Final[str] = 'player_pitch'
    PLAYER_SPEED: Final[str] = 'player_speed'
    PUNCTUATION: Final[str] = 'punctuation'
    REMOTE_PITCH: Final[str] = 'remote_pitch'
    REMOTE_SERVER: Final[str] = 'remote_server'
    REMOTE_SPEED: Final[str] = 'remote_speed'
    REMOTE_VOLUME: Final[str] = 'remote_volume'
    SETTINGS_BEING_CONFIGURED: Final[str] = 'settings_being_configured'
    #  SETTINGS_LAST_CHANGED: Final[str] = 'settings_last_changed'
    SPEECH_DISPATCHER: Final[str] = 'Speech-Dispatcher'
    SPEED_ENABLED: Final[str] = 'speed_enabled'
    #  SPEED_VISIBLE: Final[str] = 'speed_visible'
    SPELLING: Final[str] = 'spelling'
    SERVICE_ID: Final[str] = 'id'
    TTS_SERVICE: Final[str] = 'tts'
    #  TTSD_HOST: Final[str] = 'ttsd_host'
    #  TTSD_PORT: Final[str] = 'ttsd_port'
    USE_AOSS: Final[str] = 'use_aoss'
    VOICE: Final[str] = 'voice'
    VOICE_PATH: Final[str] = 'voice_path'
    VOICE_TTSD: Final[str] = 'voice_ttsd'
    VOICE_VISIBLE: Final[str] = 'voice_visible'
    VOLUME_VISIBLE: Final[str] = 'volume_visible'

    API_KEY_DEFAULT: Final[str] = ''
    AUDIO_FORMAT: Final[str] = 'audio_format'
    CACHE_EXPIRATION_DEFAULT: Final[int] = 365
    CACHE_SPEECH_DEFAULT: Final[bool] = False
    ENGINE_SPEEK_DEFAULT = None
    LANGUAGE_DEFAULT: Final[str] = 'none'
    PIPE_DEFAULT = None
    PITCH_DEFAULT = None
    SPEED_DEFAULT = None
    VOICE_DEFAULT: Final[str] = 'none'
    VOLUME_DEFAULT = None

    # From TTS_Type:
    ADDONS_MD5: Final[str] = TTS_Type.ADDONS_MD5.value
    AUTO_ITEM_EXTRA: Final[str] = TTS_Type.AUTO_ITEM_EXTRA.value

    # int seconds Time to wait before saying something extra in seconds
    AUTO_ITEM_EXTRA_DELAY: Final[str] = TTS_Type.AUTO_ITEM_EXTRA_DELAY.value
    BACKGROUND_PROGRESS_INTERVAL: Final[str] = TTS_Type.BACKGROUND_PROGRESS_INTERVAL.value
    CACHE_PATH: Final[str] = TTS_Type.CACHE_PATH.value
    CACHE_EXPIRATION_DAYS: Final[str] = TTS_Type.CACHE_EXPIRATION_DAYS.value
    START_CFG_GUI_ON_STARTUP: Final[str] = (
        TTS_Type.CONFIGURE_TTS_ON_STARTUP
    )
    CONFIGURE_DEPENDENCIES_ON_STARTUP: Final[str] = (
        TTS_Type.CONFIGURE_DEPENDENCIES_ON_STARTUP.value)
    CONFIGURE_KEYMAP_ON_STARTUP: Final[str] = TTS_Type.CONFIGURE_KEYMAP_ON_STARTUP.value
    CURRENT_ENGINE: Final[str] = TTS_Type.CURRENT_ENGINE.value
    DISABLE_BROKEN_SERVICES: Final[str] = TTS_Type.DISABLE_BROKEN_SERVICES.value
    CONFIG_HELP_ON_STARTUP: Final[str] = TTS_Type.HELP_CONFIG_ON_STARTUP.value
    INTRODUCTION_ON_STARTUP: Final[str] = TTS_Type.INTRODUCTION_ON_STARTUP.value
    SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: Final[str] = (
        TTS_Type.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA.value)
    SPEAK_BACKGROUND_PROGRESS: Final[str] = TTS_Type.SPEAK_BACKGROUND_PROGRESS.value
    SPEAK_ON_SERVER: Final[str] = TTS_Type.SPEAK_ON_SERVER.value
    #  CACHE_VOICE_FILES=
    # DEBUG_LOGGING=     # Boolean: Final[str] = TTS_Type.Boolean
    DEBUG_LOG_LEVEL: Final[str] = TTS_Type.DEBUG_LOG_LEVEL.value
    #Merge: Final[str] = TTS_Type.Merge
    EXTENDED_HELP_ON_STARTUP: Final[str] = TTS_Type.EXTENDED_HELP_ON_STARTUP.value
    # GUI=
    HINT_TEXT_ON_STARTUP: Final[str] = TTS_Type.HINT_TEXT_ON_STARTUP.value
    INITIAL_RUN: Final[str] = TTS_Type.INITIAL_RUN.value
    MAX_PHRASE_LENGTH: Final[str] = 'max_phrase_length'
    # OUTPUT_VIA=
    #  OUTPUT_VISIBLE=
    OVERRIDE_POLL_INTERVAL: Final[str] = TTS_Type.OVERRIDE_POLL_INTERVAL.value
    SERVICE_NAME: Final[str] = TTS_Type.SERVICE_NAME.value
    POLL_INTERVAL: Final[str] = TTS_Type.POLL_INTERVAL.value
    READER_ON: Final[str] = TTS_Type.READER_ON.value
    #  SETTINGS_DIGEST: Final[str] = TTS_Type.SETTINGS_DIGEST.value
    #  SETTINGS_LAST_CHANGED=
    SPEAK_LIST_COUNT: Final[str] = TTS_Type.SPEAK_LIST_COUNT.value
    #  SPEAK_VIA_KODI: Final[str] = TTS_Type.SPEAK_VIA_KODI.value
    #  SPEED_VISIBLE=
    #  TTSD_HOST=
    #  TTSD_PORT=
    VERSION: Final[str] = TTS_Type.VERSION.value
    SPEED: Final[str] = TTS_Type.SPEED.value
    VOLUME: Final[str] = TTS_Type.VOLUME.value

    TOP_LEVEL_SETTINGS: List[str] = [
        ENGINE,
        TTS_SERVICE
    ]

    TTS_SETTINGS: Dict[str, None] = {
        AUTO_ITEM_EXTRA                       : None,
        AUTO_ITEM_EXTRA_DELAY                 : None,
        BACKGROUND_PROGRESS_INTERVAL          : None,
        #  CACHE_PATH: None,
        CACHE_EXPIRATION_DAYS                 : None,
        CHANNELS                              : None,
        CONFIGURE_DEPENDENCIES_ON_STARTUP     : None,
        START_CFG_GUI_ON_STARTUP              : None,
        CURRENT_ENGINE                        : None,
        DISABLE_BROKEN_SERVICES               : None,
        SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: None,
        SPEAK_BACKGROUND_PROGRESS             : None,
        #  CACHE_VOICE_FILES: None,
        ADDONS_MD5                            : None,
        # DEBUG_LOGGING: None,    #  Boolean needed to toggle visibility
        DEBUG_LOG_LEVEL                       : None,  #  Merge into Logging: None, get rid of verbose_logging
        EXTENDED_HELP_ON_STARTUP              : None,
        # GUI: None,
        CONFIG_HELP_ON_STARTUP                : None,
        HINT_TEXT_ON_STARTUP                  : None,
        INITIAL_RUN                           : None,
        INTRODUCTION_ON_STARTUP               : None,
        # OUTPUT_VIA: None,
        #  OUTPUT_VISIBLE: None,
        OVERRIDE_POLL_INTERVAL                : None,
        POLL_INTERVAL                         : None,
        READER_ON                             : None,
        #  SETTINGS_BEING_CONFIGURED: None,
        #  SETTINGS_DIGEST: None,
        #  SETTINGS_LAST_CHANGED: None,
        SPEAK_LIST_COUNT: None,
        #  SPEAK_VIA_KODI: None,
        #  SPEED_VISIBLE: None,
        #  TTSD_HOST: None,
        #  TTSD_PORT: None,
        VERSION: None,
        SPEED: None,
        VOLUME: None
    }

    # Logically, ENGINE_SPEAK and PIPE should be combined into an enum of
    # three values instructing the engine what to do with speech that it produces:
    #   WRITE_TO_FILE, SPEAK (engine itself speaks), PIPE (to some other player_key).
    #
    # However, we have two settings: ENGINE_SPEAK and PIPE. ENGINE_SPEAK takes
    # precedence. If PIPE is set to 'pipe', then it is considered True, else
    # the engine is to write to file.

    UNKNOWN_VALUE = 'unknown'

    # Most settings are associated with a player_key or a voice engine. Such
    # settings have the player_key or engine name appended to the setting name.
    #
    # Some settings are not associated with a player_key or engine. The setting
    # names are not modified. Such settings are referred to here as
    # 'top_level_settings'

    ALL_SETTINGS: Dict[str, None] = {
        ENGINE: None,  # Leave this as the FIRST setting
        ADDONS_MD5: None,
        API_KEY: None,
        AUDIO_FORMAT: None,
        AUTO_ITEM_EXTRA: None,
        #  int seconds Time to wait before saying something extra in seconds
        AUTO_ITEM_EXTRA_DELAY            : None,
        BACKGROUND_PROGRESS_INTERVAL     : None,
        CACHE_PATH                       : None,
        CACHE_EXPIRATION_DAYS            : None,
        CACHE_SPEECH                     : None,
        #  CACHE_VOICE_FILES: None, Not used
        CAPITAL_RECOGNITION              : None,
        CHANNELS                         : None,
        COMMAND                          : None,
        COMMAND_PATH                     : None,
        START_CFG_GUI_ON_STARTUP         : None,
        CONFIGURE_DEPENDENCIES_ON_STARTUP: None,
        TRANSCODER                       : None,
        #  DEBUG_LOGGING: None,
        DEBUG_LOG_LEVEL                  : None,
        DELAY_VOICING                    : None,
        DISABLE_BROKEN_SERVICES          : None,
        EXTENDED_HELP_ON_STARTUP         : None,
        GENDER                           : None,
        #  GENDER_VISIBLE: None,
        # GUI: None,
        CONFIG_HELP_ON_STARTUP           : None,
        HINT_TEXT_ON_STARTUP             : None,
        LANGUAGE                         : None,
        MODULE                           : None,
        # OUTPUT_VIA: None,
        #  OUTPUT_VISIBLE: None,
        OVERRIDE_POLL_INTERVAL           : None,
        # PIPE: None,
        PITCH                            : None,
        PLAYER                           : None,
        PLAYER_VOLUME                    : None,
        PLAYER_PITCH: None,
        PLAYER_MODE: None,
        PLAYER_SPEED: None,
        POLL_INTERVAL: None,
        PUNCTUATION: None,
        READER_ON: None,
        REMOTE_PITCH: None,
        REMOTE_SPEED: None,
        REMOTE_VOLUME: None,
        #  SETTINGS_DIGEST: None,
        #  SETTINGS_BEING_CONFIGURED: None,
        #  SETTINGS_LAST_CHANGED: None,
        SPEECH_DISPATCHER: None,
        SERVICE_ID: None,
        SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: None,
        SPEAK_BACKGROUND_PROGRESS: None,
        SPEAK_LIST_COUNT: None,
        SPEAK_ON_SERVER: None,
        #  SPEAK_VIA_KODI: None,
        SPEED: None,
        SPEED_ENABLED: None,
        #  SPEED_VISIBLE: None,
        SPELLING: None,
        TTS_SERVICE: None,
        #  TTSD_HOST: None,
        #  TTSD_PORT: None,
        USE_AOSS: None,
        VERSION: None,
        VOICE: None,
        VOICE_PATH: None,
        #  VOICE_VISIBLE: None,
        VOLUME: None
    }

    ENGINE_SETTINGS: Dict[str, None] = {
        ENGINE: None,  # Leave this as the FIRST setting
        #  ADDONS_MD5: None,
        API_KEY: None,
        #  AUTO_ITEM_EXTRA: None,
        #  int seconds Time to wait before saying something extra in seconds
        # AUTO_ITEM_EXTRA_DELAY: None,
        AUDIO_FORMAT: None,
        #  CACHE_EXPIRATION_DAYS: None,
        CACHE_SPEECH: None,
        #  CACHE_VOICE_FILES: None, Not used
        CAPITAL_RECOGNITION: None,
        TRANSCODER: None,
        #  DEBUG_LOGGING: None,
        #  DEBUG_LOG_LEVEL: None,
        DELAY_VOICING: None,
        #  DISABLE_BROKEN_SERVICES: None,
        #  EXTENDED_HELP_ON_STARTUP: None,
        GENDER: None,
        # GENDER_VISIBLE: None,
        # GUI: None,
        # HINT_TEXT_ON_STARTUP: None,
        LANGUAGE: None,
        MODULE: None,
        # OUTPUT_VIA: None,
        #  OUTPUT_VISIBLE: None,
        # OVERRIDE_POLL_INTERVAL: None,
        # PIPE: None,
        PITCH: None,
        PLAYER: None,
        PLAYER_VOLUME: None,
        PLAYER_PITCH: None,
        PLAYER_MODE: None,
        # PLAYER_SPEED: None,
        # POLL_INTERVAL: None,
        PUNCTUATION: None,
        # READER_ON: None,
        REMOTE_PITCH: None,
        REMOTE_SPEED: None,
        REMOTE_VOLUME: None,
        # SETTINGS_DIGEST: None,
        #  SETTINGS_BEING_CONFIGURED: None,
        #  SETTINGS_LAST_CHANGED: None,
        SPEECH_DISPATCHER: None,
        SERVICE_ID: None,
        #  SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: None,
        #  SPEAK_BACKGROUND_PROGRESS: None,
        # SPEAK_LIST_COUNT: None,
        SPEAK_ON_SERVER: None,
        # SPEAK_VIA_KODI: None,
        #  SPEED: None,
        SPEED_ENABLED: None,
        #  SPEED_VISIBLE: None,
        SPELLING: None,
        #  TTS_SERVICE: None,
        #  TTSD_HOST: None,
        #  TTSD_PORT: None,
        USE_AOSS: None,
        # VERSION: None,
        VOICE: None,
        VOICE_PATH: None
        # VOICE_VISIBLE: None,
        # VOLUME: None
    }

    PLAYER_SETTINGS: Dict[str, None] = {
        #  PLAYER_SPEED: None,
        # AUDIO_FORMAT: None
    }

    SETTINGS_BY_SERVICE_TYPE: Dict[ServiceType, Dict[str, None]] = {
        ServiceType.ENGINE:  ENGINE_SETTINGS,
        ServiceType.PLAYER: PLAYER_SETTINGS,
        ServiceType.TTS: TTS_SETTINGS
    }

    SettingTypes: Dict[str, SettingType] = {}

    @classmethod
    def init(cls):
        cls.SettingTypes = {
            cls.ADDONS_MD5                            : SettingType.STRING_TYPE,
            cls.API_KEY                               : SettingType.STRING_TYPE,
            cls.AUDIO_FORMAT                          : SettingType.STRING_TYPE,
            cls.AUTO_ITEM_EXTRA                       : SettingType.BOOLEAN_TYPE,
            cls.AUTO_ITEM_EXTRA_DELAY                 : SettingType.INTEGER_TYPE,
            cls.ENGINE                           : SettingType.STRING_TYPE,
            cls.EXTENDED_HELP_ON_STARTUP         : SettingType.BOOLEAN_TYPE,
            cls.BACKGROUND_PROGRESS_INTERVAL     : SettingType.INTEGER_TYPE,
            cls.CACHE_PATH                       : SettingType.STRING_TYPE,
            cls.CACHE_EXPIRATION_DAYS            : SettingType.INTEGER_TYPE,
            cls.CACHE_SPEECH                     : SettingType.BOOLEAN_TYPE,
            #  cls.CACHE_VOICE_FILES                     : SettingType.BOOLEAN_TYPE,
            cls.CAPITAL_RECOGNITION              : SettingType.BOOLEAN_TYPE,
            cls.CHANNELS                         : SettingType.STRING_TYPE,
            cls.CURRENT_ENGINE                   : SettingType.STRING_TYPE,
            cls.START_CFG_GUI_ON_STARTUP         : SettingType.BOOLEAN_TYPE,
            cls.CONFIGURE_DEPENDENCIES_ON_STARTUP: SettingType.BOOLEAN_TYPE,
            cls.CONFIGURE_KEYMAP_ON_STARTUP      : SettingType.BOOLEAN_TYPE,
            cls.TRANSCODER                       : SettingType.STRING_TYPE,
            cls.DEBUG_LOG_LEVEL                  : SettingType.INTEGER_TYPE,
            cls.DELAY_VOICING                    : SettingType.BOOLEAN_TYPE,
            cls.DISABLE_BROKEN_SERVICES          : SettingType.BOOLEAN_TYPE,
            cls.GENDER                           : SettingType.STRING_TYPE,
            cls.GENDER_VISIBLE                   : SettingType.BOOLEAN_TYPE,
            #  cls.GUI                         : SettingType.BOOLEAN_TYPE,
            cls.CONFIG_HELP_ON_STARTUP           : SettingType.BOOLEAN_TYPE,
            cls.HINT_TEXT_ON_STARTUP             : SettingType.BOOLEAN_TYPE,
            cls.INITIAL_RUN                      : SettingType.BOOLEAN_TYPE,
            cls.INTRODUCTION_ON_STARTUP          : SettingType.BOOLEAN_TYPE,
            cls.LANGUAGE                         : SettingType.STRING_TYPE,
            cls.MODULE                           : SettingType.STRING_TYPE,
            #  cls.OUTPUT_VIA                  : SettingType.STRING_TYPE,
            #  cls.OUTPUT_VISIBLE                        : SettingType.BOOLEAN_TYPE,
            cls.OVERRIDE_POLL_INTERVAL           : SettingType.BOOLEAN_TYPE,
            # cls.PIPE                                  : SettingType.BOOLEAN_TYPE,
            cls.PITCH                            : SettingType.INTEGER_TYPE,
            cls.PLAYER                                : SettingType.STRING_TYPE,
            cls.PLAYER_VOLUME                         : SettingType.INTEGER_TYPE,
            cls.PLAYER_PITCH                          : SettingType.INTEGER_TYPE,
            cls.PLAYER_MODE                           : SettingType.STRING_TYPE,
            cls.PLAYER_SPEED                          : SettingType.INTEGER_TYPE,
            cls.POLL_INTERVAL                         : SettingType.INTEGER_TYPE,
            cls.READER_ON                             : SettingType.BOOLEAN_TYPE,
            cls.REMOTE_PITCH                          : SettingType.INTEGER_TYPE,
            # Replaces engine.ttsd, etc.
            cls.REMOTE_SERVER                         : SettingType.STRING_TYPE,
            cls.REMOTE_SPEED                          : SettingType.INTEGER_TYPE,
            cls.REMOTE_VOLUME                         : SettingType.INTEGER_TYPE,
            cls.SERVICE_ID                            : SettingType.STRING_TYPE,
            # cls.SETTINGS_BEING_CONFIGURED             : SettingType.BOOLEAN_TYPE,
            #  cls.SETTINGS_DIGEST                       : SettingType.STRING_TYPE,
            # cls.SETTINGS_LAST_CHANGED                 : SettingType.INTEGER_TYPE,
            cls.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: SettingType.BOOLEAN_TYPE,
            cls.SPEAK_BACKGROUND_PROGRESS             : SettingType.BOOLEAN_TYPE,
            cls.SPEAK_LIST_COUNT                      : SettingType.BOOLEAN_TYPE,
            cls.SPEAK_ON_SERVER                       : SettingType.BOOLEAN_TYPE,
            #  cls.SPEAK_VIA_KODI                        : SettingType.BOOLEAN_TYPE,
            cls.SPEECH_DISPATCHER                     : SettingType.STRING_TYPE,
            cls.SPEED                                 : SettingType.INTEGER_TYPE,
            cls.SPEED_ENABLED                         : SettingType.BOOLEAN_TYPE,
            #  cls.SPEED_VISIBLE                         : SettingType.BOOLEAN_TYPE,
            #  cls.TTSD_HOST                             : SettingType.STRING_TYPE,
            #  cls.TTSD_PORT                             : SettingType.INTEGER_TYPE,
            cls.USE_AOSS                              : SettingType.BOOLEAN_TYPE,
            cls.VERSION                               : SettingType.STRING_TYPE,
            cls.VOICE                                 : SettingType.STRING_TYPE,
            cls.VOICE_PATH                            : SettingType.STRING_TYPE,
            cls.VOICE_VISIBLE                         : SettingType.BOOLEAN_TYPE,
            cls.VOLUME                                : SettingType.INTEGER_TYPE,
            cls.VOLUME_VISIBLE                        : SettingType.STRING_TYPE
        }


SettingProp.init()
