# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.players.player_index import PlayerIndex
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import Players

module_logger: BasicLogger = BasicLogger.get_logger(__name__)


class PaplayAudioPlayer(SubprocessAudioPlayer):
    #
    # Pulse Audio player_key
    #
    # Has ability to play on remote server
    #
    ID = Players.PAPLAY
    # name = 'paplay'
    _availableArgs = ('paplay', '--version')
    _playArgs = ('paplay', None)
    _pipeArgs = ('paplay',)
    _volumeArgs = ('--volume', None)

    def __init__(self):
        super().__init__()
        self._logger = module_logger

    def playArgs(self, path):
        args = self.baseArgs(path)
        if self.volume:
            args.extend(self._volumeArgs)
            # Convert dB to paplay value
            args[args.index(None)] = str(
                    int(65536 * (10 ** (self.volume / 20.0))))
            self._logger.debug_v(f'args: {" ".join(args)}')
        return args

    def canSetVolume(self):
        return True

    @classmethod
    def register(cls):
        PlayerIndex.register(PaplayAudioPlayer.ID, PaplayAudioPlayer)
        BaseServices.register(cls)
