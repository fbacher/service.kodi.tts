from __future__ import annotations  # For union operator |

import os
import sys
import threading

from backends.audio.base_audio import AudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import ServiceType
from common import *
from common import utils
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import Players
from common.system_queries import SystemQueries

module_logger: BasicLogger = BasicLogger.get_logger(__name__)


class WindowsAudioPlayer(AudioPlayer):
    ID = Players.WINDOWS
    service_ID = ID
    # name = 'Windows Internal'
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None
    _supported_input_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    _available = SystemQueries.is_windows
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    @classmethod
    def init_class(cls):
        if cls._logger is None:
            cls._logger = module_logger

    def __init__(self, *args, **kwargs):
        super().__init__()

        from . import winplay
        self._player = winplay
        self.audio = None
        self.event: threading.Event = threading.Event()
        self.event.clear()

    def play(self, path):
        if not os.path.exists(path):
            type(self)._logger.info(
                    f'WindowsAudioPlayer.play() - Missing sound file: {path}')
            return
        self.audio = self._player.load(path)
        self.audio.play()
        self.event.clear()
        self.event.wait(self.audio.milliseconds() / 1000.0)
        if self.event.isSet():
            self.audio.stop()
        while self.audio.isplaying():
            utils.sleep(10)
        self.audio = None

    def isPlaying(self):
        return not self.event.isSet()

    def stop(self):
        self.event.set()

    def close(self):
        self.stop()

    @staticmethod
    def available(ext=None):
        if not SystemQueries.isWindows():
            return False
        try:
            from . import winplay  # @analysis:ignore
            return True
        except AbortException:
            reraise(*sys.exc_info())
        except:
            WindowsAudioPlayer._logger.error('winplay import failed')
        return False

    @classmethod
    def register(cls):
        PlayerIndex.register(WindowsAudioPlayer.ID, WindowsAudioPlayer)
        BaseServices.register(cls)


WindowsAudioPlayer.init_class()
