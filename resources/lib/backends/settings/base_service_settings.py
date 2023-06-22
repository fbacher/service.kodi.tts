# coding=utf-8
from backends.settings.constraints import Constraints
from backends.settings.service_types import Services
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, IntValidator, StringValidator)
from common.logger import BasicLogger
from common.setting_constants import Backends
from common.settings_low_level import SettingsProperties
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class BaseServiceSettings:
    backend_id = Services.TTS_SERVICE
    service_ID: str = Services.TTS_SERVICE
    displayName: str = 'TTS'
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False
    _logger: BasicLogger = None


    # Define TTS native scales for volume, speed, etc
    #
    # Min, Default, Max, Integer_Only (no float)
    ttsPitchConstraints: Constraints = Constraints(0, 50, 99, True, False, 1.0,
                                                   SettingsProperties.PITCH, 50, 1.0)
    ttsVolumeConstraints: Constraints = Constraints(minimum=-12, default=0, maximum=12,
                                                    integer=True, decibels=True,
                                                    scale=1.0,
                                                    property_name=SettingsProperties.VOLUME,
                                                    midpoint=0, increment=1.0)
    ttsSpeedConstraints: Constraints = Constraints(25, 100, 400, False, False, 0.01,
                                                   SettingsProperties.SPEED, 100, 0.25)

    # TODO: move to default settings map
    TTSConstraints: Dict[str, Constraints] = {
        SettingsProperties.SPEED : ttsSpeedConstraints,
        SettingsProperties.PITCH : ttsPitchConstraints,
        SettingsProperties.VOLUME: ttsVolumeConstraints
    }
    # _supported_input_formats: List[str] = []
    # _supported_output_formats: List[str] = []
    # _provides_services: List[ServiceType] = [ServiceType.ENGINE]

    def __init__(self, *args, **kwargs):
        # Allow parents to define settings first, so that they can be overriden here
        # and not the other way around

        # BaseServices()
        clz = type(self)
        self.initialized: bool = False

        if self.initialized:
            return
        self.initialized = True
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.init_settings()

    def init_settings(self):
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingsProperties.PIPE, self.service_ID,
                                       default=False)
        SettingsMap.define_setting(self.service_ID, SettingsProperties.PIPE,
                                   pipe_validator)

        engine_id_validator = StringValidator(SettingsProperties.ENGINE,
                                              '',
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way too big
                                              max_length=32,
                                              default_value=Backends.DEFAULT_ENGINE_ID)
        SettingsMap.define_setting(SettingsProperties.ENGINE, '',
                                   engine_id_validator)

        addon_md5_validator = StringValidator(SettingsProperties.ADDONS_MD5, Services.TTS_SERVICE,
                                              allowed_values=[], min_length=32,
                                              max_length=32, default_value='')
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.ADDONS_MD5,
                                   addon_md5_validator)

        auto_item_extra_validator: BoolValidator
        auto_item_extra_validator = BoolValidator(SettingsProperties.AUTO_ITEM_EXTRA, Services.TTS_SERVICE,
                                                  default=False)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.AUTO_ITEM_EXTRA,
                                   auto_item_extra_validator)
        auto_item_extra_delay_validator: IntValidator
        auto_item_extra_delay_validator = IntValidator(
                SettingsProperties.AUTO_ITEM_EXTRA_DELAY, Services.TTS_SERVICE,
                min_value=0, max_value=3, default_value=0,
                step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.AUTO_ITEM_EXTRA_DELAY,
                                   auto_item_extra_delay_validator)
        background_progress_validator: IntValidator
        background_progress_validator = IntValidator(
                SettingsProperties.BACKGROUND_PROGRESS_INTERVAL, Services.TTS_SERVICE,
                min_value=0, max_value=60, default_value=5,
                step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.BACKGROUND_PROGRESS_INTERVAL,
                                   background_progress_validator)
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
        cache_path_val: StringValidator
        cache_path_val = StringValidator(SettingsProperties.CACHE_PATH, Services.TTS_SERVICE,
                                         allowed_values=[],
                                         min_length=1,
                                         max_length=1024,
                                         default_value=SettingsProperties.CACHE_PATH_DEFAULT)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.CACHE_PATH,
                                   cache_path_val)

        cache_expiration_val: IntValidator
        cache_expiration_val = IntValidator(SettingsProperties.CACHE_EXPIRATION_DAYS,
                                            Services.TTS_SERVICE,
                                            min_value=0, max_value=3654,
                                            default_value=365,
                                            step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.CACHE_EXPIRATION_DAYS,
                                   cache_expiration_val)
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
                                         min_value=0, max_value=1000, default_value=100,
                                         step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.POLL_INTERVAL,
                                   poll_interval_val)

        debug_log_level_val: IntValidator
        debug_log_level_val = IntValidator(SettingsProperties.DEBUG_LOG_LEVEL,
                                           Services.TTS_SERVICE,
                                           min_value=0, max_value=5, default_value=4,
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
                                      default_value=None)
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

    # def register(self, what: Type[ITTSBackendBase]) -> None:
    #     BaseServices.register(what)
