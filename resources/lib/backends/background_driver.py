# coding=utf-8

'''
 Some speech engines may produce high quality voices, but at an unacceptably slow
 rate. This driver converts text to speech in the background and pupulates the
 cache.
 '''
import threading
from pathlib import Path

import xbmcvfs

from backends.base import BaseEngineService
from backends.players.iplayer import IPlayer
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from common.base_services import BaseServices
from common.file_utils import Delay, FindTextToVoice
from common.logger import BasicLogger
from common.monitor import Monitor
from common.setting_constants import Backends
from common.settings import Settings
from common.typing import *

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class BackgroundDriver(BaseServices):

    #  Find .txt files which don't have corresponding .mp3 files in the cace
    #  Proceed to generate sound files for each

    _unvoiced_phrases: List[str] = []
    _logger: BasicLogger = None


    def __init__(self, engine_id: str, seconds_delay: int = 20):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(self.__class__.__name__)

        self.engine_id: str = engine_id
        self.engine: BaseEngineService = BaseServices.getService(engine_id)
        cache_path: str = Settings.getSetting(SettingsProperties.CACHE_PATH,
                                              SettingsProperties.TTS_SERVICE,
                                              SettingsProperties.CACHE_PATH_DEFAULT)
        engine_dir: str = Backends.ENGINE_CACHE_CODE[engine_id]
        self.cache_directory: str = xbmcvfs.translatePath(f'{cache_path}/{engine_dir}')
        self.work_list = FindTextToVoice(top=self.cache_directory)
        self.thread: threading.Thread = None
        self.stop: bool = False
        self.seconds_delay: int = seconds_delay
        self.delay: Delay = None

    def start(self):
        self.stop = False
        self.thread = threading.Thread(target=self.create_voice_files)
        self.delay = Delay(bias=self.seconds_delay, call_scale_factor=0.0,
                           scale_factor=0.0)
        self.thread.start()

    def stop(self):
        self.stop = True

    def create_voice_files(self):
        while not self.stop:
            self.voice_next()

    def voice_next(self) -> Path:
        if self.stop:
            return None

        clz = type(self)
        finished: bool = False
        voiced_file: Path = None
        while not finished:
            self.delay.delay()
            text_file: Path = self.work_list.get_next()
            if text_file is None:
                return

            text: str
            try:
                with open(text_file, 'rt') as f:
                    text = f.read()
            except Exception as e:
                clz._logger.exception('')

            try:
                voiced_file = self.generate_voice(text)
            except Exception as e:
                clz._logger.exception('')
        return voiced_file

    def generate_voice(self, text: str) -> Path:
        Monitor.exception_on_abort(timeout=0.01)
        player_id: str = SettingsMap.get_value(self.engine_id,
                                               SettingsProperties.PLAYER)

        # Forces initialization and populates capabilities, settings, etc.

        player: IPlayer = PlayerIndex.get_player(player_id)
        cached_voice_file: str = None
        exists: bool = False

        if player_id == Services.INTERNAL_PLAYER_ID:
            return None
        else:
            cached_voice_file, exists = self.engine.get_path_to_voice_file(text,
                                                                    use_cache=True)
            if exists:
                return Path(cached_voice_file)
            exists = self.engine.runCommand(text, cached_voice_file)
            if exists:
                clz = type(self)
                clz._logger.debug(f'generated cache file for {text}')
                return Path(cached_voice_file)
            return None
