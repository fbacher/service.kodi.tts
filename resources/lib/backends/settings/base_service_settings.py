# coding=utf-8
from __future__ import annotations  # For union operator |

import xbmc

from backends.settings.setting_properties import SettingProp, SettingType
from common import *

from backends.settings.service_types import (ServiceKey, Services, ServiceType, ServiceID,
                                             TTS_Type)
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator,
                                          IntValidator,
                                          SimpleStringValidator, StringValidator,
                                          TTSNumericValidator)
from common.logger import BasicLogger
from common.message_ids import MessageId
from common.service_status import StatusType
from common.setting_constants import Backends

MY_LOGGER = BasicLogger.get_logger(__name__)


class BaseServiceSettings:
    """
    Defines base settings inherited by all other services: engine, player_key, converter,
    etc.
    """
    engine_id = Services.TTS_SERVICE
    service_id: str = Services.TTS_SERVICE
    service_type: ServiceType = ServiceType.TTS
    service_key: ServiceID = ServiceKey.TTS_KEY
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    displayName: str = MessageId.TTS_SETTINGS
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False
    initialized: bool = False

    MY_LOGGER.debug(f'In BaseServiceSettings')
    tts_pitch_validator: TTSNumericValidator
    tts_pitch_validator = TTSNumericValidator(ServiceKey.PITCH,
                                              minimum=0, maximum=99, default=50,
                                              is_decibels=False, is_integer=True,
                                              internal_scale_factor=1,
                                              persist=False)

    tts_volume_validator: TTSNumericValidator
    tts_volume_validator = TTSNumericValidator(ServiceKey.VOLUME,
                                               minimum=-120, maximum=120,
                                               default=0, is_decibels=True,
                                               is_integer=True,
                                               internal_scale_factor=10,
                                               persist=False)
    tts_speed_validator: TTSNumericValidator
    tts_speed_validator = TTSNumericValidator(ServiceKey.SPEED,
                                              minimum=50, maximum=200,
                                              increment=10,
                                              default=100,
                                              is_decibels=False,
                                              is_integer=False,
                                              internal_scale_factor=100,
                                              persist=False)

    global_settings_initialized: bool = False

    # _supported_input_formats: List[str] = []
    # _supported_output_formats: List[str] = []
    # _provides_services: List[ServiceType] = [ServiceType.ENGINE]

    @staticmethod
    def config_predefined_settings(*args, **kwargs) -> None:
        cls = BaseServiceSettings
        if BaseServiceSettings.initialized:
            return

        # TTS_SERVICE. Does not need to persist
        BaseServiceSettings.initialized = True
        SettingsMap.define_setting(service_id=cls.service_key,
                                   setting_type=SettingType.STRING_TYPE,
                                   service_status=StatusType.OK,
                                   persist=False)
        SettingsMap.set_available(cls.service_key, StatusType.OK)
        name_validator: SimpleStringValidator
        name_validator = SimpleStringValidator(service_key=cls.NAME_KEY,
                                               value=cls.displayName,
                                               const=True,
                                               persist=False)
        SettingsMap.define_setting(ServiceKey.INITIAL_RUN,
                                   setting_type=SettingType.BOOLEAN_TYPE,
                                   persist=True)
        MY_LOGGER.debug(f'Creating debug_log_level: {ServiceKey.DEBUG_LOG_LEVEL}')
        debug_log_level_val: IntValidator
        debug_log_level_val = IntValidator(ServiceKey.DEBUG_LOG_LEVEL,
                                           min_value=0, max_value=5, default=4,
                                           # INFO
                                           step=1, scale_internal_to_external=1,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)

        version_level_val: SimpleStringValidator
        version_level_val = SimpleStringValidator(ServiceKey.VERSION,
                                                  value='0.0.0',
                                                  const=False,
                                                  define_setting=True,
                                                  persist=True)

        # TODO: Change to use allowed_values  BackendInfo.getAvailableBackends()
        MY_LOGGER.debug(f'Creating current_engine_key: {ServiceKey.CURRENT_ENGINE_KEY}')
        engine_id_validator = StringValidator(ServiceKey.CURRENT_ENGINE_KEY,
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way too big
                                              max_length=32,
                                              default=Backends.DEFAULT_ENGINE_ID,
                                              define_setting=True,
                                              service_status=StatusType.OK,
                                              persist=True)

        addon_md5_validator = StringValidator(ServiceKey.ADDONS_MD5,
                                              allowed_values=[], min_length=32,
                                              max_length=32, default='',
                                              define_setting=True,
                                              service_status=StatusType.OK,
                                              persist=True)

        background_progress_validator: IntValidator
        background_progress_validator = IntValidator(
                ServiceKey.BACKGROUND_PROGRESS_INTERVAL,
                min_value=0, max_value=60, default=5,
                step=1, scale_internal_to_external=1,
                define_setting=True,
                service_status=StatusType.OK,
                persist=True)

        '''
        What?
        settings_digest: BoolValidator
        settings_digest = BoolValidator(ServiceKey.SETTINGS_DIGEST, default=True)
        SettingsMap.define_setting(settings_digest.service_key,
                                   validator=settings_digest)
        '''

        extended_help: BoolValidator
        extended_help = BoolValidator(ServiceKey.EXTENDED_HELP_ON_STARTUP, default=True,
                                      define_setting=True,
                                      service_status=StatusType.OK,
                                      persist=True)

        disable_broken_services: BoolValidator
        disable_broken_services = BoolValidator(ServiceKey.DISABLE_BROKEN_SERVICES,
                                                default=True,
                                                define_setting=True,
                                                service_status=StatusType.OK,
                                                persist=True)

        speak_background_progress: BoolValidator
        speak_background_progress = BoolValidator(ServiceKey.SPEAK_BACKGROUND_PROGRESS,
                                                  default=False,
                                                  define_setting=True,
                                                  service_status=StatusType.OK,
                                                  persist=True)

        speak_during_media: BoolValidator
        speak_during_media = BoolValidator(
                ServiceKey.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
                default=False,
                define_setting=True,
                service_status=StatusType.OK,
                persist=True)

        override_poll_interval_val: BoolValidator
        override_poll_interval_val = BoolValidator(ServiceKey.OVERRIDE_POLL_INTERVAL,
                                                   default=False,
                                                   define_setting=True,
                                                   service_status=StatusType.OK,
                                                   persist=True)
        # Poll interval in milliseconds
        poll_interval_val: IntValidator
        poll_interval_val = IntValidator(ServiceKey.POLL_INTERVAL,
                                         min_value=0, max_value=1000, default=100,
                                         step=1, scale_internal_to_external=1,
                                         define_setting=True,
                                         service_status=StatusType.OK,
                                         persist=True)
        auto_item_extra_val: BoolValidator
        auto_item_extra_val = BoolValidator(service_key=ServiceKey.AUTO_ITEM_EXTRA,
                                            default=False,
                                            define_setting=True,
                                            service_status=StatusType.OK,
                                            persist=True)

        auto_item_extra_delay_val: IntValidator
        auto_item_extra_delay_val = IntValidator(
                                        service_key=ServiceKey.AUTO_ITEM_EXTRA_DELAY,
                                        min_value=1, max_value=60, default=2,
                                        step=1, scale_internal_to_external=1,
                                        define_setting=True,
                                        service_status=StatusType.OK,
                                        persist=True)

        reader_on_val: BoolValidator
        reader_on_val = BoolValidator(ServiceKey.READER_ON,
                                      default=True,
                                      define_setting=True,
                                      service_status=StatusType.OK,
                                      persist=True)

        speak_list_count_val: BoolValidator
        speak_list_count_val = BoolValidator(ServiceKey.SPEAK_LIST_COUNT,
                                             default=True,
                                             define_setting=True,
                                             service_status=StatusType.OK,
                                             persist=True)
        '''
        use_tempfs_val: BoolValidator
        use_tempfs_val = BoolValidator(ServiceKey.USE_TMPFS,
                                       default=True)
        SettingsMap.define_setting(use_tempfs_val.service_key,
                                   use_tempfs_val)

        '''
        hint_text_on_startup: BoolValidator
        hint_text_on_startup = BoolValidator(ServiceKey.HINT_TEXT_ON_STARTUP,
                                             default=True,
                                             define_setting=True,
                                             service_status=StatusType.OK,
                                             persist=True)
        service_key = ServiceKey.TTS_KEY.with_prop(SettingProp.CONFIGURE_ON_STARTUP)
        SettingsMap.define_setting(service_key, setting_type=SettingType.BOOLEAN_TYPE,
                                   persist=True)
        service_key = ServiceKey.TTS_KEY.with_prop(SettingProp.INTRODUCTION_ON_STARTUP)
        SettingsMap.define_setting(service_key, setting_type=SettingType.BOOLEAN_TYPE,
                                   persist=True)
        service_key = ServiceKey.TTS_KEY.with_prop(SettingProp.HELP_CONFIG_ON_STARTUP)
        SettingsMap.define_setting(service_key, setting_type=SettingType.BOOLEAN_TYPE,
                                   persist=True)
        cache_expiration_days: IntValidator
        cache_expiration_days = IntValidator(ServiceKey.CACHE_EXPIRATION_DAYS,
                                             min_value=0, max_value=3650,
                                             step=1,
                                             default=SettingProp.CACHE_EXPIRATION_DEFAULT,
                                             define_setting=True,
                                             service_status=StatusType.OK,
                                             persist=True)

        '''
        speak_on_server: BoolValidator
        speak_on_server = BoolValidator(ServiceKey.SPEAK_ON_SERVER,
                                        default=True)
        SettingsMap.define_setting(speak_on_server.service_key,
                                   speak_on_server)
    '''
        MY_LOGGER.debug(f'exiting init_settings')
