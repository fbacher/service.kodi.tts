# coding=utf-8
from __future__ import annotations  # For union operator |

import xbmc

from backends.audio import PLAYSFX_HAS_USECACHED
from backends.engines.base_engine_settings import BaseEngineSettings
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.service_types import Services, ServiceType, ServiceID
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, StringValidator, Validator)
from common.constants import Constants
from common.setting_constants import AudioType, PlayerMode, Players
from common.settings import Settings
from common.settings_low_level import SettingProp


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

    @classmethod
    def config_settings(cls, *args, **kwargs):
        if cls.initialized:
            return
        cls.initialized = True
        #  BaseEngineSettings.config_settings(SFXSettings.service_key)
        cls._config()

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
        return True

    @staticmethod
    def isInstalled() -> bool:
        return True

    @staticmethod
    def available(ext=None) -> bool:
        return xbmc and hasattr(xbmc, 'stopSFX') and PLAYSFX_HAS_USECACHED
