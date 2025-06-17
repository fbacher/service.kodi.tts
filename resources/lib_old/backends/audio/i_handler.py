# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.players.iplayer import IPlayer
from backends.settings.setting_properties import SettingProp
from common import *
from common.logger import *
from common.settings import Settings

module_logger: BasicLogger = BasicLogger.get_logger(__name__)


class PlayerHandlerType:
    ID: None
    _advanced: bool = None
    sound_file_types: List[str] = ['.wav']
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger

    def __init__(self):
        clz = type(self)
        self.hasAdvancedPlayer: bool
        clz._logger = module_logger
        self.availablePlayers: List[Type[IPlayer]] | None

    @classmethod
    def getAvailablePlayers(cls, include_builtin=True) -> List['PlayerHandlerType']:
        raise Exception('Not Implemented')

    def get_player(self, player_id) -> Union[Type[IPlayer], None]:
        raise Exception('Not Implemented')

    def setPlayer(self, preferred=None, advanced=None):
        raise Exception('Not Implemented')

    def getSpeed(self) -> float:
        speed: float = Settings.getSetting(SettingProp.SPEED,
                                           Settings.get_engine_id())
        return speed

    def getVolumeDb(self) -> float:
        volumeDb: float = Settings.getSetting(SettingProp.VOLUME,
                                              Settings.get_engine_id())
        return volumeDb

    def setSpeed(self, speed: float):
        self._logger.debug(f'setSpeed: {speed}')
        pass  # self.speed = speed

    def setVolume(self, volume: float):
        self._logger.debug(f'setVolume: {volume}')
        pass  # self.volume = volume

    def player(self) -> str | None:
        raise Exception('Not Implemented')

    def canSetPipe(self) -> bool:
        raise Exception('Not Implemented')

    def pipeAudio(self, source):
        raise Exception('Not Implemented')

    @classmethod
    def get_sound_file(cls, text: str, sound_file_types: List[str] | None = None,
                       use_cache: bool = False) -> str:
        raise Exception('Not Implemented')

    @classmethod
    def set_sound_dir(cls):
        raise Exception('Not Implemented')

    def play(self):
        raise Exception('Not Implemented')

    def isPlaying(self):
        raise Exception('Not Implemented')

    def stop(self):
        raise Exception('Not Implemented')

    def close(self):
        raise Exception('Not Implemented')
