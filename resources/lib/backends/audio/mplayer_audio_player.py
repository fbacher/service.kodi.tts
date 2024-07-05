from __future__ import annotations  # For union operator |

import os
import sys
import tempfile
from pathlib import Path

from backends.settings.settings_map import SettingsMap
from common import *

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.validators import ConstraintsValidator, NumericValidator
from common.base_services import BaseServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.logger import BasicLogger
from common.phrases import Phrase
from common.setting_constants import Players

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class MPlayerAudioPlayer(SubprocessAudioPlayer, BaseServices):
    """
     name = 'MPlayer'
     MPlayer supports -idle and -slave which keeps player from exiting
     after files played. When in slave mode, commands are read from stdin.
    """
    ID = Players.MPLAYER
    service_ID: str = Services.MPLAYER_ID
    service_TYPE: str = ServiceType.PLAYER

    _supported_input_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER,
                                             ServiceType.CONVERTER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    if Constants.PLATFORM_WINDOWS:
        # Mplayer not readily available on Windows
        raise NotImplementedError('mplayer not available on Windows')
    else:
        _availableArgs = (Constants.MPLAYER_PATH, '--help')
    #
    """
      mplayer is NOT used for slave mode since it has an inferior implementation
      than mpv.
    """
    MPLAYER_AUDIO_FILTER: str = '-af'
    MPLAYER_PLAY_ARGS = (Constants.MPLAYER_PATH, '-really-quiet', None)
    MPLAYER_PIPE_ARGS = (Constants.MPLAYER_PATH, '-', '-really-quiet', '-cache', '8192')
    MPLAYER_SPEED_ARGS = 'scaletempo=scale={0}:speed=none'

    # Multiplier of 1.0 = 100% of speed (i.e. no change)
    _speedMultiplier: Final[float] = 1.0  # The base range is 3 .. 30.
    _volumeArgs = 'volume={0:.2f}'  # Volume in db -200db .. +40db Default 0
    _logger: BasicLogger = None

    def __init__(self):
        clz = MPlayerAudioPlayer
        if clz._logger is None:
            clz._logger = module_logger.getChild(self.__class__.__name__)
            clz.register(self)
        super().__init__()

        self.engine_id: str = None
        self.configVolume: bool = True
        self.configSpeed: bool = True
        self.configPitch: bool = True

    def init(self, engine_id: str):
        self.engine_id = engine_id
        engine: BaseServices = BaseServices.getService(engine_id)

        can_set_volume: bool = self.canSetVolume()
        can_set_speed: bool = self.canSetSpeed()
        can_set_pitch: bool = self.canSetPitch()
        # self.configVolume, self.configSpeed, self.configPitch =
        vol, speed, pitch = \
            engine.negotiate_engine_config(
                    engine_id, can_set_volume, can_set_speed, can_set_pitch)
        self.configVolume = vol
        self.configSpeed = speed
        self.configPitch = pitch

    def playArgs(self, phrase: Phrase) -> List[str]:
        clz = type(self)
        args: List[str] = []
        try:
            args.append(phrase.get_text())
        except ExpiredException:
            reraise(*sys.exc_info())
        #
        # None is returned if engine can not control speed, etc.
        #
        speed: float = self.get_player_speed()
        # Get the volume produced by the engine using TTS scale

        volume: float
        volume = self.get_player_volume(as_decibels=True)

        if speed is None:
            self.configSpeed = False
        if volume is None:
            self.configVolume = False

        if self.configSpeed or self.configVolume:
            filters: List[str] = []
            if self.configSpeed:
                filters.append(clz.MPLAYER_SPEED_ARGS.format(self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            audio_filter: List[str] = []
            audio_filter.append(MPlayerAudioPlayer.MPLAYER_AUDIO_FILTER)
            audio_filter.append(",".join(filters))
            clz._logger.debug(f'audio_filter: {audio_filter}')
            args.extend(audio_filter)
        self._logger.debug_verbose(f'args: {" ".join(args)}')
        return args

    def get_pipe_args(self) -> List[str]:
        clz = type(self)
        args: List[str] = []
        args.extend(clz.MPLAYER_PIPE_ARGS)
        speed: float = self.get_player_speed()
        volume: float = self.get_player_volume(as_decibels=True)
        if speed is None:
            self.configSpeed = False
        if volume is None:
            self.configVolume = False

        if self.configSpeed or self.configVolume:
            filters = []
            if self.configSpeed:
                filters.append(clz.MPLAYER_SPEED_ARGS.format(self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            audio_filter: List[str] = []
            audio_filter.append(MPlayerAudioPlayer.MPLAYER_AUDIO_FILTER)
            audio_filter.append(",".join(filters))
            clz._logger.debug(f'audio_filter: {audio_filter}')
            args.extend(audio_filter)
        self._logger.debug_verbose(f'args: {" ".join(args)}')
        # Debug.dump_all_threads(0.0)
        return args

    def canSetSpeed(self) -> bool:
        return True

    def canSetVolume(self) -> bool:
        return True

    def canSetPitch(self) -> bool:
        """
        You CAN set mplayer pitch. Just not supporting that capability just yet
        :return:
        """
        return False

    def canSetPipe(self) -> bool:
        return True

    def get_player_speed(self) -> float:
        clz = type(self)
        speed_validator: NumericValidator
        speed_validator = clz.get_validator(clz.service_ID,
                                            property_id=SettingsProperties.SPEED)
        speed = speed_validator.get_value()
        # clz._logger.debug(f'service_ID: {clz.service_ID} speed: {speed}')
        return speed

    def get_player_volume(self, as_decibels: bool = True) -> float:
        """
        Mplayer/mpv support several types of volume controls
        --volume flag. Adjusts the software volume (does not tell the driver to
                 alter device volume). Values are in percent:
                 100% does not alter the input volume
                 200% doubles volume, etc.
                 50% cuts it in half (presumabley perceptive difference)
                 <= 0 gives 0 volume

        --af=scaletempo=scale=1.50:speed=none,volume=4 adjusts volume
        by 4 decibels.

                 The quality of adjusting volume in software is inferior to
                 adjusting in hardware, but it is frequently simplier to adjust
                 the software volume.
        :return:
        """
        clz = type(self)

        volume_validator = SettingsMap.get_validator(clz.service_ID,
                                                     property_id=SettingsProperties.VOLUME)
        volume_validator: NumericValidator
        volume: float
        if as_decibels:
            volume = volume_validator.as_decibels()
        else:
            volume = volume_validator.as_percent()

        return volume

    @classmethod
    def register(cls, what):
        PlayerIndex.register(MPlayerAudioPlayer.ID, what)
        BaseServices.register(what)
