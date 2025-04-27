# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.settings.i_validators import INumericValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import PlayerType, Services, ServiceType
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, StringValidator, Validator)
from common.config_exception import UnusableServiceException
from common.constants import Constants
from common.logger import BasicLogger
from common.service_status import Progress, ServiceStatus
from common.setting_constants import AudioType, PlayerMode, Players
from common.settings_low_level import SettingProp
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class BuiltinPlayerSettings:
    """
    Defines a dummy, built-in-player_key, such as provided by eSpeak. This player_key
    provides values that make the configuration and running happy. The
    BuiltInPlayer doesn't do anything. The eSpeak engine, for example, recognizes
    when it's player_key is Builtin, and modifies its command line appropriately.
    """
    ID = Players.BUILT_IN
    service_id: Services = Services.BUILT_IN_PLAYER_ID
    service_type: ServiceType = ServiceType.PLAYER
    service_key: ServiceID = ServiceID(service_type, service_id)
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    displayName = 'Built-in'

    settings: Dict[str, Validator] = {}

    _supported_input_formats: List[AudioType] = [AudioType.BUILT_IN]
    _supported_output_formats: List[AudioType] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_key, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False
    _service_status: ServiceStatus = ServiceStatus()

    @classmethod
    def config_settings(cls, *args, **kwargs) -> ServiceStatus:
        if cls.initialized:
            return cls.get_status()
        # Basic checks that don't depend on config
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
        #  SettingsMap.define_service_properties(cls.service_key,
        #                                        service_properties)

        t_service_key: ServiceID
        t_service_key = cls.service_key.with_prop(SettingProp.VOLUME)
        tts_volume_validator: INumericValidator
        tts_volume_validator = SettingsMap.get_validator(cls.service_key)
        volume_validator: NumericValidator
        volume_validator = NumericValidator(t_service_key,
                                            minimum=5, maximum=400,
                                            default=100, is_decibels=False,
                                            is_integer=False)
        SettingsMap.define_setting(volume_validator.service_key,
                                   volume_validator)

        t_service_key = cls.service_key.with_prop(SettingProp.SPEED)
        speed_validator: NumericValidator
        speed_validator = NumericValidator(t_service_key,
                                           minimum=0.25, maximum=3,
                                           is_decibels=False,
                                           is_integer=False)
        SettingsMap.define_setting(speed_validator.service_key,
                                   speed_validator)

        t_service_key = cls.service_key.with_prop(SettingProp.CACHE_SPEECH)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(t_service_key,
                                        default=False)
        SettingsMap.define_setting(cache_validator.service_key,
                                   cache_validator)

        allowed_player_modes: List[str] = [
            PlayerMode.ENGINE_SPEAK.value
        ]
        t_service_key = cls.service_key.with_prop(SettingProp.PLAYER_MODE)
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(t_service_key,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.ENGINE_SPEAK.value)
        SettingsMap.define_setting(player_mode_validator.service_key,
                                   player_mode_validator)

    @classmethod
    def check_is_supported_on_platform(cls) -> None:
        if cls._service_status.progress == Progress.START:
            cls._service_status.progress = Progress.SUPPORTED
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
        success: bool = False
        if (cls._service_status.progress == Progress.INSTALLED
                and cls._service_status.status == Status.OK):
            MY_LOGGER.debug(f'{cls.displayName} available: {success}')
            cls._service_status.progress = Progress.AVAILABLE

    @classmethod
    def check_is_usable(cls) -> None:
        """
        Determine if the player is usable in this environment.
        :return None:
        """
        if cls._service_status.progress == Progress.AVAILABLE:
            if cls._service_status.status == Status.OK:
                cls._service_status.progress = Progress.USABLE
            SettingsMap.set_available(cls.service_key, cls._service_status)

    @classmethod
    def is_usable(cls) -> bool:
        """
        Determines if there are any known reasons that this service is not
        functional. Runs the check_ methods to determine the result.

        :return True IFF functional:
        :raises UnusableServiceException: when this service is not functional
        :raises ValueError: when called before this module fully initialized.
        """
        MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                        f'status: {cls._service_status.status}')
        if cls._service_status.status != Status.OK:
            raise UnusableServiceException(service_key=cls.service_key,
                                           reason=cls._service_status,
                                           msg='')
        check_state: Progress = cls._service_status.progress
        MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                        f'status: {cls._service_status.status}')
        if check_state != Progress.USABLE:
            raise ValueError(f'Service: {cls.service_key} not fully initialized')
        return True

    @classmethod
    def get_status(cls) -> ServiceStatus:
        return cls._service_status
