from backends.audio.base_audio import SubprocessAudioPlayer
from backends.players.player_index import PlayerIndex
from common.logger import BasicLogger
from common.base_services import BaseServices
from common.setting_constants import Players
from common.typing import *
module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)

class AplayAudioPlayer(SubprocessAudioPlayer):
    #
    # ALSA player. amixer could be used for volume, etc.
    #
    ID = Players.APLAY
    # name = 'aplay'
    _availableArgs = ('aplay', '--version')
    _playArgs = ('aplay', '-q', None)
    _pipeArgs = ('aplay', '-q')
    kill = True

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
                self.__class__.__name__)  # type: module_logger

    def canSetPipe(self) -> bool:  # Input and output supported
        return True

    @classmethod
    def register(cls):
        PlayerIndex.register(AplayAudioPlayer.ID, AplayAudioPlayer)
        BaseServices.register(cls)
