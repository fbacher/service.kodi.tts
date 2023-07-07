# -*- coding: utf-8 -*-

import datetime
import hashlib
import io
import os
import sys
import time
from pathlib import Path
from typing import IO

import xbmcvfs

from backends.audio.sound_capabilties import SoundCapabilities
from backends.backend_info_bridge import BackendInfoBridge
from backends.i_tts_backend_base import ITTSBackendBase
from backends.players.iplayer import IPlayer
from backends.players.player_index import PlayerIndex
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import *
from common.phrases import Phrase
from common.setting_constants import Backends
from common.settings import Settings
from common.settings_low_level import SettingsProperties
from common.typing import *

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)
else:
    module_logger = BasicLogger.get_module_logger()


class VoiceCache:
    """

    """
    _logger: BasicLogger = None
    ignore_cache_count: int = 0
    cache_directory: str
    sound_file_base = '{filename}{suffix}'

    def __init__(self):
        clz = type(self)
        VoiceCache._logger = module_logger.getChild(
            self.__class__.__name__)
        try:
            cache_path: str = Settings.get_cache_base()
            engine_id: str = Settings.get_engine_id()
            engine_dir: str = Backends.ENGINE_CACHE_CODE.get(engine_id, None)
            assert engine_dir is not None, \
                f'Can not find voice-cache dir for engine: {engine_id}'

            clz.cache_directory = xbmcvfs.translatePath(f'{cache_path}/{engine_dir}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')

    @classmethod
    def get_path_to_voice_file(cls, phrase: Phrase,
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
        @param use_cache:
        @return: path, exists: Path is the path to the voiced text. exists
        is True when the voiced text is already in the cache at the path location
        """
        voice_file: str = ''
        exists: bool = False
        try:
            engine_id: str = Settings.get_engine_id()
            player: IPlayer
            player_id: str = Settings.get_player_id(engine_id=engine_id)
            player = PlayerIndex.get_player(player_id)
            input_formats: List[str] = SoundCapabilities.get_input_formats(player_id)
            file_type: str = ''
            if use_cache:
                paths: Tuple[str, bool, str] = VoiceCache.get_best_path(phrase,
                                                                        input_formats)
                voice_file, exists, file_type = paths
            else:
                voice_file = player.get_tmp_path(phrase.get_text(), input_formats[0])
                phrase.set_cache_path(Path(voice_file), False)
                exists = False
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
        return voice_file, exists

    @classmethod
    def get_best_path(cls, phrase: Phrase,
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
        best_voice_file: str = ''
        best_sound_file_type: str = ''
        best_exists: bool = False
        try:
            engine_id: str = Settings.get_engine_id()
            backend_class: ITTSBackendBase = BaseServices.getService(engine_id)
            if not cls.is_cache_sound_files(backend_class):
                return '', False, ''

            results: Dict[str, Tuple[str, bool]]
            results = VoiceCache.get_paths(phrase, sound_file_types)
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
        except Exception as e:
            cls._logger.exception('')
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

    @classmethod
    def get_sound_file_paths(cls, phrase: Phrase,
                             suffixes: List[str]) -> Dict[str, Tuple[str, bool]]:
        """
        Checks to see if the given text is in the cache as already voiced

        :param phrase: The text go be voiced
        :param suffixes: Sound file suffixes (.mp3, .wav) to look for, in order of
        preference
        :return: A dictionary, indexed by one of the suffixes. The value is a
        tuple(path_to_sound_file, exists: bool).

        Note that even if the voiced text is not in the cache, the paths for
        where it should be located will be returned.
        """
        results: Dict[str, Tuple[str, bool]] = {}
        try:
            for suffix in suffixes:
                suffix: str
                path_found: bool
                msg: str
                path: str
                text_to_voice: str = phrase.get_text()
                path_found, msg, path = cls._get_path(text_to_voice, suffix)
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
                                cls._logger.debug_verbose(
                                    f'Expired sound file: {path}')
                                delete = True
                        except Exception as e:
                            msg: str = f'Exception accessing voice file: {path}'
                            cls._logger.warning(msg)
                            cls._logger.showNotification(msg)
                            exception_occurred = True
                            delete = True

                        if delete:
                            path_found = False
                            try:
                                # Blow away bad cache file
                                if exception_occurred and path is not None:
                                    os.remove(path)
                            except Exception as e:
                                cls._logger.warning(
                                    'Trying to delete bad cache file.')

                results[suffix] = (path, path_found)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
        return results

    @classmethod
    def get_paths(cls, phrase: Phrase, suffixes:List[str]) \
            -> Dict[str, Tuple[str, bool]]:
        results: Dict[str, Tuple[str, bool]] = {}
        try:
            path: str | None
            exists: bool
            text_to_voice: str = phrase.get_text()
            path_info: Dict[str, Tuple[str, bool]]
            path_info = cls.get_sound_file_paths(phrase, suffixes)
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
                            cls._logger.error(msg)
                            cls._logger.showNotification(msg)
                            exception_occurred = True
                            delete = True
                        except Exception as e:
                            msg: str = f'Exception reading voice file: {path}'
                            cls._logger.error(msg)
                            cls._logger.showNotification(msg)
                            exception_occurred = True
                            delete = True
                        if exception_occurred or delete \
                                and not Constants.IGNORE_CACHE_EXPIRATION_DATE:
                            exists = False
                            try:
                                os.remove(path)
                            except Exception as e:
                                msg: str = f'Error deleting bad cache file{path}'
                                cls._logger.error(msg)
                                cls._logger.showNotification(msg)
                if path and not exception_occurred:
                    results[suffix] = path, exists
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
        return results

    @classmethod
    def _get_path(cls, text_to_voice: str, suffix: str) -> Tuple[bool, str, str]:
        path: Path = None
        path_found: bool = True
        msg: str = ''
        try:
            filename: str = VoiceCache.get_hash(text_to_voice)
            filename = cls.sound_file_base.format(filename=filename, suffix=suffix)
            subdir: str = filename[0:2]
            path = Path(cls.cache_directory, subdir, filename)
            if path.is_dir():
                msg = f'Ignoring cached voice file: {path}. It is a directory.'
                path_found = False
                cls._logger.showNotification(msg)
            elif not path.exists():
                msg = f'Ignoring cached voice file: {path}. Not found.'
                path_found = False
            if path_found:
                if not os.access(str(path), os.R_OK):
                    msg = f'Ignoring cached voice file: {str(path)}. No read access.'
                    path_found = False
                    cls._logger.showNotification(msg)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
            path_found: bool = False
            msg: str = repr(e)
            path = None
        # Extract any volume, pitch, speed information embedded in name
        return path_found, msg, str(path)

    '''
    @classmethod
    def get_path_to_write_voice_file(cls, text_to_voice: str,
                                     suffix: str) -> Tuple[bool, str, bool, bool, str]:
        preferred_directory = Settings.getSetting(SettingsProperties.CACHE_PATH, None)
        preferred_directory = xbmcvfs.translatePath(preferred_directory)
        default_directory: str = Constants.DEFAULT_CACHE_DIRECTORY
        status, good_path, created, alternate_used, msg = cls.check_directory(
            preferred_directory,
            default_directory)
        filename: str = VoiceCache.get_hash(text_to_voice)
        filename = cls.sound_file_base.format(filename=filename, suffix=suffix)
        path = str(Path(good_path, filename))
        return status, path, created, alternate_used, msg

    @classmethod
    def check_directory(cls, preferred_path: str, alternate_path: str,
                        create_dir: bool = True) -> Tuple[bool, str, bool, bool, str]:
        """
        :return: (ok, good_path, created, alternate_used)
                  ok == True means returned path is writeable by user
                        False means neither preferred or alternate path exists
                        nor created with the correct permissions
                  good_path = Either preferred_path or alternate_path, whichever
                        was found to work first. Empty if ok = False
                  created = True when good_path was created
                  alternate_used = Only meaninguful if ok = True
                                   True when preferred_path was not useable, but
                                   the alternate was.
                  msg = message explaining failure
        """
        ok: bool = True
        good_path: str = ""
        created_dir: bool = False
        alternate_used: bool = False
        msg: str = ""
        same_path: bool = preferred_path == alternate_path
        paths: Tuple[str, str]
        if same_path:
            paths = tuple(preferred_path)
        else:
            paths = (preferred_path, alternate_path)

        for path in paths:
            if not os.path.exists(path) and create_dir:
                cachePath: Path = Path(preferred_path)
                try:
                    if not os.access(cachePath, os.O_RDWR):
                        alternate_used = True
                        break

                    cachePath.mkdir(mode=0o777, parents=True, exist_ok=True)
                    created_dir = True
                    good_path = path
                    break
                except:
                    pass

                alternate_used = True

        if not good_path:
            ok = False
            alternate_used = False
            if same_path:
                msg = f'Can not use or create TTS cache directory: {preferred_path}. ' \
                      f'No caching will occur.'
            else:
                msg = f'Neither the specified TTS cache directory: {preferred_path} ' \
                      f'nor the default cache directory: {alternate_path} were useable. ' \
                      f'' \
                      f'No caching will occur.'
        return ok, good_path, created_dir, alternate_used, msg
    '''

    @classmethod
    def get_hash(cls, text_to_voice: str) -> str:
        hash_value: str = hashlib.md5(
            text_to_voice.encode('UTF-8')).hexdigest()
        return hash_value

    @classmethod
    def create_sound_file(cls, voice_file_path: Path,
                          create_dir_only: bool=False)\
            -> Tuple[int, IO[io.BufferedWriter] | None]:
        """
            Create given voice_file_path and return file handle to it
        """

        rc: int = 0
        cache_file: IO[io.BufferedWriter] | None = None
        try:
            p = voice_file_path
            if not os.path.exists(p.parent):
                try:
                    p.parent.mkdir(mode=0o777, parents=True, exist_ok=True)
                except:
                    cls._logger.error(f'Can not create directory: {p.parent}')
                    rc = 1
                    return rc, None

            if create_dir_only:
                return rc, None

            try:
                cache_file = io.open(voice_file_path, mode='wb')
            except Exception as e:
                rc = 2
                cls._logger.error(f'Can not create cache file: {voice_file_path}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
        return rc, cache_file

    '''
    @classmethod
    def save_sound_file(cls, text_to_voice: str,
                        suffix: str,
                        voiced_text: bytes
                        ) -> int:
        """
            Write the given voiced text to the cache
        """
        """
        (ok, good_path, created, alternate_used)
        ok == True means returned path is writeable by user
        False means neither preferred nor alternate path exists
        nor created with the correct permissions
        good_path = Either preferred_path or alternate_path, whichever
        was found to work first. Empty if ok = False
        created = True when good_path was created
        alternate_used = Only meaninguful if ok = True
        True when preferred_path was not useable, but
        the alternate was.
        msg = message explaining failure
        """
        ok: bool  # True if everything normal
        good_path: str  # either preferred, or alternate path. Invalid if ok = false
        created: bool  # True if directory created
        alternate_used: bool  # True if default cache path used
        msg: str  # Error text for logging/display
        rc: int

        ok, good_path, created, alternate_used, msg = \
            VoiceCache.get_path_to_write_voice_file(text_to_voice, suffix)
        if not ok:
            rc = 2
        elif alternate_used:
            rc = 3
        if ok:
            try:
                with io.open(good_path, mode='wb') as cacheFile:
                    cacheFile.write(voiced_text)
                    cacheFile.flush()
            except Exception as e:
                rc = 1
                cls._logger.error(
                    'Can not write cache file: {}'.format(good_path))
        if not ok or alternate_used:
            cls._logger.info(msg)
            #  TODO: Add popup
        return rc
    '''

    @classmethod
    def clean_cache(cls, purge: bool = False) -> None:
        return
        try:
            dummy_cached_file: str = VoiceCache.get_path_to_voice_file('', '')
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
                            cls._logger.debug_verbose('Deleting: {}'.format(path))
                            os.remove(path)
                    except Exception as e:
                        pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')


instance = VoiceCache()
