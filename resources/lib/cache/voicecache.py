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
from pathlib import Path

import xbmcvfs

from common import *

from backends.audio.sound_capabilties import SoundCapabilities
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
from common.settings import Settings
from common.settings_low_level import SettingsProperties

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_logger(__name__)
else:
    module_logger = BasicLogger.get_logger(__name__)


class VoiceCache:
    """

    """
    _logger: BasicLogger = None
    ignore_cache_count: int = 0
    sound_file_base = '{filename}{suffix}'
    referenced_cache_dirs: Dict[str, str] = {}  # Acts as a set with value == key
    cache_change_listener: Callable = None

    def __init__(self):
        """
        Creates a VoiceCache instance meant to be used by a particular TTS engine.
        """
        clz = type(self)
        VoiceCache._logger = module_logger

    def get_cache_directory(self) -> pathlib.Path:
        clz = type(self)
        cache_directory: str = None
        try:
            cache_path: str = Settings.get_cache_base()
            engine_id: str = Settings.get_engine_id()
            engine_dir: str = SettingsMap.get_service_property(engine_id,
                                                               Constants.CACHE_SUFFIX)
            assert engine_dir is not None, \
                f'Can not find voice-cache dir for engine: {engine_id}'
            cache_directory = xbmcvfs.translatePath(f'{cache_path}/{engine_dir}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
        return pathlib.Path(cache_directory)

    def get_path_to_voice_file(self, phrase: Phrase,
                               use_cache: bool = False) -> Tuple[str, bool]:
        """
        If results of the speech engine are cached, then this function
        returns the path to retrieve or store the voiced file in/from the
        cache.
        When caching is not used, then the temporary file path for the
        engine output is returned.

        SoundCapabilities are used by consumers/producers of voiced files to
        trade what sound file formats each endpoint is capable of producing
        or consuming, as well as the order of preference.

        @param phrase:
        @param use_cache: True a path in the cache is to be created, otherwise
                        a path to a temp-file will be created

        @return: path, exists: Path is the path to the voiced text. exists
        is True when the voiced text is already in the cache at the path location
        """
        clz = type(self)
        voice_file: str = ''
        exists: bool = False
        try:
            engine_id: str = Settings.get_engine_id()
            player: IPlayer
            player_id: str = Settings.get_player_id(engine_id=engine_id)
            player = PlayerIndex.get_player(player_id)
            input_formats: List[str] = SoundCapabilities.get_input_formats(player_id)
            file_type: str = None
            if use_cache:
                paths: Tuple[str, bool, str] = self.get_best_path(phrase,
                                                                   input_formats)
                voice_file, exists, file_type = paths
            else:
                file_type: str = input_formats[0]
                tempdir: str = player.get_sound_dir()
                temp_voice_file = tempfile.NamedTemporaryFile(mode='w+b', buffering=-1,
                                                              suffix=None,
                                                              prefix=None,
                                                              dir=tempdir,
                                                              delete=False)
                voice_file = temp_voice_file.name
                phrase.set_cache_path(Path(voice_file, temp=True), False)
                exists = False
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException as e:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
        return voice_file, exists

    def get_best_path(self, phrase: Phrase,
                      sound_file_types: List[str]) -> Tuple[str, bool, str]:
        """
        Finds the best voiced version of the given text in the cache, according
        to the sound_file_types search order

        This method is typically called before having the voice engine voice the text

        :param phrase: Voiced text to find
        :param sound_file_types: Preference order of sound file type of voiced
        text (.mp3 or .wav)
        :return: Tuple (path_to_voiced_file, exists, sound_file_type)

        Note that if no voiced file for the text is found, the path to the
        preferred file type is returned, exists is false.
        """
        clz = type(self)
        best_voice_file: str = ''
        best_sound_file_type: str = ''
        best_exists: bool = False
        try:
            engine_id: str = Settings.get_engine_id()
            engine = BaseServices.getService(engine_id)
            if not self.is_cache_sound_files(engine):
                return '', False, ''

            results: Dict[str, Tuple[str, bool]]
            results = self.get_paths(phrase, sound_file_types)
            for suffix in results.keys():
                path: str
                exists: bool
                path, exists = results[suffix]
                if len(path) > 0:
                    best_voice_file = path
                    best_exists = exists
                    best_sound_file_type = suffix
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
        phrase.set_cache_path(Path(best_voice_file), best_exists)
        return best_voice_file, best_exists, best_sound_file_type

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
    def is_cache_sound_files(cls, backend_class: ITTSBackendBase) -> bool:
        """
        Indicates whether caching is enabled
        :param backend_class: check if voiced text from this engine is cached
        :return: true if caching is enabled, otherwise false.
        """
        use_cache: bool = False
        try:
            if Settings.configuring_settings() and cls.ignore_cache_count < 3:
                cls.ignore_cache_count += 1
                return False

            use_cache = Settings.is_use_cache()
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
        return use_cache

    def get_sound_file_paths(self, phrase: Phrase,
                             suffixes: List[str]) -> Dict[str, Tuple[str, bool]]:
        """
        Checks to see if the given text is in the cache as already voiced

        :param phrase: The text to be voiced
        :param suffixes: Sound file suffixes (.mp3, .wav) to look for, in order of
        preference
        :return: A dictionary, indexed by one of the suffixes. The value is a
        tuple(path_to_sound_file, exists: bool).

        Note that even if the voiced text is not in the cache, the paths for
        where it should be located will be returned.
        """
        clz = type(self)
        results: Dict[str, Tuple[str, bool]] = {}
        try:
            for suffix in suffixes:
                suffix: str
                path_found: bool
                msg: str
                path: str
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

                            if os.stat(path).st_mtime < expiration_time:
                                clz._logger.debug_v(
                                        f'Expired sound file: {path}')
                                delete = True
                        except Exception as e:
                            msg: str = f'Exception accessing voice file: {path}'
                            clz._logger.warning(msg)
                            clz._logger.showNotification(msg)
                            exception_occurred = True
                            delete = True

                        if delete:
                            path_found = False
                            try:
                                # Blow away bad cache file
                                if exception_occurred and path is not None:
                                    os.remove(path)
                            except Exception as e:
                                clz._logger.warning(
                                        'Trying to delete bad cache file.')

                results[suffix] = (path, path_found)
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
        return results

    def get_paths(self, phrase: Phrase, suffixes: List[str]) \
            -> Dict[str, Tuple[str, bool]]:
        clz = type(self)
        results: Dict[str, Tuple[str, bool]] = {}
        try:
            path: str | None
            exists: bool
            path_info: Dict[str, Tuple[str, bool]]
            path_info = self.get_sound_file_paths(phrase, suffixes)
            for suffix in suffixes:
                exception_occurred: bool = False
                exists = False
                path = None
                if path_info.get(suffix):
                    path, exists = path_info[suffix]
                    if exists:
                        delete: bool = False
                        try:
                            voice_size: int = Path(path).stat().st_size
                            if voice_size < 1000:
                                delete = True
                            io.open(path, mode='rb')
                        except IOError as e:
                            msg: str = f'IOError reading voice file: {path}'
                            clz._logger.error(msg)
                            clz._logger.showNotification(msg)
                            exception_occurred = True
                            delete = True
                        except Exception as e:
                            msg: str = f'Exception reading voice file: {path}'
                            clz._logger.error(msg)
                            clz._logger.showNotification(msg)
                            exception_occurred = True
                            delete = True
                        if exception_occurred or delete \
                                and not Constants.IGNORE_CACHE_EXPIRATION_DATE:
                            exists = False
                            try:
                                os.remove(path)
                            except Exception as e:
                                msg: str = f'Error deleting bad cache file{path}'
                                clz._logger.error(msg)
                                clz._logger.showNotification(msg)
                if path and not exception_occurred:
                    results[suffix] = path, exists
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
        return results

    def _get_path(self, phrase: Phrase, suffix: str) -> Tuple[bool, str, str]:
        clz = type(self)
        path: Path = None
        path_found: bool = True
        msg: str = ''
        try:
            filename: str = self.get_hash(phrase.text)
            filename = clz.sound_file_base.format(filename=filename, suffix=suffix)
            subdir: str = filename[0:2]
            path = Path(self.get_cache_directory(), phrase.lang_dir,
                        phrase.territory_dir, subdir)
            path.mkdir(mode=0o777, exist_ok=True, parents=True)
            path = path.joinpath(filename)
            if path.is_dir():
                msg = f'Ignoring cached voice file: {path}. It is a directory.'
                path_found = False
                clz._logger.showNotification(msg)
            elif not path.exists():
                msg = f'Ignoring cached voice file: {path}. Not found.'
                path_found = False
            if path_found:
                if not os.access(str(path), os.R_OK):
                    msg = f'Ignoring cached voice file: {str(path)}. No read access.'
                    path_found = False
                    clz._logger.showNotification(msg)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
            path_found: bool = False
            msg: str = repr(e)
            path = None
        # Extract any volume, pitch, speed information embedded in name
        return path_found, msg, str(path)

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
            p = voice_file_path
            if not p.parent.is_dir():
                try:
                    p.parent.mkdir(mode=0o777, parents=True, exist_ok=True)
                except:
                    cls._logger.error(f'Can not create directory: {p.parent}')
                    rc = 1
                    return rc, None

            if create_dir_only:
                return rc, None

            try:
                cache_file = voice_file_path.open(mode='wb')
            except Exception as e:
                rc = 2
                cls._logger.error(f'Can not create cache file: {voice_file_path}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
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
                            cls._logger.debug_v('Deleting: {}'.format(path))
                            os.remove(path)
                    except Exception as e:
                        pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
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
                if Settings.is_use_cache():
                    self.get_path_to_voice_file(phrase, use_cache=True)
                    if not phrase.exists():
                        text: str = phrase.get_text()
                        voice_file_path: pathlib.Path = phrase.get_cache_path()
                        clz._logger.debug(f'PHRASE Text {text}')
                        rc: int = 0
                        try:
                            text_file: pathlib.Path | None
                            text_file = voice_file_path.with_suffix('.txt')
                            try:
                                if text_file.is_file() and text_file.exists():
                                    text_file.unlink()

                                with open(text_file, 'wt', encoding='utf-8') as f:
                                    f.write(text)
                            except Exception as e:
                                if clz._logger.isEnabledFor(ERROR):
                                    clz._logger.error(
                                            f'Failed to save text file: '
                                            f'{text_file} Exception: {str(e)}')
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                        'Failed to save text: {}'.format(str(e)))
        except Exception as e:
            clz._logger.exception('')

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
            cache_path: str = Settings.get_cache_base()
            engine_id: str = Settings.get_engine_id()
            engine_code: str = SettingsMap.get_service_property(engine_id,
                                                                Constants.CACHE_SUFFIX)
            assert engine_code is not None, \
                f'Can not find voice-cache dir for engine: {engine_id}'
            # cache_directory = xbmcvfs.translatePath(f'{cache_path}/{engine_code}')

            cache_file_path = phrase.get_cache_path()
            phrase_engine_code: str = str(cache_file_path.parent.parent.parent.name)
            if phrase_engine_code == engine_code:
                cache_dir: str = str(cache_file_path.parent.parent.parent.parent.name)
                clz.referenced_cache_dirs[cache_dir] = cache_dir
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
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
            value: str = None
            subdir: str = None
            while value is None:
                subdir, value = cls.referenced_cache_dirs.popitem()
            cls.cache_change_listener(subdir)
            return True
        except KeyError:
            pass
        return False


#  instance = VoiceCache()
