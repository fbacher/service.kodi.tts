# coding=utf-8
from __future__ import annotations  # For union operator |

from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.i_validators import INumericValidator, ValueType
from backends.settings.service_types import PlayerType, Services, ServiceType
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, NumericValidator,
                                          SimpleStringValidator, StringValidator)
from common.config_exception import UnusableServiceException
from common.constants import Constants
from common.logger import BasicLogger
from common.message_ids import MessageId
from common.service_status import Progress, ServiceStatus
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
    _service_status: ServiceStatus = ServiceStatus()


    @classmethod
    def config_settings(cls, *args, **kwargs):
        # Define each engine's default settings here, afterward, they can be
        # overridden by this class.
        BaseEngineSettings.config_settings(cls.service_key)
        if cls.initialized:
            return
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

    @classmethod
    def _config(cls):
        MY_LOGGER.debug(f'Adding powershell to engine service')

        cache_validator: BoolValidator
        cache_validator = BoolValidator(
                cls.service_key.with_prop(SettingProp.CACHE_SPEECH),
                default=True, const=False)

        SettingsMap.define_setting(cache_validator.service_key,
                                   cache_validator)

        cache_service_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_PATH)
        cache_path_val: SimpleStringValidator
        cache_path_val = SimpleStringValidator(cache_service_key,
                                               value=SettingProp.CACHE_PATH_DEFAULT)
        SettingsMap.define_setting(cache_path_val.service_key,
                                   cache_path_val)

        cache_suffix_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix: str = Backends.ENGINE_CACHE_CODE[Backends.POWERSHELL_ID]

        cache_suffix_val: SimpleStringValidator
        cache_suffix_val = SimpleStringValidator(cache_suffix_key,
                                                 value=cache_suffix)
        SettingsMap.define_setting(cache_suffix_val.service_key,
                                   cache_suffix_val)

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
            PlayerMode.SLAVE_FILE.value,
            PlayerMode.FILE.value,
            # PlayerMode.PIPE.value
            PlayerMode.ENGINE_SPEAK.value
        ]
        t_key = cls.service_key.with_prop(SettingProp.PLAYER_MODE)
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(t_key,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.FILE.value)
        SettingsMap.define_setting(player_mode_validator.service_key,
                                   player_mode_validator)

        Settings.set_current_output_format(cls.service_key, AudioType.BUILT_IN)
        SoundCapabilities.add_service(cls.service_key,
                                      service_types=[ServiceType.ENGINE],
                                      supported_input_formats=[],
                                      supported_output_formats=[AudioType.WAV,
                                                                AudioType.BUILT_IN])
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[AudioType.BUILT_IN, AudioType.WAV, AudioType.MP3],
                producer_formats=[])

        # Can use LAME to convert to mp3. This code is untested
        # TODO: test, expose capability in settings config

        transcoder_service_key: ServiceID
        transcoder_service_key = cls.service_key.with_prop(SettingProp.TRANSCODER)
        transcoder_val: StringValidator
        transcoder_val = StringValidator(transcoder_service_key,
                                         allowed_values=[Services.LAME_ID,
                                                         Services.MPLAYER_ID])
        SettingsMap.define_setting(transcoder_val.service_key,
                                   transcoder_val)

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        players: List[str] = [Players.MPV, Players.MPLAYER,
                              Players.SFX, Players.WINDOWS, Players.APLAY,
                              Players.PAPLAY, Players.AFPLAY, Players.SOX,
                              Players.MPG321, Players.MPG123,
                              Players.MPG321_OE_PI, Players.BUILT_IN]

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
                                           default=Players.MPV)
        SettingsMap.define_setting(player_validator.service_key,
                                   player_validator)
        t_key = cls.service_key.with_prop(SettingProp.CACHE_SPEECH)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(t_key,
                                        default=True)

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
    def check_is_supported_on_platform(cls) -> None:
        if cls._service_status.progress == Progress.START:
            cls._service_status.progress = Progress.SUPPORTED
            supported: bool = Constants.PLATFORM_WINDOWS
            if not supported:
                cls._service_status.status = Status.FAILED
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
        Determines if the engine is functional. The test is only run once and
        remembered.

        :return:
        """
        # Don't have a test for installed, just move on to available
        if cls._service_status.progress == Progress.INSTALLED:
            if cls._service_status.status == Status.OK:
                cls._service_status.progress = Progress.AVAILABLE

    @classmethod
    def check_is_usable(cls) -> None:
        """
        Determine if the engine is usable in this environment. Perhaps there is
        no player that can work with this engine available.
        :return None:
        """
        # Don't have a test for installed, just move on to available
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
        progress: Progress = cls._service_status.progress
        MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                        f'status: {cls._service_status.status}')
        if progress != Progress.USABLE:
            raise ValueError(f'Service: {cls.service_key} not fully initialized')
        return True

    @classmethod
    def get_status(cls) -> ServiceStatus:
        return cls._service_status
