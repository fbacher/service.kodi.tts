from __future__ import annotations  # For union operator |

import os
import subprocess
import sys

from common import *

from backends.audio.sound_capabilties import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.i_validators import INumericValidator, ValueType
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, NumericValidator,
                                          StringValidator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Backends, PlayerMode, Players
from common.system_queries import SystemQueries

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ESpeakSettings(BaseServiceSettings):
    # Only returns .wav files, or speech
    ID: str = Backends.ESPEAK_ID
    engine_id = Backends.ESPEAK_ID
    service_ID: str = Services.ESPEAK_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
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
        cls._logger.debug(f'Adding eSpeak to engine service')
        service_properties = {Constants.NAME: cls.displayName}
        SettingsMap.define_service(ServiceType.ENGINE, cls.service_ID,
                                   service_properties)
        x = SettingsMap.get_services_for_service_type(ServiceType.ENGINE)
        cls._logger.debug(f'Got back {len(x)} services')

        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        pitch_validator: NumericValidator
        pitch_validator = NumericValidator(SettingsProperties.PITCH,
                                           cls.service_ID,
                                           minimum=0, maximum=99, default=50,
                                           is_decibels=False, is_integer=True,
                                           increment=1)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PITCH,
                                   pitch_validator)

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

        allowed_player_modes: List[str] = [
            PlayerMode.SLAVE_FILE.value,
            PlayerMode.FILE.value,
            PlayerMode.PIPE.value
        ]
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(SettingsProperties.PLAYER_MODE,
                                                cls.service_ID,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.SLAVE_FILE.value)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER_MODE,
                                   player_mode_validator)
        # pipe_validator: BoolValidator
        # pipe_validator = BoolValidator(SettingsProperties.PIPE, cls.engine_id,
        #                                default=False)

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
                                             max_length=10)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.LANGUAGE,
                                   language_validator)

        voice_validator: StringValidator
        voice_validator = StringValidator(SettingsProperties.VOICE, cls.engine_id,
                                          allowed_values=[], min_length=1, max_length=20,
                                          default=None)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOICE,
                                   voice_validator)
        # SettingsMap.define_setting(cls.service_ID, SettingsProperties.PIPE,
        #                            pipe_validator)

        # 'normal speed' is 175 words per minute.
        # The slowest supported rate appears to be about 70, any slower doesn't
        # seem to make any real difference. The maximum speed is unbounded, but
        # 4x (4 * 175 = 700) is hard to listen to.
        # TTS scale is based upon mpv/mplayer which is a multiplier which
        # has 1 = no change in speed, 0.25 slows down by 4, and 4 speeds up by 4
        #
        # In other words espeak speed = 175 * mpv speed

        speed_validator: NumericValidator
        speed_validator = NumericValidator(SettingsProperties.SPEED,
                                           cls.service_ID,
                                           minimum=43, maximum=700,
                                           default=176,
                                           is_decibels=False,
                                           is_integer=True, increment=45)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.SPEED,
                                   speed_validator)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER,
                                   player_validator)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, cls.service_ID,
                                        default=False)

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
