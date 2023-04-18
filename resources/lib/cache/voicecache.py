# -*- coding: utf-8 -*-

import datetime
import hashlib
import io
import os
import time
from pathlib import Path, PosixPath

import xbmcvfs

from common.typing import *
from common.constants import Constants
from common.logger import *
from common.settings import Settings


if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)
else:
    module_logger = BasicLogger.get_module_logger()


class VoiceCache:

    _logger: BasicLogger = None
    ignore_cache_count = 0

    def __init__(self):
        VoiceCache._logger = module_logger.getChild(
            self.__class__.__name__)

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
    def is_cache_sound_files(cls, backend_class):
        if Settings.configuring_settings() and cls.ignore_cache_count < 3:
            cls.ignore_cache_count += 1
            return False

        return backend_class.getSetting(Settings.CACHE_SPEECH)

    @classmethod
    def get_sound_file_path(cls, text_to_voice, suffix):
        path_found: bool
        msg: str
        path: str
        path_found, msg, path = cls.get_path_to_read_voice_file(text_to_voice, suffix)
        exception_occurred = False
        file_exists = False
        try:
            expiration_time = time.time() - \
                datetime.timedelta(Settings.getSetting(
                    Settings.CACHE_EXPIRATION_DAYS, None,
                    Settings.CACHE_EXPIRATION_DEFAULT)).total_seconds()

            if os.stat(path).st_mtime < expiration_time:
                cls._logger.debug_verbose(f'Expired sound file: {path}')

                if Constants.IGNORE_CACHE_EXPIRATION_DATE:
                    return path, file_exists

        except Exception as e:
            cls._logger.warning(f'Exception accessing voice file: {path}')
            cls._logger.warning(str(e))
            exception_occurred = True

        try:
            # Blow away bad cache file
            if exception_occurred and path is not None:
                os.remove(path)
        except Exception as e:
            cls._logger.warning('Trying to delete bad cache file.')

        file_exists = True
        return path, file_exists

    @classmethod
    def get_text_to_speech(cls, text_to_voice, suffix):
        path, exists = cls.get_sound_file_path(text_to_voice, suffix)

        exception_occurred = False
        voiced_text = None
        if exists:
            try:
                with io.open(path, mode='rb') as cache_file:
                    voiced_text = cache_file.read()
            except IOError as e:
                cls._logger.error(
                    'IOError reading voice file: {}'.format(path))
                cls._logger.error(str(e))
                exception_occurred = True
            except Exception as e:
                cls._logger.error(
                    'Exception reading voice file: {}'.format(path))
                cls._logger.error(str(e))
                exception_occurred = True

            try:
                # Blow away bad cache file
                if exception_occurred and path is not None:
                    os.remove(path)
            except Exception as e:
                cls._logger.error('Trying to delete bad cache file.')

        if voiced_text is not None:
            cls._logger.debug_verbose(
                'found: {} for: {}'.format(path, text_to_voice))
        return path, voiced_text

    @classmethod
    def get_path_to_read_voice_file(cls, text_to_voice: str, suffix: str) -> Tuple[bool, str, str]:
        file_name: str = VoiceCache.get_hash(text_to_voice)
        cache_directory: str = xbmcvfs.translatePath(Settings.getSetting(Settings.CACHE_PATH,
                                                                         None))

        path = Path(cache_directory + '/' + file_name + suffix)
        path_found: bool = True
        msg: str = ''
        if path.is_dir():
            msg = f'Ignoring cached voice file: {path}. It is a directory.'
            path_found = False
        elif not path.exists():
            msg = f'Ignoring cached voice file: {path}. Not found.'
            path_found = False
        if path_found:
            if not os.access(str(path), os.R_OK):
                msg = f'Ignoring cached voice file: {str(path)}. No read access.'
                path_found = False
        # Extract any volume, pitch, speed information embedded in name

        return path_found, msg, str(path)

    @classmethod
    def get_path_to_write_voice_file(cls, text_to_voice: str, suffix: str) -> Tuple[bool, str, bool, bool, str]:
        file_name = VoiceCache.get_hash(text_to_voice)
        preferred_directory = Settings.getSetting(Settings.CACHE_PATH, None)
        preferred_directory = xbmcvfs.translatePath(preferred_directory)
        default_directory: str = Constants.DEFAULT_CACHE_DIRECTORY
        status, good_path, created, alternate_used, msg = cls.check_directory(preferred_directory,
                                                                              default_directory)
        return status, good_path, created, alternate_used, msg

    @classmethod
    def check_directory(cls, preferred_path: str, alternate_path: str,
                        create_dir: bool = True) -> Tuple[bool, str, bool, bool, str]:
        '''
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
        '''
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
                      f'No caching will occur.'
        return ok, good_path, created_dir, alternate_used, msg

    @classmethod
    def get_hash(cls, text_to_voice):
        hash_value = hashlib.md5(text_to_voice.encode('UTF-8')).hexdigest()
        cls._logger.debug(f'text: |{text_to_voice}|\n hash: {hash_value}')
        return hash_value

    @classmethod
    def save_sound_file(cls, text_to_voice,  # type: str
                        suffix,  # type: str
                        voiced_text  # type: bytes
                        ):
        # type: (str, str, bytes) -> None
        """
            Write the given voiced text to the cache
        """
        """
        (ok, good_path, created, alternate_used)
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
        ok: bool # True if everything normal
        good_path: str  # either preferred, or alternate path. Invalid if ok = false
        created: bool # True if directory created
        alternate_used: bool # True if default cache path used
        msg: str # Error text for logging/display

        ok, good_path, created, alternate_used, msg = VoiceCache.get_path_to_write_voice_file(text_to_voice, suffix)
        if ok:
            try:
                with io.open(good_path, mode='wb') as cacheFile:
                    cacheFile.write(voiced_text)
                    cacheFile.flush()
            except Exception as e:
                cls._logger.error('Can not write cache file: {}'.format(good_path))
        if not ok or alternate_used:
            cls._logger.info(msg)
            #  TODO: Add popup

    @classmethod
    def clean_cache(cls, purge=False):
        return
        dummy_cached_file = VoiceCache.get_path_to_voice_file('', '')
        cache_directory, _ = os.path.split(dummy_cached_file)
        expiration_time = time.time() - \
            Settings.getSetting(
                'cache_expiration_days', None, 30) * 86400
        for root, dirs, files in os.walk(cache_directory, topdown=False):
            for file in files:
                try:
                    path = os.path.join(root, file)
                    if purge or os.stat(path).st_mtime < expiration_time:
                        cls._logger.debug_verbose('Deleting: {}'.format(path))
                        os.remove(path)
                except Exception as e:
                    pass


instance = VoiceCache()
