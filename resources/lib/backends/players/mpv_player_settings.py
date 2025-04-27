# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess

from backends.settings.i_validators import INumericValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, SimpleStringValidator,
                                          StringValidator, Validator)
from common.config_exception import UnusableServiceException
from common.constants import Constants
from common.logger import *
from common.service_status import Progress, ServiceStatus
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
    _service_status: ServiceStatus = ServiceStatus()

    @classmethod
    def config_settings(cls, *args, **kwargs) -> ServiceStatus:
        if cls.initialized:
            return cls.get_status()
        cls.check_is_supported_on_platform()
        cls.check_is_installed()
        if cls._service_status.status != Status.OK:
            SettingsMap.set_available(cls.service_key, cls._service_status)
            raise UnusableServiceException(cls.service_key,
                                           cls._service_status,
                                           msg='')
        cls.initialized = True
        cls._config()
        cls.check_is_available()
        cls.check_is_usable()
        cls.is_usable()
        return cls.get_status()

    @classmethod
    def _config(cls):

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

        if MY_LOGGER.isEnabledFor(DEBUG):
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
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'About to configure CACHE_SPEECH')
        cache_validator: BoolValidator
        cache_validator = BoolValidator(cls.CACHE_SPEECH_KEY,
                                        default=True)
        SettingsMap.define_setting(cache_validator.service_key,
                                   cache_validator)

        allowed_player_modes: List[str] = [
            PlayerMode.FILE.value,
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
    def check_is_supported_on_platform(cls) -> None:
        if cls._service_status.progress == Progress.START:
            supported: bool = (SystemQueries.isLinux() or SystemQueries.isWindows()
                               or SystemQueries.isOSX())
            cls._service_status.progress = Progress.SUPPORTED
            if not supported:
                cls._service_status.status = Status.FAILED
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                            f'status: {cls._service_status.status}')

    @classmethod
    def check_is_installed(cls) -> None:
        # Don't have a test for installed, just move on to available
        if (cls._service_status.progress == Progress.SUPPORTED
                and cls._service_status.status == Status.OK):
            cls._service_status.progress = Progress.INSTALLED

    @classmethod
    def check_is_available(cls) -> None:
        """
        Determines if the player is functional. The test is only run once and
        remembered.

        :return:
        """
        if (cls._service_status.progress == Progress.INSTALLED
                and cls._service_status.status == Status.OK):
            success: bool = False
            completed: subprocess.CompletedProcess | None = None
            try:
                args = cls._availableArgs
                args.append('--version')
                env = os.environ.copy()
                if Constants.PLATFORM_WINDOWS:
                    #  MY_LOGGER.info(f'Running command: Windows')
                    completed = subprocess.run(args, stdin=None, capture_output=True,
                                               text=True, env=env, close_fds=True,
                                               encoding='utf-8', shell=False,
                                               check=True,
                                               creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    #  MY_LOGGER.info(f'Running command: Linux')
                    completed = subprocess.run(args, stdin=None, capture_output=True,
                                               text=True, env=env, close_fds=True,
                                               encoding='utf-8', shell=False,
                                               check=True)
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

            cls._service_status.progress = Progress.AVAILABLE
            if not success:
                cls._service_status.status = Status.FAILED
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                            f'status: {cls._service_status.status}')

    @classmethod
    def check_is_usable(cls) -> None:
        """
        Determine if the engine is usable in this environment. Perhaps there is
        no player that can work with this engine available.
        :return None:
        """
        # eSpeak should always be usable, since it comes with its own player
        if cls._service_status.progress == Progress.AVAILABLE:
            if cls._service_status.status == Status.OK:
                cls._service_status.progress = Progress.USABLE
            SettingsMap.set_available(cls.service_key, cls._service_status)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                            f'status: {cls._service_status.status}')

    @classmethod
    def is_usable(cls) -> bool:
        """
        Determines if there are any known reasons that this service is not
        functional. Runs the check_ methods to determine the result.

        :return True IFF functional:
        :raises UnusableServiceException: when this service is not functional
        :raises ValueError: when called before this module fully initialized.
        """
        if (cls._service_status.status != Status.OK or
                cls._service_status.progress != Progress.USABLE):
            raise UnusableServiceException(service_key=cls.service_key,
                                           reason=cls._service_status,
                                           msg='')
        return True

    @classmethod
    def get_status(cls) -> ServiceStatus:
        return cls._service_status
