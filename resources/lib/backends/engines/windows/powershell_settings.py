# coding=utf-8
from __future__ import annotations  # For union operator |

from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingProp, SettingType
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (GenderValidator, NumericValidator,
                                          SimpleStringValidator, StringValidator)
from common.config_exception import UnusableServiceException
from common.constants import Constants
from common.logger import *
from common.message_ids import MessageId
from common.service_status import Progress, ServiceStatus, StatusType
from common.setting_constants import AudioType, Backends, Genders, PlayerMode, Players
from common.settings import Settings
from backends.settings.service_types import ServiceID

MY_LOGGER = BasicLogger.get_logger(__name__)


class PowerShellTTSSettings:
    ID = Backends.POWERSHELL_ID
    service_id: str = Services.POWERSHELL_ID
    service_type: ServiceType = ServiceType.ENGINE
    engine_id: str = Backends.POWERSHELL_ID
    service_key: ServiceID = ServiceID(service_type, service_id, SettingProp.SERVICE_ID)
    OUTPUT_FILE_TYPE: str = '.wav'
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    displayName: str = MessageId.ENGINE_POWERSHELL.get_msg()

    initialized: bool = False
    _available: bool | None = None
    _service_status: ServiceStatus = ServiceStatus()

    @classmethod
    def config_settings(cls, *args, **kwargs):
        if cls.initialized:
            return
            # Basic checks that don't depend on config
        cls.check_is_supported_on_platform()
        cls.check_is_installed()
        if cls._service_status.status != Status.OK:
            raise UnusableServiceException(cls.service_key,
                                           cls._service_status,
                                           msg='')
        cls.initialized = True
        cls.check_is_available()
        cls.check_is_usable()
        cls.is_usable()
        cls._config()

    @classmethod
    def _config(cls):
        name_validator: SimpleStringValidator
        name_validator = SimpleStringValidator(service_key=cls.NAME_KEY,
                                               value=cls.displayName,
                                               const=True,
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=False)

        BaseEngineSettings.config_settings(cls.service_key,
                                           settings=[SettingProp.GENDER_VISIBLE])

        cache_speech_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SPEECH)
        SettingsMap.define_setting(cache_speech_key,
                                   setting_type=SettingType.BOOLEAN_TYPE,
                                   service_status=StatusType.OK, persist=True)

        cache_service_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_PATH)
        cache_path_val: SimpleStringValidator
        cache_path_val = SimpleStringValidator(cache_service_key,
                                               value=str(Constants.DEFAULT_CACHE_DIRECTORY),
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=False)

        cache_suffix_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix: str = Backends.ENGINE_CACHE_CODE[Backends.POWERSHELL_ID]

        cache_suffix_val: SimpleStringValidator
        cache_suffix_val = SimpleStringValidator(cache_suffix_key,
                                                 value=cache_suffix,
                                                 define_setting=True,
                                                 service_status=StatusType.OK,
                                                 persist=False)

        gender_validator = GenderValidator(cls.service_key.with_prop(SettingProp.GENDER),
                                           min_value=Genders.FEMALE,
                                           max_value=Genders.ANY,
                                           default=Genders.ANY,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)
        gender_validator.set_tts_value(Genders.ANY)

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
                                            is_integer=True,
                                            define_setting=True,
                                            service_status=StatusType.OK,
                                            persist=False)

        t_key = cls.service_key.with_prop(SettingProp.LANGUAGE)
        SettingsMap.define_setting(t_key, SettingType.STRING_TYPE,
                                   service_status=StatusType.OK,
                                   persist=True)

        t_key = cls.service_key.with_prop(SettingProp.VOICE)
        SettingsMap.define_setting(t_key, SettingType.STRING_TYPE,
                                   service_status=StatusType.OK,
                                   persist=True)

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
                                                default=PlayerMode.FILE.value,
                                                define_setting=True,
                                                service_status=StatusType.OK,
                                                persist=True)

        Settings.set_current_output_format(cls.service_key, AudioType.BUILT_IN)
        SoundCapabilities.add_service(cls.service_key,
                                      service_types=[ServiceType.ENGINE],
                                      supported_input_formats=[],
                                      supported_output_formats=[AudioType.WAV,
                                                                AudioType.BUILT_IN])
        candidates: List[ServiceID]
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
                                                         Services.MPLAYER_ID],
                                         define_setting=True,
                                         service_status=StatusType.OK,
                                         persist=True)

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        players: List[str] = [Players.MPV, Players.MPLAYER,
                              Players.SFX, Players.WINDOWS, Players.APLAY,
                              Players.PAPLAY, Players.AFPLAY, Players.SOX,
                              Players.MPG321, Players.MPG123,
                              Players.MPG321_OE_PI, Players.BUILT_IN]

        valid_players: List[str] = []
        for player_key in candidates:
            player_id: str
            player_key: ServiceID
            player_id = player_key.service_id
            if player_id in players and SettingsMap.is_available(player_key):
                valid_players.append(player_id)

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'valid_players: {valid_players}')
        t_key = cls.service_key.with_prop(SettingProp.PLAYER)
        player_validator: StringValidator
        player_validator = StringValidator(t_key,
                                           allowed_values=valid_players,
                                           default=Players.MPV,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)

        t_key = cls.service_key.with_prop(SettingProp.SPEED)
        speed_validator: NumericValidator
        speed_validator = NumericValidator(t_key,
                                           minimum=.50, maximum=2.0,
                                           default=1.2,
                                           is_decibels=False,
                                           is_integer=False, increment=45,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)

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
                cls._service_status.status_summary = StatusType.NOT_ON_PLATFORM
                Settings.set_availability(cls.service_key, StatusType.NOT_ON_PLATFORM)

    @classmethod
    def check_is_installed(cls) -> None:
        # Don't have a test for installed, just move on to available
        if cls._service_status.progress == Progress.SUPPORTED:
            if cls._service_status.status == Status.OK:
                cls._service_status.progress = Progress.INSTALLED
            else:
                cls._service_status.status_summary = StatusType.NOT_FOUND
                Settings.set_availability(cls.service_key, StatusType.NOT_FOUND)

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
            cls._service_status.progress = Progress.USABLE
            cls._service_status.status_summary = StatusType.OK
            SettingsMap.define_setting(cls.service_key,
                                       setting_type=SettingType.STRING_TYPE,
                                       service_status=StatusType.OK,
                                       persist=True)
            Settings.set_availability(cls.service_key, availability=StatusType.OK)

    @classmethod
    def is_usable(cls) -> bool:
        """
        Determines if there are any known reasons that this service is not
        functional. Runs the check_ methods to determine the result.

        :return True IFF functional:
        :raises UnusableServiceException: when this service is not functional
        :raises ValueError: when called before this module fully initialized.
        """
        if cls._service_status.status != Status.OK:
            raise UnusableServiceException(service_key=cls.service_key,
                                           reason=cls._service_status,
                                           msg='')
        progress: Progress = cls._service_status.progress
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                            f'status: {cls._service_status.status}')
        if progress != Progress.USABLE:
            raise ValueError(f'Service: {cls.service_key} not fully initialized')
        return True

    @classmethod
    def get_status(cls) -> ServiceStatus:
        return cls._service_status
