# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import datetime
import hashlib
import io
import os
import pathlib
import sys
import tempfile
import time
from collections import namedtuple
from pathlib import Path

import xbmcvfs

from backends.settings.service_types import ServiceType
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
from common.phrases import Phrase, PhraseList
from common.setting_constants import AudioType, Backends, Players
from common.settings import Settings
from common.settings_low_level import SettingsProperties

MY_LOGGER = BasicLogger.get_logger(__name__)


class VoiceCache:
    """

    """
    ignore_cache_count: int = 0
    # Does not have full path, just directory name
    referenced_cache_dirs: Dict[str, str] = {}  # Acts as a set with value == key
    cache_change_listener: Callable = None
    tmp_dir: Path | None = None

    def __init__(self, service_id: str, reset_engine_each_call=False):
        """
        Creates a VoiceCache instance meant to be used by a particular TTS engine.
        """
        clz = type(self)
        self.reset_engine_each_call: bool = reset_engine_each_call
        self.service_id: str = service_id
        self.engine_id: str | None = None
        self.engine: BaseServices | None = None
        self._top_of_engine_cache: Path | None = None
        self._audio_type: AudioType = None
        self.reset_engine()

    def reset_engine(self) -> None:
        cache_directory: Path | None = None
        try:
            cache_path: str = Settings.get_cache_base()
            self.engine_id: str = self.service_id
            if self.engine_id is None:
                self.engine_id = Settings.get_engine_id()
            MY_LOGGER.debug(f'engine_id: {self.engine_id}')
            self.engine = BaseServices.getService(self.engine_id)
            service_type: ServiceType
            if self.service_id in Players.ALL_PLAYER_IDS:
                service_type = ServiceType.PLAYER
                self._audio_type = Settings.get_current_input_format(self.service_id)
            if self.service_id in Backends.ALL_ENGINE_IDS:
                service_type = ServiceType.ENGINE
                self._audio_type = Settings.get_current_output_format(self.service_id)

            # Suffix is
            engine_dir: str = SettingsMap.get_service_property(self.engine_id,
                                                               Constants.CACHE_SUFFIX)
            assert engine_dir is not None, \
                f'Can not find voice-cache dir for engine: {self.engine_id}'
            cache_top: Path = SettingsMap.get_service_property(self.engine_id,
                                                               Constants.CACHE_TOP)
            if cache_top is not None:
                cache_directory = cache_top / engine_dir
            else:
                cache_directory = Path(xbmcvfs.translatePath(f'{cache_path}/{engine_dir}'))
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        self._top_of_engine_cache = Path(cache_directory)
        return

    @classmethod
    def is_tmp_file(cls, file_path: Path) -> bool:
        """
        Determines if the given file_path is a temp file

        :param file_path:
        :return:
        """
        temp_root: Path = cls.temp_dir()
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

        if self.reset_engine_each_call or self.engine is None:
            self.reset_engine()
        return self._top_of_engine_cache

    @property
    def audio_type(self) -> AudioType:
        return self._audio_type

    @property
    def audio_suffix(self) -> str:
        return f'.{self.audio_type}'

    def get_path_to_voice_file(self, phrase: Phrase,
                               use_cache: bool = False
                               ) -> CacheEntryInfo:
        """
        If results of the speech engine are cached, then this function
        returns the path of the audio file for the phrase and other relevant
        information.

        When caching is not used, then the temporary file path for the
        engine output is returned,

        Note: All files related to a phrase differ only in their file suffix.
        Note: the engine, player or transcoder that created this VoiceCache instance
        sets the audio file type which is created or consumed by that service.

        @param phrase:
        @param use_cache: True a path in the cache is to be returned, otherwise
                        a path to a temp-file will be created

        @return: namedtuple('CacheEntryInfo',
                            'current_audio_path, '
                            'audio_exists',
                            'text_exists, audio_suffixes')
        current_audio_path is the path to the voiced phrase in the cache (file may
        not yet exist). audio_exits is True if the current_audio_path file is not empty.
        text_exists is a boolean that is True if the .txt file
        text_exists. audio_suffixes is a list of the suffixes of audio files for
        this phrase. (Normally only one suffix '.txt' exists)

        Note: When caching is NOT used, text_exists is None and audio_suffixes empty
        """
        exists: bool = False
        audio_exists: bool = False
        text_exists: bool = False
        audio_suffixes: List[str] = []
        cache_dir: Path | None = None
        cache_path: Path | None = None
        try:
            if not use_cache or not self.is_cache_sound_files(self.engine_id):
                phrase.set_audio_type(self.audio_type)
                temp_voice_file = self.tmp_file(f'{self.audio_suffix}')
                cache_path = Path(temp_voice_file.name)
                MY_LOGGER.debug(f'voice_file: {cache_path} audio_suffix: '
                                f'{self.audio_suffix}')
            else:
                try:
                    path: Path | None = None
                    cache_top: Path = self.cache_directory
                    lang_dir: str = phrase.lang_dir
                    territory_dir: str = phrase.territory_dir
                    filename: str = self.get_hash(phrase.text)
                    subdir: str = filename[0:2]
                    cache_dir: str = ''
                    if territory_dir is None or territory_dir == '':
                        cache_dir = cache_top / lang_dir / subdir
                    else:
                        cache_dir = cache_top / lang_dir / territory_dir / subdir
                    cache_path = cache_dir / filename
                    cache_path = cache_path.with_suffix(self.audio_suffix)
                    phrase.set_audio_type(self.audio_type)
                    if not cache_dir.exists():
                        try:
                            cache_dir.mkdir(mode=0o777, exist_ok=True, parents=True)
                        except:
                            MY_LOGGER.error(f'Can not create directory: {cache_dir}')
                            return CacheEntryInfo(current_audio_path=None,
                                                  text_exists=None,
                                                  audio_suffixes=audio_suffixes)
                    MY_LOGGER.debug(f'cache_dir: {cache_dir}')
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
        result = CacheEntryInfo(current_audio_path=cache_path,
                                audio_exists=audio_exists,
                                text_exists=text_exists,
                                audio_suffixes=audio_suffixes)
        MY_LOGGER.debug(f'result: {result}')
        return result

    @classmethod
    def temp_dir(cls) -> Path:
        """
        Controls the tempfile and tempfile.NamedTemporaryFile 'dir' entry
        used to create temporary audio files. A None value allows tempfile
        to decide.
        :return:
        """
        if cls.tmp_dir is None:
            tmpfs: Path | None = None
            tmpfs = utils.getTmpfs()
            if tmpfs is None:
                tmpfs = Path(Constants.PROFILE_PATH)
            tmpfs = tmpfs / 'kodi_speech'
            if not tmpfs.exists():
                tmpfs.mkdir(parents=True)
            cls.tmp_dir = tmpfs
        return cls.tmp_dir

    @classmethod
    def tmp_file(cls, file_type: str) -> tempfile.NamedTemporaryFile:
        tmp_dir: Path = cls.temp_dir()
        tmp_file = tempfile.NamedTemporaryFile(mode='w+b', buffering=-1,
                                               suffix=file_type,
                                               prefix=None,
                                               dir=tmp_dir,
                                               delete=False)
        return tmp_file

    '''
    def get_best_path(self, phrase: Phrase,
                      sound_file_types: List[str]) -> Tuple[Path, bool, str]:
        """
        Finds the best voiced version of the given text in the cache, according
        to the sound_file_types search order

        This method is typically called before having the voice engine voice the text

        :param phrase: Voiced text to find
        :param sound_file_types: Preference order of sound file type of voiced
        text (.mp3 or .wav)
        :return: Tuple (path_to_voiced_file, text_exists, sound_file_type)

        Note that if no voiced file for the text is found, the path to the
        preferred file type is returned, text_exists is false.
        """
        clz = type(self)
        best_voice_file: Path = Path()
        best_sound_file_type: str = ''
        best_exists: bool = False
        try:
            engine_id: str = Settings.get_engine_id()
            engine = BaseServices.getService(engine_id)
            if not self.is_cache_sound_files(engine):
                return best_voice_file, False, ''

            results: Dict[str, Tuple[Path, bool]]
            results = self.get_paths(phrase, sound_file_types)
            for suffix in results.keys():
                path: Path
                text_exists: bool
                path, text_exists = results[suffix]
                if str(path) != '':
                    best_voice_file = path
                    best_exists = text_exists
                    best_sound_file_type = suffix
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        phrase.set_cache_path(Path(best_voice_file), best_exists)
        return best_voice_file, best_exists, best_sound_file_type
    '''

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
    def is_cache_sound_files(cls, engine_id: str) -> bool:
        """
        Indicates whether caching is enabled
        :param engine_id: check if voiced text from this engine is cached
        :return: true if caching is enabled, otherwise false.
        """
        use_cache: bool = False
        try:
            if Settings.configuring_settings() and cls.ignore_cache_count < 3:
                cls.ignore_cache_count += 1
                return False

            use_cache = Settings.is_use_cache(engine_id)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return use_cache

    '''
    def get_sound_file_paths(self, phrase: Phrase,
                             suffixes: List[str]) -> Dict[str, Tuple[Path, bool]]:
        """
        Checks to see if the given text is in the cache as already voiced

        :param phrase: The text to be voiced
        :param suffixes: Sound file suffixes (.mp3, .wav) to look for, in order of
        preference
        :return: A dictionary, indexed by one of the suffixes. The value is a
        tuple(path_to_sound_file, text_exists: bool).

        Note that even if the voiced text is not in the cache, the paths for
        where it should be located will be returned.
        """
        clz = type(self)
        results: Dict[str, Tuple[Path, bool]] = {}
        try:
            for suffix in suffixes:
                suffix: str
                path_found: bool
                msg: str
                path: Path
                path_found, msg, path = self._get_path(phrase, suffix)
                exception_occurred = False
                if path_found:
                    delete = False
                    if not Constants.IGNORE_CACHE_EXPIRATION_DATE:
                        try:
                            expiration_time = time.time() - \
                                              datetime.timedelta(Settings.getSetting(
                                                      SettingsProperties.CACHE_EXPIRATION_DAYS,
                                                      SettingsProperties.TTS_SERVICE,
                                                      SettingsProperties.CACHE_EXPIRATION_DEFAULT)).total_seconds()
                            if path.stat().st_mtime < expiration_time:
                                MY_LOGGER.debug_v(
                                        f'Expired sound file: {path}')
                                delete = True
                        except Exception as e:
                            msg: str = f'Exception accessing voice file: {path}'
                            MY_LOGGER.warning(msg)
                            MY_LOGGER.showNotification(msg)
                            exception_occurred = True
                            delete = True

                        if delete:
                            path_found = False
                            try:
                                # Blow away bad cache file
                                if exception_occurred and path is not None:
                                    path.unlink(missing_ok=True)
                            except Exception as e:
                                MY_LOGGER.warning(
                                        'Trying to delete bad cache file.')

                results[suffix] = (path, path_found)
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return results
    '''
    '''
    def get_paths(self,
                  phrase: Phrase) -> :
        clz = type(self)
        results: Dict[str, Tuple[Path, bool]] = {}
        try:
            path: Path | None
            text_exists: bool
            path_info: Dict[str, Tuple[Path, bool]]
            path_info = self.get_sound_file_paths(phrase, suffixes)
            for suffix in suffixes:
                exception_occurred: bool = False
                text_exists = False
                path = None
                if path_info.get(suffix):
                    path, text_exists = path_info[suffix]
                    if text_exists:
                        delete: bool = False
                        try:
                            voice_size: int = path.stat().st_size
                            if voice_size < 1000:
                                delete = True
                            path.open(mode='rb')
                        except IOError as e:
                            msg: str = f'IOError reading voice file: {path}'
                            MY_LOGGER.error(msg)
                            MY_LOGGER.showNotification(msg)
                            exception_occurred = True
                            delete = True
                        except Exception as e:
                            msg: str = f'Exception reading voice file: {path}'
                            MY_LOGGER.error(msg)
                            MY_LOGGER.showNotification(msg)
                            exception_occurred = True
                            delete = True
                        if exception_occurred or delete \
                                and not Constants.IGNORE_CACHE_EXPIRATION_DATE:
                            text_exists = False
                            try:
                                path.unlink(missing_ok=True)
                            except Exception as e:
                                msg: str = f'Error deleting bad cache file{path}'
                                MY_LOGGER.error(msg)
                                MY_LOGGER.showNotification(msg)
                if path and not exception_occurred:
                    results[suffix] = path, text_exists
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return results
    '''

    '''
    def _get_path(self, phrase: Phrase, suffix: str) -> Tuple[bool, str, Path | None]:
        clz = type(self)
        path: Path | None = None
        path_found: bool = True
        msg: str = ''
        try:
            filename: str = self.get_hash(phrase.text)
            filename = f'{filename}.{suffix}'
            subdir: str = filename[0:2]
            MY_LOGGER.debug(f'cache_dir: {self.get_cache_directory()}\n'
                            f'lang_dir: {phrase.lang_dir}\n'
                            f'territory: {phrase.territory_dir}\n'
                            f'subdir: {subdir}')
            path = Path(self.get_cache_directory(), phrase.lang_dir,
                        phrase.territory_dir, subdir)
            path.mkdir(mode=0o777, exist_ok=True, parents=True)
            path = path.joinpath(filename)
            if path.is_dir():
                msg = f'Ignoring cached voice file: {path}. It is a directory.'
                path_found = False
                MY_LOGGER.showNotification(msg)
            elif not path.text_exists():
                msg = f'Ignoring cached voice file: {path}. Not found.'
                path_found = False
            if path_found:
                if not os.access(path, os.R_OK):
                    msg = f'Ignoring cached voice file: {path}. No read access.'
                    path_found = False
                    MY_LOGGER.showNotification(msg)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            path_found: bool = False
            msg: str = repr(e)
            path = None
        # Extract any volume, pitch, speed information embedded in name
        return path_found, msg, path
    '''

    @classmethod
    def get_hash(cls, text_to_voice: str) -> str:
        hash_value: str = hashlib.md5(
                text_to_voice.encode('UTF-8')).hexdigest()
        return hash_value

    @classmethod
    def create_sound_file(cls, voice_file_path: Path,
                          create_dir_only: bool = False) \
            -> Tuple[int, BinaryIO | None]:
        """
            Create given voice_file_path and return file handle to it
        """

        rc: int = 0
        cache_file: BinaryIO | None = None
        try:
            p: Path
            p = voice_file_path
            if not p.parent.is_dir():
                try:
                    p.parent.mkdir(mode=0o777, parents=True, exist_ok=True)
                except:
                    MY_LOGGER.error(f'Can not create directory: {p.parent}')
                    rc = 1
                    return rc, None

            if create_dir_only:
                return rc, None

            try:
                cache_file = voice_file_path.open(mode='wb')
            except Exception as e:
                rc = 2
                MY_LOGGER.error(f'Can not create cache file: {voice_file_path}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return rc, cache_file

    def clean_cache(self, purge: bool = False) -> None:
        clz = type(self)
        return
    '''
        try:
            dummy_cached_file: str = self.get_path_to_voice_file('', '')
            cache_directory, _ = os.path.split(dummy_cached_file)
            expiration_time = time.time() - \
                              Settings.getSetting(
                                      SettingsProperties.CACHE_EXPIRATION_DAYS,
                                      SettingsProperties.TTS_SERVICE, 30) * 86400
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
            #  cache_path: str = Settings.get_cache_base()
            engine_id: str = Settings.get_engine_id()
            engine_code: str = SettingsMap.get_service_property(engine_id,
                                                                Constants.CACHE_SUFFIX)
            assert engine_code is not None, \
                f'Can not find voice-cache dir for engine: {engine_id}'

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
    def register_cache_change_listener(cls, cache_change_listener: Callable[
        [str], None]) -> None:
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


#  instance = VoiceCache()
