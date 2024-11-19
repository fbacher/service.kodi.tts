# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.settings.i_validators import INumericValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, StringValidator, Validator)
from common.constants import Constants
from common.setting_constants import AudioType, Converters, PlayerMode, Players
from common.settings import Settings
from common.settings_low_level import SettingsProperties


class LAMESettings:
    ID = Converters.LAME
    service_ID: str = Services.LAME_ID
    service_type: str = ServiceType.TRANSCODER
    displayName = 'SFX'

    """
    SFX is a simple player that uses Kodi for playing the audio. Its primary
    benefit is that it is always available, therefore providing a critical
    service when none other is available
    """

    _supported_input_formats: List[AudioType] = [AudioType.WAV]
    _supported_output_formats: List[AudioType] = [AudioType.MP3]
    _provides_services: List[ServiceType] = [ServiceType.TRANSCODER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

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
        SettingsMap.define_service(ServiceType.TRANSCODER, cls.service_ID,
                                   service_properties)

        allowed_player_modes: List[str] = [
            PlayerMode.FILE.value
        ]
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(SettingsProperties.PLAYER_MODE,
                                                cls.service_ID,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.FILE.value)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER_MODE,
                                   player_mode_validator)
