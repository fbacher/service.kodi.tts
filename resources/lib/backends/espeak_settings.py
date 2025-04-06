# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys

import xbmc

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
                                          SimpleStringValidator, StringValidator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import AudioType, Backends, Genders, PlayerMode, Players
from common.settings import Settings
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class ESpeakSettings:
    # Only returns .wav files, or speech
    ID: str = Backends.ESPEAK_ID
    engine_id = Backends.ESPEAK_ID
    service_id: str = Services.ESPEAK_ID
    service_type: ServiceType = ServiceType.ENGINE
    service_key: ServiceID = ServiceID(service_type, service_id)
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    displayName = 'eSpeak'

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False
    _available: bool | None = None

    @classmethod
    def config_settings(cls, *args, **kwargs: Dict[str, str]):
        if cls.initialized:
            return
        cls.initialized = True
        # Define each engine's default settings here, afterward, they can be
        # overridden by this class.
        cls._config(**kwargs)

    @classmethod
    def _config(cls, **kwargs: Dict[str, str]):
        MY_LOGGER.debug(f'Adding eSpeak to engine service')
        '''
        service_properties = {Constants.NAME: cls.displayName,
                              Constants.CACHE_SUFFIX: 'espk'}
        SettingsMap.define_service_properties(cls.service_key, service_properties)
        '''

        cache_service_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_PATH)
        cache_path_val: SimpleStringValidator
        cache_path_val = SimpleStringValidator(cache_service_key,
                                               value=SettingProp.CACHE_PATH_DEFAULT)
        SettingsMap.define_setting(cache_path_val.service_key,
                                   cache_path_val)

        cache_suffix_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix: str = Backends.ENGINE_CACHE_CODE[Backends.ESPEAK_ID]

        cache_suffix_val: SimpleStringValidator
        cache_suffix_val = SimpleStringValidator(cache_suffix_key,
                                                 value=cache_suffix)
        SettingsMap.define_setting(cache_suffix_val.service_key,
                                   cache_suffix_val)

        name_validator: StringValidator
        name_validator = StringValidator(service_key=cls.NAME_KEY,
                                         allowed_values=[cls.displayName],
                                         allow_default=False,
                                         const=True
                                         )

        SettingsMap.define_setting(cls.NAME_KEY, name_validator)
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        pitch_validator: NumericValidator
        pitch_validator = NumericValidator(cls.service_key.with_prop(SettingProp.PITCH),
                                           minimum=0, maximum=99, default=50,
                                           is_decibels=False, is_integer=True,
                                           increment=1)
        SettingsMap.define_setting(pitch_validator.service_key, pitch_validator)

        volume_validator: NumericValidator
        volume_validator = NumericValidator(cls.service_key.with_prop(SettingProp.VOLUME),
                                            minimum=0, maximum=200,
                                            default=100, is_decibels=False,
                                            is_integer=True)
        SettingsMap.define_setting(volume_validator.service_key,
                                   volume_validator)

        # Can use LAME to convert to mp3. This code is untested
        # TODO: test, expose capability in settings config

        transcoder_service_key: ServiceID
        transcoder_service_key = cls.service_key.with_prop(SettingProp.TRANSCODER)
        audio_validator: StringValidator
        audio_converter_validator = StringValidator(transcoder_service_key,
                                                    allowed_values=[Services.LAME_ID,
                                                                    Services.MPLAYER_ID])

        SettingsMap.define_setting(audio_converter_validator.service_key,
                                   audio_converter_validator)
        # Defines a very loose language validator. Basically it will accept
        # almost any strings. The real work is done by LanguageInfo and
        # SettingsHelper. Should revisit this validator
        t_svc_key = cls.service_key.with_prop(SettingProp.LANGUAGE)
        MY_LOGGER.debug(f't_svc_key: {t_svc_key} service: {t_svc_key.service_key}')
        language_validator: StringValidator
        language_validator = StringValidator(t_svc_key,
                                             allowed_values=[], min_length=2,
                                             max_length=10)
        SettingsMap.define_setting(language_validator.service_key,
                                   language_validator)

        voice_validator: StringValidator
        voice_validator = StringValidator(cls.service_key.with_prop(SettingProp.VOICE),
                                          allowed_values=[], min_length=1, max_length=20,
                                          default=None)

        SettingsMap.define_setting(voice_validator.service_key,
                                   voice_validator)

        gender_validator = GenderValidator(cls.service_key.with_prop(SettingProp.GENDER),
                                           min_value=Genders.FEMALE,
                                           max_value=Genders.UNKNOWN,
                                           default=Genders.UNKNOWN)

        SettingsMap.define_setting(gender_validator.service_key,
                                   gender_validator)
        gender_validator.set_tts_value(Genders.FEMALE)

        gender_visible_service_key: ServiceID
        gender_visible_service_key = cls.service_key.with_prop(SettingProp.GENDER_VISIBLE)
        gender_visible: BoolValidator
        gender_visible = BoolValidator(gender_visible_service_key,
                                       default=True)
        SettingsMap.define_setting(gender_visible.service_key,
                                   gender_visible)

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
                                                default=PlayerMode.ENGINE_SPEAK.value)
        SettingsMap.define_setting(player_mode_validator.service_key,
                                   player_mode_validator)

        Settings.set_current_output_format(cls.service_key, AudioType.WAV)
        output_audio_types: List[AudioType] = [AudioType.WAV, AudioType.NONE]
        SoundCapabilities.add_service(cls.service_key,
                                      service_types=[ServiceType.ENGINE],
                                      supported_input_formats=[],
                                      supported_output_formats=output_audio_types)

        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[AudioType.WAV],
                producer_formats=[])

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        players: List[str] = [Players.MPV, Players.MPLAYER,
                              Players.SFX, Players.WINDOWS, Players.APLAY,
                              Players.PAPLAY, Players.AFPLAY, Players.SOX,
                              Players.MPG321, Players.MPG123,
                              Players.MPG321_OE_PI, Players.INTERNAL]

        MY_LOGGER.debug(f'candidates: {candidates}')
        valid_players: List[str] = []
        for player_id in candidates:
            player_id: str
            player_key: ServiceID
            player_key = ServiceID(ServiceType.PLAYER, player_id)
            if player_id in players and SettingsMap.is_available(player_key):
                valid_players.append(player_id)

        MY_LOGGER.debug(f'valid_players: {valid_players}')

        # TODO: what if default player_key is not available?
        player_validator: StringValidator
        player_validator = StringValidator(cls.service_key.with_prop(SettingProp.PLAYER),
                                           allowed_values=valid_players,
                                           default=Players.INTERNAL)
        SettingsMap.define_setting(player_validator.service_key,
                                   player_validator)

        # If espeak native .wav is produced, then cache_speech = False.
        # If espeak is converted to mp3, then cache_speech = True, otherwise, why
        # bother to spend cpu to produce mp3?

        cache_validator: BoolValidator
        cache_validator = BoolValidator(cls.service_key.with_prop(SettingProp.CACHE_SPEECH),
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

        # TODO: Is this needed?

        speed_validator: NumericValidator
        speed_validator = NumericValidator(cls.service_key.with_prop(SettingProp.SPEED),
                                           minimum=43, maximum=700,
                                           default=176,
                                           is_decibels=False,
                                           is_integer=True, increment=45)
        SettingsMap.define_setting(speed_validator.service_key,
                                   speed_validator)

    @classmethod
    def check_availability(cls) -> Reason:
        availability: Reason = Reason.AVAILABLE
        if not cls.isSupportedOnPlatform():
            availability = Reason.NOT_SUPPORTED
        if not cls.isInstalled():
            availability = Reason.NOT_AVAILABLE
        elif not cls.is_available():
            availability = Reason.BROKEN
        SettingsMap.set_is_available(cls.service_key,
                                     availability)
        return availability

    @staticmethod
    def isSupportedOnPlatform() -> bool:
        return (SystemQueries.isLinux() or SystemQueries.isWindows()
                or SystemQueries.isOSX())

    @classmethod
    def isInstalled(cls) -> bool:
        if not cls.isSupportedOnPlatform():
            return False
        return cls.is_available()

    @classmethod
    def is_available(cls) -> bool:
        """
        Determines if the engine is functional. The test is only run once and
        remembered.

        :return:
        """
        success: bool = False
        if cls._available is not None:
            return cls._available
        completed: subprocess.CompletedProcess | None = None
        try:
            cmd_path = 'espeak-ng'
            args = [cmd_path, '--version']
            env = os.environ.copy()
            completed: subprocess.CompletedProcess | None = None
            if Constants.PLATFORM_WINDOWS:
                MY_LOGGER.info(f'Running command: Windows')
                completed = subprocess.run(args, stdin=None, capture_output=True,
                                           text=True, env=env, close_fds=True,
                                           encoding='utf-8', shell=False, check=True,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                MY_LOGGER.info(f'Running command: Linux')
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

        cls._available = success
        MY_LOGGER.debug(f'eSpeak available: {success}')
        return cls._available
