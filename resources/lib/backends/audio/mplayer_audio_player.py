import sys
from zipfile import Path

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.backend_info_bridge import BackendInfoBridge
from backends.players.player_index import PlayerIndex
from backends.settings.constraints import Constraints
from backends.settings.i_validators import IIntValidator, IValidator
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator
from common.debug import Debug
from common.exceptions import ExpiredException
from common.logger import BasicLogger
from common.base_services import BaseServices
from common.phrases import Phrase
from common.setting_constants import Players
from common.settings import Settings
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
    _playArgs = ('/usr/bin/mplayer', '-really-quiet', None)
    _pipeArgs = ('/usr/bin/mplayer', '-', '-really-quiet', '-cache', '8192')
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

        self.configVolume: bool = False
        self.configSpeed: bool = False
        self.configPitch: bool = False

    def init(self, service_id: str):
        # engine_id: str = Settings.get_engine_id()
        self.configVolume, self.configSpeed, self.configPitch = \
            BackendInfoBridge.negotiate_engine_config(
                    service_id, self.canSetVolume(),
                    self.canSetSpeed(), self.canSetPitch())

    def scaleVolume(self) -> float:
        """
            Scales the volume produced by the engine using TTS scale.
            Any difference between the engine's volume and the configured TTS
            volume will have to be compensated by the player.
            :returns: the engine's volume using TTS scale
        """
        clz = type(self)
        engine_id: str = Settings.get_engine_id()
        engine_constraints: Constraints
        engine_volume_val: ConstraintsValidator | IIntValidator
        engine_volume_val = SettingsMap.get_validator(engine_id,
                                                      SettingsProperties.VOLUME)
        engine_volume: int = engine_volume_val.getValue()
        engine_constraints = engine_volume_val.constraints
        player_volume_val: IValidator | ConstraintsValidator
        player_volume_val = SettingsMap.get_validator(clz.service_ID,
                                                      SettingsProperties.VOLUME)
        player_constraints: Constraints = player_volume_val.constraints
        player_volume: float = player_constraints.translate_value(engine_constraints,
                                                                  - engine_volume)
        return player_volume

    def playArgs(self, phrase: Phrase):
        clz = type(self)
        try:
            args = self.baseArgs(phrase)
        except ExpiredException:
            reraise(*sys.exc_info())
        #
        # None is returned if engine can not control speed, etc.
        #
        speed: float = self.getPlayerSpeed()
        # Get the volume produced by the engine using TTS scale
        volume: float
        # volume = self.getVolumeDb()
        volume = self.scaleVolume()
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
        #  self._logger.debug_verbose(f'args: {" ".join(args)}')
        #  Debug.dump_all_threads(0.0)
        return args

    # def play(self, path: str):
    #     clz = type(self)
    #     args = self.playArgs(path)
    #     clz._logger.debug_verbose(f'args: {" ".join(args)}')

    def get_pipe_args(self) -> List[str]:
        clz = type(self)
        args: List[str] = []
        args.extend(self._pipeArgs)
        speed: float = self.getPlayerSpeed()
        volume: float = self.getVolumeDb()
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

    def getPlayerSpeed(self) -> float | None:
        clz = type(self)
        # Get speed of cached voice
        engine_id: str = Settings.get_engine_id()
        engine: BaseServices = BaseServices.getService(Settings.get_engine_id())
        cache_speed: float | None = engine.getSpeed()
        engine_speed_validator: ConstraintsValidator | IValidator
        engine_speed_validator = SettingsMap.get_validator(service_id=engine_id,
                                                           property_id=SettingsProperties.SPEED)
        if engine_speed_validator is None:
            return None
        engine_speed_constraints: Constraints = engine_speed_validator.constraints
        engine_speed: float = engine_speed_validator.getValue()

        """
            Scale the speed produced by the engine using TTS scale.
            Any difference between the engine's speed and the configured TTS
            speed will have to be compensated by the player.
            :returns: the engine's speed using TTS scale
        """
        current_speed: float = cache_speed
        desired_speed: float = engine_speed
        player_speed_val: IValidator | ConstraintsValidator
        player_speed_val = SettingsMap.get_validator(clz.service_ID,
                                                      SettingsProperties.SPEED)
        player_constraints: Constraints = player_speed_val.constraints
        player_speed: float = player_constraints.translate_value(engine_speed_constraints,
                                                                  cache_speed)
        return 1.50

    @classmethod
    def register(cls, what):
        PlayerIndex.register(MPlayerAudioPlayer.ID, what)
        BaseServices.register(what)
