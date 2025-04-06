# coding=utf-8
from __future__ import annotations  # For union operator |

import xbmc

from common import *

from backends.settings.constraints import Constraints
from backends.settings.service_types import (ServiceKey, Services, ServiceType, ServiceID,
                                             TTS_Type)
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, IntValidator, NumericValidator,
                                          SimpleStringValidator, StringValidator,
                                          TTSNumericValidator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Backends, Genders, PlayerMode
from common.settings import Settings
from common.settings_low_level import SettingProp

MY_LOGGER = BasicLogger.get_logger(__name__)


class BaseServiceSettings:
    """
    Defines base settings inherited by all other services: engine, player_key, converter,
    etc.
    """
    engine_id = Services.TTS_SERVICE
    service_id: str = Services.TTS_SERVICE
    service_type: ServiceType = ServiceType.TTS
    service_key: ServiceID = ServiceID(service_type, service_id)
    displayName: str = 'TTS'
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False
    initialized: bool = False

    tts_pitch_validator: TTSNumericValidator
    tts_pitch_validator = TTSNumericValidator(ServiceKey.PITCH,
                                              minimum=0, maximum=99, default=50,
                                              is_decibels=False, is_integer=True,
                                              internal_scale_factor=1)

    tts_volume_validator: TTSNumericValidator
    tts_volume_validator = TTSNumericValidator(ServiceKey.VOLUME,
                                               minimum=-120, maximum=120,
                                               default=0, is_decibels=True,
                                               is_integer=True,
                                               internal_scale_factor=10)
    tts_speed_validator: TTSNumericValidator
    tts_speed_validator = TTSNumericValidator(ServiceKey.SPEED,
                                              minimum=50, maximum=200,
                                              increment=10,
                                              default=100,
                                              is_decibels=False,
                                              is_integer=False,
                                              internal_scale_factor=100)


    # TODO: move to default settings map
    # TTSConstraints: Dict[str, Constraints] = {
    #    SettingProp.SPEED: tts_speed_validator,
    #    SettingProp.PITCH: tts_pitch_validator,
    #    SettingProp.VOLUME: tts_volume_validator
    #  }
    global_settings_initialized: bool = False

    # _supported_input_formats: List[str] = []
    # _supported_output_formats: List[str] = []
    # _provides_services: List[ServiceType] = [ServiceType.ENGINE]

    @staticmethod
    def config_predefined_settings(*args, **kwargs) -> None:
        # Only initialize TTS_Service items
        if BaseServiceSettings.initialized:
            return
        BaseServiceSettings.initialized = True
        debug_log_level_val: IntValidator
        debug_log_level_val = IntValidator(ServiceKey.DEBUG_LOG_LEVEL,
                                           min_value=0, max_value=5, default=4,
                                           # INFO
                                           step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(debug_log_level_val.service_key,
                                   debug_log_level_val)
        #
        # To the user, all settings are in TTS space. For Volume, it uses a
        # -12 .. +12 dB scale. The engine modifies it's own volume constraints
        # to adjust the TTS volume into the equivalent engine volume

        SettingsMap.define_setting(BaseServiceSettings.tts_volume_validator.service_key,
                                   BaseServiceSettings.tts_volume_validator)
        SettingsMap.define_setting(BaseServiceSettings.tts_pitch_validator.service_key,
                                   BaseServiceSettings.tts_pitch_validator)
        SettingsMap.define_setting(BaseServiceSettings.tts_speed_validator.service_key,
                                   BaseServiceSettings.tts_speed_validator)

        '''
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingProp.PIPE, cls.setting_id,
                                       default=False)
        SettingsMap.define_setting(cls.setting_id, SettingProp.PIPE,
                                   pipe_validator)
        '''
        # TODO: Change to use allowed_values  BackendInfo.getAvailableBackends()
        engine_id_validator = StringValidator(ServiceKey.CURRENT_ENGINE_KEY,
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way too big
                                              max_length=32,
                                              default=Backends.DEFAULT_ENGINE_ID)
        SettingsMap.define_setting(engine_id_validator.service_key,
                                   engine_id_validator)

        addon_md5_validator = StringValidator(ServiceKey.ADDONS_MD5,
                                              allowed_values=[], min_length=32,
                                              max_length=32, default='')
        SettingsMap.define_setting(addon_md5_validator.service_key,
                                   addon_md5_validator)

        background_progress_validator: IntValidator
        background_progress_validator = IntValidator(
                ServiceKey.BACKGROUND_PROGRESS_INTERVAL,
                min_value=0, max_value=60, default=5,
                step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(background_progress_validator.service_key,
                                   background_progress_validator)

        settings_digest: BoolValidator
        settings_digest = BoolValidator(ServiceKey.SETTINGS_DIGEST, default=True)
        SettingsMap.define_setting(settings_digest.service_key,
                                   settings_digest)

        extended_help: BoolValidator
        extended_help = BoolValidator(
                ServiceKey.EXTENDED_HELP_ON_STARTUP, default=True)
        SettingsMap.define_setting(extended_help.service_key,
                                   extended_help)

        disable_broken_services: BoolValidator
        disable_broken_services = BoolValidator(ServiceKey.DISABLE_BROKEN_SERVICES,
                                                default=True)
        SettingsMap.define_setting(disable_broken_services.service_key,
                                   disable_broken_services)

        speak_background_progress: BoolValidator
        speak_background_progress = BoolValidator(
                ServiceKey.SPEAK_BACKGROUND_PROGRESS, default=False)
        SettingsMap.define_setting(speak_background_progress.service_key,
                                   speak_background_progress)

        speak_during_media: BoolValidator
        speak_during_media = BoolValidator(
                ServiceKey.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
                default=False)

        SettingsMap.define_setting(speak_during_media.service_key,
                                   speak_during_media)

        override_poll_interval_val: BoolValidator
        override_poll_interval_val = BoolValidator(
                ServiceKey.OVERRIDE_POLL_INTERVAL,
                default=False)
        SettingsMap.define_setting(override_poll_interval_val.service_key,
                                   override_poll_interval_val)

        # Poll interval in milliseconds
        poll_interval_val: IntValidator
        poll_interval_val = IntValidator(ServiceKey.POLL_INTERVAL,
                                         min_value=0, max_value=1000, default=100,
                                         step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(poll_interval_val.service_key,
                                   poll_interval_val)

        auto_item_extra_val: BoolValidator
        auto_item_extra_val = BoolValidator(
                service_key=ServiceKey.AUTO_ITEM_EXTRA,
                default=False)
        SettingsMap.define_setting(ServiceKey.AUTO_ITEM_EXTRA,
                                   auto_item_extra_val)

        auto_item_extra_delay_val: IntValidator
        auto_item_extra_delay_val = IntValidator(
                                      service_key=ServiceKey.AUTO_ITEM_EXTRA_DELAY,
                                      min_value=1, max_value=60, default=2,
                                      step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(ServiceKey.AUTO_ITEM_EXTRA_DELAY,
                                   auto_item_extra_delay_val)

        reader_on_val: BoolValidator
        reader_on_val = BoolValidator(ServiceKey.READER_ON,
                                      default=True)
        SettingsMap.define_setting(reader_on_val.service_key,
                                   reader_on_val)

        speak_list_count_val: BoolValidator
        speak_list_count_val = BoolValidator(ServiceKey.SPEAK_LIST_COUNT,
                                             default=True)
        SettingsMap.define_setting(speak_list_count_val.service_key,
                                   speak_list_count_val)

        '''
        version_val: StringValidator
        version_val = StringValidator(ServiceKey.VERSION,
                                      allowed_values=[],
                                      min_length=5,
                                      max_length=20,
                                      default=None)
        SettingsMap.define_setting(version_val.service_key,
                                   version_val)

        use_tempfs_val: BoolValidator
        use_tempfs_val = BoolValidator(ServiceKey.USE_TMPFS,
                                       default=True)
        SettingsMap.define_setting(use_tempfs_val.service_key,
                                   use_tempfs_val)

        '''
        hint_text_on_startup: BoolValidator
        hint_text_on_startup = BoolValidator(ServiceKey.HINT_TEXT_ON_STARTUP,
                                             default=True)
        SettingsMap.define_setting(hint_text_on_startup.service_key,
                                   hint_text_on_startup)
        '''
        speak_on_server: BoolValidator
        speak_on_server = BoolValidator(ServiceKey.SPEAK_ON_SERVER,
                                        default=True)
        SettingsMap.define_setting(speak_on_server.service_key,
                                   speak_on_server)
    '''
        MY_LOGGER.debug(f'exiting init_settings')
