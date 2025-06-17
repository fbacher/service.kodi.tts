# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import datetime
import hashlib
import io
import os
import pathlib
import sys
import tempfile
import threading
import time
from collections import namedtuple
from enum import Enum
from pathlib import Path

import xbmcvfs

from backends.settings.service_types import (MyType, ServiceID, ServiceKey, ServiceType,
                                             TTS_Type)
from cache.common_types import CacheEntryInfo
from common import *
from common.constants import Constants
from common.exceptions import ExpiredException
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import AudioType, Backends
from common.settings import Settings
from common.settings_low_level import SettingProp
from common.utils import TempFileUtils
from utils.util import runInThread

MY_LOGGER = BasicLogger.get_logger(__name__)



class VoiceCache:
    """

    """
    ignore_cache_count: int = 0
    # Key is full path to directory containing .txt files to generate .voice files
    referenced_cache_dirs: Dict[str, None] = {}  # Acts as a set
    cache_change_listener: Callable = None
    tmp_dir: Path | None = None
    # Provide for a simple means to purge old, un-cached audio files.
    # Have two temp directories for temp audio files. Rotate use every two
    # minutes. As the rotation occurs, erase the contents directory that is being
    # rotated to just before use.
    rotating_tmp_subdirs: List[str] = ['a', 'b']
    current_tmp_subdir: int = 0

    @classmethod
    def init_thread(cls):
        runInThread(cls.rotate_tmp_dir_thrd, args=[], name='cln_tmp_dir')

    def __init__(self, service_key: ServiceID, reset_engine_each_call=False):
        """
        Creates a VoiceCache instance meant to be used by a particular TTS engine.
        """
        clz = type(self)
        self.reset_engine_each_call: bool = reset_engine_each_call
        self.service_key: ServiceID = service_key
        self._top_of_engine_cache: Path | None = None
        self._audio_type: AudioType | None = None
        self.reset_engine()

    def reset_engine(self) -> None:
        cache_directory: Path | None = None
        try:
            # CACHE_PATH is in app_data/cache UNLESS the special, predefined
            # minimal "backup cache" is being used. This minimal cache is
            # used when there are NO usable engines available or no players
            # compatible with any usable engines. The backup cache contains
            # enough messages to guide the user out of this mess. The
            # backup cache is used when 'no_engine' and SFX player are used.

            #  engine_key: ServiceKey.ENGINE_KEY = Settings.get_engine_key()
            #  cache_path: str = Settings.get_cache_base(engine_key.with_prop(
            #          TTS_Type.CACHE_PATH))

            #  engine_code: str = Settings.get_cache_suffix(engine_key.with_prop(
            #          SettingProp.CACHE_SUFFIX))
            service_type: ServiceType = self.service_key.service_type
            if service_type == ServiceType.PLAYER:
                self._audio_type = Settings.get_current_input_format(self.service_key)
            elif service_type == ServiceType.ENGINE:
                self._audio_type = Settings.get_current_output_format(self.service_key)

            cache_base: str = Settings.get_cache_base(self.service_key.with_prop(
                    SettingProp.CACHE_PATH))
            suffix: str = Settings.get_cache_suffix(self.service_key.with_prop(
                                                               Constants.CACHE_SUFFIX))
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'cache_base: {cache_base} suffix: {suffix}'
                                  f' audio_type: {self._audio_type} service_key: '
                                  f'{self.service_key}')
            cache_directory = Path(cache_base) / suffix
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        self._top_of_engine_cache = Path(cache_directory)
        return

    @classmethod
    def rotate_tmp_dir_thrd(cls):
        cls.current_tmp_subdir = 0
        temp_root: Path = TempFileUtils.temp_dir()
        tmp_dir: Path
        while not Monitor.real_waitForAbort(Constants.ROTATE_TEMP_VOICE_DIR_SECONDS):
            if cls.current_tmp_subdir == 0:
                cls.current_tmp_subdir = 1
            else:
                cls.current_tmp_subdir = 0
            # Clean previously used subdir
            tmp_dir = temp_root / cls.rotating_tmp_subdirs[cls.current_tmp_subdir-1]
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'tmp_dir: {tmp_dir} current_tmp_subdir: '
                                  f'{cls.current_tmp_subdir - 1}')
            TempFileUtils.clean_tmp_dir(tmp_dir)

    @classmethod
    def is_tmp_file(cls, file_path: Path) -> bool:
        """
        Determines if the given file_path is a temp file

        :param file_path: P
        :return:
        """
        temp_root: Path = TempFileUtils.temp_dir()
        return str(file_path).startswith(str(temp_root))

    @property
    def cache_directory(self) -> Path:
        """
        Constructs an appropriate cache path for the given engine. The basic
        pattern is <top_of_cache>/<engine_subdir> where engine_subdir is defined in
        <engine>_settings as one of the service_properties. Example: Google_TTS
        has a subdir of 'goo'.

        Later, directories for the primary language and voice will be added.

        The constructed path is placed in the given phrase

        :return:
        """
        # Most VoiceCache instances belong to the engine in use. However, some
        # instances, like for a player, can persist through engine changes.

        if self.reset_engine_each_call:
            self.reset_engine()
        return self._top_of_engine_cache

    @property
    def audio_type(self) -> AudioType:
        if self.service_key.service_type == ServiceType.PLAYER:
            self._audio_type = Settings.get_current_input_format(self.service_key)
        elif self.service_key.service_type  == ServiceType.ENGINE:
            self._audio_type = Settings.get_current_output_format(self.service_key)
        return self._audio_type

    @property
    def audio_suffix(self) -> str:
        return f'.{self.audio_type}'

    def get_path_to_voice_file(self, phrase: Phrase,
                               use_cache: bool = False) -> CacheEntryInfo:
        """
        Determines where audio and related information for the given phrase is, or
        should be stored. If use_cache is True, then audio and a copy of the
        text that the audio is created from is stored in the cache using the
        MD5 hash of the text. If use_cache is False, temp file paths are created
        which are frequently garbage collected.

        Two audio paths are returned: the temp_voice_path, which is for storing
        audio as it is being created. On successful creation of the audio, it is
        renamed to the final_audio_path. This is particularly useful when the
        audio-engine has limits on the input text so that the audio is converted
        in chunks. The extra temp file makes it a bit easier to handle failures.

        Note: All files related to a phrase differ only in their file suffix.
        Note: the engine, player or transcoder that created this VoiceCache instance
        sets the audio file type which is created or consumed by that service.

        @param phrase: Contains the text and related information for the conversion
        @param use_cache: True a path in the cache is to be returned, otherwise
                        a path to a temp-file will be created

        @return: namedtuple('CacheEntryInfo',
                            'final_audio_path,'
                            'temp_voice_path,'
                            'use_cache,'
                            'audio_exists',
                            'text_exists, audio_suffixes')
        final_audio_path is the final path for the voiced phrase. Depending
           use_cache, the path will either be in the cache or in a temp
           directory.
        temp_voice_path is a temporay path used just during generation of the audio.
           It is either discarded on error, or immediately renamed to final_audio_path
           on successful generation.
        use_cache indicates if the audio file is (or is to be) stored in the
            cache, or a temp directory. Files in a temp directory are deleted once
            played.
        audio_exits is True if the final_audio_path file is not empty. temp_voice_path
           is set to None when True
        text_exists is a boolean that is True if use_cache is true and the .txt
           file exists. (The .txt file is only used when cache is True).
        audio_suffixes is None when use_cache is False. It is a list of the
           suffixes of audio and text files for this phrase. Normally only one
            audio file exists, but in some cases .wav and .mpg both exists.
        """
        try:
            if not use_cache or not self.is_cache_sound_files(self.service_key):
                return self._get_path_to_tmp_voice_file(phrase)
            else:
                return self._get_path_to_cached_voice_file(phrase)
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            reraise(*sys.exc_info())

        except Exception as e:
            MY_LOGGER.exception('')

    def _get_path_to_tmp_voice_file(self, phrase: Phrase) -> CacheEntryInfo:
        """
        See get_path_to_voice_file

        :param phrase:
        :return:
        """
        clz = type(self)
        final_audio_path: Path | None = None
        temp_voice_path: Path | None = None
        try:
            phrase.set_audio_type(self.audio_type)

            filename: str = self.get_hash(phrase.text)
            temp_root: Path = TempFileUtils.temp_dir()
            tmp_dir = temp_root / clz.rotating_tmp_subdirs[clz.current_tmp_subdir]
            tmp_dir.mkdir(mode=0o777, parents=True, exist_ok=True)
            final_audio_path: Path
            final_audio_path = tmp_dir / Path(filename).with_suffix(self.audio_suffix)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'final_audio_path: {final_audio_path}')
            if final_audio_path.exists():
                try:
                    # Note that Windows won't let you unlink a file in use
                    # by another process
                    final_audio_path.unlink(missing_ok=True)
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'unlink {final_audio_path}')
                except:
                    MY_LOGGER.exception(f'Could not delete {final_audio_path}')
            rc, temp_voice_path, _ = self.create_tmp_sound_file(final_audio_path,
                                                                delete_if_exists=True)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'final_audio_path: {final_audio_path} audio_suffix: '
                                f'{self.audio_suffix} temp_file: {temp_voice_path}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        audio_suffixes: List[str] = []
        result: CacheEntryInfo
        result = CacheEntryInfo(final_audio_path=final_audio_path,
                                use_cache=False,
                                temp_voice_path=temp_voice_path,
                                audio_exists=False,
                                text_exists=False,
                                audio_suffixes=audio_suffixes)
        if final_audio_path is not None:
            phrase.set_cache_path(cache_path=final_audio_path,
                                  text_exists=False,
                                  temp=not result.use_cache)
        #  MY_LOGGER.debug(f'result: {result}')
        return result

    def _get_path_to_cached_voice_file(self, phrase: Phrase,
                                       use_cache: bool = False) -> CacheEntryInfo:
        """
        See get_path_to_voice_file

        :param phrase:
        :param use_cache:
        :return:
        """
        exists: bool = False
        audio_exists: bool = False
        text_exists: bool = False
        audio_suffixes: List[str] = []
        cache_dir: Path | None = None
        final_audio_path: Path | None = None
        temp_voice_path: Path | None = None
        try:
            path: Path | None = None
            cache_top: Path = self.cache_directory
            lang_dir: str = phrase.lang_dir
            territory_dir: str = phrase.territory_dir
            voice_dir: str = phrase.voice
            filename: str = self.get_hash(phrase.text)
            subdir: str = filename[0:2]
            cache_dir: str
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'territory: {territory_dir} '
                                  f'cache_top: {cache_top} '
                                  f'lang_dir: {lang_dir} '
                                  f'voice_dir: {voice_dir} '
                                  f'subdir: {subdir}')
            # TODO: Fix HACK
            # HACK for when a phrase comes in when locale fields are not set up.
            # Seems to occur when caching has just been turned on.
            if lang_dir is None or lang_dir == '':
                lang_dir = 'missing_lang'
            if territory_dir is None or territory_dir == '':
                territory_dir = 'missing_territory'
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'cache_top: {cache_top} '
                                f'lang_dir: {lang_dir} '
                                f'territory_dir: {territory_dir} '
                                f'voice_dir: {voice_dir} '
                                f'subdir: {subdir}')
            cache_dir = cache_top / lang_dir / territory_dir / voice_dir / subdir
            cache_path = cache_dir / filename
            final_audio_path = cache_path.with_suffix(self.audio_suffix)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'final_audio_path: {final_audio_path}')
            audio_exists = final_audio_path.exists()
            if audio_exists:
                if final_audio_path.stat().st_size < 1000:
                    audio_exists = False
                    try:
                        final_audio_path.unlink(missing_ok=True)
                    except Exception:
                        MY_LOGGER.exception('')
            phrase.set_audio_type(self.audio_type)
            if not cache_dir.exists():
                try:
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'mkdir: {cache_dir}')
                    cache_dir.mkdir(mode=0o777, exist_ok=True, parents=True)
                except Exception:
                    MY_LOGGER.error(f'Can not create directory: {cache_dir}')
                    return CacheEntryInfo(final_audio_path=None,
                                          use_cache=use_cache,
                                          temp_voice_path=None,
                                          audio_exists=False,
                                          text_exists=None,
                                          audio_suffixes=audio_suffixes)
            #  MY_LOGGER.debug(f'cache_dir: {cache_dir}')
            for file in cache_dir.glob(f'{filename}.*'):
                file: Path
                if file.is_dir():
                    msg = (f'Ignoring cached voice file: {file}. It is'
                           f' a directory.')
                    MY_LOGGER.showNotification(msg)
                    continue
                if not os.access(file, os.R_OK):
                    msg = (f'Ignoring cached voice file: {file}. No read'
                           f' access.')
                    MY_LOGGER.showNotification(msg)
                    continue

                suffix: str = file.suffix
                if suffix == '.txt':
                    if file.stat().st_size > 0:
                        text_exists = True
                    else:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Text file empty: {file}')
                else:
                    audio_suffixes.append(suffix)
                    if suffix == self.audio_suffix:
                        audio_exists = file.exists()
                        audio_good: bool
                        if audio_exists:
                            audio_good = file.stat().st_size > 1000
                            if not audio_good:
                                try:
                                    file.unlink(missing_ok=True)
                                    audio_exists = False
                                except PermissionError:
                                    if MY_LOGGER.isEnabledFor(DEBUG):
                                        MY_LOGGER.debug(f'Can not delete {file} '
                                                        f'due to permissions')
                                except:
                                    MY_LOGGER.exception('Error deleting: '
                                                        f'{file}')
            if not audio_exists:
                rc, temp_voice_path, _ = self.create_tmp_sound_file(
                        final_audio_path, delete_if_exists=True)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

        result: CacheEntryInfo
        result = CacheEntryInfo(final_audio_path=final_audio_path,
                                use_cache=use_cache,
                                temp_voice_path=temp_voice_path,
                                audio_exists=audio_exists,
                                text_exists=text_exists,
                                audio_suffixes=audio_suffixes)
        if final_audio_path is not None:
            phrase.set_cache_path(cache_path=final_audio_path,
                                  text_exists=text_exists,
                                  temp=not result.use_cache)
        #  MY_LOGGER.debug(f'result: {result}')
        return result

    @classmethod
    def create_tmp_sound_file(cls, voice_file_path: Path,
                              create_dir_only: bool = False,
                              delete_if_exists: bool = True) \
            -> Tuple[int, Path, BinaryIO | None]:
        """
        Create a tmp file based on voice_file_path and return file
        handle to it. Once the contents are successfully generated
        elsewhere, the tmp file can be renamed to the correct name,
        or the contents can be discarded.

        :param voice_file_path: final path to the audio file to be
        geenrated.
        :param create_dir_only: When True, only create the directory
        for the voice_file_path
        :param delete_if_exists: When True, delete any pre-existing tmp-sound file
        :return: Tuple[return_code:int, tmp_path: str, file_handle: BinaryIO]
        """

        rc: int = 0
        cache_file: BinaryIO | None = None
        tmp_name: str = (f'{voice_file_path.stem}{Constants.TEMP_AUDIO_NAME_SUFFIX}'
                         f'{voice_file_path.suffix}')
        tmp_path: Path = voice_file_path.parent / tmp_name
        #  MY_LOGGER.debug(f'voice_file_path: {voice_file_path} tmp_path: {tmp_path}')
        try:
            if not tmp_path.parent.is_dir():
                try:
                    tmp_path.parent.mkdir(mode=0o777, parents=True, exist_ok=True)
                except:
                    MY_LOGGER.error(f'Can not create directory: {tmp_path.parent}')
                    rc = 1
                    return rc, tmp_path, None

            if delete_if_exists and tmp_path.exists():
                try:
                    tmp_path.unlink(missing_ok=True)
                except:
                    MY_LOGGER.exception(f'Can not delete tmp_path: {tmp_path}')
            if create_dir_only:
                return rc, tmp_path, None

            '''
            try:
                cache_file = tmp_path.open(mode='wb')
            except Exception as e:
                rc = 2
                MY_LOGGER.error(f'Can not create cache file: {voice_file_path}')
            '''
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        #  MY_LOGGER.debug(f'{rc} {tmp_path}')
        return rc, tmp_path, cache_file

    @classmethod
    def tmp_file(cls, file_type: str) -> tempfile.NamedTemporaryFile:
        """
        Create a temp file for audio. Used when audio is NOT cached
        """
        temp_root: Path = TempFileUtils.temp_dir()
        tmp_dir = temp_root / cls.rotating_tmp_subdirs[cls.current_tmp_subdir]
        tmp_dir.mkdir(mode=0o777, parents=True, exist_ok=True)
        tmp_file = tempfile.mkstemp(suffix=file_type, prefix=None, dir=tmp_dir)
        #  MY_LOGGER.debug(f'Created tempfile {tmp_file}')
        return tmp_file

    @classmethod
    def for_debug_setting_changed(cls):
        #
        # For debugging. Reduces load on remote service while experimenting.
        # Remove on shipping product.
        #
        # Causes cache to be ignored for five voicings after any backend setting
        # has changed

        cls.ignore_cache_count = 0

    @classmethod
    def is_cache_sound_files(cls, service_key: ServiceID) -> bool:
        """
        Indicates whether caching is enabled
        :param service_key: check if voiced text from this engine/player is cached
        :return: true if caching is enabled, otherwise false.
        """
        use_cache: bool = False
        try:
            if Settings.configuring_settings() and cls.ignore_cache_count < 3:
                cls.ignore_cache_count += 1
                return False

            use_cache = Settings.is_use_cache(service_key)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return use_cache

    @classmethod
    def get_hash(cls, text_to_voice: str) -> str:
        hash_value: str = hashlib.md5(
                text_to_voice.encode('UTF-8')).hexdigest()
        return hash_value

    def clean_cache(self, purge: bool = False) -> None:
        clz = type(self)
        return
    '''
        try:
            dummy_cached_file: str = self.get_path_to_voice_file('', '')
            cache_directory, _ = os.path.split(dummy_cached_file)
            expiration_time = time.time() - \
                              Settings.getSetting(
                                      SettingProp.CACHE_EXPIRATION_DAYS,
                                      SettingProp.TTS_SERVICE, 30) * 86400
            for root, dirs, files in os.walk(cache_directory, topdown=False):
                for file in files:
                    try:
                        path = os.path.join(root, file)
                        if purge or os.stat(path).st_mtime < expiration_time:
                            MY_LOGGER.debug_v('Deleting: {}'.format(path))
                            os.remove(path)
                    except Exception as e:
                        pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
    '''

    def seed_text_cache(self, phrases: PhraseList) -> None:
        """
         For engines that are expensive, it can be beneficial to cache the voice
         files. In addition, by saving text to the cache that is not yet
         voiced, then a background process can generate speech so the cache
         gets built more quickly

         :param phrases: phrases to have voiced in background
        """
        clz = type(self)
        if not Settings.is_use_cache():
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'is_use_cache False')
            return None

        try:
            phrases = phrases.clone(check_expired=False)
            engine_key: ServiceID | None = None
            if self.service_key.service_type == ServiceType.ENGINE:
                engine_key = self.service_key
            for phrase in phrases:
                phrase: Phrase
                phrase.set_engine(engine_key)
                self.create_txt_cache_file(phrase)
        except Exception as e:
            MY_LOGGER.exception('')

    def create_txt_cache_file(self, phrase: Phrase) -> bool:
        """
        Adds the text contained in the phrase if it is not already in
        the cache.
        :param phrase: Phrase containing text
        :return: True if the text is added to the cache, otherwise, False
        """
        if not Settings.is_use_cache():
            return False

        text: str = phrase.get_text()
        result: CacheEntryInfo
        result = self.get_path_to_voice_file(phrase, use_cache=True)
        voice_file_path: Path = result.final_audio_path
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'voice_file_path: {voice_file_path}')
        rc: int = 0
        try:
            text_file: Path | None
            text_file = voice_file_path.with_suffix('.txt')
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'text_file path: {text_file}')
            try:
                if not text_file.is_file():
                    with text_file.open('wt', encoding='utf-8') as f:
                        f.write(text)
                else:
                    if text_file.stat().st_size < len(phrase.text):
                        text_file.unlink(missing_ok=True)
                if not text_file.is_file():
                    with text_file.open('wt', encoding='utf-8') as f:
                        f.write(text)
            except Exception as e:
                if MY_LOGGER.isEnabledFor(ERROR):
                    MY_LOGGER.error(
                            f'Failed to save text file: '
                            f'{text_file} Exception: {str(e)}')
        except Exception as e:
            if MY_LOGGER.isEnabledFor(ERROR):
                MY_LOGGER.error(
                        f'Failed to save text: {str(e)}')
            return False
        return True

    def text_referenced(self, phrase: Phrase) -> None:
        """
         cache files are organized:
          <cache_path>/<engine_code>/<lang/<voice>/<first-two-chars-of-cache-file-name
          >/<cache_file_name>.<suffix>

          Example: cache_path =  ~/.kodi/userdata/addon_data/service.kodi.tts/cache
                   engine_code = goo (for google)
                   lang = 'en'
                   voice='en-us'  # For gtts
                   first-two-chars-of-cache-file-name = d4
                   hash of text  = cache_file_name = d4562ab3243c84746a670e47dbdc61a2
                   suffix = .mp3 or .txt
        """
        clz = type(self)
        try:
            engine_code: str = Settings.get_cache_suffix(self.service_key.with_prop(
                    Constants.CACHE_SUFFIX))

            #  engine_code: str = Backends.ENGINE_CACHE_CODE[self.service_key.service_id]
            assert engine_code is not None, \
                f'Can not find voice-cache dir for: {self.service_key}'

            cache_file_path: Path = phrase.get_cache_path()
            cache_dir: str = str(cache_file_path.parent)
            eng_code: str
            eng_code = str(cache_file_path.parent.parent.parent.parent.parent.name)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'cache_file_path: {cache_file_path} eng_code: '
                                f'{eng_code} cache_dir: {cache_dir}')
            if engine_code == eng_code:
                clz.referenced_cache_dirs[cache_dir] = None
            else:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'engine_code: {engine_code} eng_code: {eng_code}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return

    @classmethod
    def register_cache_change_listener(cls,
                                       cache_change_listener: Callable[[str],
                                                                       None]) -> None:
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'listener: {cache_change_listener}')
        cls.cache_change_listener = cache_change_listener

    @classmethod
    def send_change_cache_dir(cls) -> bool:
        """
        Background cache_change_listener requesting a cache directory to examine
        for phrase text that may have not been voiced. This may occur when user
        moves the cursor prior to enough time to generate and play the voice.

        :return: True if the change_listener called, else False
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'in send_change_cache_dir')
        if cls.cache_change_listener is None:
            return False
        try:
            path: str | None = None
            # popitem is LIFO, but not a big concern
            path, _ = cls.referenced_cache_dirs.popitem()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'referenced_cache_dirs: {path}')
            cls.cache_change_listener(path)
            return True
        except KeyError:
            pass
        except Exception:
            MY_LOGGER.exception('')
        return False


VoiceCache.init_thread()
