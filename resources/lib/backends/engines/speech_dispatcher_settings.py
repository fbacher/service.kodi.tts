from backends.engines.base_engine_settings import BaseEngineSettings
from backends.settings.constraints import Constraints
from backends.settings.i_validators import ValueType
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator
from common.logger import BasicLogger
from common.setting_constants import Backends

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SpeechDispatcherSettings:
    # Only returns .mp3 files
    ID: str = Backends.SPEECH_DISPATCHER_ID
    backend_id = Backends.SPEECH_DISPATCHER_ID
    service_ID: str = Services.SPEECH_DISPATCHER_ID
    displayName = 'Speech Dispatcher'

    class VolumeConstraintsValidator(ConstraintsValidator):

        def __init__(self, setting_id: str, service_id: str,
                     constraints: Constraints) -> None:
            super().__init__(setting_id, service_id, constraints)
            clz = type(self)

        def setValue(self, value: int | float | str,
                     value_type: ValueType = ValueType.VALUE) -> None:
            """
            Keep value fixed at 1
            :param value:
            :param value_type:
            """
            constraints: Constraints = self.constraints
            constraints.setSetting(1, self.service_id)

        def getValue(self, value_type: ValueType = ValueType.VALUE) -> int | float | str:
            """
            Keep value fixed at 1
            :return:
            """
            return 1

        def setUIValue(self, ui_value: str) -> None:
            pass

        def getUIValue(self) -> str:
            return f'{self.getValue()}'

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
        volumeConversionConstraints: Constraints = Constraints(minimum=0.1, default=1.0,
                                                               maximum=2.0, integer=False,
                                                               decibels=False, scale=1.0,
                                                               property_name=SettingsProperties.VOLUME,
                                                               midpoint=1, increment=0.1)
        volume_constraints_validator = self.VolumeConstraintsValidator(
                SettingsProperties.VOLUME, self.backend_id, volumeConversionConstraints)

        SettingsMap.define_setting(self.service_ID, SettingsProperties.VOLUME,
                                   volume_constraints_validator)
