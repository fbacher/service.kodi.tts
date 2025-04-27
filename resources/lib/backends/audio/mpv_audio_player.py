# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import xbmc

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilities import SoundCapabilities
from backends.players.mpv_player_settings import MPVPlayerSettings
from backends.players.player_index import PlayerIndex
from backends.settings.i_validators import IChannelValidator, INumericValidator
from backends.settings.service_types import ServiceID, ServiceKey, Services, ServiceType
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (ChannelValidator, NumericValidator)
from common import *
from common.base_services import BaseServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.logger import *
from common.phrases import Phrase
from common.setting_constants import Channels, Players
from common.settings import Settings
from common.utils import TempFileUtils

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class MPVAudioPlayer(SubprocessAudioPlayer, BaseServices):
    """
     name = 'MPV'
     MPV is based on MPLAYER. It offers several improvements, particularly with
     running in slave mode. Using slave mode eliminates the overhead and delay of
     launching a player_key for each phrase spoken. There are some significant differences
     in the commands/aruments/behavior, but not radically different.

     MPV supports -idle and -slave which keeps player_key from exiting
     after files played. When in slave mode, commands are read from sockets or
     named pipe.
    """
    ID = Players.MPV
    service_id: str = Services.MPV_ID
    service_type: ServiceType = ServiceType.PLAYER
    MPV_KEY: ServiceID = ServiceID(service_type, service_id)
    service_key: ServiceID = MPV_KEY
    CHANNELS_KEY: MPV_KEY.with_prop(SettingProp.CHANNELS)
    CACHE_SPEECH_KEY = MPV_KEY.with_prop(SettingProp.CACHE_SPEECH)
    MPV_VOLUME_KEY: ServiceID = MPV_KEY.with_prop(SettingProp.VOLUME)
    PLAYER_MODE_KEY = MPV_KEY.with_prop(SettingProp.PLAYER_MODE)
    SPEED_KEY: ServiceID = MPV_KEY.with_prop(SettingProp.SPEED)

    """
    There are many, many features. But what we are most interested in are:
     - Adjusting volume, pitch and speed (without changing pitch)
     - Using mpv in slave mode, as a daemon
    
    For consistency use same options for slave and non-slave modes.
       non-slave mode use command-line arguments:
       --volume=<float>, (in percent change 100 == no change)
       --speed=<float>  (accepts a <float> multiplier 1.0 == no change)

       slave mode commands are sent as json over pipe 
        # For volume, send:
           f'{{ "command": ["set_property", "volume", "{self.volume}"],'
                f' "request_id": "{self.latest_config_transaction_num}" }}'
          The volume is again in percent change.
          
          For speed use:
           f'{{ "command": ["set_property", '
                              f'"speed", "{self.speed}"], "request_id": '
                              f'"{self.latest_config_transaction_num}" }}
            The speed is also a multiplier as with the command line. 
        
        Note that there are other ways to pass speed and volume where they may be
        in different units. In particular, volume is sometimes in decibels.
    """

    MPV_PLAY_ARGS = (Constants.MPV_PATH, '--really-quiet')
    MPV_PIPE_ARGS = (Constants.MPV_PATH, '-', '--really-quiet', '--cache', '8192')
    SLAVE_ARGS: Tuple[str] = (Constants.MPV_PATH, '--really-quiet', '--idle')

    '''
     Send commands via named pipe (or stdin) to play files:
       mkpipe ./slave.input
    
     Note that speed, volume, etc. RESET between each file played. Example below
     resets speed/tempo before each play.
    
     mpv  -af "scaletempo" -slave  -idle -input file=./slave.input
    
     From another shell:
     (echo "loadfile <audio_file> 0"; echo "speed_mult 1.5") >> ./slave.input
     To play another AFTER the previous completes
     (echo loadfile <audio_file2> 0; echo speed_mult 1.5) >> ./slave.input
     To stop playing current file and start playing another:
     (echo loadfile <audio_file3> 1; echo speed_mult 1.5) >>./slave.input

     mpv supports speeds > 0:
      0.30 ~1/3 speed
      0.5 1/2 speed
      1   1 x speed
      2   2 x speed ...
     When volume specified with --af=scaletempo=scale=1.50:speed=none,volume=12
     Then the volume is in decibels, otherwise it is a percentage as in:
      mpv --really-quiet --idle --volume=200.0 525d04b81883fcc53188d624bb389e79.mp3
     Or even
     mpv --really-quiet --af=scaletempo=scale=1.50:speed=none --volume=200 
     525d04b81883fcc53188d624bb389e79.mp3
    
    mpv plays mono on only one channel by default. To force playing on stereo 
    speakers use:
    
        --af=format=channels=stereo
    '''
    _initialized: bool = False

    def __init__(self):
        clz = MPVAudioPlayer
        # Set get here size super also sets clz.get. And clz is the same for
        # both. This messes up register
        if not clz._initialized:
            clz.register(self)
            clz._initialized = True
        super().__init__()

        self.engine_id: str | None = None
        self.engine_key: ServiceID | None = None
        self.configVolume: bool = True
        self.configSpeed: bool = True
        self.slave_pipe_path: Path | None = None
        self.play_channels: Channels = Channels.MONO

    def init(self, engine_key: ServiceID):
        super().init(engine_key)

        can_set_volume: bool = self.canSetVolume()
        can_set_speed: bool = self.canSetSpeed()
        can_set_pitch: bool = self.canSetPitch()
        # vol, speed, pitch = \
        #     self.engine.negotiate_engine_config(
        #             service_key, can_set_volume, can_set_speed, can_set_pitch)
        # self.configVolume = vol
        # self.configSpeed = speed
        channels: Channels = Channels.MONO
        self.play_channels: Channels = channels

    def playArgs(self, phrase: Phrase) -> List[str]:
        clz = MPVAudioPlayer
        args: List[str] = []
        try:
            args.extend(clz.MPV_PLAY_ARGS)
            volume: float = self.get_player_volume(as_decibels=False)
            speed = self.get_player_speed()

            # By default, mpv has --audio-pitch-correction=yes and
            #                     --scaletempo2 selected
            # therefore, a change in speed will automatically preserve pitch
            # and volume
            #
            if int(abs(round(volume * 10))) != 0:
                args.append(f'--volume={volume}')
            if int(abs(round(speed * 10))) != 0:
                args.append(f'--speed={speed}')
            args.append(f'{phrase.get_cache_path()}')
        except ExpiredException:
            reraise(*sys.exc_info())
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'args: {" ".join(args)}')
        return args

    def get_slave_pipe_path(self) -> Path:
        return self.slave_pipe_path

    def get_slave_play_args(self) -> List[str]:
        """
        mpv is used for PlayerMode.SLAVE_FILE & SLAVE_PIPE since it has a much better
        implementation than mplayer.

        In slave mode you have to set volume, speed, etc. for EVERY item
        played because it is reset to the values set when mpv started
        for each item played.

        :return:
        """
        clz = MPVAudioPlayer
        slave_pipe_dir: Path = Path(tempfile.mkdtemp(dir=TempFileUtils.temp_dir()))
        self.slave_pipe_path = slave_pipe_dir.joinpath('mpv.tts')
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'slave_pipe_path: {self.slave_pipe_path}')
        args: List[str] = []
        args.extend(clz.SLAVE_ARGS)
        args.append(f'--input-ipc-server={self.slave_pipe_path}')
        channels: Channels = self.play_channels
        if channels != Channels.NO_PREF:
            args.append(f'--audio-channels={channels.name.lower()}')

        default_volume: float = self.get_player_volume(as_decibels=False)
        default_speed = self.get_player_speed()

        # By default, mpv has --audio-pitch-correction=yes and
        #                     --scaletempo2 selected
        # therefore, a change in speed will automatically preserve pitch
        # and volume
        #
        if int(abs(round(default_volume * 10))) != 0:
            args.append(f'--volume={default_volume}')
        if int(abs(round(default_speed * 10))) != 0:
            args.append(f'--speed={default_speed}')
        return args

    def get_pipe_args(self) -> List[str]:
        clz = MPVAudioPlayer
        args: List[str] = []
        try:
            args.extend(MPVAudioPlayer.MPV_PIPE_ARGS)

            volume: float = self.get_player_volume(as_decibels=False)
            speed = self.get_player_speed()

            # By default, mpv has --audio-pitch-correction=yes and
            #                     --scaletempo2 selected
            # therefore, a change in speed will automatically preserve pitch
            # and volume
            #
            if int(abs(round(volume * 10))) != 0:
                args.append(f'--volume={volume}')
            if int(abs(round(speed * 10))) != 0:
                args.append(f'--speed={speed}')
        except ExpiredException:
            reraise(*sys.exc_info())
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'args: {" ".join(args)}')
        return args

    def canSetSpeed(self) -> bool:
        return True

    def canSetVolume(self) -> bool:
        return True

    def canSetPitch(self) -> bool:
        """
        You CAN set mpv pitch. Just not supporting that capability just yet
        :return:
        """
        return False

    def canSetPipe(self) -> bool:
        return True

    def get_player_speed(self) -> float:
        clz = MPVAudioPlayer
        speed: float = Settings.get_speed()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'speed: {speed}')
        return speed

    def get_player_volume(self, as_decibels: bool = True) -> float:
        """
        mpv supports several types of volume controls
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
        clz = MPVAudioPlayer
        volume_validator: INumericValidator
        volume_validator = SettingsMap.get_validator(clz.MPV_VOLUME_KEY)
        volume_validator: NumericValidator
        volume: float
        if as_decibels:
            volume = volume_validator.as_decibels()
        else:
            volume = volume_validator.as_percent()

        # MY_LOGGER.debug(f'getVolume as_decibels: {as_decibels} volume: {volume}')
        return volume

    def get_player_channels(self) -> Channels:
        """
        User can choose to voice in stereo, mono, or don't care.
        MPV by default plays mono out of one channel, while mplayer plays on both
        stereo speakers. Have not tried 5.1 configurations, buut I think stereo means
        the noormal stereo channels. It is possible to specify all speakers, or the
        center speaker, etc. That can be revisited if needed.

        :return: True means to play in stereo, False means to play in mono,
                 None means to do default behavior
        """

        clz = MPVAudioPlayer
        channel_validator: IChannelValidator
        channel_validator = SettingsMap.get_validator(clz.CHANNELS_KEY)
        channel_validator: ChannelValidator
        channels: Channels = channel_validator.getInternalValue()
        return channels

    @classmethod
    def register(cls, what):
        PlayerIndex.register(MPVAudioPlayer.ID, what)
        BaseServices.register(what)
