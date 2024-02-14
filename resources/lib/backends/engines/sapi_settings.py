from __future__ import print_function, annotations

from backends.audio.sound_capabilties import SoundCapabilities
from common import *

from backends.engines.base_engine_settings import BaseEngineSettings
from backends.settings.constraints import Constraints
from backends.settings.i_validators import ValueType
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator, StringValidator
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Backends, Players

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SAPI_Settings:
    # Only returns .mp3 files
    ID: str = Backends.SAPI_ID
    backend_id = Backends.SAPI_ID
    service_ID: str = Services.SAPI_ID
    displayName = 'SAPI'
    _logger: BasicLogger = None

    class VolumeConstraintsValidator(ConstraintsValidator):

        def __init__(self, setting_id: str, service_id: str,
                     constraints: Constraints) -> None:
            super().__init__(setting_id, service_id, constraints)
            clz = type(self)

        def set_tts_value(self, value: int | float | str,
                          value_type: ValueType = ValueType.VALUE) -> None:
            """
            Keep value fixed at 1
            :param value:
            :param value_type:
            """
            constraints: Constraints = self.constraints
            constraints.setSetting(1, self.service_id)

        def get_tts_value(self, default_value=1.0,
                          value_type: ValueType = ValueType.VALUE) -> int | float | str:
            """
            Keep value fixed at 1
            :return:
            """
            return 1

        def setUIValue(self, ui_value: str) -> None:
            pass

        def getUIValue(self) -> str:
            value, _, _, _ = self.get_tts_values()
            return str(value)

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(*args, **kwargs)
        BaseEngineSettings(clz.service_ID)
        self.initialized: bool = False
        if self.initialized:
            return
        self.initialized = True
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.init_settings()

    def init_settings(self):
        clz = type(self)
        service_properties = {Constants.NAME: clz.displayName}
        SettingsMap.define_service(ServiceType.ENGINE, clz.service_ID,
                                   service_properties)
        volumeConversionConstraints: Constraints = Constraints(minimum=0.1, default=1.0,
                                                               maximum=2.0, integer=False,
                                                               decibels=False, scale=1.0,
                                                               property_name=SettingsProperties.VOLUME,
                                                               midpoint=1, increment=0.1)
        volume_constraints_validator = self.VolumeConstraintsValidator(
                SettingsProperties.VOLUME, self.backend_id, volumeConversionConstraints)

        SettingsMap.define_setting(self.service_ID, SettingsProperties.VOLUME,
                                   volume_constraints_validator)
        _supported_input_formats: List[str] = []
        _supported_output_formats: List[str] = []
        _provides_services: List[ServiceType] = [ServiceType.ENGINE,
                                                 ServiceType.INTERNAL_PLAYER]
        SoundCapabilities.add_service(clz.service_ID, _provides_services,
                                      _supported_input_formats,
                                      _supported_output_formats)

        valid_players: List[str] = [Players.INTERNAL]
        player_validator: StringValidator
        player_validator = StringValidator(SettingsProperties.PLAYER, clz.service_ID,
                                           allowed_values=valid_players,
                                           default=Players.INTERNAL)
        SettingsMap.define_setting(clz.service_ID, SettingsProperties.PLAYER,
                                   player_validator)
    @classmethod
    def available(cls) -> bool:
        pass
        # Need access to Engine
        # return bool(getSpeechDSpeaker(test=True))

    @classmethod
    def isInstalled(cls) -> bool:
        return True
