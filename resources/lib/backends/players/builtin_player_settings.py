from __future__ import annotations  # For union operator |

from backends.settings.i_validators import INumericValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import PlayerType, Services, ServiceType
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, StringValidator, Validator)
from common.constants import Constants
from common.setting_constants import AudioType, PlayerMode, Players
from common.settings_low_level import SettingsProperties


class BuiltinPlayerSettings:
    """
    Defines a dummy, built-in-player, such as provided by eSpeak. This player
    provides values that make the configuration and running happy. The
    BuiltInPlayer doesn't do anything. The eSpeak engine, for example, recognizes
    when it's player is Builtin, and modifies its command line appropriately.
    """
    ID = Players.INTERNAL
    service_ID: str = PlayerType.INTERNAL.value
    service_type: str = ServiceType.PLAYER
    displayName = 'Internal'

    settings: Dict[str, Validator] = {}

    _supported_input_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
    _supported_output_formats: List[AudioType] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz.initialized:
            clz.initialized = True
            return
        clz.init()

    @classmethod
    def init(cls):
        service_properties = {Constants.NAME: cls.displayName}
        SettingsMap.define_service(ServiceType.PLAYER, cls.service_ID,
                                   service_properties)

        tts_volume_validator: INumericValidator
        tts_volume_validator = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                         SettingsProperties.VOLUME)
        volume_validator: NumericValidator
        volume_validator = NumericValidator(SettingsProperties.VOLUME,
                                            cls.service_ID,
                                            minimum=5, maximum=400,
                                            default=100, is_decibels=False,
                                            is_integer=False)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.VOLUME,
                                   volume_validator)

        speed_validator: NumericValidator
        speed_validator = NumericValidator(SettingsProperties.SPEED,
                                           SettingsProperties.TTS_SERVICE,
                                           minimum=0.25, maximum=3,
                                           is_decibels=False,
                                           is_integer=False)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.SPEED,
                                   speed_validator)

        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, cls.service_ID,
                                        default=False)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.CACHE_SPEECH,
                                   cache_validator)

        allowed_player_modes: List[str] = [
            PlayerMode.ENGINE_SPEAK.value
        ]
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(SettingsProperties.PLAYER_MODE,
                                                cls.service_ID,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.ENGINE_SPEAK.value)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER_MODE,
                                   player_mode_validator)
