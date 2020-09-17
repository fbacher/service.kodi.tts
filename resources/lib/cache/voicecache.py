# -*- coding: utf-8 -*-

import datetime
import hashlib
import io
import os
import time
import xbmcvfs

from common.configuration_utils import ConfigUtils
from common.constants import Constants
from common.logger import LazyLogger
from common.settings import Settings


if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = LazyLogger.get_addon_module_logger().getChild(
        'lib.cache')
else:
    module_logger = LazyLogger.get_addon_module_logger()


class VoiceCache:

    _logger = None
    ignore_cache_count = 0

    def __init__(self):
        VoiceCache._logger = module_logger.getChild(
            self.__class__.__name__)  # type: LazyLogger

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
        path = VoiceCache.get_path_to_voice_file(text_to_voice, suffix)

        exception_occurred = False
        file_exists = False
        try:
            if not os.path.exists(path):
                cls._logger.debug_verbose(
                    'Not cached: {} {}'.format(text_to_voice, path))
                return path, file_exists

            if not os.access(path, os.R_OK):
                cls._logger.debug_verbose(
                    'VoiceCache.get_sound_file- Can not read cache file: {}'.format(path))
                return path, file_exists

            expiration_time = time.time() - \
                datetime.timedelta(Settings.getSetting(
                    Settings.CACHE_EXPIRATION_DAYS,
                    Settings.CACHE_EXPIRATION_DEFAULT)).total_seconds()

            if os.stat(path).st_mtime < expiration_time:
                cls._logger.debug_verbose(
                    'VoiceCache.get_sound_file- Expired sound file: {}'.format(path))
                return path, file_exists

        except Exception as e:
            cls._logger.error(
                'Exception accessing voice file: {}'.format(path))
            cls._logger.error(str(e))
            exception_occurred = True

        try:
            # Blow away bad cache file
            if exception_occurred and path is not None:
                os.remove(path)
        except Exception as e:
            cls._logger.error('Trying to delete bad cache file.')

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

    @staticmethod
    def get_path_to_voice_file(text_to_voice, suffix):
        file_name = VoiceCache.get_hash(text_to_voice) + suffix
        cache_directory = Settings.getSetting(Settings.CACHE_PATH)
        cache_directory = xbmcvfs.translatePath(cache_directory)
        path = os.path.join(cache_directory, file_name)
        return path

    @staticmethod
    def get_hash(text_to_voice):
        hash_value = hashlib.md5(text_to_voice.encode('UTF-8')).hexdigest()

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
        path = VoiceCache.get_path_to_voice_file(text_to_voice, suffix)
        cache_directory = Settings.getSetting(Settings.CACHE_PATH,
                                              Constants.DEFAULT_CACHE_DIRECTORY)
        try:
            if not os.path.exists(cache_directory):
                try:
                    os.makedirs(cache_directory)
                except Exception as e:
                    cls._logger.error(
                        'Can not create cache directory: {}'.format(cache_directory))

            if os.path.exists(path) and not os.access(path, os.W_OK):
                cls._logger.error('Can not write cache file: {}'.format(path))
            with io.open(path, mode='wb') as cacheFile:
                cacheFile.write(voiced_text)
                cacheFile.flush()
        except Exception as e:
            cls._logger.error('Can not write cache file: {}'.format(path))

    @classmethod
    def clean_cache(cls, purge=False):
        return
        dummy_cached_file = VoiceCache.get_path_to_voice_file('', '')
        cache_directory, _ = os.path.split(dummy_cached_file)
        expiration_time = time.time() - \
            Settings.getSetting(
                'cache_expiration_days', 30) * 86400
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
