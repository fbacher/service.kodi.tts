from __future__ import annotations  # For union operator |

import os
import sys
import tempfile
from pathlib import Path

from common import *

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.validators import ConstraintsValidator
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
        _availableArgs = (Constants.MPV_PATH, '--help')
    else:
        _availableArgs = (Constants.MPLAYER_PATH, '--help')
    #
    # Run mplayer in slave mode, not exiting when idle and reading
    # slave commands from a path yet to be provided by file=

    MPV_AUDIO_FILTER: str = '--af='
    MPLAYER_AUDIO_FILTER: str = '-af'

    USE_MPV_PLAYER: bool
    if Constants.PLATFORM_WINDOWS:
        USE_MPV_PLAYER = True
    else:
        USE_MPV_PLAYER = False

    MPV_PLAY_ARGS = (Constants.MPV_PATH, '--really-quiet', None)
    MPLAYER_PLAY_ARGS = (Constants.MPLAYER_PATH, '-really-quiet', None)
    MPV_PIPE_ARGS = (Constants.MPV_PATH, '-', '--really_quiet', '--cache', '8192')
    MPLAYER_PIPE_ARGS = (Constants.MPLAYER_PATH, '-', '-really-quiet', '-cache', '8192')
    SLAVE_ARGS: Tuple[str] = (Constants.MPV_PATH, '--really-quiet',  '--idle')

    # _pipeArgs = (Constants.MPLAYER_PATH, '-', '-really-quiet', '-cache', '8192',
    #              '-slave', '-input', 'file=/tmp/tts_mplayer_pipe')
    # Send commands via named pipe (or stdin) to play files:
    # mkpipe ./slave.input
    #
    # Note that speed, volume, etc. RESET between each file played. Example below
    # resets speed/tempo before each play.
    #
    # mplayer  -af "scaletempo" -slave  -idle -input file=./slave.input
    #
    # From another shell:
    # (echo "loadfile <audio_file> 0"; echo "speed_mult 1.5") >> ./slave.input
    # To play another AFTER the previous completes
    # (echo loadfile <audio_file2> 0; echo speed_mult 1.5) >> ./slave.input
    # To stop playing current file and start playing another:
    # (echo loadfile <audio_file3> 1; echo speed_mult 1.5) >>./slave.input

    # Mplayer supports speeds > 0:
    #  0.30 ~1/3 speed
    #  0.5 1/2 speed
    #  1   1 x speed
    #  2   2 x speed ...
    MPV_SPEED_ARGS = 'scaletempo=scale={0}:speed=none'
    MPLAYER_SPEED_ARGS = 'scaletempo=scale={0}:speed=none'

    # Multiplier of 1.0 = 100% of speed (i.e. no change)
    _speedMultiplier: Final[float] = 1.0  # The base range is 3 .. 30.
    _volumeArgs = 'volume={0:.2f}'  # Volume in db -200db .. +40db Default 0
    _logger: BasicLogger = None

    def __init__(self):
        clz = type(self)
        # Set logger here size super also sets clz.logger. And clz is the same for
        # both. This messes up register
        if clz._logger is None:
            clz._logger = module_logger.getChild(self.__class__.__name__)
            clz.register(self)
        super().__init__()

        self.engine_id: str = None
        self.configVolume: bool = True
        self.configSpeed: bool = True
        self.configPitch: bool = True
        self.slave_pipe_path: Path = None

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
            args = self.baseArgs(phrase)
        except ExpiredException:
            reraise(*sys.exc_info())
        #
        # None is returned if engine can not control speed, etc.
        #
        speed: float = self.get_player_speed()
        # Get the volume produced by the engine using TTS scale

        volume: float
        if clz.USE_MPV_PLAYER:
            volume = self.get_player_volume()
        else:
            volume = self.get_player_volume()

        if speed is None:
            self.configSpeed = False
        if volume is None:
            self.configVolume = False

        if self.configSpeed or self.configVolume:
            filters: List[str] = []
            if self.configSpeed:
                filters.append(clz.MPV_SPEED_ARGS.format(
                        self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            audio_filter: List[str] = []
            if clz.USE_MPV_PLAYER:
                audio_filter.append(f'{MPlayerAudioPlayer.MPV_AUDIO_FILTER}{",".join(filters)}')
            else:
                audio_filter.append(MPlayerAudioPlayer.MPLAYER_AUDIO_FILTER)
                audio_filter.append(",".join(filters))
            clz._logger.debug(f'audio_filter: {audio_filter}')
            args.extend(audio_filter)
        self._logger.debug_verbose(f'args: {" ".join(args)}')
        return args

    '''
    def get_speed_volume_argsx(self) -> List[str]:
        clz = type(self)
        args: List[str] = []
        #
        # None is returned if engine can not control speed, etc.
        #
        speed: float = self.get_player_speed()
        # Get the volume produced by the engine using TTS scale
        volume: float
        volume = self.get_player_volume()
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
            clz._logger.debug(f'audio_filter: {MPlayerAudioPlayer.AUDIO_FILTER}')

            if Constants.PLATFORM_WINDOWS:
                args.append(f'{MPlayerAudioPlayer.AUDIO_FILTER}{",".join(filters)}')
            else:
                args.append(MPlayerAudioPlayer.AUDIO_FILTER)
                args.append(",".join(filters))

            clz._logger.debug(f'audio_filters: {",".join(filters)}')
        return args
    '''

    def get_slave_pipe_path(self):
        return self.slave_pipe_path

    '''
    def get_start_slave_args(self):
        clz = type(self)
        slave_pipe_dir: Path = Path(tempfile.mkdtemp())
        self.slave_pipe_path = slave_pipe_dir.joinpath('mpv.tts')
        clz._logger.debug(f'slave_pipe_path: {self.slave_pipe_path}')
        args: List[str] = []
        args.extend(clz.SLAVE_ARGS)
        args.append(f'--input-ipc-server={self.slave_pipe_path}')
        # args.extend(self.get_speed_volume_args())
        #  Debug.dump_all_threads(0.0)
        self._logger.debug(f'args: {args}')
        return args
        '''

    def get_slave_play_args(self) -> List[str]:
        """
        mpv is used for slave mode since it has a much better implementation
        than mplayer.

        In slave mode you have to set volume, speed, etc. for EVERY item
        played because it is reset to the values set when mplayer started
        for each item played.

        :return:
        """
        clz = type(self)
        slave_pipe_dir: Path = Path(tempfile.mkdtemp())
        self.slave_pipe_path = slave_pipe_dir.joinpath('mpv.tts')
        clz._logger.debug(f'slave_pipe_path: {self.slave_pipe_path}')
        args: List[str] = []
        args.extend(clz.SLAVE_ARGS)
        args.append(f'--input-ipc-server={self.slave_pipe_path}')
        speed: float = self.get_player_speed()
        volume: float = self.get_player_volume()
        if speed is None:
            self.configSpeed = False
        if volume is None:
            self.configVolume = False

        if False:  # self.configSpeed or self.configVolume:
            filters = []
            if self.configSpeed:
                filters.append(clz.MPV_SPEED_ARGS.format(
                        self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            args.append(
                    f'{MPlayerAudioPlayer.MPV_AUDIO_FILTER}{",".join(filters)}')
        self._logger.debug_verbose(f'args: {" ".join(args)}')
        return args

    def get_pipe_args(self) -> List[str]:
        clz = type(self)
        args: List[str] = []
        args.extend(self._pipeArgs)
        speed: float = self.get_player_speed()
        volume: float = self.get_player_volume()
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
            audio_filter: List[str] = []
            if clz.USE_MPV_PLAYER:
                audio_filter.append(
                    f'{MPlayerAudioPlayer.MPV_AUDIO_FILTER}{",".join(filters)}')
            else:
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
        speed_validator: ConstraintsValidator
        speed_validator = clz.get_validator(clz.service_ID,
                                            property_id=SettingsProperties.SPEED)
        speed = speed_validator.get_impl_value(self.engine_id)
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

                 The quality of adjusting volume in software is inferior to
                 adjusting in hardware, but it is frequently simplier to adjust
                 the software volume.
        :return:
        """
        clz = type(self)
        volume_validator: ConstraintsValidator

        # Get validator that gives units in native (MPlayer) units.

        volume_validator = clz.get_validator(clz.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume = volume_validator.get_impl_value(self.engine_id,
                                                 as_decibels=as_decibels)
        # mplayer volume of 0.0 means don't change volume (or 1.0)
        # mpv volume of 0.0 means no sound

        if volume < 0.01:
            volume = 1.0

        return volume

    @classmethod
    def register(cls, what):
        PlayerIndex.register(MPlayerAudioPlayer.ID, what)
        BaseServices.register(what)
