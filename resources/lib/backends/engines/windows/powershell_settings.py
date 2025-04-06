# coding=utf-8
from __future__ import annotations  # For union operator |

from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.i_validators import INumericValidator, ValueType
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, NumericValidator,
                                          StringValidator)
from common.constants import Constants
from common.logger import BasicLogger
from common.message_ids import MessageId
from common.setting_constants import AudioType, Backends, Genders, PlayerMode, Players
from common.settings import Settings
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class PowerShellTTSSettings:
    ID = Backends.POWERSHELL_ID
    service_id: str = Services.POWERSHELL_ID
    service_type: ServiceType = ServiceType.ENGINE
    engine_id: str = Backends.POWERSHELL_ID
    service_key: ServiceID = ServiceID(service_type, service_id)
    OUTPUT_FILE_TYPE: str = '.wav'
    displayName: str = MessageId.ENGINE_POWERSHELL.get_msg()

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False
    _available: bool | None = None

    @classmethod
    def config_settings(cls, *args, **kwargs):
        # Define each engine's default settings here, afterward, they can be
        # overridden by this class.
        BaseEngineSettings.config_settings(cls.service_key)
        if cls.initialized:
            return
        cls.initialized = True
        cls._config()

    @classmethod
    def _config(cls):
        MY_LOGGER.debug(f'Adding powershell to engine service')

        cache_suffix_key: ServiceID
        cache_suffix_key = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix_validator: StringValidator
        cache_suffix_validator = StringValidator(cache_suffix_key,
                                                 allowed_values=['pwrsh'], min_length=3,
                                                 max_length=5)
        SettingsMap.define_setting(cache_suffix_validator.service_key,
                                   cache_suffix_validator)

        gender_validator = GenderValidator(cls.service_key.with_prop(SettingProp.GENDER),
                                           min_value=Genders.FEMALE,
                                           max_value=Genders.UNKNOWN,
                                           default=Genders.UNKNOWN)
        SettingsMap.define_setting(gender_validator.service_key,
                                   gender_validator)
        t_key: ServiceID
        t_key = cls.service_key.with_prop(SettingProp.GENDER_VISIBLE)
        gender_visible: BoolValidator
        gender_visible = BoolValidator(t_key,
                                       default=True)
        SettingsMap.define_setting(gender_visible.service_key,
                                   gender_visible)
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings
        '''
        pitch_validator: NumericValidator
        pitch_validator = NumericValidator(SettingProp.PITCH,
                                           cls.setting_id,
                                           minimum=0, maximum=99, default=50,
                                           is_decibels=False, is_integer=True,
                                           increment=1)
        SettingsMap.define_setting(cls.setting_id, SettingProp.PITCH,
                                   pitch_validator)
        '''
        t_key = cls.service_key.with_prop(SettingProp.VOLUME)
        volume_validator: NumericValidator
        volume_validator = NumericValidator(t_key,
                                            minimum=0, maximum=200,
                                            default=100, is_decibels=False,
                                            is_integer=True)
        SettingsMap.define_setting(volume_validator.service_key,
                                   volume_validator)

        # Can use LAME to convert to mp3. This code is untested
        # TODO: test, expose capability in settings config

        # audio_validator: StringValidator
        # audio_converter_validator = StringValidator(SettingProp.TRANSCODER,
        #                                             cls.engine_id,
        #                                             allowed_values=[Services.LAME_ID])

        # SettingsMap.define_setting(cls.setting_id, SettingProp.TRANSCODER,
        #                            audio_converter_validator)
        # Defines a very loose language validator. Basically it will accept
        # almost any strings. The real work is done by LanguageInfo and
        # SettingsHelper. Should revisit this validator

        t_key = cls.service_key.with_prop(SettingProp.LANGUAGE)
        language_validator: StringValidator
        language_validator = StringValidator(t_key,
                                             allowed_values=[], min_length=2,
                                             max_length=10)
        SettingsMap.define_setting(language_validator.service_key,
                                   language_validator)
        t_key = cls.service_key.with_prop(SettingProp.VOICE)
        voice_validator: StringValidator
        voice_validator = StringValidator(t_key,
                                          allowed_values=[], min_length=1, max_length=20,
                                          default=None)
        SettingsMap.define_setting(voice_validator.service_key,
                                   voice_validator)

        allowed_player_modes: List[str] = [
            # PlayerMode.SLAVE_FILE.value,
            # PlayerMode.FILE.value,
            # PlayerMode.PIPE.value
            PlayerMode.ENGINE_SPEAK.value
        ]
        t_key = cls.service_key.with_prop(SettingProp.PLAYER_MODE)
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(t_key,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.ENGINE_SPEAK.value)
        SettingsMap.define_setting(player_mode_validator.service_key,
                                   player_mode_validator)

        Settings.set_current_output_format(cls.service_key, AudioType.NONE)
        SoundCapabilities.add_service(cls.service_key,
                                      service_types=[ServiceType.ENGINE],
                                      supported_input_formats=[],
                                      supported_output_formats=[  # AudioType.WAV,
                                                                AudioType.NONE])

        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[AudioType.NONE],
                producer_formats=[])

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        players: List[str] = [Players.INTERNAL]

        MY_LOGGER.debug(f'candidates: {candidates}')
        valid_players: List[str] = []
        for player_id in candidates:
            player_id: str
            player_key: ServiceID
            player_key = ServiceID(ServiceType.PLAYER, player_id)
            if player_id in players and SettingsMap.is_available(player_key):
                valid_players.append(player_id)

        MY_LOGGER.debug(f'valid_players: {valid_players}')
        t_key = cls.service_key.with_prop(SettingProp.PLAYER)
        player_validator: StringValidator
        player_validator = StringValidator(t_key,
                                           allowed_values=valid_players,
                                           default=Players.INTERNAL)
        SettingsMap.define_setting(player_validator.service_key,
                                   player_validator)
        t_key = cls.service_key.with_prop(SettingProp.CACHE_SPEECH)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(t_key,
                                        default=False)

        SettingsMap.define_setting(cache_validator.service_key,
                                   cache_validator)

        # For consistency (and simplicity) any speed adjustments are actually
        # done by a player_key that supports it. Direct adjustment of player_key speed
        # could be re-added, but it would complicate configuration a bit.
        #
        # TTS scale is based upon mpv/mplayer which is a multiplier which
        # has 1 = no change in speed, 0.25 slows down by 4, and 4 speeds up by 4
        #
        # eSpeak-ng 'normal speed' is 175 words per minute.
        # The slowest supported rate appears to be about 70, any slower doesn't
        # seem to make any real difference. The maximum speed is unbounded, but
        # 4x (4 * 175 = 700) is hard to listen to.
        #
        # In other words espeak speed = 175 * mpv speed
        t_key = cls.service_key.with_prop(SettingProp.SPEED)
        speed_validator: NumericValidator
        speed_validator = NumericValidator(t_key,
                                           minimum=43, maximum=700,
                                           default=176,
                                           is_decibels=False,
                                           is_integer=True, increment=45)
        SettingsMap.define_setting(speed_validator.service_key,
                                   speed_validator)

    @classmethod
    def isSettingSupported(cls, setting: str) -> bool:
        return SettingsMap.is_valid_setting(cls.service_key.with_prop(setting))

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
        supported: bool = Constants.PLATFORM_WINDOWS
        MY_LOGGER.info(f'powershell supported: {supported}')
        return supported

    @classmethod
    def isInstalled(cls) -> bool:
        return cls.isSupportedOnPlatform()

    @classmethod
    def is_available(cls):
        return cls.isSupportedOnPlatform()
