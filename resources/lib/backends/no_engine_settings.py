# coding=utf-8
from __future__ import annotations  # For union operator |


from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.i_validators import INumericValidator, ValueType
from backends.settings.service_types import GENERATE_BACKUP_SPEECH, Services, ServiceType
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, NumericValidator,
                                          SimpleStringValidator, StringValidator)
from common.config_exception import UnusableServiceException
from common.constants import Constants
from common.logger import BasicLogger
from common.service_status import Progress, ServiceStatus
from common.setting_constants import AudioType, Backends, Genders, PlayerMode, Players
from common.settings import Settings
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class NoEngineSettings:
    # Only returns .wav files, or speech
    ID: str = Backends.NO_ENGINE_ID
    engine_id = Backends.NO_ENGINE_ID
    service_id: str = Services.NO_ENGINE_ID
    service_type: ServiceType = ServiceType.ENGINE
    service_key: ServiceID = ServiceID(service_type, service_id)
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    NO_ENGINE_KEY: ServiceID = service_key
    displayName = 'noEngine'

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False
    _service_status: ServiceStatus = ServiceStatus()

    @classmethod
    def config_settings(cls, *args, **kwargs):
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
        MY_LOGGER.debug(f'Adding NoEngine to engine service'
                        f' cache_top: {Constants.PREDEFINED_CACHE}')

        name_validator: StringValidator
        name_validator = StringValidator(service_key=cls.NAME_KEY,
                                         allowed_values=[cls.displayName],
                                         allow_default=False,
                                         const=True
                                         )

        SettingsMap.define_setting(cls.NAME_KEY, name_validator)

        cache_service_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_PATH)
        cache_path_val: SimpleStringValidator
        cache_path_val = SimpleStringValidator(cache_service_key,
                                               value=str(Constants.PREDEFINED_CACHE),
                                               const=True)
        SettingsMap.define_setting(cache_path_val.service_key,
                                   cache_path_val)

        cache_suffix_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix: str = Backends.ENGINE_CACHE_CODE[Backends.NO_ENGINE_ID]

        cache_suffix_val: SimpleStringValidator
        cache_suffix_val = SimpleStringValidator(cache_suffix_key,
                                                 value=cache_suffix,
                                                 const=True)
        SettingsMap.define_setting(cache_suffix_val.service_key,
                                   cache_suffix_val)

        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings
        '''
        pitch_validator: NumericValidator
        pitch_validator = NumericValidator(cls.service_key.with_prop(SettingProp.PITCH),
                                           minimum=0, maximum=99, default=50,
                                           is_decibels=False, is_integer=True,
                                           increment=1)
        SettingsMap.define_setting(pitch_validator.service_key,
                                   pitch_validator)
        '''
        tmp_key: ServiceID
        tmp_key = cls.service_key.with_prop(SettingProp.VOLUME)
        volume_validator: NumericValidator
        volume_validator = NumericValidator(tmp_key,
                                            minimum=0, maximum=200,
                                            default=100, is_decibels=False,
                                            is_integer=True)
        SettingsMap.define_setting(volume_validator.service_key,
                                   volume_validator)

        # Defines a very loose language validator. Basically it will accept
        # almost any strings. The real work is done by LanguageInfo and
        # SettingsHelper. Should revisit this validator

        tmp_key = cls.service_key.with_prop(SettingProp.LANGUAGE)
        language_validator: StringValidator
        language_validator = StringValidator(tmp_key,
                                             allowed_values=[], min_length=2,
                                             max_length=10)
        SettingsMap.define_setting(language_validator.service_key,
                                   language_validator)

        allowed_player_modes: List[str] = [
            PlayerMode.FILE.value
        ]
        tmp_key = cls.service_key.with_prop(SettingProp.PLAYER_MODE)
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(tmp_key,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.FILE.value)
        SettingsMap.define_setting(player_mode_validator.service_key,
                                   player_mode_validator)
        Settings.set_current_output_format(cls.service_key, AudioType.WAV)

        SoundCapabilities.add_service(cls.service_key,
                                      service_types=[ServiceType.ENGINE],
                                      supported_input_formats=[],
                                      supported_output_formats=[AudioType.WAV])

        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[AudioType.WAV],
                producer_formats=[])

        players: List[str] = [Players.SFX]

        MY_LOGGER.debug(f'candidates: {candidates}')
        valid_players: List[str] = []
        for player_id in candidates:
            player_id: str
            player_key: ServiceID
            player_key = ServiceID(ServiceType.PLAYER, player_id)
            if player_id in players and SettingsMap.is_available(player_key):
                valid_players.append(player_id)

        MY_LOGGER.debug(f'valid_players: {valid_players}')

        tmp_key = cls.service_key.with_prop(SettingProp.PLAYER)
        player_validator: StringValidator
        player_validator = StringValidator(tmp_key,
                                           allowed_values=valid_players,
                                           default=Players.SFX)
        SettingsMap.define_setting(player_validator.service_key,
                                   player_validator)

        '''
        tmp_key = cls.service_key.with_prop(SettingProp.GENDER)
        gender_validator = GenderValidator(tmp_key,
                                           min_value=Genders.FEMALE,
                                           max_value=Genders.UNKNOWN,
                                           default=Genders.UNKNOWN)
        SettingsMap.define_setting(gender_validator.service_key,
                                   gender_validator)

        tmp_key = cls.service_key.with_prop(SettingProp.GENDER_VISIBLE)
        gender_visible_val: BoolValidator
        gender_visible_val = BoolValidator(tmp_key, default=True)
        SettingsMap.define_setting(gender_visible_val.service_key,
                                   gender_visible_val)
        '''

        tmp_key = cls.service_key.with_prop(SettingProp.CACHE_SPEECH)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(tmp_key, default=True)
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

        '''
        speed_validator: NumericValidator
        speed_validator = NumericValidator(SettingProp.SPEED,
                                           cls.setting_id,
                                           minimum=43, maximum=700,
                                           default=176,
                                           is_decibels=False,
                                           is_integer=True, increment=45)
        SettingsMap.define_setting(cls.setting_id,
                                   SettingProp.SPEED,
                                   speed_validator)
        '''

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
        MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                        f'status: {cls._service_status.status}')

    @classmethod
    def check_is_available(cls) -> None:
        """
        Determines if the engine is functional. The test is only run once and
        remembered.

        :return:
        """
        success: bool = True
        if (cls._service_status.progress == Progress.INSTALLED
                and cls._service_status.status == Status.OK):
            cls._service_status.progress = Progress.AVAILABLE
        MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                        f'status: {cls._service_status.status}')

    @classmethod
    def check_is_usable(cls) -> None:
        """
        Determine if the engine is usable in this environment. Perhaps there is
        no player that can work with this engine available.
        :return None:
        """
        # eSpeak should always be usable, since it comes with its own player
        if cls._service_status.progress == Progress.AVAILABLE:
            cls._service_status.progress = Progress.USABLE
            SettingsMap.set_available(cls.service_key, cls._service_status)
        MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                        f'status: {cls._service_status.status}')

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
