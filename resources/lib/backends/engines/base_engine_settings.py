# coding=utf-8
from __future__ import annotations  # For union operator |

from common import *

from backends.settings.constraints import Constraints
from backends.settings.service_types import ServiceID, ServiceKey, Services
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, GenderValidator, IntValidator,
                                          StringValidator, Validator)
from common.logger import BasicLogger
from common.service_status import StatusType
from common.setting_constants import Backends, Genders

module_logger = BasicLogger.get_logger(__name__)


class BaseEngineSettings:
    engine_id = 'auto'
    service_id: str = Services.TTS_SERVICE
    displayName: str = 'Auto'
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False
    initialized: Dict[ServiceID, bool] = {}

    settings: Dict[str, Validator] = {}
    constraints: Dict[str, Constraints] = {}

    _logger: BasicLogger = None

    # _supported_input_formats: List[str] = []
    # _supported_output_formats: List[str] = []
    # _provides_services: List[ServiceType] = [ServiceType.ENGINE]

    '''
    def __init__(self, setting_id, *args, **kwargs):
        clz = type(self)
        #  super().__init__()

        self.setting_id = setting_id
        if BaseEngineSettings.initialized.setdefault(setting_id, False):
            return
        BaseEngineSettings.initialized[setting_id] = True
        if clz._logger is None:
            clz._logger = module_logger
        BaseEngineSettings.config_settings(setting_id)
    '''

    @staticmethod
    def config_settings(service_key: ServiceID,
                        settings: List[str]) -> None:
        """
        Configures settings common to some engines

        :param service_key: Identifies the engine being configured
        :param settings: List of settings that are to be configured here for the
                         engine being configured
        :return:
        """
        if BaseEngineSettings.initialized.setdefault(service_key, False):
            return
        BaseEngineSettings.initialized[service_key] = True

        for setting_id in settings:
            if setting_id == SettingProp.CACHE_SPEECH:
                service_id: ServiceID = service_key.with_prop(SettingProp.CACHE_SPEECH)
                cache_validator: BoolValidator
                cache_validator = BoolValidator(service_id,
                                                default=False,
                                                define_setting=True,
                                                service_status=StatusType.OK,
                                                persist=True)

            if setting_id == SettingProp.GENDER_VISIBLE:
                service_id: ServiceID = service_key.with_prop(SettingProp.GENDER_VISIBLE)
                gender_visible: BoolValidator
                gender_visible = BoolValidator(service_id,
                                               default=True,
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=True)
