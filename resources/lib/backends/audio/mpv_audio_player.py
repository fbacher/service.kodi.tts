from __future__ import annotations  # For union operator |

import subprocess
import sys
import tempfile
from pathlib import Path

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.i_validators import IChannelValidator, INumericValidator
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (ChannelValidator, NumericValidator)
from common import *
from common.base_services import BaseServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.logger import BasicLogger
from common.phrases import Phrase
from common.setting_constants import Channels, Players

module_logger: BasicLogger = BasicLogger.get_logger(__name__)


class MPVAudioPlayer(SubprocessAudioPlayer, BaseServices):
    """
     name = 'MPV'
     MPV is based on MPLAYER. It offers several improvements, particularly with
     running in slave mode. Using slave mode eliminates the overhead and delay of
     launching a player for each phrase spoken. There are some significant differences
     in the commands/aruments/behavior, but not radically different.

     MPV supports -idle and -slave which keeps player from exiting
     after files played. When in slave mode, commands are read from sockets or
     named pipe.
    """
    ID = Players.MPV
    service_ID: str = Services.MPV_ID
    service_TYPE: str = ServiceType.PLAYER

    _supported_input_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER,
                                             ServiceType.CONVERTER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    _availableArgs: Tuple[str, str] = (Constants.MPV_PATH, '--help')

    """
    There are many, many features. But what we are most interested in are:
     - Adjusting volume, pitch and speed (without changing pitch)
     - Using mpv in slave mode, as a daemon
    
    For consistency use same options for slave and non-slave modes.
       non-slave mode use command-line arguments:
       --volume=<float>, (in percent change 100 == no change)
       --speed  (accepts a <float> multiplier 1 == no change)

       slave mode commands are sent as json over pipe 
        # For volume, send:
           f'{{ "command": ["set_property", "volume", "{self.volume}"],'
                f' "request_id": "{self.latest_request_sequence_number}" }}'
          The volume is again in percent change.
          
          For speed use:
           f'{{ "command": ["set_property", '
                              f'"speed", "{self.speed}"], "request_id": '
                              f'"{self.latest_request_sequence_number}" }}
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
    
     mplayer  -af "scaletempo" -slave  -idle -input file=./slave.input
    
     From another shell:
     (echo "loadfile <audio_file> 0"; echo "speed_mult 1.5") >> ./slave.input
     To play another AFTER the previous completes
     (echo loadfile <audio_file2> 0; echo speed_mult 1.5) >> ./slave.input
     To stop playing current file and start playing another:
     (echo loadfile <audio_file3> 1; echo speed_mult 1.5) >>./slave.input

     Mplayer supports speeds > 0:
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

    _logger: BasicLogger = None

    def __init__(self):
        clz = MPVAudioPlayer
        # Set get here size super also sets clz.get. And clz is the same for
        # both. This messes up register
        if clz._logger is None:
            clz._logger = module_logger
            clz.register(self)
        super().__init__()

        self.engine_id: str | None = None
        self.configVolume: bool = True
        self.configSpeed: bool = True
        self.slave_pipe_path: Path | None = None
        self.play_channels: Channels = Channels.MONO

    def init(self, engine_id: str):
        self.engine_id = engine_id
        engine: BaseServices = BaseServices.getService(engine_id)

        can_set_volume: bool = self.canSetVolume()
        can_set_speed: bool = self.canSetSpeed()
        can_set_pitch: bool = self.canSetPitch()
        vol, speed, pitch = \
            engine.negotiate_engine_config(
                    engine_id, can_set_volume, can_set_speed, can_set_pitch)
        self.configVolume = vol
        self.configSpeed = speed
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
                args.append(f'--default_volume={volume}')
            if int(abs(round(speed * 10))) != 0:
                args.append(f'--default_speed={speed}')
                args.append(f'{phrase.get_cache_path()}')
        except ExpiredException:
            reraise(*sys.exc_info())
        self._logger.debug_v(f'args: {" ".join(args)}')
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
        slave_pipe_dir: Path = Path(tempfile.mkdtemp())
        self.slave_pipe_path = slave_pipe_dir.joinpath('mpv.tts')
        clz._logger.debug(f'slave_pipe_path: {self.slave_pipe_path}')
        args: List[str] = []
        args.extend(clz.SLAVE_ARGS)
        args.append(f'--input-ipc-server={self.slave_pipe_path}')
        channels: Channels = self.play_channels
        if channels != Channels.NO_PREF:
            args.append(f'--audio-channels={channels.name.lower()}')
        '''
        speed: float = self.get_player_speed()
        volume: float = self.get_player_volume(as_decibels=True)
        if speed is None:
            self.configSpeed = False
        if volume is None:
            self.configVolume = False

        if self.configSpeed or self.configVolume:
            filters = []
            if self.configSpeed:
                filters.append(clz.MPV_SPEED_ARGS.format(
                        self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            args.append(
                    f'{MPVAudioPlayer.MPV_AUDIO_FILTER}{",".join(filters)}')
        '''
        self._logger.debug_v(f'args: {" ".join(args)}')
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
                args.append(f'--default_volume={volume}')
            if int(abs(round(speed * 10))) != 0:
                args.append(f'--default_speed={speed}')
        except ExpiredException:
            reraise(*sys.exc_info())
        self._logger.debug_v(f'args: {" ".join(args)}')
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
        speed_validator: NumericValidator
        speed_validator = clz.get_validator(self.service_ID,
                                            property_id=SettingsProperties.SPEED)
        speed = speed_validator.get_value()
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
        volume_validator = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                     property_id=SettingsProperties.VOLUME)
        volume_validator: NumericValidator
        volume: float
        if as_decibels:
            volume = volume_validator.as_decibels()
        else:
            volume = volume_validator.as_percent()

        # clz._logger.debug(f'getVolume as_decibels: {as_decibels} volume: {volume}')
        return volume

    def get_player_channels(self) -> Channels:
        """
        User can choose to prefer TTS to voice in stereo, mono, or don't care.
        MPV by default plays mono out of one channel, while mplayer plays on both
        stereo speakers. Have not tried 5.1 configurations, buut I think stereo means
        the noormal stereo channels. It is possible to specify all speakers, or the
        center speaker, etc. That can be revisited if needed.

        :return: True means to play in stereo, False means to play in mono,
                 None means to do default behavior
        """

        clz = MPVAudioPlayer
        channel_validator: IChannelValidator
        channels_prop: str = SettingsProperties.CHANNELS
        channel_validator = SettingsMap.get_validator(clz.service_ID,
                                                      property_id=channels_prop)
        channel_validator: ChannelValidator
        channels: Channels = channel_validator.getInternalValue()
        return channels

    @classmethod
    def register(cls, what):
        PlayerIndex.register(MPVAudioPlayer.ID, what)
        BaseServices.register(what)

    @classmethod
    def available(cls, ext=None) -> bool:
        try:
            subprocess.run(cls._availableArgs, stdout=subprocess.DEVNULL,
                           universal_newlines=True, stderr=subprocess.STDOUT)
        except AbortException:
            reraise(*sys.exc_info())
        except:
            return False
        return True
