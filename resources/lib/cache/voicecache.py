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

from backends.settings.i_validators import IStringValidator
from backends.settings.service_types import ServiceID, ServiceKey, ServiceType, TTS_Type
from backends.settings.validators import StringValidator
from cache.common_types import CacheEntryInfo
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.i_tts_backend_base import ITTSBackendBase
from backends.players.iplayer import IPlayer
from backends.players.player_index import PlayerIndex
from backends.settings.settings_map import SettingsMap
from common import utils
from common.base_services import BaseServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import AudioType, Backends, Players
from common.settings import Settings
from common.settings_low_level import SettingProp
from common.utils import TempFileUtils
from utils.util import runInThread

MY_LOGGER = BasicLogger.get_logger(__name__)


class VoiceCache:
    """

    """
    ignore_cache_count: int = 0
    # Does not have full path, just directory name
    referenced_cache_dirs: Dict[str, str] = {}  # Acts as a set with value == key
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
        MY_LOGGER.debug(f'service_key: {service_key}')
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
            #  MY_LOGGER.debug(f'cache_path: {cache_path} service_key: {self.service_key}')
            service_type: ServiceType = self.service_key.service_type
            if service_type == ServiceType.PLAYER:
                self._audio_type = Settings.get_current_input_format(self.service_key)
            elif service_type == ServiceType.ENGINE:
                self._audio_type = Settings.get_current_output_format(self.service_key)

            cache_base: str = Settings.get_cache_base(self.service_key.with_prop(
                    SettingProp.CACHE_PATH))
            suffix: str = Settings.get_cache_suffix(self.service_key.with_prop(
                                                               Constants.CACHE_SUFFIX))
            MY_LOGGER.debug(f'cache_base: {cache_base} suffix: {suffix}')
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
        while not Monitor.real_waitForAbort(120.0):
            if cls.current_tmp_subdir == 0:
                cls.current_tmp_subdir = 1
            else:
                cls.current_tmp_subdir = 0
            # Clean previously used subdir
            tmp_dir = temp_root / cls.rotating_tmp_subdirs[cls.current_tmp_subdir-1]
            TempFileUtils.clean_tmp_dir(tmp_dir)

    @classmethod
    def is_tmp_file(cls, file_path: Path) -> bool:
        """
        Determines if the given file_path is a temp file

        :param file_path:
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
        # instances, like for a [player_key, can persist through engine changes.

        if self.reset_engine_each_call:
            self.reset_engine()
        return self._top_of_engine_cache

    @property
    def audio_type(self) -> AudioType:
        return self._audio_type

    @property
    def audio_suffix(self) -> str:
        return f'.{self.audio_type}'

    def get_path_to_voice_file(self, phrase: Phrase,
                               use_cache: bool = False) -> CacheEntryInfo:
        """
        If results of the speech engine are cached, then this function
        returns the path of the audio file for the phrase and other relevant
        information.

        When caching is not used, then the temporary file path for the
        engine output is returned,

        Note: All files related to a phrase differ only in their file suffix.
        Note: the engine, player_key or transcoder that created this VoiceCache instance
        sets the audio file type which is created or consumed by that service.

        @param phrase:
        @param use_cache: True a path in the cache is to be returned, otherwise
                        a path to a temp-file will be created

        @return: namedtuple('CacheEntryInfo',
                            'current_audio_path,'
                            'temp_voice_path,'
                            'use_cache,'
                            'audio_exists',
                            'text_exists, audio_suffixes')
        current_audio_path is the path to the voiced phrase. Depending upon use_cache,
           the path will either be in the cache or in a temp directory. (The file
            may not yet exist).
        temp_voice_path is a temporay path used just during generation of the audio.
           It is either discarded on error, or immediately renamed to current_audio_path
           on successful generation.
        use_cache indicates if the audio file is (or is to be) stored in the
            cache, or a temp directory. Files in a temp directory are deleted once
            played.
        audio_exits is True if the current_audio_path file is not empty. temp_voice_path
           is set to None when True
        text_exists is a boolean that is True if use_cache is true and the .txt
           file exists.
        audio_suffixes is None when use_cache is False. It is a list of the
           suffixes of audio and text files for this phrase. Normally only one
            audio file exists, but in some cases .wav and .mpg both exists.
        """
        exists: bool = False
        audio_exists: bool = False
        text_exists: bool = False
        audio_suffixes: List[str] = []
        cache_dir: Path | None = None
        current_audio_path: Path | None = None
        temp_voice_path: Path | None = None
        try:
            if not use_cache or not self.is_cache_sound_files(self.service_key):
                phrase.set_audio_type(self.audio_type)
                current_audio_path = Path(self.tmp_file(f'{self.audio_suffix}').name)
                rc, temp_voice_path, _ = self.create_tmp_sound_file(current_audio_path)
                MY_LOGGER.debug(f'current_audio_path: {current_audio_path} audio_suffix: '
                                f'{self.audio_suffix} temp_file: {temp_voice_path}')
            else:
                try:
                    path: Path | None = None
                    cache_top: Path = self.cache_directory
                    lang_dir: str = phrase.lang_dir
                    territory_dir: str = phrase.territory_dir
                    filename: str = self.get_hash(phrase.text)
                    subdir: str = filename[0:2]
                    cache_dir: str
                    if territory_dir is None or territory_dir == '':
                        cache_dir = cache_top / lang_dir / subdir
                    else:
                        cache_dir = cache_top / lang_dir / territory_dir / subdir
                    cache_path = cache_dir / filename
                    current_audio_path = cache_path.with_suffix(self.audio_suffix)
                    phrase.set_audio_type(self.audio_type)
                    if not cache_dir.exists():
                        try:
                            cache_dir.mkdir(mode=0o777, exist_ok=True, parents=True)
                        except:
                            MY_LOGGER.error(f'Can not create directory: {cache_dir}')
                            return CacheEntryInfo(current_audio_path=None,
                                                  use_cache=use_cache,
                                                  temp_voice_path=None,
                                                  audio_exists=False,
                                                  text_exists=None,
                                                  audio_suffixes=audio_suffixes)
                    #  MY_LOGGER.debug(f'cache_dir: {cache_dir}')
                    audio_exists: bool = False
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
                            text_exists = True
                        else:
                            audio_suffixes.append(suffix)
                            if suffix == self.audio_suffix:
                                audio_exists = file.stat().st_size > 1000
                                if not audio_exists:
                                    try:
                                        file.unlink(missing_ok=True)
                                    except:
                                        MY_LOGGER.exception('Error deleting file')
                    if not audio_exists:
                        rc, temp_voice_path, _ = self.create_tmp_sound_file(
                                current_audio_path)
                        MY_LOGGER.debug(f'audio_exists: {audio_exists} '
                                        f'current_audio_path: {current_audio_path} '
                                        f'temp_voice_path: {temp_voice_path}')
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    MY_LOGGER.exception('')
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException as e:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

        result: CacheEntryInfo
        result = CacheEntryInfo(current_audio_path=current_audio_path,
                                use_cache=use_cache,
                                temp_voice_path=temp_voice_path,
                                audio_exists=audio_exists,
                                text_exists=text_exists,
                                audio_suffixes=audio_suffixes)
        if current_audio_path is not None:
            phrase.set_cache_path(cache_path=current_audio_path,
                                  text_exists=phrase.text_exists(),
                                  temp=not result.use_cache)
        #  MY_LOGGER.debug(f'result: {result}')
        return result

    @classmethod
    def tmp_file(cls, file_type: str) -> tempfile.NamedTemporaryFile:
        """
        Create a temp file for audio. Used when audio is NOT cached
        """
        temp_root: Path = TempFileUtils.temp_dir()
        tmp_dir = temp_root / cls.rotating_tmp_subdirs[cls.current_tmp_subdir]
        tmp_dir.mkdir(mode=0o777, parents=True, exist_ok=True)
        tmp_file = tempfile.NamedTemporaryFile(mode='w+b', buffering=-1,
                                               suffix=file_type,
                                               prefix=None,
                                               dir=tmp_dir,
                                               delete=False)
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

    @classmethod
    def create_tmp_sound_file(cls, voice_file_path: Path,
                              create_dir_only: bool = False) \
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
            :return: Tuple[return_code:int, tmp_path: str, file_handle: BinaryIO]
        """

        rc: int = 0
        cache_file: BinaryIO | None = None
        tmp_name: str = (f'{voice_file_path.stem}{Constants.TEMP_AUDIO_NAME_SUFFIX}'
                         f'{voice_file_path.suffix}')
        tmp_path: Path = voice_file_path.parent / tmp_name
        MY_LOGGER.debug(f'voice_file_path: {voice_file_path} tmp_path: {tmp_path}')
        try:
            if not tmp_path.parent.is_dir():
                try:
                    tmp_path.parent.mkdir(mode=0o777, parents=True, exist_ok=True)
                except:
                    MY_LOGGER.error(f'Can not create directory: {tmp_path.parent}')
                    rc = 1
                    return rc, tmp_path, None

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
        MY_LOGGER.debug(f'{rc} {tmp_path}')
        return rc, tmp_path, cache_file

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
        try:
            phrases = phrases.clone(check_expired=False)
            for phrase in phrases:
                phrase: Phrase
                if Settings.is_use_cache():
                    result: CacheEntryInfo
                    result = self.get_path_to_voice_file(phrase, use_cache=True)
                    if not result.text_exists:
                        text: str = phrase.get_text()
                        voice_file_path: Path = result.current_audio_path
                        MY_LOGGER.debug(f'PHRASE Text {text} path: {voice_file_path}')
                        rc: int = 0
                        try:
                            text_file: Path | None
                            text_file = voice_file_path.with_suffix('.txt')
                            try:
                                if text_file.is_file() and text_file.exists():
                                    MY_LOGGER.debug(f'UNLINKING {text_file}')
                                    text_file.unlink(missing_ok=True)

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
                                        'Failed to save text: {}'.format(str(e)))
        except Exception as e:
            MY_LOGGER.exception('')

        #  self.text_referenced(phrase)

    def text_referenced(self, phrase: Phrase) -> None:
        """
         cache files are organized:
          <cache_path>/<engine_code>/<lang/<voice>/<first-two-chars-of-cache-file-name
          >/<cache_file_name>.<suffix>

          Example: cache_path =  ~/.kodi/userdata/addon_data/service.kodi.tts/cache
                   engine_code = goo (for google)
                   lang = 'en'
                   voice='us'  # For gtts
                   first-two-chars-of-cache-file-name = d4
                   hash of text  = cache_file_name = d4562ab3243c84746a670e47dbdc61a2
                   suffix = .mp3 or .txt
        """
        clz = type(self)
        try:
            engine_code: str = Settings.get_setting_str(self.service_key.with_prop(
                    SettingProp.CACHE_SUFFIX))
            assert engine_code is not None, \
                f'Can not find voice-cache dir for: {self.service_key}'

            cache_file_path: Path = phrase.get_cache_path()
            phrase_engine_code: str = str(cache_file_path.parent.parent.parent.name)
            if phrase_engine_code == engine_code:
                cache_dir: str = str(cache_file_path.parent.parent.parent.parent.name)
                clz.referenced_cache_dirs[cache_dir] = cache_dir
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return

    @classmethod
    def register_cache_change_listener(cls,
                                       cache_change_listener: Callable[[str],
                                                                       None]) -> None:
        cls.cache_change_listener = cache_change_listener
        if not cls.cache_changed():
            # Re-register if not fired
            cls.cache_change_listener = cache_change_listener

    @classmethod
    def cache_changed(cls) -> bool:
        """

        :return: True if the change_listener called, else False
        """
        if cls.cache_change_listener is None:
            return False
        try:
            value: str | None = None
            subdir: str | None = None
            while value is None:
                subdir, value = cls.referenced_cache_dirs.popitem()
            cls.cache_change_listener(subdir)
            return True
        except KeyError:
            pass
        return False


VoiceCache.init_thread()
