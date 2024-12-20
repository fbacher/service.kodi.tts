# coding=utf-8
from __future__ import annotations  # For union operator |

import xbmc

from common import *

from backends.settings.constraints import Constraints
from backends.settings.service_types import Services
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, IntValidator, NumericValidator,
                                          StringValidator,
                                          TTSNumericValidator)
from common.logger import BasicLogger
from common.setting_constants import Backends, Genders, PlayerMode
from common.settings import Settings
from common.settings_low_level import SettingsProperties

MY_LOGGER = BasicLogger.get_logger(__name__)


class BaseServiceSettings:
    """
    Defines base settings inherited by all other services: engine, player, converter,
    etc.
    """
    engine_id = Services.TTS_SERVICE
    service_ID: str = Services.TTS_SERVICE
    displayName: str = 'TTS'
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False
    initialized: bool = False
    tts_pitch_validator: TTSNumericValidator
    tts_pitch_validator = TTSNumericValidator(SettingsProperties.PITCH,
                                              minimum=0, maximum=99, default=50,
                                              is_decibels=False, is_integer=True,
                                              internal_scale_factor=1)
    SettingsMap.define_setting(service_ID, SettingsProperties.PITCH,
                               tts_pitch_validator)

    tts_volume_validator: TTSNumericValidator
    tts_volume_validator = TTSNumericValidator(SettingsProperties.VOLUME,
                                               minimum=-120, maximum=120,
                                               default=0, is_decibels=True,
                                               is_integer=True,
                                               internal_scale_factor=10)
    SettingsMap.define_setting(service_ID, SettingsProperties.VOLUME,
                               tts_volume_validator)
    tts_speed_validator: TTSNumericValidator
    tts_speed_validator = TTSNumericValidator(SettingsProperties.SPEED,
                                              minimum=50, maximum=200,
                                              increment=10,
                                              default=100,
                                              is_decibels=False,
                                              is_integer=False,
                                              internal_scale_factor=100)
    SettingsMap.define_setting(service_ID, SettingsProperties.SPEED,
                               tts_speed_validator)

    # TODO: move to default settings map
    # TTSConstraints: Dict[str, Constraints] = {
    #    SettingsProperties.SPEED: tts_speed_validator,
    #    SettingsProperties.PITCH: tts_pitch_validator,
    #    SettingsProperties.VOLUME: tts_volume_validator
    #  }
    global_settings_initialized: bool = False

    # _supported_input_formats: List[str] = []
    # _supported_output_formats: List[str] = []
    # _provides_services: List[ServiceType] = [ServiceType.ENGINE]

    def __init__(self, *args, **kwargs):
        # Allow parents to define settings first, so that they can be overriden here
        # and not the other way around

        xbmc.log(f'In base_service_settings.__init__', xbmc.LOGDEBUG)
        # BaseServices()
        clz = type(self)

        # Only initialized TTS_Service items

        if BaseServiceSettings.initialized:
            return
        BaseServiceSettings.initialized = True
        # Explicitly init this class. Self would initialize the self class
        BaseServiceSettings.init_settings()
        if not clz.global_settings_initialized:
            BaseServiceSettings.init_global_settings()
            clz.global_settings_initialized = True

    @classmethod
    def init_global_settings(cls):
        #
        # To the user, all settings are in TTS space. For Volume, it uses a
        # -12 .. +12 dB scale. The engine modifies it's own volume constraints
        # to adjust the TTS volume into the equivalent engine volume

        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.VOLUME,
                                   cls.tts_volume_validator)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.PITCH,
                                   cls.tts_pitch_validator)
        SettingsMap.define_setting(BaseServiceSettings.service_ID,
                                   SettingsProperties.SPEED,
                                   BaseServiceSettings.tts_speed_validator)

    @classmethod
    def init_settings(cls):
        MY_LOGGER.debug(f'In init_settings')
        '''
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingsProperties.PIPE, cls.service_ID,
                                       default=False)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PIPE,
                                   pipe_validator)
        '''
        debug_log_level_val: IntValidator
        debug_log_level_val = IntValidator(SettingsProperties.DEBUG_LOG_LEVEL,
                                           Services.TTS_SERVICE,
                                           min_value=0, max_value=5, default=4,
                                           # INFO
                                           step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.DEBUG_LOG_LEVEL,
                                   debug_log_level_val)

        allowed_player_modes: List[str] = [
            PlayerMode.SLAVE_FILE.value,
            PlayerMode.FILE.value
        ]
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(SettingsProperties.PLAYER_MODE,
                                                cls.service_ID,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.SLAVE_FILE.value)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER_MODE,
                                   player_mode_validator)

        # TODO: Change to use allowed_values  BackendInfo.getAvailableBackends()
        engine_id_validator = StringValidator(SettingsProperties.ENGINE,
                                              '',
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way too big
                                              max_length=32,
                                              default=Backends.DEFAULT_ENGINE_ID)
        SettingsMap.define_setting(SettingsProperties.ENGINE, '',
                                   engine_id_validator)

        addon_md5_validator = StringValidator(SettingsProperties.ADDONS_MD5,
                                              Services.TTS_SERVICE,
                                              allowed_values=[], min_length=32,
                                              max_length=32, default='')
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.ADDONS_MD5,
                                   addon_md5_validator)

        '''
        auto_item_extra_validator: BoolValidator
        auto_item_extra_validator = BoolValidator(SettingsProperties.AUTO_ITEM_EXTRA,
                                                  Services.TTS_SERVICE,
                                                  default=False)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.AUTO_ITEM_EXTRA,
                                   auto_item_extra_validator)
        auto_item_extra_delay_validator: IntValidator
        auto_item_extra_delay_validator = IntValidator(
                SettingsProperties.AUTO_ITEM_EXTRA_DELAY, Services.TTS_SERVICE,
                min_value=0, max_value=3, default=0,
                step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.AUTO_ITEM_EXTRA_DELAY,
                                   auto_item_extra_delay_validator)
        '''
        background_progress_validator: IntValidator
        background_progress_validator = IntValidator(
                SettingsProperties.BACKGROUND_PROGRESS_INTERVAL, Services.TTS_SERVICE,
                min_value=0, max_value=60, default=5,
                step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.BACKGROUND_PROGRESS_INTERVAL,
                                   background_progress_validator)

        settings_digest: BoolValidator
        settings_digest = BoolValidator(
                SettingsProperties.SETTINGS_DIGEST, Services.TTS_SERVICE,
                default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.SETTINGS_DIGEST,
                                   settings_digest)

        extended_help: BoolValidator
        extended_help = BoolValidator(
                SettingsProperties.EXTENDED_HELP_ON_STARTUP, Services.TTS_SERVICE,
                default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.EXTENDED_HELP_ON_STARTUP,
                                   extended_help)

        disable_broken_services: BoolValidator
        disable_broken_services = BoolValidator(
                SettingsProperties.DISABLE_BROKEN_SERVICES, Services.TTS_SERVICE,
                default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.DISABLE_BROKEN_SERVICES,
                                   disable_broken_services)

        speak_background_progress: BoolValidator
        speak_background_progress = BoolValidator(
                SettingsProperties.SPEAK_BACKGROUND_PROGRESS, Services.TTS_SERVICE,
                default=False)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.SPEAK_BACKGROUND_PROGRESS,
                                   speak_background_progress)

        speak_during_media: BoolValidator
        speak_during_media = BoolValidator(
                SettingsProperties.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
                Services.TTS_SERVICE,
                default=False)

        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
                                   speak_during_media)

        override_poll_interval_val: BoolValidator
        override_poll_interval_val = BoolValidator(
                SettingsProperties.OVERRIDE_POLL_INTERVAL, Services.TTS_SERVICE,
                default=False)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.OVERRIDE_POLL_INTERVAL,
                                   override_poll_interval_val)

        # Poll interval in milliseconds
        poll_interval_val: IntValidator
        poll_interval_val = IntValidator(SettingsProperties.POLL_INTERVAL,
                                         Services.TTS_SERVICE,
                                         min_value=0, max_value=1000, default=100,
                                         step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.POLL_INTERVAL,
                                   poll_interval_val)

        cache_path_val: StringValidator
        cache_path_val = StringValidator(SettingsProperties.CACHE_PATH,
                                         Services.TTS_SERVICE,
                                         allowed_values=[],
                                         min_length=1,
                                         max_length=1024,
                                         default=SettingsProperties.CACHE_PATH_DEFAULT)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.CACHE_PATH,
                                   cache_path_val)

        override_poll_interval_val: BoolValidator
        override_poll_interval_val = BoolValidator(
                SettingsProperties.OVERRIDE_POLL_INTERVAL, Services.TTS_SERVICE,
                default=False)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.OVERRIDE_POLL_INTERVAL,
                                   override_poll_interval_val)
        # Poll interval in milliseconds
        poll_interval_val: IntValidator
        poll_interval_val = IntValidator(SettingsProperties.POLL_INTERVAL,
                                         Services.TTS_SERVICE,
                                         min_value=0, max_value=1000, default=100,
                                         step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.POLL_INTERVAL,
                                   poll_interval_val)

        debug_log_level_val: IntValidator
        debug_log_level_val = IntValidator(SettingsProperties.DEBUG_LOG_LEVEL,
                                           Services.TTS_SERVICE,
                                           min_value=0, max_value=5, default=4,
                                           # INFO
                                           step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.DEBUG_LOG_LEVEL,
                                   debug_log_level_val)

        reader_on_val: BoolValidator
        reader_on_val = BoolValidator(SettingsProperties.READER_ON,
                                      Services.TTS_SERVICE,
                                      default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.READER_ON,
                                   reader_on_val)
        speak_list_count_val: BoolValidator
        speak_list_count_val = BoolValidator(SettingsProperties.SPEAK_LIST_COUNT,
                                             Services.TTS_SERVICE,
                                             default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.SPEAK_LIST_COUNT,
                                   speak_list_count_val)

        version_val: StringValidator
        version_val = StringValidator(SettingsProperties.VERSION,
                                      Services.TTS_SERVICE,
                                      allowed_values=[],
                                      min_length=5,
                                      max_length=20,
                                      default=None)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.VERSION,
                                   version_val)

        use_tempfs_val: BoolValidator
        use_tempfs_val = BoolValidator(SettingsProperties.USE_TEMPFS,
                                       Services.TTS_SERVICE,
                                       default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.USE_TEMPFS,
                                   use_tempfs_val)

        gender_validator = GenderValidator(SettingsProperties.GENDER,
                                           Services.TTS_SERVICE,
                                           min_value=Genders.FEMALE,
                                           max_value=Genders.UNKNOWN,
                                           default=Genders.UNKNOWN)
        SettingsMap.define_setting(Services.TTS_SERVICE, SettingsProperties.GENDER,
                                   gender_validator)
        gender_validator.set_tts_value(Genders.FEMALE)

        hint_text_on_startup: BoolValidator
        hint_text_on_startup = BoolValidator(
                SettingsProperties.HINT_TEXT_ON_STARTUP, Services.TTS_SERVICE,
                default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.HINT_TEXT_ON_STARTUP,
                                   hint_text_on_startup)

        version_val: StringValidator
        version_val = StringValidator(SettingsProperties.VERSION, Services.TTS_SERVICE,
                                      allowed_values=[],
                                      min_length=5,
                                      max_length=20,
                                      default=None)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.VERSION,
                                   version_val)

        MY_LOGGER.debug(f'exiting init_settings')


        @staticmethod
        def isSupportedOnPlatform():
            """
            This O/S supports this engine/backend

            :return:
            """
            return False

        @staticmethod
        def isInstalled():
            """
            This eGngine/backend is installed and configured on the O/S.

            :return:
            """
            return False

        @classmethod
        def is_available_and_usable(cls):
            """

            @return:
            """
            return cls._available()

        @classmethod
        def _available(cls):
            if cls.broken and Settings.getSetting(
                    SettingsProperties.DISABLE_BROKEN_SERVICES,
                    SettingsProperties.TTS_SERVICE, True):
                return False
            return cls.available()

        @staticmethod
        def available():
            """Static method representing the speech engines availability

            Subclasses should override this and return True if the speech engine is
            capable of speaking text in the current environment.
            Default implementation returns False.
            """
            return False
