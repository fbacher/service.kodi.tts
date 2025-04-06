# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.settings.i_validators import INumericValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import PlayerType, Services, ServiceType
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, StringValidator, Validator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import AudioType, PlayerMode, Players
from common.settings_low_level import SettingProp
from backends.settings.service_types import ServiceID

MY_LOGGER = BasicLogger.get_logger(__name__)


class BuiltinPlayerSettings:
    """
    Defines a dummy, built-in-player_key, such as provided by eSpeak. This player_key
    provides values that make the configuration and running happy. The
    BuiltInPlayer doesn't do anything. The eSpeak engine, for example, recognizes
    when it's player_key is Builtin, and modifies its command line appropriately.
    """
    ID = Players.INTERNAL
    service_id: str = PlayerType.INTERNAL.value
    service_type: ServiceType = ServiceType.PLAYER
    service_key: ServiceID = ServiceID(service_type, service_id)
    displayName = 'Internal'

    settings: Dict[str, Validator] = {}

    _supported_input_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
    _supported_output_formats: List[AudioType] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_key, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

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

    @classmethod
    def isSupportedOnPlatform(cls) -> bool:
        return True

    @classmethod
    def isInstalled(cls) -> bool:
        if not cls.isSupportedOnPlatform():
            return False
        return cls.available()

    @classmethod
    def available(cls) -> bool:
        """
        Determines if the engine is functional. The test is only run once and
        remembered.

        :return:
        """
        return True
