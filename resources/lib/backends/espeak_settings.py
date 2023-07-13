import os
import subprocess
import sys

from backends.audio.sound_capabilties import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.i_validators import ValueType
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          EnumValidator, StringValidator)
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import Backends, Genders, Players
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ESpeakSettings(BaseServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.ESPEAK_ID
    engine_id = Backends.ESPEAK_ID
    service_ID: str = Services.ESPEAK_ID
    displayName = 'eSpeak'

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

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    # speedConstraints = Constraints(80, 175, 450, True, False, 1.0, SettingsProperties.SPEED)
    # pitchConstraints = Constraints(0, 50, 99, True, False, 1.0, SettingsProperties.PITCH)
    # volumeNativeConstraints = Constraints(0, 100, 200, True, False, 1.0, SettingsProperties.VOLUME)
    # volumeConstraints = Constraints(-12, 0, 12, False, True, 1.0, SettingsProperties.VOLUME)
    # constraints: Dict[str, Constraints] = {}

    '''
    settings = {
        # 'output_via_espeak': False,
        SettingsProperties.PLAYER: Players.INTERNAL,
        SettingsProperties.PITCH: 0,
        SettingsProperties.PIPE: False,
        SettingsProperties.SPEED: 0,
        SettingsProperties.VOICE: '',
        SettingsProperties.VOLUME: 0
    }
    '''
    #  supported_settings: Dict[str, str | int | bool] = settings
    initialized: bool = False
    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _logger: BasicLogger = None

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(*args, **kwargs)
        BaseEngineSettings(clz.service_ID)
        if ESpeakSettings.initialized:
            return
        ESpeakSettings.initialized = True
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        ESpeakSettings.init_settings()
        SettingsMap.set_is_available(clz.service_ID, Reason.AVAILABLE)

    @classmethod
    def init_settings(cls):
        SettingsMap.define_service(ServiceType.ENGINE, cls.service_ID,
                                   cls.displayName)
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        speed_constraints_validator = ConstraintsValidator(SettingsProperties.SPEED,
                                                           cls.engine_id,
                                                           BaseServiceSettings.ttsSpeedConstraints)

        pitch_constraints: Constraints = Constraints(0, 50, 99, True, False, 1.0,
                                                     SettingsProperties.PITCH)
        pitch_constraints_validator = ConstraintsValidator(SettingsProperties.PITCH,
                                                           cls.engine_id,
                                                           pitch_constraints)

        volumeConversionConstraints: Constraints = Constraints(minimum=1, default=100,
                                                               maximum=200, integer=True,
                                                               decibels=False, scale=1.0,
                                                               property_name=SettingsProperties.VOLUME,
                                                               midpoint=100, increment=5)
        volume_constraints_validator = ConstraintsValidator(
                SettingsProperties.VOLUME,
                cls.engine_id,
                volumeConversionConstraints)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOLUME,
                                   volume_constraints_validator)

        audio_validator: StringValidator
        audio_converter_validator = StringValidator(SettingsProperties.CONVERTER,
                                                    cls.engine_id,
                                                    allowed_values=[Services.LAME_ID])

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.CONVERTER,
                                   audio_converter_validator)

        language_validator: StringValidator
        language_validator = StringValidator(SettingsProperties.LANGUAGE, cls.engine_id,
                                             allowed_values=[], min_length=2,
                                             max_length=5)
        voice_validator: StringValidator
        voice_validator = StringValidator(SettingsProperties.VOICE, cls.engine_id,
                                          allowed_values=[], min_length=1, max_length=10,
                                          default='')
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingsProperties.PIPE, cls.engine_id,
                                       default=False)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, cls.engine_id,
                                        default=False)
        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        valid_players: List[str] = [Players.SFX, Players.WINDOWS, Players.APLAY,
                                    Players.PAPLAY, Players.AFPLAY, Players.SOX,
                                    Players.MPLAYER, Players.MPG321, Players.MPG123,
                                    Players.MPG321_OE_PI, Players.INTERNAL]
        player_validator: StringValidator
        player_validator = StringValidator(SettingsProperties.PLAYER, cls.engine_id,
                                           allowed_values=valid_players,
                                           default=Players.MPLAYER)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.LANGUAGE,
                                   language_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOICE,
                                   voice_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PIPE,
                                   pipe_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.SPEED,
                                   speed_constraints_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PITCH,
                                   pitch_constraints_validator)
        # SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOLUME,
        #                           volume_constraints_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER,
                                   player_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.CACHE_SPEECH,
                                       cache_validator)

    @classmethod
    def isSupportedOnPlatform(cls) -> bool:
        return (SystemQueries.isLinux() or SystemQueries.isWindows()
                or SystemQueries.isOSX())

    @classmethod
    def isInstalled(cls) -> bool:
        installed: bool = False
        if cls.isSupportedOnPlatform():
            installed = True
        return installed

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        return SettingsMap.is_valid_property(cls.service_ID, setting)

    @classmethod
    def available(cls):
        try:
            subprocess.run(['espeak', '--version'], stdout=(open(os.path.devnull, 'w')),
                           universal_newlines=True, stderr=subprocess.STDOUT)
        except AbortException:
            reraise(*sys.exc_info())
        except:
            return False
        return True
