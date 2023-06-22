from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.backend_info_bridge import BackendInfoBridge
from backends.players.player_index import PlayerIndex
from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator
from common.debug import Debug
from common.logger import BasicLogger
from common.base_services import BaseServices
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

    _availableArgs = ('mplayer', '--help')
    _playArgs = ('mplayer', '-really-quiet', None)
    _pipeArgs = ('mplayer', '-', '-really-quiet', '-cache', '8192')
    # Mplayer supports speeds > 0:
    #  0.30 ~1/3 speed
    #  0.5 1/2 speed
    #  1   1 x speed
    #  2   2 x speed ...
    _speedArgs = 'scaletempo=scale={0}:speed=none'

    # Multiplier of 1.0 = 100% of speed (i.e. no change)
    _speedMultiplier: Final[float] = 1.0  # The base range is 3 .. 30.
    _volumeArgs = 'volume={0}'  # Volume in db -200db .. +40db Default 0
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

    def playArgs(self, path: str):
        clz = type(self)
        args = self.baseArgs(path)
        #
        # None is returned if engine can not control speed, etc.
        #
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
        engine_id: str = Settings.get_engine_id()
        engine_speed_validator: ConstraintsValidator | IValidator
        engine_speed_validator = SettingsMap.get_validator(service_id=engine_id,
                                                           property_id=SettingsProperties.SPEED)
        if engine_speed_validator is None:
            return None
        engine_speed: float = engine_speed_validator.getValue()
        # Kodi TTS speed representation is 0.25 .. 4.0
        # 0.25 = 1/4 speed, 4.0 is 4x speed
        player_speed: float = engine_speed
        return player_speed

    @classmethod
    def register(cls, what):
        PlayerIndex.register(MPlayerAudioPlayer.ID, what)
        BaseServices.register(what)
