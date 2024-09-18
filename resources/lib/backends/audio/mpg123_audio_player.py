from __future__ import annotations  # For union operator |

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import Services, ServiceType
from common import *
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import Players

module_logger: BasicLogger = BasicLogger.get_logger(__name__)


class Mpg123AudioPlayer(SubprocessAudioPlayer, BaseServices):
    ID = Players.MPG123
    service_ID = Services.MPG123_ID
    # name = 'mpg123'
    _availableArgs = ('mpg123', '--version')
    _playArgs = ('mpg123', '-q', None)
    _pipeArgs = ('mpg123', '-q', '-')

    _supported_input_formats: List[str] = [SoundCapabilities.MP3]
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    _logger: BasicLogger = None

    def __init__(self) -> None:
        super().__init__()
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
            clz.register(clz)

    def canSetSpeed(self) -> bool:
        return False

    def canSetVolume(self) -> bool:  # (1-100)
        return False

    def canSetPitch(self) -> bool:  # Depends upon hardware used.
        return False

    def canSetPipe(self) -> bool:  # Can read to/from pipe
        return True

    @classmethod
    def register(cls):
        PlayerIndex.register(Mpg123AudioPlayer.ID, Mpg123AudioPlayer)
        BaseServices.register(cls)
