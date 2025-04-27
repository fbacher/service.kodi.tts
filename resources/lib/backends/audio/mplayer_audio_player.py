# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys
from pathlib import Path

import xbmc

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilities import SoundCapabilities
from backends.players.iplayer import IPlayer
from backends.players.mplayer_settings import MPlayerSettings
from backends.players.player_index import PlayerIndex
from backends.settings.i_validators import INumericValidator
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import NumericValidator
from common import *
from common.base_services import BaseServices, IServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.logger import BasicLogger
from common.phrases import Phrase
from common.setting_constants import Players
from common.settings import Settings
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class MPlayerAudioPlayer(SubprocessAudioPlayer, BaseServices):
    """
     name = 'MPlayer'
     MPlayer supports slave mode, however mpv's implementation is much
     better, so it is not used here.

     MPlayer supports -idle and -slave which keeps player_key from exiting
     after files played. When in slave mode, commands are read from stdin.
    """
    ID = Players.MPLAYER
    service_id: str = Services.MPLAYER_ID
    service_type: ServiceType = ServiceType.PLAYER
    service_key: ServiceID = ServiceID(ServiceType.PLAYER, service_id)

    _availableArgs = (Constants.MPLAYER_PATH, '--help')
    _available: bool | None = None
    #
    """
      mplayer is NOT used for slave mode since it has an inferior implementation
      than mpv.
    """
    MPLAYER_AUDIO_FILTER: str = '-af'
    MPLAYER_PLAY_ARGS = (Constants.MPLAYER_PATH, '-really-quiet')
    MPLAYER_PIPE_ARGS = (Constants.MPLAYER_PATH, '-', '-really-quiet', '-cache', '8192')
    MPLAYER_SPEED_ARGS = 'scaletempo=scale={0}:speed=none'

    # Multiplier of 1.0 = 100% of speed (i.e. no change)
    _speedMultiplier: Final[float] = 1.0  # The base range is 3 .. 30.
    _volumeArgs = 'volume={0:.2f}'  # Volume in db -200db .. +40db Default 0
    _initialized: bool = False

    def __init__(self):
        clz = MPlayerAudioPlayer
        if not clz._initialized:
            clz.initialized = True
            clz.register(self)
        super().__init__()

        self.engine_key: ServiceID | None = None
        self.configVolume: bool = True
        self.configSpeed: bool = True
        self.configPitch: bool = True

    def init(self, engine_key: ServiceID):
        clz = type(self)
        self.engine_key = engine_key
        engine: BaseServices = BaseServices.get_service(engine_key)

        can_set_volume: bool = self.canSetVolume()
        can_set_speed: bool = self.canSetSpeed()
        can_set_pitch: bool = self.canSetPitch()
        # self.configVolume, self.configSpeed, self.configPitch =
        vol, speed, pitch = \
            engine.negotiate_engine_config(
                    engine_key, can_set_volume, can_set_speed, can_set_pitch)
        self.configVolume = vol
        self.configSpeed = speed
        self.configPitch = pitch

    def playArgs(self, phrase: Phrase) -> List[str]:
        clz = type(self)
        args: List[str] = []
        args.extend(clz.MPLAYER_PLAY_ARGS)

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
            audio_filter: List[str] = [MPlayerAudioPlayer.MPLAYER_AUDIO_FILTER,
                                       ",".join(filters)]
            MY_LOGGER.debug(f'audio_filter: {audio_filter}')
            args.extend(audio_filter)
            try:
                if phrase.get_pre_pause() != 0 and phrase.pre_pause_path() is not None:
                    args.append(str(phrase.pre_pause_path()))
                    MY_LOGGER.debug(f'pre_silence {phrase.get_pre_pause()} ms')

                args.append(f'{phrase.get_cache_path()}')
                MY_LOGGER.debug(f'phrase: {phrase} path: {phrase.get_cache_path()}')
                if phrase.get_post_pause() != 0 and phrase.post_pause_path() is not None:
                    args.append(str(phrase.post_pause_path()))
                    MY_LOGGER.debug(f'post_silence {phrase.get_post_pause()} ms')
                MY_LOGGER.debug(f'args: {args}')
            except ExpiredException:
                reraise(*sys.exc_info())
        MY_LOGGER.debug_v(f'args: {" ".join(args)}')
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
            MY_LOGGER.debug(f'audio_filter: {audio_filter}')
            args.extend(audio_filter)
        MY_LOGGER.debug_v(f'args: {" ".join(args)}')
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
        speed = Settings.get_speed()
        # MY_LOGGER.debug(f'setting_id: {clz.setting_id} speed: {speed}')
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

        volume_validator = SettingsMap.get_validator(
                                            clz.service_key.with_prop(SettingProp.VOLUME))
        volume_validator: INumericValidator
        volume: float
        if as_decibels:
            volume = volume_validator.as_decibels()
        else:
            volume = volume_validator.as_percent()

        return volume

    @classmethod
    def register(cls, me: IPlayer):
        """

        :param me:
        :return:
        """
        PlayerIndex.register(MPlayerAudioPlayer.ID, me)
        me: IServices
        BaseServices.register(me)
