from __future__ import annotations  # For union operator |

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilities import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import ServiceType
from common import *
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import AudioType, Players

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class AplayAudioPlayer(SubprocessAudioPlayer):
    #
    # ALSA player. amixer could be used for volume, etc.
    #
    ID: Final[str] = Players.APLAY
    service_ID: Final[str] = ID
    # name = 'aplay'
    _availableArgs = ('aplay', '--version')
    _playArgs = ('aplay', '-q', None)
    _pipeArgs = ('aplay', '-q')
    kill = True

    _supported_input_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
    _supported_output_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER,
                                             ServiceType.TRANSCODER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    def __init__(self):
        super().__init__()

    def canSetPipe(self) -> bool:  # Input and output supported
        return True

    @classmethod
    def register(cls):
        PlayerIndex.register(AplayAudioPlayer.ID, AplayAudioPlayer)
        BaseServices.register(cls)
