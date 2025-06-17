# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess

from backends.settings.i_validators import INumericValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.service_types import ServiceKey, Services, ServiceType
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (BoolValidator,
                                          NumericValidator, SimpleStringValidator,
                                          StringValidator, Validator)
from common.config_exception import UnusableServiceException
from common.constants import Constants
from common.logger import *
from common.message_ids import MessageId
from common.service_status import Progress, ServiceStatus, StatusType
from common.setting_constants import AudioType, Backends, PlayerMode, Players
from common.settings import Settings
from common.settings_low_level import SettingProp
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class MPlayerSettings:
    ID = Players.MPLAYER
    service_id: str = Services.MPLAYER_ID
    service_type: ServiceType = ServiceType.PLAYER
    MPLAYER_KEY: ServiceID = ServiceKey.MPLAYER_KEY
    service_key: ServiceID = MPLAYER_KEY
    CACHE_SPEECH_KEY = MPLAYER_KEY.with_prop(SettingProp.CACHE_SPEECH)
    VOLUME_KEY: ServiceID = MPLAYER_KEY.with_prop(SettingProp.VOLUME)
    PLAYER_MODE_KEY = MPLAYER_KEY.with_prop(SettingProp.PLAYER_MODE)
    SPEED_KEY: ServiceID = MPLAYER_KEY.with_prop(SettingProp.SPEED)
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    displayName: str = MessageId.PLAYER_MPLAYER.get_msg()

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

    _available: bool | None = None
    _availableArgs = (Constants.MPLAYER_PATH, '--help')
    initialized: bool = False
    _service_status: ServiceStatus = ServiceStatus()

    @classmethod
    def config_settings(cls, *args, **kwargs) -> None:
        if cls.initialized:
            return
        cls.check_is_supported_on_platform()
        cls.check_is_installed()
        if cls._service_status.status != Status.OK:
            raise UnusableServiceException(cls.service_key,
                                           cls._service_status,
                                           msg='')
        cls.check_is_available()
        cls.check_is_usable()
        cls.is_usable()
        cls.initialized = True
        cls._config()
        return

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
                                               const=True,
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=True)

        _supported_input_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
        _supported_output_formats: List[AudioType] = []
        _provides_services: List[ServiceType] = [ServiceType.PLAYER,
                                                 ServiceType.TRANSCODER]
        SoundCapabilities.add_service(cls.service_key, _provides_services,
                                      _supported_input_formats,
                                      _supported_output_formats)

        cache_service_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_PATH)
        cache_path_val: SimpleStringValidator
        cache_path_val = SimpleStringValidator(cache_service_key,
                                               value=SettingProp.CACHE_PATH_DEFAULT,
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=True)

        cache_suffix_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix: str = Backends.ENGINE_CACHE_CODE[Services.MPLAYER_ID]

        cache_suffix_val: SimpleStringValidator
        cache_suffix_val = SimpleStringValidator(cache_suffix_key,
                                                 value=cache_suffix,
                                                 define_setting=True,
                                                 service_status=StatusType.OK,
                                                 persist=True)

        speed_validator: NumericValidator
        speed_validator = NumericValidator(cls.SPEED_KEY,
                                           minimum=.25, maximum=3,
                                           default=1,
                                           is_decibels=False,
                                           is_integer=False,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)
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
                                            is_integer=False,
                                            define_setting=True,
                                            service_status=StatusType.OK,
                                            persist=True)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(cls.CACHE_SPEECH_KEY,
                                        default=True, const=True,
                                        define_setting=True,
                                        service_status=StatusType.OK,
                                        persist=False)

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
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(cls.PLAYER_MODE_KEY,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.FILE.value,
                                                define_setting=True,
                                                service_status=StatusType.OK,
                                                persist=True)

    @classmethod
    def check_is_supported_on_platform(cls) -> None:
        if cls._service_status.progress == Progress.START:
            supported: bool = (SystemQueries.isLinux() or SystemQueries.isWindows()
                               or SystemQueries.isOSX())
            cls._service_status.progress = Progress.SUPPORTED
            if not supported:
                cls._service_status.status = Status.FAILED
                cls._service_status.status_summary = StatusType.NOT_ON_PLATFORM
                Settings.set_availability(cls.service_key, StatusType.NOT_ON_PLATFORM)

    @classmethod
    def check_is_installed(cls) -> None:
        # Don't have a test for installed, just move on to available
        if cls._service_status.progress == Progress.SUPPORTED:
            if cls._service_status.status == Status.OK:
                cls._service_status.progress = Progress.INSTALLED
            else:
                cls._service_status.status_summary = StatusType.NOT_FOUND
                Settings.set_availability(cls.service_key, StatusType.NOT_FOUND)

    @classmethod
    def check_is_available(cls) -> None:
        """
        Determines if the player is functional. The test is only run once and
        remembered.

        :return:
        """
        success: bool = False
        if (cls._service_status.progress == Progress.INSTALLED
                and cls._service_status.status == Status.OK):
            completed: subprocess.CompletedProcess | None = None
            try:
                args: List = list(cls._availableArgs)
                env = os.environ.copy()
                completed: subprocess.CompletedProcess | None = None
                if Constants.PLATFORM_WINDOWS:
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'Running command: Windows')
                    # mplayer returns RC=1
                    completed = subprocess.run(args, stdin=None, capture_output=True,
                                               text=True, env=env, close_fds=True,
                                               encoding='utf-8', shell=False, check=False,
                                               creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'Running command: Linux')
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

            cls._service_status.progress = Progress.AVAILABLE
            if not success:
                cls._service_status.status = Status.FAILED
                cls._service_status.status_summary = StatusType.BROKEN
                Settings.set_availability(cls.service_key, StatusType.BROKEN)

    @classmethod
    def check_is_usable(cls) -> None:
        """
        Determine if the player is usable in this environment.
        :return None:
        """
        if cls._service_status.progress == Progress.AVAILABLE:
            if cls._service_status.status == Status.OK:
                cls._service_status.progress = Progress.USABLE
                cls._service_status.status_summary = StatusType.OK
            else:
                cls._service_status.status_summary = StatusType.BROKEN

            SettingsMap.set_available(cls.service_key, cls._service_status.status_summary)

    @classmethod
    def is_usable(cls) -> bool:
        """
        Determines if there are any known reasons that this service is not
        functional. Runs the check_ methods to determine the result.

        :return True IFF functional:
        :raises UnusableServiceException: when this service is not functional
        :raises ValueError: when called before this module fully initialized.
        """
        return SettingsMap.is_available(cls.service_key)

    @classmethod
    def get_status(cls) -> ServiceStatus:
        return cls._service_status
