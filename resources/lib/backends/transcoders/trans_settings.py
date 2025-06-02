# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.settings.i_validators import INumericValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import ServiceID, Services, ServiceType
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator,
                                          NumericValidator, StringValidator, Validator)
from common.constants import Constants
from common.service_status import StatusType
from common.setting_constants import AudioType, Converters, PlayerMode, Players
from common.settings import Settings
from common.settings_low_level import SettingProp


class LAMESettings:
    ID = Converters.LAME
    service_id: str = Services.LAME_ID
    service_type: ServiceType = ServiceType.TRANSCODER
    service_key: ServiceID = ServiceID(service_type, service_id)
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    displayName = 'SFX'

    """
    SFX is a simple player_key that uses Kodi for playing the audio. Its primary
    benefit is that it is always available, therefore providing a critical
    service when none other is available
    """

    _supported_input_formats: List[AudioType] = [AudioType.WAV]
    _supported_output_formats: List[AudioType] = [AudioType.MP3]
    _provides_services: List[ServiceType] = [ServiceType.TRANSCODER]
    SoundCapabilities.add_service(service_key, _provides_services,
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
        name_validator: StringValidator
        name_validator = StringValidator(service_key=cls.NAME_KEY,
                                         allowed_values=[cls.displayName],
                                         allow_default=False,
                                         const=True,
                                         define_setting=True,
                                         service_status=StatusType.OK,
                                         persist=True)

        allowed_player_modes: List[str] = [
            PlayerMode.FILE.value
        ]
        t_svc_key: ServiceID
        t_svc_key = cls.service_key.with_prop(SettingProp.PLAYER_MODE)
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(t_svc_key,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.FILE.value,
                                                define_setting=True,
                                                service_status=StatusType.OK,
                                                persist=True)
