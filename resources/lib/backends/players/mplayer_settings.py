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
from common.logger import BasicLogger
from common.setting_constants import AudioType, Backends, PlayerMode, Players
from common.settings_low_level import SettingProp
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class MPlayerSettings:
    ID = Players.MPLAYER
    service_id: str = Services.MPLAYER_ID
    service_type: ServiceType = ServiceType.PLAYER
    MPLAYER_KEY: ServiceID = ServiceID(service_type, service_id)
    service_key: ServiceID = MPLAYER_KEY
    CACHE_SPEECH_KEY = MPLAYER_KEY.with_prop(SettingProp.CACHE_SPEECH)
    VOLUME_KEY: ServiceID = MPLAYER_KEY.with_prop(SettingProp.VOLUME)
    PLAYER_MODE_KEY = MPLAYER_KEY.with_prop(SettingProp.PLAYER_MODE)
    SPEED_KEY: ServiceID = MPLAYER_KEY.with_prop(SettingProp.SPEED)
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    displayName = 'MPlayer'

    """
    In an attempt to bring some consistency between the various players, engines and 
    converters, standard "TTS" constraints are defined which every engine, player_key,
    converter, etc. is to convert to/from. Hopefully this will help these settings
    to remain sane regardless of the combination of services used. 
    
    So, if an engine does not produce volume that matches the db-scale based
    ttsVolumeConstraints, then the engine needs to create a custom converter. 
    Here, volumeConversionConstraints performs that function. ResponsiveVoice
    uses a percent scale with a default value of 1.0 and a max of 2.0. In 
    ResponsiveVoice.getEngineVolume you can see the conversion using:
    
        volume = cls.volumeConstraints.translate_value(
                                        cls.volumeConversionConstraints, volumeDb)
    
    """
    _supported_input_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
    _supported_output_formats: List[AudioType] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER,
                                             ServiceType.TRANSCODER]
    SoundCapabilities.add_service(service_key, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    _available: bool | None = None
    _availableArgs = (Constants.MPLAYER_PATH, '--help')
    initialized: bool = False

    @classmethod
    def config_settings(cls, *args, **kwargs):
        if cls.initialized:
            return
        cls.initialized = True
        cls._config()

    @classmethod
    def _config(cls):
        # Not supporting Pitch changes with mplayer at this time

        # TTS Speed constraints defined as linear from 0.25 to 4 with 1 being 100%
        # speed. 0.25 is 1/4 speed, 4 is 4x speed. This fits nicely with Mplayer
        # speed settings.
        # Since saving the value in settings.xml as a float makes it more difficult
        # for a human to work with, we save it as an int by scaling it by 100 when
        # it is saved.
        #

        name_validator: StringValidator
        name_validator = StringValidator(service_key=cls.NAME_KEY,
                                         allowed_values=[cls.displayName],
                                         allow_default=False,
                                         const=True
                                         )

        SettingsMap.define_setting(cls.NAME_KEY, name_validator)

        cache_service_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_PATH)
        cache_path_val: SimpleStringValidator
        cache_path_val = SimpleStringValidator(cache_service_key,
                                               value=SettingProp.CACHE_PATH_DEFAULT)
        SettingsMap.define_setting(cache_path_val.service_key,
                                   cache_path_val)

        cache_suffix_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix: str = Backends.ENGINE_CACHE_CODE[Services.MPLAYER_ID]

        cache_suffix_val: SimpleStringValidator
        cache_suffix_val = SimpleStringValidator(cache_suffix_key,
                                                 value=cache_suffix)
        SettingsMap.define_setting(cache_suffix_val.service_key,
                                   cache_suffix_val)

        speed_validator: NumericValidator
        speed_validator = NumericValidator(cls.SPEED_KEY,
                                           minimum=.25, maximum=3,
                                           default=1,
                                           is_decibels=False,
                                           is_integer=False)
        SettingsMap.define_setting(speed_validator.service_key,
                                   speed_validator)
        """
         MPlayer uses both percentage and decibel volume scales.
         The decibel scale is used for the (-af) audio filter with range -200db .. +40db.
         The percent scale is used for the --volume flag (there are multiple ways to
         specify volume, including json).
        
         TTS uses a decibel scale with range -12db .. +12db. Just convert the
         values with no change. Do this by simply using the TTS volume constraints
        """
        volume_validator: NumericValidator
        volume_validator = NumericValidator(cls.VOLUME_KEY,
                                            minimum=5, maximum=400,
                                            default=100, is_decibels=False,
                                            is_integer=False)
        SettingsMap.define_setting(volume_validator.service_key,
                                   volume_validator)
        # TODO: Using a constant-value validator just to reflect that this player_key supports
        #       a cached in order to determine if PLAYER_MODE.SLAVE_FILE should be used.
        #       This causes logged entries indicating that CACHE_SPEECH can not be
        #       saved to settings.xml (because we dont need to for this constant).
        cache_validator: BoolValidator
        cache_validator = BoolValidator(cls.CACHE_SPEECH_KEY,
                                        default=True, const=True)
        SettingsMap.define_setting(cache_validator.service_key,
                                   cache_validator)
        '''
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingProp.PIPE, cls.setting_id,
                                       default=False)
        SettingsMap.define_setting(cls.setting_id, SettingProp.PIPE,
                                   pipe_validator)
       '''
        allowed_player_modes: List[str] = [
            PlayerMode.FILE.value
        ]
        MY_LOGGER.debug(f'About to import mplayer PLAYER_MODE')
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(cls.PLAYER_MODE_KEY,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.FILE.value)
        SettingsMap.define_setting(player_mode_validator.service_key,
                                   player_mode_validator)

        x = SettingsMap.get_srvc_props_for_service_type(ServiceType.PLAYER)
        MY_LOGGER.debug(f'PLAYERS len: {len(x)}')
        for service_id, label in x:
            MY_LOGGER.debug(f'{service_id} {label}')

    @classmethod
    def check_availability(cls) -> Reason:
        availability: Reason = Reason.AVAILABLE
        if not cls.isSupportedOnPlatform():
            availability = Reason.NOT_SUPPORTED
        if not cls.isInstalled():
            availability = Reason.NOT_AVAILABLE
        elif not cls.is_available():
            availability = Reason.BROKEN
        SettingsMap.set_is_available(cls.service_key, availability)
        return availability

    @classmethod
    def isSupportedOnPlatform(cls) -> bool:
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
        return cls.is_available()

    @classmethod
    def is_available(cls) -> bool:
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
            args: List = list(cls._availableArgs)
            env = os.environ.copy()
            completed: subprocess.CompletedProcess | None = None
            if Constants.PLATFORM_WINDOWS:
                MY_LOGGER.info(f'Running command: Windows')
                # mplayer returns RC=1
                completed = subprocess.run(args, stdin=None, capture_output=True,
                                           text=True, env=env, close_fds=True,
                                           encoding='utf-8', shell=False, check=False,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                MY_LOGGER.info(f'Running command: Linux')
                # mplayer returns RC=1
                completed = subprocess.run(args, stdin=None, capture_output=True,
                                           text=True, env=env, close_fds=True,
                                           encoding='utf-8', shell=False, check=False)
            for line in completed.stdout.split('\n'):
                line: str
                if len(line) > 0:
                    if line.startswith('MPlayer'):
                        success = True
                        break
            # RC is normally 1
            if completed.returncode != 1:
                success = False
        except (subprocess.CalledProcessError, FileNotFoundError):
            MY_LOGGER.exception('')
        except OSError:
            MY_LOGGER.exception('')
        except Exception:
            MY_LOGGER.exception('')

        cls._available = success
        MY_LOGGER.debug(f'mplayer available: {success}')
        return cls._available
