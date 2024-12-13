from __future__ import print_function, annotations

from backends.audio.sound_capabilities import SoundCapabilities
from common import *

from backends.engines.base_engine_settings import BaseEngineSettings
from backends.settings.constraints import Constraints
from backends.settings.i_validators import ValueType
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator, StringValidator, NumericValidator
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Backends, Players

module_logger = BasicLogger.get_logger(__name__)


class SAPI_Settings:
    # Only returns .mp3 files
    ID: str = Backends.SAPI_ID
    engine_id = Backends.SAPI_ID
    service_ID: str = Services.SAPI_ID
    displayName = 'SAPI'
    _logger: BasicLogger = None

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(*args, **kwargs)
        BaseEngineSettings(clz.service_ID)
        self.initialized: bool = False
        if self.initialized:
            return
        self.initialized = True
        if clz._logger is None:
            clz._logger = module_logger
        self.init_settings()

    @classmethod
    def init_settings(cls):
        service_properties = {Constants.NAME: cls.displayName}
        SettingsMap.define_service(ServiceType.ENGINE, cls.service_ID,
                                   service_properties)
        volume_validator: NumericValidator
        volume_validator = NumericValidator(SettingsProperties.VOLUME,
                                            cls.service_ID,
                                            minimum=0, maximum=200,
                                            default=100, is_decibels=False,
                                            is_integer=True)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.VOLUME,
                                   volume_validator)

        speed_validator: NumericValidator
        speed_validator = NumericValidator(SettingsProperties.SPEED,
                                           cls.service_ID,
                                           minimum=.25, maximum=5,
                                           default=1,
                                           is_decibels=False,
                                           is_integer=False)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.SPEED,
                                   speed_validator)

        _supported_input_formats: List[str] = []
        _supported_output_formats: List[str] = []
        _provides_services: List[ServiceType] = [ServiceType.ENGINE,
                                                 ServiceType.INTERNAL_PLAYER]
        SoundCapabilities.add_service(cls.service_ID, _provides_services,
                                      _supported_input_formats,
                                      _supported_output_formats)

        valid_players: List[str] = [Players.INTERNAL]
        player_validator: StringValidator
        player_validator = StringValidator(SettingsProperties.PLAYER, cls.service_ID,
                                           allowed_values=valid_players,
                                           default=Players.INTERNAL)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER,
                                   player_validator)
    @classmethod
    def available(cls) -> bool:
        pass
        # Need access to Engine
        # return bool(getSpeechDSpeaker(test=True))

    @classmethod
    def isInstalled(cls) -> bool:
        return True
