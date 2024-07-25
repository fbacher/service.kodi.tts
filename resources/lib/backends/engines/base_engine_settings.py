from __future__ import annotations  # For union operator |

from common import *

from backends.settings.constraints import Constraints
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, GenderValidator, IntValidator,
                                          StringValidator, Validator)
from common.logger import BasicLogger
from common.setting_constants import Backends, Genders

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class BaseEngineSettings:
    backend_id = 'auto'
    service_ID: str = Services.TTS_SERVICE
    displayName: str = 'Auto'
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False
    initialized: Dict[str, bool] = {}

    settings: Dict[str, Validator] = {}
    constraints: Dict[str, Constraints] = {}

    _logger: BasicLogger = None

    # _supported_input_formats: List[str] = []
    # _supported_output_formats: List[str] = []
    # _provides_services: List[ServiceType] = [ServiceType.ENGINE]

    def __init__(self, service_ID, *args, **kwargs):
        clz = type(self)
        super().__init__()
        self.service_ID = service_ID

        if BaseEngineSettings.initialized.setdefault(service_ID, False):
            return
        BaseEngineSettings.initialized[service_ID] = True
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        BaseEngineSettings.init_settings(service_ID)

    @classmethod
    def init_settings(cls, service_id):
        gender_validator = GenderValidator(SettingsProperties.GENDER, service_id,
                                           min_value=Genders.FEMALE,
                                           max_value=Genders.UNKNOWN,
                                           default=Genders.UNKNOWN)
        SettingsMap.define_setting(service_id, SettingsProperties.GENDER,
                                   gender_validator)
        # gender_validator.set_tts_value(Genders.FEMALE)

        engine_id_validator = StringValidator(SettingsProperties.ENGINE,
                                              Services.TTS_SERVICE,
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way to big
                                              max_length=32,
                                              default=Backends.DEFAULT_ENGINE_ID)
        SettingsMap.define_setting(Services.TTS_SERVICE, SettingsProperties.ENGINE,
                                   engine_id_validator)
        '''
        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, service_id,
                                        default=False)

        SettingsMap.define_setting(service_id, SettingsProperties.CACHE_SPEECH,
                                   cache_validator)
        '''

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

        speak_list_count_val: BoolValidator
        speak_list_count_val = BoolValidator(SettingsProperties.SPEAK_LIST_COUNT,
                                             Services.TTS_SERVICE,
                                             default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.SPEAK_LIST_COUNT,
                                   speak_list_count_val)

        version_val: StringValidator
        version_val = StringValidator(SettingsProperties.VERSION, Services.TTS_SERVICE,
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
