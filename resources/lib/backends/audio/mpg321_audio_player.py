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


class Mpg321AudioPlayer(SubprocessAudioPlayer):
    ID = Players.MPG321
    service_ID = ID
    # name = 'mpg321'
    _availableArgs: Tuple[str, str] = ('mpg321', '--version')
    _playArgs: Tuple[str, str, str] = ('mpg321', '-q', None)
    _pipeArgs: Tuple[str, str, str] = ('mpg321', '-q', '-')

    _supported_input_formats: List[str] = [SoundCapabilities.MP3]
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
                self.__class__.__name__)  # type: module_logger

    def canSetVolume(self):
        return True

    def canSetPitch(self):
        return False

    def canSetPipe(self) -> bool:  # Can read/write to pipe
        return True

    @classmethod
    def register(cls):
        PlayerIndex.register(Mpg321AudioPlayer.ID, Mpg321AudioPlayer)
        BaseServices.register(cls)
