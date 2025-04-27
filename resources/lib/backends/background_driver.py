# coding=utf-8

"""
 Some speech engines may produce high quality voices, but at an unacceptably slow
 rate. This driver converts text to speech in the background and pupulates the
 cache.
"""
from __future__ import annotations

from pathlib import Path

import xbmcvfs

from backends.settings.service_types import ServiceKey, TTS_Type
from backends.settings.setting_properties import SettingProp
from common import *

from backends.base import SimpleTTSBackend
from backends.settings.settings_map import SettingsMap
from cache.voicecache import CacheEntryInfo, VoiceCache
from common.base_services import BaseServices
from common.constants import Constants
from common.file_utils import Delay, FindTextToVoice
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase
from common.settings import Settings
from utils.util import runInThread

module_logger: BasicLogger = BasicLogger.get_logger(__name__)


class BackgroundDriver(BaseServices):

    #  Find .txt files which don't have corresponding .mp3 files in the cache
    #  Proceed to generate sound files for each

    _unvoiced_phrases: List[str] = []
    _logger: BasicLogger = None
    _default_delay: int = 3 * 60

    def __init__(self):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger

        self.active_engine: BaseServices | None = None
        self.cache_directory: Path = None
        self.delay: Delay = None
        self.seconds_delay: int = clz._default_delay
        self.work_list: FindTextToVoice = None
        VoiceCache.register_cache_change_listener(self.cache_change_listener)

    def cache_change_listener(self, changed_cache_dir: str):
        """
         Called when a missing voice file is referenced from the cache.
         Our job is to generate every missing voice file from the given directory

         cache files are organized:
          <cache_path>/<engine_code>/<first-two-chars-of-cache-file-name
          >/<cache_file_name>.<suffix>

          Example: cache_path =  ~/.kodi/userdata/addon_data/service.kodi.tts/cache
                   engine_code = goo (for google)
                   first-two-chars-of-cache-file-name = d4
                   hash of text  = cache_file_name = d4562ab3243c84746a670e47dbdc61a2
                   suffix = .mp3 or .txt

        :param changed_cache_dir:  the first-two-chars-of-cache-file-name, above
        :return: None when finished
        """
        clz = type(self)
        engine_key: ServiceKey.ENGINE_KEY = Settings.get_engine_key()
        self.active_engine = BaseServices.get_service(engine_key)

        cache_path: str = Settings.get_cache_base(engine_key.with_prop(
                TTS_Type.CACHE_PATH))
        engine_code: str = Settings.get_cache_suffix(engine_key.with_prop(
                SettingProp.CACHE_SUFFIX))
        assert engine_code is not None, \
            f'Can not find voice-cache dir for engine: {engine_key}'
        self.cache_directory: str = xbmcvfs.translatePath(f'{cache_path}/{engine_code}/'
                                                          f'{changed_cache_dir}')

        self.cache_directory: Path = Path(self.cache_directory)
        self.work_list = FindTextToVoice(top=self.cache_directory)
        # self.thread: threading.Thread = None
        self.stop: bool = False
        self.seconds_delay = clz._default_delay
        self.delay = Delay(bias=self.seconds_delay, call_scale_factor=0.0,
                           scale_factor=0.0)
        self.start()

    def start(self):
        self.stop = False
        runInThread(self.create_voice_files, name='crtVcFil',
                    delay=0.0)

    def stop(self):
        self.stop = True

    def create_voice_files(self):
        try:
            while not self.stop:
                self.voice_next()
        except StopIteration:
            pass
        VoiceCache.register_cache_change_listener(self.cache_change_listener)

    def voice_next(self) -> None:
        if self.stop:
            raise StopIteration()

        clz = type(self)
        finished: bool = False
        voiced_file: Path | None = None
        while not finished:
            self.delay.delay()
            text_file: Path = self.work_list.get_next()
            if text_file is None:
                continue
            clz._logger.debug(f'Got cache text file: {text_file} without .mp3')

            text: str
            try:
                with text_file.open('rt', encoding='utf-8') as f:
                    text = f.read()
            except Exception as e:
                clz._logger.exception('')

            try:
                phrase: Phrase = Phrase(text, check_expired=False)
                result: CacheEntryInfo
                result = VoiceCache.get_path_to_voice_file(phrase, use_cache=True)
                if not phrase.text_exists(self.active_engine):
                    self.generate_voice(phrase)
            except Exception as e:
                clz._logger.exception('')
        return

    def generate_voice(self, phrase: Phrase) -> Path:
        clz = type(self)
        Monitor.exception_on_abort(timeout=0.5)
        self.engine: SimpleTTSBackend
        success: bool = self.active_engine.runCommand(phrase)
        if success:
            clz._logger.debug(f'generated voice file for {phrase.get_text()}')
            return phrase.get_cache_path()
        return None
