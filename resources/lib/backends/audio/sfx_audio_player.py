import os
import threading
import wave

import xbmc

from backends.audio import PLAYSFX_HAS_USECACHED
from backends.audio.base_audio import AudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import ServiceType
from common.logger import BasicLogger
from common.base_services import BaseServices
from common.setting_constants import Players

from common.typing import *
module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class PlaySFXAudioPlayer(AudioPlayer):
    ID = Players.SFX
    # name = 'XBMC PlaySFX'
    _logger: BasicLogger = None
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _supported_input_formats: List[str] = [SoundCapabilities.WAVE]
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    sound_capabilities = SoundCapabilities(ID, _provides_services,
                                           _supported_input_formats,
                                           _supported_output_formats)

    def __init__(self):
        super().__init__()
        cls = type(self)
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)

        self._isPlaying: bool = False
        self.event: threading.Event = threading.Event()
        self.event.clear()

    def doPlaySFX(self, path) -> None:
        xbmc.playSFX(path, False)

    def play(self, path: str) -> None:
        clz = type(self)
        if not os.path.exists(path):
            clz._logger.info('playSFXHandler.play() - Missing wav file')
            return
        self._isPlaying = True
        self.doPlaySFX(path)
        f = wave.open(path, 'r')
        frames = f.getnframes()
        rate = f.getframerate()
        f.close()
        duration = frames / float(rate)
        self.event.clear()
        self.event.wait(duration)
        self._isPlaying = False

    def isPlaying(self) -> bool:
        return self._isPlaying

    def stop(self) -> None:
        self.event.set()
        xbmc.stopSFX()

    def close(self) ->None:
        self.stop()

    @classmethod
    def register(cls):
        PlayerIndex.register(PlaySFXAudioPlayer.ID, PlaySFXAudioPlayer)
        BaseServices.register(cls)

    @staticmethod
    def available(ext=None)  -> bool:
        return xbmc and hasattr(xbmc, 'stopSFX') and PLAYSFX_HAS_USECACHED
