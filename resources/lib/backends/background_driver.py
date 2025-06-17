# coding=utf-8

"""
 Some speech engines may produce high quality voices, but at an unacceptably slow
 rate. This driver converts text to speech in the background and pupulates the
 cache.
"""
from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path

import xbmcvfs

from backends.settings.service_types import ServiceID, ServiceKey, TTS_Type
from backends.settings.setting_properties import SettingProp
from cache.cache_file_state import CacheFileState
from common import *

from backends.base import SimpleTTSBackend
from cache.voicecache import VoiceCache
from common.base_services import BaseServices
from common.constants import Constants
from common.file_utils import Delay, FindTextToVoice
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase
from common.setting_constants import Backends
from common.settings import Settings
from utils.util import runInThread

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class BackgroundDriver(BaseServices):

    #  Find .txt files which don't have corresponding .mp3 files in the cache
    #  Proceed to generate sound files for each

    _active_engine_key: ServiceID | None = None
    _active_engine: SimpleTTSBackend | None = None
    _cache_path: Path = None
    _default_delay: float = Constants.SEED_CACHE_DELAY_START_SECONDS
    _delay: Delay = None
    _finished: bool = False
    _first_call: bool = True
    max_active_dirs: int
    max_active_dirs = Constants.SEED_CACHE_DIR_LIMIT
    _modified_directories: queue.Queue = queue.Queue(maxsize=max_active_dirs)
    _seconds_delay: float = _default_delay
    _stop: bool = False
    _unvoiced_phrases: List[str] = []
    _work_list: FindTextToVoice | None = None

    @classmethod
    def class_init(cls):
        if not Constants.SEED_CACHE_WITH_EXPIRED_PHRASES:
            return
        # Ignore incoming notifications when queue is full.
        VoiceCache.register_cache_change_listener(cls.cache_change_listener)
        VoiceCache.send_change_cache_dir()
        runInThread(func=cls.generate_missing_voice_files, name='seed_proc')

    @classmethod
    def cache_change_listener(cls, changed_cache_path: str) -> None:
        """
         Called when a missing voice file is referenced from the cache.
         Our job is to generate every missing voice file from the given directory

         cache files are organized:
          <cache_path>/<engine_code>/<first-two-chars-of-cache-file-name
          >/<cache_file_name>.<suffix>

          Example: cache_path =  ~/.kodi/userdata/addon_data/service.kodi.tts/cache
                   engine_code = goo (for google)
                   lang_code = 'en'
                   country_code = 'us'
                   voice_code = 'Vira' (for Windows TTS), '_' (when no voice)
                   first-two-chars-of-cache-file-name = d4
                   hash of text  = cache_file_name = d4562ab3243c84746a670e47dbdc61a2
                   suffix = .mp3 or .txt

        :param changed_cache_path:  full path to the directory containing .txt and
                                    voiced files
        :return: None when finished
        """
        try:
            if not Constants.SEED_CACHE_WITH_EXPIRED_PHRASES:
                return
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'changed_cache_path: {changed_cache_path}')
            engine_key: ServiceID = Settings.get_engine_key()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'engine_key: {engine_key}')
            if cls._first_call:
                cls._active_engine_key = engine_key
                cls._active_engine = BaseServices.get_service(engine_key)
                cls._first_call = False
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'active_engine: {cls._active_engine_key}')
            if cls._active_engine_key is not None and engine_key != cls._active_engine_key:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'New engine: {engine_key}, purging queue')
                finished: bool = False
                while not finished:
                    try:
                        cls._modified_directories.get_nowait()
                        cls._active_engine_key = None
                    except queue.Empty:
                        finished = True

            cls._active_engine_key = engine_key
            cls._active_engine = BaseServices.get_service(engine_key)
            if not Settings.is_use_cache(engine_key):
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'not using cache, exiting')
                return
            # cache_path: str = Settings.get_cache_base(engine_key.with_prop(
            #         TTS_Type.CACHE_PATH))
            engine_code: str = Backends.ENGINE_CACHE_CODE[engine_key.service_id]
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'engine_code: {engine_code}')
            #  assert engine_code is not None, \
            #      f'Can not find voice-cache dir for engine: {engine_key}'
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Adding {changed_cache_path} to modified_directories')
            cls._modified_directories.put(item=changed_cache_path)
        except:
            MY_LOGGER.exception('')

    @classmethod
    def generate_missing_voice_files(cls) -> None:
        """
        Helps to populate the cache with voice files by searching directories
        with recently added unvoiced .txt files. This runs in a separate thread.
        :return:
        """
        try:
            while not cls._finished:
                try:
                    cache_path: str = cls._modified_directories.get_nowait()
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'process_directory of {cache_path}')
                    cls.process_directory(cache_path)
                except queue.Empty:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'queue empty. Requesting changes')
                    VoiceCache.send_change_cache_dir()
                    delay: float = Constants.SEED_CACHE_DIRECTORY_DELAY_SECONDS
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Waiting {delay / 60.0}'
                                        f' minutes to check for more changes')
                    Monitor.exception_on_abort(delay)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')

    @classmethod
    def process_directory(cls, cache_path: str) -> None:
        cache_path: Path = Path(cache_path)
        engine_key: ServiceID = Settings.get_engine_key()
        cls._active_engine = BaseServices.get_service(engine_key)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'cache_path: {cache_path} engine: {engine_key} '
                            f'active_engine: {cls._active_engine}')
        if not Settings.is_use_cache(engine_key):
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Not using cache, exiting')
            return
        engine_code: str = Settings.get_cache_suffix(engine_key.with_prop(
                SettingProp.CACHE_SUFFIX))
        assert engine_code is not None, \
            f'Can not find voice-cache dir for engine: {engine_key}'

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Searching for text files to convert to voice')
        cls._work_list = FindTextToVoice(top=cache_path)
        # self.thread: threading.Thread = None
        cls._seconds_delay = cls._default_delay
        cls._delay = Delay(bias=cls._seconds_delay, call_scale_factor=0.0,
                           scale_factor=0.0)
        cls.start()

    @classmethod
    def start(cls):
        cls._stop = False
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'starting thread for create_voice_files')
        runInThread(cls.create_voice_files, name='crtVcFil', delay=0.0)

    @classmethod
    def stop(cls):
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v('STOP')
        cls._stop = True

    @classmethod
    def create_voice_files(cls):
        try:
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v('In create_voice_files')
            while not cls._stop:
                cls.voice_next()
        except StopIteration:
            pass

    @classmethod
    def voice_next(cls) -> None:
        if cls._stop:
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'Stopping')
            raise StopIteration()

        finished: bool = False
        voiced_file: Path | None = None
        while not finished:
            cls._delay.delay()
            text_file: Path = cls._work_list.get_next()
            MY_LOGGER.debug(f'text_file: {text_file}')
            if text_file is None:
                continue
            MY_LOGGER.debug(f'Got cache text file: {text_file} without .mp3')
            text: str
            try:
                with text_file.open('rt', encoding='utf-8') as f:
                    text = f.read()
            except Exception as e:
                MY_LOGGER.exception('')
            try:
                phrase: Phrase = Phrase(text, check_expired=False)
                MY_LOGGER.debug(f'{phrase.text}')
                #  voice_cache: VoiceCache = cls._active_engine.get_voice_cache()
                #  result: CacheEntryInfo
                #  result = voice_cache.get_path_to_voice_file(phrase, use_cache=True)
                #  if not result.audio_exists():
                cls.generate_voice(phrase)
            except Exception as e:
                MY_LOGGER.exception('')
        return

    @classmethod
    def generate_voice(cls, phrase: Phrase) -> Path | None:
        try:
            Monitor.exception_on_abort(timeout=0.5)
            success: CacheFileState = cls._active_engine.get_cached_voice_file(phrase)
            if success:
                MY_LOGGER.debug(f'generated voice file for {phrase.get_text()}')
                return phrase.get_cache_path()
            return None
        except Exception:
            MY_LOGGER.exception('')


BackgroundDriver.class_init()
