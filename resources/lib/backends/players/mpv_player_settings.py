# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess

from backends.settings.i_validators import INumericValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, SimpleStringValidator,
                                          StringValidator, Validator)
from common.constants import Constants
from common.logger import *
from common.setting_constants import AudioType, PlayerMode, Players
from common.settings_low_level import SettingProp
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class MPVPlayerSettings:
    ID = Players.MPV
    service_id: str = Services.MPV_ID
    service_type: ServiceType = ServiceType.PLAYER
    service_key: ServiceID = ServiceID(service_type, service_id)
    CACHE_SPEECH_KEY = service_key.with_prop(SettingProp.CACHE_SPEECH)
    MPV_VOLUME_KEY: ServiceID = service_key.with_prop(SettingProp.VOLUME)
    PLAYER_MODE_KEY = service_key.with_prop(SettingProp.PLAYER_MODE)
    SPEED_KEY: ServiceID = service_key.with_prop(SettingProp.SPEED)
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    displayName = 'MPV'

    """
    In an attempt to bring some consistency between the various players, engines and 
    converters, standard "TTS" constraints are defined which every engine, player_key,
    converter, etc. is to convert to/from. Hopefully this will help these settings
    to remain sane regardless of the combination of services used. 
    
    So, if an engine does not produce volume that matches the db-scale based
    ttsVolumeConstraints, then the engine needs to create a customer converter. 
    Here, volumeConversionConstraints performs that function. ResponsiveVoice
    uses a percent scale with a default value of 1.0 and a max of 2.0. In 
    ResponsiveVoice.getEngineVolume you can see the conversion using:
    
        volume = cls.volumeConstraints.translate_value(
                                        cls.volumeConversionConstraints, volumeDb)
    
    """
    _supported_input_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
    _supported_output_formats: List[AudioType] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER, ServiceType.TRANSCODER]
    SoundCapabilities.add_service(service_key, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    _available: bool | None = None
    _availableArgs = [Constants.MPV_PATH, '--version']

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False

    @classmethod
    def config_settings(cls, *args, **kwargs):
        if cls.initialized:
            return
        cls.initialized = True
        cls._config()

    @classmethod
    def _config(cls):
        if not cls.check_availability():
            MY_LOGGER.info(f'Service {cls.service_id} is NOT available on this system')
            return
        #  service_properties = {Constants.NAME: cls.displayName}
        #  SettingsMap.define_service_properties(cls.service_key, service_properties)

        # Not supporting Pitch changes with MPV_Player at this time

        """
         MPV uses both percentage and decibel volume scales.
         The decibel scale is used for the (-af) audio filter with range -200db .. +40db.
         The percent scale is used for the --volume flag (there are multiple ways to
         specify volume, including json).

         TTS uses a decibel scale with range -12db .. +12db. Just convert the
         values with no change. Do this by simply using the TTS volume constraints
        """
        '''
        tts_volume_validator: INumericValidator
        key: ServiceID = ServiceID(ServiceType.TTS, setting_id='')
        tts_volume_validator = SettingsMap.get_validator(key,
                                                         SettingProp.VOLUME)
        '''
        name_validator: SimpleStringValidator
        name_validator = SimpleStringValidator(service_key=cls.NAME_KEY,
                                               value=cls.displayName,
                                               const=True)
        SettingsMap.define_setting(cls.NAME_KEY, name_validator)

        MY_LOGGER.debug(f'About to configure VOLUME')
        volume_validator: NumericValidator
        volume_validator = NumericValidator(cls.MPV_VOLUME_KEY,
                                            minimum=5, maximum=400,
                                            default=100, is_decibels=False,
                                            is_integer=False)
        SettingsMap.define_setting(volume_validator.service_key,
                                   volume_validator)

        speed_validator: NumericValidator
        speed_validator = NumericValidator(cls.SPEED_KEY,
                                           minimum=0.25, maximum=3,
                                           is_decibels=False,
                                           is_integer=False)
        SettingsMap.define_setting(speed_validator.service_key,
                                   speed_validator)

        # TODO: CACHE_SPEECH does not need to be persisted for players. It
        #       is just reflecting whether the player_key supports caching (or rather
        #       SLAVE_FILE. However, this is generating benign warnings hat
        #       the settings can't be saved due to the setting not being in
        #       settings.xml template.
        MY_LOGGER.debug(f'About to configure CACHE_SPEECH')
        cache_validator: BoolValidator
        cache_validator = BoolValidator(cls.CACHE_SPEECH_KEY,
                                        default=True)
        SettingsMap.define_setting(cache_validator.service_key,
                                   cache_validator)

        allowed_player_modes: List[str] = [
            PlayerMode.FILE.value
        ]
        default_mode: PlayerMode = PlayerMode.FILE.value
        if not Constants.PLATFORM_WINDOWS:
            allowed_player_modes.append(PlayerMode.SLAVE_FILE.value)
            default_mode = PlayerMode.SLAVE_FILE.value

        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(cls.PLAYER_MODE_KEY,
                                                allowed_values=allowed_player_modes,
                                                default=default_mode)
        SettingsMap.define_setting(player_mode_validator.service_key,
                                   player_mode_validator)
        '''
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingProp.PIPE, cls.setting_id,
                                       default=False)
        SettingsMap.define_setting(cls.setting_id, SettingProp.PIPE,
                                   pipe_validator)
        '''
    @classmethod
    def check_availability(cls) -> Reason:
        availability: Reason = Reason.AVAILABLE
        if not cls.isSupportedOnPlatform():
            availability = Reason.NOT_SUPPORTED
        if not cls.isInstalled():
            availability = Reason.NOT_AVAILABLE
        elif not cls.available():
            availability = Reason.BROKEN
        SettingsMap.set_is_available(cls.service_key, availability)
        return availability

    @staticmethod
    def isSupportedOnPlatform() -> bool:
        """
        Determines if this player_key is supported on this platform (i.e. Linux, Windows,
        OSX, etc.).
        :return: True if supported on the current platform
        """
        return (SystemQueries.isLinux() or SystemQueries.isWindows()
                or SystemQueries.isOSX())

    @classmethod
    def isInstalled(cls) -> bool:
        if not cls.isSupportedOnPlatform():
            return False
        return cls.available()

    @classmethod
    def available(cls) -> bool:
        """
        Determines if the player_key is functional. The test is only run once and
        remembered.

        :return:
        """
        success: bool = False
        if cls._available is not None:
            return cls._available
        completed: subprocess.CompletedProcess | None = None
        try:
            args = cls._availableArgs
            args.append('--version')
            env = os.environ.copy()
            completed: subprocess.CompletedProcess | None = None
            if Constants.PLATFORM_WINDOWS:
                MY_LOGGER.info(f'Running command: Windows')
                completed = subprocess.run(args, stdin=None, capture_output=True,
                                           text=True, env=env, close_fds=True,
                                           encoding='utf-8', shell=False, check=True,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                MY_LOGGER.info(f'Running command: Linux')
                completed = subprocess.run(args, stdin=None, capture_output=True,
                                           text=True, env=env, close_fds=True,
                                           encoding='utf-8', shell=False, check=True)
            for line in completed.stdout.split('\n'):
                line: str
                if len(line) > 0:
                    if line.startswith('mpv'):
                        success = True
                        break
            if completed.returncode != 0:
                success = False
        except (subprocess.CalledProcessError, FileNotFoundError):
            #  MY_LOGGER.exception('')
            pass
        except OSError:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.exception('')
        except Exception:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.exception('')

        cls._available = success
        MY_LOGGER.debug(f'mpv available: {success}')
        return cls._available
