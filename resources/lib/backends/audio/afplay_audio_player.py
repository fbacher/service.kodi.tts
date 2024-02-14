from __future__ import annotations  # For union operator |

from common import *

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import ServiceType
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import Players

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class AfplayPlayer(SubprocessAudioPlayer):  # OSX
    ID = Players.AFPLAY
    service_ID = ID
    # name = 'afplay'
    _availableArgs = ('afplay', '-h')
    _playArgs = ('afplay', None)
    _speedArgs = ('-r', None)  # usable values 0.4 to 3.0
    # 0 (silent) 1.0 (normal/default) 255 (very loud) db
    _volumeArgs = ('-v', None)
    kill = True
    _supported_input_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
                self.__class__.__name__)  # type: module_logger

    def getVolume(self) -> float:
        volume: float = super().getVolumeDb()
        self.volume = min(int(100 * (10 ** (volume / 20.0))),
                          100)  # Convert dB to percent

    def getSpeed(self) -> float:
        speed: float = super().getSpeed() * 0.01
        return speed

    def playArgs(self, path):
        args = self.baseArgs(path)
        speed: float = self.getSpeed()
        volume: float = self.getVolume()
        args.extend(self._volumeArgs)
        args[args.index(None)] = str(volume)

        args.extend(self._speedArgs)
        args[args.index(None)] = str(speed)
        self._logger.debug_verbose(f'args: {" ".join(args)}')
        return args

    def canSetSpeed(self) -> bool:
        return True

    def canSetVolume(self) -> bool:
        return True

    @classmethod
    def register(cls):
        PlayerIndex.register(AfplayPlayer.ID, AfplayPlayer)
        BaseServices.register(cls)
