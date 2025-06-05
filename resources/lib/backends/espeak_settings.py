# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys
from pathlib import Path

import xbmc

from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.i_validators import INumericValidator, ValueType
from backends.settings.service_types import Services, ServiceType
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


class ESpeakSettings:
    # Only returns .wav files, or speech
    ID: str = Backends.ESPEAK_ID
    engine_id = Backends.ESPEAK_ID
    service_id: Services = Services.ESPEAK_ID
    service_type: ServiceType = ServiceType.ENGINE
    service_key: ServiceID = ServiceID(service_type, service_id, SettingProp.SERVICE_ID)
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    displayName: str = MessageId.ENGINE_ESPEAK.get_msg()
    ESPEAK_CMD: str = 'espeak-ng'

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False
    _service_status: ServiceStatus = ServiceStatus()

    @classmethod
    def config_settings(cls, *args, **kwargs: Dict[str, str]) -> None:
        BaseEngineSettings.config_settings(cls.service_key,
                                           settings=[SettingProp.GENDER_VISIBLE])
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
        # Define each engine's default settings here, afterward, they can be
        # overridden by this class.
        cls._config(**kwargs)
        return

    @classmethod
    def _config(cls, **kwargs: Dict[str, str]):
        MY_LOGGER.debug(f'Adding eSpeak to engine service')
        '''
        service_properties = {Constants.NAME: cls.displayName,
                              Constants.CACHE_SUFFIX: 'espk'}
        SettingsMap.define_service_properties(cls.service_key, service_properties)
        '''
        name_validator: SimpleStringValidator
        name_validator = SimpleStringValidator(service_key=cls.NAME_KEY,
                                               value=cls.displayName,
                                               const=True,
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=False)

        cache_service_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_PATH)
        cache_path_val: SimpleStringValidator
        cache_path_val = SimpleStringValidator(cache_service_key,
                                               value=SettingProp.CACHE_PATH_DEFAULT,
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=True)

        cache_suffix_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix: str = Backends.ENGINE_CACHE_CODE[Backends.ESPEAK_ID]

        cache_suffix_val: SimpleStringValidator
        cache_suffix_val = SimpleStringValidator(cache_suffix_key,
                                                 value=cache_suffix,
                                                 define_setting=True,
                                                 service_status=StatusType.OK,
                                                 persist=True)
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        pitch_validator: NumericValidator
        pitch_validator = NumericValidator(cls.service_key.with_prop(SettingProp.PITCH),
                                           minimum=0, maximum=99, default=50,
                                           is_decibels=False, is_integer=True,
                                           increment=1,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)

        volume_validator: NumericValidator
        volume_validator = NumericValidator(cls.service_key.with_prop(SettingProp.VOLUME),
                                            minimum=0, maximum=200,
                                            default=100, is_decibels=False,
                                            is_integer=True,
                                            define_setting=True,
                                            service_status=StatusType.OK,
                                            persist=True)

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

        t_key = cls.service_key.with_prop(SettingProp.LANGUAGE)
        SettingsMap.define_setting(t_key, SettingType.STRING_TYPE,
                                   service_status=StatusType.OK)

        t_key = cls.service_key.with_prop(SettingProp.VOICE)
        SettingsMap.define_setting(t_key, SettingType.STRING_TYPE,
                                   service_status=StatusType.OK)
        gender_validator = GenderValidator(cls.service_key.with_prop(SettingProp.GENDER),
                                           min_value=Genders.FEMALE,
                                           max_value=Genders.UNKNOWN,
                                           default=Genders.UNKNOWN,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)

        gender_validator.set_tts_value(Genders.FEMALE)


        # Player Options:
        #  1 Use internal player_key and don't produce .wav. Currently don't support
        #    adjusting volume/speed, etc. this way. Not difficult to add.
        #  2 Produce .wav from engine (no mp3 support) and use mpv (or mplayer)
        #     to play the .wav via file. Better control of speed/volume but adds
        #     extra delay and cpu
        #  3 Produce .wav, use transcoder to .mp3, store .mp3 in cache and then
        #     use mpv to play via slave (or file, but slave better). Takes up
        #     storage, but reduces latency and cpu.
        #  Default is 1. espeak quality not that great, so don't invest that much
        #  in it. Allow caching.
        #
        allowed_player_modes: List[str] = [
            PlayerMode.SLAVE_FILE.value,
            PlayerMode.FILE.value,
            PlayerMode.PIPE.value,
            PlayerMode.ENGINE_SPEAK.value
        ]
        t_svc_key: ServiceID
        t_svc_key = cls.service_key.with_prop(SettingProp.PLAYER_MODE)
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(t_svc_key,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.ENGINE_SPEAK.value,
                                                define_setting=True,
                                                service_status=StatusType.OK,
                                                persist=True)

        Settings.set_current_output_format(cls.service_key, AudioType.WAV)
        output_audio_types: List[AudioType] = [AudioType.WAV, AudioType.BUILT_IN]
        SoundCapabilities.add_service(cls.service_key,
                                      service_types=[ServiceType.ENGINE],
                                      supported_input_formats=[],
                                      supported_output_formats=output_audio_types)

        candidates: List[ServiceID]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[AudioType.WAV],
                producer_formats=[])
        MY_LOGGER.debug(f'candidates: {candidates}')

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        players: List[str] = [Players.MPV, Players.MPLAYER,
                              Players.SFX, Players.WINDOWS, Players.APLAY,
                              Players.PAPLAY, Players.AFPLAY, Players.SOX,
                              Players.MPG321, Players.MPG123,
                              Players.MPG321_OE_PI, Players.BUILT_IN]

        valid_players: List[str] = []
        for player_key in candidates:
            player_key: ServiceID
            player_id = player_key.service_key
            if player_id in players and SettingsMap.is_available(player_key):
                valid_players.append(player_id)

        MY_LOGGER.debug(f'valid_players: {valid_players}')

        # TODO: what if default player is not available?
        player_validator: StringValidator
        player_validator = StringValidator(cls.service_key.with_prop(SettingProp.PLAYER),
                                           allowed_values=valid_players,
                                           default=Players.BUILT_IN,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)

        # If espeak native .wav is produced, then cache_speech = False.
        # If espeak is transcoded to mp3, then cache_speech = True, otherwise, why
        # bother to spend cpu to produce mp3?

        setting_id: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SPEECH)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(setting_id,
                                        default=False,
                                        define_setting=True,
                                        service_status=StatusType.OK,
                                        persist=True)

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

        # TODO: Is this needed?

        speed_validator: NumericValidator
        speed_validator = NumericValidator(cls.service_key.with_prop(SettingProp.SPEED),
                                           minimum=43, maximum=700,
                                           default=176,
                                           is_decibels=False,
                                           is_integer=True, increment=45,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)

    @classmethod
    def check_is_supported_on_platform(cls) -> None:
        if cls._service_status.progress == Progress.START:
            supported: bool = (SystemQueries.isLinux() or SystemQueries.isWindows()
                               or SystemQueries.isOSX())
            cls._service_status.progress = Progress.SUPPORTED
            if not supported:
                cls._service_status.status = Status.FAILED
                cls._service_status.status_summary = StatusType.NOT_ON_PLATFORM
                SettingsMap.define_setting(cls.service_key,
                                           setting_type=SettingType.STRING_TYPE,
                                           service_status=StatusType.NOT_ON_PLATFORM,
                                           validator=None)

        MY_LOGGER.debug(f'state: {cls._service_status.progress} '
                        f'status: {cls._service_status.status}')

    @classmethod
    def check_is_installed(cls) -> None:
        # Don't have a test for installed, just move on to available
        if cls._service_status.progress == Progress.SUPPORTED:
            if cls._service_status.status == Status.OK:
                cls._service_status.progress = Progress.INSTALLED
            else:
                cls._service_status.status_summary = StatusType.NOT_FOUND
                SettingsMap.define_setting(cls.service_key,
                                           setting_type=SettingType.STRING_TYPE,
                                           service_status=StatusType.NOT_FOUND,
                                           validator=None)

    @classmethod
    def check_is_available(cls) -> None:
        """
        Determines if the engine is functional. The test is only run once and
        remembered.

        :return:
        """
        success: bool = False
        if (cls._service_status.progress == Progress.INSTALLED
                and cls._service_status.status == Status.OK):
            try:
                cmd_path: Path = Constants.ESPEAK_PATH / 'espeak-ng.exe'
                args = [cmd_path, '--version']
                env = os.environ.copy()
                completed: subprocess.CompletedProcess | None = None
                if Constants.PLATFORM_WINDOWS:
                    MY_LOGGER.info(f'Running command: Windows args: {args}')
                    completed = subprocess.run(args, stdin=None, capture_output=True,
                                               text=True, env=env, close_fds=True,
                                               encoding='utf-8', shell=False, check=True,
                                               creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    MY_LOGGER.info(f'Running command: Linux args: {args}')
                    completed = subprocess.run(args, stdin=None, capture_output=True,
                                               text=True, env=env, close_fds=True,
                                               encoding='utf-8', shell=False, check=True)
                for line in completed.stdout.split('\n'):
                    if len(line) > 0:
                        if line.find('eSpeak NG text_to_speech'):
                            success = True
                            break
                if completed.returncode != 0:
                    success = False
            except subprocess.CalledProcessError:
                MY_LOGGER.exception('')
            except OSError:
                MY_LOGGER.exception('')
            except Exception:
                MY_LOGGER.exception('')

            MY_LOGGER.debug(f'eSpeak available: {success}')
            cls._service_status.progress = Progress.AVAILABLE
            if not success:
                cls._service_status.status = Status.FAILED
                cls._service_status.status_summary = StatusType.BROKEN
                SettingsMap.define_setting(cls.service_key,
                                           setting_type=SettingType.STRING_TYPE,
                                           service_status=StatusType.BROKEN,
                                           validator=None)
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
            cls._service_status.status_summary = StatusType.OK
            SettingsMap.define_setting(cls.service_key,
                                       setting_type=SettingType.STRING_TYPE,
                                       service_status=StatusType.OK,
                                       validator=None)

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
        if (cls._service_status.status != Status.OK or
                cls._service_status.progress != Progress.USABLE):
            raise UnusableServiceException(service_key=cls.service_key,
                                           reason=cls._service_status,
                                           msg='')
        return True

    @classmethod
    def get_status(cls) -> ServiceStatus:
        return cls._service_status
