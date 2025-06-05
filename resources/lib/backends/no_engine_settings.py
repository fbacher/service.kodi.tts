# coding=utf-8
from __future__ import annotations  # For union operator |


from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.i_validators import INumericValidator, ValueType
from backends.settings.service_types import (GENERATE_BACKUP_SPEECH, ServiceKey, Services,
                                             ServiceType)
from backends.settings.setting_properties import SettingProp, SettingType
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (BoolValidator,
                                          GenderValidator, NumericValidator,
                                          SimpleStringValidator, StringValidator)
from common.config_exception import UnusableServiceException
from common.constants import Constants
from common.logger import BasicLogger
from common.message_ids import MessageId
from common.service_status import Progress, ServiceStatus, StatusType
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
    NO_ENGINE_KEY: ServiceID = ServiceKey.NO_ENGINE_KEY
    service_key: ServiceID = NO_ENGINE_KEY
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    displayName: str = MessageId.ENGINE_NO_ENGINE.get_msg()

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False
    _service_status: ServiceStatus = ServiceStatus()

    @classmethod
    def config_settings(cls, *args, **kwargs) -> None:

        if cls.initialized:
            return
            # Basic checks that don't depend on config
        cls.check_is_supported_on_platform()
        cls.check_is_installed()
        if cls._service_status.status != Status.OK:
            raise UnusableServiceException(cls.service_key,
                                           cls._service_status,
                                           msg='')
        cls.check_is_available()
        cls.check_is_usable()
        cls.is_usable()
        cls.initialized = True
        BaseEngineSettings.config_settings(cls.service_key,
                                           settings=[SettingProp.CACHE_SPEECH])
        cls._config()

    @classmethod
    def _config(cls):
        MY_LOGGER.debug(f'Adding NoEngine to engine service'
                        f' cache_top: {Constants.PREDEFINED_CACHE}')

        name_validator: SimpleStringValidator
        name_validator = SimpleStringValidator(service_key=cls.NAME_KEY,
                                               value=cls.displayName,
                                               const=True,
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=True)

        cache_service_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_PATH)
        cache_path_val: SimpleStringValidator
        cache_path_val = SimpleStringValidator(cache_service_key,
                                               value=str(Constants.PREDEFINED_CACHE),
                                               const=True,
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=True)

        cache_suffix_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix: str = Backends.ENGINE_CACHE_CODE[Backends.NO_ENGINE_ID]

        cache_suffix_val: SimpleStringValidator
        cache_suffix_val = SimpleStringValidator(cache_suffix_key,
                                                 value=cache_suffix,
                                                 const=True,
                                                 define_setting=True,
                                                 service_status=StatusType.OK,
                                                 persist=True)

        tmp_key: ServiceID
        tmp_key = cls.service_key.with_prop(SettingProp.VOLUME)
        volume_validator: NumericValidator
        volume_validator = NumericValidator(tmp_key,
                                            minimum=0, maximum=200,
                                            default=100, is_decibels=False,
                                            is_integer=True,
                                            define_setting=True,
                                            service_status=StatusType.OK,
                                            persist=True)

        t_key = cls.service_key.with_prop(SettingProp.LANGUAGE)
        SettingsMap.define_setting(t_key, SettingType.STRING_TYPE,
                                   service_status=StatusType.OK)

        t_key = cls.service_key.with_prop(SettingProp.VOICE)
        SettingsMap.define_setting(t_key, SettingType.STRING_TYPE,
                                   service_status=StatusType.OK)

        allowed_player_modes: List[str] = [
            PlayerMode.FILE.value
        ]
        tmp_key = cls.service_key.with_prop(SettingProp.PLAYER_MODE)
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(tmp_key,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.FILE.value,
                                                define_setting=True,
                                                service_status=StatusType.OK,
                                                persist=True)
        Settings.set_current_output_format(cls.service_key, AudioType.WAV)

        SoundCapabilities.add_service(cls.service_key,
                                      service_types=[ServiceType.ENGINE],
                                      supported_input_formats=[],
                                      supported_output_formats=[AudioType.WAV])

        candidates: List[ServiceID]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[AudioType.WAV],
                producer_formats=[])

        players: List[str] = [Players.SFX]

        MY_LOGGER.debug(f'candidates: {candidates}')
        valid_players: List[str] = []
        for player_key in candidates:
            player_id: str
            player_key: ServiceID
            player_id = player_key.service_id
            if player_id in players and SettingsMap.is_available(player_key):
                valid_players.append(player_id)

        MY_LOGGER.debug(f'valid_players: {valid_players}')

        tmp_key = cls.service_key.with_prop(SettingProp.PLAYER)
        player_validator: StringValidator
        player_validator = StringValidator(tmp_key,
                                           allowed_values=valid_players,
                                           default=Players.SFX,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)
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
    @classmethod
    def check_is_supported_on_platform(cls) -> None:
        if cls._service_status.progress == Progress.START:
            cls._service_status.progress = Progress.SUPPORTED
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
        success: bool = True
        if (cls._service_status.progress == Progress.INSTALLED
                and cls._service_status.status == Status.OK):
            cls._service_status.progress = Progress.AVAILABLE

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
            cls._service_status.status_summary = StatusType.OK
            SettingsMap.define_setting(cls.service_key,
                                       setting_type=SettingType.STRING_TYPE,
                                       service_status=StatusType.OK,
                                       validator=None)

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
