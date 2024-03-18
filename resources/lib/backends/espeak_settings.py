from __future__ import annotations  # For union operator |

import os
import subprocess
import sys

from common import *

from backends.audio.sound_capabilties import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.i_validators import INumericValidator, ValueType
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, NumericValidator,
                                          StringValidator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Backends, Players
from common.system_queries import SystemQueries

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ESpeakSettings(BaseServiceSettings):
    # Only returns .wav files, or speech
    ID: str = Backends.ESPEAK_ID
    engine_id = Backends.ESPEAK_ID
    service_ID: str = Services.ESPEAK_ID
    displayName = 'eSpeak'

 
    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False
    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE,
                                             ServiceType.INTERNAL_PLAYER]
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
        service_properties = {Constants.NAME: cls.displayName}
        SettingsMap.define_service(ServiceType.ENGINE, cls.service_ID,
                                   service_properties)
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        pitch_constraints: Constraints = Constraints(minimum=0, default=50,
                                                     maximum=99, integer=True,
                                                     decibels=False, scale=1.0,
                                                     property_name=SettingsProperties.PITCH,
                                                     midpoint=50, increment=1.0,
                                                     tts_line_value=50)

        pitch_constraints_validator = ConstraintsValidator(SettingsProperties.PITCH,
                                                           cls.engine_id,
                                                           pitch_constraints)


        volume_validator: NumericValidator
        volume_validator = NumericValidator(SettingsProperties.VOLUME,
                                            cls.service_ID,
                                            minimum=0, maximum=200,
                                            default=100, is_decibels=False,
                                            is_integer=True)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.VOLUME,
                                   volume_validator)

        audio_validator: StringValidator
        audio_converter_validator = StringValidator(SettingsProperties.CONVERTER,
                                                    cls.engine_id,
                                                    allowed_values=[Services.LAME_ID])

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.CONVERTER,
                                   audio_converter_validator)

        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingsProperties.PIPE, cls.engine_id,
                                       default=False)

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        valid_players: List[str] = [Players.SFX, Players.WINDOWS, Players.APLAY,
                                    Players.PAPLAY, Players.AFPLAY, Players.SOX,
                                    Players.MPLAYER, Players.MPV, Players.MPG321,
                                    Players.MPG123, Players.MPG321_OE_PI,
                                    Players.INTERNAL]
        player_validator: StringValidator
        player_validator = StringValidator(SettingsProperties.PLAYER, cls.engine_id,
                                           allowed_values=valid_players,
                                           default=Players.MPLAYER)

        language_validator: StringValidator
        language_validator = StringValidator(SettingsProperties.LANGUAGE, cls.engine_id,
                                             allowed_values=[], min_length=2,
                                             max_length=5)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.LANGUAGE,
                                   language_validator)

        voice_validator: StringValidator
        voice_validator = StringValidator(SettingsProperties.VOICE, cls.engine_id,
                                          allowed_values=[], min_length=1, max_length=10,
                                          default=None)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOICE,
                                   voice_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PIPE,
                                   pipe_validator)

        # ttsPitchConstraints: Constraints = Constraints(0, 50, 99, True, False, 1.0,
        #                                        SettingsProperties.PITCH, 50, 1.0)

        speedConstraints: Constraints = Constraints(minimum=43, default=175,
                                                    maximum=700, integer=True,
                                                    decibels=False, scale=1.0,
                                                    property_name=SettingsProperties.SPEED,
                                                    midpoint=175, increment=45,
                                                    tts_line_value=175)

        #  Speed in words per minute. Default 175
        speed_constraints_validator = ConstraintsValidator(SettingsProperties.SPEED,
                                                           cls.engine_id,
                                                           speedConstraints)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.SPEED,
                                   speed_constraints_validator)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PITCH,
                                   pitch_constraints_validator)
        # SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOLUME,
        #                           volume_constraints_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER,
                                   player_validator)


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
