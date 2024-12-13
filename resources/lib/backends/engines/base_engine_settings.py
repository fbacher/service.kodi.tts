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

module_logger = BasicLogger.get_logger(__name__)


class BaseEngineSettings:
    engine_id = 'auto'
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
            clz._logger = module_logger
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

        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, service_id,
                                        default=False)

        SettingsMap.define_setting(service_id, SettingsProperties.CACHE_SPEECH,
                                   cache_validator)

        gender_visible: BoolValidator
        gender_visible = BoolValidator(
                SettingsProperties.GENDER_VISIBLE, Services.TTS_SERVICE,
                default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.GENDER_VISIBLE,
                                   gender_visible)

        speak_list_count_val: BoolValidator
        speak_list_count_val = BoolValidator(SettingsProperties.SPEAK_LIST_COUNT,
                                             Services.TTS_SERVICE,
                                             default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.SPEAK_LIST_COUNT,
                                   speak_list_count_val)

        speak_on_server: BoolValidator
        speak_on_server = BoolValidator(SettingsProperties.SPEAK_ON_SERVER,
                                             Services.TTS_SERVICE,
                                             default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.SPEAK_ON_SERVER,
                                   speak_on_server)
