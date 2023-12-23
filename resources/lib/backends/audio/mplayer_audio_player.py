import os
import sys
import tempfile

from backends.audio.base_audio import PlayerSlaveInfo, SubprocessAudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.validators import ConstraintsValidator
from common.base_services import BaseServices
from common.exceptions import ExpiredException
from common.logger import BasicLogger
from common.phrases import Phrase
from common.setting_constants import Players
from common.typing import *

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

    _availableArgs = ('/usr/bin/mplayer', '--help')
    #
    # Run mplayer in slave mode, not exiting when idle and reading
    # slave commands from a path yet to be provided by file=

    _slave_args: Tuple[str] = ('/usr/bin/mpv', '--really-quiet',
                               '--idle')
    _playArgs = ('/usr/bin/mplayer', '-really-quiet', None)

    _pipeArgs = ('/usr/bin/mplayer', '-', '-really-quiet', '-cache', '8192')
    # _pipeArgs = ('/usr/bin/mplayer', '-', '-really-quiet', '-cache', '8192',
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
    _speedArgs = 'scaletempo=scale={0}:speed=none'

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
        volume = self.get_player_volume()
        if speed is None:
            self.configSpeed = False
        if volume is None:
            self.configVolume = False

        if self.configSpeed or self.configVolume:
            args.append('-af')
            filters = []
            if self.configSpeed:
                filters.append(self._speedArgs.format(
                        self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            args.append(','.join(filters))
        self._logger.debug_verbose(f'args: {" ".join(args)}')
        #  Debug.dump_all_threads(0.0)
        return args

    def get_speed_volume_args(self) -> List[str]:
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
            args.append('-af')
            filters = []
            if self.configSpeed:
                filters.append(self._speedArgs.format(
                        self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            args.append(','.join(filters))
        return args

    def get_start_slave_args(self):
        clz = type(self)
        slave_pipe_dir: str = tempfile.mkdtemp()
        slave_pipe_path = os.path.join(slave_pipe_dir, 'mplayer.tts')
        clz._logger.debug(f'slave_pipe_path: {slave_pipe_path}')
        # try:
        #     os.mkfifo(slave_pipe_path)
        # except OSError as e:
        #     clz._logger.exception(f'Failed to create FIFO: {slave_pipe_path}')

        self.slave_info = PlayerSlaveInfo(slave_pipe_dir, slave_pipe_path)
        args: List[str] = []
        args.extend(clz._slave_args)
        args.append(f'--input-ipc-server={slave_pipe_path}')
        # args.extend(self.get_speed_volume_args())
        #  Debug.dump_all_threads(0.0)
        self._logger.debug(f'args: {args}')
        return args

    def get_slave_play_args(self) -> List[str]:
        """
        In slave mode you have to set volume, speed, etc. for EVERY item
        played because it is reset to the values set when mplayer started
        for each item played.

        :return:
        """
        clz = type(self)
        args: List[str] = []
        args.extend(self._play_slave_args)
        speed: float = self.get_player_speed()
        volume: float = self.get_player_volume()
        if speed is None:
            self.configSpeed = False
        if volume is None:
            self.configVolume = False

        if self.configSpeed or self.configVolume:
            args.append('-af')
            filters = []
            if self.configSpeed:
                filters.append(self._speedArgs.format(
                        self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            args.append(','.join(filters))
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
            args.append('-af')
            filters = []
            if self.configSpeed:
                filters.append(self._speedArgs.format(
                        self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            args.append(','.join(filters))
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

    def get_player_volume(self) -> float:
        clz = type(self)
        volume_validator: ConstraintsValidator
        volume_validator = clz.get_validator(clz.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume = volume_validator.get_impl_value(self.engine_id)
        return volume

    @classmethod
    def register(cls, what):
        PlayerIndex.register(MPlayerAudioPlayer.ID, what)
        BaseServices.register(what)
