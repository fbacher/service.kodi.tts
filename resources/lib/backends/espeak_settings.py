from __future__ import annotations  # For union operator |

import os
import subprocess
import sys

from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.i_validators import INumericValidator, ValueType
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, NumericValidator,
                                          StringValidator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import AudioType, Backends, PlayerMode, Players
from common.settings import Settings
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class ESpeakSettings(BaseServiceSettings):
    # Only returns .wav files, or speech
    ID: str = Backends.ESPEAK_ID
    engine_id = Backends.ESPEAK_ID
    service_ID: str = Services.ESPEAK_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    displayName = 'eSpeak'

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(*args, **kwargs)
        BaseEngineSettings(clz.service_ID)
        if ESpeakSettings.initialized:
            return
        ESpeakSettings.initialized = True
        ESpeakSettings.init_settings()
        SettingsMap.set_is_available(clz.service_ID, Reason.AVAILABLE)

    @classmethod
    def init_settings(cls):
        MY_LOGGER.debug(f'Adding eSpeak to engine service')
        service_properties = {Constants.NAME: cls.displayName,
                              Constants.CACHE_SUFFIX: 'espk'}
        SettingsMap.define_service(ServiceType.ENGINE, cls.service_ID,
                                   service_properties)
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        pitch_validator: NumericValidator
        pitch_validator = NumericValidator(SettingsProperties.PITCH,
                                           cls.service_ID,
                                           minimum=0, maximum=99, default=50,
                                           is_decibels=False, is_integer=True,
                                           increment=1)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PITCH,
                                   pitch_validator)

        volume_validator: NumericValidator
        volume_validator = NumericValidator(SettingsProperties.VOLUME,
                                            cls.service_ID,
                                            minimum=0, maximum=200,
                                            default=100, is_decibels=False,
                                            is_integer=True)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.VOLUME,
                                   volume_validator)

        # Can use LAME to convert to mp3. This code is untested
        # TODO: test, expose capability in settings config

        audio_validator: StringValidator
        audio_converter_validator = StringValidator(SettingsProperties.TRANSCODER,
                                                    cls.engine_id,
                                                    allowed_values=[Services.LAME_ID,
                                                                    Services.MPLAYER_ID])

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.TRANSCODER,
                                   audio_converter_validator)
        # Defines a very loose language validator. Basically it will accept
        # almost any strings. The real work is done by LanguageInfo and
        # SettingsHelper. Should revisit this validator

        language_validator: StringValidator
        language_validator = StringValidator(SettingsProperties.LANGUAGE, cls.engine_id,
                                             allowed_values=[], min_length=2,
                                             max_length=10)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.LANGUAGE,
                                   language_validator)

        voice_validator: StringValidator
        voice_validator = StringValidator(SettingsProperties.VOICE, cls.engine_id,
                                          allowed_values=[], min_length=1, max_length=20,
                                          default=None)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOICE,
                                   voice_validator)

        # Player Options:
        #  1 Use internal player and don't produce .wav. Currently don't support
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
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(SettingsProperties.PLAYER_MODE,
                                                cls.service_ID,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.SLAVE_FILE.value)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER_MODE,
                                   player_mode_validator)

        Settings.set_current_output_format(cls.service_ID, AudioType.WAV)

        SoundCapabilities.add_service(cls.service_ID,
                                      service_types=[ServiceType.ENGINE],
                                      supported_input_formats=[],
                                      supported_output_formats=[AudioType.WAV])

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
            if player_id in players and SettingsMap.is_available(player_id):
                valid_players.append(player_id)

        MY_LOGGER.debug(f'valid_players: {valid_players}')

        # TODO: what if default player is not available?
        player_validator: StringValidator
        player_validator = StringValidator(SettingsProperties.PLAYER, cls.engine_id,
                                           allowed_values=valid_players,
                                           default=Players.INTERNAL)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER,
                                   player_validator)

        # If espeak native .wav is produced, then cache_speech = False.
        # If espeak is converted to mp3, then cache_speech = True, otherwise, why
        # bother to spend cpu to produce mp3?

        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, cls.service_ID,
                                        default=False)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.CACHE_SPEECH,
                                   cache_validator)

        # For consistency (and simplicity) any speed adjustments are actually
        # done by a player that supports it. Direct adjustment of player speed
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

        speed_validator: NumericValidator
        speed_validator = NumericValidator(SettingsProperties.SPEED,
                                           cls.service_ID,
                                           minimum=43, maximum=700,
                                           default=176,
                                           is_decibels=False,
                                           is_integer=True, increment=45)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.SPEED,
                                   speed_validator)

    @classmethod
    def isSupportedOnPlatform(cls) -> bool:
        return (SystemQueries.isLinux() or SystemQueries.isWindows()
                or SystemQueries.isOSX())

    @classmethod
    def isInstalled(cls) -> bool:
        installed: bool = False
        if cls.isSupportedOnPlatform():
            installed = True
        return installed

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        return SettingsMap.is_valid_property(cls.service_ID, setting)

    @classmethod
    def available(cls):
        try:
            subprocess.run(['espeak-ng', '--version'], stdout=(open(os.path.devnull, 'w')),
                           universal_newlines=True, stderr=subprocess.STDOUT)
        except AbortException:
            reraise(*sys.exc_info())
        except:
            return False
        return True
