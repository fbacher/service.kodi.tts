# coding=utf-8
from __future__ import annotations  # For union operator |

import xbmc

from backends.audio import PLAYSFX_HAS_USECACHED
from backends.engines.base_engine_settings import BaseEngineSettings
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.service_types import Services, ServiceType, ServiceID
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, StringValidator, Validator)
from common.config_exception import UnusableServiceException
from common.constants import Constants
from common.logger import BasicLogger
from common.service_status import Progress, ServiceStatus
from common.setting_constants import AudioType, PlayerMode, Players
from common.settings import Settings
from common.settings_low_level import SettingProp

MY_LOGGER = BasicLogger.get_logger(__name__)


class SFXSettings:
    ID = Players.SFX
    service_id: str = Services.SFX_ID
    service_type: ServiceType = ServiceType.PLAYER
    SFX_KEY: ServiceID = ServiceID(service_type, service_id)
    service_key: ServiceID = SFX_KEY
    CACHE_SPEECH_KEY = SFX_KEY.with_prop(SettingProp.CACHE_SPEECH)
    SFX_VOLUME_KEY: ServiceID = SFX_KEY.with_prop(SettingProp.VOLUME)
    PLAYER_MODE_KEY = SFX_KEY.with_prop(SettingProp.PLAYER_MODE)
    SPEED_KEY: ServiceID = SFX_KEY.with_prop(SettingProp.SPEED)
    displayName = 'SFX'

    """
    SFX is a simple player_key that uses Kodi for playing the audio. Its primary
    benefit is that it is always available, therefore providing a critical
    service when none other is available
    """

    _supported_input_formats: List[AudioType] = [AudioType.WAV]
    _supported_output_formats: List[AudioType] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_key, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    initialized: bool = False
    _available: bool | None = None
    _service_status: ServiceStatus = ServiceStatus()

    @classmethod
    def config_settings(cls, *args, **kwargs):
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
        #  BaseEngineSettings.config_settings(SFXSettings.service_key)
        cls._config()
        cls.check_is_available()
        cls.check_is_usable()
        cls.is_usable()
        return cls.get_status()

    @classmethod
    def _config(cls):
        #  service_properties = {Constants.NAME: cls.displayName}
        #  SettingsMap.define_service_properties(cls.service_key, service_properties)

        #  tts_volume_validator: INumericValidator
        #  tts_volume_validator = SettingsMap.get_validator(SettingProp.TTS_SERVICE,
        #                                                   SettingProp.VOLUME)
        volume_validator = NumericValidator(cls.SFX_VOLUME_KEY,
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
        #       SLAVE_FILE. However, this is generating benign warnings that
        #       the settings can't be saved due to the setting not being in
        #       settings.xml template.
        cache_validator: BoolValidator
        cache_validator = BoolValidator(cls.CACHE_SPEECH_KEY,
                                        default=True)
        SettingsMap.define_setting(cache_validator.service_key,
                                   cache_validator)

        allowed_player_modes: List[str] = [
            PlayerMode.FILE.value
        ]
        default_mode: PlayerMode = PlayerMode.FILE.value

        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(cls.PLAYER_MODE_KEY,
                                                allowed_values=allowed_player_modes,
                                                default=default_mode)
        SettingsMap.define_setting(player_mode_validator.service_key,
                                   player_mode_validator)

        # Can use LAME to convert to wave. This code is untested
        # TODO: test, expose capability in settings config

        tmp_key = cls.service_key.with_prop(SettingProp.TRANSCODER)
        audio_validator: StringValidator
        audio_converter_validator = StringValidator(tmp_key,
                                                    allowed_values=[Services.LAME_ID,
                                                                    Services.MPLAYER_ID])
        SettingsMap.define_setting(audio_converter_validator.service_key,
                                   audio_converter_validator)

        Settings.set_current_input_format(cls.service_key, AudioType.WAV)

    @classmethod
    def isSettingSupported(cls, service_key: ServiceID) -> bool:
        return SettingsMap.is_valid_setting(service_key)

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
            if not (xbmc and hasattr(xbmc, 'stopSFX') and PLAYSFX_HAS_USECACHED):
                cls._service_status.status = Status.FAILED

    @classmethod
    def check_is_usable(cls) -> None:
        """
        Determine if the player is usable in this environment.
        :return None:
        """
        if cls._service_status.progress == Progress.AVAILABLE:
            if cls._service_status.status == Status.OK:
                cls._service_status.progress = Progress.USABLE

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
        if (cls._service_status.progress == Progress.USABLE
                or cls._service_status.status != Status.OK):
            SettingsMap.set_available(cls.service_key, cls._service_status)
        MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                        f'status: {cls._service_status.status}')
        if cls._service_status.progress != Progress.USABLE:
            raise ValueError(f'Service: {cls.service_key} not fully initialized')
        return True

    @classmethod
    def get_status(cls) -> ServiceStatus:
        return cls._service_status
